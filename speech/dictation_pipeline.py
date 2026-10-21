"""Stop-controlled recording → transcription → correction in one worker job."""
from dataclasses import dataclass
from ai.dictation_corrector import correct_transcript, CorrectionResult
from speech.audio_recorder import record_audio


@dataclass(frozen=True)
class ProcessedDictation:
    """Only the corrected candidate crosses to the UI in production."""
    correction: CorrectionResult
    input_overflow: bool = False
    reached_limit: bool = False
    test_raw: str = ''


def run_dictation(whisper, engine, settings, model_size, stop_event, on_started,
                  on_status, is_closed, recorder=record_audio) -> ProcessedDictation:
    """Never infer end-of-conversation from silence; physician sets stop_event."""
    try:
        if settings.low_memory:engine.unload()
        whisper.load(model_size)
        if stop_event.is_set() or is_closed():
            return ProcessedDictation(CorrectionResult(''))
        audio,overflow,limit=recorder(stop_event,on_started)
        if is_closed():return ProcessedDictation(CorrectionResult(''))
        on_status('Türkçe transkripsiyon yapılıyor...')
        try:transcript=whisper.transcribe(audio).strip()
        finally:audio=None
        if settings.low_memory:whisper.unload()
        if is_closed():return ProcessedDictation(CorrectionResult(''))
        on_status('Yerel yazım kontrolü ve anamnez hazırlanıyor...')
        if settings.local_correction:
            correction=correct_transcript(transcript,
                engine if settings.model_path and len(transcript)<=16000 else None)
        else:correction=CorrectionResult(transcript,mode='disabled')
        return ProcessedDictation(correction,overflow,limit,
                                  transcript if settings.test_mode else '')
    finally:
        if settings.low_memory or is_closed():whisper.unload()
