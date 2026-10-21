"""Primary offline workflow: review, date stamp, verified copy, manual paste."""
import tkinter as tk
import json
from tkinter import ttk, messagebox
from config import FIELDS
from note_workflow import build_note_body, approve_note
from ui.clipboard import ClipboardError, normalize_lines


class NotePanel:
    """Own draft and approval state; clipboard never receives an unapproved draft."""
    def __init__(self, app, frame):
        self.app=app
        self.approved=None
        self.last_copied=None
        self.edited=False
        self._source=self.sources()
        self.mode_notice=tk.StringVar()
        ttk.Label(frame,textvariable=self.mode_notice,wraplength=940).pack(anchor='w')
        self.update_mode_notice()
        ttk.Label(frame,text='1. Dikteyi başlat → 2. Dikteyi bitir → metin otomatik hazırlanır → 3. Onayla ve aktar.',wraplength=940).pack(anchor='w')
        top=ttk.Frame(frame);top.pack(fill='x',pady=6)
        self.record_button=ttk.Button(top,text='1. Dikteyi başlat',command=app._toggle_microphone_recording)
        self.record_button.pack(side='left')
        ttk.Button(top,text='Manuel alanlar',command=lambda:app.tabs.select(app.form_tab)).pack(side='left',padx=6)
        ttk.Button(top,text='Dikte ve alanlardan taslak hazırla',command=self.prepare).pack(side='left')
        ttk.Button(top,text='Yeni görüşme',command=app._new_visit).pack(side='right')
        ttk.Label(frame,text='Hekim düzenlemesi — yalnızca doğruladığınız bilgileri bırakın:').pack(anchor='w')
        self.editor=tk.Text(frame,wrap='word',height=6,undo=True)
        self.editor.pack(fill='both',expand=True)
        self.editor.bind('<<Modified>>',self._edited)
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=6)
        self.approve_button=ttk.Button(buttons,text='3. Onayla ve aktar (şimdilik panoya)',command=self.complete,state='disabled')
        self.approve_button.pack(side='left')
        self.recopy_button=ttk.Button(buttons,text='Yeniden kopyala',command=self.recopy,state='disabled')
        self.recopy_button.pack(side='left',padx=8)
        self.state=tk.StringVar(value='Yeni görüşme. Onaylanmış metin yok.')
        ttk.Label(frame,textvariable=self.state,wraplength=940).pack(anchor='w')
        ttk.Label(frame,text='Miamed’e yapıştırılacak metin — tarih ve saat onay anında eklenir:').pack(anchor='w',pady=(6,0))
        self.preview=tk.Text(frame,wrap='word',height=6,state='disabled')
        self.preview.pack(fill='both',expand=True)
        files=ttk.Frame(frame);files.pack(fill='x',pady=(6,0))
        ttk.Button(files,text='Metin kaydet',command=app._save_output).pack(side='left')
        ttk.Button(files,text='Görüşmeyi JSON kaydet',command=app._save_json).pack(side='left',padx=8)
        ttk.Button(files,text='JSON aç',command=app._load_json).pack(side='left')
        app.draft_text=self.editor
        app.output_text=self.preview

    def update_mode_notice(self):
        self.mode_notice.set('TEST MODU AÇIK — ham metin test kaydına yazılabilir; yalnızca sentetik/izinli veri kullanın.'
                             if self.app.settings.test_mode else 'Üretim modu: yalnızca onayladığınız son anamnez kaydedilir.')

    def update_actions(self):
        """Third action is usable only with complete, current, nonempty input."""
        ready=(not self.app._processing_dictation and self.app._recording_stop is None
               and self.sources()==self._source and bool(self.body().strip()))
        self.approve_button.configure(state='normal' if ready else 'disabled')

    def sources(self):
        """Full input snapshot, compared only in memory and never logged."""
        return (tuple(self.app.entry_variables[key].get() for key in FIELDS),
                self.app.dictation_text.get('1.0','end-1c'),
                json.dumps(self.app.values.get('_v2'),ensure_ascii=False,sort_keys=True))

    def body(self):
        return self.editor.get('1.0','end-1c')

    def _preview(self,text):
        self.preview.configure(state='normal')
        self.preview.delete('1.0','end');self.preview.insert('1.0',text)
        self.preview.configure(state='disabled')

    def clear_owned_clipboard(self):
        """Erase our stale note only while clipboard still contains that note."""
        if self.last_copied is None:return
        current=self.app.clipboard.read()
        if current is not None and normalize_lines(current)==normalize_lines(self.last_copied):
            self.app.clipboard.write('')
        self.last_copied=None

    def invalidate(self,message):
        """Edits revoke approval and attempt to remove the stale clipboard note."""
        self.approved=None
        self.recopy_button.configure(state='disabled')
        try:self.clear_owned_clipboard()
        except ClipboardError:
            message+=' Eski pano temizlenemedi; Miamed’e yapıştırmayın, yeniden onaylayın.'
        self.state.set(message)
        self._preview(self.body())
        self.update_actions()

    def source_changed(self):
        if self.sources()!=self._source:
            self.invalidate('Dikte veya alanlar değişti. Taslağı yeniden hazırlayın ve onaylayın.')

    def _edited(self,_event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.edited=True
            self.invalidate('Metin değişti. Tarihli kopya için yeniden onaylayın.')

    def _set_body(self,text):
        self.editor.delete('1.0','end');self.editor.insert('1.0',text)
        self.editor.edit_modified(False);self.editor.edit_reset()
        self.edited=False
        self._source=self.sources()
        self.invalidate('Taslak hazır. Kontrol edip onaylayın.')

    def prepare(self):
        """Build deterministically, preserving clinician edits unless discarded."""
        if self.edited and self.body() and not messagebox.askyesno('Taslağı yenile',
                'Düzenlediğiniz taslak, mevcut dikte ve alanlardan yeniden hazırlanacak. Devam edilsin mi?'):
            return False
        self.app._read_form()
        transcript=self.app.dictation_text.get('1.0','end-1c').strip()
        if transcript==self.app._dictation_applied:transcript=''
        self._set_body(build_note_body(self.app.values,transcript))
        return True

    def complete(self):
        """One explicit approval stamps and copies exactly the displayed text."""
        if self.app._recording_stop is not None or self.app._processing_dictation:
            self.state.set('Kayıt veya transkripsiyon sürüyor. Anamnezi tamamlamadan önce bitmesini bekleyin.')
            return False
        if self.editor.edit_modified():self._edited()
        if self.sources()!=self._source:
            self.source_changed()
            self.app.status.set('Önce güncel dikte ve alanlardan taslak hazırlayın.')
            return False
        # A direct method/button call can precede Tk's Modified event.
        if self.approved is not None and self.body()!=self.approved.body:
            self.invalidate('Metin değişti; yeniden onaylanıyor.')
        try:
            note=self.approved or approve_note(self.body())
        except ValueError as error:
            self.state.set(str(error));return False
        self.approved=note
        self._preview(note.text)
        self.app._discard_raw_after_approval()
        self.recopy_button.configure(state='normal')
        return self._copy()

    def _copy(self):
        self.last_copied=self.approved.text
        try:
            self.app.clipboard.write(self.approved.text)
        except ClipboardError:
            self.state.set('Kopyalanamadı. Miamed’e yapıştırmayın; Yeniden kopyala düğmesini kullanın.')
            self.app.status.set('Pano kopyalaması başarısız; işlem tamamlanmadı.')
            return False
        self.last_copied=self.approved.text
        self.state.set('Panoya kopyalandı — Miamed anamnez alanının sonuna yapıştırabilirsiniz.')
        self.app.status.set('Anamnez onaylandı ve tarih/saatle panoya kopyalandı.')
        return True

    def recopy(self):
        """Retry the same approved snapshot without changing its timestamp."""
        if self.approved is None:return False
        if self.sources()!=self._source or self.body()!=self.approved.body:
            self.invalidate('Bilgiler değişti. Taslağı güncelleyip yeniden onaylayın.')
            return False
        return self._copy()

    def snapshot(self):
        """Only explicit test mode may persist raw sources or an unapproved draft."""
        self.source_changed()
        if self.editor.edit_modified():self._edited()
        snapshot={'body':self.body(),
                'last_approved_text':self.approved.text if self.approved else None,
                'approved_at':self.approved.approved_at.isoformat() if self.approved else None,
                'sources_current':self.sources()==self._source}
        if self.app.settings.test_mode:
            snapshot.update(transcript=self.app.dictation_text.get('1.0','end-1c'),
                            dictation_applied=self.app._dictation_applied)
        return snapshot

    def current_approval(self):
        """Never save stale approval after an unprocessed edit event."""
        if self.editor.edit_modified():self._edited()
        if self.sources()!=self._source:self.source_changed()
        return self.approved is not None and self.body()==self.approved.body

    def export_text(self):
        """Save precisely the current preview; never regenerate over manual edits."""
        self.source_changed()
        if self.editor.edit_modified():self._edited()
        return self.preview.get('1.0','end-1c')

    def restore(self,data=None):
        """A loaded note is always pending review, never automatically copied."""
        data=data if isinstance(data,dict) else {}
        body=data.get('body')
        if isinstance(body,str) and len(body)<=1_000_000:
            self._set_body(body)
            self.edited=True
            # Stale saved drafts must not silently become current on load.
            if data.get('sources_current') is not True:self._source=None
        else:self._set_body(build_note_body(self.app.values))
        self.state.set('Yüklenen görüşmeyi kontrol edip yeniden onaylayın.')
