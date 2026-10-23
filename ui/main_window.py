import datetime
import json
import re
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


from config import FIELDS, INITIAL_DATA, RECOMMENDATIONS
from clinical_notes import format_note, parse_dictation
from literature.legacy import fetch_pubmed_references
from storage.patient_storage import save_patient, load_patient
from storage.record_policy import prepare_record, without_legacy_raw
from speech.dictation_pipeline import run_dictation
from note_workflow import build_note_body
from settings import load_settings, save_settings, Settings
from ai.llm_engine import GGUFEngine
from literature.pubmed_client import PubMedClient
from speech.whisper_engine import WhisperEngine
from speech.errors import SpeechModelError
from speech.audio_recorder import record_audio
from ui.worker import WorkerBridge
from ui.note_panel import NotePanel
from ui.clipboard import create_clipboard, ClipboardError
from ui.clinical_assistant_tab import ClinicalAssistantTab
from ui.settings_tab import build_settings_tab
from ui.update_panel import UpdatePanel
from ui.model_progress import ModelDownloadProgress
from ai.encounter_extractor import extract_encounter
from ai.dictation_corrector import CorrectionResult
from speech.dictation_pipeline import ProcessedDictation
from ui.design import apply_design, wheel_scroll

class AnamnezApp:
    def __init__(self, root):
        self.root = root
        apply_design(root)
        self.root.title("Anamnez Asistanı V2-alpha1.4")
        self.root.geometry(f"{min(1180,root.winfo_screenwidth()-60)}x{min(850,root.winfo_screenheight()-90)}")
        self.root.minsize(960, 640)
        self.values = dict(INITIAL_DATA)
        self.entries = {}
        self.entry_variables = {}
        self._dictation_applied = ''
        self._test_raw_transcript = ''
        self.clipboard = create_clipboard(root)
        self.reference_ids = []
        self._processing_dictation = False
        self._review_pending = False
        self._speech_context = None
        self._suppress_source_changes = False
        self._recording = False
        self._recording_stop = None
        self.bridge = WorkerBridge(root)
        self._settings_error = False
        try:
            self.settings = load_settings()
        except (OSError, ValueError, TypeError):
            self.settings = Settings()
            self._settings_error = True
        self.engine = GGUFEngine(self.settings)
        self.speech_engine = WhisperEngine()
        self.pubmed = PubMedClient(self.settings)
        self.root.protocol('WM_DELETE_WINDOW', self._close)
        self._build_ui()
        if self._settings_error:
            self.status.set('Ayar dosyası okunamadı; varsayılanlar kullanılıyor. Ayarları kontrol edin.')

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=(12, 10))
        header.pack(fill="x")
        assets=Path(__file__).resolve().parents[1]/'assets'
        self.logo=tk.PhotoImage(file=str(assets/'logo-header.png'))
        self.window_icon=tk.PhotoImage(file=str(assets/'logo-icon.png'))
        self.root.iconphoto(True,self.window_icon)
        ttk.Label(header,image=self.logo).pack(side='left',padx=(0,12))
        header_text=ttk.Frame(header);header_text.pack(side='left',fill='x',expand=True)
        ttk.Label(header_text, text="Anamnez Asistanı",style='Title.TLabel').pack(anchor="w")
        ttk.Label(
            header_text,
            text="Konuşun. İnceleyin. Onaylayıp kopyalayın.",style='Subtitle.TLabel',
            wraplength=650,
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(header_text,text='Yerel dikte ve AI  •  Son karar hekimde',style='Badge.TLabel').pack(anchor='w',pady=(8,0))
        ttk.Button(header,text='Kullanım kılavuzu  ·  F1',command=self._open_guide).pack(side='right',padx=(8,0))

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.form_tab = ttk.Frame(self.tabs, padding=8)
        self.dictation_tab = ttk.Frame(self.tabs, padding=8)
        self.recommendations_tab = ttk.Frame(self.tabs, padding=8)
        self.output_tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(self.output_tab, text="Anamnez • Miamed")
        self.tabs.add(self.dictation_tab, text="Dikte metni")
        self.tabs.add(self.form_tab, text="Hasta bilgileri")
        self.tabs.add(self.recommendations_tab, text="Değerlendirme")
        self._build_form()
        self._build_dictation()
        self._build_recommendations()
        self._build_output()
        clinical_frame = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(clinical_frame, text='Klinik Asistan')
        self.clinical = ClinicalAssistantTab(self, clinical_frame)
        settings_frame = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(settings_frame, text='Ayarlar')
        settings_canvas = tk.Canvas(settings_frame, highlightthickness=0)
        settings_scroll = ttk.Scrollbar(settings_frame, orient='vertical', command=settings_canvas.yview)
        settings_container = ttk.Frame(settings_canvas, padding=8)
        settings_window = settings_canvas.create_window((0,0), window=settings_container, anchor='nw')
        settings_container.bind('<Configure>', lambda _e: settings_canvas.configure(scrollregion=settings_canvas.bbox('all')))
        settings_canvas.bind('<Configure>', lambda e: settings_canvas.itemconfigure(settings_window, width=e.width))
        settings_canvas.configure(yscrollcommand=settings_scroll.set)
        settings_canvas.pack(side='left', fill='both', expand=True)
        settings_scroll.pack(side='right', fill='y')
        build_settings_tab(self, settings_container)
        wheel_scroll(settings_canvas)
        update_frame = ttk.Frame(self.tabs,padding=16)
        self.tabs.add(update_frame,text='Güncelleme')
        self.updates = UpdatePanel(self,update_frame)
        self.dictation_text.bind('<<Modified>>', self._transcript_changed)
        for variable in self.entry_variables.values():
            variable.trace_add('write', lambda *_: None if self._suppress_source_changes else self.note_panel.source_changed())
        self.status = tk.StringVar(value="Hazır.")
        footer=ttk.Frame(self.root)
        footer.pack(fill='x')
        self.model_progress=ModelDownloadProgress(footer)
        ttk.Label(footer, textvariable=self.status, anchor="w", padding=(12, 4),wraplength=700).pack(side='left',fill="x",expand=True)
        self.speech_engine.on_progress=lambda event:self.bridge.post(lambda:self.model_progress.update(event))
        def focus_draft(_event=None):
            self.tabs.select(self.output_tab);self.note_panel.editor.focus_set();return 'break'
        def next_tab(_event=None):
            self.tabs.select((self.tabs.index('current')+1)%len(self.tabs.tabs()));return 'break'
        shortcuts={'<F1>':lambda _e:(self._open_guide(),'break')[-1],
                   '<F6>':focus_draft,'<Control-Tab>':next_tab,
                   '<Control-n>':lambda _e:(self._new_visit(),'break')[-1],
                   '<Control-o>':lambda _e:(self._load_json(),'break')[-1]}
        for key,command in shortcuts.items():self.root.bind(key,command)
        def text_shortcuts(widget):
            if isinstance(widget,tk.Text):
                for key,command in shortcuts.items():widget.bind(key,command)
                widget.bind('<Tab>',lambda e:(e.widget.tk_focusNext().focus_set(),'break')[-1])
                widget.bind('<Shift-Tab>',lambda e:(e.widget.tk_focusPrev().focus_set(),'break')[-1])
                widget.bind('<ISO_Left_Tab>',lambda e:(e.widget.tk_focusPrev().focus_set(),'break')[-1])
            for child in widget.winfo_children():text_shortcuts(child)
        text_shortcuts(self.root)

    def _open_guide(self):
        guide=Path(__file__).resolve().parents[1]/'assets'/'kullanim-kilavuzu.html'
        if not webbrowser.open(guide.as_uri()):
            messagebox.showinfo('Kullanım kılavuzu',f'Kılavuz dosyasını tarayıcınızda açın:\n{guide}')

    def _build_form(self):
        canvas = tk.Canvas(self.form_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.form_tab, orient="vertical", command=canvas.yview)
        container = ttk.Frame(canvas, padding=8)
        container.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        form_window=canvas.create_window((0, 0), window=container, anchor="nw")
        canvas.bind('<Configure>',lambda event:canvas.itemconfigure(form_window,width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for row, (key, label) in enumerate(FIELDS.items()):
            ttk.Label(container, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
            variable = tk.StringVar(value=self.values[key])
            self.entry_variables[key] = variable
            entry = ttk.Entry(container, width=92, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            self.entries[key] = entry
        container.columnconfigure(1, weight=1)
        wheel_scroll(canvas)
        ttk.Button(container, text="Değişiklikleri uygula", command=self._read_form).grid(
            row=len(FIELDS), column=1, sticky="e", pady=10
        )

    def _build_dictation(self):
        ttk.Label(
            self.dictation_tab,
            text="Türkçe konuşmayı yerel Whisper modeliyle yazıya çevirebilir veya metni kendiniz girebilirsiniz. Ses kaydedilmez ya da bir sunucuya gönderilmez.",
            wraplength=950,
        ).pack(anchor="w", pady=(0, 8))
        controls = ttk.Frame(self.dictation_tab)
        controls.pack(fill="x", pady=(0, 8))
        self.whisper_model = tk.StringVar(value=self.settings.whisper_model)
        ttk.Label(controls, text="Whisper modeli:").pack(side="left")
        self.whisper_model_choice = ttk.Combobox(
            controls,
            textvariable=self.whisper_model,
            values=("small", "medium", "large-v3", "turbo"),
            state="readonly",
            width=13,
        )
        self.whisper_model_choice.pack(side="left", padx=(6, 12))
        self.record_button = ttk.Button(
            controls, text="1. Dikteyi başlat", command=self._toggle_microphone_recording
        )
        self.record_button.pack(side="left")
        ttk.Label(
            controls,
            text="Small hızlıdır; medium ve büyük modeller daha ağır olabilir. Türkçe doğruluğunu kendi sesinizle kontrol edin.",
            wraplength=590,
        ).pack(side="left", padx=10)
        self.dictation_text = tk.Text(self.dictation_tab, wrap="word", height=22)
        self.dictation_text.pack(fill="both", expand=True)
        buttons = ttk.Frame(self.dictation_tab)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Miamed taslağını hazırla", command=self._prepare_miamed).pack(side="left", padx=(0,8))
        ttk.Button(buttons, text="Dikteyi alanlara aktar", command=self._apply_dictation).pack(side="left")
        ttk.Button(buttons, text="Dikte alanını temizle", command=lambda: self.dictation_text.delete("1.0", "end")).pack(
            side="left", padx=8
        )
        ttk.Label(
            self.dictation_tab,
            text="Etiketsiz cümleler şikâyet alanına eklenir. Fizik muayene dâhil diğer alanlar yalnızca etiketli ve dolu bilgi varsa değişir; boş/eksik muayene alanları korunur. Sesli dikte ilk kullanımda seçili Whisper modelini internetten indirir; sesin kendisi bilgisayarda işlenir.",
            wraplength=950,
        ).pack(anchor="w", pady=(8, 0))

    def _toggle_microphone_recording(self):
        if self._recording:
            self._recording = False
            self._set_record_controls('Metin hazırlanıyor...', 'disabled')
            self.status.set("Kayıt durduruldu; Türkçe ses yazıya çevriliyor...")
            if self._recording_stop:
                self._recording_stop.set()
            return
        if self.bridge.busy:
            self.status.set('Devam eden işlemin bitmesini bekleyin.')
            return
        if self._review_pending:
            self.status.set('Önce inceleme bekleyen konuşmaları değerlendirin.');return
        if not self._clinical_model_ready():return
        model_size = self.whisper_model.get()
        if model_size not in ("small", "medium", "large-v3", "turbo"):
            messagebox.showerror("Whisper modeli", "Listeden geçerli bir Whisper modeli seçin.")
            return
        self._speech_context = (self.note_panel.sources(), self.note_panel.body())
        self.model_progress.reset()
        self._processing_dictation = True
        self._recording = True
        self.note_panel.invalidate('Yeni dikte başladı. Kayıt ve transkripsiyondan sonra taslağı güncelleyip onaylayın.')
        self._recording_stop = threading.Event()
        self._set_record_controls('Whisper hazırlanıyor...', 'disabled')
        self.status.set(
            f"Whisper {model_size} hazırlanıyor. İlk kullanımda model indirilir; indirme tamamlanınca kayıt başlayacak."
        )
        stop_event = self._recording_stop
        self.bridge.start(
            lambda: self._record_and_transcribe(model_size, stop_event),
            self._microphone_transcription_finished,
            self._microphone_error,
        )

    def _clinical_model_ready(self):
        if not self.settings.structure_dictation:return True
        if self.settings.model_path and Path(self.settings.model_path).is_file():return True
        from ai.model_setup import default_model_path, SIZE
        cached=default_model_path()
        if not self.settings.model_path and cached.is_file() and cached.stat().st_size==SIZE:
            self.settings.model_path=str(cached)
            self.engine=GGUFEngine(self.settings)
            if hasattr(self,'settings_values'):self.settings_values['model_path'].set(str(cached))
            try:save_settings(self.settings)
            except OSError:pass
            return True
        if messagebox.askyesno('Yerel anamnez AI ilk kurulumu',
                'Anamnez ayıklama için Whisper’dan ayrı bir yerel dil modeli gerekir. '
                'Qwen3 1.7B modeli yaklaşık 1,3 GB indirilir ve bilgisayarınızda çalışır. '
                'Hasta konuşması internete gönderilmez. Şimdi indirilsin mi?'):
            self._install_clinical_model()
        return False

    def _install_clinical_model(self):
        if self.bridge.busy:
            self.status.set('Önce devam eden işlemin bitmesini bekleyin.');return
        from ai.model_setup import install_model
        self.model_progress.reset()
        self.status.set('Yerel anamnez AI modeli indiriliyor; bu yalnızca ilk kurulumdur.')
        def progress(event):self.bridge.post(lambda:self.model_progress.update(event))
        def done(path):
            self.settings.model_path=path
            try:save_settings(self.settings)
            except OSError:
                self.status.set('Model indirildi; ayarlar kaydedilemedi. Ayarlar’dan dosyayı seçin.');return
            self.engine=GGUFEngine(self.settings)
            if hasattr(self,'settings_values'):self.settings_values['model_path'].set(path)
            self.status.set('Yerel AI hazır. Dikteyi başlatabilirsiniz.')
        self.bridge.start(lambda:install_model(progress),done,
            self._clinical_model_install_failed)

    def _clinical_model_install_failed(self,_):
        from speech.model_download import ModelProgress
        self.model_progress.update(ModelProgress('error','Yerel AI'))
        self.status.set('Yerel AI modeli indirilemedi. Bağlantı/disk alanını kontrol edip Ayarlar’dan yeniden deneyin.')

    def _structure_manual_dictation(self,text):
        if self.bridge.busy or self._review_pending:return False
        if not self._clinical_model_ready():return False
        self._speech_context=(self.note_panel.sources(),self.note_panel.body())
        self._processing_dictation=True;self.note_panel.invalidate('Yerel AI anamnezi ayıklıyor...')
        def work():
            try:
                if self.settings.low_memory:self.speech_engine.unload()
                extraction=extract_encounter(self.engine,text)
                return ProcessedDictation(CorrectionResult(text),extraction=extraction,existing_source=True)
            except Exception:
                return ProcessedDictation(CorrectionResult(text),structure_error='Yerel AI ayıklaması tamamlanamadı; metni inceleyin.',existing_source=True)
            finally:
                self.engine.unload()
        return self.bridge.start(work,self._microphone_transcription_finished,self._microphone_error)

    def _record_and_transcribe(self, model_size, stop_event):
        return run_dictation(self.speech_engine, self.engine, self.settings,
            model_size, stop_event,
            lambda: self.bridge.post(self._microphone_recording_started),
            lambda text: self.bridge.post(lambda: self.status.set(text)),
            lambda: self.bridge.closed, recorder=record_audio)

    def _set_record_controls(self, text, state):
        self.record_button.configure(text=text, state=state)
        self.note_panel.record_button.configure(text=text, state=state)

    def _microphone_recording_started(self):
        self._set_record_controls('2. Dikteyi bitir', 'normal')
        self.status.set('Kayıt sürüyor. Sessizlik kaydı bitirmez; konuşmanız bitince Dikteyi bitir düğmesine basın.')

    def _microphone_transcription_finished(self, result):
        context = self._speech_context
        unchanged = context is None or context == (self.note_panel.sources(), self.note_panel.body())
        self._speech_context = None
        self._recording = False
        self._recording_stop = None
        self._processing_dictation = False
        self._set_record_controls('1. Dikteyi başlat', 'normal')
        transcript = result.correction.text
        if not transcript:
            self.note_panel.state.set('Konuşma algılanmadı. Mikrofonu kontrol edip yeniden deneyin.')
            self.note_panel.update_actions()
            self.status.set('Anamneze yeni metin eklenmedi.')
            return
        existing = self.dictation_text.get('1.0','end-1c').strip()
        combined = transcript if result.existing_source else existing + ('\n' if existing else '') + transcript
        self.dictation_text.delete('1.0','end')
        self.dictation_text.insert('1.0', combined)
        self.dictation_text.edit_modified(False)
        self.clinical.invalidate()
        if self.settings.test_mode:
            self._test_raw_transcript += ('\n' if self._test_raw_transcript else '') + result.test_raw
        else:
            self._test_raw_transcript = ''
        if not unchanged:
            self.note_panel.source_changed()
            self.status.set('İşlem sırasında metin/alanlar değişti. Yeni dikte ikincil sekmede korundu; taslağı kontrol ederek yenileyin.')
            return
        self._read_form()
        base = context[1] if context else self.note_panel.body()
        if self.settings.structure_dictation:
            waiting=[];accepted={}
            if result.extraction is not None:
                waiting=list(result.extraction.review)
                for field,value in result.extraction.fields.items():
                    current=self.values.get(field,'').strip()
                    if current and current!=value:
                        waiting.append(f'{FIELDS[field]} alanında mevcut bilgi var. Yeni kaynak: {value}')
                    elif not current:
                        accepted[field]=value
                self._suppress_source_changes=True
                try:
                    for field,value in accepted.items():
                        self.values[field]=value;self.entry_variables[field].set(value)
                finally:self._suppress_source_changes=False
                new_body=build_note_body(accepted) if base else build_note_body(self.values)
                self.note_panel._set_body(base+('\n\nEK ANAMNEZ:\n'+new_body if new_body else '') if base else new_body)
                self._dictation_applied=combined
                self.note_panel.set_selection_details(waiting,result.extraction.excluded)
            else:
                waiting=[result.structure_error or 'Anamnez ayıklaması doğrulanamadı.',combined]
                self.note_panel._set_body(base)
                self.note_panel.set_selection_details(waiting,())
            self._review_pending=bool(waiting)
            self.note_panel.update_actions()
            self.note_panel.state.set('Yerel AI ilgili kaynak bilgilerini anamnez alanlarına yerleştirdi. '
                +('İnceleme bekleyen bölümleri değerlendirin.' if waiting else 'Alanları ve son metni kontrol edip onaylayın.'))
            self.status.set('Anamnez ayıklandı; ilgisiz konuşmalar son metne eklenmedi.' if result.extraction else 'Yerel AI tamamlanamadı; ham konuşma otomatik anamneze eklenmedi.')
            self.tabs.select(self.output_tab)
            return
        if not base:
            self.note_panel._set_body(build_note_body(self.values, combined))
        else:
            self.note_panel._set_body(base + '\n\nGÖRÜŞME NOTU:\n' + transcript)
        warnings = [result.correction.warning] if result.correction.warning else []
        if result.input_overflow:
            warnings.append('Mikrofon tamponu taştı; eksik ses olabilir.')
        if result.reached_limit:
            warnings.append('15 dakikalık kayıt sınırına ulaşıldı.')
        mode = 'Yerel AI yazım kontrolü' if result.correction.mode == 'local_model' else 'Sözlük yazım kontrolü' if result.correction.mode != 'disabled' else 'Yazım kontrolü kapalı'
        self.note_panel.state.set(mode + ' tamamlandı. Son metni inceleyip onaylayın.' + (' ' + ' '.join(warnings) if warnings else ''))
        self.note_panel.update_actions()
        self.tabs.select(self.output_tab)
        self.status.set('Anamnez hazır. 3. adım: Onayla ve aktar (şimdilik panoya).')

    def _microphone_error(self, error, missing_dependency=False):
        self._recording = False
        self._processing_dictation = False
        self._speech_context = None
        self._set_record_controls('1. Dikteyi başlat', 'normal')
        self._recording_stop = None
        self.note_panel.state.set('Dikte tamamlanamadı; mevcut metin korundu.')
        self.note_panel.update_actions()
        self.status.set("Mikrofon diktesi başarısız oldu.")
        if isinstance(error,SpeechModelError):
            self.status.set(f'Whisper modeli hazırlanamadı. Hata kodu: {error.code}')
            messagebox.showerror('Whisper modeli hazırlanamadı',f'{error.message}\n\nHata kodu: {error.code}')
            return
        if missing_dependency:
            messagebox.showerror(
                "Whisper bileşenleri kurulu değil",
                "Dikte için gereken yerel bileşenler bulunamadı. Uygulama klasöründeki "
                "'WhisperKurulum.vbs' dosyasına çift tıklayıp kurulumu tamamlayın.\n\n"
                "Kurulumu tamamlayıp yeniden deneyin.",
            )
        else:
            messagebox.showerror(
                "Dikte başarısız oldu",
                "Mikrofon kaydı veya Whisper çözümlemesi tamamlanamadı.\n\n"
                "Mikrofon iznini, internet bağlantısını (model ilk indirme için) ve seçili modeli kontrol edin.",
            )

    def _build_recommendations(self):
        top = ttk.Frame(self.recommendations_tab)
        top.pack(fill="x")
        ttk.Label(
            top,
            text="Aşağıdakiler tanı veya tedavi değildir; klinisyen değerlendirmesi için genel başlıklardır. Beş başlık için PubMed kayıtları çevrimiçi aranır.",
            wraplength=900,
        ).pack(side="left", fill="x", expand=True)
        self.search_button = ttk.Button(top, text="PubMed kaynaklarını getir", command=self._start_reference_search)
        self.search_button.pack(side="right", padx=(8, 0))
        self.recommendation_text = tk.Text(self.recommendations_tab, wrap="word", height=27)
        self.recommendation_text.pack(fill="both", expand=True, pady=(10, 0))
        self._render_recommendations(None, None)

    def _render_recommendations(self, id_sets, summaries):
        self.recommendation_text.configure(state="normal")
        self.recommendation_text.delete("1.0", "end")
        for index, (title, explanation, query) in enumerate(RECOMMENDATIONS):
            self.recommendation_text.insert("end", f"{index + 1}. {title}\n", "title")
            self.recommendation_text.insert("end", explanation + "\n")
            scholar_url = "https://scholar.google.com/scholar?" + urllib.parse.urlencode({"q": query})
            self.recommendation_text.insert("end", "Google Scholar: " + scholar_url + "\n")
            if id_sets is None:
                self.recommendation_text.insert("end", "PubMed: Kaynakları getirmek için üstteki düğmeye basın.\n\n")
            elif index < len(id_sets) and id_sets[index]:
                self.recommendation_text.insert("end", "PubMed kaynakları:\n")
                for uid in id_sets[index][:3]:
                    citation = summaries.get(uid)
                    if citation:
                        details = " — ".join(
                            part for part in (citation["authors"], citation["journal"], citation["year"]) if part
                        )
                        self.recommendation_text.insert(
                            "end",
                            f"• {citation['title']}" + (f" ({details})" if details else "") + "\n"
                            f"  https://pubmed.ncbi.nlm.nih.gov/{uid}/\n",
                        )
                    else:
                        self.recommendation_text.insert(
                            "end", f"• https://pubmed.ncbi.nlm.nih.gov/{uid}/\n"
                        )
                self.reference_ids.extend(id_sets[index][:3])
            else:
                self.recommendation_text.insert(
                    "end",
                    "PubMed: Eşleşen kayıt bulunamadı. "
                    + "https://pubmed.ncbi.nlm.nih.gov/?"
                    + urllib.parse.urlencode({"term": query})
                    + "\n",
                )
            self.recommendation_text.insert("end", "\n")
        self.recommendation_text.tag_configure("title", font=("Segoe UI", 10, "bold"))
        self.recommendation_text.configure(state="disabled")

    def _build_output(self):
        self.note_panel = NotePanel(self, self.output_tab)

    def _prepare_miamed(self):
        if self.note_panel.prepare():
            self.tabs.select(self.output_tab)

    def _read_form(self):
        for key, entry in self.entries.items():
            self.values[key] = entry.get().strip()

    def _sync_form(self):
        for key, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, self.values[key])

    def _apply_dictation(self):
        text = self.dictation_text.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Dikte metni", "Önce dikte metnini yapıştırın.")
            return
        if self.settings.structure_dictation:
            return self._structure_manual_dictation(text)
        if text == self._dictation_applied:
            self.status.set('Bu dikte zaten alanlara aktarıldı; tekrar eklenmedi.')
            return
        self._read_form()
        updated = parse_dictation(text, self.values)
        self._dictation_applied = text
        self._sync_form()
        self._refresh_output()
        self.status.set("Güncellenen alanlar: " + ", ".join(dict.fromkeys(updated)))
        self.tabs.select(self.form_tab)

    def _refresh_output(self):
        return self.note_panel.prepare()

    def _copy_output(self):
        return self.note_panel.complete()

    def _save_output(self):
        if not self.settings.test_mode and not self.note_panel.current_approval():
            self.status.set('Kaydetmeden önce son metni onaylayın.')
            return
        path = filedialog.asksaveasfilename(
            title="Anamnez metnini kaydet",
            defaultextension=".txt",
            filetypes=[("Metin dosyası", "*.txt"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            if not self.settings.test_mode and not self.note_panel.current_approval():
                self.status.set('Metin değişti. Kaydetmeden önce yeniden onaylayın.')
                return
            try:
                Path(path).write_text(self.note_panel.export_text(), encoding="utf-8")
            except OSError:
                messagebox.showerror('Kayıt', 'Metin kaydedilemedi. Konumu ve yazma iznini kontrol edin.')
                return
            self.status.set("Anamnez metni kaydedildi: " + path)

    def _save_json(self):
        if not self.settings.test_mode and not self.note_panel.current_approval():
            self.status.set('Kaydetmeden önce son metni onaylayın.')
            return
        self._read_form()
        path = filedialog.asksaveasfilename(
            title="Hasta verisini kaydet",
            defaultextension=".json",
            filetypes=[("JSON dosyası", "*.json"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            if not self.settings.test_mode and not self.note_panel.current_approval():
                self.status.set('Metin değişti. Kaydetmeden önce yeniden onaylayın.')
                return
            try:
                save_patient(path, prepare_record(self.values, self.note_panel.snapshot(),
                    test_mode=self.settings.test_mode, raw_transcript=self._test_raw_transcript))
            except (OSError, ValueError):
                messagebox.showerror('Kayıt', 'Dosya kaydedilemedi. Konumu ve yazma iznini kontrol edin.')
                return
            self.status.set("Hasta verisi kaydedildi: " + path)

    def _load_json(self):
        if self._recording_stop is not None:
            self.status.set('Önce mikrofon kaydının ve transkripsiyonun bitmesini bekleyin.')
            return
        path = filedialog.askopenfilename(
            title="Hasta verisini aç", filetypes=[("JSON dosyası", "*.json"), ("Tüm dosyalar", "*.*")]
        )
        if not path:
            return
        try:
            loaded = load_patient(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showerror("Dosya açılamadı", str(error))
            return
        if not self._leave_visit():
            return
        self._review_pending=False
        self.note_panel.clear_selection_details()
        if self.settings.test_mode:
            self.values = loaded
            saved_note = loaded.get('_note_draft')
            test_data = loaded.get('_test_data')
            raw = test_data.get('raw_transcript', '') if isinstance(test_data, dict) else ''
            self._test_raw_transcript = raw if isinstance(raw, str) else ''
        else:
            self.values, saved_note = without_legacy_raw(loaded)
            self._test_raw_transcript = ''
        self.dictation_text.delete('1.0','end')
        if self.settings.test_mode and isinstance(saved_note, dict):
            transcript = saved_note.get('transcript', '')
            applied = saved_note.get('dictation_applied', '')
            if isinstance(transcript, str) and len(transcript) <= 1_000_000:
                self.dictation_text.insert('1.0', transcript)
            self._dictation_applied = applied if isinstance(applied, str) else ''
        else:
            self._dictation_applied = ''
        self.dictation_text.edit_modified(False)
        self.clinical.invalidate()
        extension = self.values.get('_v2')
        if isinstance(extension, dict):
            from safety.output_validator import clinical_schema
            try:
                restored = clinical_schema(extension.get('structured_anamnesis'))
            except ValueError:
                pass
            else:
                self.clinical.structured = restored
                self.clinical._display(self.clinical.facts, json.dumps(restored,ensure_ascii=False,indent=2))
        self._sync_form()
        self.note_panel.restore(saved_note)
        self.status.set("Hasta verisi yüklendi. Metni kontrol edip yeniden onaylayın.")

    def _start_reference_search(self):
        if self.bridge.busy:
            self.status.set('Devam eden işlemin bitmesini bekleyin.')
            return
        self.search_button.configure(state='disabled')
        self.status.set('PubMed kaynakları aranıyor...')
        self.bridge.start(lambda: fetch_pubmed_references(RECOMMENDATIONS),
            lambda result: self._reference_success(*result), self._reference_error)

    def _close(self):
        if self._recording_stop:
            self._recording_stop.set()
        self._test_raw_transcript = ''
        self._speech_context = None
        self.dictation_text.delete('1.0','end')
        self.dictation_text.edit_reset()
        self._dictation_applied = ''
        self.note_panel.clear_selection_details()
        self.bridge.close()
        # Native inference cannot be safely interrupted; daemon jobs finish or exit
        # with the process, without posting callbacks to the destroyed window.
        self.root.destroy()

    def _transcript_changed(self, _event=None):
        if self.dictation_text.edit_modified():
            self.clinical.invalidate()
            if not self._suppress_source_changes:
                self.note_panel.source_changed()
            self.dictation_text.edit_modified(False)

    def _reference_error(self, error):
        self.search_button.configure(state="normal")
        self.status.set("PubMed araması başarısız oldu.")
        messagebox.showerror(
            "PubMed kaynakları alınamadı",
            "PubMed bağlantısı veya yanıtı başarısız oldu.\n"
            "İnternet bağlantısını kontrol edip yeniden deneyin; Google Scholar bağlantıları kullanılabilir.",
        )

    def _reference_success(self, id_sets, summaries):
        self.search_button.configure(state="normal")
        self.reference_ids.clear()
        self._render_recommendations(id_sets, summaries)
        total = sum(len(ids) for ids in id_sets)
        self.status.set(f"PubMed araması tamamlandı; {total} kayıt bulundu.")

    def _leave_visit(self):
        """Do not discard a local draft or leave our previous note on the clipboard."""
        if (self.note_panel.body() or any(entry.get().strip() for entry in self.entries.values())
                or self.dictation_text.get('1.0','end-1c').strip()):
            if not messagebox.askyesno('Görüşmeden ayrıl',
                    'Mevcut görüşme ekrandan kaldırılacak. Kaydetmediğiniz bilgiler kaybolabilir. Devam edilsin mi?'):
                return False
        try:
            self.note_panel.clear_owned_clipboard()
        except ClipboardError:
            messagebox.showerror('Pano temizlenemedi',
                'Önceki anamnez panodan temizlenemedi. Yeniden deneyin; yeni görüşme henüz açılmadı.')
            return False
        return True

    def _new_visit(self):
        """Reset every patient-specific state; prevent delayed speech crossing patients."""
        if self._recording_stop is not None:
            self.status.set('Önce mikrofon kaydının ve transkripsiyonun bitmesini bekleyin.')
            return False
        if not self._leave_visit():
            return False
        self._review_pending=False
        self.note_panel.clear_selection_details()
        self.values = dict(INITIAL_DATA)
        self._dictation_applied = ''
        self._test_raw_transcript = ''
        self._speech_context = None
        self._sync_form()
        self.dictation_text.delete('1.0','end')
        self.dictation_text.edit_modified(False)
        self.clinical.invalidate()
        self.reference_ids.clear()
        self._render_recommendations(None, None)
        self.note_panel._set_body('')
        self.note_panel.state.set('Yeni görüşme. Önceki hasta bilgileri temizlendi.')
        self.status.set('Yeni görüşme hazır.')
        self.tabs.select(self.output_tab)
        return True

    def _discard_raw_after_approval(self):
        """Production keeps only the reviewed note; no forensic zeroization claim."""
        if self.settings.test_mode:
            return
        self._review_pending=False
        self.note_panel.clear_selection_details()
        self._suppress_source_changes = True
        try:
            self.dictation_text.delete('1.0','end')
            self.dictation_text.edit_modified(False)
            self.dictation_text.edit_reset()
            self._dictation_applied = ''
            self._test_raw_transcript = ''
            self._speech_context = None
            self.values.pop('_note_draft',None)
            self.values.pop('_test_data',None)
            self.note_panel.editor.edit_reset()
            self.note_panel._source = self.note_panel.sources()
        finally:
            self._suppress_source_changes = False
