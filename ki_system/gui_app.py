# -*- coding: utf-8 -*-
import tkinter as tk
import json
import threading
import time
import sqlite3
from tkinter import ttk, filedialog
from ki_system.memory import Memory
from ki_system.ingest import import_file
from ki_system.autonomous import AutonomousLoop
from ki_system.dialogue import DialogueManager
from ki_system.search import semantic_search, answer
from ki_system import v8_cycle_diagnostics_release as _cycle_diagnostics
from ki_system import v8_wal_maintenance_release as _wal_maintenance

# BEGIN BRAINSTEM CANONICAL PER-CYCLE RUNTIME STARTUP ACTIVATION V1.1
# Startup-only activation. The imported bridge remains shadow-only.
import importlib as _brainstem_runtime_importlib
_brainstem_runtime_importlib.import_module("ki_system.v8_non_productive_recheck_canonical_autoload_shadow_runtime_integration_v1")
# END BRAINSTEM CANONICAL PER-CYCLE RUNTIME STARTUP ACTIVATION V1.1

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
    cooperative = _kv(con, "cooperative_sleep_wake_state")
    cooperative_mode = str(cooperative.get("state", "")).strip().lower()
    cooperative_asleep = (cooperative_mode == "sleep")
    # BRAINSTEM_GUI_DUAL_SLEEP_AUTHORITY_FIX_V1 (09 September 2026)
    phase7a_state = _kv(con, "phase7a_adenosine_state")
    phase7a_mode = str(phase7a_state.get("homeostat_mode", "wake")).strip().lower()
    phase7a_asleep = (phase7a_mode == "sleep")
    if cooperative_mode in ("wake", "sleep"):
        asleep = cooperative_asleep or phase7a_asleep
        if cooperative_asleep and phase7a_asleep:
            sleep_authority = "cooperative+phase7a"
        elif cooperative_asleep:
            sleep_authority = "cooperative"
        elif phase7a_asleep:
            sleep_authority = "phase7a"
        else:
            sleep_authority = "none"
    else:
        legacy_asleep = ((vals["adenosine"] >= 0.6 and vals["histamine"] <= 0.45) or regimes["histamine"] == "sleep_permissive")
        asleep = legacy_asleep or phase7a_asleep
        sleep_authority = "legacy_fallback+phase7a" if phase7a_asleep else ("legacy_fallback" if legacy_asleep else "none")
    regimes["_asleep"] = bool(asleep)
    regimes["sleep_authority"] = sleep_authority
    regimes["sleep_score"] = cooperative.get("sleep_score", "n/a")
    regimes["phase7a_mode"] = phase7a_mode
    regimes["cooperative_mode"] = cooperative_mode or "n/a"
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
        authority = regimes.get("sleep_authority", "")
        if authority == "phase7a":
            return ("(-_-) zzz", "Konsolidiert (Phase7a)")
        if authority in ("cooperative", "cooperative+phase7a"):
            return ("(-_-) zzz", "Schlaeft")
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
        self._closing = False
        self._shutdown_poll_id = None
        self._auto_thread = None
        self._drift_thread = None
        self._import_thread = None
        self._reset_thread = None
        self.head = None
        self.mode = "idle"
        self._cov_cache = None
        self._cov_ts = 0.0
        # BRAINSTEM_GUI_STATS_CACHE_FIX_V1 (11 September 2026): see _cached_stats()
        # below for the full explanation.
        self._stats_cache = None
        self._stats_ts = 0.0
        # BRAINSTEM_GRADUATION_QUEUE_DISPLAY_V1 (11 September 2026): see
        # _graduation_queue_snapshot() below for the full explanation.
        self._grad_queue_cache = None
        self._grad_queue_ts = 0.0
        self._current_tab_name = "Chat"
        self._ui()
        self._gui_pending = []
        self._gui_pending_lock = threading.Lock()
        self._gui_pump_scheduled = True
        self._refresh_running = False
        self.after(50, self._gui_pump)  # GUI_MAINLOOP_STABILIZATION_V1_1
        self._create_floating_head()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh()
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
        # BRAINSTEM_GRADUATION_QUEUE_DISPLAY_V1 (11 September 2026)
        #
        # Purpose: surface the internal state of Phase 7d's survivor-
        # reactivation queue (v8_phase7d_slow_wave_sleep_substructure_
        # release.py:_build_candidate_pool()) -- the mechanism that gives
        # a hypothesis with 1 or 2 (but not yet 3) confirmed, reinforced
        # consolidation survivals a fair, rotating chance to be re-selected
        # as a candidate again in a later cycle, biologically analogous to
        # synaptic priming/reconsolidation rather than a pure-random
        # re-draw from the entire hypothesis population. This was added
        # after a joint investigation into why hypothesis graduation
        # (uncertain_hypothesis -> stable_hypothesis) slowed sharply after
        # the corpus and hypothesis population grew large: the mechanism
        # itself was found to already be correctly implemented (a rotating
        # cursor-based queue, not blind random sampling), so this display
        # exists purely for transparency/observation of that existing,
        # already-correct queue -- it does not add, change, or gate any
        # new behavior in the underlying phase itself.
        ttk.Separator(left).pack(fill=tk.X, pady=(8, 4))
        ttk.Label(left, text="Hypothesen-Graduierung: Reaktivierungs-Warteschlange (Phase 7d)",
                  font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.grad_queue_text = ttk.Label(left, text="Warteschlange: -")
        self.grad_queue_text.pack(anchor=tk.W)
        self.grad_cursor_text = ttk.Label(left, text="Cursor: -")
        self.grad_cursor_text.pack(anchor=tk.W)
        self.grad_eta_text = ttk.Label(left, text="Geschaetzte Wartezeit: -", wraplength=520, justify=tk.LEFT)
        self.grad_eta_text.pack(anchor=tk.W)
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
    def _cycle_diag_text(self, n, step):
        import sqlite3
        lines = ["=== Autonomer Zyklus %d / Schritt %d ===" % (n, step)]
        try:
            con = sqlite3.connect("ki_memory.sqlite3", timeout=60)
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
                lines.append("Schlaf -> Kooperativ: %s (Score %s) | Phase7a: %s | Aktiv: %s (%s)" % (
                    regimes.get("cooperative_mode", "n/a"), regimes.get("sleep_score", "n/a"),
                    regimes.get("phase7a_mode", "n/a"),
                    "JA" if regimes.get("_asleep") else "nein", regimes.get("sleep_authority", "none")))
                lines.append("7d Slow-Wave -> Survivors %s | Participated %s | Weakened %s | Schwelle %.3f" % (surv, part, weak, float(thr)))
                lines.append("SAFETY facts/relations/questions: %s" % safe)
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
            con = sqlite3.connect("ki_memory.sqlite3", timeout=60)
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
    # BRAINSTEM_GUI_STATS_CACHE_FIX_V1 (11 September 2026)
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
    # BRAINSTEM_GRADUATION_QUEUE_DISPLAY_V1 (11 September 2026)
    #
    # Background: a joint investigation into why hypothesis graduation
    # (context_hypotheses.role: uncertain_hypothesis -> stable_hypothesis,
    # see v8_stageb_guarded_hypothesis_graduation_release.py) slowed
    # sharply as the corpus/hypothesis population grew (34 graduations in
    # the first 1,000 real cycles, then only 2 more, then none across the
    # next ~9,500 cycles at 1.59 million active uncertain_hypothesis rows)
    # led to inspecting v8_phase7d_slow_wave_sleep_substructure_release.py.
    # That inspection found the reactivation mechanism is NOT a blind
    # random re-draw from the entire hypothesis population (which, at this
    # scale, would make a second confirmation of the same hypothesis
    # statistically very rare) -- it is a deliberate, rotating "three-track"
    # candidate pool (anchors / reactivated survivors / novel) with a
    # persistent, fair cursor per survival level (1 or 2 confirmed cycles),
    # biologically analogous to synaptic priming/reconsolidation rather
    # than an efficiency optimization. This method and the three labels it
    # feeds exist purely to make that ALREADY-CORRECT, ALREADY-EXISTING
    # mechanism observable in the GUI -- they add no new behavior, no new
    # write path, and no change whatsoever to Phase 7d's own logic.
    #
    # Read-only: opens its own short-lived connection, executes only
    # SELECT statements, never writes anything. Mirrors the exact
    # WHERE/HAVING clauses used by the real
    # _build_candidate_pool()/_run_slow_wave_sleep() functions in Phase 7d,
    # so the displayed queue counts and cursor positions accurately
    # reflect what that phase itself would compute on its next real
    # invocation -- but this method itself never calls into Phase 7d code
    # and never mutates phase7d_state, phase6b_state, or any other table.
    #
    # Cached for 30 seconds (longer than the other 10-second GUI caches)
    # since this query is heavier (a GROUP BY/HAVING over
    # phase7d_consolidation_survivors) and a human-readable ETA estimate
    # does not benefit from sub-30-second freshness.
    def _graduation_queue_snapshot(self):
        now = time.time()
        if self._grad_queue_cache is not None and (now - self._grad_queue_ts) < 30.0:
            return self._grad_queue_cache
        result = {
            "available": False, "level1_total": 0, "level2_total": 0,
            "level1_ahead": 0, "level2_ahead": 0,
            "cursor_n1": 0, "cursor_n2": 0,
            "last_capacity": 0, "last_reactivated": 0,
            "sleep_fraction": 0.0, "estimated_cycles": None,
            "error": None,
        }
        con = None
        try:
            con = sqlite3.connect("ki_memory.sqlite3", timeout=10)

            def _tbl(t):
                return con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)
                ).fetchone() is not None

            def _i(x, d=0):
                try:
                    return int(float(x))
                except Exception:
                    return d

            if not _tbl("phase7d_consolidation_survivors") or not _tbl("phase7d_state"):
                result["error"] = "phase7d_noch_nicht_initialisiert"
                self._grad_queue_cache = result
                self._grad_queue_ts = now
                return result

            state = dict(con.execute("SELECT key,value FROM phase7d_state").fetchall())
            phase6b_state = {}
            if _tbl("phase6b_state"):
                phase6b_state = dict(con.execute("SELECT key,value FROM phase6b_state").fetchall())

            current_cycle = _i(state.get("cycle_count"), 0) + 1
            checkpoint = _i(phase6b_state.get("phase7d_survivor_anchor_checkpoint_id"), 0)
            cursor_n1 = _i(state.get("survivor_reactivation_cursor_n1"), 0)
            cursor_n2 = _i(state.get("survivor_reactivation_cursor_n2"), 0)
            last_capacity = _i(state.get("reactivation_capacity"), 0)
            last_reactivated = _i(state.get("reactivation_selected"), 0)

            active_anchor_sources = set()
            if _tbl("phase6b_anchor_pool"):
                active_anchor_sources = {
                    _i(row[0]) for row in con.execute(
                        "SELECT source_id FROM phase6b_anchor_pool "
                        "WHERE active=1 AND source_table='context_hypotheses'"
                    ).fetchall()
                }

            # Mirrors v8_phase7d_slow_wave_sleep_substructure_release.py:
            # _build_candidate_pool()'s own read query exactly (read-only).
            rows = con.execute(
                "SELECT source_id,COUNT(DISTINCT cycle_index) AS survived_cycles,"
                "MAX(cycle_index) AS last_cycle "
                "FROM phase7d_consolidation_survivors "
                "WHERE id>? AND reinforced=1 AND source_table='context_hypotheses' "
                "GROUP BY source_id "
                "HAVING COUNT(DISTINCT cycle_index) IN (1,2) AND MAX(cycle_index)<?",
                (checkpoint, current_cycle),
            ).fetchall()

            level1_ids, level2_ids = [], []
            for source_id, survived_cycles, _last_cycle in rows:
                sid = _i(source_id)
                if sid in active_anchor_sources:
                    continue
                level = _i(survived_cycles)
                if level == 1:
                    level1_ids.append(sid)
                elif level == 2:
                    level2_ids.append(sid)

            result["level1_total"] = len(level1_ids)
            result["level2_total"] = len(level2_ids)
            result["level1_ahead"] = sum(1 for sid in level1_ids if sid > cursor_n1)
            result["level2_ahead"] = sum(1 for sid in level2_ids if sid > cursor_n2)
            result["cursor_n1"] = cursor_n1
            result["cursor_n2"] = cursor_n2
            result["last_capacity"] = last_capacity
            result["last_reactivated"] = last_reactivated

            total_phase7d_cycles = _i(state.get("cycle_count"), 0)
            total_sleep_events = 0
            if _tbl("phase7d_slow_wave_cycles"):
                r = con.execute("SELECT COUNT(*) FROM phase7d_slow_wave_cycles").fetchone()
                total_sleep_events = _i(r[0] if r else 0)
            sleep_fraction = (total_sleep_events / total_phase7d_cycles) if total_phase7d_cycles > 0 else 0.0
            result["sleep_fraction"] = sleep_fraction

            queue_total = result["level1_total"] + result["level2_total"]
            throughput = last_reactivated if last_reactivated > 0 else last_capacity
            if queue_total > 0 and throughput > 0 and sleep_fraction > 1e-6:
                est_sleep_cycles = queue_total / float(throughput)
                est_real_cycles = est_sleep_cycles / sleep_fraction
                result["estimated_cycles"] = int(round(est_real_cycles))
            else:
                result["estimated_cycles"] = None

            result["available"] = True
        except Exception as exc:
            result["error"] = type(exc).__name__ + ":" + str(exc)
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
        self._grad_queue_cache = result
        self._grad_queue_ts = now
        return result
    def _update_graduation_queue_display(self):
        snap = self._graduation_queue_snapshot()
        if not snap.get("available"):
            reason = snap.get("error") or "unbekannt"
            self.grad_queue_text.configure(text="Warteschlange: nicht verfuegbar (%s)" % reason)
            self.grad_cursor_text.configure(text="Cursor: -")
            self.grad_eta_text.configure(text="Geschaetzte Wartezeit: -")
            return
        self.grad_queue_text.configure(
            text="Warteschlange: Level 2 (kurz vor Graduierung) %d | Level 1 %d" % (
                snap["level2_total"], snap["level1_total"]))
        self.grad_cursor_text.configure(
            text="Cursor: Level 2 bei Hypothese-ID %d (%d/%d in dieser Runde noch offen) | "
                 "Level 1 bei Hypothese-ID %d (%d/%d offen)" % (
                snap["cursor_n2"], snap["level2_ahead"], snap["level2_total"],
                snap["cursor_n1"], snap["level1_ahead"], snap["level1_total"]))
        if snap["estimated_cycles"] is not None:
            self.grad_eta_text.configure(
                text="Geschaetzte Wartezeit bis vollstaendiger Durchlauf der aktuellen Warteschlange: "
                     "~%d Realzyklen (letzte Reaktivierung: %d von Kapazitaet %d pro Schlafzyklus, "
                     "Schlafanteil %.1f%% der Zyklen)" % (
                    snap["estimated_cycles"], snap["last_reactivated"], snap["last_capacity"],
                    snap["sleep_fraction"] * 100.0))
        else:
            self.grad_eta_text.configure(
                text="Geschaetzte Wartezeit: noch nicht genug Daten fuer eine Schaetzung "
                     "(Warteschlange leer oder noch keine Reaktivierung beobachtet)")
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
            self._worker_mem = Memory("ki_memory.sqlite3")
        return self._worker_mem
    def auto_start(self):
        if self.auto_running:
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
        import importlib as _brainstem_late_importlib
        _brainstem_late_runtime = _brainstem_late_importlib.import_module("ki_system.v8_non_productive_recheck_canonical_autoload_shadow_runtime_integration_v1")
        from ki_system.autonomous import AutonomousLoop as _brainstem_late_loop
        _brainstem_patch_marker = "_brainstem_per_cycle_runtime_provenance_fix_v1"
        _brainstem_current_cycle = getattr(_brainstem_late_loop, "cycle", None)
        if not hasattr(_brainstem_current_cycle, "__wrapped__") and hasattr(_brainstem_late_loop, _brainstem_patch_marker):
            delattr(_brainstem_late_loop, _brainstem_patch_marker)
        _brainstem_late_runtime.autoload(_brainstem_late_loop)
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
        return sqlite3.connect("ki_memory.sqlite3", timeout=60), True
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
        self.behavior_text.configure(text="Regime: Orexin %s (%.2f) | BDNF %s (%.2f) | Cortisol %s (%.2f) | Schlaf: koop=%s/phase7a=%s" % (
            regimes.get("orexin", "n/a"), vals.get("orexin", 0.0),
            regimes.get("bdnf", "n/a"), vals.get("bdnf", 0.0),
            regimes.get("cortisol", "n/a"), vals.get("cortisol", 0.0),
            regimes.get("cooperative_mode", "n/a"), regimes.get("phase7a_mode", "n/a")))
        self.trend_text.configure(text="Homeostase: ADE %.2f | ECB %.2f | HIS %.2f" % (
            vals.get("adenosine", 0.0), vals.get("endocannabinoid", 0.0), vals.get("histamine", 0.0)))
        emoji, name = compute_mood(vals, regimes)
        if self.mood_emoji is not None:
            self.mood_emoji.configure(text=emoji)
        if self.mood_name is not None:
            self.mood_name.configure(text=name)
        self.neuro_bars.draw(vals)
    def refresh(self):
        self._gui_enqueue(self._refresh)
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
        if self.auto_running:
            from tkinter import messagebox
            messagebox.showwarning("Drift-Report", "Bitte zuerst 'Autonom stoppen'.")
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
            self.after(0, lambda: self.drift_status.configure(text="Modul-Fehler: " + str(e)))
            self._drift_finish()
            return
        con = sqlite3.connect(str(root / "ki_memory.sqlite3"), timeout=60.0)
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
            self.after(0, lambda: self.drift_status.configure(text="Drift-Fehler: " + str(e)))
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
    def _refresh(self):
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
            if hasattr(self, "grad_queue_text"):
                try:
                    self._update_graduation_queue_display()
                except Exception as exc:
                    self.grad_queue_text.configure(text="Warteschlange: Fehler: " + str(exc))
            if hasattr(self, "docs") and self._current_tab_name == "Datenbank":
                self.docs.delete(*self.docs.get_children())
                for d in self.mem.rows("SELECT * FROM documents ORDER BY created_at DESC LIMIT 2000"):
                    self.docs.insert("", tk.END, values=(d["id"], d["title"], d["kind"], d["path"]))
            if hasattr(self, "facts") and self._current_tab_name == "Fakten/Relationen":
                self.facts.delete(*self.facts.get_children())
                for f in self.mem.rows("SELECT * FROM facts ORDER BY created_at DESC LIMIT 2000"):
                    self.facts.insert("", tk.END, values=(f["subject"], f["relation"], f["value"], round(f["confidence"], 2)))
        finally:
            try:
                self.after(2000, self._refresh)
            except Exception:
                pass


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
        try: self.after(50,self._gui_pump)
        except Exception: self._gui_pump_scheduled=False

def main():
    App().mainloop()
