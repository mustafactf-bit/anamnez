"""CPU INT8 Turkish speech engine with explicit resource lifecycle."""

class WhisperEngine:
    """Preserves all V1 model options and decoding settings."""
    def __init__(self):
        self.model=None
        self.model_size=None

    def load(self,model_size: str) -> None:
        """Reuse a loaded model in fast mode."""
        if self.model is not None and model_size==self.model_size:return
        self.unload()
        from faster_whisper import WhisperModel
        self.model=WhisperModel(model_size,device='cpu',compute_type='int8')
        self.model_size=model_size

    def transcribe(self,audio) -> str:
        """Decode locally in Turkish."""
        segments,_=self.model.transcribe(audio,language='tr',task='transcribe',beam_size=5,vad_filter=True)
        return ' '.join(s.text.strip() for s in segments).strip()

    def unload(self) -> None:
        """Release references before LLM inference on low-memory systems."""
        self.model=None;self.model_size=None
