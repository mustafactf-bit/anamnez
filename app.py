"""Unified desktop application entry point."""
import tkinter as tk
import logging
import sys
import json
from pathlib import Path
from ui.main_window import AnamnezApp

def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
    root = tk.Tk()
    if '--package-smoke' in sys.argv:
        root.withdraw()
    AnamnezApp(root)
    if '--package-smoke' in sys.argv:
        import faster_whisper
        import ctranslate2
        import sounddevice
        import llama_cpp
        from faster_whisper.vad import get_vad_model
        from config import VERSION
        get_vad_model()
        root.update()
        Path(sys.argv[sys.argv.index('--package-smoke')+1]).write_text(json.dumps(
            {'version':VERSION,'tk':True,'whisper':True,'vad':True,'llama_cpp':True,
             'sounddevice':True}),encoding='utf-8')
        root.destroy()
        return
    root.mainloop()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
