"""Fail-closed outbound boundary: only curated clinical concepts leave the device.

PII regex alone cannot establish anonymity. Unknown concepts require an offline
vocabulary change and review, not an automatic exception from the LLM.
"""
import re

VOCABULARY = {
    'hypertension','hypokalemia','primary aldosteronism','adrenal nodule',
    'adrenal vein sampling','aldosterone renin ratio','screening','diagnosis',
    'treatment','prognosis','guideline','fatigue','diabetes mellitus',
    'type 2 diabetes','glycemic control','thyroid function tests','hypothyroidism',
    'hyperthyroidism','anemia','iron deficiency','vitamin b12 deficiency',
    'polycystic ovary syndrome','metabolic screening','primary care',
    'sleep apnea','amlodipine','beta blockers','adults','randomized controlled trial',
    'systematic review','meta-analysis','cohort study','case-control study',
    'obesity','weight loss','potassium','adrenal incidentaloma','aldosterone',
    'renin','blood pressure','cardiovascular risk','diabetes','insulin resistance',
}


class PrivacyError(ValueError):
    """Outbound text could not be proven to contain only allowed concepts."""


def safe_concept(value: str) -> str:
    """Resolve an exact reviewed concept; reject arbitrary names and text."""
    if not isinstance(value,str) or value.strip().lower() not in VOCABULARY:
        raise PrivacyError('Arama engellendi: kavram yerel güvenli klinik sözlüğünde yok. Soru kavramlarını düzenleyin; kişisel veri kullanmayın.')
    return value.strip().lower()


def validate_query(query: str) -> str:
    """Revalidate generated syntax at the final network/cache boundary."""
    pattern=r'\("([a-z 0-9-]+)"\[Title/Abstract\]\)(?: AND |$)'
    parts=list(re.finditer(pattern,query))
    if not parts or ''.join(m.group(0) for m in parts)!=query:
        raise PrivacyError('Sorgu güvenli klinik sorgu biçiminde değil.')
    for match in parts:
        safe_concept(match.group(1))
    return query
