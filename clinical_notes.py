import datetime
import re
from config import FIELDS, LABELS

def format_note(data):
    date = datetime.datetime.now().strftime("%d.%m.%Y")
    return f"""TARİH: {date:<20} BOY: {data['boy']:<6} CM      KİLO: {data['kilo']:<6} KG
ŞİKÂYETİ:
{data['sikayet']}

ÖZGEÇMİŞİ:
{data['ozgecmis']}

SOYGEÇMİŞİ:
ANNE: {data['soygecmis_anne']}
BABA: {data['soygecmis_baba']}
KARDEŞ: {data['soygecmis_kardes']}

KULLANDIĞI İLAÇLAR:
{data['ilaclar']}

FİZİK MUAYENE:
GENEL DURUMU: {data['genel_durum']}
TANSİYON: {data['tansiyon']:<15} NABIZ: {data['nabiz']:<15} ATEŞ: {data['ates']:<15} SOL.SAYISI: {data['solunum']}
BB: {data['bb']}
KVS: {data['kvs']}
SOLS: {data['sols']}
BATIN: {data['batin']}
EXT: {data['ext']}

LABORATUVAR:
AKŞ: {data['aks']:<10} HbA1c: {data['hba1c']:<10} sT4: {data['st4']:<10} TSH: {data['tsh']:<10} KCFT: {data['kcft']:<10} BFT: {data['bft']}

GÖRÜNTÜLEME (USG/BT/MR/SİNTİGRAFİ):
{data['goruntuleme']}

ÖNTANI: {data['ontani']}
ÖNERİ: {data['oneri']}

1- HASTA BİLGİLENDİRİLDİ, İLAÇLARI ANLATILDI
2- POLİKLİNİK KONTROLÜ ÖNERİLDİ
"""

def parse_dictation(text, data):
    updated = []
    unlabelled = []
    field_names = sorted(
        {alias for aliases in LABELS.values() for alias in aliases},
        key=len,
        reverse=True,
    )
    field_pattern = "|".join(re.escape(alias) for alias in field_names)
    separator = r"(?<=[.!?])\s+|\s*[;\n]+\s*|,\s*(?=(?:" + field_pattern + r")(?:\s*[:：\-]|\s))"
    parts = re.split(separator, text, flags=re.IGNORECASE)
    for raw_line in parts:
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for key, aliases in LABELS.items():
            for alias in sorted(aliases, key=len, reverse=True):
                match = re.match(
                    r"^\s*"
                    + re.escape(alias)
                    + r"(?:\s*[:：,\-]\s*|\s+)(.*?)\s*$",
                    line,
                    re.IGNORECASE,
                )
                if match and match.group(1).strip():
                    data[key] = re.sub(r"[.!?]+$", "", match.group(1).strip()).strip()
                    updated.append(FIELDS[key])
                    matched = True
                    break
            if matched:
                break
        if not matched:
            unlabelled.append(line)
    if unlabelled:
        existing = data["sikayet"].strip()
        additions = "\n".join(unlabelled)
        if existing in ("", "..."):
            data["sikayet"] = additions
        else:
            data["sikayet"] = existing + "\n" + additions
        updated.append(FIELDS["sikayet"] + " (etiketsiz dikte eklendi)")
    return updated
