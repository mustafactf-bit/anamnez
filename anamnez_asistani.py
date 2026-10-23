"""Compatible launcher for the single unified application."""
from app import main
from clinical_notes import format_note, parse_dictation
from config import FIELDS, INITIAL_DATA, LABELS, RECOMMENDATIONS
from ui.main_window import AnamnezApp

if __name__ == "__main__":
    main()
