# -*- coding: utf-8 -*-
import tkinter as tk
import csv
import json
import threading
import time
import sqlite3
from datetime import datetime
from tkinter import ttk, filedialog
from ki_system.memory import Memory
from ki_system.ingest import import_file
from ki_system.autonomous import AutonomousLoop
from ki_system.dialogue import DialogueManager
from ki_system.search import semantic_search, answer
from ki_system import v8_cycle_diagnostics_release as _cycle_diagnostics
from ki_system import v8_wal_maintenance_release as _wal_maintenance


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

def read_integration_transparency(con):
    sleep = _kv(con, "phase6a_neuromodulated_sleep_state")
    out = {"tonic_weight": _clamp01(sleep.get("tonic_weight", 0.18))}
    for k in ("dopamine", "serotonin", "noradrenaline", "acetylcholine"):
        out[k + "_phasic"] = _clamp01(sleep.get(k + "_phasic", sleep.get(k, 0.0)))
    evidence_state = "n/a"
    try:
        if _table_exists(con, "phase6a_sleep_replay_cycles"):
            row = con.execute(
                "SELECT evidence_state FROM phase6a_sleep_replay_cycles ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                evidence_state = str(row[0])
    except Exception:
        pass
    out["phase6a_evidence_state"] = evidence_state
    return out

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
    switch = _kv(con, "cooperative_sleep_wake_state")
    sleep_state = str(switch.get("state", "")).strip().lower()
    regimes["_asleep"] = (sleep_state == "sleep")
    regimes["sleep_state"] = sleep_state if sleep_state in ("wake", "sleep") else "n/a"
    regimes["sleep_upper"] = _clamp01(switch.get("upper_threshold", 0.0))
    regimes["sleep_lower"] = _clamp01(switch.get("lower_threshold", 0.0))
    regimes["sleep_position"] = _clamp01(switch.get("pressure_position", 0.0))
    try:
        regimes["sleep_dwell"] = int(float(switch.get("dwell_cycles", 0)))
    except (TypeError, ValueError):
        regimes["sleep_dwell"] = 0
    regimes["sleep_reason"] = str(switch.get("transition_reason", "n/a"))
    regimes["maturity"] = _clamp01(_kv(con, "phase7a_adenosine_state").get("developmental_maturity", 0.0))
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
    if asleep:
        return ("(-_-) zzz", "Schlaeft und konsolidiert")
    if adeno >= regimes.get("sleep_upper", 1.0) - 0.05 and regimes.get("sleep_upper", 0.0) > 0.0:
        return ("(-.-)", "Muede")
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
    CHANGE_THRESHOLD = 0.005

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
        self._items = {}
        self._last_values = {}
        self._built = False
        self.draw({k: 0.0 for k in (NEURO_CORE + NEURO_NEW)})

    def _layout_row(self, keys, top_y, base_y):
        margin = 14
        bar_w = 26
        gap = 18
        x = margin
        out = []
        for name in keys:
            out.append((name, x, top_y, base_y, bar_w))
            x += bar_w + gap
        return out

    def _build_items(self, values):
        row_h = (self.height - 20) / 2
        layout = (self._layout_row(NEURO_CORE, 16, 16 + row_h - 24) +
                  self._layout_row(NEURO_NEW, 16 + row_h + 10, 16 + 2 * row_h - 14))
        self.hitboxes = []
        for name, x, top_y, base_y, bar_w in layout:
            value = _clamp01(values.get(name, 0.0))
            color = NEURO_COLORS.get(name, "#888888")
            label = NEURO_LABELS.get(name, name[:3].upper())
            usable_h = base_y - top_y
            h = usable_h * value
            self.canvas.create_rectangle(x, top_y, x + bar_w, base_y, outline="#dddddd", fill="#f7f7f7")
            fill_id = self.canvas.create_rectangle(x, base_y - h, x + bar_w, base_y, outline=color, fill=color)
            self.canvas.create_text(x + bar_w / 2, base_y + 10, text=label, font=("Arial", 8))
            value_id = self.canvas.create_text(x + bar_w / 2, top_y - 6, text="%.2f" % value, font=("Arial", 7))
            self._items[name] = {
                "fill_id": fill_id, "value_id": value_id,
                "x": x, "top_y": top_y, "base_y": base_y, "bar_w": bar_w,
            }
            self._last_values[name] = value
            self.hitboxes.append((x, x + bar_w, top_y - 12, base_y + 14, name))
        self._built = True

    def draw(self, values):
        if not self._built:
            self._build_items(values)
            return
        for name, item in self._items.items():
            value = _clamp01(values.get(name, 0.0))
            last = self._last_values.get(name, None)
            if last is not None and abs(value - last) < self.CHANGE_THRESHOLD:
                continue
            top_y = item["top_y"]; base_y = item["base_y"]; x = item["x"]; bar_w = item["bar_w"]
            usable_h = base_y - top_y
            h = usable_h * value
            self.canvas.coords(item["fill_id"], x, base_y - h, x + bar_w, base_y)
            self.canvas.itemconfig(item["value_id"], text="%.2f" % value)
            self._last_values[name] = value
    def _on_motion(self, event):
        for x0, x1, y0, y1, key in self.hitboxes:
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.tooltip.show(self.winfo_rootx() + event.x, self.winfo_rooty() + event.y, NEURO_FULL.get(key, key))
                return
        self.tooltip.hide()

class App(tk.Tk):
    LOGGER_FLOAT_DEADBAND = 0.0005
    LOGGER_HEARTBEAT_SECONDS = 600.0

    def __init__(self, db_path="ki_memory.sqlite3"):
        super().__init__()
        self.title("Brainstem V8 Admin")
        self.geometry("1250x875")
        self.db_path = str(db_path)
        self.mem = Memory(self.db_path)
        self.dialogue = DialogueManager(self.mem)
        self.cancel = False
        self.auto_stop = False
        self.auto_running = False
        self.auto_loop = None
        self._closing = False
        self._shutdown_poll_id = None
        self._auto_thread = None
        self._drift_thread = None
        self._import_thread = None
        self._reset_thread = None
        self.head = None
        self.mode = "idle"
        self._logger_file = None
        self._logger_writer = None
        self._logger_path = None
        self._logger_fields = None
        self._logger_last_written = None
        self._logger_last_seen = None
        self._logger_last_write_ts = 0.0
        self._logger_rows_written = 0
        self._logger_rows_skipped = 0
        self._cov_cache = None
        self._cov_ts = 0.0
        self._stats_cache = None
        self._stats_ts = 0.0
        self._current_tab_name = "Chat"
        self._ui()
        self._gui_pending = []
        self._gui_pending_lock = threading.Lock()
        self._gui_pump_scheduled = True
        self._refresh_running = False
        self._refresh_requested = False
        self._refresh_timer_id = None
        self._gui_pump_id = self.after(50, self._gui_pump)
        self._create_floating_head()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh_timer_start()
    def _ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        self.nb = nb
        self.tabs = {}
        for n in ["Chat", "Import & Jobs", "Suche & Antwort", "Datenbank", "Fakten/Relationen", "Export/Konfig", "Drift-Report"]:
            f = ttk.Frame(nb, padding=8)
            nb.add(f, text=n)
            self.tabs[n] = f
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._chat_tab()
        self._import_tab()
        self._search_tab()
        self._db_tab()
        self._facts_tab()
        self._export_tab()
        self._drift_tab()
    def _on_tab_changed(self, event=None):
        try:
            self._current_tab_name = self.nb.tab(self.nb.select(), "text")
        except Exception:
            pass
        self.refresh()
    def _chat_tab(self):
        f = self.tabs["Chat"]
        self.chat_out = tk.Text(f, wrap=tk.WORD)
        self.chat_out.pack(fill=tk.BOTH, expand=True)
        self.chat_in = tk.StringVar()
        ttk.Entry(f, textvariable=self.chat_in).pack(fill=tk.X)
        ttk.Button(f, text="Senden", command=self.chat_send).pack(anchor=tk.W)
    def _import_tab(self):
        f = self.tabs["Import & Jobs"]
        import_row = ttk.Frame(f)
        import_row.pack(anchor=tk.W, pady=(0, 2))
        ttk.Button(import_row, text="Import starten", command=self.pick_import).pack(side=tk.LEFT)
        ttk.Label(import_row, text="Korpussprache:").pack(side=tk.LEFT, padx=(12, 4))
        stored_lang = str(self.mem.get_setting("corpus_language", "de") or "de")
        self.corpus_language = tk.StringVar(value=stored_lang if stored_lang in ("de", "en") else "de")
        lang_box = ttk.Combobox(import_row, textvariable=self.corpus_language, values=("de", "en"),
                                 width=4, state="readonly")
        lang_box.pack(side=tk.LEFT)
        lang_box.bind("<<ComboboxSelected>>", self._on_corpus_language_changed)
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
        self.integration_text = ttk.Label(left, text="Integration (phasisch/tonisch): -")
        self.integration_text.pack(anchor=tk.W)
        self.evidence_text = ttk.Label(left, text="Phase6a Evidenzstatus: -")
        self.evidence_text.pack(anchor=tk.W)
        self.neuro_bars = NeuromodulatorBars(left)
        self.neuro_bars.pack(anchor=tk.W)
        legend = ("Legende: DA=Dopamin  5-HT=Serotonin  GLU=Glutamat  GABA=GABA  NA=Noradrenalin  ACh=Acetylcholin\n"
                  "ADE=Adenosin  ECB=Endocannabinoide  CORT=Cortisol  HIS=Histamin  ORX=Orexin  BDNF=Wachstumsfaktor\n"
                  "Integrationszeile: phasisch/tonisch = Phase6a-Rohwert / final gemischter Wert (w=tonic_weight, "
                  "cortisol-gesteuert). GLU/GABA bleiben ausschliesslich von Phase 7c verantwortet.")
        ttk.Label(left, text=legend, font=("Arial", 8), foreground="#555555", justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 4))
        ttk.Separator(left).pack(fill=tk.X, pady=(8, 4))
        ttk.Label(left, text="GUI-Wertelogger (fortlaufende CSV)", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        logger_row = ttk.Frame(left)
        logger_row.pack(anchor=tk.W, pady=(2, 0))
        self.gui_logger_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(logger_row, text="Logger aktiv", variable=self.gui_logger_enabled,
                        command=self._logger_toggle).pack(side=tk.LEFT)
        self.gui_logger_changes_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(logger_row, text="Nur bei Aenderung loggen",
                        variable=self.gui_logger_changes_only).pack(side=tk.LEFT, padx=(12, 0))
        self.logger_status = ttk.Label(left, text="Logger inaktiv")
        self.logger_status.pack(anchor=tk.W, pady=(2, 4))
        self.log = tk.Text(f, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)
    def _on_corpus_language_changed(self, event=None):
        value = self.corpus_language.get()
        if value not in ("de", "en"):
            value = "de"
            self.corpus_language.set(value)
        self.mem.set_setting("corpus_language", value)
        self.println("Korpussprache auf '" + value + "' gesetzt (wirkt ab dem naechsten Zyklus).")
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
        """Kooperativen Shutdown starten; Tk bleibt bis zum Worker-Ende aktiv."""
        if self._closing:
            return
        self._closing = True
        try:
            self.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception:
            pass
        self.cancel = True
        self.auto_stop = True
        self.drift_stop = True
        if self.auto_loop is not None:
            try:
                self.auto_loop.stop()
            except Exception:
                pass
        self._set_shutdown_status("Beenden angefordert. Laufender atomarer Schritt wird abgeschlossen ...")
        self._poll_shutdown()

    def _set_shutdown_status(self, text):
        try:
            if hasattr(self, "status"):
                self.status.configure(text=text)
        except Exception:
            pass
        try:
            if hasattr(self, "drift_status") and self.drift_running:
                self.drift_status.configure(text=text)
        except Exception:
            pass

    def _shutdown_threads(self):
        out = []
        for name in ("_auto_thread", "_drift_thread", "_import_thread", "_reset_thread"):
            thread = getattr(self, name, None)
            if thread is not None and thread.is_alive():
                out.append((name, thread))
        return out

    def _busy_operation_name(self):
        """Return a human-readable name of the currently running exclusive
        database operation (reset, import, autonomous learning, or drift
        test), or None if none of them is currently active."""
        live = {name for name, _ in self._shutdown_threads()}
        if "_reset_thread" in live:
            return "Lernsystem-Reset"
        if self.mode == "import" or "_import_thread" in live:
            return "Import"
        if self.auto_running or "_auto_thread" in live:
            return "Autonomes Lernen"
        if self.drift_running or "_drift_thread" in live:
            return "Drift-Test"
        return None

    def _poll_shutdown(self):
        live = self._shutdown_threads()
        if live or self.auto_running or self.drift_running or self.mode == "import":
            names = ", ".join(name.replace("_", "") for name, _ in live) or "Worker"
            self._set_shutdown_status("Sicheres Beenden. Warte auf: " + names)
            try:
                self._shutdown_poll_id = self.after(100, self._poll_shutdown)
            except Exception:
                pass
            return
        self._finalize_close()

    def _finalize_close(self):
        """Erst nach Worker-Ende DB und Fenster geordnet schliessen."""
        for name in ("_auto_thread", "_drift_thread", "_import_thread", "_reset_thread"):
            thread = getattr(self, name, None)
            if thread is not None:
                try:
                    thread.join(timeout=0)
                except Exception:
                    pass
                setattr(self, name, None)
        try:
            if getattr(self, "_logger_file", None) is not None:
                self._logger_flush_pending()
                self._logger_file.close()
                self._logger_file = None
        except Exception:
            pass
        try:
            db = getattr(self.mem, "db", None)
            if db is not None:
                db.commit()
        except Exception:
            pass
        try:
            close_fn = getattr(self.mem, "close", None)
            if callable(close_fn):
                close_fn()
            else:
                db = getattr(self.mem, "db", None)
                if db is not None:
                    db.close()
        except Exception:
            pass
        try:
            worker_mem = getattr(self, "_worker_mem", None)
            if worker_mem is not None:
                db = getattr(worker_mem, "db", None)
                if db is not None:
                    try:
                        db.commit()
                    except Exception:
                        pass
                    db.close()
        except Exception:
            pass
        try:
            if self.head is not None:
                self.head.destroy()
                self.head = None
        except Exception:
            pass
        for timer_attr in ("_refresh_timer_id", "_gui_pump_id", "_shutdown_poll_id"):
            timer_id = getattr(self, timer_attr, None)
            if timer_id is not None:
                try:
                    self.after_cancel(timer_id)
                except Exception:
                    pass
                setattr(self, timer_attr, None)
        try:
            self.destroy()
        except Exception:
            pass
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
        busy = self._busy_operation_name()
        if busy:
            messagebox.showwarning("Reset", "Bitte zuerst laufenden Vorgang beenden: " + busy)
            return
        confirm = messagebox.askyesno("Lernsystem zuruecksetzen",
            "Wirklich ALLE gelernten Daten loeschen?\nDer ZIM-Korpus (Chunks) bleibt erhalten.\nEin Backup wird automatisch angelegt.")
        if not confirm:
            return
        def _worker():
            try:
                import importlib.util, pathlib
                mod_path = pathlib.Path(__file__).resolve().parent / "reset_learning.py"
                spec = importlib.util.spec_from_file_location("reset_learning", str(mod_path))
                rl = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(rl)
                db = str(pathlib.Path(self.db_path).resolve())
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
        self._reset_thread = threading.Thread(target=_worker, name="brainstem-reset", daemon=False)
        self._reset_thread.start()           
    def println(self, msg):
        def _do():
            try:
                self.log.insert(tk.END, str(msg) + "\n")
                total = int(self.log.index("end-1c").split(".")[0])
                if total > 200:
                    self.log.delete("1.0", "%d.0" % (total - 200 + 1))
                self.log.see(tk.END)
            except Exception:
                pass
        self._gui_enqueue(_do)
    def _stageb_experiment_stats_line(self, con):
        def _kv(table):
            try:
                return dict(con.execute("SELECT key,value FROM " + table).fetchall())
            except Exception:
                return {}
        def _count(sql):
            try:
                return con.execute(sql).fetchone()[0]
            except Exception:
                return "?"
        gap_state = _kv("stageb_gap_detection_state")
        contra_state = _kv("stageb_contradiction_detection_state")
        revision_state = _kv("stageb_revision_state")
        promo_state = _kv("stageb_fact_promotion_state")
        open_gaps = _count("SELECT COUNT(*) FROM internal_learning_gaps WHERE status='open'")
        open_contra = _count("SELECT COUNT(*) FROM contradictions WHERE status IN ('open','resolvable')")
        unverified_contrasts = _count("SELECT COUNT(*) FROM contradictions WHERE status='unverified' AND relation='unverified_text_contrast'")
        facts_now = _count("SELECT COUNT(*) FROM facts")
        return ("Stage-B Erweiterung -> Gaps offen: %s (gesamt erzeugt: %s) | "
                "Widersprueche offen: %s (gesamt erkannt: %s) | Textkontraste ungeprueft: %s | Revisionen gesamt: %s | "
                "Facts: %s aktuell (%s erzeugt, %s zurueckgezogen)") % (
            open_gaps, gap_state.get("gaps_created_total", "0"),
            open_contra, contra_state.get("contradictions_created_total", "0"),
            unverified_contrasts, revision_state.get("total_revised", "0"),
            facts_now, promo_state.get("facts_promoted_total", "0"),
            promo_state.get("facts_retracted_total", "0"),
        )

    def _cycle_diag_text(self, n, step):
        import sqlite3
        lines = ["=== Autonomer Zyklus %d / Schritt %d ===" % (n, step)]
        try:
            con = sqlite3.connect(self.db_path, timeout=60)
            try:
                vals, regimes = read_all_neuromods(con)
                covered, total, hyp = self._corpus_stats()
                surv = part = weak = 0; thr = 0.0
                try:
                    r = con.execute("SELECT candidates_survived,candidates_participated,weakened,adaptive_threshold_avg FROM phase7d_slow_wave_cycles ORDER BY id DESC LIMIT 1").fetchone()
                    if r: surv, part, weak, thr = r[0], r[1], r[2], (r[3] or 0.0)
                except Exception: pass
                safe = []
                for t in ("facts", "relations", "questions"):
                    try: safe.append(con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0])
                    except Exception: safe.append("?")
                pct = (100.0 * covered / total) if total else 0.0
                lines.append("Gelesene Chunks: %d / %d (%.1f%%)" % (covered, total, pct))
                lines.append("Hypothesen gesamt: %d" % hyp)
                lines.append("Dopamin %.3f | Serotonin %.3f | Glutamat %.3f | GABA %.3f | Noradrenalin %.3f | Acetylcholin %.3f" % (
                    vals.get("dopamine", 0.0), vals.get("serotonin", 0.0), vals.get("glutamate", 0.0),
                    vals.get("gaba", 0.0), vals.get("noradrenaline", 0.0), vals.get("acetylcholine", 0.0)))
                lines.append("Adenosin %.3f | Endocannabinoide %.3f | Histamin %.3f | Orexin %.3f | BDNF %.3f | Cortisol %.3f" % (
                    vals.get("adenosine", 0.0), vals.get("endocannabinoid", 0.0), vals.get("histamine", 0.0),
                    vals.get("orexin", 0.0), vals.get("bdnf", 0.0), vals.get("cortisol", 0.0)))
                lines.append("Regime -> Orexin: %s | BDNF: %s | Cortisol: %s | Histamin: %s" % (
                    regimes.get("orexin", "n/a"), regimes.get("bdnf", "n/a"),
                    regimes.get("cortisol", "n/a"), regimes.get("histamine", "n/a")))
                lines.append("Schlaf -> Zustand: %s seit %d Zyklen | Adenosin %.3f (Schlaf ab %.3f, Wachen ab %.3f) | Reife %.1f%% | Letzter Wechsel: %s" % (
                    regimes.get("sleep_state", "n/a"), regimes.get("sleep_dwell", 0), vals.get("adenosine", 0.0),
                    regimes.get("sleep_upper", 0.0), regimes.get("sleep_lower", 0.0), 100.0 * regimes.get("maturity", 0.0),
                    regimes.get("sleep_reason", "n/a")))
                lines.append("7d Slow-Wave -> Survivors %s | Participated %s | Weakened %s | Schwelle %.3f" % (surv, part, weak, float(thr)))
                lines.append("SAFETY facts/relations/questions: %s" % safe)
                try:
                    lines.append(self._stageb_experiment_stats_line(con))
                except Exception as exc:
                    lines.append("Stage-B Erweiterung: nicht verfuegbar (" + str(exc) + ")")
            finally:
                con.close()
        except Exception as e:
            lines.append("(Diagnose nicht verfuegbar: " + str(e) + ")")
        return "\n".join(lines)
    def progress(self, c, t, msg=""):
        self._gui_enqueue(lambda: (self.bar_cycle.configure(value=c / max(1, t) * 100), self.status.configure(text='%s/%s %s' % (c, t, msg))))
    def _set_cycle_bar(self, step, total):
        self._gui_enqueue(lambda: self.bar_cycle.configure(value=step / max(1, total) * 100))
    def _corpus_stats(self):
        now = time.time()
        if self._cov_cache is not None and (now - self._cov_ts) < 10.0:
            return self._cov_cache
        con = None
        covered = 0; total = 0; hypo = 0
        try:
            con = sqlite3.connect(self.db_path, timeout=60)
            r = con.execute("SELECT COUNT(*) FROM chunks").fetchone()
            total = r[0] if r else 0
            try:
                r = con.execute("SELECT COUNT(*) FROM reading_queue WHERE COALESCE(read_count,0)>0").fetchone()
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
    def _cached_stats(self):
        now = time.time()
        if self._stats_cache is not None and (now - self._stats_ts) < 10.0:
            return self._stats_cache
        try:
            st = self.mem.stats()
        except Exception:
            st = {}
        self._stats_cache = st
        self._stats_ts = now
        return st
    def chat_send(self):
        t = self.chat_in.get().strip()
        if t:
            r = self.dialogue.respond(t)
            note = ""
            if not r.persisted and r.skip_reason and r.skip_reason != "memory_readonly":
                note = "\n[Hinweis: Konversation wurde NICHT gespeichert - " + r.skip_reason + "]"
            self.chat_out.insert(tk.END, "Du: " + t + "\n\nAntwort:\n" + r.response + note + "\n\n")
            self.chat_in.set("")
    def pick_import(self):
        busy = self._busy_operation_name()
        if busy and busy != "Import":
            from tkinter import messagebox
            messagebox.showwarning("Import", "Bitte zuerst laufenden Vorgang beenden: " + busy)
            return
        paths = filedialog.askopenfilenames(filetypes=[("Unterstuetzt", "*.txt *.pdf *.zim"), ("Alle", "*.*")])
        self.cancel = False
        if paths:
            self._import_thread = threading.Thread(target=self._import, args=(paths,), name="brainstem-import", daemon=False)
            self._import_thread.start()
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
    def _set_auto(self, r):
        def _apply():
            self.auto_start_btn.configure(state=tk.DISABLED if r else tk.NORMAL)
            self.auto_stop_btn.configure(state=tk.NORMAL if r else tk.DISABLED)
            if hasattr(self, "reset_btn"):
                self.reset_btn.configure(state=tk.DISABLED if r else tk.NORMAL)
        self._gui_enqueue(_apply)        
    def _get_worker_memory(self):
        if getattr(self, "_worker_mem", None) is None:
            self._worker_mem = Memory(self.db_path)
        return self._worker_mem
    def auto_start(self):
        if self.auto_running:
            return
        busy = self._busy_operation_name()
        if busy:
            from tkinter import messagebox
            messagebox.showwarning("Autonomes Lernen", "Bitte zuerst laufenden Vorgang beenden: " + busy)
            return
        self.auto_stop = False
        self.auto_running = True
        self.cancel = False
        self._set_auto(True)
        self.println("Autonomes Dauerlernen gestartet.")
        self._auto_thread = threading.Thread(target=self._auto_worker, name="brainstem-auto", daemon=False)
        self._auto_thread.start()
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
        worker_mem = self._get_worker_memory()
        try:
            while not self.auto_stop:
                n += 1
                self.println("=== Autonomer Dauerlern-Zyklus %d ===" % n)
                self.auto_loop = AutonomousLoop(worker_mem)
                self._set_cycle_bar(0, 5)
                for step in range(5):
                    if self.auto_stop:
                        break
                    try:
                        cycle_result = self.auto_loop.cycle()
                    except Exception as cycle_exc:
                        self.println("!! AUTONOMER ZYKLUS ABGEBROCHEN (unerwarteter Fehler) !!")
                        self.println("   " + type(cycle_exc).__name__ + ": " + str(cycle_exc))
                        self.auto_stop = True
                        break
                    backend_step = (n - 1) * 5 + step + 1
                    try:
                        summary = _cycle_diagnostics.summarize_cycle_result(cycle_result)
                        if summary["cycle_status"] == "failed":
                            self.println("!! ZYKLUS-FEHLER (Kernphase) !!")
                            for finding in summary["fatal_errors"]:
                                self.println("   - " + str(finding.get("phase") or finding.get("path")) + ": " + str(finding.get("error") or finding.get("status")))
                        elif summary["cycle_status"] == "degraded":
                            self.println("(i) Zyklus degradiert: %d nicht-kernkritische Warnung(en)" % len(summary["warnings"]))
                    except Exception as diag_exc:
                        self.println("(Diagnose-Zusammenfassung fehlgeschlagen: " + str(diag_exc) + ")")
                    self.println(self._cycle_diag_text(n, step + 1))
                    self._set_cycle_bar(step + 1, 5)
                    self.refresh()
                self.auto_loop = None
                try:
                    db_for_checkpoint = getattr(worker_mem, "db", None)
                    if db_for_checkpoint is not None:
                        wal_result = _wal_maintenance.checkpoint_now(db_for_checkpoint, mode="TRUNCATE")
                        if wal_result.get("status") == "ok":
                            self.println("(i) WAL-Checkpoint: busy=%s log=%s checkpointed=%s wal_bytes %s -> %s" % (
                                wal_result.get("busy"), wal_result.get("log_frames"), wal_result.get("checkpointed_frames"),
                                wal_result.get("wal_file_size_bytes_before"), wal_result.get("wal_file_size_bytes_after")))
                        else:
                            self.println("(i) WAL-Checkpoint uebersprungen: " + str(wal_result.get("error")))
                except Exception as wal_exc:
                    self.println("(i) WAL-Checkpoint-Fehler (nicht kritisch): " + str(wal_exc))
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
        return sqlite3.connect(self.db_path, timeout=60), True
    def _collect_all_gui_values(self):
        """Read every value currently displayed anywhere in the GUI
        directly from the database, in one place. Returns an ordered dict
        (Python 3.7+ dicts preserve insertion order) so the CSV header row
        and each data row always line up, and so a fresh header is always
        derivable from a single source of truth instead of being
        hand-duplicated wherever a row is written."""
        out = {}
        out["timestamp_iso"] = datetime.now().isoformat(timespec="seconds")
        con = None
        try:
            con = sqlite3.connect(self.db_path, timeout=60)
            vals, regimes = read_all_neuromods(con)
            for k in NEURO_CORE + NEURO_NEW:
                out[k] = round(vals.get(k, 0.0), 6)
            integ = read_integration_transparency(con)
            for k in ("dopamine", "serotonin", "noradrenaline", "acetylcholine"):
                out[k + "_phasic"] = round(integ.get(k + "_phasic", 0.0), 6)
            out["tonic_weight"] = round(integ.get("tonic_weight", 0.0), 6)
            out["phase6a_evidence_state"] = integ.get("phase6a_evidence_state", "n/a")
            out["regime_orexin"] = regimes.get("orexin", "n/a")
            out["regime_bdnf"] = regimes.get("bdnf", "n/a")
            out["regime_cortisol"] = regimes.get("cortisol", "n/a")
            out["regime_histamine"] = regimes.get("histamine", "n/a")
            out["sleep_state"] = regimes.get("sleep_state", "n/a")
            out["sleep_active"] = bool(regimes.get("_asleep"))
            out["sleep_dwell_cycles"] = regimes.get("sleep_dwell", 0)
            out["sleep_upper_threshold"] = regimes.get("sleep_upper", 0.0)
            out["sleep_lower_threshold"] = regimes.get("sleep_lower", 0.0)
            out["sleep_pressure_position"] = regimes.get("sleep_position", 0.0)
            out["sleep_transition_reason"] = regimes.get("sleep_reason", "n/a")
            out["developmental_maturity"] = regimes.get("maturity", 0.0)
            mood_emoji, mood_name = compute_mood(vals, regimes)
            out["mood_name"] = mood_name

            covered, total, hypo = self._corpus_stats()
            out["chunks_covered"] = covered
            out["chunks_total"] = total
            out["chunks_pct"] = round((100.0 * covered / total) if total else 0.0, 4)
            out["hypotheses_total"] = hypo

            st = self._cached_stats()
            out["documents"] = st.get("documents", 0)
            out["chunks_stat"] = st.get("chunks", 0)
            out["facts"] = st.get("facts", 0)
            out["relations"] = st.get("relations", 0)
            out["ontology"] = st.get("ontology", 0)
            out["questions"] = st.get("questions", 0)

            surv = part = weak = 0
            thr = 0.0
            try:
                r = con.execute(
                    "SELECT candidates_survived,candidates_participated,weakened,adaptive_threshold_avg "
                    "FROM phase7d_slow_wave_cycles ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if r:
                    surv, part, weak, thr = r[0], r[1], r[2], (r[3] or 0.0)
            except Exception:
                pass
            out["phase7d_survivors"] = surv
            out["phase7d_participated"] = part
            out["phase7d_weakened"] = weak
            out["phase7d_threshold"] = round(float(thr), 6)

            try:
                out["stageb_experiment_summary"] = self._stageb_experiment_stats_line(con)
            except Exception as exc:
                out["stageb_experiment_summary"] = "unavailable: " + str(exc)

            out["mode"] = self.mode
            out["auto_running"] = bool(self.auto_running)
        except Exception as exc:
            out["error"] = str(exc)
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
        return out

    def _logger_toggle(self):
        if self.gui_logger_enabled.get():
            self._logger_start()
        else:
            self._logger_stop()

    def _logger_start(self):
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = "gui_log_%s.csv" % ts
        try:
            self._logger_file = open(filename, "w", newline="", encoding="utf-8")
            self._logger_writer = None
            self._logger_path = filename
            self._logger_fields = None
            self._logger_last_written = None
            self._logger_last_seen = None
            self._logger_last_write_ts = 0.0
            self._logger_rows_written = 0
            self._logger_rows_skipped = 0
            self.logger_status.configure(text="Logger AKTIV -> " + filename)
        except Exception as exc:
            self.gui_logger_enabled.set(False)
            self.logger_status.configure(text="Logger-Fehler: " + str(exc))

    def _logger_stop(self):
        self._logger_flush_pending()
        if getattr(self, "_logger_file", None) is not None:
            try:
                self._logger_file.close()
            except Exception:
                pass
        path = getattr(self, "_logger_path", None)
        n_rows = getattr(self, "_logger_rows_written", 0)
        self._logger_file = None
        self._logger_writer = None
        self.logger_status.configure(
            text=("Logger gestoppt (zuletzt: %s, %d Zeilen)" % (path, n_rows)) if path else "Logger inaktiv")

    @staticmethod
    def _logger_numeric(value):
        """Return a float for real-valued measurements (a float, or a string
        holding a decimal number such as the sleep score '0.5123'); return
        None for everything that must be compared exactly: ints/counters,
        bools, plain text, empty values, NaN/inf."""
        if isinstance(value, bool):
            return None
        number = None
        if isinstance(value, float):
            number = value
        elif isinstance(value, str):
            text = value.strip()
            if "." in text or "e" in text.lower():
                try:
                    number = float(text)
                except ValueError:
                    number = None
        if number is None or number != number or number in (float("inf"), float("-inf")):
            return None
        return number

    def _logger_row_changed(self, values, last):
        """True if `values` differs materially from the LAST WRITTEN row.
        timestamp_iso never counts as a change (it differs on every tick)."""
        if last is None:
            return True
        fields = self._logger_fields or list(values.keys())
        if set(values.keys()) != set(fields):
            return True
        for key in fields:
            if key == "timestamp_iso":
                continue
            new = values.get(key, "")
            old = last.get(key, "")
            new_num = self._logger_numeric(new)
            old_num = self._logger_numeric(old)
            if new_num is not None and old_num is not None:
                if abs(new_num - old_num) >= self.LOGGER_FLOAT_DEADBAND:
                    return True
            elif str(new) != str(old):
                return True
        return False

    def _logger_flush_pending(self):
        """Write the latest skipped sample (if any) as a final row."""
        try:
            if (getattr(self, "_logger_file", None) is not None
                    and self._logger_writer is not None
                    and self._logger_last_seen is not None):
                self._logger_writer.writerow(self._logger_last_seen)
                self._logger_file.flush()
                self._logger_rows_written += 1
                self._logger_last_written = self._logger_last_seen
                self._logger_last_seen = None
        except Exception:
            pass

    def _logger_update_status(self):
        try:
            self.logger_status.configure(
                text="Logger AKTIV -> %s | Zeilen: %d geschrieben, %d unveraendert uebersprungen" % (
                    self._logger_path, self._logger_rows_written, self._logger_rows_skipped))
        except Exception:
            pass

    def _logger_write_row_if_enabled(self):
        if not self.gui_logger_enabled.get():
            return
        if getattr(self, "_logger_file", None) is None:
            return
        try:
            values = self._collect_all_gui_values()
            if self._logger_writer is None:
                self._logger_fields = list(values.keys())
                self._logger_writer = csv.DictWriter(self._logger_file, fieldnames=self._logger_fields)
                self._logger_writer.writeheader()
            now = time.time()
            changes_only_var = getattr(self, "gui_logger_changes_only", None)
            changes_only = bool(changes_only_var.get()) if changes_only_var is not None else True
            if changes_only:
                due = self._logger_row_changed(values, self._logger_last_written)
                if not due and (now - self._logger_last_write_ts) >= self.LOGGER_HEARTBEAT_SECONDS:
                    due = True  # heartbeat: nothing changed for a long time
                if not due:
                    self._logger_last_seen = values
                    self._logger_rows_skipped += 1
                    self._logger_update_status()
                    return
            self._logger_writer.writerow(values)
            self._logger_file.flush()
            self._logger_last_written = values
            self._logger_last_seen = None
            self._logger_last_write_ts = now
            self._logger_rows_written += 1
            self._logger_update_status()
        except Exception as exc:
            self.logger_status.configure(text="Logger-Schreibfehler: " + str(exc))

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
        self.behavior_text.configure(text="Regime: Orexin %s (%.2f) | BDNF %s (%.2f) | Cortisol %s (%.2f) | Schlaf: %s (%d Zyklen, Druck %d%%, Reife %d%%)" % (
            regimes.get("orexin", "n/a"), vals.get("orexin", 0.0),
            regimes.get("bdnf", "n/a"), vals.get("bdnf", 0.0),
            regimes.get("cortisol", "n/a"), vals.get("cortisol", 0.0),
            regimes.get("sleep_state", "n/a"), regimes.get("sleep_dwell", 0),
            int(round(100 * regimes.get("sleep_position", 0.0))), int(round(100 * regimes.get("maturity", 0.0)))))
        self.trend_text.configure(text="Homeostase: ADE %.2f | ECB %.2f | HIS %.2f" % (
            vals.get("adenosine", 0.0), vals.get("endocannabinoid", 0.0), vals.get("histamine", 0.0)))
        con2, should_close2 = self._neuro_con()
        try:
            integ = read_integration_transparency(con2)
        finally:
            if should_close2:
                try:
                    con2.close()
                except Exception:
                    pass
        tw = integ.get("tonic_weight", 0.18)
        integ_line = "Integration (phasisch/tonisch, w=%.2f): " % tw + " | ".join(
            "%s %.2f/%.2f" % (NEURO_LABELS[k], integ.get(k + "_phasic", 0.0), vals.get(k, 0.0))
            for k in ("dopamine", "serotonin", "noradrenaline", "acetylcholine")
        )
        self.integration_text.configure(text=integ_line)
        self.evidence_text.configure(
            text="Phase6a Evidenzstatus: %s" % integ.get("phase6a_evidence_state", "n/a"))
        emoji, name = compute_mood(vals, regimes)
        if self.mood_emoji is not None:
            self.mood_emoji.configure(text=emoji)
        if self.mood_name is not None:
            self.mood_name.configure(text=name)
        self.neuro_bars.draw(vals)
    REFRESH_INTERVAL_MS = 2000

    def refresh(self):
        """Request one immediate dashboard update. Thread-safe (workers call
        it). Does NOT start a timer; requests made before the pending update
        has run are merged into that single update."""
        if getattr(self, "_refresh_requested", False):
            return
        self._refresh_requested = True
        self._gui_enqueue(self._refresh_once)
    def _refresh_timer_start(self):
        """Start (or restart) THE single periodic dashboard timer."""
        old = getattr(self, "_refresh_timer_id", None)
        if old is not None:
            try:
                self.after_cancel(old)
            except Exception:
                pass
        self._refresh_timer_id = self.after(50, self._refresh_tick)
    def _refresh_tick(self):
        self._refresh_timer_id = None
        try:
            self._refresh_once()
        finally:
            if not getattr(self, "_closing", False):
                try:
                    self._refresh_timer_id = self.after(self.REFRESH_INTERVAL_MS, self._refresh_tick)
                except Exception:
                    pass
    def _drift_tab(self):
        f = self.tabs["Drift-Report"]
        self.drift_running = False
        self.drift_stop = False
        self.drift_rows = []
        ttk.Label(f, text="Sensorischer Entzug / Drift-Kalibrierung", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(f, text="Input AUS (keine neuen Chunks), innere Dynamik laeuft weiter. Log als CSV im Projekt-Root.",
                  foreground="#555555").pack(anchor=tk.W, pady=(0, 6))
        ctl = ttk.Frame(f)
        ctl.pack(anchor=tk.W, pady=(2, 4))
        self.drift_start_btn = ttk.Button(ctl, text="Start", command=self.drift_start)
        self.drift_start_btn.pack(side=tk.LEFT)
        self.drift_stop_btn = ttk.Button(ctl, text="Stop", command=self.drift_stop_now, state=tk.DISABLED)
        self.drift_stop_btn.pack(side=tk.LEFT, padx=6)
        self.drift_limit_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctl, text="Zyklenzahl begrenzen", variable=self.drift_limit_on,
                        command=self._drift_toggle_limit).pack(side=tk.LEFT, padx=(12, 4))
        self.drift_cycles = tk.IntVar(value=100)
        self.drift_spin = ttk.Spinbox(ctl, from_=1, to=9999, textvariable=self.drift_cycles, width=8, state=tk.DISABLED)
        self.drift_spin.pack(side=tk.LEFT)
        self.drift_status = ttk.Label(f, text="Bereit.")
        self.drift_status.pack(anchor=tk.W, pady=(2, 4))
        self.drift_canvas = tk.Canvas(f, width=760, height=240, bg="white",
                                      highlightthickness=1, highlightbackground="#cccccc")
        self.drift_canvas.pack(anchor=tk.W, pady=(2, 4))
        ttk.Label(f, text="Kurven: exploration_bias (rot) | adenosine (braun) | plasticity (blau) | effectiveness (gruen) | histamine (magenta)",
                  font=("Arial", 8), foreground="#555555").pack(anchor=tk.W)
        self.drift_report = tk.Text(f, wrap=tk.WORD, height=12)
        self.drift_report.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
    def _drift_toggle_limit(self):
        self.drift_spin.configure(state=(tk.NORMAL if self.drift_limit_on.get() else tk.DISABLED))
    def drift_stop_now(self):
        self.drift_stop = True
        self.drift_status.configure(text="Stop-Anforderung gesetzt.")
    def drift_start(self):
        if self.drift_running:
            return
        busy = self._busy_operation_name()
        if busy:
            from tkinter import messagebox
            messagebox.showwarning("Drift-Report", "Bitte zuerst laufenden Vorgang beenden: " + busy)
            return
        self.drift_running = True
        self.drift_stop = False
        self.drift_rows = []
        self.drift_start_btn.configure(state=tk.DISABLED)
        self.drift_stop_btn.configure(state=tk.NORMAL)
        self.drift_report.delete("1.0", tk.END)
        self._drift_thread = threading.Thread(target=self._drift_worker, name="brainstem-drift", daemon=False)
        self._drift_thread.start()
    def _drift_worker(self):
        import importlib.util, pathlib, sqlite3
        root = pathlib.Path(__file__).resolve().parent.parent
        def _load(modfile, modname):
            spec = importlib.util.spec_from_file_location(modname, str(root / "ki_system" / modfile))
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
        try:
            runner = _load("v8_deprivation_runner.py", "v8_deprivation_runner")
            sd = _load("v8_sensory_deprivation.py", "v8_sensory_deprivation")
        except Exception as e:
            self.after(0, lambda message=str(e): self.drift_status.configure(text="Modul-Fehler: " + message))
            self._drift_finish()
            return
        con = sqlite3.connect(self.db_path, timeout=60.0)
        loop = AutonomousLoop(self._get_worker_memory())
        limit_on = bool(self.drift_limit_on.get())
        cycles = int(self.drift_cycles.get()) if limit_on else None
        def cycle_fn():
            loop.cycle()
        def stop_flag():
            return self.drift_stop
        def set_flag_fn(active):
            sd.set_deprivation(con, active)
        def on_cycle(n, snap):
            self.drift_rows.append(snap)
            self.after(0, lambda: self.drift_status.configure(
                text="Entzug-Zyklus %d | expl=%.3f ade=%.3f eff=%.4f" % (
                    n, snap.get("exploration_bias", 0.0), snap.get("adenosine", 0.0), snap.get("effectiveness", 0.0))))
            if n % 5 == 0:
                self.after(0, self._drift_draw)
            self.after(0, lambda: self._drift_log_line(
                "Zyklus %d | expl %.3f | ade %.3f | plast %.3f | eff %.4f | hist %.3f" % (
                    n, snap.get("exploration_bias", 0.0), snap.get("adenosine", 0.0),
                    snap.get("plasticity_level", 0.0), snap.get("effectiveness", 0.0), snap.get("histamine", 0.0))))
        try:
            csv_name = "drift_log_" + time.strftime("%Y%m%d_%H%M%S") + ".csv"
            csv_path = str(root / csv_name)
            rep = runner.run_deprivation(con, cycle_fn, cycles=cycles, stop_flag=stop_flag,
                                         on_cycle=on_cycle, csv_path=csv_path, set_flag_fn=set_flag_fn)
            text, overall = runner.write_report(rep["rows"], csv_path)
            self.after(0, lambda: (self.drift_report.insert(tk.END, text + "\n\nCSV: " + csv_path + "\n"),
                                   self.drift_status.configure(text="Fertig: %d Zyklen | GESAMT: %s" % (rep["cycles"], overall))))
        except Exception as e:
            self.after(0, lambda message=str(e): self.drift_status.configure(text="Drift-Fehler: " + message))
        finally:
            try: sd.set_deprivation(con, False)
            except Exception: pass
            try: con.close()
            except Exception: pass
            self.after(0, self._drift_draw)
            self._drift_finish()
    def _drift_finish(self):
        self.drift_running = False
        self.drift_stop = False
        self.after(0, lambda: (self.drift_start_btn.configure(state=tk.NORMAL),
                               self.drift_stop_btn.configure(state=tk.DISABLED)))
        self.after(0, self.refresh)
    def _drift_draw(self):
        c = self.drift_canvas
        c.delete("all")
        w = int(c["width"]); h = int(c["height"]); pad = 12
        c.create_rectangle(pad, pad, w - pad, h - pad, outline="#dddddd")
        rows = self.drift_rows
        n = len(rows)
        if n < 2:
            return
        maxpts = 200
        if n > maxpts:
            step = n / float(maxpts)
            idxs = [int(i * step) for i in range(maxpts)]
            if idxs[-1] != n - 1:
                idxs.append(n - 1)
        else:
            idxs = list(range(n))
        m = len(idxs)
        series = [("exploration_bias", "#d62728"), ("adenosine", "#8c564b"),
                  ("plasticity_level", "#1f77b4"), ("effectiveness", "#2ca02c"), ("histamine", "#e377c2")]
        for key, color in series:
            pts = []
            for j, i in enumerate(idxs):
                v = rows[i].get(key, 0.0)
                try: v = float(v)
                except Exception: v = 0.0
                if v < 0.0: v = 0.0
                if v > 1.0: v = 1.0
                x = pad + (w - 2 * pad) * (j / max(1, m - 1))
                y = (h - pad) - v * (h - 2 * pad)
                pts.append((x, y))
            for k in range(1, len(pts)):
               c.create_line(pts[k - 1][0], pts[k - 1][1], pts[k][0], pts[k][1], fill=color, width=2)
    def _drift_log_line(self, msg):
        try:
            self.drift_report.insert(tk.END, str(msg) + "\n")
            total = int(self.drift_report.index("end-1c").split(".")[0])
            if total > 200:
                self.drift_report.delete("1.0", "%d.0" % (total - 200 + 1))
            self.drift_report.see(tk.END)
        except Exception:
            pass
    def _refresh_once(self):
        if self._refresh_running:
            return  # never run two refreshes at the same time
        self._refresh_running = True
        self._refresh_requested = False
        try:
            covered, total, hypo = self._corpus_stats()
            pct = (100.0 * covered / total) if total else 0.0
            st = self._cached_stats()
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
            if hasattr(self, "gui_logger_enabled"):
                self._logger_write_row_if_enabled()
            if hasattr(self, "docs") and self._current_tab_name == "Datenbank":
                self.docs.delete(*self.docs.get_children())
                for d in self.mem.rows("SELECT * FROM documents ORDER BY created_at DESC LIMIT 2000"):
                    self.docs.insert("", tk.END, values=(d["id"], d["title"], d["kind"], d["path"]))
            if hasattr(self, "facts") and self._current_tab_name == "Fakten/Relationen":
                self.facts.delete(*self.facts.get_children())
                for f in self.mem.rows("SELECT * FROM facts ORDER BY created_at DESC LIMIT 2000"):
                    self.facts.insert("", tk.END, values=(f["subject"], f["relation"], f["value"], round(f["confidence"], 2)))
        finally:
            self._refresh_running = False


    def _gui_enqueue(self, callback):
        if not callable(callback): return
        lock=getattr(self, '_gui_pending_lock', None)
        if lock is None: return
        with lock:
            if len(self._gui_pending)>=256: del self._gui_pending[:-128]
            self._gui_pending.append(callback)

    def _gui_pump(self):
        batch=[]; lock=getattr(self, '_gui_pending_lock', None)
        if lock is not None:
            with lock:
                if self._gui_pending:
                    batch=self._gui_pending[-32:]; self._gui_pending.clear()
        for callback in batch:
            try: callback()
            except Exception as exc:
                try: print('[GUI_PUMP_ERROR]',repr(exc))
                except Exception: pass
        if getattr(self, '_closing', False):
            self._gui_pump_scheduled=False; return
        try: self._gui_pump_id=self.after(50,self._gui_pump)
        except Exception: self._gui_pump_scheduled=False

def main(db_path="ki_memory.sqlite3"):
    App(db_path).mainloop()
