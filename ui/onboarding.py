"""Patient-free, optional first-run walkthrough; never starts clinical actions."""
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from storage.patient_storage import save_patient

STEPS=(
    ('Hoş geldiniz','Ana işiniz üç adım: dikteyi başlatın, bitirip taslağı inceleyin, onaylayıp kopyalayın. Bu tur hiçbir kayıt başlatmaz ve hasta bilgisi istemez.','output_tab'),
    ('İlk kullanım: modelleri hazırlayın','Whisper sesi yazıya çevirir; ayrı yerel AI ilgili hasta bilgilerini ayırır. İlk kullanımda indirme gerekebilir. Gerçek yüzde indirme çubuğunda görünür. Hazırlık sürerken hareketli gösterge çalışır.','settings_frame'),
    ('Konuşun, sonra kendiniz bitirin','Dikteyi başlatın. KAYIT AÇIK bilgisini görmeden konuşmayın. Konuşmanız bitince aynı düğmeden kaydı durdurun. Sessizlik kaydı durdurmaz. Geçen süre ve işlenen aşama üstte görünür.','output_tab'),
    ('Taslağı ve inceleme uyarılarını okuyun','İşlem bitince hasta bilgilerini, ilaç dozlarını ve “yok” gibi ifadeleri kontrol edin. İlgisiz konuşmalar ayıklanır; kime ait olduğu belirsiz bilgi için ek inceleme gerekir. AI kusursuz kabul edilmemelidir.','output_tab'),
    ('Onaylayın ve Miamed’e yapıştırın','Onayla ve kopyala ile tarihli metin panoya alınır. Miamed’de doğru hasta ve başvuruyu doğrulayın; önceki anamnezin sonuna Ctrl+V ile yapıştırıp Miamed’de kaydedin. Uygulama Miamed’e kendi başına yazmaz. F1 kılavuzu, F2 bu turu yeniden açar.','output_tab'),
)

class Onboarding:
    def __init__(self,app,path=None):
        self.app=app;self.window=None;self.index=0
        self.path=Path(path) if path else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AnamnezAsistani'/'ui-preferences.json'

    def seen(self):
        try:return json.loads(self.path.read_text(encoding='utf-8')).get('intro_v1_seen') is True
        except (OSError,ValueError,AttributeError):return False

    def first_run(self):
        if not self.seen():self.open()

    def open(self):
        if self.app.bridge.busy or self.app._recording_stop is not None:
            self.app.status.set('Turu açmadan önce devam eden işlemi bitirin.');return
        if self.window is not None and self.window.winfo_exists():self.window.lift();return
        self.index=0;self.window=tk.Toplevel(self.app.root)
        self.window.title('Anamnez Asistanı · Hızlı başlangıç')
        self.window.transient(self.app.root)
        root=self.app.root
        x=max(0,min(root.winfo_rootx()+(root.winfo_width()-700)//2,root.winfo_screenwidth()-720))
        y=max(0,min(root.winfo_rooty()+(root.winfo_height()-460)//2,root.winfo_screenheight()-510))
        self.window.geometry(f'700x460+{x}+{y}');self.window.minsize(600,420)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        outer=ttk.Frame(self.window,padding=24);outer.pack(fill='both',expand=True)
        self.counter=tk.StringVar();self.title=tk.StringVar();self.body=tk.StringVar()
        ttk.Label(outer,textvariable=self.counter,style='Badge.TLabel').pack(anchor='w')
        self.progress=ttk.Progressbar(outer,maximum=len(STEPS),mode='determinate')
        self.progress.pack(fill='x',pady=(12,18))
        ttk.Label(outer,textvariable=self.title,style='Section.TLabel',wraplength=630).pack(anchor='w',pady=(0,12))
        ttk.Label(outer,textvariable=self.body,wraplength=630,justify='left').pack(fill='x',anchor='w')
        bottom=ttk.Frame(outer);bottom.pack(side='bottom',fill='x')
        self.remember=tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom,text='Sonraki açılışlarda otomatik gösterme',variable=self.remember).pack(anchor='w',pady=10)
        buttons=ttk.Frame(bottom);buttons.pack(fill='x')
        ttk.Button(buttons,text='Şimdilik atla',command=self.close).pack(side='left')
        self.back=ttk.Button(buttons,text='Geri',command=lambda:self.move(-1))
        self.next=ttk.Button(buttons,text='İleri',style='Primary.TButton',command=lambda:self.move(1));self.next.pack(side='right')
        self.back.pack(side='right',padx=8)
        self.window.bind('<Escape>',lambda _e:self.close())
        self.render()

    def render(self):
        title,body,target=STEPS[self.index]
        self.counter.set(f'KULLANIM TURU  {self.index+1} / {len(STEPS)}')
        self.title.set(title);self.body.set(body);self.progress.configure(value=self.index+1)
        self.back.configure(state='normal' if self.index else 'disabled')
        self.next.configure(text='Kullanmaya başla' if self.index==len(STEPS)-1 else 'İleri')
        self.app.tabs.select(getattr(self.app,target,self.app.output_tab))

    def move(self,delta):
        if self.index+delta>=len(STEPS):self.close();return
        self.index=max(0,self.index+delta);self.render()

    def close(self):
        if self.window is None:return
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            save_patient(str(self.path),{'intro_v1_seen':bool(self.remember.get())})
        except OSError:self.app.status.set('Tur tercihi kaydedilemedi; sonraki açılışta yeniden görünebilir.')
        self.window.destroy();self.window=None
        self.app.tabs.select(self.app.output_tab)
