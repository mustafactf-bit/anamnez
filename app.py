"""Unified desktop application entry point."""
import tkinter as tk
from ui.main_window import AnamnezApp

def main():
    root = tk.Tk()
    AnamnezApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
