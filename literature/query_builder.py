"""Deterministic field-scoped PubMed query construction."""
from safety.privacy import safe_concept, validate_query

def build_query(concepts: list[str]) -> str:
    """Build from reviewed terms; raw model syntax is never accepted."""
    if not isinstance(concepts,list) or not 1<=len(concepts)<=6:
        raise ValueError('Bir ile altı klinik arama kavramı gerekli.')
    terms=list(dict.fromkeys(safe_concept(x) for x in concepts))
    return validate_query(' AND '.join(f'("{term}"[Title/Abstract])' for term in terms))
