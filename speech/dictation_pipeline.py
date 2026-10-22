"""Stop-controlled recording → transcription → correction in one worker job."""
from dataclasses import dataclass
from ai.dictation_corrector import correct_transcript, CorrectionResult
from speech.audio_recorder import record_audio
from ai.encounter_extractor import extract_encounter, EncounterExtraction


@dataclass(frozen=True)
class ProcessedDictation:
    """Only the corrected candidate crosses to the UI in production."""
    correction: CorrectionResult
    input_overflow: bool = False
    reached_limit: bool = False
    test_raw: str = ''
    extraction: EncounterExtraction | None = None
    structure_error: str = ''
    existing_source: bool = False


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
                engine if settings.model_path and not settings.structure_dictation and len(transcript)<=16000 else None)
        else:correction=CorrectionResult(transcript,mode='disabled')
        extraction=None;structure_error=''
        if settings.structure_dictation:
            on_status('Yerel AI hasta bilgilerini ayıklayıp alanlara yerleştiriyor...')
            try:
                if not settings.model_path:raise ValueError('missing model')
                extraction=extract_encounter(engine,correction.text)
            except Exception:
                structure_error='Yerel AI anamnezi güvenilir biçimde ayıklayamadı. Dikte ikincil sekmede tutuldu; son metni elle düzenleyip incelemeyi tamamlayın.'
            finally:
                if settings.low_memory:engine.unload()
        return ProcessedDictation(correction,overflow,limit,
                                  transcript if settings.test_mode else '',extraction,structure_error)
    finally:
        if settings.low_memory or is_closed():whisper.unload()
