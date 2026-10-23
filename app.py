"""Unified desktop application entry point."""
import tkinter as tk
import logging
import sys
import json
from pathlib import Path
from ui.main_window import AnamnezApp

def main():
    if '--clinical-smoke' in sys.argv:
        from ai.clinical_smoke import run
        target=Path(sys.argv[sys.argv.index('--clinical-smoke')+1])
        try:
            result=run()
        except Exception as error:
            target.write_text(json.dumps({'local_gguf':False,'error_type':type(error).__name__}),encoding='utf-8')
            raise SystemExit(1)
        target.write_text(json.dumps(result),encoding='utf-8')
        return
    if '--model-smoke' in sys.argv:
        import traceback
        from speech.whisper_engine import WhisperEngine
        target=Path(sys.argv[sys.argv.index('--model-smoke')+1])
        engine=WhisperEngine()
        engine.on_progress=lambda event:None
        try:
            engine.load('small')
            import numpy as np
            engine.transcribe(np.zeros(16000,dtype=np.float32))
            result={'model_load':True,'silence_transcription':True}
        except Exception:
            result={'model_load':False,'error':traceback.format_exc()}
        finally:engine.unload()
        target.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        if not result['model_load']:raise SystemExit(1)
        return
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
    root = tk.Tk()
    if '--package-smoke' in sys.argv:
        root.withdraw()
    app = AnamnezApp(root)
    if '--package-smoke' in sys.argv:
        assert app.logo.width() == 96
        assert (Path(__file__).resolve().parent/'assets'/'kullanim-kilavuzu.html').is_file()
        import faster_whisper
        import ctranslate2
        import sounddevice
        import llama_cpp
        from faster_whisper.vad import get_vad_model
        from config import VERSION
        get_vad_model()
        root.update()
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            app.onboarding.path=Path(directory)/'ui-preferences.json'
            app.onboarding.first_run();root.update()
            assert app.onboarding.window is not None
            assert app._recording_stop is None and app.note_panel.approved is None
            app.onboarding.close();assert app.onboarding.seen()
        app.activity.begin('Paket arayüz testi')
        assert app.activity.bar.winfo_manager()=='pack'
        app.activity.finish();assert app.activity.heading.get()=='TAMAMLANDI'
        Path(sys.argv[sys.argv.index('--package-smoke')+1]).write_text(json.dumps(
            {'version':VERSION,'tk':True,'whisper':True,'vad':True,'llama_cpp':True,
             'sounddevice':True,'activity':True,'onboarding':True}),encoding='utf-8')
        root.destroy()
        return
    root.mainloop()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
