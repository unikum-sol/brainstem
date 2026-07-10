import tkinter as tk, json
from tkinter import ttk
from ki_system.memory import Memory
from ki_system.dialogue import DialogueManager
from ki_system.search import semantic_search, answer
class UserApp(tk.Tk):
    def __init__(self,db_path='ki_memory.sqlite3'):
        super().__init__(); self.title('KI-System V8 User'); self.geometry('1000x700'); self.mem=Memory(db_path,readonly=True); self.dialogue=DialogueManager(self.mem); self._ui()
    def _ui(self):
        nb=ttk.Notebook(self); nb.pack(fill=tk.BOTH,expand=True); chat=ttk.Frame(nb,padding=8); search=ttk.Frame(nb,padding=8); nb.add(chat,text='Chat'); nb.add(search,text='Suche & Antwort')
        self.chat_out=tk.Text(chat,wrap=tk.WORD); self.chat_out.pack(fill=tk.BOTH,expand=True); self.chat_in=tk.StringVar(); ttk.Entry(chat,textvariable=self.chat_in).pack(fill=tk.X); ttk.Button(chat,text='Senden',command=self.chat_send).pack(anchor=tk.W)
        self.q=tk.StringVar(); ttk.Entry(search,textvariable=self.q).pack(fill=tk.X); ttk.Button(search,text='Suchen',command=self.do_search).pack(anchor=tk.W); ttk.Button(search,text='Antwort',command=self.do_answer).pack(anchor=tk.W); self.out=tk.Text(search,wrap=tk.WORD); self.out.pack(fill=tk.BOTH,expand=True)
    def chat_send(self):
        t=self.chat_in.get().strip()
        if not t: return
        r=self.dialogue.respond(t); self.chat_out.insert(tk.END,'Du: '+t+'\n\nAntwort:\n'+r.response+'\n\n'); self.chat_out.see(tk.END); self.chat_in.set('')
    def do_search(self):
        self.out.delete('1.0',tk.END)
        for h in semantic_search(self.mem,self.q.get(),25): self.out.insert(tk.END,f'{h.score:.3f} [{h.method}] {h.title} | Chunk {h.chunk_id}\n{h.text[:1000]}\n\n')
    def do_answer(self): self.out.delete('1.0',tk.END); self.out.insert(tk.END,json.dumps(answer(self.mem,self.q.get()),ensure_ascii=False,indent=2))
