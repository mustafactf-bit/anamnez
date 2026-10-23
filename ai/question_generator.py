"""Clinician-reviewable literature questions, never treatment instructions."""
import json
from ai.llm_engine import LLMEngine, LLMError
from safety.output_validator import text

def generate_questions(engine: LLMEngine, anamnesis: dict) -> list[dict]:
    """Suggest 2–5 questions with optional PICO and English search concepts."""
    result=engine.generate_json('Tanı koymadan 2–5 Türkçe literatür sorusu öner. Yalnızca JSON: '
        '{"questions":[{"question":"...", "concepts":["English clinical concept"], '
        '"pico":null}]}. PICO yalnızca müdahale/karşılaştırma sorularında population/intervention/comparison/outcome '
        'alanlarıyla nesne olsun. Kavramlar klinik terimler olmalı, kişisel veri içermemeli. Hasta verisi: '
        +json.dumps(anamnesis,ensure_ascii=False))
    if not isinstance(result,dict) or set(result)!={'questions'} or not isinstance(result['questions'],list) or not 2<=len(result['questions'])<=5:
        raise LLMError('Model 2–5 geçerli klinik soru üretmedi.')
    for q in result['questions']:
        if not isinstance(q,dict) or set(q)!={'question','concepts','pico'}:
            raise LLMError('Soru şeması geçersiz.')
        text(q['question'])
        if not isinstance(q['concepts'],list) or not 1<=len(q['concepts'])<=6:
            raise LLMError('Arama kavramları geçersiz.')
        for concept in q['concepts']: text(concept)
        if q['pico'] is not None:
            if not isinstance(q['pico'],dict) or set(q['pico'])!={'population','intervention','comparison','outcome'}:
                raise LLMError('PICO şeması geçersiz.')
            for v in q['pico'].values(): text(v,True)
    return result['questions']
