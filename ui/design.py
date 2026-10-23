"""Shared desktop visual language; no workflow or patient state."""
import tkinter as tk
from tkinter import ttk

NAVY='#123454'
BLUE='#185c91'
BG='#f2f5f9'
INK='#182c40'
MUTED='#4b6075'

def apply_design(root):
    root.configure(background=BG)
    root.option_add('*Font',('Segoe UI',10))
    root.option_add('*Text.Font',('Segoe UI',11))
    for key,value in {'background':'#ffffff','foreground':INK,'insertBackground':BLUE,
                      'selectBackground':'#cce3f5','selectForeground':INK,
                      'relief':'flat','borderWidth':0,'highlightThickness':1,
                      'highlightBackground':'#cbd5e1','highlightColor':BLUE,
                      'padX':14,'padY':12}.items():
        root.option_add('*Text.'+key,value)
    style=ttk.Style(root)
    style.theme_use('clam')
    style.configure('.',font=('Segoe UI',10),background=BG,foreground=INK)
    style.configure('TFrame',background=BG)
    style.configure('TLabel',background=BG)
    style.configure('Title.TLabel',font=('Segoe UI',21,'bold'),foreground=NAVY)
    style.configure('Subtitle.TLabel',foreground=MUTED,font=('Segoe UI',10))
    style.configure('Section.TLabel',font=('Segoe UI',11,'bold'),foreground=NAVY)
    style.configure('Badge.TLabel',background='#e3edf6',foreground=NAVY,padding=(10,5))
    style.configure('Notice.TLabel',background='#e7f1f6',foreground=NAVY,padding=(12,8))
    style.configure('TButton',padding=(12,8),background='#e5ebf2',borderwidth=0)
    style.map('TButton',background=[('active','#d4e1ee')],foreground=[('disabled','#64748b')])
    style.configure('Primary.TButton',background=BLUE,foreground='white',font=('Segoe UI',10,'bold'))
    style.map('Primary.TButton',background=[('disabled','#dde5ee'),('active','#124a76')],
              foreground=[('disabled','#64748b'),('!disabled','white')])
    style.configure('Record.TButton',background=NAVY,foreground='white',font=('Segoe UI',10,'bold'))
    style.map('Record.TButton',background=[('disabled','#dde5ee'),('active',BLUE)],
              foreground=[('disabled','#64748b'),('!disabled','white')])
    style.configure('TNotebook',background=BG,borderwidth=0,tabmargins=(0,0,0,8))
    style.configure('TNotebook.Tab',padding=(13,9),background='#e5ebf2')
    style.map('TNotebook.Tab',background=[('selected',NAVY)],foreground=[('selected','white')])
    style.configure('TEntry',padding=7,fieldbackground='white')
    style.configure('TLabelframe',padding=12,bordercolor='#cbd5e1')
    style.configure('TLabelframe.Label',font=('Segoe UI',10,'bold'),foreground=NAVY)

def text_area(parent,**kwargs):
    frame=ttk.Frame(parent)
    text=tk.Text(frame,**kwargs)
    scroll=ttk.Scrollbar(frame,orient='vertical',command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y')
    text.pack(side='left',fill='both',expand=True)
    return frame,text

def wheel_scroll(canvas):
    """Scoped binding: scrolling a form never hijacks other tabs/windows."""
    def scroll(event):
        if event.delta:canvas.yview_scroll(-int(event.delta/120),'units')
        return 'break'
    def bind_children(widget):
        widget.bind('<MouseWheel>',scroll,add='+')
        for child in widget.winfo_children():bind_children(child)
    canvas.after_idle(lambda:bind_children(canvas))
