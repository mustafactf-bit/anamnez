"""Source evidence, unrelated speech and automatic field placement."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from ai.encounter_extractor import extract_encounter,validate_selection,split_units
from ai.llm_engine import LLMError
from speech.dictation_pipeline import ProcessedDictation
from ai.dictation_corrector import CorrectionResult
import tests.test_alpha11 as legacy
from tests.test_note_workflow import FakeClipboard

TEXT='Hasta: Üç gündür baş ağrım var. Öğrenci: Yarınki ders kaçta? Hasta: Ateşim yok. Hasta: Metformin 500 mg günde iki kez alıyorum. Hekim: Tansiyon 120/80 mmHg.'
def row(i,field=None,subject='patient',action='include',quote=None):
    return {'id':i,'field':field,'subject':subject,'action':action,'quote':split_units(TEXT)[i] if quote is None else quote}
ROWS=[row(0,'sikayet'),row(1,subject='other',action='exclude',quote=''),row(2,'ates'),row(3,'ilaclar'),row(4,'tansiyon')]

class EvidenceTests(unittest.TestCase):
    def test_dialogue_selects_original_answers_without_rewriting_questions(self):
        text='Geceleri su içmek için kalkıyor musunuz? İki haftadır gece su içiyorum. İştahınız nasıl? Çok yiyorum ama kilo kaybediyorum. Sürekli yorgunum.'
        engine=Mock()
        rows=[
            {'id':i,'action':'review' if i in (0,2) else 'include',
             'field':None if i in (0,2) else 'sikayet','subject':'patient'} for i in range(5)]
        engine.generate_json.side_effect=[{'items':rows[:4]},{'items':rows[4:]}]
        result=extract_encounter(engine,text)
        self.assertEqual(result.fields['sikayet'],'İki haftadır gece su içiyorum.\nÇok yiyorum ama kilo kaybediyorum.\nSürekli yorgunum.')
        self.assertNotIn('?',result.fields['sikayet'])
        self.assertNotIn('ontani',result.fields)
        self.assertEqual(len(result.review),2)

    def test_compact_contract_rejects_generated_text_and_invalid_ids(self):
        for item in [dict(id=0,action='include',field='sikayet',subject='patient',quote='uydurma'),
                     dict(id=True,action='include',field='sikayet',subject='patient'),
                     dict(id=7,action='include',field='sikayet',subject='patient')]:
            engine=Mock();engine.generate_json.return_value={'items':[item]}
            with self.assertRaises(LLMError):extract_encounter(engine,'Başım ağrıyor.')

    def test_later_batch_failure_does_not_return_partial_success(self):
        engine=Mock()
        engine.generate_json.side_effect=[{'items':[
            {'id':i,'action':'include','field':'sikayet','subject':'patient'} for i in range(4)]},LLMError('test')]
        with self.assertRaises(LLMError):extract_encounter(engine,' '.join(f'{i} gündür başım ağrıyor.' for i in range(5)))
        self.assertEqual(engine.generate_json.call_count,2)

    def test_filters_student_and_preserves_medication_negation_numbers(self):
        engine=Mock();engine.generate_json.side_effect=[{'items':[{k:v for k,v in r.items() if k!='quote'} for r in ROWS[i:i+4]]} for i in range(0,len(ROWS),4)]
        result=extract_encounter(engine,TEXT)
        self.assertNotIn('ders',json.dumps(result.fields,ensure_ascii=False))
        self.assertIn('Ateşim yok',result.fields['ates'])
        self.assertIn('500 mg günde iki kez',result.fields['ilaclar'])
        self.assertIn('120/80',result.fields['tansiyon'])
        self.assertEqual(len(result.excluded),1);self.assertFalse(result.review)

    def test_invention_wrong_field_and_incomplete_coverage_rejected(self):
        for rows in [ROWS[:-1],[dict(ROWS[0],quote='Baş ağrısı yok.')]+ROWS[1:],
                     [dict(ROWS[0],field='diagnosis')]+ROWS[1:],[ROWS[0],ROWS[0]]+ROWS[2:]]:
            with self.assertRaises(LLMError):validate_selection(split_units(TEXT),rows,list(range(5)))

    def test_negation_dose_and_frequency_cannot_be_trimmed(self):
        for source,quote in [('Ateşim yok.','Ateşim'),('Metformin 500 mg alıyorum.','Metformin'),
                             ('Bazen başım ağrıyor.','başım ağrıyor.')]:
            fields,waiting,_=validate_selection([source],[{'id':0,'action':'include','subject':'patient','field':'sikayet','quote':quote}],[0])
            self.assertFalse(fields);self.assertEqual(waiting,[source])

    def test_third_party_clinical_talk_is_not_patient_history(self):
        source='Öğrenci: Benim annemde diyabet var.'
        fields,waiting,_=validate_selection([source],[{'id':0,'action':'include','subject':'family','field':'soygecmis_anne','quote':source}],[0])
        self.assertFalse(fields);self.assertTrue(waiting)

    def test_unmarked_dropped_clinical_information_requires_review(self):
        source='Nefes darlığım ve göğüs ağrım var.'
        fields,waiting,excluded=validate_selection([source],[{'id':0,'action':'exclude','subject':'other','field':None,'quote':''}],[0])
        self.assertFalse(fields);self.assertEqual(waiting,[source]);self.assertFalse(excluded)

    def test_question_is_not_an_affirmed_finding(self):
        source='Göğüs ağrısı var mı?'
        fields,waiting,_=validate_selection([source],[{'id':0,'action':'include','subject':'patient','field':'sikayet','quote':source}],[0])
        self.assertFalse(fields);self.assertTrue(waiting)

    def test_bare_answer_without_its_question_is_not_a_standalone_fact(self):
        for source in ['Evet.','Hasta: Hayır.','Yok.']:
            fields,waiting,_=validate_selection([source],[{'id':0,'action':'include','subject':'patient','field':'ates','quote':source}],[0])
            self.assertFalse(fields);self.assertEqual(waiting,[source])

    def test_nonclinical_logistics_number_does_not_become_patient_fact(self):
        source='Sınav yarın saat 10 olacak.'
        fields,waiting,excluded=validate_selection([source],[{'id':0,'action':'exclude','subject':'other','field':None,'quote':''}],[0])
        self.assertFalse(fields);self.assertFalse(waiting);self.assertEqual(excluded,[source])

class StructuredFlowTests(unittest.TestCase):
    setUp=legacy.ThreeClickTests.setUp
    tearDown=legacy.ThreeClickTests.tearDown
    pump=legacy.ThreeClickTests.pump
    wait_started=legacy.ThreeClickTests.wait_started
    recorder=legacy.ThreeClickTests.recorder
    start_and_stop=legacy.ThreeClickTests.start_and_stop

    def enable(self):
        self.app.settings.structure_dictation=True;self.app.settings.model_path=__file__
        self.app.speech_engine.transcribe.return_value=TEXT
        self.app.engine.generate_json.side_effect=[{'items':[{k:v for k,v in r.items() if k!='quote'} for r in ROWS[i:i+4]]} for i in range(0,len(ROWS),4)]

    def test_three_clicks_place_fields_and_never_copy_student_chat(self):
        self.enable()
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.assertIn('120/80',self.app.entries['tansiyon'].get())
        self.assertIn('500 mg',self.app.entries['ilaclar'].get())
        self.assertNotIn('ders',self.app.note_panel.body())
        self.app.note_panel.approve_button.invoke();self.root.update()
        self.assertIn('120/80',self.clip.value);self.assertNotIn('ders',self.clip.value)
        self.assertFalse(self.app.note_panel.selection_details)
        self.assertEqual(self.app.dictation_text.get('1.0','end-1c'),'')

    def test_invalid_ai_never_falls_back_to_full_conversation(self):
        self.enable();self.app.engine.generate_json.side_effect=None;self.app.engine.generate_json.return_value={'items':[]}
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.assertTrue(self.app._review_pending)
        self.assertEqual(self.app.note_panel.body(),'')
        self.assertNotIn('yerleştirdi',self.app.note_panel.state.get())
        self.assertIn('tamamlanamadı',self.app.note_panel.state.get())
        self.assertFalse(self.app.note_panel.complete())
        self.assertIn('ders',self.app.dictation_text.get('1.0','end-1c'))
        self.assertNotIn('transkripsiyon sürüyor',self.app.note_panel.state.get())

    def test_uncertain_information_blocks_approval_until_explicit_review(self):
        self.enable();rows=[dict(r) for r in ROWS];rows[0]['action']='review'
        self.app.engine.generate_json.side_effect=[{'items':[{k:v for k,v in r.items() if k!='quote'} for r in rows[i:i+4]]} for i in range(0,len(rows),4)]
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.assertTrue(self.app._review_pending);self.assertFalse(self.app.note_panel.complete())
        self.app.note_panel.resolve_review();self.assertTrue(self.app.note_panel.complete())

    def test_conflicting_manual_value_is_preserved_and_flagged(self):
        self.enable();self.app.entry_variables['tansiyon'].set('130/85');self.root.update()
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.assertEqual(self.app.entries['tansiyon'].get(),'130/85')
        self.assertTrue(self.app._review_pending)
        self.assertIn('120/80',self.app.note_panel.review_text.get('1.0','end-1c'))

    def test_logo_and_window_icon_are_real_assets(self):
        self.assertEqual(self.app.logo.width(),96)
        self.assertEqual(self.app.window_icon.width(),64)

    def test_first_setup_decline_does_not_start_recording(self):
        self.app.settings.structure_dictation=True;self.app.settings.model_path=''
        with tempfile.TemporaryDirectory() as directory,patch('ai.model_setup.default_model_path',return_value=Path(directory)/'missing.gguf'),patch('ui.main_window.messagebox.askyesno',return_value=False):
            self.app._toggle_microphone_recording()
        self.assertIsNone(self.app._recording_stop)
        self.app.speech_engine.load.assert_not_called()

    def test_invalid_ai_preserves_old_draft_but_cannot_approve_it_as_new(self):
        self.enable();self.app.note_panel._set_body('Hekimin mevcut notu.')
        self.app.engine.generate_json.side_effect=None;self.app.engine.generate_json.return_value={'items':[]}
        with patch('ui.main_window.record_audio',side_effect=self.recorder):self.start_and_stop()
        self.assertEqual(self.app.note_panel.body(),'Hekimin mevcut notu.')
        self.assertTrue(self.app._review_pending);self.assertFalse(self.app.note_panel.complete())

    def test_manual_transcript_uses_same_ai_instead_of_copying_everything(self):
        self.enable();self.app.dictation_text.insert('1.0',TEXT);self.root.update()
        self.assertTrue(self.app.note_panel.prepare());self.pump()
        self.assertIn('120/80',self.app.note_panel.body())
        self.assertNotIn('ders',self.app.note_panel.body())
        self.assertEqual(self.app.dictation_text.get('1.0','end-1c'),TEXT)

    def test_failed_manual_extraction_can_retry_without_approving_failure(self):
        self.enable();self.app.dictation_text.insert('1.0',TEXT);self.root.update()
        self.app.engine.generate_json.side_effect=None
        self.app.engine.generate_json.return_value={'items':[]}
        self.assertTrue(self.app.note_panel.prepare());self.pump()
        self.assertTrue(self.app._review_pending);self.assertFalse(self.app.note_panel.body())
        self.enable()
        self.assertTrue(self.app.note_panel.prepare());self.pump()
        self.assertFalse(self.app._review_pending)
        self.assertIn('120/80',self.app.note_panel.body())
        self.assertIsNone(self.app.note_panel.approved)
