import unittest
import tempfile
from pathlib import Path
from clinical_notes import parse_dictation, format_note
from config import INITIAL_DATA
from storage.patient_storage import load_patient, save_patient

class CompatibilityTests(unittest.TestCase):
    def test_labels_preserve_other_fields(self):
        data=dict(INITIAL_DATA)
        parse_dictation('Tansiyon: 120/80; HbA1c: 7,2',data)
        self.assertEqual(data['tansiyon'],'120/80')
        self.assertEqual(data['hba1c'],'7,2')
        self.assertEqual(data['bb'],INITIAL_DATA['bb'])

    def test_free_dictation_appends(self):
        data=dict(INITIAL_DATA)
        parse_dictation('Üç aydır halsizlik var.',data)
        self.assertTrue(data['sikayet'].startswith(INITIAL_DATA['sikayet']))
        self.assertIn('Üç aydır',data['sikayet'])

    def test_v1_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'patient.json')
            data={**INITIAL_DATA,'extension':{'preserved':True}}
            save_patient(path,data)
            self.assertEqual(load_patient(path),data)
            self.assertIn('FİZİK MUAYENE',format_note(data))

    def test_invalid_file_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'patient.json';path.write_text('{}')
            with self.assertRaises(ValueError):load_patient(str(path))
            self.assertEqual(path.read_text(),'{}')
