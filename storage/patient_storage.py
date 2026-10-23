"""Compatible patient JSON storage; writes replace atomically."""
import json
import os
import tempfile
from pathlib import Path
from config import FIELDS

def save_patient(path: str, data: dict) -> None:
    """Save all fields, preserving unknown extensions on a load/save cycle."""
    target = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, delete=False) as stream:
        temporary = stream.name
        json.dump(data, stream, ensure_ascii=False, indent=2)
    try:
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def load_patient(path: str) -> dict:
    """Read V1 flat JSON without altering the source file."""
    loaded = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(loaded, dict) or any(key not in loaded for key in FIELDS):
        raise ValueError('Dosya gerekli anamnez alanlarını içermiyor.')
    return {**loaded, **{key: str(loaded[key]) for key in FIELDS}}
