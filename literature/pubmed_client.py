"""Bounded E-utilities transport, in-memory cache and structured publications."""
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from safety.privacy import validate_query


@dataclass(frozen=True)
class Article:
    """Metadata retrieved from PubMed, with optional abstract/DOI."""
    pmid: str
    title: str
    abstract: str = ''
    authors: tuple[str,...] = ()
    journal: str = ''
    year: str = ''
    publication_types: tuple[str,...] = ()
    doi: str = ''


def parse_articles(xml: bytes) -> list[Article]:
    """Parse efetch XML including labelled abstracts and inline title markup."""
    root=ET.fromstring(xml)
    def content(node):
        return ''.join(node.itertext()).strip() if node is not None else ''
    articles=[]
    for item in root.findall('.//PubmedArticle'):
        citation=item.find('MedlineCitation'); article=citation.find('Article') if citation is not None else None
        if article is None: continue
        pmid=citation.findtext('PMID','')
        if not re.fullmatch(r'[0-9]{1,10}',pmid): continue
        date=article.find('Journal/JournalIssue/PubDate')
        date_text=content(date)
        year=re.search(r'\b(?:19|20)\d{2}\b',date_text)
        abstracts=[(node.get('Label','')+': ' if node.get('Label') else '')+content(node) for node in article.findall('Abstract/AbstractText')]
        authors=tuple(content(a.find('CollectiveName')) or ' '.join(filter(None,[a.findtext('ForeName',''),a.findtext('LastName','')])) for a in article.findall('AuthorList/Author'))
        doi=next((content(n) for n in item.findall('PubmedData/ArticleIdList/ArticleId') if n.get('IdType')=='doi'),'')
        articles.append(Article(pmid,content(article.find('ArticleTitle')),'\n'.join(abstracts),authors,
            content(article.find('Journal/Title')),year.group() if year else '',
            tuple(content(n) for n in article.findall('PublicationTypeList/PublicationType')),doi))
    return articles


class PubMedError(ValueError):
    """Safe network error independent of raw request text."""


class PubMedClient:
    """Public PubMed transport. Use from a background worker only."""
    def __init__(self,settings,opener=urllib.request.urlopen,sleeper=time.sleep):
        self.settings=settings
        self.opener=opener
        self.sleep=sleeper
        self.cache={}
        self._last_request=0.0

    def _request(self,endpoint,params):
        url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'+endpoint+'.fcgi?'+urllib.parse.urlencode({'db':'pubmed',**params})
        for attempt in range(self.settings.retries+1):
            self.sleep(max(0,0.36-(time.monotonic()-self._last_request)))
            self._last_request=time.monotonic()
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'AnamnezAsistani/2.0-alpha'})
                with self.opener(request,timeout=self.settings.timeout) as response:
                    data=response.read(4_000_001)
                if len(data)>4_000_000: raise PubMedError('PubMed yanıtı boyut sınırını aştı.')
                return data
            except (OSError,TimeoutError) as error:
                if attempt==self.settings.retries:
                    raise PubMedError('PubMed erişilemedi. İnternet bağlantısını kontrol edip yeniden deneyin.') from error
                self.sleep(2**attempt)

    def esearch(self,query: str) -> list[str]:
        """Search a privacy-checked clinical query."""
        validate_query(query)
        result=json.loads(self._request('esearch',{'term':query,'retmode':'json','retmax':self.settings.pubmed_retmax}))
        ids=result['esearchresult']['idlist']
        return self._ids(ids)[:self.settings.pubmed_retmax]

    @staticmethod
    def _ids(ids):
        if not isinstance(ids,list) or any(not isinstance(x,str) or not re.fullmatch(r'[0-9]{1,10}',x) for x in ids):
            raise PubMedError('PubMed geçersiz yayın kimliği döndürdü.')
        return list(dict.fromkeys(ids))

    def esummary(self,ids: list[str]) -> dict:
        """Fetch summary metadata for validated numeric identifiers."""
        ids=self._ids(ids)
        if not ids:return {}
        return json.loads(self._request('esummary',{'id':','.join(ids),'retmode':'json'}))['result']

    def efetch(self,ids: list[str]) -> list[Article]:
        """Fetch abstracts and metadata, accepting only requested identifiers."""
        ids=self._ids(ids)
        if not ids:return []
        return [a for a in parse_articles(self._request('efetch',{'id':','.join(ids),'retmode':'xml'})) if a.pmid in ids]

    def search(self,query: str) -> list[Article]:
        """Short bounded cache stores literature only, never patient data."""
        validate_query(query)
        now=time.monotonic()
        self.cache={k:v for k,v in self.cache.items() if now-v[0]<self.settings.cache_seconds}
        if query in self.cache:return list(self.cache[query][1])
        try:
            articles=self.efetch(self.esearch(query))
        except (KeyError,TypeError,json.JSONDecodeError,ET.ParseError) as error:
            raise PubMedError('PubMed yanıtı okunamadı; yeniden deneyin.') from error
        if len(self.cache)>=32:self.cache.pop(next(iter(self.cache)))
        self.cache[query]=(now,tuple(articles))
        return articles
