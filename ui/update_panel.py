"""Nonblocking, explicit update flow independent of clinical workers."""
import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from config import VERSION, DISPLAY_VERSION
from distribution.updater import check_updates, download_update, launch_installer

class UpdatePanel:
    def __init__(self,app,frame):
        self.app=app; self.release=None; self.package=None; self.busy=False
        self.state=tk.StringVar(value=f'{DISPLAY_VERSION}. Güncellemeler açılışta otomatik kontrol edilir.')
        ttk.Label(frame,text='Uygulama güncellemeleri',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(frame,textvariable=self.state,wraplength=820).pack(anchor='w',pady=8)
        self.button=ttk.Button(frame,text='Güncellemeleri kontrol et',command=self.action)
        self.button.pack(anchor='w')
        self.progress=ttk.Progressbar(frame,mode='indeterminate',length=380)
        self.progress_text=tk.StringVar(value='')
        ttk.Label(frame,textvariable=self.progress_text).pack(anchor='w',pady=6)
        ttk.Label(frame,text='Kontrol yalnızca sürüm bilgisi alır. Görüşme metni gönderilmez. '
            'Kurulum siz başlatmadan çalışmaz. Önceki sürüm ve kullanıcı verileri korunur.',wraplength=820).pack(anchor='w',pady=8)
        if getattr(sys,'frozen',False) and '--package-smoke' not in sys.argv: app.root.after(2500,self.action)

    def task(self,work,done):
        self.busy=True;self.button.configure(state='disabled')
        self.progress.configure(mode='indeterminate');self.progress.pack(anchor='w',pady=8);self.progress.start(15)
        self.progress_text.set('İşlem sürüyor…')
        def worker():
            try: result=work(); error=False
            except Exception: result=None; error=True
            def finish():
                self.busy=False; self.button.configure(state='normal')
                self.progress.stop()
                if error:
                    self.progress.pack_forget();self.progress_text.set('Tamamlanamadı — yeniden deneyebilirsiniz.')
                    self.state.set('Güncelleme tamamlanamadı. Bağlantıyı kontrol edip yeniden deneyin; mevcut sürüm çalışmaya devam eder.')
                else:
                    self.progress.pack_forget();self.progress_text.set('İşlem tamamlandı.')
                    done(result)
            self.app.bridge.post(finish)
        threading.Thread(target=worker,daemon=True).start()

    def action(self):
        if self.busy:return
        if self.package is not None:
            if self.app.bridge.busy or self.app._recording_stop is not None:
                self.state.set('Kurulumdan önce devam eden işlemi bitirin.');return
            if not self.app._leave_visit(): return
            # The confirmation above runs a nested event loop; recheck active jobs.
            if self.app.bridge.busy or self.app._recording_stop is not None:return
            try: launch_installer(self.package,self.release)
            except Exception:
                self.package=None
                self.button.configure(text='Güncellemeyi yeniden indir')
                self.state.set('Kurulum başlatılamadı; mevcut sürüm açık tutuldu. Paketi yeniden indirebilirsiniz.');return
            self.app._close();return
        if self.release is not None:
            self.state.set('Güncelleme indiriliyor ve doğrulanıyor. Görüşmeye devam edebilirsiniz.')
            folder=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AnamnezAsistani'/'updates'
            def progress(done,total):
                self.app.bridge.post(lambda:self._download_progress(done,total))
            self.task(lambda:download_update(self.release,folder,progress),self.downloaded);return
        self.state.set('Yeni sürüm kontrol ediliyor…')
        self.task(lambda:check_updates(VERSION),self.checked)

    def checked(self,release):
        self.release=release
        if release:
            self.state.set(f'{release.version} hazır. İndirmek için düğmeye basın.')
            self.button.configure(text='Güncellemeyi indir')
            self.app.status.set(f'Yeni sürüm hazır: {release.version}. Güncelleme sekmesinden indirebilirsiniz.')
        else:self.state.set('Bu güncelleme kanalında daha yeni sürüm yok.')

    def downloaded(self,path):
        self.package=path
        self.state.set('Paket imzası ve dosya bütünlüğü doğrulandı. Görüşmenizi kaydedip kurulumu başlatın.')
        self.button.configure(text='Güncelle ve yeniden başlat')
        self.progress_text.set('%100 — paket doğrulandı, kurulum hazır.')

    def _download_progress(self,done,total):
        if not self.busy:return
        percent=min(99,int(done*100/total))
        self.progress.stop();self.progress.configure(mode='determinate',value=percent)
        self.progress_text.set(f'%{percent} — {done/1048576:.1f} / {total/1048576:.1f} MB' if done<total else 'İndirme bitti; dosya özeti doğrulanıyor…')
