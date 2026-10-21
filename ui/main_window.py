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
from settings import load_settings, Settings
from ai.llm_engine import GGUFEngine
from literature.pubmed_client import PubMedClient
from speech.whisper_engine import WhisperEngine
from speech.audio_recorder import record_audio
from ui.worker import WorkerBridge
from ui.note_panel import NotePanel
from ui.clipboard import create_clipboard, ClipboardError
from ui.clinical_assistant_tab import ClinicalAssistantTab
from ui.settings_tab import build_settings_tab

class AnamnezApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Anamnez Asistanı V2-alpha1")
        self.root.geometry("1050x760")
        self.root.minsize(820, 600)
        self.values = dict(INITIAL_DATA)
        self.entries = {}
        self.entry_variables = {}
        self._dictation_applied = ''
        self.clipboard = create_clipboard(root)
        self.reference_ids = []
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
        ttk.Label(header, text="Anamnez Asistanı V2-alpha1", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Dikte için Türkçe Whisper modeli yerel olarak çalışır. Dikte ve hasta bilgileri dış servislere gönderilmez; yalnızca genel literatür aramaları PubMed'e iletilir.",
            wraplength=990,
        ).pack(anchor="w", pady=(4, 0))

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.form_tab = ttk.Frame(self.tabs, padding=8)
        self.dictation_tab = ttk.Frame(self.tabs, padding=8)
        self.recommendations_tab = ttk.Frame(self.tabs, padding=8)
        self.output_tab = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(self.output_tab, text="Anamnez • Miamed")
        self.tabs.add(self.dictation_tab, text="Dikte metni")
        self.tabs.add(self.form_tab, text="Hasta bilgileri")
        self.tabs.add(self.recommendations_tab, text="5 değerlendirme önerisi")
        self._build_form()
        self._build_dictation()
        self._build_recommendations()
        self._build_output()
        clinical_frame = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(clinical_frame, text='Klinik Asistan')
        self.clinical = ClinicalAssistantTab(self, clinical_frame)
        settings_frame = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(settings_frame, text='Ayarlar')
        build_settings_tab(self, settings_frame)
        self.dictation_text.bind('<<Modified>>', self._transcript_changed)
        for variable in self.entry_variables.values():
            variable.trace_add('write', lambda *_: self.note_panel.source_changed())
        self.status = tk.StringVar(value="Hazır.")
        ttk.Label(self.root, textvariable=self.status, anchor="w", padding=(12, 4)).pack(fill="x")

    def _build_form(self):
        canvas = tk.Canvas(self.form_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.form_tab, orient="vertical", command=canvas.yview)
        container = ttk.Frame(canvas, padding=8)
        container.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=container, anchor="nw")
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
            controls, text="Mikrofonla dikte et", command=self._toggle_microphone_recording
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
            self.record_button.configure(text="Dikte yazıya çevriliyor...", state="disabled")
            self.status.set("Kayıt durduruldu; Türkçe ses yazıya çevriliyor...")
            if self._recording_stop:
                self._recording_stop.set()
            return
        if self.bridge.busy:
            self.status.set('Devam eden işlemin bitmesini bekleyin.')
            return
        model_size = self.whisper_model.get()
        if model_size not in ("small", "medium", "large-v3", "turbo"):
            messagebox.showerror("Whisper modeli", "Listeden geçerli bir Whisper modeli seçin.")
            return
        self._recording = True
        self.note_panel.invalidate('Yeni dikte başladı. Kayıt ve transkripsiyondan sonra taslağı güncelleyip onaylayın.')
        self._recording_stop = threading.Event()
        self.record_button.configure(text="Whisper yükleniyor...", state="disabled")
        self.status.set(
            f"Whisper {model_size} hazırlanıyor. İlk kullanımda model indirilir; indirme tamamlanınca kayıt başlayacak."
        )
        stop_event = self._recording_stop
        self.bridge.start(
            lambda: self._record_and_transcribe(model_size, stop_event),
            lambda result: self._microphone_transcription_finished(*result),
            self._microphone_error,
        )

    def _record_and_transcribe(self, model_size, stop_event):
        try:
            if self.settings.low_memory:
                self.engine.unload()
            self.speech_engine.load(model_size)
            if stop_event.is_set():
                return '', False, False
            audio, overflow, limit = record_audio(stop_event,
                lambda: self.bridge.post(self._microphone_recording_started))
            if self.bridge.closed:
                return '', overflow, limit
            self.bridge.post(lambda: self.status.set('Türkçe transkripsiyon yapılıyor...'))
            return self.speech_engine.transcribe(audio), overflow, limit
        finally:
            if self.settings.low_memory or self.bridge.closed:
                self.speech_engine.unload()

    def _microphone_recording_started(self):
        self.record_button.configure(text="Kaydı bitir ve yazıya çevir", state="normal")
        self.status.set("Kayıt başladı. Konuşmanız bitince kaydı durdurun (en fazla 15 dakika).")

    def _microphone_transcription_finished(self, transcript, input_overflow, reached_limit):
        self._recording = False
        self.record_button.configure(text="Mikrofonla dikte et", state="normal")
        self._recording_stop = None
        if not transcript:
            self.status.set("Konuşma algılanmadı. Mikrofon ses düzeyini ve kaydı kontrol edin.")
            messagebox.showinfo("Dikte sonucu", "Ses kaydedildi ancak anlaşılır konuşma algılanmadı.")
            return
        current = self.dictation_text.get("1.0", "end").strip()
        if current:
            self.dictation_text.insert("end", "\n")
        self.dictation_text.insert("end", transcript)
        self.dictation_text.see("end")
        self.status.set(
            "Dikte metne çevrildi; gözden geçirip 'Dikteyi alanlara aktar' düğmesine basın."
        )
        notes = []
        if input_overflow:
            notes.append("Kayıt sırasında mikrofon tamponu taştı; bazı sesler eksik olabilir.")
        if reached_limit:
            notes.append("15 dakikalık kayıt sınırına ulaşıldı.")
        if notes:
            messagebox.showwarning("Dikte uyarısı", "\n".join(notes))

    def _microphone_error(self, error, missing_dependency=False):
        self._recording = False
        self.record_button.configure(text="Mikrofonla dikte et", state="normal")
        self._recording_stop = None
        self.status.set("Mikrofon diktesi başarısız oldu.")
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
        path = filedialog.asksaveasfilename(
            title="Anamnez metnini kaydet",
            defaultextension=".txt",
            filetypes=[("Metin dosyası", "*.txt"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            try:
                Path(path).write_text(self.note_panel.export_text(), encoding="utf-8")
            except OSError:
                messagebox.showerror('Kayıt', 'Metin kaydedilemedi. Konumu ve yazma iznini kontrol edin.')
                return
            self.status.set("Anamnez metni kaydedildi: " + path)

    def _save_json(self):
        self._read_form()
        path = filedialog.asksaveasfilename(
            title="Hasta verisini kaydet",
            defaultextension=".json",
            filetypes=[("JSON dosyası", "*.json"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            try:
                save_patient(path, {**self.values, '_note_draft': self.note_panel.snapshot()})
            except OSError:
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
        self.values = loaded
        self.dictation_text.delete('1.0','end')
        saved_note = loaded.get('_note_draft')
        if isinstance(saved_note, dict):
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
        self.note_panel.restore(loaded.get('_note_draft'))
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
        self.bridge.close()
        # Native inference cannot be safely interrupted; daemon jobs finish or exit
        # with the process, without posting callbacks to the destroyed window.
        self.root.destroy()

    def _transcript_changed(self, _event=None):
        if self.dictation_text.edit_modified():
            self.clinical.invalidate()
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
        self.values = dict(INITIAL_DATA)
        self._dictation_applied = ''
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
