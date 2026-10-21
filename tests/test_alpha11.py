"""Three actual UI commands, real worker orchestration and production raw policy."""
import json
import tempfile
import threading
import time
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
import tests.test_ui as ui_tests
from tests.test_note_workflow import FakeClipboard
from ai.dictation_corrector import correct_transcript, candidates, apply_edits
from storage.record_policy import prepare_record, without_legacy_raw
from config import INITIAL_DATA
from speech.audio_recorder import record_audio

RAW='Hiper tansiyon öyküsü var. Ateş yok. İlaç: amlodipin 2,5 mg. Potasyum 2.9.'


class CorrectionTests(unittest.TestCase):
    def test_dictionary_preserves_clinical_tokens(self):
        result=correct_transcript(RAW)
        self.assertIn('Hipertansiyon',result.text)
        for token in ['var','yok','amlodipin 2,5 mg','2.9']:self.assertIn(token,result.text)
        self.assertNotIn('Hiper tansiyon',result.text)
        self.assertFalse(hasattr(result,'raw'))

    def test_local_model_can_only_select_reviewed_patches(self):
        engine=Mock();engine.generate_json.return_value={'edits':candidates(RAW)}
        result=correct_transcript(RAW,engine)
        self.assertEqual(result.mode,'local_model')
        self.assertIn('Hipertansiyon',result.text)
        engine.unload.assert_called_once()

    def test_model_dose_negation_drug_and_invention_rejected(self):
        for source,replacement in [('2,5','25'),('yok','var'),('amlodipin','amiodaron'),('Potasyum','Yeni tanı')]:
            start=RAW.index(source)
            edit={'start':start,'end':start+len(source),'source':source,'replacement':replacement}
            text,count,rejected=apply_edits(RAW,[edit])
            self.assertEqual(text,RAW);self.assertEqual(count,0);self.assertEqual(rejected,1)

    def test_malformed_or_missing_model_falls_back_without_error(self):
        for value in ['not json',None,{'edits':'bad'},{'other':[]}]:
            engine=Mock();engine.generate_json.return_value=value
            result=correct_transcript(RAW,engine)
            self.assertTrue(result.text)
            self.assertIn('amlodipin 2,5 mg',result.text)
        engine=Mock();engine.generate_json.side_effect=MemoryError('synthetic')
        self.assertEqual(correct_transcript(RAW,engine).mode,'dictionary_fallback')

    def test_identity_line_is_not_corrected(self):
        raw='Hasta adı: Hiper tansiyon\nŞikâyet: halsizlk.'
        corrected=correct_transcript(raw).text
        self.assertIn('Hasta adı: Hiper tansiyon',corrected)
        self.assertIn('halsizlik',corrected)

    def test_stale_offsets_duplicate_and_overlapping_edits_rejected(self):
        edit=candidates(RAW)[0]
        stale=dict(edit,start=edit['start']+1)
        text,count,rejected=apply_edits(RAW,[edit,edit,stale])
        self.assertEqual(count,1);self.assertEqual(rejected,2)
        self.assertIn('Hipertansiyon',text)


class RecordPolicyTests(unittest.TestCase):
    def test_production_never_exports_known_raw_extensions(self):
        data={**INITIAL_DATA,'custom':'preserved','_test_data':{'raw_transcript':'SECRET_RAW'},
              '_note_draft':{'transcript':'SECRET_RAW','dictation_applied':'SECRET_RAW'}}
        snapshot={'body':'Onaylı metin','last_approved_text':'Tarih\nOnaylı metin',
                  'approved_at':'2026-10-21T12:00:00+03:00','sources_current':True,
                  'transcript':'SECRET_RAW','dictation_applied':'SECRET_RAW'}
        record=prepare_record(data,snapshot,raw_transcript='SECRET_RAW')
        self.assertNotIn('SECRET_RAW',json.dumps(record))
        self.assertEqual(record['custom'],'preserved')
        self.assertIn('SECRET_RAW',json.dumps(data)) # original file/data not deleted

    def test_only_test_mode_can_save_raw_or_unapproved_draft(self):
        draft={'body':'Taslak','last_approved_text':None,'transcript':'TEST_RAW'}
        with self.assertRaises(ValueError):prepare_record(INITIAL_DATA,draft)
        record=prepare_record(INITIAL_DATA,draft,test_mode=True,raw_transcript='TEST_RAW')
        self.assertEqual(record['_test_data']['raw_transcript'],'TEST_RAW')

    def test_old_raw_is_not_restored_in_production(self):
        data={**INITIAL_DATA,'_note_draft':{'body':'Son metin','transcript':'TEST_RAW'},'_test_data':{'raw_transcript':'TEST_RAW'}}
        values,note=without_legacy_raw(data)
        self.assertNotIn('TEST_RAW',json.dumps([values,note]))
        self.assertIn('TEST_RAW',json.dumps(data))


class AudioStopTests(unittest.TestCase):
    def test_silence_does_not_end_recording(self):
        sample=Mock()
        sd=Mock();stream=sd.InputStream.return_value
        def opened():
            sd.InputStream.call_args.kwargs['callback'](sample,1600,None,None)
        stream.__enter__=Mock(side_effect=opened);stream.__exit__=Mock(return_value=False)
        np=Mock();np.concatenate.return_value.reshape.return_value='synthetic_audio'
        stop=Mock();stop.wait.side_effect=[False,False,False,True]
        with patch.dict(sys.modules,{'sounddevice':sd,'numpy':np}):
            audio,overflow,limit=record_audio(stop,lambda:None)
        self.assertEqual(audio,'synthetic_audio')
        self.assertEqual(stop.wait.call_count,4)
        self.assertFalse(limit)

    def test_safety_duration_limit_is_not_silence_detection(self):
        sample=Mock();sd=Mock();stream=sd.InputStream.return_value
        stream.__enter__=Mock(side_effect=lambda:sd.InputStream.call_args.kwargs['callback'](sample,1600,None,None))
        stream.__exit__=Mock(return_value=False)
        stop=Mock();stop.wait.return_value=False
        with patch.dict(sys.modules,{'sounddevice':sd,'numpy':Mock()}):
            _,_,limit=record_audio(stop,lambda:None,max_seconds=0)
        self.assertTrue(limit)
        self.assertEqual(stop.wait.call_count,1)


class ThreeClickTests(unittest.TestCase):
    def setUp(self):
        ui_tests.UITests.setUp(self)
        self.clip=FakeClipboard();self.app.clipboard=self.clip
        self.app.speech_engine=Mock()
        self.app.speech_engine.transcribe.return_value=RAW
        self.app.engine=Mock()
        self.started=threading.Event()

    def tearDown(self):ui_tests.UITests.tearDown(self)
    def pump(self):ui_tests.UITests.pump(self)

    def wait_started(self):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            self.root.update()
            if str(self.app.note_panel.record_button['state'])=='normal' and self.started.is_set():return
            time.sleep(.01)
        self.fail('Recording did not become ready')

    def recorder(self,stop,on_started):
        self.started.set();on_started()
        if not stop.wait(3):raise RuntimeError('Test did not stop recording')
        return object(),False,False

    def start_and_stop(self):
        self.app.note_panel.record_button.invoke() # click 1
        self.wait_started()
        self.assertFalse(self.app._recording_stop.is_set())
        self.assertEqual(str(self.app.note_panel.approve_button['state']),'disabled')
        self.app.note_panel.record_button.invoke() # click 2
        self.pump()

    def test_three_clicks_produce_corrected_dated_clipboard_and_no_raw_record(self):
        with patch('ui.main_window.record_audio',side_effect=self.recorder):
            self.start_and_stop()
        self.assertIn('Hipertansiyon',self.app.note_panel.body())
        self.assertEqual(self.app.tabs.select(),str(self.app.output_tab))
        self.assertEqual(str(self.app.note_panel.approve_button['state']),'normal')
        self.app.note_panel.approve_button.invoke() # click 3; no prepare/accept/copy click
        self.root.update()
        self.assertIn('Hipertansiyon',self.clip.value)
        self.assertIn('amlodipin 2,5 mg',self.clip.value)
        self.assertIsNotNone(self.app.note_panel.approved)
        self.assertEqual(self.app.dictation_text.get('1.0','end-1c'),'')
        self.assertEqual(self.app._test_raw_transcript,'')
        self.assertEqual(self.app._dictation_applied,'')
        self.assertIsNone(self.app._speech_context)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'approved.json'
            with patch('ui.main_window.filedialog.asksaveasfilename',return_value=str(path)):self.app._save_json()
            record=json.loads(path.read_text(encoding='utf-8'))
            self.assertNotIn('Hiper tansiyon',json.dumps(record,ensure_ascii=False))
            self.assertNotIn('transcript',record['_note_draft'])
            self.assertNotIn('_test_data',record)
        self.assertTrue(self.app.note_panel.recopy())

    def test_test_mode_can_preserve_synthetic_raw(self):
        self.app.settings.test_mode=True
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.app.note_panel.approve_button.invoke();self.root.update()
        self.assertEqual(self.app._test_raw_transcript,RAW)
        self.assertIn('transcript',self.app.note_panel.snapshot())

    def test_model_enabled_uses_same_backend_automatically(self):
        self.app.settings.model_path='synthetic.gguf'
        self.app.engine.generate_json.return_value={'edits':candidates(RAW)}
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.app.engine.generate_json.assert_called_once()
        self.assertIn('Hipertansiyon',self.app.note_panel.body())
        self.assertIn('Yerel AI',self.app.note_panel.state.get())

    def test_edit_during_processing_is_not_overwritten(self):
        with patch('ui.main_window.record_audio',side_effect=self.recorder):
            self.app.note_panel.record_button.invoke();self.wait_started()
            self.app.draft_text.insert('1.0','Hekimin korunacak düzenlemesi');self.root.update()
            self.app.note_panel.record_button.invoke();self.pump()
        self.assertEqual(self.app.note_panel.body(),'Hekimin korunacak düzenlemesi')
        self.assertIn('Hipertansiyon',self.app.dictation_text.get('1.0','end-1c'))
        self.assertIsNone(self.app.note_panel.approved)
        self.assertEqual(self.clip.value,'')

    def test_recording_error_never_enables_false_completion(self):
        with patch('ui.main_window.record_audio',side_effect=RuntimeError('synthetic microphone error')), patch('ui.main_window.messagebox.showerror'):
            self.app.note_panel.record_button.invoke();self.pump()
        self.assertEqual(str(self.app.note_panel.approve_button['state']),'disabled')
        self.assertEqual(self.clip.value,'')
        self.assertFalse(self.app._processing_dictation)

    def test_correction_model_error_still_allows_manual_review_in_same_flow(self):
        self.app.settings.model_path='missing.gguf'
        self.app.engine.generate_json.side_effect=ValueError('synthetic unavailable model')
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.assertIn('Hipertansiyon',self.app.note_panel.body())
        self.assertIn('yalnızca güvenli sözlük',self.app.note_panel.state.get())
        self.app.note_panel.approve_button.invoke()
        self.assertTrue(self.clip.value)

    def test_edit_while_save_dialog_open_cannot_export_unapproved_text(self):
        with tempfile.TemporaryDirectory() as folder:
            for operation in [self.app._save_json,self.app._save_output]:
                self.app.note_panel._set_body('Onaylı sentetik not')
                self.assertTrue(self.app.note_panel.complete())
                path=Path(folder)/('note.json' if operation==self.app._save_json else 'note.txt')
                def dialog(**_kwargs):
                    self.app.draft_text.insert('end',' onaysız değişiklik')
                    return str(path)
                with patch('ui.main_window.filedialog.asksaveasfilename',side_effect=dialog):operation()
                self.assertFalse(path.exists())
