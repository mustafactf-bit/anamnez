"""Real Tk checks for review visibility, keyboard access and local help."""
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from ui.main_window import AnamnezApp
from settings import Settings

class DesignTests(unittest.TestCase):
    def setUp(self):
        try:self.root=tk.Tk()
        except tk.TclError as error:self.skipTest(str(error))
        with patch('ui.main_window.load_settings',return_value=Settings()):
            self.app=AnamnezApp(self.root)
        self.root.geometry('980x680');self.root.update()

    def tearDown(self):
        self.app.bridge.close();self.root.destroy()

    def test_local_guide_and_keyboard(self):
        with patch('ui.main_window.webbrowser.open',return_value=True) as opened:
            self.app._open_guide()
            self.assertTrue(opened.call_args.args[0].endswith('assets/kullanim-kilavuzu.html'))
        self.assertTrue((Path(__file__).parents[1]/'assets/kullanim-kilavuzu.html').is_file())
        self.assertTrue(self.root.bind('<F1>'))
        self.assertTrue(self.root.bind('<F6>'))
        self.app.tabs.select(self.app.form_tab)
        self.root.event_generate('<F6>');self.root.update()
        # The same binding is registered on Text widgets so class bindings cannot swallow it.
        self.assertTrue(self.app.note_panel.editor.bind('<Control-n>'))
        self.assertTrue(self.app.note_panel.editor.bind('<Tab>'))

    def test_preview_toggle_preserves_editor_and_does_not_approve(self):
        panel=self.app.note_panel
        panel._set_body('Sentetik örnek')
        self.assertFalse(panel.preview_frame.winfo_manager())
        panel.toggle_preview();self.root.update()
        self.assertTrue(panel.preview_frame.winfo_manager())
        panel.toggle_preview()
        self.assertEqual(panel.body(),'Sentetik örnek')
        self.assertIsNone(panel.approved)

    def test_actions_fit_small_window(self):
        panel=self.app.note_panel
        for button in (panel.record_button,panel.approve_button,panel.preview_toggle):
            self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
            self.assertGreater(button.winfo_height(),25)
        panel.set_selection_details(('Belirsiz ifade',),())
        self.app._review_pending=True;panel.update_actions();self.root.update()
        self.assertEqual(str(panel.approve_button['state']),'disabled')
        self.assertTrue(panel.review_text.winfo_ismapped())
