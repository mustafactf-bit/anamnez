"""Strict lightweight schema validation for untrusted model output."""
from ai.llm_engine import LLMError


def text(value, nullable=False):
    """Validate bounded strings."""
    if nullable and value is None:
        return value
    if not isinstance(value,str) or len(value)>12000:
        raise LLMError('Model çıktısında geçersiz metin alanı var.')
    return value


def string_list(value):
    """Validate a bounded list of strings."""
    if not isinstance(value,list) or len(value)>50:
        raise LLMError('Model çıktısında geçersiz liste var.')
    return [text(x) for x in value]


def clinical_schema(value):
    """Reject invalid clinical objects instead of coercing invented values."""
    keys={'age','sex','chief_complaint','duration','history','medications','labs'}
    if not isinstance(value,dict) or set(value)!=keys:
        raise LLMError('Anamnez JSON alanları beklenen şemayla uyuşmuyor.')
    if value['age'] is not None and (type(value['age']) is not int or not 0<=value['age']<=130):
        raise LLMError('Yaş alanı geçersiz.')
    if value['sex'] not in (None,'male','female','other'):
        raise LLMError('Cinsiyet alanı geçersiz.')
    for key in ('chief_complaint','duration'): text(value[key],True)
    for key in ('history','medications'): string_list(value[key])
    if not isinstance(value['labs'],list) or len(value['labs'])>50:
        raise LLMError('Laboratuvar listesi geçersiz.')
    for lab in value['labs']:
        if not isinstance(lab,dict) or set(lab)!={'name','value','unit'}:
            raise LLMError('Laboratuvar şeması geçersiz.')
        text(lab['name']);text(lab['unit'],True)
        if lab['value'] is not None and (type(lab['value']) not in (int,float,str) or isinstance(lab['value'],str) and len(lab['value'])>100):
            raise LLMError('Laboratuvar değeri geçersiz.')
    return value
