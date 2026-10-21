import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

def fetch_pubmed_references(queries):
    id_sets = []
    for _, _, query in queries:
        params = urllib.parse.urlencode(
            {"db": "pubmed", "term": query, "retmax": 3, "retmode": "json"}
        )
        request = urllib.request.Request(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + params,
            headers={"User-Agent": "AnamnezAsistani/1.0 (literature lookup)"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        id_sets.append(result["esearchresult"]["idlist"])

    ids = list(dict.fromkeys(identifier for group in id_sets for identifier in group))
    summaries = {}
    if ids:
        params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
        request = urllib.request.Request(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + params,
            headers={"User-Agent": "AnamnezAsistani/1.0 (literature lookup)"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            root = ET.fromstring(response.read())
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
