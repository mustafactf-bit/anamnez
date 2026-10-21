"""Retrieval membership is required for every displayed model claim."""
import re
from ai.llm_engine import LLMError
from safety.output_validator import text

def validate_synthesis(value: dict, articles: list) -> dict:
    """Reject the entire synthesis on any invalid PMID/DOI, including prose."""
    if not isinstance(value,dict) or set(value)!={'claims','limitations'} or not isinstance(value['claims'],list) or not 1<=len(value['claims'])<=10:
        raise LLMError('Kanıt özeti şeması geçersiz.')
    allowed={a.pmid:a for a in articles if a.abstract}
    text(value['limitations'])
    for claim in value['claims']:
        if not isinstance(claim,dict) or set(claim)!={'claim','pmid','doi'}:
            raise LLMError('Kaynaklı iddia şeması geçersiz.')
        text(claim['claim']);text(claim['pmid']);text(claim['doi'],True)
        article=allowed.get(claim['pmid'])
        if not article or claim['doi'] not in (None,'',article.doi):
            raise LLMError('Özet engellendi: getirilen yayınlarda bulunmayan PMID/DOI var.')
    # References are rendered exclusively from validated metadata, never prose.
    prose=' '.join([value['limitations']]+[c['claim'] for c in value['claims']])
    if re.search(r'\bPMID\b|\bDOI\b|https?://|10\.\d{4,9}/',prose,re.I):
        raise LLMError('Özet engellendi: metin içinde doğrulanamayan kaynak ifadesi var.')
    if re.search(r'kesin tanı|tanı\s+\w+.{0,20}dır|şu ilacı ver|kesinlikle.{0,30}uygula',prose,re.I):
        raise LLMError('Özet karar destek diline uymuyor; yeniden deneyin.')
    return value
