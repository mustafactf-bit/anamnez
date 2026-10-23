"""Visible operation lifecycle, real download progress and elapsed time."""
import time
import tkinter as tk
from tkinter import ttk

class ActivityPanel:
    def __init__(self,parent,status):
        self.frame=ttk.Frame(parent,padding=(14,8))
        self.frame.pack(fill='x',padx=10,pady=(0,8))
        self.status=status;self.busy=False;self.started=0;self.timer=None
        self.heading=tk.StringVar(value='HAZIR')
        self.elapsed=tk.StringVar(value='')
        self.title=ttk.Label(self.frame,textvariable=self.heading,style='Section.TLabel')
        self.title.pack(side='left',padx=(0,14))
        center=ttk.Frame(self.frame);center.pack(side='left',fill='x',expand=True)
        self.message=ttk.Label(center,textvariable=status,wraplength=730)
        self.message.pack(anchor='w')
        self.bar=ttk.Progressbar(center,mode='indeterminate',length=250)
        ttk.Label(self.frame,textvariable=self.elapsed,style='Subtitle.TLabel').pack(side='right',padx=(10,0))
        self.frame.bind('<Configure>',lambda e:self.message.configure(wraplength=max(300,e.width-240)))
        self.frame.bind('<Destroy>',lambda e:self.close() if e.widget==self.frame else None)
        self.trace=status.trace_add('write',self._status_changed)

    def _status_changed(self,*_):
        if self.busy:
            if self.status.get().startswith('Kayıt sürüyor'):
                self.heading.set('KAYIT AÇIK');self.title.configure(foreground='#a32020')
            elif self.heading.get()=='KAYIT AÇIK' and self.status.get().startswith(('Kayıt durduruldu','Türkçe transkripsiyon','Yerel yazım','Yerel AI')):
                self.heading.set('İŞLENİYOR');self.title.configure(foreground='#123454')
        else:
            self.elapsed.set('')
            text=self.status.get().lower()
            failed=any(word in text for word in ('başarısız','tamamlanamadı','kopyalanamadı','uygulanamadı','indirilemedi'))
            done=any(word in text for word in ('kaydedildi','kopyalandı','yüklendi','görüşme hazır','aktarıldı','inceleme tamamlandı','taslak yeniden hazırlandı'))
            self.heading.set('TAMAMLANAMADI' if failed else 'TAMAMLANDI' if done else 'BİLGİ')
            self.title.configure(foreground='#a32020' if failed else '#17633d' if done else '#123454')

    def begin(self,label=None):
        self.busy=True;self.started=time.monotonic()
        self.heading.set('İŞLENİYOR');self.title.configure(foreground='#123454')
        if label:self.status.set(label)
        self.bar.configure(mode='indeterminate');self.bar.pack(fill='x',pady=(5,0));self.bar.start(15)
        self._tick()

    def _tick(self):
        if not self.busy:return
        seconds=int(time.monotonic()-self.started)
        self.elapsed.set(f'Geçen süre  {seconds//60:02d}:{seconds%60:02d}')
        self.timer=self.frame.after(250,self._tick)

    def progress(self,event):
        if not self.busy:return
        if event.phase=='downloading' and event.percent is not None:
            self.bar.stop();self.bar.configure(mode='determinate',value=event.percent)
            self.heading.set(f'İNDİRİLİYOR %{event.percent}')
        elif event.phase in ('downloaded','loading','cached','checking','ready'):
            self.bar.stop();self.bar.configure(mode='indeterminate');self.bar.start(15)
            self.heading.set('HAZIRLANIYOR')

    def finish(self,error=False,review=False):
        seconds=int(time.monotonic()-self.started)
        self.busy=False;self.bar.stop();self.bar.pack_forget()
        if self.timer is not None:self.frame.after_cancel(self.timer);self.timer=None
        self.heading.set('TAMAMLANAMADI' if error else 'İNCELEME GEREKLİ' if review else 'TAMAMLANDI')
        self.title.configure(foreground='#a32020' if error else '#805600' if review else '#17633d')
        self.elapsed.set(f'{seconds//60:02d}:{seconds%60:02d}')

    def close(self):
        self.busy=False
        try:
            self.bar.stop()
            if self.timer is not None:self.frame.after_cancel(self.timer)
            self.status.trace_remove('write',self.trace)
        except tk.TclError:pass
        self.timer=None
