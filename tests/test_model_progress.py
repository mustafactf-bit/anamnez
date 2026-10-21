"""Byte progress, cache/resume/failure and actual Tk lower-left rendering."""
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from speech.model_download import ByteProgress, ModelProgress, download_snapshot, download_whisper_model
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
            cache=Path(directory)/'file';cache.write_bytes(b'1234')
            file=types.SimpleNamespace(rfilename='config.json',size=4)
            info=types.SimpleNamespace(sha='immutable-commit',siblings=[file])
            hub=types.SimpleNamespace(HfApi=Mock(return_value=Mock(model_info=Mock(return_value=info))),
                try_to_load_from_cache=Mock(return_value=str(cache) if cached else None))
            tracker=[];events=[]
            def factory(value):tracker.append(value);return object
            def snapshot(*args,**kwargs):
                self.assertEqual(kwargs['revision'],'immutable-commit')
                if not cached:tracker[0].update(2,True)
                if fail:raise OSError('offline')
                return directory
            hub.snapshot_download=Mock(side_effect=snapshot)
            with patch.dict('sys.modules',{'huggingface_hub':hub}),patch('speech.model_download.progress_class',side_effect=factory):
                if fail:
                    with self.assertRaises(OSError):download_snapshot('repo/model','small',events.append,['config.json'])
                else:download_snapshot('repo/model','small',events.append,['config.json'])
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
            with self.assertRaises(OSError):engine.load('large-v3')
        self.assertEqual(events[-1].phase,'error');self.assertIsNone(engine.model)

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
