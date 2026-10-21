"""Priority acceptance tests: complete, stamp, copy, append, change patient."""
import datetime as dt
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch
import unittest
from config import INITIAL_DATA
from note_workflow import build_note_body, approve_note
from storage.patient_storage import save_patient
import tests.test_ui as ui_tests
from ui.clipboard import ClipboardError, normalize_lines, create_clipboard


class FakeClipboard:
    """Controlled clipboard failure injection without touching personal contents."""
    def __init__(self):self.value='';self.fail=False
    def read(self):
        if self.fail:raise ClipboardError('busy')
        return self.value
    def write(self,value):
        if self.fail:raise ClipboardError('busy')
        self.value=value


class NoteFormattingTests(unittest.TestCase):
    def test_new_encounter_has_no_presumed_facts(self):
        self.assertTrue(all(value=='' for value in INITIAL_DATA.values()))
        self.assertEqual(build_note_body(INITIAL_DATA),'')
        with self.assertRaises(ValueError):approve_note('  ')

    def test_only_entered_content(self):
        body=build_note_body({**INITIAL_DATA,'sikayet':'Öksürük yok. Halsizlik var.', 'tansiyon':'120/80','bb':'...'})
        self.assertIn('Öksürük yok.',body)
        self.assertIn('120/80',body)
        self.assertNotIn('Baş-boyun',body)
        self.assertNotIn('HASTA BİLGİLENDİRİLDİ',body)
        self.assertNotIn('POLİKLİNİK KONTROLÜ',body)

    def test_timestamp_and_append_boundary(self):
        note=approve_note('Şikâyet: Üç gündür öksürük.',dt.datetime(2026,10,21,16,30))
        self.assertTrue(note.text.startswith('\n\n────────── 21.10.2026 16:30'))
        self.assertEqual(note.text.count('21.10.2026'),1)
        previous='Eski hekim kaydı — korunacak.'
        self.assertTrue((previous+note.text).startswith(previous+'\n\n'))

    def test_reviewed_clinical_details_are_not_lost(self):
        from tests.test_pipeline import CASE
        body=build_note_body({**INITIAL_DATA,'_v2':{'structured_anamnesis':CASE}})
        for part in ['Yaş: 58','Yakınma süresi: 3 ay','potasyum: 2.9']:
            self.assertIn(part,body)


class NoteUITests(unittest.TestCase):
    # Reuse setup/pump without discovering the existing regression tests twice.
    def setUp(self):
        ui_tests.UITests.setUp(self)
        self.clip=FakeClipboard();self.app.clipboard=self.clip

    def tearDown(self):
        ui_tests.UITests.tearDown(self)

    def pump(self):
        ui_tests.UITests.pump(self)

    def draft(self,text='Şikâyet: Halsizlik var, ateş yok. İlaç dozu 2,5 mg.'):
        self.app.draft_text.insert('1.0',text)
        self.root.update()
        return text

    def test_approval_matches_preview_and_repeat_keeps_timestamp(self):
        body=self.draft()
        self.assertEqual(self.clip.value,'')
        self.assertTrue(self.app._copy_output())
        self.root.update()
        panel=self.app.note_panel;original=self.clip.value
        self.assertIsNotNone(panel.approved)
        self.assertEqual(original,self.app.output_text.get('1.0','end-1c'))
        self.assertIn(body,original)
        self.assertTrue(panel.recopy());self.assertEqual(self.clip.value,original)
        self.assertTrue(panel.complete());self.assertEqual(self.clip.value,original)

    def test_empty_cannot_complete(self):
        self.assertFalse(self.app._copy_output())
        self.assertEqual(self.clip.value,'')
        self.assertNotIn('Panoya kopyalandı',self.app.note_panel.state.get())

    def test_edit_revokes_approval_and_clears_owned_clipboard(self):
        self.draft();self.app._copy_output()
        self.app.draft_text.insert('end',' Yeni bilgi.');self.root.update()
        self.assertIsNone(self.app.note_panel.approved)
        self.assertEqual(self.clip.value,'')
        self.assertFalse(self.app.note_panel.recopy())
        self.assertTrue(self.app.note_panel.complete())
        self.assertIn('Yeni bilgi.',self.clip.value)

    def test_source_edit_blocks_stale_approval(self):
        self.draft();self.app._copy_output()
        self.app.entry_variables['tansiyon'].set('120/80')
        self.assertIsNone(self.app.note_panel.approved)
        self.assertFalse(self.app.note_panel.complete())
        self.assertEqual(self.clip.value,'')
        with patch('ui.note_panel.messagebox.askyesno',return_value=True):self.app.note_panel.prepare()
        self.assertTrue(self.app.note_panel.complete())
        self.assertIn('120/80',self.clip.value)

    def test_failed_copy_is_not_success_retry_same_note(self):
        self.draft();self.clip.fail=True
        self.assertFalse(self.app.note_panel.complete())
        self.assertIn('Kopyalanamadı',self.app.note_panel.state.get())
        approved=self.app.note_panel.approved.text
        self.clip.fail=False
        self.assertTrue(self.app.note_panel.recopy())
        self.assertEqual(self.clip.value,approved)

    def test_other_clipboard_content_survives_note_edit(self):
        self.draft();self.app._copy_output();self.clip.value='Başka uygulamadan kopyalanan metin'
        self.app.draft_text.insert('end',' Değişiklik.');self.root.update()
        self.assertEqual(self.clip.value,'Başka uygulamadan kopyalanan metin')

    def test_new_visit_resets_all_patient_state_and_clipboard(self):
        self.draft();self.app._copy_output()
        self.app.values['_v2']={'patient':'synthetic'}
        self.app.values['unknown_extension']='previous patient'
        with patch('ui.main_window.messagebox.askyesno',return_value=True):
            self.assertTrue(self.app._new_visit())
        self.root.update()
        self.assertEqual(self.app.values,INITIAL_DATA)
        self.assertEqual(self.app.note_panel.body(),'')
        self.assertEqual(self.app.dictation_text.get('1.0','end-1c'),'')
        self.assertEqual(self.clip.value,'')
        self.assertIsNone(self.app.note_panel.approved)

    def test_busy_clipboard_blocks_patient_switch(self):
        self.draft();self.app._copy_output();self.clip.fail=True
        with patch('ui.main_window.messagebox.askyesno',return_value=True),patch('ui.main_window.messagebox.showerror'):
            self.assertFalse(self.app._new_visit())
        self.assertTrue(self.app.note_panel.body())
        self.clip.fail=False

    def test_cancel_new_visit_keeps_note(self):
        text=self.draft();self.app._copy_output();clipboard=self.clip.value
        with patch('ui.main_window.messagebox.askyesno',return_value=False):
            self.assertFalse(self.app._new_visit())
        self.assertEqual(self.app.note_panel.body(),text)
        self.assertEqual(self.clip.value,clipboard)

    def test_old_json_load_does_not_autocopy(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'old.json'
            data={**INITIAL_DATA,'sikayet':'Önceki dosyadan bilgi','custom':'preserved'}
            save_patient(str(file),data)
            with patch('ui.main_window.filedialog.askopenfilename',return_value=str(file)):
                self.app._load_json()
            self.root.update()
            self.assertEqual(self.clip.value,'')
            self.assertEqual(self.app.values['custom'],'preserved')
            self.assertIn('Önceki dosyadan bilgi',self.app.note_panel.body())
            self.assertTrue(self.app.note_panel.complete())

    def test_saved_manual_draft_roundtrip_pending_review(self):
        text=self.draft();self.app._copy_output()
        with tempfile.TemporaryDirectory() as folder:
            file=str(Path(folder)/'draft.json')
            with patch('ui.main_window.filedialog.asksaveasfilename',return_value=file):self.app._save_json()
            self.app.draft_text.insert('end',' Not saved');self.root.update()
            with patch('ui.main_window.filedialog.askopenfilename',return_value=file),patch('ui.main_window.messagebox.askyesno',return_value=True):self.app._load_json()
            self.root.update()
            self.assertEqual(self.app.note_panel.body(),text)
            self.assertIsNone(self.app.note_panel.approved)
            self.assertEqual(self.clip.value,'')

    def test_pending_modified_event_cannot_revoke_fresh_approval(self):
        self.app.draft_text.insert('1.0','Anlık düzenleme')
        self.assertTrue(self.app.note_panel.complete())
        self.root.update()
        self.assertIsNotNone(self.app.note_panel.approved)
        self.assertTrue(self.clip.value)

    def test_literature_worker_does_not_block_manual_copy(self):
        event=threading.Event()
        self.app.bridge.start(lambda:event.wait(2),lambda _:None,lambda _:None)
        self.draft();self.assertTrue(self.app.note_panel.complete())
        event.set();self.pump()

    def test_unedited_dictation_does_not_duplicate(self):
        self.app.dictation_text.insert('1.0','Şikâyet: Halsizlik var.')
        self.root.update();self.app._apply_dictation()
        self.root.update()
        first=self.app.note_panel.body()
        self.app._apply_dictation();self.root.update()
        self.assertEqual(self.app.note_panel.body(),first)
        self.assertEqual(first.count('Halsizlik var'),1)

    def test_real_clipboard_append_to_existing_widget(self):
        import tkinter as tk
        real=create_clipboard(self.root)
        try:previous=real.read()
        except ClipboardError:self.skipTest('System clipboard is busy/unavailable')
        if previous is None:self.skipTest('Non-text clipboard left untouched')
        self.app.clipboard=real
        try:
            self.draft('Şikâyet: Üç gündür öksürük; ateş yok. Ölçüm: 2,9.')
            self.assertTrue(self.app.note_panel.complete())
            final=self.app.output_text.get('1.0','end-1c')
            self.assertEqual(normalize_lines(real.read()),normalize_lines(final))
            target=tk.Text(self.root)
            target.insert('1.0','Önceki anamnez kaydı.');target.mark_set('insert','end-1c')
            target.event_generate('<<Paste>>');self.root.update()
            self.assertEqual(normalize_lines(target.get('1.0','end-1c')),'Önceki anamnez kaydı.'+normalize_lines(final))
            target.destroy()
        finally:
            real.write(previous)
            self.app.clipboard=self.clip

    def test_new_visit_waits_for_speech_not_literature(self):
        self.app._recording_stop=threading.Event()
        self.assertFalse(self.app._new_visit())
        self.app._recording_stop=None

    def test_cannot_copy_incomplete_recording(self):
        self.draft()
        self.app._recording_stop=threading.Event()
        self.assertFalse(self.app.note_panel.complete())
        self.assertEqual(self.clip.value,'')
        self.app._recording_stop=None

    def test_transcript_change_requires_updated_draft(self):
        self.draft();self.app._copy_output()
        self.app.dictation_text.insert('1.0','Yeni dikte bilgisi')
        # Check even before the asynchronous Modified event has been processed.
        self.assertFalse(self.app.note_panel.complete())
        self.assertIsNone(self.app.note_panel.approved)
        self.assertEqual(self.clip.value,'')

    def test_manual_edits_survive_cancelled_regeneration(self):
        text=self.draft('Hekimin elle düzelttiği son metin')
        self.app.entry_variables['sikayet'].set('Alan içeriği')
        with patch('ui.note_panel.messagebox.askyesno',return_value=False):
            self.assertFalse(self.app.note_panel.prepare())
        self.assertEqual(self.app.note_panel.body(),text)

    def test_text_export_saves_manual_body_without_regeneration(self):
        text=self.draft()
        self.app._copy_output()
        expected=self.clip.value
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'note.txt'
            with patch('ui.main_window.filedialog.asksaveasfilename',return_value=str(file)):
                self.app._save_output()
            self.assertEqual(file.read_text(encoding='utf-8'),expected)
        self.assertEqual(self.app.note_panel.body(),text)

    def test_saved_stale_draft_is_not_silently_approved_on_load(self):
        self.draft();self.app.entry_variables['tansiyon'].set('110/70')
        with tempfile.TemporaryDirectory() as folder:
            file=str(Path(folder)/'stale.json')
            with patch('ui.main_window.filedialog.asksaveasfilename',return_value=file):self.app._save_json()
            with patch('ui.main_window.filedialog.askopenfilename',return_value=file),patch('ui.main_window.messagebox.askyesno',return_value=True):self.app._load_json()
            self.assertFalse(self.app.note_panel.complete())
            self.assertEqual(self.clip.value,'')

