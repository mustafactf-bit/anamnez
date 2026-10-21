"""Unified desktop application entry point."""
import tkinter as tk
import logging
from ui.main_window import AnamnezApp

def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
    root = tk.Tk()
    AnamnezApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
