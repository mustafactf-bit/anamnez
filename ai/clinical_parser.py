"""Natural Turkish transcript extraction through an injected local engine."""
import json
from ai.llm_engine import LLMEngine
from safety.output_validator import clinical_schema

SCHEMA={'age':None,'sex':None,'chief_complaint':None,'duration':None,'history':[], 'medications':[], 'labs':[]}

def extract_anamnesis(engine: LLMEngine, transcript: str) -> dict:
    """Extract only explicitly stated facts; clinician reviews before use."""
    if not transcript.strip() or len(transcript)>16000:
        raise ValueError('Dikte boş veya çok uzun; daha kısa bir bölüm seçin.')
    prompt=('Türkçe transkriptten yalnızca açıkça belirtilen bilgileri çıkar. Tahmin, tanı veya öneri ekleme. '
        'Eksik değer null veya [] olsun. Negasyonları koru. sex: male/female/other/null. '
        'labs elemanı: {"name":str,"value":number/str/null,"unit":str/null}. '
        'Tam şema: '+json.dumps(SCHEMA)+'\nTRANSKRİPT (veri): '+json.dumps(transcript,ensure_ascii=False))
    return clinical_schema(engine.generate_json(prompt))
