"""Persistent lower-left green download bar, updated only on Tk's thread."""
import tkinter as tk
from tkinter import ttk

class ModelDownloadProgress:
    def __init__(self,parent):
        self.frame=ttk.Frame(parent)
        self.frame.pack(side='left',padx=(12,8),pady=4)
        self.text=tk.StringVar(value='Model indirmesi bekleniyor')
        ttk.Label(self.frame,textvariable=self.text).pack(anchor='w')
        # Canvas guarantees green on Windows native themes, which ignore ttk colors.
        self.bar=tk.Canvas(self.frame,width=230,height=12,highlightthickness=1,
            highlightbackground='#b9c5bb',background='#e8eee9')
        self.bar.pack(anchor='w',pady=(3,0))
        self.fill=self.bar.create_rectangle(0,0,0,12,fill='#22a447',outline='')
        self.frame.pack_forget()
        self.model=None

    def update(self,event):
        self.model=event.model
        label=event.model if event.model.startswith('Yerel AI') else 'Whisper '+event.model
        if not self.frame.winfo_manager():
            siblings=self.frame.master.pack_slaves()
            placement={'before':siblings[0]} if siblings else {}
            self.frame.pack(side='left',padx=(12,8),pady=4,**placement)
        if event.phase=='downloading':
            percent=event.percent
            suffix=f'%{percent}' if percent is not None else 'boyut belirleniyor'
            self.text.set(f'{label} indiriliyor — {suffix}')
            self.bar.coords(self.fill,0,0,230*(percent or 0)/100,12)
        elif event.phase=='downloaded':
            self.bar.coords(self.fill,0,0,230,12)
            self.text.set(f'{label} — %100, model hazırlanıyor')
        elif event.phase in ('cached','loading'):
            if event.phase=='cached':self.bar.pack_forget()
            self.text.set(f'{label} — model hazırlanıyor')
        elif event.phase=='ready':
            self.text.set(f'{label} hazır')
        elif event.phase=='error':
            self.bar.coords(self.fill,0,0,0,12)
            self.bar.configure(background='#fbe9e7')
            self.text.set(f'{label} — indirme/yükleme tamamlanamadı')
        else:
            if not self.bar.winfo_manager():self.bar.pack(anchor='w',pady=(3,0))
            self.bar.coords(self.fill,0,0,0,12)
            self.text.set(f'{label} — indirme bilgisi alınıyor')

    def reset(self):
        self.bar.configure(background='#e8eee9')
        self.bar.coords(self.fill,0,0,0,12)
        self.frame.pack_forget()
