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
    # BRAINSTEM_GUI_DUAL_SLEEP_AUTHORITY_FIX_V1
    #
    # Root cause (confirmed 09 September 2026 via diagnose_sleep_authority.py
    # against a real 467-cycle production database): the GUI mood indicator
    # previously relied EXCLUSIVELY on cooperative_sleep_wake_state.state.
    # That cooperative authority combines five weighted signals behind a
    # single, high, combined threshold (default 0.62) and, measured over
    # 467 real cycles, never once crossed it (peak observed: 0.5403 at
    # cycle 8, then oscillating between 0.31-0.54 -- i.e. NOT a data-
    # maturity effect, since the score does not trend upward over time).
    #
    # Meanwhile phase7a_adenosine_homeostat_release.py -- the older,
    # independent, single-signal adenosine homeostat -- was confirmed to be
    # working correctly and extensively the entire time: 290 of 467 cycles
    # recorded homeostat_mode='sleep', with 58 real transitions and a full
    # sleep/wake event history (v8_phase7a_adenosine_homeostat_release.py,
    # threshold_high=0.65). The two authorities structurally interfere with
    # each other: phase7a enters sleep and begins actively discharging
    # (decaying) adenosine as soon as its own single-signal 0.65 threshold
    # is crossed, which is exactly the dominant (35% weight) input the
    # cooperative authority needs to reach ITS OWN, later, combined 0.62
    # threshold -- so by the time phase7a's decay has run its course, the
    # cooperative score never gets a real chance to climb high enough on
    # its own.
    #
    # This exact "OR both authorities together" pattern is already the
    # established, working convention used elsewhere in this same codebase
    # for entering real Slow-Wave-Sleep: see
    # v8_phase7d_slow_wave_sleep_substructure_release.py:
    #   if canonical_mode == "sleep" or cooperative_mode == "sleep":
    # and v8_phase7e_histamine_wake_arousal_release.py, which reads
    # phase7a's homeostat_mode the same way. Phase7d's own real slow-wave
    # consolidation (reinforcement/weakening of hypotheses, the actual
    # mechanism the user is asking to see reflected here) already runs
    # whenever EITHER authority says "sleep" -- so real consolidation has
    # been happening in the background this whole time, just never shown
    # in the GUI, because the GUI checked only ONE of the two authorities
    # that phase7d itself already treats as equally valid.
    #
    # Fix: mirror phase7d/phase7e's own established pattern in the GUI's
    # mood/regime read path. The GUI now shows "sleep" whenever EITHER the
    # cooperative authority OR the phase7a homeostat reports sleep, exactly
    # matching what actually gates real consolidation in phase7d. This is
    # not a new, invented threshold or behavior -- it is the GUI catching
    # up to a convention that already governs real learning behavior
    # elsewhere in this codebase.
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
        # BRAINSTEM_GUI_DUAL_SLEEP_AUTHORITY_FIX_V1: distinguish which
        # authority triggered sleep, for transparency in the mood label.
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
        self.tabs = {}
        for n in ["Chat", "Import & Jobs", "Suche & Antwort", "Datenbank", "Fakten/Relationen", "Export/Konfig", "Drift-Report"]:
            f = ttk.Frame(nb, padding=8)
            nb.add(f, text=n)
            self.tabs[n] = f
        self._chat_tab()
        self._import_tab()
        self._search_tab()
        self._db_tab()
        self._facts_tab()
        self._export_tab()
        self._drift_tab()
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
        # BRAINSTEM_SHARED_CONNECTION_THREAD_SAFETY_FIX_V1: also commit and
        # close the dedicated worker connection (used by the autonomous-
        # learning and drift/sensory-deprivation background threads), if one
        # was ever created. Both worker threads are already joined above
        # before this runs, so it is safe to close here.
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
            # BRAINSTEM_MEMORY_TIMEOUT_FIX_V1: this separate diagnostic
            # connection previously used only timeout=5 (SQLite's default
            # busy-wait if unspecified is also effectively very short).
            # Raised to 60s to match the main Memory connection's own fix
            # (see memory.py) and every other module's own resolve_db()
            # fallback convention throughout this codebase, reducing the
            # chance that this read-only diagnostic query itself contends
            # with, or is blocked by, a concurrent long-running write from
            # the real learning cycle at large database sizes.
            con = sqlite3.connect("ki_memory.sqlite3", timeout=60)
            try:
                vals, regimes = read_all_neuromods(con)
                total = 0; covered = 0; hyp = 0
                try: total = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
                except Exception: pass
                try: covered = con.execute("SELECT COUNT(*) FROM reading_queue WHERE COALESCE(read_count,0)>0").fetchone()[0]
                except Exception: pass
                try: hyp = con.execute("SELECT COUNT(*) FROM context_hypotheses").fetchone()[0]
                except Exception: pass
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
                # BRAINSTEM_GUI_DUAL_SLEEP_AUTHORITY_FIX_V1: surface both
                # sleep authorities explicitly in the per-cycle diagnostic
                # text, so it is fully transparent which one (if any) is
                # currently asleep, instead of only the combined GUI mood.
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
        # BRAINSTEM GUI FIVE STEP PROGRESS FIX V1
        # Preserve real backend substep callbacks in learn/auto mode.
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
            # BRAINSTEM_MEMORY_TIMEOUT_FIX_V1: raised from timeout=5, see
            # _cycle_diag_text() above for the full rationale.
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
    def chat_send(self):
        t = self.chat_in.get().strip()
        if t:
            r = self.dialogue.respond(t)
            note = ""
            # BRAINSTEM_GUI_PERSIST_NOTE_FIX_V1: the admin GUI's Memory is
            # writable, so r.skip_reason should normally be None here; but if
            # persistence genuinely fails for any reason it is now surfaced
            # instead of being silently discarded (see dialogue.py fix).
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
        # BRAINSTEM_SHARED_CONNECTION_THREAD_SAFETY_FIX_V1
        #
        # Root-cause finding (09 September 2026, second occurrence): the
        # previous fix (raising sqlite3 busy-timeouts from 5s to 60s) did
        # NOT resolve "database is locked" -- the error recurred even
        # EARLIER (cycle 14 vs. previously cycle 22). This is strong
        # evidence that the error is NOT primarily SQLITE_BUSY (cross-
        # connection file-lock contention, which busy-timeout retries DO
        # help with), but SQLITE_LOCKED (a conflict caused by concurrent,
        # unsynchronized statement execution on the SAME sqlite3.Connection
        # object from multiple threads at once). SQLite's busy-handler/
        # busy-timeout mechanism explicitly does NOT retry SQLITE_LOCKED
        # errors, so no timeout value, however large, can fix this specific
        # failure mode.
        #
        # The actual root cause: self.mem (and therefore self.mem.db, a
        # single sqlite3.Connection) was shared between the GUI's own
        # periodic self.after(2000, self._refresh) timer (running on the
        # main/GUI thread, calling self.mem.rows()/self.mem.stats(), which
        # DOES go through self.mem.lock) and the "brainstem-auto" background
        # thread (running AutonomousLoop(self.mem).cycle(), where most
        # v8_phase*.py modules call resolve_db(self) and then execute SQL
        # DIRECTLY on the raw connection, completely bypassing self.mem.lock
        # entirely). Two threads therefore issued SQL statements on the
        # exact same Connection handle concurrently and without a shared
        # mutex protecting every access path -- a well-documented Python/
        # sqlite3 pitfall. The official, standard-practice fix (per Python's
        # own sqlite3 documentation) is: give each thread its own dedicated
        # connection instead of sharing one across threads.
        #
        # This method lazily creates ONE dedicated Memory instance (with its
        # own separate sqlite3.Connection, same 60s busy-timeout as the
        # main connection) reserved exclusively for the autonomous-learning
        # background thread (and the drift/sensory-deprivation thread, which
        # has the identical sharing problem via AutonomousLoop(self.mem)).
        # The GUI's own self.mem connection continues to be used only by the
        # main/GUI thread (chat, facts/documents browser, corpus stats,
        # neuromodulator dashboard), so the two connections are now each
        # confined to a single thread, eliminating the unsynchronized
        # concurrent-access pattern at its root instead of only masking one
        # symptom of it.
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
        # BEGIN BRAINSTEM MERGED HISTORICAL FIVE-EVALUATION WORKER V1
        # BEGIN BRAINSTEM LATE RUNTIME REPATCH V1.2
        # Re-apply after all later phase autoloads have replaced AutonomousLoop.cycle.
        import importlib as _brainstem_late_importlib
        _brainstem_late_runtime = _brainstem_late_importlib.import_module("ki_system.v8_non_productive_recheck_canonical_autoload_shadow_runtime_integration_v1")
        # The class marker can be stale when a later phase replaces AutonomousLoop.cycle.
        from ki_system.autonomous import AutonomousLoop as _brainstem_late_loop
        _brainstem_patch_marker = "_brainstem_per_cycle_runtime_provenance_fix_v1"
        _brainstem_current_cycle = getattr(_brainstem_late_loop, "cycle", None)
        if not hasattr(_brainstem_current_cycle, "__wrapped__") and hasattr(_brainstem_late_loop, _brainstem_patch_marker):
            delattr(_brainstem_late_loop, _brainstem_patch_marker)
        _brainstem_late_runtime.autoload(_brainstem_late_loop)
        # END BRAINSTEM LATE RUNTIME REPATCH V1.2
        n = 0
        self.mode = "learn"
        # BRAINSTEM_SHARED_CONNECTION_THREAD_SAFETY_FIX_V1: use a dedicated
        # connection for this background thread instead of sharing self.mem
        # with the GUI thread. See _get_worker_memory() for the full
        # root-cause explanation.
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
                    # BRAINSTEM_AUTO_WORKER_CYCLE_CRASH_CONTAINMENT_FIX_V1:
                    # self.auto_loop.cycle() previously had no exception
                    # handling at all. A production crash at 167,661-chunk
                    # scale showed that an uncaught sqlite3.OperationalError
                    # ("database is locked"), originating deep inside a
                    # non-productive audit-log write, could propagate all
                    # the way up through the entire wrapped cycle() chain
                    # and silently kill this background thread: the GUI
                    # only ever showed the generic "Autonomes Dauerlernen
                    # gestoppt." from the outer finally: block below, while
                    # the actual exception and traceback were only visible
                    # as an unhandled "Exception in thread brainstem-auto"
                    # in the console -- never in the GUI itself. That
                    # specific audit-write crash is now separately fixed at
                    # its source (see v8_non_productive_recheck_canonical_
                    # autoload_shadow_runtime_integration_v1.py), but this
                    # call is now also defensively guarded so that ANY
                    # future unexpected exception from a real cycle is
                    # caught, fully logged to the visible GUI log with its
                    # exact type and message, and autonomous learning stops
                    # cleanly and visibly instead of dying silently.
                    try:
                        cycle_result = self.auto_loop.cycle()
                    except Exception as cycle_exc:
                        self.println("!! AUTONOMER ZYKLUS ABGEBROCHEN (unerwarteter Fehler) !!")
                        self.println("   " + type(cycle_exc).__name__ + ": " + str(cycle_exc))
                        self.auto_stop = True
                        break
                    backend_step = (n - 1) * 5 + step + 1
                    # BRAINSTEM_GUI_DIAGNOSTICS_SURFACE_FIX_V1: previously the
                    # GUI only ever displayed database state read back after
                    # the fact (via _cycle_diag_text) and had no way to know
                    # whether the cycle that just ran actually completed its
                    # core phases without error -- a failed core phase (e.g.
                    # Phase 6a) could be nested deep inside cycle_result and
                    # would look identical to a healthy cycle in the GUI. The
                    # recursive summarizer now makes this explicit.
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
                    # GUI_FIVE_EVALUATION_CONTRACT_FIX_V1: diagnose every real subcycle
                    self.println(self._cycle_diag_text(n, step + 1))
                    # GUI_FIVE_EVALUATION_CONTRACT_FIX_V1: render every real subcycle
                    self._set_cycle_bar(step + 1, 5)
                    self.refresh()
                self.auto_loop = None
                # BRAINSTEM_WAL_CHECKPOINT_MAINTENANCE_WIRING_V1: explicitly
                # authorized fix for the (previously unconfirmed) WAL-growth
                # hypothesis raised after a real 167,661-chunk production
                # run showed increasing GUI sluggishness followed by a
                # "database is locked" failure. No module anywhere in this
                # codebase ever explicitly checkpoints the WAL journal, and
                # this admin GUI's own periodic self.after(2000,self._refresh)
                # read loop is exactly the kind of long-lived reader that can
                # prevent SQLite's automatic passive checkpointing from ever
                # fully shrinking the on-disk -wal file during a long
                # autonomous-learning session. A checkpoint is now run once
                # after every completed outer ("Autonomer Dauerlern-Zyklus")
                # GUI cycle -- i.e. every 5 real cycles -- which keeps the
                # WAL file consistently small rather than letting it grow
                # for hundreds of cycles before ever being reclaimed. This
                # call is fully guarded and can never raise or interrupt
                # autonomous learning; a failure here is only ever logged.
                try:
                    # BRAINSTEM_SHARED_CONNECTION_THREAD_SAFETY_FIX_V1: use
                    # worker_mem's own connection (this thread's dedicated
                    # connection) rather than self.mem.db, so the checkpoint
                    # call never touches the GUI thread's connection object.
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
        # BRAINSTEM_GUI_DUAL_SLEEP_AUTHORITY_FIX_V1: surface both sleep
        # authorities in the Regime line too, so the user can see at a
        # glance which one (if either) reports sleep, not just the emoji.
        self.behavior_text.configure(text="Regime: Orexin %s (%.2f) | BDNF %s (%.2f) | Cortisol %s (%.2f) | Schlaf: koop=%s/phase7a=%s" % (
            regimes.get("orexin", "n/a"), vals.get("orexin", 0.0),
            regimes.get("bdnf", "n/a"), vals.get("bdnf", 0.0),
            regimes.get("cortisol", "n/a"), vals.get("cortisol", 0.0),
            regimes.get("cooperative_mode", "n/a"), regimes.get("phase7a_mode", "n/a")))
        self.trend_text.configure(text="Homeostase: ADE %.2f | ECB %.2f | HIS %.2f" % (
            vals.get("adenosine", 0.0), vals.get("endocannabinoid", 0.0), vals.get("histamine", 0.0)))
        self.neuro_bars.draw(vals)
        emoji, name = compute_mood(vals, regimes)
        if self.mood_emoji is not None:
            self.mood_emoji.configure(text=emoji)
        if self.mood_name is not None:
            self.mood_name.configure(text=name)
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
        # BRAINSTEM_SHARED_CONNECTION_THREAD_SAFETY_FIX_V1: this background
        # thread previously shared self.mem (and thus self.mem.db) with the
        # GUI thread's own periodic reads, the identical root cause as the
        # autonomous-learning worker (see _get_worker_memory() for the full
        # explanation). drift_start() already refuses to run concurrently
        # with autonomous learning, but the GUI's own self.after(2000,
        # self._refresh) timer keeps running regardless of mode, so this
        # thread still needs its own dedicated connection.
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
