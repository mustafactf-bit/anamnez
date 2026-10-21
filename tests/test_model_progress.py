"""Byte progress, cache/resume/failure and actual Tk lower-left rendering."""
import tempfile
import io
import hashlib
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from speech.model_download import ByteProgress, ModelProgress, download_snapshot, download_whisper_model, model_cache, stream_file
from speech.errors import SpeechModelError
from speech.whisper_engine import WhisperEngine
import tests.test_ui as ui_tests

class DownloadTests(unittest.TestCase):
    def test_fixed_bytes_cached_and_resumed(self):
        events=[];tracker=ByteProgress('small',1000,200,events.append)
        tracker.update(0,True);tracker.update(300,True);tracker.update(800,True)
        self.assertEqual([e.percent for e in events],[20,50,99])
        self.assertEqual(events[-1].downloaded,1000)

    def test_unknown_size_is_never_fake_percent(self):
        events=[];tracker=ByteProgress('small',0,0,events.append);tracker.update(0,True)
        self.assertIsNone(events[-1].percent)

    def test_throttle_and_cap(self):
        events=[];tracker=ByteProgress('medium',100000,0,events.append)
        with patch('speech.model_download.time.monotonic',return_value=1):
            for i in range(10000):tracker.update(i)
        self.assertEqual(len(events),1)
        tracker.update(200000,True)
        self.assertEqual(events[-1].percent,99)

    def fake_download(self,fail=False,cached=False):
        with tempfile.TemporaryDirectory() as directory:
            folder=model_cache('small',directory)/('a'*40);folder.mkdir(parents=True)
            if cached:(folder/'config.json').write_bytes(b'1234')
            file=types.SimpleNamespace(rfilename='config.json',size=4)
            info=types.SimpleNamespace(sha='a'*40,siblings=[file])
            hub=types.SimpleNamespace(HfApi=Mock(return_value=Mock(model_info=Mock(return_value=info))))
            events=[]
            def stream(url,target,size,progress,sha):
                self.assertIn('/resolve/'+('a'*40)+'/',url)
                progress(0);progress(2)
                if fail:raise OSError('offline')
                target.write_bytes(b'1234')
            with patch.dict('sys.modules',{'huggingface_hub':hub}),patch('speech.model_download.stream_file',side_effect=stream),patch('speech.model_download.time.monotonic',side_effect=[100,101]):
                if fail:
                    with self.assertRaises(OSError):download_snapshot('repo/model','small',events.append,['config.json'],directory)
                else:download_snapshot('repo/model','small',events.append,['config.json'],directory)
            return events

    def test_metadata_pinned_and_success_only_100(self):
        events=self.fake_download()
        self.assertEqual([e.percent for e in events if e.phase=='downloading'],[0,50])
        self.assertEqual(events[-1].percent,100)

    def test_failure_never_emits_100(self):
        self.assertFalse(any(e.percent==100 for e in self.fake_download(fail=True)))

    def test_cached_snapshot_has_no_download_percent(self):
        events=self.fake_download(cached=True)
        self.assertEqual([e.phase for e in events],['checking','cached'])

    def test_complete_existing_cache_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            for file in ['config.json','model.bin','tokenizer.json','vocabulary.txt']:
                (Path(directory)/file).write_text('fixture')
            module=types.SimpleNamespace(download_model=Mock(return_value=directory))
            events=[]
            with patch.dict('sys.modules',{'faster_whisper.utils':module}),patch('speech.model_download.download_snapshot') as remote:
                self.assertEqual(download_whisper_model('small',events.append),directory)
                remote.assert_not_called()
            self.assertEqual(events[-1].phase,'cached')

    def test_engine_loads_local_path_after_download(self):
        events=[];engine=WhisperEngine();engine.on_progress=events.append
        whisper=types.SimpleNamespace(WhisperModel=Mock())
        with patch.dict('sys.modules',{'faster_whisper':whisper}),patch('speech.model_download.download_whisper_model',return_value='cached/path'):
            engine.load('medium')
            whisper.WhisperModel.assert_called_once_with('cached/path',device='cpu',compute_type='int8',local_files_only=True)
            self.assertEqual([e.phase for e in events],['loading','ready'])
            engine.load('medium');self.assertEqual(whisper.WhisperModel.call_count,1)

    def test_engine_failure_visible(self):
        engine=WhisperEngine();events=[];engine.on_progress=events.append
        with patch.dict('sys.modules',{'faster_whisper':types.SimpleNamespace(WhisperModel=Mock())}),patch('speech.model_download.download_whisper_model',side_effect=OSError):
            with self.assertRaises(SpeechModelError) as caught:engine.load('large-v3')
        self.assertEqual(caught.exception.stage,'download')
        self.assertEqual(events[-1].phase,'error');self.assertIsNone(engine.model)

    def test_http_range_resume_hash_and_bad_range(self):
        class Response(io.BytesIO):
            status=206
            headers={'Content-Range':'bytes 2-3/4'}
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'model.bin';partial=target.with_suffix('.bin.partial')
            partial.write_bytes(b'12');events=[]
            with patch('speech.model_download.urllib.request.urlopen',return_value=Response(b'34')) as request:
                stream_file('https://huggingface.co/r/resolve/a/model.bin?download=true',target,4,events.append,hashlib.sha256(b'1234').hexdigest())
                self.assertEqual(request.call_args.args[0].get_header('Range'),'bytes=2-3')
            self.assertEqual(target.read_bytes(),b'1234');self.assertFalse(partial.exists())
            target.unlink();partial.write_bytes(b'12')
            response=Response(b'34');response.headers={'Content-Range':'bytes 0-1/4'}
            with patch('speech.model_download.urllib.request.urlopen',return_value=response):
                with self.assertRaises(OSError):stream_file('https://example.test/x?download=true',target,4,events.append)
            self.assertFalse(target.exists())

    def test_http_hash_mismatch_never_completes(self):
        class Response(io.BytesIO):
            status=200
            headers={}
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'model.bin'
            with patch('speech.model_download.urllib.request.urlopen',return_value=Response(b'FAIL')):
                with self.assertRaises(OSError):stream_file('https://example.test/x?download=true',target,4,lambda _:None,'0'*64)
            self.assertFalse(target.exists());self.assertFalse(target.with_suffix('.bin.partial').exists())

class ProgressUITests(unittest.TestCase):
    setUp=ui_tests.UITests.setUp
    tearDown=ui_tests.UITests.tearDown
    pump=ui_tests.UITests.pump

    def test_worker_updates_real_green_bar_on_ui_thread(self):
        progress=self.app.model_progress
        self.app.bridge.start(lambda:self.app.speech_engine.on_progress(ModelProgress('downloading','small',37,37,100)),lambda _:None,lambda _:self.fail('worker failed'))
        self.pump()
        self.assertIn('%37',progress.text.get())
        self.assertAlmostEqual(progress.bar.coords(progress.fill)[2],230*.37)
        self.assertEqual(progress.bar.itemcget(progress.fill,'fill'),'#22a447')
        self.assertEqual(progress.frame.pack_info()['side'],'left')
        self.assertEqual(progress.frame.master.pack_slaves()[0],progress.frame)

    def test_ready_error_and_new_model_reset(self):
        progress=self.app.model_progress
        progress.update(ModelProgress('downloaded','small',100))
        self.assertIn('%100',progress.text.get())
        progress.update(ModelProgress('ready','small'))
        self.assertIn('hazır',progress.text.get())
        progress.reset();progress.update(ModelProgress('checking','large-v3'))
        self.assertEqual(progress.bar.coords(progress.fill)[2],0)
        self.assertNotIn('%100',progress.text.get())
        progress.update(ModelProgress('error','large-v3'))
        self.assertIn('tamamlanamadı',progress.text.get())
        self.assertEqual(progress.bar.coords(progress.fill)[2],0)
        self.assertEqual(progress.bar.cget('background'),'#fbe9e7')
