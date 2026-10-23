import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from config import RECOMMENDATIONS
from settings import Settings
from literature.pubmed_client import PubMedClient
from safety.privacy import PrivacyError

def fetch_pubmed_references(queries):
    """Retained general references accept only the five reviewed fixed queries."""
    if list(queries) != RECOMMENDATIONS:
        raise PrivacyError('Genel kaynak aramasında yalnızca sabit klinik sorgular kullanılabilir.')
    client = PubMedClient(Settings())
    id_sets = []
    for _, _, query in queries:
        result = json.loads(client._request('esearch',
            {'term':query, 'retmax':3, 'retmode':'json'}))
        id_sets.append(client._ids(result['esearchresult']['idlist']))

    ids = list(dict.fromkeys(identifier for group in id_sets for identifier in group))
    summaries = {}
    if ids:
        root = ET.fromstring(client._request('esummary',
            {'id':','.join(ids), 'retmode':'xml'}))
        for item in root.findall(".//DocSum"):
            uid = item.findtext("Id", "")
            values = {node.get("Name", ""): node for node in item.findall("Item")}
            title = values.get("Title")
            full_title = "".join(title.itertext()).strip() if title is not None else "Başlık bulunamadı"
            authors_item = values.get("AuthorList")
            authors = (
                ", ".join("".join(author.itertext()).strip() for author in authors_item.findall("Item")[:3])
                if authors_item is not None
                else ""
            )
            if authors_item is not None and len(authors_item.findall("Item")) > 3:
                authors += ", et al."
            journal = values.get("FullJournalName")
            journal_name = "".join(journal.itertext()).strip() if journal is not None else ""
            pubdate = values.get("PubDate")
            year = "".join(pubdate.itertext()).strip()[:4] if pubdate is not None else ""
            summaries[uid] = {
                "title": full_title,
                "authors": authors,
                "journal": journal_name,
                "year": year,
            }
    return id_sets, summaries
