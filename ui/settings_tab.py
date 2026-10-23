"""Persistent local model and resource settings."""
from dataclasses import asdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from settings import Settings, save_settings
from ai.llm_engine import GGUFEngine
from literature.pubmed_client import PubMedClient

def build_settings_tab(app,frame):
    """Build configuration without depending on loaded native inference libraries."""
    values={}
    app.settings_values=values
    groups={}
    for row,(key,title) in enumerate((('models','Dikte ve yerel AI'),('resources','Gelişmiş · Bilgisayar kaynakları'),('literature','Gelişmiş · Literatür araması'),('testing','Test ve doğrulama'))):
        group=ttk.LabelFrame(frame,text=title,padding=12)
        group.grid(row=row,column=0,columnspan=3,sticky='ew',pady=(0,12))
        group.columnconfigure(1,weight=1)
        groups[key]=(group,0)
    labels={'model_path':'Yerel GGUF dosyası','context_size':'Bağlam boyutu','threads':'CPU iş parçacığı',
        'max_tokens':'En fazla çıktı tokenı','whisper_model':'Whisper modeli','low_memory':'Düşük RAM modu',
        'pubmed_retmax':'PubMed aday sayısı (20–50)','rerank_top_k':'Sıralama top-k',
        'synthesis_top_k':'Sentez top-k (1–10)','timeout':'Ağ zaman aşımı (sn)','retries':'Yeniden deneme',
        'cache_seconds':'Literatür önbelleği (sn)','debug_queries':'Gerçek arama sorgusunu göster',
        'local_correction':'Yerel yazım kontrolü',
        'structure_dictation':'Yerel AI ile ilgisiz konuşmaları ayır ve anamnez alanlarını doldur',
        'test_mode':'TEST MODU — ham metin saklanabilir (sentetik/izinli veri)'}
    for row,(key,value) in enumerate(asdict(app.settings).items()):
        group_key=('models' if key in ('model_path','whisper_model','structure_dictation','local_correction') else
                   'resources' if key in ('context_size','threads','max_tokens','low_memory') else
                   'testing' if key=='test_mode' else 'literature')
        group,row=groups[group_key];groups[group_key]=(group,row+1)
        ttk.Label(group,text=labels[key],wraplength=430).grid(row=row,column=0,sticky='w',pady=6)
        variable=tk.BooleanVar(value=value) if type(value) is bool else tk.StringVar(value=str(value))
        values[key]=variable
        if type(value) is bool:widget=ttk.Checkbutton(group,variable=variable)
        elif key=='whisper_model':widget=ttk.Combobox(group,textvariable=variable,values=('small','medium','large-v3','turbo'),state='readonly')
        else:widget=ttk.Entry(group,textvariable=variable,width=40)
        widget.grid(row=row,column=1,sticky='ew',padx=8)
        if key=='model_path':ttk.Button(group,text='Dosya seç',command=lambda:values['model_path'].set(filedialog.askopenfilename(filetypes=[('GGUF modeli','*.gguf')]))).grid(row=row,column=2)
    def save():
        if app.bridge.busy:
            app.status.set('Ayarları değiştirmeden önce işlemin bitmesini bekleyin.');return
        try:
            data={key:(var.get() if isinstance(getattr(app.settings,key),(bool,str)) else int(var.get())) for key,var in values.items()}
            settings=Settings(**data).validate();save_settings(settings)
        except (ValueError,OSError):
            messagebox.showerror('Ayarlar','Ayar değerlerini ve kayıt iznini kontrol edin.');return
        def work():
            app.engine.unload();app.speech_engine.unload()
        def done(_):
            was_test_mode=app.settings.test_mode
            app.settings=settings;app.engine=GGUFEngine(settings);app.pubmed=PubMedClient(settings)
            if was_test_mode and not settings.test_mode:
                app._discard_raw_after_approval()
            app.note_panel.update_mode_notice()
            app.whisper_model.set(settings.whisper_model)
            app.status.set('Ayarlar kaydedildi.')
        app.bridge.start(work,done,lambda _:messagebox.showerror('Ayarlar','Model kaynakları serbest bırakılamadı.'))
    ttk.Button(frame,text='Ayarları kaydet',style='Primary.TButton',command=save).grid(row=4,column=1,sticky='e',pady=10)
    ttk.Button(frame,text='Yerel anamnez AI modelini indir (ilk kurulum)',command=app._install_clinical_model).grid(row=5,column=1,sticky='e',pady=6)
    frame.columnconfigure(1,weight=1)
