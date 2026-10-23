"""Explicitly reviewed Miamed append notes, independent of AI and networking."""
import datetime as dt
from dataclasses import dataclass
from config import FIELDS

PLACEHOLDERS = {'', '...', '…'}

def filled(value: str) -> bool:
    """Only explicitly populated fields become note content."""
    return str(value).strip() not in PLACEHOLDERS

def build_note_body(data: dict, transcript: str = '') -> str:
    """Preserve entered text without inserting presumed findings or procedures."""
    sections = []
    def section(title, keys, labelled=False):
        lines = []
        for key in keys:
            value = str(data.get(key, '')).strip()
            if filled(value):
                lines.append(f'{FIELDS[key]}: {value}' if labelled else value)
        if lines:
            sections.append(title + ':\n' + '\n'.join(lines))
    section('ÖLÇÜMLER', ['boy', 'kilo'], True)
    section('ŞİKÂYET / HASTALIK ÖYKÜSÜ', ['sikayet'])
    section('ÖZGEÇMİŞ', ['ozgecmis'])
    section('SOYGEÇMİŞ', ['soygecmis_anne','soygecmis_baba','soygecmis_kardes'], True)
    section('KULLANDIĞI İLAÇLAR', ['ilaclar'])
    section('FİZİK MUAYENE', ['genel_durum','tansiyon','nabiz','ates','solunum','bb','kvs','sols','batin','ext'], True)
    section('LABORATUVAR', ['aks','hba1c','st4','tsh','kcft','bft'], True)
    section('GÖRÜNTÜLEME', ['goruntuleme'])
    section('HEKİMİN ÖN DEĞERLENDİRMESİ', ['ontani'])
    section('HEKİMİN PLANI', ['oneri'])
    extension=data.get('_v2')
    structured=extension.get('structured_anamnesis') if isinstance(extension,dict) else None
    if isinstance(structured,dict):
        details=[]
        if structured.get('age') is not None:details.append(f"Yaş: {structured['age']}")
        sex={'male':'Erkek','female':'Kadın','other':'Diğer'}.get(structured.get('sex'))
        if sex:details.append('Cinsiyet: '+sex)
        if structured.get('duration'):details.append('Yakınma süresi: '+structured['duration'])
        for lab in structured.get('labs',[]):
            if isinstance(lab,dict):
                details.append(f"{lab.get('name','')}: {lab.get('value') if lab.get('value') is not None else 'belirtilmedi'} {lab.get('unit') or ''}".strip())
        if details:sections.append('HEKİMİN AKTARDIĞI EK BİLGİLER:\n'+'\n'.join(details))
    if transcript.strip():
        sections.append('GÖRÜŞME NOTU:\n' + transcript.strip())
    return '\n\n'.join(sections)


@dataclass(frozen=True)
class ApprovedNote:
    """Immutable-in-use snapshot of exactly what the physician approved."""
    body: str
    approved_at: dt.datetime

    @property
    def text(self) -> str:
        """Leading newlines separate this encounter from existing Miamed text."""
        return '\n\n────────── ' + self.approved_at.strftime('%d.%m.%Y %H:%M') + ' ──────────\n\n' + self.body + '\n'

def approve_note(body: str, now=None) -> ApprovedNote:
    """Stamp only at explicit approval; never append a second generated header."""
    if not body.strip():
        raise ValueError('Onaylanacak anamnez boş. Önce metin girin.')
    return ApprovedNote(body, now if now is not None else dt.datetime.now().astimezone())
