"""Optional first-time local GGUF setup; only public weights leave the network."""
import os
from pathlib import Path
from speech.model_download import stream_file, ByteProgress, ModelProgress

REPO='ggml-org/Qwen3-1.7B-GGUF'
REVISION='daeb8e2d528a760970442092f6bf1e55c3b659eb'
FILENAME='Qwen3-1.7B-Q4_K_M.gguf'
SIZE=1282439264
SHA256='d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5'

def default_model_path():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AnamnezAsistani'/'models'/'clinical'/FILENAME

def install_model(callback=lambda event:None):
    target=default_model_path();target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_file() and target.stat().st_size==SIZE:return str(target)
    def report(event):
        callback(ModelProgress(event.phase,'Yerel AI — Qwen3 1.7B',event.percent,event.downloaded,event.total))
    tracker=ByteProgress('Yerel AI',SIZE,0,report)
    stream_file(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{FILENAME}?download=true',
                target,SIZE,tracker.update,SHA256)
    report(ModelProgress('downloaded','Yerel AI',100,SIZE,SIZE))
    return str(target)
