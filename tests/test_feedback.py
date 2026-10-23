"""Real Tk lifecycle/onboarding checks with blocked synthetic workers, never a mic."""
import gc
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from ui.main_window import AnamnezApp
from ui.onboarding import Onboarding,STEPS
from speech.model_download import ModelProgress
from settings import Settings

class FeedbackTests(unittest.TestCase):
    def setUp(self):
        try:self.root=tk.Tk()
        except tk.TclError as error:self.skipTest(str(error))
        with patch('ui.main_window.load_settings',return_value=Settings()):self.app=AnamnezApp(self.root)
        self.root.update()
        self.temp=tempfile.TemporaryDirectory()
        self.tour=Onboarding(self.app,Path(self.temp.name)/'ui.json')
        self.gate=threading.Event()

    def tearDown(self):
        self.gate.set();self.app.bridge.close();self.app.activity.close();self.root.destroy()
        self.temp.cleanup();del self.app;gc.collect()

    def pump(self):
        until=time.monotonic()+3
        while self.app.bridge.busy and time.monotonic()<until:self.root.update();time.sleep(.01)
        self.root.update();self.assertFalse(self.app.bridge.busy)

    def test_running_phase_elapsed_and_completion(self):
        self.app.bridge.start(lambda:self.gate.wait(2),lambda _:self.app.status.set('Taslak hazır.'),lambda _:None,label='Sentetik işlem sürüyor')
        self.root.update()
        self.assertTrue(self.app.activity.busy)
        self.assertEqual(str(self.app.activity.bar['mode']),'indeterminate')
        self.assertTrue(self.app.activity.bar.winfo_ismapped())
        self.assertIn('00:',self.app.activity.elapsed.get())
        self.assertEqual(str(self.app.clinical.action_buttons[0]['state']),'disabled')
        self.assertFalse(self.app.bridge.start(lambda:None,lambda _:None,lambda _:None))
        self.app.status.set('Kayıt sürüyor. Sentetik örnek')
        self.assertEqual(self.app.activity.heading.get(),'KAYIT AÇIK')
        self.app.status.set('Devam eden işlemin bitmesini bekleyin.')
        self.assertEqual(self.app.activity.heading.get(),'KAYIT AÇIK')
        self.app.status.set('Türkçe transkripsiyon yapılıyor...')
        self.assertEqual(self.app.activity.heading.get(),'İŞLENİYOR')
        self.gate.set();self.pump()
        self.assertFalse(self.app.activity.busy)
        self.assertEqual(self.app.activity.heading.get(),'TAMAMLANDI')
        self.assertFalse(self.app.activity.bar.winfo_manager())
        self.assertEqual(str(self.app.clinical.action_buttons[0]['state']),'normal')
        self.app.status.set('Anamnez onaylandı ve panoya kopyalandı.')
        self.assertEqual(self.app.activity.elapsed.get(),'')

    def test_failure_and_review_do_not_claim_completion(self):
        def fail():raise RuntimeError('synthetic')
        self.app.bridge.start(fail,lambda _:None,lambda _:self.app.status.set('İşlem tamamlanamadı.'))
        self.pump();self.assertEqual(self.app.activity.heading.get(),'TAMAMLANAMADI')
        self.app.bridge.start(lambda:None,lambda _:setattr(self.app,'_review_pending',True),lambda _:None)
        self.pump();self.assertEqual(self.app.activity.heading.get(),'İNCELEME GEREKLİ')

    def test_real_download_percent_returns_to_preparation(self):
        self.app.activity.begin('Model indiriliyor')
        self.app._model_progress(ModelProgress('downloading','small',37,37,100))
        self.assertEqual(float(self.app.activity.bar['value']),37)
        self.assertEqual(str(self.app.activity.bar['mode']),'determinate')
        self.app._model_progress(ModelProgress('loading','small'))
        self.assertEqual(str(self.app.activity.bar['mode']),'indeterminate')

    def test_first_run_skip_remember_and_reopen(self):
        self.assertFalse(self.tour.seen());self.tour.first_run();self.root.update()
        window=self.tour.window;self.tour.open();self.assertIs(self.tour.window,window)
        self.tour.move(1);self.assertEqual(self.app.tabs.select(),str(self.app.settings_frame))
        self.tour.close();self.assertTrue(self.tour.seen())
        self.assertEqual(json.loads(self.tour.path.read_text()),{'intro_v1_seen':True})
        self.tour.first_run();self.assertIsNone(self.tour.window)
        self.tour.open();self.assertIsNotNone(self.tour.window);self.tour.close()
        self.assertFalse(self.app.bridge.busy);self.assertIsNone(self.app._recording_stop)

    def test_skip_without_remember_and_complete(self):
        self.tour.open();self.tour.remember.set(False);self.tour.close()
        self.assertFalse(self.tour.seen());self.tour.first_run()
        for _ in STEPS:self.tour.move(1)
        self.assertIsNone(self.tour.window);self.assertTrue(self.tour.seen())

    def test_tour_preserves_draft_and_cannot_interrupt_active_job(self):
        self.app.note_panel._set_body('Sentetik taslak')
        self.app.bridge.busy=True;self.tour.open();self.assertIsNone(self.tour.window)
        self.app.bridge.busy=False;self.tour.open()
        for _ in STEPS:self.tour.move(1)
        self.assertEqual(self.app.note_panel.body(),'Sentetik taslak')
        self.assertIsNone(self.app.note_panel.approved)

    def test_update_progress_is_not_verified_until_downloaded(self):
        panel=self.app.updates;panel.busy=True
        panel._download_progress(25,100)
        self.assertEqual(float(panel.progress['value']),25)
        panel._download_progress(100,100)
        self.assertEqual(float(panel.progress['value']),99)
        self.assertIn('doğrulanıyor',panel.progress_text.get())
        panel.downloaded(Path('synthetic.exe'))
        self.assertIn('%100',panel.progress_text.get())

    def test_model_setup_ready_and_settings_failure_are_distinct(self):
        with patch('ai.model_setup.install_model',return_value='synthetic.gguf'),patch('ui.main_window.save_settings'):
            self.app._install_clinical_model();self.pump()
        self.assertIn('hazır',self.app.model_progress.text.get())
        self.assertNotIn('hazırlanıyor',self.app.model_progress.text.get())
        self.assertEqual(self.app.activity.heading.get(),'TAMAMLANDI')
        with patch('ai.model_setup.install_model',return_value='synthetic.gguf'),patch('ui.main_window.save_settings',side_effect=OSError()):
            self.app._install_clinical_model();self.pump()
        self.assertEqual(self.app.activity.heading.get(),'TAMAMLANAMADI')
        self.assertFalse(self.app.activity.bar.winfo_manager())

if __name__=='__main__':unittest.main()
