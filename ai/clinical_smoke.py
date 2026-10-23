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
        assert 'baş ağrım' in result.fields.get('sikayet','') and 'yok' in result.fields.get('ates','')
        assert not result.review
        dialogue=extract_encounter(engine,'Geceleri susuyor musunuz? Hasta: Üç haftadır gece su içmek için kalkıyorum. İştahınız nasıl? Hasta: İştahım arttı ama kilo kaybediyorum. Hasta: Sürekli yorgunum. Öğrenci: Yarın sınav var.')
        complaints=dialogue.fields.get('sikayet','')
        assert 'Üç haftadır' in complaints and 'kilo kaybediyorum' in complaints and 'yorgunum' in complaints
        assert '?' not in complaints and 'sınav' not in complaints
        assert not dialogue.fields.get('ontani') and not dialogue.fields.get('oneri')
        return {'dialogue_answers_preserved':True,'questions_not_findings':True,'local_gguf':True,'structured_fields':True,'unrelated_excluded':True,
                'negation_dose_preserved':True,'seconds':round(time.monotonic()-started,2)}
    finally:engine.unload()
