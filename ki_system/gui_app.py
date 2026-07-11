# -*- coding: utf-8 -*-
import tkinter as tk
import json
import threading
import time
import sqlite3
from tkinter import ttk, filedialog
from ki_system.memory import Memory
from ki_system.ingest import import_file
from ki_system import nlp
from ki_system.autonomous import AutonomousLoop
from ki_system.dialogue import DialogueManager
from ki_system.search import semantic_search, answer

NEURO_CORE = ["dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine"]
NEURO_NEW = ["adenosine", "endocannabinoid", "cortisol", "histamine", "orexin", "bdnf"]
NEURO_LABELS = {
    "dopamine": "DA", "serotonin": "5-HT", "glutamate": "GLU", "gaba": "GABA",
    "noradrenaline": "NA", "acetylcholine": "ACh", "adenosine": "ADE",
    "endocannabinoid": "ECB", "cortisol": "CORT", "histamine": "HIS",
    "orexin": "ORX", "bdnf": "BDNF",
}
NEURO_FULL = {
    "dopamine": "Dopamin", "serotonin": "Serotonin", "glutamate": "Glutamat",
    "gaba": "GABA", "noradrenaline": "Noradrenalin", "acetylcholine": "Acetylcholin",
    "adenosine": "Adenosin", "endocannabinoid": "Endocannabinoide (2-AG)",
    "cortisol": "Cortisol", "histamine": "Histamin", "orexin": "Orexin",
    "bdnf": "BDNF (Wachstumsfaktor)",
}
NEURO_COLORS = {
    "dopamine": "#e6b800", "serotonin": "#2ca02c", "glutamate": "#d95f0e",
    "gaba": "#1f77b4", "noradrenaline": "#9467bd", "acetylcholine": "#17becf",
    "adenosine": "#8c564b", "endocannabinoid": "#7f7f7f", "cortisol": "#d62728",
    "histamine": "#e377c2", "orexin": "#ff7f0e", "bdnf": "#2aa198",
}

def _clamp01(x):
    try:
        x = float(str(x).strip().strip('"').strip("'"))
    except Exception:
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x

def _table_exists(con, table):
    try:
        return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None
    except Exception:
        return False

def _columns(con, table):
    try:
        return set(c[1] for c in con.execute("PRAGMA table_info(" + table + ")").fetchall())
    except Exception:
        return set()

def _kv(con, table):
    if not _table_exists(con, table):
        return {}
    cs = _columns(con, table)
    if "key" not in cs or "value" not in cs:
        return {}
    try:
        return dict(con.execute("SELECT key,value FROM " + table).fetchall())
    except Exception:
        return {}

def _find_kv(con, keynames):
    want = [k.lower() for k in keynames]
    try:
        tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    except Exception:
        return None
    for t in tabs:
        cs = _columns(con, t)
        if "key" in cs and "value" in cs:
            d = _kv(con, t)
            low = {}
            for k, v in d.items():
                low[str(k).lower()] = v
            for w in want:
                if w in low:
                    return low[w]
    return None

def read_all_neuromods(con):
    sleep = _kv(con, "phase6a_neuromodulated_sleep_state")
    vals = {}
    for k in ("dopamine", "serotonin", "glutamate", "gaba", "noradrenaline",
              "acetylcholine", "histamine", "orexin", "bdnf"):
        vals[k] = _clamp01(sleep.get(k, 0.0))
    ade = _kv(con, "phase7a_adenosine_state").get("adenosine_level")
    if ade is None:
        ade = _find_kv(con, ["adenosine_level", "adenosine"])
    vals["adenosine"] = _clamp01(ade if ade is not None else 0.0)
    ecb = _kv(con, "phase7b_endocannabinoid_state").get("endocannabinoid_2ag")
    if ecb is None:
        ecb = _find_kv(con, ["endocannabinoid_2ag", "2ag_current", "two_ag_level"])
    vals["endocannabinoid"] = _clamp01(ecb if ecb is not None else 0.0)
    cort = _kv(con, "cortisol_state").get("cortisol_level")
    vals["cortisol"] = _clamp01(cort if cort is not None else 0.0)
    regimes = {
        "orexin": _kv(con, "phase7f_orexin_state").get("last_regime", "n/a"),
        "bdnf": _kv(con, "phase7g_bdnf_state").get("last_regime", "n/a"),
        "cortisol": _kv(con, "cortisol_state").get("last_regime", "n/a"),
        "histamine": _kv(con, "phase7e_histamine_state").get("last_regime", "n/a"),
    }
    asleep = ((vals["adenosine"] >= 0.6 and vals["histamine"] <= 0.45)
              or regimes["histamine"] == "sleep_permissive")
    regimes["_asleep"] = bool(asleep)
    return vals, regimes

def compute_mood(vals, regimes):
    cortisol = vals.get("cortisol", 0.0)
    adeno = vals.get("adenosine", 0.0)
    orx = vals.get("orexin", 0.0)
    bdnf = vals.get("bdnf", 0.0)
    glu = vals.get("glutamate", 0.0)
    his = vals.get("histamine", 0.0)
    asleep = regimes.get("_asleep", False)
    if cortisol >= 0.6:
        return ("(>_<)", "Gestresst")
    if asleep or adeno >= 0.75:
        return ("(-_-) zzz", "Schlaeft")
    if regimes.get("orexin") == "curious_drive" and regimes.get("bdnf") == "growth":
        return ("(^o^)/", "Wissbegierig")
    if regimes.get("bdnf") == "growth":
        return ("(^_^)v", "Wachsend")
    if glu >= 0.65 or orx >= 0.65:
        return ("(o_o)/", "Explorativ")
    return ("(^_^)", "Ausgewogen")

class NeuroTooltip:
    def __init__(self, master):
        self.master = master
        self.tip = None
    def show(self, x, y, text):
        self.hide()
        self.tip = tk.Toplevel(self.master)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        tk.Label(self.tip, text=text, bg="#ffffe0", relief=tk.SOLID, borderwidth=1,
                 font=("Arial", 9)).pack()
        self.tip.geometry("+%d+%d" % (x + 12, y + 12))
    def hide(self):
        if self.tip is not None:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None

class NeuromodulatorBars(ttk.Frame):
    def __init__(self, master, width=320, height=210):
        super().__init__(master)
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(self, width=width, height=height, bg="white",
                                highlightthickness=1, highlightbackground="#cccccc")
        self.canvas.pack(anchor=tk.W, pady=(4, 4))
        self.hitboxes = []
        self.tooltip = NeuroTooltip(self)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", lambda e: self.tooltip.hide())
        self.draw({k: 0.0 for k in (NEURO_CORE + NEURO_NEW)})
    def _draw_row(self, keys, values, top_y, base_y):
        margin = 14
        bar_w = 26
        gap = 18
        x = margin
        for name in keys:
            value = _clamp01(values.get(name, 0.0))
            color = NEURO_COLORS.get(name, "#888888")
            label = NEURO_LABELS.get(name, name[:3].upper())
            usable_h = base_y - top_y
            h = usable_h * value
            self.canvas.create_rectangle(x, top_y, x + bar_w, base_y, outline="#dddddd", fill="#f7f7f7")
            self.canvas.create_rectangle(x, base_y - h, x + bar_w, base_y, outline=color, fill=color)
            self.canvas.create_text(x + bar_w / 2, base_y + 10, text=label, font=("Arial", 8))
            self.canvas.create_text(x + bar_w / 2, top_y - 6, text="%.2f" % value, font=("Arial", 7))
            self.hitboxes.append((x, x + bar_w, top_y - 12, base_y + 14, name))
            x += bar_w + gap
    def draw(self, values):
        self.canvas.delete("all")
        self.hitboxes = []
        row_h = (self.height - 20) / 2
        self._draw_row(NEURO_CORE, values, 16, 16 + row_h - 24)
        self._draw_row(NEURO_NEW, values, 16 + row_h + 10, 16 + 2 * row_h - 14)
    def _on_motion(self, event):
        for x0, x1, y0, y1, key in self.hitboxes:
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.tooltip.show(self.winfo_rootx() + event.x, self.winfo_rooty() + event.y, NEURO_FULL.get(key, key))
                return
        self.tooltip.hide()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Brainstem V8 Admin")
        self.geometry("1250x875")
        self.mem = Memory("ki_memory.sqlite3")
        self.dialogue = DialogueManager(self.mem)
        self.cancel = False
        self.auto_stop = False
        self.auto_running = False
        self.auto_loop = None
        self.head = None
        self.mode = "idle"
        self._cov_cache = None
        self._cov_ts = 0.0
        self._ui()
        self._create_floating_head()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh()
    def _ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        self.tabs = {}
        for n in ["Chat", "Import & Jobs", "Suche & Antwort", "Datenbank", "Fakten/Relationen", "Export/Konfig"]:
            f = ttk.Frame(nb, padding=8)
            nb.add(f, text=n)
            self.tabs[n] = f
        self._chat_tab()
        self._import_tab()
        self._search_tab()
        self._db_tab()
        self._facts_tab()
        self._export_tab()
    def _chat_tab(self):
        f = self.tabs["Chat"]
        self.chat_out = tk.Text(f, wrap=tk.WORD)
        self.chat_out.pack(fill=tk.BOTH, expand=True)
        self.chat_in = tk.StringVar()
        ttk.Entry(f, textvariable=self.chat_in).pack(fill=tk.X)
        ttk.Button(f, text="Senden", command=self.chat_send).pack(anchor=tk.W)
    def _import_tab(self):
        f = self.tabs["Import & Jobs"]
        ttk.Button(f, text="Import starten", command=self.pick_import).pack(anchor=tk.W)
        ttk.Button(f, text="Import/Lernen abbrechen", command=lambda: setattr(self, "cancel", True)).pack(anchor=tk.W)
        row = ttk.Frame(f)
        row.pack(anchor=tk.W, pady=(4, 2))
        self.auto_start_btn = ttk.Button(row, text="Autonom dauerhaft starten", command=self.auto_start)
        self.auto_start_btn.pack(side=tk.LEFT)
        self.auto_stop_btn = ttk.Button(row, text="Autonom stoppen", command=self.auto_stop_now, state=tk.DISABLED)
        self.auto_stop_btn.pack(side=tk.LEFT, padx=6)
        ttk.Label(f, text="Gesamtfortschritt (gelesene Chunks)", font=("Arial", 8)).pack(anchor=tk.W, pady=(6, 0))
        self.bar_total = ttk.Progressbar(f, maximum=100)
        self.bar_total.pack(fill=tk.X)
        ttk.Label(f, text="Aktueller GUI-Zyklus (Schritt/5)", font=("Arial", 8)).pack(anchor=tk.W, pady=(4, 0))
        self.bar_cycle = ttk.Progressbar(f, maximum=100)
        self.bar_cycle.pack(fill=tk.X)
        self.status = ttk.Label(f)
        self.status.pack(anchor=tk.W, pady=(2, 0))
        left = ttk.Frame(f)
        left.pack(fill=tk.X, anchor=tk.NW)
        ttk.Label(left, text="Digitale Botenstoffe", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(8, 0))
        self.neuro_text = ttk.Label(left, text="Neuromodulatoren: -")
        self.neuro_text.pack(anchor=tk.W)
        self.behavior_text = ttk.Label(left, text="Regime: -")
        self.behavior_text.pack(anchor=tk.W)
        self.trend_text = ttk.Label(left, text="Homeostase: -")
        self.trend_text.pack(anchor=tk.W)
        self.neuro_bars = NeuromodulatorBars(left)
        self.neuro_bars.pack(anchor=tk.W)
        legend = ("Legende: DA=Dopamin  5-HT=Serotonin  GLU=Glutamat  GABA=GABA  NA=Noradrenalin  ACh=Acetylcholin\n"
                  "ADE=Adenosin  ECB=Endocannabinoide  CORT=Cortisol  HIS=Histamin  ORX=Orexin  BDNF=Wachstumsfaktor")
        ttk.Label(left, text=legend, font=("Arial", 8), foreground="#555555", justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 4))
        self.log = tk.Text(f, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
    def _search_tab(self):
        f = self.tabs["Suche & Antwort"]
        self.q = tk.StringVar()
        ttk.Entry(f, textvariable=self.q).pack(fill=tk.X)
        ttk.Button(f, text="Suchen", command=self.do_search).pack(anchor=tk.W)
        ttk.Button(f, text="Antwort", command=self.do_answer).pack(anchor=tk.W)
        self.out = tk.Text(f, wrap=tk.WORD)
        self.out.pack(fill=tk.BOTH, expand=True)
    def _db_tab(self):
        f = self.tabs["Datenbank"]
        ttk.Button(f, text="Aktualisieren", command=self.refresh).pack(anchor=tk.W)
        self.docs = ttk.Treeview(f, columns=("id", "title", "kind", "path"), show="headings")
        for c in ("id", "title", "kind", "path"):
            self.docs.heading(c, text=c)
        self.docs.pack(fill=tk.BOTH, expand=True)
    def _facts_tab(self):
        f = self.tabs["Fakten/Relationen"]
        self.facts = ttk.Treeview(f, columns=("s", "r", "v", "conf"), show="headings")
        for c in ("s", "r", "v", "conf"):
            self.facts.heading(c, text=c)
        self.facts.pack(fill=tk.BOTH, expand=True)
    def _export_tab(self):
        f = self.tabs["Export/Konfig"]
        ttk.Label(f, text="Export").pack(anchor=tk.W)
        ttk.Button(f, text="Export JSON", command=self._safe_export_json).pack(anchor=tk.W, pady=(4, 0))
        ttk.Button(f, text="Export Fakten CSV", command=self._safe_export_facts).pack(anchor=tk.W, pady=(4, 8))
        ttk.Separator(f).pack(fill=tk.X, pady=8)
        ttk.Label(f, text="Max. ZIM-Artikel beim Import").pack(anchor=tk.W)
        self.max_articles = tk.IntVar(value=int(self.mem.get_setting("max_articles", 2000) or 2000))
        ttk.Spinbox(f, from_=1, to=1000000, textvariable=self.max_articles, width=12).pack(anchor=tk.W, pady=(4, 4))
        ttk.Button(f, text="Speichern", command=self.save_config).pack(anchor=tk.W)
        self.config_status = ttk.Label(f, text="Aktueller Wert: " + str(self.mem.get_setting("max_articles", 2000)))
        self.config_status.pack(anchor=tk.W, pady=(8, 0))
        ttk.Separator(f).pack(fill=tk.X, pady=12)
        ttk.Label(f, text="Achtung: entfernt alle gelernten Daten, ZIM-Korpus bleibt erhalten.",
        foreground="#b00000").pack(anchor=tk.W)
        self.reset_btn = ttk.Button(f, text="Lernsystem zuruecksetzen (Korpus bleibt)", command=self.reset_learning_gui)
        self.reset_btn.pack(anchor=tk.W, pady=(4, 0))
    def _create_floating_head(self):
        self.head = tk.Toplevel(self)
        self.head.overrideredirect(True)
        self.head.attributes("-topmost", True)
        frame = tk.Frame(self.head, bg="#f0f0f0", relief=tk.RIDGE, borderwidth=2)
        frame.pack()
        self.mood_emoji = tk.Label(frame, text="(^_^)", font=("Consolas", 22, "bold"), bg="#f0f0f0", width=11, anchor="center")
        self.mood_emoji.pack(padx=6, pady=(6, 0))
        self.mood_name = tk.Label(frame, text="Ausgewogen", font=("Arial", 10), bg="#f0f0f0", anchor="center")
        self.mood_name.pack(padx=6, pady=(0, 6))
        self.update_idletasks()
        try:
            hx = self.winfo_x() + self.winfo_width() + 8
            hy = self.winfo_y() + 40
        except Exception:
            hx, hy = 100, 100
        self.head.geometry("+%d+%d" % (hx, hy))
        self._drag = {"x": 0, "y": 0}
        for w in (self.head, frame, self.mood_emoji, self.mood_name):
            w.bind("<Button-1>", self._head_press)
            w.bind("<B1-Motion>", self._head_drag)
    def _head_press(self, event):
        self._drag["x"] = event.x_root - self.head.winfo_x()
        self._drag["y"] = event.y_root - self.head.winfo_y()
    def _head_drag(self, event):
        self.head.geometry("+%d+%d" % (event.x_root - self._drag["x"], event.y_root - self._drag["y"]))
    def _on_close(self):
        try:
            if self.head is not None:
                self.head.destroy()
        except Exception:
            pass
        self.destroy()
    def _safe_export_json(self):
        try:
            self.mem.export_json("export_ki_system.json")
            self.config_status.configure(text="Export JSON gespeichert: export_ki_system.json")
        except Exception as e:
            self.config_status.configure(text="Export JSON Fehler: " + str(e))
    def _safe_export_facts(self):
        try:
            self.mem.export_facts_csv("facts.csv")
            self.config_status.configure(text="Fakten CSV gespeichert: facts.csv")
        except Exception as e:
            self.config_status.configure(text="Fakten CSV Fehler: " + str(e))
    def save_config(self):
        try:
            value = max(1, int(self.max_articles.get()))
            self.mem.set_setting("max_articles", value)
            self.config_status.configure(text="Aktueller Wert: %d" % value)
        except Exception as e:
            self.config_status.configure(text="Speichern fehlgeschlagen: " + str(e))
    def reset_learning_gui(self):
        from tkinter import messagebox
        if self.auto_running:
            messagebox.showwarning("Reset", "Bitte zuerst 'Autonom stoppen'.")
            return
        confirm = messagebox.askyesno("Lernsystem zuruecksetzen",
            "Wirklich ALLE gelernten Daten loeschen?\nDer ZIM-Korpus (Chunks) bleibt erhalten.\nEin Backup wird automatisch angelegt.")
        if not confirm:
            return
        def _worker():
            try:
                import importlib.util, pathlib
                root = pathlib.Path(__file__).resolve().parent.parent
                mod_path = root / "reset_learning.py"
                spec = importlib.util.spec_from_file_location("reset_learning", str(mod_path))
                rl = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(rl)
                db = str(root / "ki_memory.sqlite3")
                self.println("Lern-Reset gestartet ...")
                rep = rl.reset_learning(db, dry_run=False)
                wiped = len(rep.get("deleted", {}))
                total = 0
                for v in rep.get("deleted", {}).values():
                    if isinstance(v, int):
                        total += v
                self.println("Backup: " + str(rep.get("backup")))
                self.println("Geleerte Tabellen: %d | geloeschte Zeilen: %d" % (wiped, total))
                self.println("FERTIG: Lernsystem zurueckgesetzt, Korpus bleibt erhalten.")
                self.refresh()
            except Exception as e:
                self.println("Reset-FEHLER: " + str(e))
        import threading
        threading.Thread(target=_worker, daemon=True).start()           
    def println(self, msg):
        self.after(0, lambda: (self.log.insert(tk.END, str(msg) + "\n"), self.log.see(tk.END)))
    def progress(self, c, t, msg=""):
        if self.mode == "learn":
            return
        self.after(0, lambda: (self.bar_cycle.configure(value=(c / max(1, t)) * 100),
                               self.status.configure(text="%s/%s %s" % (c, t, msg))))
    def _set_cycle_bar(self, step, total):
        self.after(0, lambda: self.bar_cycle.configure(value=(step / max(1, total)) * 100))
    def _corpus_stats(self):
        now = time.time()
        if self._cov_cache is not None and (now - self._cov_ts) < 10.0:
            return self._cov_cache
        con = None
        covered = 0; total = 0; hypo = 0
        try:
            con = sqlite3.connect("ki_memory.sqlite3", timeout=5)
            r = con.execute("SELECT COUNT(*) FROM chunks").fetchone()
            total = r[0] if r else 0
            try:
                r = con.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_attention_scores").fetchone()
                covered = r[0] if r else 0
            except Exception:
                covered = 0
            try:
                r = con.execute("SELECT COUNT(*) FROM context_hypotheses").fetchone()
                hypo = r[0] if r else 0
            except Exception:
                hypo = 0
        except Exception:
            pass
        finally:
            if con is not None:
                try: con.close()
                except Exception: pass
        self._cov_cache = (covered, total, hypo)
        self._cov_ts = now
        return self._cov_cache
    def chat_send(self):
        t = self.chat_in.get().strip()
        if t:
            r = self.dialogue.respond(t)
            self.chat_out.insert(tk.END, "Du: " + t + "\n\nAntwort:\n" + r.response + "\n\n")
            self.chat_in.set("")
    def pick_import(self):
        paths = filedialog.askopenfilenames(filetypes=[("Unterstuetzt", "*.txt *.pdf *.zim"), ("Alle", "*.*")])
        self.cancel = False
        if paths:
            threading.Thread(target=self._import, args=(paths,), daemon=True).start()
    def _import(self, paths):
        self.mode = "import"
        try:
            for p in paths:
                try:
                    self.println("Import: " + p)
                    self.println(str(import_file(p, self.mem, int(self.mem.get_setting("max_articles", 2000) or 2000), self.progress, lambda: self.cancel, True)))
                except Exception as e:
                    self.println("FEHLER: " + str(e))
        finally:
            self.mode = "idle"
        self.refresh()
    def learn(self):
        threading.Thread(target=lambda: self.println("Lernen: " + str(nlp.learn_from_memory(self.mem, self.progress, lambda: self.cancel))), daemon=True).start()
    def _set_auto(self, r):
        def _apply():
            self.auto_start_btn.configure(state=tk.DISABLED if r else tk.NORMAL)
            self.auto_stop_btn.configure(state=tk.NORMAL if r else tk.DISABLED)
            if hasattr(self, "reset_btn"):
                self.reset_btn.configure(state=tk.DISABLED if r else tk.NORMAL)
        self.after(0, _apply)        
    def auto_start(self):
        if self.auto_running:
            return
        self.auto_stop = False
        self.auto_running = True
        self.cancel = False
        self._set_auto(True)
        self.println("Autonomes Dauerlernen gestartet.")
        threading.Thread(target=self._auto_worker, daemon=True).start()
    def auto_stop_now(self):
        self.auto_stop = True
        self.cancel = True
        if self.auto_loop:
            try: self.auto_loop.stop()
            except Exception: pass
        self.println("Stop-Anforderung gesetzt.")
    def _auto_worker(self):
        n = 0
        self.mode = "learn"
        try:
            while not self.auto_stop:
                n += 1
                self.println("=== Autonomer Dauerlern-Zyklus %d ===" % n)
                self.auto_loop = AutonomousLoop(self.mem)
                self._set_cycle_bar(0, 5)
                for step in range(5):
                    if self.auto_stop:
                        break
                    r = self.auto_loop.cycle()
                    self.println(json.dumps(r, ensure_ascii=False, indent=2))
                    self._set_cycle_bar(step + 1, 5)
                    self.refresh()
                self.auto_loop = None
                for _ in range(10):
                    if self.auto_stop:
                        break
                    time.sleep(.2)
        finally:
            self.auto_running = False
            self.auto_stop = False
            self.cancel = False
            self.mode = "idle"
            self._set_auto(False)
            self.refresh()
            self.println("Autonomes Dauerlernen gestoppt.")
    def do_search(self):
        self.out.delete("1.0", tk.END)
        for h in semantic_search(self.mem, self.q.get(), 25):
            self.out.insert(tk.END, "%.3f [%s] %s | Chunk %s\n%s\n\n" % (h.score, h.method, h.title, h.chunk_id, h.text[:1000]))
    def do_answer(self):
        self.out.delete("1.0", tk.END)
        self.out.insert(tk.END, json.dumps(answer(self.mem, self.q.get()), ensure_ascii=False, indent=2))
    def _neuro_con(self):
        for attr in ("db", "con", "conn", "connection", "sqlite"):
            c = getattr(self.mem, attr, None)
            if isinstance(c, sqlite3.Connection):
                return c, False
        return sqlite3.connect("ki_memory.sqlite3", timeout=5), True
    def _update_neuro_dashboard(self):
        con, should_close = self._neuro_con()
        try:
            vals, regimes = read_all_neuromods(con)
        finally:
            if should_close:
                try:
                    con.close()
                except Exception:
                    pass
        core_line = " | ".join("%s %.2f" % (NEURO_LABELS[k], vals.get(k, 0.0)) for k in NEURO_CORE)
        self.neuro_text.configure(text="Neuromodulatoren: " + core_line)
        self.behavior_text.configure(text="Regime: Orexin %s (%.2f) | BDNF %s (%.2f) | Cortisol %s (%.2f)" % (
            regimes.get("orexin", "n/a"), vals.get("orexin", 0.0),
            regimes.get("bdnf", "n/a"), vals.get("bdnf", 0.0),
            regimes.get("cortisol", "n/a"), vals.get("cortisol", 0.0)))
        self.trend_text.configure(text="Homeostase: ADE %.2f | ECB %.2f | HIS %.2f" % (
            vals.get("adenosine", 0.0), vals.get("endocannabinoid", 0.0), vals.get("histamine", 0.0)))
        self.neuro_bars.draw(vals)
        emoji, name = compute_mood(vals, regimes)
        if self.mood_emoji is not None:
            self.mood_emoji.configure(text=emoji)
        if self.mood_name is not None:
            self.mood_name.configure(text=name)
    def refresh(self):
        self.after(0, self._refresh)
    def _refresh(self):
        try:
            covered, total, hypo = self._corpus_stats()
            pct = (100.0 * covered / total) if total else 0.0
            st = {}
            try:
                st = self.mem.stats()
            except Exception:
                st = {}
            self.status.configure(text="Chunks gelesen %d/%d (%.1f%%) | Fakten %d | Relationen %d | Ontologie %d | Fragen %d | Hypothesen %d" % (
                covered, total, pct, st.get("facts", 0), st.get("relations", 0), st.get("ontology", 0), st.get("questions", 0), hypo))
            try:
                self.bar_total.configure(value=pct)
            except Exception:
                pass
            if hasattr(self, "neuro_text"):
                try:
                    self._update_neuro_dashboard()
                except Exception as exc:
                    self.neuro_text.configure(text="Neuromodulatoren: nicht verfuegbar: " + str(exc))
            if hasattr(self, "docs"):
                self.docs.delete(*self.docs.get_children())
                for d in self.mem.rows("SELECT * FROM documents ORDER BY created_at DESC LIMIT 2000"):
                    self.docs.insert("", tk.END, values=(d["id"], d["title"], d["kind"], d["path"]))
            if hasattr(self, "facts"):
                self.facts.delete(*self.facts.get_children())
                for f in self.mem.rows("SELECT * FROM facts ORDER BY created_at DESC LIMIT 2000"):
                    self.facts.insert("", tk.END, values=(f["subject"], f["relation"], f["value"], round(f["confidence"], 2)))
        finally:
            try:
                self.after(2000, self._refresh)
            except Exception:
                pass

def main():
    App().mainloop()
