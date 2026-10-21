import json
import unittest
from unittest.mock import Mock
from ai.llm_engine import parse_json, LLMError, GGUFEngine
from ai.clinical_parser import extract_anamnesis
from ai.question_generator import generate_questions
from settings import Settings
from literature.query_builder import build_query
from literature.pubmed_client import Article, PubMedClient, PubMedError, parse_articles
from literature.evidence_ranker import DeterministicRanker
from safety.privacy import PrivacyError, validate_query
from safety.citation_guard import validate_synthesis
from ai.evidence_synthesizer import synthesize

CASE={'age':58,'sex':'male','chief_complaint':'halsizlik','duration':'3 ay',
      'history':['hipertansiyon'],'medications':['amlodipin'],
      'labs':[{'name':'potasyum','value':2.9,'unit':None}]}
TRANSCRIPT='58 yaşında erkek hasta. Üç aydır halsizlik. On yıldır hipertansiyonu var. Amlodipin kullanıyor. Potasyum 2.9.'

class PipelineTests(unittest.TestCase):
    def test_extraction_contract(self):
        engine=Mock();engine.generate_json.return_value=CASE
        self.assertEqual(extract_anamnesis(engine,TRANSCRIPT),CASE)
        self.assertIn(TRANSCRIPT,engine.generate_json.call_args.args[0])

    def test_malformed_json(self):
        for value in ['{bad','null trailing','']:
            with self.assertRaises(LLMError):parse_json(value)
        self.assertEqual(parse_json('```json\n{"a":1}\n```'),{'a':1})

    def test_schema_rejects_wrong_fields_and_types(self):
        engine=Mock()
        for value in [{},dict(CASE,age=True),dict(CASE,labs='2.9'),dict(CASE,sex='guess')]:
            engine.generate_json.return_value=value
            with self.assertRaises(LLMError):extract_anamnesis(engine,TRANSCRIPT)

    def test_model_path_required(self):
        engine=GGUFEngine(Settings())
        with self.assertRaises(LLMError):engine.load()
        self.assertFalse(engine.is_loaded())
        engine.unload()

    def test_questions(self):
        engine=Mock();q={'question':'Hangi tarama yaklaşımları araştırılabilir?', 'concepts':['hypertension','hypokalemia'],'pico':None}
        engine.generate_json.return_value={'questions':[q,q]}
        self.assertEqual(len(generate_questions(engine,CASE)),2)
        engine.generate_json.return_value={'questions':[q]}
        with self.assertRaises(LLMError):generate_questions(engine,CASE)

    def test_query(self):
        self.assertEqual(build_query(['hypertension','hypokalemia']),
            '("hypertension"[Title/Abstract]) AND ("hypokalemia"[Title/Abstract])')

    def test_privacy_fail_closed(self):
        for value in ['Ahmet Yılmaz','12345678901','0555 123 45 67','Antalya adres','hypertension OR Ahmet','patient 24', '10.1000/example']:
            with self.assertRaises(PrivacyError):build_query([value])
        for value in ['hypertension','("Ahmet"[Title/Abstract])','("hypertension"[Title/Abstract]) OR 12345678901']:
            with self.assertRaises(PrivacyError):validate_query(value)

    def test_xml(self):
        articles=parse_articles(b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Trial <i>title</i></ArticleTitle><Abstract><AbstractText Label="RESULTS">Findings</AbstractText></Abstract><Journal><Title>Journal</Title><JournalIssue><PubDate><MedlineDate>2024 Jan</MedlineDate></PubDate></JournalIssue></Journal><PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType></PublicationTypeList></Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1000/test</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>''')
        self.assertEqual(articles[0].title,'Trial title')
        self.assertEqual(articles[0].year,'2024')
        self.assertEqual(articles[0].doi,'10.1000/test')
        self.assertIn('RESULTS',articles[0].abstract)

    def test_timeout_bounded(self):
        opener=Mock(side_effect=TimeoutError)
        client=PubMedClient(Settings(retries=1),opener,sleeper=lambda _:None)
        with self.assertRaises(PubMedError):client.search(build_query(['fatigue']))
        self.assertEqual(opener.call_count,2)

    def test_empty_and_cache(self):
        client=PubMedClient(Settings());client.esearch=Mock(return_value=[])
        query=build_query(['fatigue'])
        self.assertEqual(client.search(query),[])
        self.assertEqual(client.search(query),[])
        client.esearch.assert_called_once()
        self.assertEqual(synthesize(Mock(),'question',[],8192)['claims'],[])

    def test_citation_guard(self):
        articles=[Article('123','Title','Abstract',doi='10.1000/real')]
        valid={'claims':[{'claim':'Getirilen yayınlarda sınırlı kanıt var.','pmid':'123','doi':'10.1000/real'}],'limitations':'Küçük örneklem.'}
        self.assertEqual(validate_synthesis(valid,articles),valid)
        for pmid,doi in [('999',''),('123','10.1000/fake')]:
            bad={'claims':[{'claim':'İddia','pmid':pmid,'doi':doi}],'limitations':''}
            with self.assertRaises(LLMError):validate_synthesis(bad,articles)
        bad={'claims':[{'claim':'PMID: 999999','pmid':'123','doi':None}],'limitations':''}
        with self.assertRaises(LLMError):validate_synthesis(bad,articles)

    def test_relevance_before_type(self):
        a=Article('1','Hypertension hypokalemia','Relevant',year='2000')
        b=Article('2','Unrelated','Other',year='2026',publication_types=('Guideline',))
        self.assertEqual(DeterministicRanker().rank([b,a],['hypertension','hypokalemia'],1),[a])

    def test_settings(self):
        self.assertTrue(Settings().validate().low_memory)
        with self.assertRaises(ValueError):Settings(threads=0).validate()
