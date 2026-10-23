"""Primary offline workflow: review, date stamp, verified copy, manual paste."""
import tkinter as tk
import json
from tkinter import ttk, messagebox
from config import FIELDS
from note_workflow import build_note_body, approve_note
from ui.clipboard import ClipboardError, normalize_lines
from ui.design import text_area


class NotePanel:
    """Own draft and approval state; clipboard never receives an unapproved draft."""
    def __init__(self, app, frame):
        self.app=app
        self.approved=None
        self.last_copied=None
        self.edited=False
        self._source=self.sources()
        self.mode_notice=tk.StringVar()
        ttk.Label(frame,textvariable=self.mode_notice,wraplength=1050,style='Subtitle.TLabel').pack(anchor='w',pady=(0,8))
        self.update_mode_notice()
        steps=ttk.Frame(frame);steps.pack(fill='x',pady=(0,10))
        for label in ('01   KONUŞUN','02   BİTİRİN VE İNCELEYİN','03   ONAYLAYIP KOPYALAYIN'):
            ttk.Label(steps,text=label,style='Badge.TLabel').pack(side='left',padx=(0,8))
        top=ttk.Frame(frame);top.pack(fill='x',pady=6)
        self.record_button=ttk.Button(top,text='1. Dikteyi başlat',style='Record.TButton',command=app._toggle_microphone_recording)
        self.record_button.pack(side='left')
        ttk.Button(top,text='Manuel alanlar',command=lambda:app.tabs.select(app.form_tab)).pack(side='left',padx=6)
        ttk.Button(top,text='Taslağı yeniden hazırla',command=self.prepare).pack(side='left')
        ttk.Button(top,text='Yeni görüşme',command=app._new_visit).pack(side='right')
        ttk.Label(frame,text='Anamnez taslağı',style='Section.TLabel').pack(anchor='w',pady=(8,2))
        ttk.Label(frame,text='Hasta bilgilerini, ilaç dozlarını ve olumsuz ifadeleri kontrol edin. Metni burada düzenleyebilirsiniz.',style='Subtitle.TLabel').pack(anchor='w',pady=(0,8))
        self.editor_frame,self.editor=text_area(frame,wrap='word',height=8,undo=True)
        self.editor.bind('<<Modified>>',self._edited)
        self.selection_details=()
        self.details_window=None
        self.review_frame=ttk.Frame(frame)
        ttk.Label(self.review_frame,text='İnceleme gerekli — bu ifadeler otomatik eklenmedi.',style='Notice.TLabel').pack(fill='x')
        self.review_text=tk.Text(self.review_frame,height=3,wrap='word',state='disabled')
        self.review_text.pack(fill='x')
        ttk.Button(self.review_frame,text='İnceledim; gerekli bilgiyi son metinde düzenledim',command=self.resolve_review).pack(anchor='w')
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=6)
        self.action_row=buttons
        self.approve_button=ttk.Button(buttons,text='3. Onayla ve kopyala',style='Primary.TButton',command=self.complete,state='disabled')
        self.approve_button.pack(side='left')
        self.recopy_button=ttk.Button(buttons,text='Yeniden kopyala',command=self.recopy,state='disabled')
        self.recopy_button.pack(side='left',padx=8)
        self.details_button=ttk.Button(buttons,text='Ayıklama ayrıntıları',command=self.show_selection_details,state='disabled')
        self.details_button.pack(side='left',padx=6)
        self.state=tk.StringVar(value='Yeni görüşme. Onaylanmış metin yok.')
        state_label=ttk.Label(frame,textvariable=self.state,wraplength=900,style='Notice.TLabel')
        state_label.pack(fill='x',pady=(0,6))
        preview_row=ttk.Frame(frame);preview_row.pack(fill='x',pady=(2,4))
        self.preview_toggle=ttk.Button(preview_row,text='Aktarım önizlemesini göster',command=self.toggle_preview)
        self.preview_toggle.pack(side='left')
        ttk.Label(preview_row,text='Miamed: doğru hasta → anamnezin sonu → Ctrl+V',style='Subtitle.TLabel').pack(side='right')
        self.preview_frame,self.preview=text_area(frame,wrap='word',height=4,state='disabled')
        files=ttk.Frame(frame);files.pack(fill='x',pady=(6,0))
        ttk.Button(files,text='Metin kaydet',command=app._save_output).pack(side='left')
        ttk.Button(files,text='Görüşmeyi JSON kaydet',command=app._save_json).pack(side='left',padx=8)
        ttk.Button(files,text='JSON aç',command=app._load_json).pack(side='left')
        self.files_row=files
        # Reserve actions first; the editor takes remaining height on small displays.
        for widget in (files,preview_row,state_label,buttons):widget.pack_forget()
        for widget in (files,preview_row,state_label,buttons):
            widget.pack(side='bottom',fill='x',pady=4)
        self.editor_frame.pack(side='top',fill='both',expand=True)
        app.draft_text=self.editor
        app.output_text=self.preview

    def toggle_preview(self):
        if self.preview_frame.winfo_manager():
            self.preview_frame.pack_forget()
            self.preview_toggle.configure(text='Aktarım önizlemesini göster')
        else:
            self.preview_frame.pack(side='bottom',fill='x',after=self.files_row,pady=(0,6))
            self.preview_toggle.configure(text='Aktarım önizlemesini gizle')
        if not self.app.bridge.busy:
            self.app.status.set('Aktarım önizlemesi açıldı; bu işlem onay vermez.' if self.preview_frame.winfo_manager() else 'Aktarım önizlemesi kapatıldı. Taslakta düzenlemeye devam edebilirsiniz.')

    def update_mode_notice(self):
        self.mode_notice.set('TEST MODU AÇIK — ham metin test kaydına yazılabilir; yalnızca sentetik/izinli veri kullanın.'
                             if self.app.settings.test_mode else 'Üretim modu: yalnızca onayladığınız son anamnez kaydedilir.')
        if not self.app.settings.structure_dictation:
            self.mode_notice.set(self.mode_notice.get()+' AI ayıklama kapalı: konuşma elle düzenlenmelidir.')

    def set_selection_details(self,waiting,excluded):
        self.selection_details=tuple(waiting)+tuple(excluded)
        self.details_button.configure(state='normal' if self.selection_details else 'disabled')
        self.review_text.configure(state='normal');self.review_text.delete('1.0','end')
        self.review_text.insert('1.0','\n\n'.join(waiting));self.review_text.configure(state='disabled')
        if waiting:self.review_frame.pack(side='bottom',fill='x',after=self.action_row,pady=4)
        else:self.review_frame.pack_forget()

    def resolve_review(self):
        if self.app._processing_dictation:return
        self.app._review_pending=False
        self.review_frame.pack_forget()
        self._source=self.sources()
        self.invalidate('İnceleme tamamlandı. Son metni onaylayabilirsiniz.')
        self.app.status.set('İnceleme tamamlandı. Son metni kontrol edip Onayla ve kopyala seçin.')

    def show_selection_details(self):
        if self.details_window is not None and self.details_window.winfo_exists():self.details_window.lift();return
        self.details_window=tk.Toplevel(self.app.root);self.details_window.title('Anamneze otomatik eklenmeyen konuşmalar')
        text=tk.Text(self.details_window,wrap='word',width=85,height=20)
        text.pack(fill='both',expand=True);text.insert('1.0','\n\n'.join(self.selection_details));text.configure(state='disabled')

    def clear_selection_details(self):
        self.selection_details=()
        self.review_text.configure(state='normal');self.review_text.delete('1.0','end');self.review_text.configure(state='disabled')
        self.review_frame.pack_forget();self.details_button.configure(state='disabled')
        if self.details_window is not None:
            try:self.details_window.destroy()
            except tk.TclError:pass
            self.details_window=None

    def update_actions(self):
        """Third action is usable only with complete, current, nonempty input."""
        ready=(not self.app._processing_dictation and not self.app._review_pending and self.app._recording_stop is None
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
        transcript=self.app.dictation_text.get('1.0','end-1c').strip()
        if self.app.settings.structure_dictation and transcript and transcript!=self.app._dictation_applied:
            return self.app._structure_manual_dictation(transcript)
        if self.edited and self.body() and not messagebox.askyesno('Taslağı yenile',
                'Düzenlediğiniz taslak, mevcut dikte ve alanlardan yeniden hazırlanacak. Devam edilsin mi?'):
            return False
        self.app._read_form()
        transcript=self.app.dictation_text.get('1.0','end-1c').strip()
        if transcript==self.app._dictation_applied:transcript=''
        self._set_body(build_note_body(self.app.values,transcript))
        self.app.status.set('Taslak yeniden hazırlandı. Kontrol edip onaylayın.')
        return True

    def complete(self):
        """One explicit approval stamps and copies exactly the displayed text."""
        if self.app._review_pending:
            self.state.set('İnceleme bekleyen ifadeler var. Son metni düzenleyip incelemeyi tamamlayın.')
            return False
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
        if self.app._review_pending:return False
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
