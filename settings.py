"""Validated, patient-free application settings."""
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from storage.patient_storage import save_patient


@dataclass
class Settings:
    """CPU-first runtime configuration."""
    model_path: str = ''
    context_size: int = 8192
    threads: int = 4
    max_tokens: int = 1200
    whisper_model: str = 'small'
    low_memory: bool = True
    pubmed_retmax: int = 30
    rerank_top_k: int = 10
    synthesis_top_k: int = 5
    timeout: int = 15
    retries: int = 2
    cache_seconds: int = 300
    debug_queries: bool = False
    local_correction: bool = True
    test_mode: bool = False

    def validate(self) -> 'Settings':
        for name, low, high in [('context_size',2048,32768),('threads',1,64),
                ('max_tokens',128,4096),('pubmed_retmax',20,50),('rerank_top_k',1,50),
                ('synthesis_top_k',1,10),('timeout',1,120),('retries',0,5),('cache_seconds',0,3600)]:
            value=getattr(self,name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{name}: {low}–{high} aralığında tam sayı gerekli.')
        if self.synthesis_top_k > self.rerank_top_k or self.max_tokens >= self.context_size:
            raise ValueError('Top-k veya model bağlam ayarları uyumsuz.')
        if self.whisper_model not in ('small','medium','large-v3','turbo'):
            raise ValueError('Geçersiz Whisper modeli.')
        if not isinstance(self.model_path,str) or any(type(getattr(self,k)) is not bool for k in ('low_memory','debug_queries','local_correction','test_mode')):
            raise ValueError('Geçersiz ayar türü.')
        return self


SETTINGS_PATH = Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'AnamnezAsistani' / 'settings.json'

def load_settings(path=SETTINGS_PATH) -> Settings:
    """Missing settings use defaults; corrupt settings are not overwritten."""
    if not Path(path).exists():
        return Settings()
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    return Settings(**{k:v for k,v in data.items() if k in Settings.__dataclass_fields__}).validate()

def save_settings(settings: Settings, path=SETTINGS_PATH) -> None:
    """Persist only configuration, never patient text."""
    settings.validate()
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    save_patient(str(path),asdict(settings))
