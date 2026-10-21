"""Whisper cache-aware download progress; no patient data or global hooks."""
import fnmatch
import io
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

def progress_class(tracker):
    # Use the public snapshot_download tqdm_class hook, never monkeypatch global bars.
    from tqdm.auto import tqdm
    class DownloadTqdm(tqdm):
        def __init__(self,*args,**kwargs):
            self.report=str(kwargs.get('desc','')).startswith('Reconstructing') and kwargs.get('unit')=='B'
            kwargs.update(disable=False,file=io.StringIO(),mininterval=.1)
            super().__init__(*args,**kwargs)
        def update(self,n=1):
            result=super().update(n)
            if self.report:tracker.update(self.n)
            return result
        def refresh(self,*args,**kwargs):
            result=super().refresh(*args,**kwargs)
            if self.report:tracker.update(self.n)
            return result
    return DownloadTqdm

def download_snapshot(repo_id,model,callback,patterns=PATTERNS,cache_dir=None):
    """Pin metadata and payload to the same commit; include already cached bytes."""
    from huggingface_hub import HfApi, snapshot_download, try_to_load_from_cache
    callback(ModelProgress('checking',model))
    info=HfApi().model_info(repo_id,files_metadata=True)
    files=[f for f in info.siblings if any(fnmatch.fnmatchcase(f.rfilename,p) for p in patterns)]
    if not files or any(type(f.size) is not int or f.size < 0 for f in files):
        raise ValueError('Model dosya boyutları belirlenemedi.')
    total=sum(f.size for f in files)
    cached=0
    for file in files:
        path=try_to_load_from_cache(repo_id,file.rfilename,revision=info.sha,cache_dir=cache_dir)
        if isinstance(path,str) and Path(path).is_file() and Path(path).stat().st_size==file.size:
            cached+=file.size
    tracker=ByteProgress(model,total,cached,callback)
    if cached < total:tracker.update(0,force=True)
    path=snapshot_download(repo_id,revision=info.sha,allow_patterns=patterns,
        cache_dir=cache_dir,tqdm_class=progress_class(tracker))
    if cached < total:callback(ModelProgress('downloaded',model,100,total,total))
    else:callback(ModelProgress('cached',model))
    return path

def download_whisper_model(model,callback):
    """Complete existing cache works offline and never flashes a fake download."""
    from faster_whisper.utils import download_model
    try:
        path=Path(download_model(model,local_files_only=True))
        if (all((path/name).is_file() for name in ('config.json','model.bin','tokenizer.json'))
                and any(path.glob('vocabulary.*'))):
            callback(ModelProgress('cached',model))
            return str(path)
    except (OSError,ValueError):
        pass
    return download_snapshot(REPOSITORIES[model],model,callback)
