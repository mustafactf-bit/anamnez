"""Hidden real Tk tests; no microphone, downloads or external requests."""
import threading
import gc
import time
import unittest
from unittest.mock import Mock, patch
import tkinter as tk
from ui.main_window import AnamnezApp
from settings import Settings
from tests.test_pipeline import CASE

class UITests(unittest.TestCase):
    def setUp(self):
        try:self.root=tk.Tk()
        except tk.TclError as error:self.skipTest(str(error))
        self.root.withdraw()
        with patch('ui.main_window.load_settings',return_value=Settings()):
            self.app=AnamnezApp(self.root)
        self.root.update()

    def tearDown(self):
        if hasattr(self,'app') and not self.app.bridge.closed:self.app._close()
        if hasattr(self,'app'):del self.app
        if hasattr(self,'root'):del self.root
        gc.collect()

    def pump(self):
        deadline=time.monotonic()+3
        while self.app.bridge.busy and time.monotonic()<deadline:
            self.root.update();time.sleep(.01)
        self.root.update()
        self.assertFalse(self.app.bridge.busy)

    def test_tabs_and_manual_fields(self):
        self.assertEqual(len(self.app.tabs.tabs()),7)
        self.app.entries['tansiyon'].delete(0,'end');self.app.entries['tansiyon'].insert(0,'120/80')
        self.app._refresh_output()
        self.assertIn('120/80',self.app.output_text.get('1.0','end'))

    def test_local_extraction_ui(self):
        self.app.dictation_text.insert('1.0','Sentetik vaka: hipertansiyon ve halsizlik.')
        self.root.update()
        engine=Mock()
        q={'question':'Hipertansiyon nasıl araştırılabilir?', 'concepts':['hypertension'],'pico':None}
        engine.generate_json.side_effect=[CASE,{'questions':[q,q]}]
        self.app.engine=engine
        self.app.clinical.extract();self.pump()
        self.assertEqual(len(self.app.clinical.questions),2)
        self.assertEqual(self.app.clinical.structured,CASE)
        previous=self.app.values['bb']
        self.app.clinical.apply_reviewed()
        self.assertEqual(self.app.values['ilaclar'],'amlodipin')
        self.assertEqual(self.app.values['bb'],previous)
        self.assertEqual(self.app.values['_v2']['structured_anamnesis'],CASE)
        self.app.dictation_text.insert('end',' Yeni bilgi.');self.root.update()
        self.assertEqual(self.app.clinical.questions,[])

    def test_empty_pubmed_in_ui(self):
        self.app.clinical.questions=[{}]
        self.app.clinical.question.set('Literatür sorusu')
        self.app.clinical.concepts.set('hypertension')
        self.app.pubmed=Mock();self.app.pubmed.search.return_value=[]
        self.app.clinical.search();self.pump()
        self.assertIn('Eşleşen yayın bulunamadı',self.app.clinical.output.get('1.0','end'))

    def test_callbacks_main_thread_and_close(self):
        threads=[]
        self.app.bridge.start(lambda:threading.get_ident(),lambda worker:threads.append((worker,threading.get_ident())),lambda _:None)
        self.pump()
        self.assertNotEqual(*threads[0])
        event=threading.Event()
        self.app.bridge.start(lambda:event.wait(1),lambda _:self.fail('Closed callback'),lambda _:None)
        self.app._close();event.set()

    def test_single_worker(self):
        event=threading.Event()
        self.assertTrue(self.app.bridge.start(lambda:event.wait(1),lambda _:None,lambda _:None))
        self.assertFalse(self.app.bridge.start(lambda:None,lambda _:None,lambda _:None))
        event.set();self.pump()

    def test_network_failure_returns_to_ui(self):
        from literature.pubmed_client import PubMedError
        self.app.clinical.questions=[{}]
        self.app.clinical.question.set('Literatür sorusu')
        self.app.clinical.concepts.set('hypertension')
        self.app.pubmed=Mock();self.app.pubmed.search.side_effect=PubMedError('PubMed erişilemedi.')
        with patch('ui.clinical_assistant_tab.messagebox.showerror') as display:
            self.app.clinical.search();self.pump()
            display.assert_called_once()
        self.assertIn('tamamlanamadı',self.app.status.get())
