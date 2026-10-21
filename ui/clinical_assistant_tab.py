"""Clinical workflow UI; engines and retrieval are injected independently."""
import json
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from ai.clinical_parser import extract_anamnesis
from ai.question_generator import generate_questions
from ai.evidence_synthesizer import synthesize
from literature.query_builder import build_query
from literature.evidence_ranker import DeterministicRanker


class ClinicalAssistantTab:
    """Clinician selects and edits questions before any network request."""
    def __init__(self,app,frame):
        self.app=app;self.frame=frame;self.questions=[];self.structured=None
        self.version=0
        ttk.Label(frame,text='Dikte metnini gözden geçirin. Yerel modelin çıkardığı bilgiler otomatik olarak hasta alanlarını değiştirmez.',wraplength=940).pack(anchor='w')
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=6)
        ttk.Button(buttons,text='Dikteden anamnez ve sorular çıkar',command=self.extract).pack(side='left')
        ttk.Button(buttons,text='Onaylanan anamnezi alanlara aktar',command=self.apply_reviewed).pack(side='left',padx=8)
        ttk.Button(buttons,text='PubMed’de Ara',command=self.search).pack(side='left',padx=8)
        ttk.Label(frame,text='Dikkat çeken bilgiler — hekim incelemesi için').pack(anchor='w')
        self.facts=tk.Text(frame,height=7,wrap='word',state='disabled');self.facts.pack(fill='x')
        ttk.Label(frame,text='Literatür sorusu seçin:').pack(anchor='w')
        self.choice=ttk.Combobox(frame,state='readonly');self.choice.pack(fill='x')
        self.choice.bind('<<ComboboxSelected>>',self.select)
        self.question=tk.StringVar();ttk.Entry(frame,textvariable=self.question).pack(fill='x',pady=4)
        ttk.Label(frame,text='Arama kavramları (İngilizce, noktalı virgülle ayırın; yalnızca güvenli sözlük kabul edilir):').pack(anchor='w')
        self.concepts=tk.StringVar();ttk.Entry(frame,textvariable=self.concepts).pack(fill='x')
        self.output=tk.Text(frame,wrap='word',height=14,state='disabled');self.output.pack(fill='both',expand=True,pady=6)

    def invalidate(self):
        """Prevent evidence from a previous patient/transcript being reused."""
        self.version+=1;self.questions=[];self.structured=None
        self.choice.configure(values=());self.choice.set('');self.question.set('');self.concepts.set('')
        self._display(self.facts,'');self._display(self.output,'')

    @staticmethod
    def _display(widget,value):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',value);widget.configure(state='disabled')

    def error(self,error):
        self.app.status.set('İşlem tamamlanamadı.')
        # Only intentionally safe domain messages reach the UI.
        from ai.llm_engine import LLMError
        from safety.privacy import PrivacyError
        from literature.pubmed_client import PubMedError
        message=str(error) if isinstance(error,(LLMError,PrivacyError,PubMedError)) else 'İşlem tamamlanamadı. Ayarları ve bağlantıyı kontrol edip yeniden deneyin.'
        messagebox.showerror('Klinik Asistan',message)

    def extract(self):
        if self.app.bridge.busy:
            self.app.status.set('Devam eden işlemin bitmesini bekleyin.');return
        transcript=self.app.dictation_text.get('1.0','end').strip()
        if not transcript:
            messagebox.showinfo('Klinik Asistan','Önce dikte metnini girin.');return
        self.invalidate();version=self.version
        settings=self.app.settings
        def work():
            try:
                if settings.low_memory:self.app.speech_engine.unload()
                self.app.bridge.post(lambda:self.app.status.set('Yerel model anamnezi yapılandırıyor...'))
                structured=extract_anamnesis(self.app.engine,transcript)
                self.app.bridge.post(lambda:self.app.status.set('Literatür soruları hazırlanıyor...'))
                return structured,generate_questions(self.app.engine,structured)
            finally:
                if settings.low_memory:self.app.engine.unload()
        def done(result):
            if version!=self.version:return
            self.structured,self.questions=result
            self._display(self.facts,json.dumps(self.structured,ensure_ascii=False,indent=2))
            self.choice.configure(values=[q['question'] for q in self.questions]);self.choice.current(0);self.select()
            self.app.status.set('Anamnezi ve soruları kontrol edin; araştırılacak soruyu seçin.')
        self.app.bridge.start(work,done,self.error)

    def select(self,_event=None):
        index=self.choice.current()
        if index<0:return
        q=self.questions[index]
        self.question.set(q['question']);self.concepts.set('; '.join(q['concepts']))
        if q['pico']:self._display(self.output,'PICO:\n'+json.dumps(q['pico'],ensure_ascii=False,indent=2))
        else:self._display(self.output,'')

    def apply_reviewed(self):
        """User explicitly accepts extracted facts; missing fields stay untouched."""
        if not self.structured:return
        self.app._read_form()
        mappings={'chief_complaint':'sikayet','history':'ozgecmis','medications':'ilaclar'}
        for source,target in mappings.items():
            value=self.structured[source]
            if value:self.app.values[target]='; '.join(value) if isinstance(value,list) else value
        self.app.values['_v2']={'structured_anamnesis':self.structured}
        self.app._sync_form();self.app._refresh_output()
        self.app.status.set('Onayladığınız bilgiler aktarıldı; eksik alanlar korunuyor. Yaş ve laboratuvar ayrıntıları V2 JSON verisinde saklanır.')

    def search(self):
        if self.app.bridge.busy:
            self.app.status.set('Devam eden işlemin bitmesini bekleyin.');return
        if not self.questions:return
        concepts=[x.strip() for x in self.concepts.get().split(';') if x.strip()]
        question=self.question.get().strip()
        if not question:return
        try:query=build_query(concepts)
        except ValueError as error:self.error(error);return
        self._display(self.output,'PubMed taranıyor...')
        self.app.status.set('PubMed taranıyor...');version=self.version
        settings=self.app.settings
        def work():
            try:
                articles=self.app.pubmed.search(query)
                self.app.bridge.post(lambda:self.app.status.set('Yayınlar değerlendiriliyor...'))
                selected=DeterministicRanker().rank(articles,concepts,settings.rerank_top_k)[:settings.synthesis_top_k]
                if selected:self.app.bridge.post(lambda:self.app.status.set('Kanıt özeti hazırlanıyor...'))
                result=synthesize(self.app.engine,question,selected,settings.context_size)
                return selected,result
            finally:
                if settings.low_memory:self.app.engine.unload()
        def done(result):
            if version!=self.version:return
            selected,summary=result
            lines=['Kanıt Özeti']
            lines.extend(f"• {c['claim']} [PMID: {c['pmid']}]" for c in summary['claims'])
            lines+=['',summary['limitations'] if selected else 'Eşleşen yayın bulunamadı. Kavramları gözden geçirin.','', 'Kaynaklar']
            for a in selected:
                lines.extend([a.title,f'{a.journal}, {a.year}',f'PMID: {a.pmid}',f'DOI: {a.doi or "Yok"}',f'https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/',''])
            if settings.debug_queries:lines+=['Kullanılan PubMed sorgusu:',query]
            self._display(self.output,'\n'.join(lines))
            self.output.configure(state='normal')
            for a in selected:
                url=f'https://pubmed.ncbi.nlm.nih.gov/{a.pmid}/'
                pos=self.output.search(url,'1.0',stopindex='end')
                if pos:
                    tag='pmid'+a.pmid;self.output.tag_add(tag,pos,f'{pos}+{len(url)}c')
                    self.output.tag_configure(tag,foreground='blue',underline=True)
                    self.output.tag_bind(tag,'<Button-1>',lambda _e,url=url:webbrowser.open(url))
            self.output.configure(state='disabled')
            self.app.status.set('Araştırma tamamlandı; kaynakları klinik bağlamda inceleyin.')
        self.app.bridge.start(work,done,self.error)
