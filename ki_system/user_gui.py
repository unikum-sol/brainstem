import tkinter as tk, json, os
from tkinter import ttk
from ki_system.memory import Memory
from ki_system.dialogue import DialogueManager
from ki_system.search import semantic_search, answer
from ki_system import gui_theme as _theme


class UserApp(tk.Tk):
    def __init__(self, db_path='ki_memory.sqlite3'):
        super().__init__()
        self.title('KI-System V8 User (Read-Only)')
        self.geometry('1000x700')
        self.minsize(760, 520)
        self.db_path = str(db_path)
        self.mem = Memory(db_path, readonly=True)
        self.dialogue = DialogueManager(self.mem)
        try:
            theme_name = str(self.mem.get_setting('gui_theme', 'dark') or 'dark')
        except Exception:
            theme_name = 'dark'
        self.theme = _theme.Theme(self, theme_name)
        self._ui()

    def _ui(self):
        bar, self._theme_buttons, self._update_theme_button = _theme.app_header(
            self, self.theme, 'Dialog (nur lesend)  ·  Datenbank: ' + os.path.basename(self.db_path), self._choose_theme)
        self.theme_btn = self._theme_buttons['light']
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=(14, 0))
        ttk.Label(bar, text='●  Read-Only', style='PillInfo.TLabel').pack(side=tk.RIGHT)
        nb = ttk.Notebook(self); nb.pack(fill=tk.BOTH, expand=True)
        chat = ttk.Frame(nb, padding=(14, 12, 14, 14)); search = ttk.Frame(nb, padding=(14, 12, 14, 14))
        nb.add(chat, text='Chat'); nb.add(search, text='Suche & Antwort')
        self.nb = nb

        c = _theme.card(chat, 'Dialog', 'Fragen an das Gedächtnis stellen. Enter sendet.')
        c.pack(fill=tk.BOTH, expand=True)
        ttk.Label(c, text='Read-Only Sitzung: Chatverlauf wird in dieser Ansicht NICHT dauerhaft gespeichert.',
                  style='PillWarn.TLabel').pack(anchor=tk.W, pady=(0, 8))
        box, self.chat_out = _theme.scrolled_text(self.theme, c, font='ui')
        box.pack(fill=tk.BOTH, expand=True)
        self.chat_out.insert(tk.END, 'Noch keine Unterhaltung. Schreibe unten eine Frage und drücke Enter.\n\n', 'hint')
        self._chat_placeholder = True
        row = ttk.Frame(c, style='Inner.TFrame'); row.pack(fill=tk.X, pady=(10, 0))
        self.chat_in = tk.StringVar()
        e = ttk.Entry(row, textvariable=self.chat_in); e.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e.bind('<Return>', lambda ev: self.chat_send())
        ttk.Button(row, text='Senden', style='Accent.TButton', command=self.chat_send).pack(side=tk.LEFT, padx=(8, 0))

        s = _theme.card(search, 'Suche & Antwort', 'Suchen (Enter): Trefferliste der passendsten Textstellen.   '
                                                   'Antwort: zusammengesetzte Antwort mit Belegen (JSON).')
        s.pack(fill=tk.BOTH, expand=True)
        row = ttk.Frame(s, style='Inner.TFrame'); row.pack(fill=tk.X, pady=(0, 10))
        self.q = tk.StringVar()
        e = ttk.Entry(row, textvariable=self.q); e.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e.bind('<Return>', lambda ev: self.do_search())
        ttk.Button(row, text='Suchen', style='Accent.TButton', command=self.do_search).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(row, text='Antwort', command=self.do_answer).pack(side=tk.LEFT, padx=(8, 0))
        box, self.out = _theme.scrolled_text(self.theme, s, font='ui')
        box.pack(fill=tk.BOTH, expand=True)
        self.out.insert(tk.END, 'Noch keine Ergebnisse. Suchbegriff eingeben und „Suchen“ oder „Antwort“ wählen.', 'hint')

    def _choose_theme(self, name):
        if name != self.theme.name:
            self.toggle_theme()

    def set_theme(self, name):
        self.theme.apply(name)
        self._update_theme_button()

    def toggle_theme(self):
        # read-only session: the choice is not persisted
        self.set_theme('light' if self.theme.name == 'dark' else 'dark')

    def chat_send(self):
        t = self.chat_in.get().strip()
        if not t: return
        r = self.dialogue.respond(t)
        if getattr(self, '_chat_placeholder', False):
            self.chat_out.delete('1.0', tk.END); self._chat_placeholder = False
        self.chat_out.insert(tk.END, 'Du: ', 'you'); self.chat_out.insert(tk.END, t + '\n\n')
        self.chat_out.insert(tk.END, 'Antwort:\n', ('bot', 'answer')); self.chat_out.insert(tk.END, r.response + '\n', 'answer')
        self.chat_out.insert(tk.END, '\n')
        self.chat_out.see(tk.END); self.chat_in.set('')

    def do_search(self):
        self.out.delete('1.0', tk.END)
        _theme.render_hits(self.out, list(semantic_search(self.mem, self.q.get(), 25)), self.q.get())

    def do_answer(self): self.out.delete('1.0', tk.END); self.out.insert(tk.END, json.dumps(answer(self.mem, self.q.get()), ensure_ascii=False, indent=2), 'mono')
