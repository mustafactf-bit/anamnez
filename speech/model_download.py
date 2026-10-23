"""Whisper cache-aware download progress; no patient data or global hooks."""
import fnmatch
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import threading
import time
from dataclasses import dataclass
from pathlib import Path

REPOSITORIES = {
    'small':'Systran/faster-whisper-small',
    'medium':'Systran/faster-whisper-medium',
    'large-v3':'Systran/faster-whisper-large-v3',
    'turbo':'mobiuslabsgmbh/faster-whisper-large-v3-turbo',
}
PATTERNS = ['config.json','preprocessor_config.json','model.bin','tokenizer.json','vocabulary.*']

@dataclass(frozen=True)
class ModelProgress:
    phase: str
    model: str
    percent: int | None = None
    downloaded: int = 0
    total: int = 0

class ByteProgress:
    """A fixed metadata denominator; throttle worker events, reserve 100 for success."""
    def __init__(self,model,total,cached,callback):
        self.model=model;self.total=total;self.cached=cached;self.callback=callback
        self.last=-1;self.when=0;self.lock=threading.Lock()

    def update(self,count,force=False):
        with self.lock:
            downloaded=min(self.total,max(0,self.cached+int(count)))
            percent=min(99,int(downloaded*100/self.total)) if self.total else None
            now=time.monotonic()
            if force or (percent != self.last and now-self.when >= .15):
                self.callback(ModelProgress('downloading',self.model,percent,downloaded,self.total))
                self.last=percent;self.when=now

def model_cache(model,cache_dir=None):
    root=Path(cache_dir) if cache_dir else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AnamnezAsistani'/'models'
    return root/'whisper'/model

def ready_snapshot(root):
    try:
        data=json.loads((root/'ready.json').read_text(encoding='utf-8'))
        if not re.fullmatch('[a-f0-9]{40}',data['revision']):return None
        folder=root/data['revision']
        for file in data['files']:
            name=file['name']
            if Path(name).name!=name or not (folder/name).is_file() or (folder/name).stat().st_size!=file['size']:return None
        if not data['files']:return None
        return str(folder)
    except (OSError,ValueError,KeyError,TypeError):return None

def stream_file(url,target,size,progress,sha256=None):
    """128 KiB reads, bounded socket wait, strict resume and atomic completion."""
    target=Path(target);partial=target.with_suffix(target.suffix+'.partial')
    offset=partial.stat().st_size if partial.exists() else 0
    if offset>size:offset=0
    total=offset;progress(total)
    while total<size:
        start=total;end=min(start+4*1024*1024,size)-1
        headers={'User-Agent':'AnamnezAsistani-ModelDownload','Accept-Encoding':'identity',
                 'Range':f'bytes={start}-{end}'}
        # Distinct range URL also avoids intermediary caches mixing range responses.
        request=urllib.request.Request(url+f'&part={start}',headers=headers)
        with urllib.request.urlopen(request,timeout=20) as response:
            if response.status==206:
                if response.headers.get('Content-Range','')!=f'bytes {start}-{end}/{size}':
                    raise OSError('Model indirme aralığı uyuşmuyor.')
                expected=end+1
            elif response.status==200:
                total=0;expected=size
            else:raise OSError('Beklenmeyen model indirme yanıtı.')
            with partial.open('ab' if total else 'wb') as output:
                while chunk:=response.read(128*1024):
                    total+=len(chunk)
                    if total>expected:raise OSError('Model boyutu uyuşmuyor.')
                    output.write(chunk);progress(total)
            if total!=expected:raise OSError('Model indirmesi eksik kaldı.')
    if total!=size:raise OSError('Model indirmesi eksik kaldı.')
    if size==0:partial.write_bytes(b'')
    if sha256:
        digest=hashlib.sha256()
        with partial.open('rb') as stream:
            while chunk:=stream.read(1024*1024):digest.update(chunk)
        if digest.hexdigest()!=sha256:
            partial.unlink(missing_ok=True)
            raise OSError('Model dosyası doğrulanamadı.')
    partial.replace(target)

def download_snapshot(repo_id,model,callback,patterns=PATTERNS,cache_dir=None):
    """Pin metadata and payload to the same commit; include already cached bytes."""
    from huggingface_hub import HfApi
    callback(ModelProgress('checking',model))
    info=HfApi().model_info(repo_id,files_metadata=True)
    files=[f for f in info.siblings if any(fnmatch.fnmatchcase(f.rfilename,p) for p in patterns)]
    if not files or any(type(f.size) is not int or f.size < 0 for f in files):
        raise ValueError('Model dosya boyutları belirlenemedi.')
    if not re.fullmatch('[a-f0-9]{40}',info.sha):raise ValueError('Geçersiz model revizyonu.')
    root=model_cache(model,cache_dir);folder=root/info.sha;folder.mkdir(parents=True,exist_ok=True)
    total=sum(f.size for f in files);done=0;downloaded=False
    tracker=ByteProgress(model,total,0,callback)
    for file in files:
        if Path(file.rfilename).name!=file.rfilename:raise ValueError('Geçersiz model dosya adı.')
        target=folder/file.rfilename
        if target.is_file() and target.stat().st_size==file.size:
            done+=file.size;continue
        downloaded=True
        url=f'https://huggingface.co/{repo_id}/resolve/{info.sha}/{urllib.parse.quote(file.rfilename)}?download=true'
        stream_file(url,target,file.size,lambda count:tracker.update(done+count),
            getattr(getattr(file,'lfs',None),'sha256',None))
        done+=file.size
    manifest={'revision':info.sha,'files':[{'name':f.rfilename,'size':f.size} for f in files]}
    pending=root/'ready.partial';pending.write_text(json.dumps(manifest),encoding='utf-8');pending.replace(root/'ready.json')
    if downloaded:callback(ModelProgress('downloaded',model,100,total,total))
    else:callback(ModelProgress('cached',model))
    return str(folder)

def download_whisper_model(model,callback):
    """Complete existing cache works offline and never flashes a fake download."""
    from faster_whisper.utils import download_model
    own_cache=ready_snapshot(model_cache(model))
    if own_cache:
        callback(ModelProgress('cached',model));return own_cache
    try:
        path=Path(download_model(model,local_files_only=True))
        if (all((path/name).is_file() for name in ('config.json','model.bin','tokenizer.json'))
                and any(path.glob('vocabulary.*'))):
            callback(ModelProgress('cached',model))
            return str(path)
    except (OSError,ValueError):
        pass
    return download_snapshot(REPOSITORIES[model],model,callback)
