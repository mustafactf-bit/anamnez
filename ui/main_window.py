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

class AnamnezApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Anamnez Asistanı")
        self.root.geometry("1050x760")
        self.root.minsize(820, 600)
        self.values = dict(INITIAL_DATA)
        self.entries = {}
        self.reference_ids = []
        self._recording = False
        self._recording_stop = None
        self._build_ui()

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=(12, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Anamnez Asistanı", font=("Segoe UI", 16, "bold")).pack(anchor="w")
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
        self.tabs.add(self.form_tab, text="Hasta bilgileri")
        self.tabs.add(self.dictation_tab, text="Dikte metni")
        self.tabs.add(self.recommendations_tab, text="5 değerlendirme önerisi")
        self.tabs.add(self.output_tab, text="Anamnez çıktısı")
        self._build_form()
        self._build_dictation()
        self._build_recommendations()
        self._build_output()
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
            entry = ttk.Entry(container, width=92)
            entry.insert(0, self.values[key])
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            self.entries[key] = entry
        container.columnconfigure(1, weight=1)
        ttk.Button(container, text="Değişiklikleri uygula", command=self._read_form).grid(
            row=len(FIELDS), column=1, sticky="e", pady=10
        )

    def _build_dictation(self):
        ttk.Label(
            self.dictation_tab,
            text="Türkçe konuşmayı yerel Whisper modeliyle yazıya çevirebilir veya Gemini'den aldığınız metni yapıştırabilirsiniz. Ses kaydedilmez ya da bir sunucuya gönderilmez.",
            wraplength=950,
        ).pack(anchor="w", pady=(0, 8))
        controls = ttk.Frame(self.dictation_tab)
        controls.pack(fill="x", pady=(0, 8))
        self.whisper_model = tk.StringVar(value="small")
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
        model_size = self.whisper_model.get()
        if model_size not in ("small", "medium", "large-v3", "turbo"):
            messagebox.showerror("Whisper modeli", "Listeden geçerli bir Whisper modeli seçin.")
            return
        self._recording = True
        self._recording_stop = threading.Event()
        self.record_button.configure(text="Whisper yükleniyor...", state="disabled")
        self.status.set(
            f"Whisper {model_size} hazırlanıyor. İlk kullanımda model indirilir; indirme tamamlanınca kayıt başlayacak."
        )
        threading.Thread(
            target=self._record_and_transcribe,
            args=(model_size, self._recording_stop),
            daemon=True,
        ).start()

    def _record_and_transcribe(self, model_size, stop_event):
        try:
            import numpy as np
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except ImportError as error:
            self.root.after(0, lambda error=error: self._microphone_error(error, missing_dependency=True))
            return

        try:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            chunks = []
            input_overflow = [False]

            def receive_audio(indata, _frames, _time_info, status):
                if status:
                    input_overflow[0] = True
                chunks.append(indata.copy())

            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                callback=receive_audio,
            ):
                self.root.after(0, self._microphone_recording_started)
                started_at = time.monotonic()
                reached_limit = False
                while not stop_event.wait(0.1):
                    if time.monotonic() - started_at >= 900:
                        reached_limit = True
                        stop_event.set()
                        break

            if not chunks:
                raise ValueError("Mikrofondan ses alınamadı. Mikrofon bağlantısını ve Windows izinlerini kontrol edin.")
            audio = np.concatenate(chunks, axis=0).reshape(-1)
            segments, _info = model.transcribe(
                audio,
                language="tr",
                task="transcribe",
                beam_size=5,
                vad_filter=True,
            )
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            self.root.after(
                0,
                lambda: self._microphone_transcription_finished(
                    transcript,
                    input_overflow[0],
                    reached_limit,
                ),
            )
        except Exception as error:
            self.root.after(0, lambda error=error: self._microphone_error(error))

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
                f"Ayrıntı: {error}",
            )
        else:
            messagebox.showerror(
                "Dikte başarısız oldu",
                f"Mikrofon kaydı veya Whisper çözümlemesi tamamlanamadı:\n{error}\n\n"
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
        buttons = ttk.Frame(self.output_tab)
        buttons.pack(fill="x", pady=(0, 8))
        ttk.Button(buttons, text="Çıktıyı oluştur / yenile", command=self._refresh_output).pack(side="left")
        ttk.Button(buttons, text="Metni panoya kopyala", command=self._copy_output).pack(side="left", padx=8)
        ttk.Button(buttons, text="Metin dosyası olarak kaydet", command=self._save_output).pack(side="left")
        ttk.Button(buttons, text="Hasta verisini JSON kaydet", command=self._save_json).pack(side="left", padx=8)
        ttk.Button(buttons, text="JSON dosyası aç", command=self._load_json).pack(side="left")
        self.output_text = tk.Text(self.output_tab, wrap="word", height=27)
        self.output_text.pack(fill="both", expand=True)
        self._refresh_output()

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
        self._read_form()
        updated = parse_dictation(text, self.values)
        self._sync_form()
        self._refresh_output()
        self.status.set("Güncellenen alanlar: " + ", ".join(dict.fromkeys(updated)))
        self.tabs.select(self.form_tab)

    def _refresh_output(self):
        self._read_form()
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", format_note(self.values))

    def _copy_output(self):
        self._refresh_output()
        self.root.clipboard_clear()
        self.root.clipboard_append(self.output_text.get("1.0", "end-1c"))
        self.status.set("Anamnez metni panoya kopyalandı.")

    def _save_output(self):
        self._refresh_output()
        path = filedialog.asksaveasfilename(
            title="Anamnez metnini kaydet",
            defaultextension=".txt",
            filetypes=[("Metin dosyası", "*.txt"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            Path(path).write_text(self.output_text.get("1.0", "end-1c"), encoding="utf-8")
            self.status.set("Anamnez metni kaydedildi: " + path)

    def _save_json(self):
        self._read_form()
        path = filedialog.asksaveasfilename(
            title="Hasta verisini kaydet",
            defaultextension=".json",
            filetypes=[("JSON dosyası", "*.json"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            save_patient(path, self.values)
            self.status.set("Hasta verisi kaydedildi: " + path)

    def _load_json(self):
        path = filedialog.askopenfilename(
            title="Hasta verisini aç", filetypes=[("JSON dosyası", "*.json"), ("Tüm dosyalar", "*.*")]
        )
        if not path:
            return
        try:
            self.values = load_patient(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showerror("Dosya açılamadı", str(error))
            return
        self._sync_form()
        self._refresh_output()
        self.status.set("Hasta verisi yüklendi.")

    def _start_reference_search(self):
        self.search_button.configure(state="disabled")
        self.status.set("PubMed kaynakları aranıyor...")
        threading.Thread(target=self._search_references, daemon=True).start()

    def _search_references(self):
        try:
            result = fetch_pubmed_references(RECOMMENDATIONS)
        except (OSError, ValueError, KeyError, ET.ParseError) as error:
            self.root.after(0, lambda error=error: self._reference_error(error))
            return
        self.root.after(0, lambda: self._reference_success(*result))

    def _reference_error(self, error):
        self.search_button.configure(state="normal")
        self.status.set("PubMed araması başarısız oldu.")
        messagebox.showerror(
            "PubMed kaynakları alınamadı",
            f"PubMed bağlantısı veya yanıtı başarısız oldu: {error}\n"
            "İnternet bağlantısını kontrol edip yeniden deneyin; Google Scholar bağlantıları kullanılabilir.",
        )

    def _reference_success(self, id_sets, summaries):
        self.search_button.configure(state="normal")
        self.reference_ids.clear()
        self._render_recommendations(id_sets, summaries)
        total = sum(len(ids) for ids in id_sets)
        self.status.set(f"PubMed araması tamamlandı; {total} kayıt bulundu.")
