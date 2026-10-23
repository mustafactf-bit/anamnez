"""Lightweight deterministic ranking, relevance before publication prestige."""
import datetime
import re
from typing import Protocol
from literature.pubmed_client import Article

class EvidenceRanker(Protocol):
    """Optional future rerankers implement this interface."""
    def rank(self, articles: list[Article], concepts: list[str], top_k: int) -> list[Article]: ...

class DeterministicRanker:
    """Term coverage dominates type and recency; no embedding model required."""
    def rank(self,articles,concepts,top_k):
        tokens=set(re.findall(r'[a-z]{3,}',' '.join(concepts).lower()))
        def score(a):
            words=set(re.findall(r'[a-z]{3,}',(a.title+' '+a.abstract).lower()))
            relevance=len(tokens & words)/max(1,len(tokens))
            kind=' '.join(a.publication_types).lower()
            weight=max((v for key,v in [('guideline',1),('systematic review',1),('meta-analysis',1),('randomized controlled trial',.8),('cohort',.5),('case-control',.4)] if key in kind),default=0)
            age=datetime.date.today().year-int(a.year) if a.year.isdigit() else 50
            recency=max(0,1-max(0,age)/20)
            return (relevance,.15*weight+.05*recency,a.pmid)
        return sorted({a.pmid:a for a in articles}.values(),key=score,reverse=True)[:top_k]
