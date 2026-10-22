"""Synthetic real-GGUF acceptance check; never reads recordings/patient files."""
import time
from ai.model_setup import install_model
from ai.llm_engine import GGUFEngine
from ai.encounter_extractor import extract_encounter
from settings import Settings

def run():
    path=install_model();engine=GGUFEngine(Settings(model_path=path))
    started=time.monotonic()
    try:
        result=extract_encounter(engine,'Üç gündür baş ağrım var. Yarınki ders saat 10 mu? Ateşim yok. Metformin 500 mg günde iki kez alıyorum. Tansiyon 120/80 mmHg.')
        values='\n'.join(result.fields.values())
        assert 'ders' not in values and '500 mg' in result.fields.get('ilaclar','')
        assert '120/80' in result.fields.get('tansiyon','') and 'yok' in values
        assert not result.review
        return {'local_gguf':True,'structured_fields':True,'unrelated_excluded':True,
                'negation_dose_preserved':True,'seconds':round(time.monotonic()-started,2)}
    finally:engine.unload()
