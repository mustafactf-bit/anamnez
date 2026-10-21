"""Patient-free HTTPS update client. Never executes unverified downloads."""
import base64
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = 'mustafactf-bit/anamnez'
API = f'https://api.github.com/repos/{REPO}/releases?per_page=20'
PUBLIC_KEY = 'OvJdpjvxo2rJjx/s/VhpMcCDWYpfmfAO5KItBQMnsq8='
MAX_INSTALLER = 1024 * 1024 * 1024

class UpdateError(ValueError):
    pass

def version_key(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:-alpha\.(\d+)\.(\d+))?', value)
    if not match:
        raise UpdateError('Desteklenmeyen sürüm biçimi.')
    major, minor, patch, alpha, revision = match.groups()
    return (int(major), int(minor), int(patch), 1 if alpha is None else 0,
            int(alpha or 0), int(revision or 0))

def allowed_url(url):
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme == 'https' and parsed.netloc == 'github.com'
            and parsed.path.startswith(f'/{REPO}/releases/download/')
            and not parsed.query and not parsed.fragment)

def fetch(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent':'AnamnezAsistani-Updater',
        'Accept':'application/vnd.github+json' if url == API else 'application/octet-stream'})
    with urllib.request.urlopen(request, timeout=25) as response:
        result = response.read(limit + 1)
    if len(result) > limit:
        raise UpdateError('Güncelleme yanıtı izin verilen boyutu aşıyor.')
    return result

@dataclass(frozen=True)
class Release:
    version: str
    url: str
    sha256: str
    size: int

def verify_manifest(raw, signature, public_key=PUBLIC_KEY):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True)).verify(signature, raw)
        data = json.loads(raw)
        if set(data) != {'version','url','sha256','size'}:
            raise ValueError()
        release = Release(**data)
        version_key(release.version)
        if (not allowed_url(release.url) or not re.fullmatch(r'[0-9a-f]{64}',release.sha256)
                or type(release.size) is not int or not 0 < release.size <= MAX_INSTALLER
                or not release.url.endswith('/Anamnez-Asistani-Kurulum.exe')
                or f'/v{release.version}/' not in release.url):
            raise ValueError()
        return release
    except Exception as error:
        raise UpdateError('Güncelleme imzası veya paket bilgisi doğrulanamadı.') from error

def check_updates(current, reader=fetch):
    """Only this repository's alpha/stable releases; no requests contain clinical data."""
    try:
        releases = json.loads(reader(API, 2 * 1024 * 1024))
        candidates = []
        for item in releases:
            if item.get('draft'): continue
            try:
                key = version_key(item.get('tag_name',''))
            except UpdateError:
                continue
            if key > version_key(current): candidates.append((key,item))
        for _, item in sorted(candidates, key=lambda x:x[0], reverse=True):
            assets = {asset['name']:asset['browser_download_url'] for asset in item.get('assets',[])}
            if not {'update.json','update.sig'} <= assets.keys(): continue
            if not all(allowed_url(assets[name]) for name in ('update.json','update.sig')):
                raise UpdateError('Beklenmeyen güncelleme adresi.')
            release = verify_manifest(reader(assets['update.json'],16384),reader(assets['update.sig'],64))
            if 'v'+release.version != item['tag_name']:
                raise UpdateError('Güncelleme sürümü uyuşmuyor.')
            return release
        return None
    except UpdateError: raise
    except Exception as error:
        raise UpdateError('Güncelleme kontrol edilemedi; internet bağlantısını kontrol edin.') from error

def download_update(release, directory):
    """Stage atomically; interrupted downloads never become executable candidates."""
    if not allowed_url(release.url): raise UpdateError('Geçersiz paket adresi.')
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'Anamnez-{release.version}-Kurulum.exe'
    part = target.with_suffix('.partial')
    digest = hashlib.sha256(); total = 0
    try:
        request = urllib.request.Request(release.url,headers={'User-Agent':'AnamnezAsistani-Updater'})
        with urllib.request.urlopen(request,timeout=30) as response, part.open('wb') as output:
            while chunk := response.read(1024*1024):
                total += len(chunk)
                if total > release.size: raise UpdateError('Paket boyutu uyuşmuyor.')
                digest.update(chunk); output.write(chunk)
        if total != release.size or digest.hexdigest() != release.sha256:
            raise UpdateError('İndirilen paket doğrulanamadı; kurulum başlatılmadı.')
        part.replace(target)
        return target
    finally:
        part.unlink(missing_ok=True)

def launch_installer(path, release):
    """Recheck bytes immediately before launch; no silent close or patient access."""
    if sys.platform != 'win32' or not getattr(sys,'frozen',False):
        raise UpdateError('Kurulum yalnızca Windows EXE sürümünden başlatılabilir.')
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        while chunk := stream.read(1024*1024): digest.update(chunk)
    if path.stat().st_size != release.size or digest.hexdigest() != release.sha256:
        raise UpdateError('Paket değişmiş; kurulum başlatılmadı.')
    subprocess.Popen([str(path),'/NOCLOSEAPPLICATIONS','/NORESTART'],close_fds=True)
