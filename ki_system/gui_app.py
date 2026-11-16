# -*- coding: utf-8 -*-
import tkinter as tk
import csv
import os
import textwrap
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
from ki_system import gui_theme as _theme


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
NEURO_COLORS = dict(_theme.NEURO_PALETTE)
NEURO_SHORT = {
    "dopamine": "Dopamin", "serotonin": "Serotonin", "glutamate": "Glutamat",
    "gaba": "GABA", "noradrenaline": "Noradrenalin", "acetylcholine": "Acetylcholin",
    "adenosine": "Adenosin", "endocannabinoid": "Endocannabinoide", "cortisol": "Cortisol",
    "histamine": "Histamin", "orexin": "Orexin", "bdnf": "BDNF",
}

MOOD_DISPLAY = {"Schlaeft und konsolidiert": "Schläft und konsolidiert", "Muede": "Müde"}

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
    def __init__(self, master, theme=None):
        self.master = master
        self.theme = theme
        self.tip = None
    def show(self, x, y, text):
        self.hide()
        self.tip = tk.Toplevel(self.master)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        if self.theme is not None:
            p = self.theme.p
            tk.Label(self.tip, text=text, bg=p["surface2"], fg=p["text"], relief=tk.FLAT, borderwidth=0,
                     highlightthickness=1, highlightbackground=p["border_strong"], padx=8, pady=4,
                     justify=tk.LEFT, font=self.theme.fonts["small"]).pack()
        else:
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
    """All 12 neuromodulators as labelled horizontal bars in two groups
    (core modulators | homeostasis & growth). Scales with the card width."""
    CHANGE_THRESHOLD = 0.005
    GROUPS = (("Kern-Neuromodulatoren", NEURO_CORE), ("Homöostase, Wachheit & Wachstum", NEURO_NEW))
    ROW_H = 27

    def __init__(self, master, theme=None, width=420, height=None):
        super().__init__(master, style="Inner.TFrame")
        self.theme = theme
        self.width = width
        self.height = height or (24 + 6 * self.ROW_H)
        self.canvas = tk.Canvas(self, width=width, height=self.height, highlightthickness=0, borderwidth=0)
        if theme is not None:
            theme.register(self.canvas, "canvas", bg="surface")
            theme.on_change(self._rebuild)
        self.canvas.pack(fill=tk.X, expand=True)
        self.hitboxes = []
        self.tooltip = NeuroTooltip(self, theme)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", lambda e: self.tooltip.hide())
        self.canvas.bind("<Configure>", self._on_resize)
        self._items = {}
        self._last_values = {}
        self._values = {k: 0.0 for k in (NEURO_CORE + NEURO_NEW)}
        self._built = False
        self._built_width = None
        self.draw(self._values)

    def _c(self, key, default):
        return self.theme.p[key] if self.theme is not None else default

    def _font(self, key, default):
        return self.theme.fonts[key] if self.theme is not None else default

    @staticmethod
    def _bar_end(tx0, tx1, value):
        # values above zero always show at least a 3 px stub
        end = tx0 + (tx1 - tx0) * value
        return max(end, tx0 + 3) if value > 0.0 else tx0 + 1

    def _on_resize(self, event):
        if self._built_width is not None and abs(event.width - self._built_width) < 4:
            return
        self._rebuild(event.width)

    def _rebuild(self, width=None):
        self.canvas.delete("all")
        self._items = {}
        self._built = False
        self._build_items(self._values, width)

    def _build_items(self, values, width=None):
        c = self.canvas
        if not width:
            width = int(c.winfo_width()) if int(c.winfo_width()) > 50 else self.width
        self._built_width = width
        gap = 32
        col_w = (width - gap) / 2.0
        text_c = self._c("text", "#222222"); muted = self._c("muted", "#555555")
        subtle = self._c("subtle", "#777777"); track = self._c("track", "#eeeeee")
        self.hitboxes = []
        for gi, (title, keys) in enumerate(self.GROUPS):
            x0 = gi * (col_w + gap)
            c.create_text(x0, 8, text=title.upper(), anchor="w", fill=subtle, font=self._font("caps", ("Arial", 8)))
            for ri, name in enumerate(keys):
                y = 24 + ri * self.ROW_H + self.ROW_H / 2.0
                value = _clamp01(values.get(name, 0.0))
                color = NEURO_COLORS.get(name, "#888888")
                abbr = NEURO_LABELS.get(name, name[:3].upper())
                c.create_rectangle(x0, y - 5, x0 + 4, y + 5, fill=color, outline=color)
                c.create_text(x0 + 12, y, text=abbr, anchor="w", fill=text_c, font=self._font("bold", ("Arial", 9, "bold")))
                c.create_text(x0 + 58, y, text=NEURO_SHORT.get(name, name), anchor="w", fill=muted,
                              font=self._font("small", ("Arial", 8)))
                tx0 = x0 + 172; tx1 = x0 + col_w - 50
                if tx1 - tx0 < 40:
                    tx1 = tx0 + 40
                c.create_rectangle(tx0, y - 5, tx1, y + 5, fill=track, outline=track)
                fill_id = c.create_rectangle(tx0, y - 5, self._bar_end(tx0, tx1, value), y + 5, fill=color, outline=color)
                value_id = c.create_text(x0 + col_w, y, text="%.2f" % value, anchor="e", fill=text_c,
                                         font=self._font("mono", ("Consolas", 9)))
                self._items[name] = {"fill_id": fill_id, "value_id": value_id, "tx0": tx0, "tx1": tx1, "y": y}
                self._last_values[name] = value
                self.hitboxes.append((x0, x0 + col_w, y - self.ROW_H / 2.0, y + self.ROW_H / 2.0, name))
        self._built = True

    def draw(self, values):
        for k in self._values:
            self._values[k] = _clamp01(values.get(k, self._values[k]))
        if not self._built:
            self._build_items(values)
            return
        for name, item in self._items.items():
            value = _clamp01(values.get(name, 0.0))
            last = self._last_values.get(name, None)
            if last is not None and abs(value - last) < self.CHANGE_THRESHOLD:
                continue
            tx0 = item["tx0"]; tx1 = item["tx1"]; y = item["y"]
            self.canvas.coords(item["fill_id"], tx0, y - 5, self._bar_end(tx0, tx1, value), y + 5)
            self.canvas.itemconfig(item["value_id"], text="%.2f" % value)
            self._last_values[name] = value

    def _on_motion(self, event):
        for x0, x1, y0, y1, key in self.hitboxes:
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.tooltip.show(self.winfo_rootx() + event.x, self.winfo_rooty() + event.y,
                                  "%s (%s): %.3f" % (NEURO_FULL.get(key, key), NEURO_LABELS.get(key, key),
                                                     self._values.get(key, 0.0)))
                return
        self.tooltip.hide()


class SleepGauge(tk.Canvas):
    """Adenosine sleep pressure on a 0..1 scale with the wake (lower) and
    sleep (upper) thresholds marked and the current level as a pointer."""

    def __init__(self, master, theme, height=62):
        super().__init__(master, height=height, highlightthickness=0, borderwidth=0)
        self.theme = theme
        theme.register(self, "canvas", bg="surface")
        theme.on_change(self.redraw)
        self.state = {"value": 0.0, "lower": 0.0, "upper": 0.0, "asleep": False}
        self.bind("<Configure>", lambda e: self.redraw())

    def set(self, value, lower, upper, asleep):
        new = {"value": _clamp01(value), "lower": _clamp01(lower), "upper": _clamp01(upper), "asleep": bool(asleep)}
        if new != self.state:
            self.state = new
            self.redraw()

    def redraw(self):
        p = self.theme.p; f = self.theme.fonts
        self.delete("all")
        w = max(int(self.winfo_width()), 120)
        x0, x1, y = 6, w - 6, 24
        sx = lambda v: x0 + (x1 - x0) * v
        st = self.state
        self.create_rectangle(x0, y - 5, x1, y + 5, fill=p["track"], outline=p["track"])
        if st["upper"] > st["lower"]:
            self.create_rectangle(sx(st["lower"]), y - 5, sx(st["upper"]), y + 5, fill=p["sleep_soft"], outline=p["sleep_soft"])
        color = p["sleep"] if st["asleep"] else p["warning"]
        self.create_rectangle(x0, y - 5, sx(st["value"]), y + 5, fill=color, outline=color)
        for key, label, anchor in (("lower", "Wachen ab %.3f", "n"), ("upper", "Schlaf ab %.3f", "n")):
            xv = sx(st[key])
            self.create_line(xv, y - 11, xv, y + 11, fill=p["text"], width=3)
            self.create_text(xv, y + 13, text=label % st[key], anchor=anchor, fill=p["text"], font=f["small"])
        xv = sx(st["value"])
        self.create_polygon(xv - 6, y - 15, xv + 6, y - 15, xv, y - 7, fill=p["text"], outline=p["text"])
        # zone captions (only where they fit and do not collide with the pointer)
        zones = (("Wach", x0, sx(st["lower"])), ("Übergang", sx(st["lower"]), sx(st["upper"])), ("Schlaf", sx(st["upper"]), x1))
        for name, a, b in zones:
            tw = f["small"].measure(name) + 8
            cx = (a + b) / 2.0
            if b - a > tw and abs(cx - xv) > tw / 2.0 + 8:
                self.create_text(cx, 7, text=name, fill=p["muted"], font=f["small"])


class App(tk.Tk):
    LOGGER_FLOAT_DEADBAND = 0.0005
    LOGGER_HEARTBEAT_SECONDS = 600.0

    def __init__(self, db_path="ki_memory.sqlite3"):
        super().__init__()
        self.title("Brainstem V8 Admin")
        self.geometry("1360x940")
        self.minsize(1180, 760)
        self.db_path = str(db_path)
        self.mem = Memory(self.db_path)
        self.dialogue = DialogueManager(self.mem)
        try:
            theme_name = str(self.mem.get_setting("gui_theme", "dark") or "dark")
        except Exception:
            theme_name = "dark"
        self.theme = _theme.Theme(self, theme_name)
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
        self._current_tab_name = "Import & Jobs"
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

    # ------------------------------------------------------------------ layout
    # The chat tab is hidden: the dialogue function is still rudimentary and
    # not in use, and a visible chat suggests abilities the system does not
    # have yet. The code stays in place; set SHOW_CHAT_TAB = True to bring the
    # tab back (it is then the first tab again).
    SHOW_CHAT_TAB = False
    CHAT_TAB_NAME = "Chat"
    TAB_NAMES = ["Import & Jobs", "Suche & Antwort", "Datenbank", "Fakten/Relationen", "Export/Konfig", "Drift-Report"]

    def _ui(self):
        self._app_bar()
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        self.nb = nb
        self.tabs = {}
        names = ([self.CHAT_TAB_NAME] if self.SHOW_CHAT_TAB else []) + self.TAB_NAMES
        for n in names:
            f = ttk.Frame(nb, padding=(14, 12, 14, 14))
            nb.add(f, text=n)
            self.tabs[n] = f
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        if self.SHOW_CHAT_TAB:
            self._chat_tab()
        self._import_tab()
        self._search_tab()
        self._db_tab()
        self._facts_tab()
        self._export_tab()
        self._drift_tab()
        try:
            nb.select(self.tabs["Import & Jobs"])
        except Exception:
            pass

    def _app_bar(self):
        bar, self._theme_buttons, self._update_theme_button = _theme.app_header(
            self, self.theme, "Admin-Konsole  ·  Datenbank: " + os.path.basename(self.db_path), self._choose_theme)
        self.theme_btn = self._theme_buttons["light"]
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=(14, 0))
        self.mode_pill = ttk.Label(bar, text="Bereit", style="PillIdle.TLabel")
        self.mode_pill.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Label(bar, text="Zustand", style="HeaderMuted.TLabel").pack(side=tk.RIGHT)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=(14, 14))
        self.header_mood = ttk.Label(bar, text="", style="HeaderMood.TLabel")
        self.header_mood.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Label(bar, text="Stimmung", style="HeaderMuted.TLabel").pack(side=tk.RIGHT)

    def set_theme(self, name):
        self.theme.apply(name)
        self._update_theme_button()
        self._style_head()

    def toggle_theme(self):
        self.set_theme("light" if self.theme.name == "dark" else "dark")
        try:
            self.mem.set_setting("gui_theme", self.theme.name)
        except Exception:
            pass

    def _on_tab_changed(self, event=None):
        try:
            self._current_tab_name = self.nb.tab(self.nb.select(), "text")
        except Exception:
            pass
        self.refresh()

    @staticmethod
    def _kv_row(parent, row, key, value_widget=None, value_text=""):
        ttk.Label(parent, text=key, style="CardMuted.TLabel").grid(row=row, column=0, sticky="w", pady=2)
        if value_widget is None:
            value_widget = ttk.Label(parent, text=value_text, style="Card.TLabel")
        value_widget.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=2)
        return value_widget

    def _chat_tab(self):
        f = self.tabs["Chat"]
        c = _theme.card(f, "Dialog", "Fragen an das Gedächtnis stellen. Enter sendet.")
        c.pack(fill=tk.BOTH, expand=True)
        box, self.chat_out = _theme.scrolled_text(self.theme, c, font="ui")
        box.pack(fill=tk.BOTH, expand=True)
        self.chat_out.insert(tk.END, "Noch keine Unterhaltung. Schreibe unten eine Frage und dr\u00fccke Enter.\n\n", "hint")
        self._chat_placeholder = True
        row = ttk.Frame(c, style="Inner.TFrame")
        row.pack(fill=tk.X, pady=(10, 0))
        self.chat_in = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.chat_in)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<Return>", lambda e: self.chat_send())
        ttk.Button(row, text="Senden", style="Accent.TButton", command=self.chat_send).pack(side=tk.LEFT, padx=(8, 0))

    def _import_tab(self):
        f = self.tabs["Import & Jobs"]
        f.columnconfigure(0, weight=0, minsize=440)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(1, weight=1)

        # --- control strip ---------------------------------------------------
        ctl = _theme.card(f, padding=(16, 10, 16, 12))
        ctl.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        g1 = ttk.Frame(ctl, style="Inner.TFrame"); g1.pack(side=tk.LEFT)
        ttk.Label(g1, text="IMPORT", style="Caps.TLabel").pack(anchor=tk.W, pady=(0, 4))
        import_row = ttk.Frame(g1, style="Inner.TFrame")
        import_row.pack(anchor=tk.W)
        ttk.Button(import_row, text="Import starten …", command=self.pick_import).pack(side=tk.LEFT)
        ttk.Label(import_row, text="Korpussprache", style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(14, 6))
        stored_lang = str(self.mem.get_setting("corpus_language", "de") or "de")
        self.corpus_language = tk.StringVar(value=stored_lang if stored_lang in ("de", "en") else "de")
        lang_box = ttk.Combobox(import_row, textvariable=self.corpus_language, values=("de", "en"),
                                 width=4, state="readonly")
        lang_box.pack(side=tk.LEFT)
        lang_box.bind("<<ComboboxSelected>>", self._on_corpus_language_changed)
        ttk.Separator(ctl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=20)
        g2 = ttk.Frame(ctl, style="Inner.TFrame"); g2.pack(side=tk.LEFT)
        ttk.Label(g2, text="AUTONOMES DAUERLERNEN  ·  LÄUFT BIS STOPP  ·  1 GUI-ZYKLUS = 5 SYSTEMZYKLEN", style="Caps.TLabel").pack(anchor=tk.W, pady=(0, 4))
        row = ttk.Frame(g2, style="Inner.TFrame")
        row.pack(anchor=tk.W)
        self.auto_start_btn = ttk.Button(row, text="▶  Autonom dauerhaft starten", style="Accent.TButton", command=self.auto_start)
        self.auto_start_btn.pack(side=tk.LEFT)
        self.auto_stop_btn = ttk.Button(row, text="■  Autonom stoppen", command=self.auto_stop_now, state=tk.DISABLED)
        self.auto_stop_btn.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Separator(ctl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=20)
        g3 = ttk.Frame(ctl, style="Inner.TFrame"); g3.pack(side=tk.LEFT)
        ttk.Label(g3, text="LAUFENDEN VORGANG", style="Caps.TLabel").pack(anchor=tk.W, pady=(0, 4))
        self.abort_btn = ttk.Button(g3, text="Import/Lernen abbrechen", command=lambda: setattr(self, "cancel", True),
                                    state=tk.DISABLED)
        self.abort_btn.pack(anchor=tk.W)

        # --- left column -----------------------------------------------------
        left_col = ttk.Frame(f)
        left_col.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        prog = _theme.card(left_col, "Fortschritt")
        prog.pack(fill=tk.X)
        r1 = ttk.Frame(prog, style="Inner.TFrame"); r1.pack(fill=tk.X)
        ttk.Label(r1, text="Gesamtfortschritt (gelesene Chunks)", style="CardMuted.TLabel").pack(side=tk.LEFT)
        self.total_pct_label = ttk.Label(r1, text="0.0 %", style="CardBold.TLabel")
        self.total_pct_label.pack(side=tk.RIGHT)
        self.bar_total = ttk.Progressbar(prog, maximum=100)
        self.bar_total.pack(fill=tk.X, pady=(4, 10))
        r2 = ttk.Frame(prog, style="Inner.TFrame"); r2.pack(fill=tk.X)
        ttk.Label(r2, text="Aktueller GUI-Zyklus (Schritt/5)", style="CardMuted.TLabel").pack(side=tk.LEFT)
        self.cycle_label = ttk.Label(r2, text="0 / 5", style="CardBold.TLabel")
        self.cycle_label.pack(side=tk.RIGHT)
        self.bar_cycle = ttk.Progressbar(prog, maximum=100, style="Success.Horizontal.TProgressbar")
        self.bar_cycle.pack(fill=tk.X, pady=(4, 12))
        tiles = ttk.Frame(prog, style="Inner.TFrame"); tiles.pack(fill=tk.X)
        self.kpi = {}
        for i, (key, label) in enumerate((("chunks", "Chunks gelesen"), ("facts", "Fakten"), ("relations", "Relationen"),
                                          ("ontology", "Ontologie"), ("questions", "Fragen"), ("hypotheses", "Hypothesen"))):
            tiles.columnconfigure(i % 3, weight=1, uniform="kpi")
            t = ttk.Frame(tiles, style="Tile.TFrame", padding=(10, 4, 10, 5))
            t.grid(row=i // 3, column=i % 3, sticky="ew", padx=(0 if i % 3 == 0 else 6, 0), pady=(0, 6))
            self.kpi[key] = ttk.Label(t, text="-", style="TileValue.TLabel")
            self.kpi[key].pack(anchor=tk.W)
            ttk.Label(t, text=label, style="TileLabel.TLabel").pack(anchor=tk.W)
        self.status = ttk.Label(prog, text="Bereit.", style="CardSmall.TLabel", wraplength=400, justify=tk.LEFT)
        self.status.pack(anchor=tk.W, pady=(4, 0))

        sleep = _theme.card(left_col, "Schlaf & Reife")
        sleep.pack(fill=tk.X, pady=(12, 0))
        self.sleep_pill = ttk.Label(sleep.header, text="n/a", style="PillIdle.TLabel")
        self.sleep_pill.pack(side=tk.RIGHT)
        self.sleep_gauge = SleepGauge(sleep, self.theme)
        self.sleep_gauge.pack(fill=tk.X, pady=(2, 6))
        grid = ttk.Frame(sleep, style="Inner.TFrame"); grid.pack(fill=tk.X)
        self.sleep_values = {}
        for i, (key, label) in enumerate((("pressure", "Schlafdruck (Adenosin)"), ("dwell", "Verweildauer im Zustand"),
                                          ("reason", "Letzter Wechsel"))):
            self.sleep_values[key] = self._kv_row(grid, i, label)
        r3 = ttk.Frame(sleep, style="Inner.TFrame"); r3.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(r3, text="Entwicklungsreife", style="CardMuted.TLabel").pack(side=tk.LEFT)
        self.maturity_label = ttk.Label(r3, text="0.0 %", style="CardBold.TLabel")
        self.maturity_label.pack(side=tk.RIGHT)
        self.bar_maturity = ttk.Progressbar(sleep, maximum=100, style="Sleep.Horizontal.TProgressbar")
        self.bar_maturity.pack(fill=tk.X, pady=(4, 0))

        logc = _theme.card(left_col, "GUI-Wertelogger (fortlaufende CSV)",
                           "Alle angezeigten Werte als gui_log_<Zeit>.csv (f\u00fcr den BrainStem CSV Viewer).")
        logc.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        logger_row = ttk.Frame(logc, style="Inner.TFrame")
        logger_row.pack(fill=tk.X)
        ttk.Button(logger_row, text="Ordner \u00f6ffnen", style="Small.TButton", width=14,
                   command=lambda: self._open_folder(os.path.abspath(os.getcwd()))).pack(side=tk.RIGHT)
        self.gui_logger_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(logger_row, text="Logger aktiv", variable=self.gui_logger_enabled, style="Card.TCheckbutton",
                        command=self._logger_toggle).pack(side=tk.LEFT)
        self.gui_logger_changes_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(logger_row, text="Nur bei Änderung loggen", style="Card.TCheckbutton",
                        variable=self.gui_logger_changes_only).pack(side=tk.LEFT, padx=(16, 0))
        self.logger_status = ttk.Label(logc, text="Logger inaktiv", style="StatusIdle.TLabel", wraplength=400, justify=tk.LEFT)
        self.logger_status.pack(anchor=tk.W, pady=(8, 0))

        # --- right column ----------------------------------------------------
        right_col = ttk.Frame(f)
        right_col.grid(row=1, column=1, sticky="nsew")
        neuro = _theme.card(right_col, "Digitale Botenstoffe")
        neuro.pack(fill=tk.X)
        ttk.Label(neuro.header, text="Maus über einen Balken zeigt Name und Wert", style="CardSmall.TLabel").pack(side=tk.RIGHT)
        self.neuro_bars = NeuromodulatorBars(neuro, self.theme)
        self.neuro_bars.pack(fill=tk.X)
        ttk.Separator(neuro).pack(fill=tk.X, pady=(10, 8))
        details = ttk.Frame(neuro, style="Inner.TFrame"); details.pack(fill=tk.X)
        details.columnconfigure(1, weight=1)
        self.behavior_text = self._kv_row(details, 0, "Regime", ttk.Label(details, text="-", style="Card.TLabel"))
        self.integration_text = self._kv_row(details, 1, "Integration", ttk.Label(details, text="-", style="Card.TLabel"))
        self.evidence_text = self._kv_row(details, 2, "Phase-6a-Evidenz", ttk.Label(details, text="-", style="Card.TLabel"))
        self.neuro_text = self._kv_row(details, 3, "Kernwerte", ttk.Label(details, text="-", style="Card.TLabel"))
        self.trend_text = self._kv_row(details, 4, "Hom\u00f6ostase", ttk.Label(details, text="-", style="Card.TLabel"))
        self._numeric_rows = [w for w in details.grid_slaves() if int(w.grid_info()["row"]) in (3, 4)]
        self._numeric_visible = tk.BooleanVar(value=False)
        self.numeric_toggle = ttk.Button(neuro.header, style="Link.TButton", command=self._toggle_numeric_rows)
        self.numeric_toggle.pack(side=tk.RIGHT, padx=(0, 16))
        self._toggle_numeric_rows(initial=True)
        legend = ("Integration: phasisch/tonisch = Phase-6a-Rohwert / final gemischter Wert (w = tonic_weight, "
                  "cortisol-gesteuert). GLU/GABA bleiben ausschließlich von Phase 7c verantwortet.")
        self.neuro_legend = ttk.Label(neuro, text=legend, style="CardSmall.TLabel", wraplength=760, justify=tk.LEFT)
        self.neuro_legend.pack(anchor=tk.W, pady=(8, 0))
        def _wrap_details(e):
            self.neuro_legend.configure(wraplength=max(300, e.width - 40))
            for w in (self.behavior_text, self.integration_text, self.evidence_text, self.neuro_text, self.trend_text):
                w.configure(wraplength=max(240, e.width - 180))
        neuro.bind("<Configure>", _wrap_details)

        logcard = _theme.card(right_col, "Protokoll")
        logcard.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.log_filter = tk.StringVar(value="Alle Meldungen")
        lf = ttk.Combobox(logcard.header, textvariable=self.log_filter, state="readonly", width=22,
                          values=("Alle Meldungen", "Nur Warnungen und Fehler"))
        lf.bind("<<ComboboxSelected>>", lambda e: self._apply_log_filter())
        ttk.Button(logcard.header, text="Leeren", style="Small.TButton", width=7,
                   command=lambda: self.log.delete("1.0", tk.END)).pack(side=tk.RIGHT)
        ttk.Button(logcard.header, text="Kopieren", style="Small.TButton", width=9,
                   command=lambda: self._copy_text(self.log.get("1.0", "end-1c"), "Protokoll")).pack(side=tk.RIGHT, padx=(0, 6))
        lf.pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Label(logcard.header, text="Neueste 200 Zeilen", style="CardSmall.TLabel").pack(side=tk.RIGHT, padx=(0, 12))
        box, self.log = _theme.scrolled_text(self.theme, logcard, font="mono", height=6)
        box.pack(fill=tk.BOTH, expand=True)
        _theme.snap_lines(self.log)
        self.log.bind("<Configure>", lambda e: setattr(self, "_log_chars", max(40, int((e.width - 30) / max(1, self.theme.fonts["mono"].measure("0"))))), add="+")

    def _copy_text(self, text, what):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.println("(i) %s in die Zwischenablage kopiert." % what)
        except Exception:
            pass

    def _toggle_numeric_rows(self, initial=False):
        if not initial:
            self._numeric_visible.set(not self._numeric_visible.get())
        show = self._numeric_visible.get()
        for w in self._numeric_rows:
            if show:
                w.grid()
            else:
                w.grid_remove()
        self.numeric_toggle.configure(text=("\u25be  Werte als Text ausblenden" if show else "\u25b8  Werte als Text"))

    def _on_corpus_language_changed(self, event=None):
        value = self.corpus_language.get()
        if value not in ("de", "en"):
            value = "de"
            self.corpus_language.set(value)
        self.mem.set_setting("corpus_language", value)
        self.println("Korpussprache auf '" + value + "' gesetzt (wirkt ab dem naechsten Zyklus).")

    def _search_tab(self):
        f = self.tabs["Suche & Antwort"]
        c = _theme.card(f, "Suche & Antwort", "Suchen (Enter): Trefferliste der passendsten Textstellen.   "
                                              "Antwort: zusammengesetzte Antwort mit Belegen (JSON).")
        c.pack(fill=tk.BOTH, expand=True)
        row = ttk.Frame(c, style="Inner.TFrame"); row.pack(fill=tk.X, pady=(0, 10))
        self.q = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.q)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<Return>", lambda e: self.do_search())
        ttk.Button(row, text="Suchen", style="Accent.TButton", command=self.do_search).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(row, text="Antwort", command=self.do_answer).pack(side=tk.LEFT, padx=(8, 0))
        box, self.out = _theme.scrolled_text(self.theme, c, font="ui")
        box.pack(fill=tk.BOTH, expand=True)
        self.out.insert(tk.END, "Noch keine Ergebnisse. Suchbegriff eingeben und „Suchen“ oder „Antwort“ wählen.", "hint")

    def _table(self, parent, columns, lead=None):
        """Treeview with themed headings, scrollbar, zebra rows, sorting,
        a text filter, ellipsis for long cells and a full-text tooltip.
        `lead` = (title, width, source_index, fn) shows an image column in
        front (the Treeview tree column) and hides the source column."""
        box = ttk.Frame(parent, style="Inner.TFrame")
        tree = ttk.Treeview(box, columns=[c[0] for c in columns], show=("tree headings" if lead else "headings"))
        for cid, title, width, anchor, stretch in columns:
            tree.heading(cid, text=title, anchor=anchor, command=lambda c=cid, t=tree: self._sort_tree(t, c, toggle=True))
            tree.column(cid, width=width, anchor=anchor, stretch=stretch, minwidth=50)
        tree._lead_fn = None
        tree._lead_idx = None
        if lead:
            title, width, src, fn = lead
            tree.heading("#0", text=title, anchor=tk.W, command=lambda t=tree: self._sort_tree(t, "#0", toggle=True))
            tree.column("#0", width=width, minwidth=width, stretch=False, anchor=tk.W)
            tree["displaycolumns"] = [c[0] for i, c in enumerate(columns) if i != src]
            tree._lead_fn = fn
            tree._lead_idx = src
        sb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree._sort = None
        tree._rows_cache = None
        tree._full = {}
        tree._filter = tk.StringVar()
        tree._titles = {c[0]: c[1] for c in columns}
        if lead:
            tree._titles["#0"] = lead[0]
        tree._render = {}
        tip = NeuroTooltip(tree, self.theme)
        tip._cell = None
        def _motion(event, t=tree):
            item = t.identify_row(event.y); col = t.identify_column(event.x)
            if not item or not col:
                tip.hide(); tip._cell = None; return
            if (item, col) == tip._cell:
                return
            tip._cell = (item, col)
            try:
                text = str(t._full[item][int(col[1:]) - 1])
            except Exception:
                text = ""
            if text != str(t.set(item, t["columns"][int(col[1:]) - 1])):
                tip.show(event.x_root, event.y_root, textwrap.fill(text, 90))
            else:
                tip.hide()
        tree.bind("<Motion>", _motion)
        tree.bind("<Leave>", lambda e: (tip.hide(), setattr(tip, "_cell", None)))
        tree.bind("<ButtonRelease-1>", lambda e, t=tree: self.after(30, lambda: self._render_tree(t)), add="+")
        tree.bind("<Configure>", lambda e, t=tree: self.after_idle(lambda: self._render_tree(t)), add="+")
        self._zebra(tree)
        self.theme.on_change(lambda t=tree: self._zebra(t))
        return box, tree

    def _table_toolbar(self, card, tree, noun):
        bar = ttk.Frame(card, style="Inner.TFrame"); bar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(bar, text="Aktualisieren", command=self.refresh).pack(side=tk.LEFT)
        ttk.Label(bar, text="Filter (alle Spalten)", style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(18, 6))
        entry = ttk.Entry(bar, textvariable=tree._filter, width=36)
        entry.pack(side=tk.LEFT, ipady=1)
        ttk.Button(bar, text="\u2715", style="Small.TButton", width=2, command=lambda: tree._filter.set("")).pack(side=tk.LEFT, padx=(4, 0))
        count = ttk.Label(bar, text="", style="CardMuted.TLabel")
        count.pack(side=tk.RIGHT)
        tree._count_label = count
        tree._noun = noun
        tree._filter.trace_add("write", lambda *a, t=tree: self._apply_filter(t))
        return count

    def _zebra(self, tree):
        tree.tag_configure("odd", background=self.theme.p["zebra"])
        tree.tag_configure("even", background=self.theme.p["field"])

    def _cell_text(self, tree, col_index, value):
        """Shorten a cell to the column width with an ellipsis."""
        text = str(value)
        cid = tree["columns"][col_index]
        width = max(40, int(tree.column(cid, "width")) - 16)
        font = self.theme.fonts["ui"]
        if font.measure(text) <= width:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "…") <= width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…"

    def _render_tree(self, tree):
        widths = tuple(int(tree.column(c, "width")) for c in tree["columns"])
        for item in tree.get_children(""):
            full = tree._full.get(item)
            if full is None:
                continue
            if tree._render.get(item) == widths:
                continue
            tree.item(item, values=[self._cell_text(tree, i, v) for i, v in enumerate(full)])
            tree._render[item] = widths

    def _sort_tree(self, tree, col, toggle=False):
        if toggle:
            prev = tree._sort
            tree._sort = (col, (not prev[1]) if prev and prev[0] == col else False)
        if tree._sort:
            col, rev = tree._sort
            idx = tree._lead_idx if col == "#0" else list(tree["columns"]).index(col)
            def key(item):
                v = tree._full.get(item, ("",) * (idx + 1))[idx]
                try:
                    return (0, float(str(v).split()[0]), "")
                except (TypeError, ValueError, IndexError):
                    return (1, 0.0, str(v).lower())
            items = sorted(tree.get_children(""), key=key, reverse=rev)
            for i, item in enumerate(items):
                tree.move(item, "", i)
        for i, item in enumerate(tree.get_children("")):
            tree.item(item, tags=("odd" if i % 2 else "even",))
        for cid, title in tree._titles.items():
            arrow = ""
            if tree._sort and cid == tree._sort[0]:
                arrow = " ▼" if tree._sort[1] else " ▲"
            tree.heading(cid, text=title + arrow)

    def _apply_filter(self, tree):
        rows = tree._rows_cache or []
        needle = tree._filter.get().strip().lower()
        shown = [r for r in rows if not needle or any(needle in str(v).lower() for v in r)]
        top = tree.yview()[0] if tree.get_children() else 0.0
        tree.delete(*tree.get_children())
        tree._full = {}
        tree._render = {}
        for values in shown:
            if tree._lead_fn is not None:
                text, image = tree._lead_fn(values)
                item = tree.insert("", tk.END, values=values, text=text, image=image)
            else:
                item = tree.insert("", tk.END, values=values)
            tree._full[item] = values
        self._sort_tree(tree, None)
        self._render_tree(tree)
        tree.yview_moveto(top)
        total = "%d %s" % (len(rows), tree._noun)
        tree._count_label.configure(text=(("%d von " % len(shown)) + total if needle else total) + "  (neueste, max. 2000)")

    def _fill_tree(self, tree, rows, count_label, noun):
        if rows == tree._rows_cache:
            return
        tree._rows_cache = rows
        self._apply_filter(tree)

    @staticmethod
    def _conf_cell(value):
        try:
            v = float(value or 0.0)
        except (TypeError, ValueError):
            v = 0.0
        return "%.2f" % v

    def _paint_conf_images(self):
        """Five-segment confidence bars as images for the facts table."""
        if not hasattr(self, "_conf_imgs"):
            self._conf_imgs = [tk.PhotoImage(master=self, width=66, height=14) for _ in range(6)]
        p = self.theme.p
        for level, img in enumerate(self._conf_imgs):
            img.blank()
            for seg in range(5):
                x0 = seg * 13
                if seg < level:
                    color = p["warning"] if level <= 1 else (p["accent"] if level <= 3 else p["success"])
                    img.put(color, to=(x0, 2, x0 + 11, 12))
                else:
                    img.put(p["border_strong"], to=(x0, 2, x0 + 11, 12))
                    img.put(p["track"], to=(x0 + 1, 3, x0 + 10, 11))

    def _paint_legend_swatches(self):
        for sw, key in self._legend_swatches:
            sw.delete("all")
            sw.create_rectangle(1, 2, 12, 12, fill=self.theme.p[key], outline=self.theme.p[key])

    def _apply_log_filter(self):
        only_problems = self.log_filter.get().startswith("Nur")
        self.log.tag_configure("cat_plain", elide=only_problems)
        self.log.see(tk.END)

    def _conf_lead(self, values):
        try:
            v = float(values[3])
        except (TypeError, ValueError, IndexError):
            v = 0.0
        return ("  %.2f" % v, self._conf_imgs[int(round(max(0.0, min(1.0, v)) * 5))])

    def _db_tab(self):
        f = self.tabs["Datenbank"]
        c = _theme.card(f, "Dokumente", "Importierte Quellen. Spaltenkopf sortiert, Filter durchsucht alle Spalten, "
                                       "Maus über gekürzter Zelle zeigt den Volltext.")
        c.pack(fill=tk.BOTH, expand=True)
        box, self.docs = self._table(c, [("id", "ID", 70, tk.E, False), ("title", "Titel", 360, tk.W, True),
                                          ("kind", "Art", 90, tk.W, False), ("path", "Pfad", 520, tk.W, True)])
        self.docs_count = self._table_toolbar(c, self.docs, "Dokumente")
        box.pack(fill=tk.BOTH, expand=True)

    def _facts_tab(self):
        f = self.tabs["Fakten/Relationen"]
        c = _theme.card(f, "Fakten & Relationen", "Gelernte Aussagen (Subjekt, Relation, Wert) mit Konfidenz. Spaltenkopf sortiert, "
                                                  "Filter durchsucht alle Spalten, Maus über gekürzter Zelle zeigt den Volltext.")
        c.pack(fill=tk.BOTH, expand=True)
        self._legend_swatches = []
        self._paint_conf_images()
        self.theme.on_change(self._paint_conf_images)
        box, self.facts = self._table(c, [("s", "Subjekt", 300, tk.W, True), ("r", "Relation", 130, tk.W, False),
                                           ("v", "Wert", 520, tk.W, True), ("conf", "Konfidenz", 100, tk.E, False)],
                                      lead=("Konfidenz (0\u20131)", 140, 3, self._conf_lead))
        self.facts_count = self._table_toolbar(c, self.facts, "Fakten")
        legend = ttk.Frame(c, style="Inner.TFrame")
        legend.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
        ttk.Label(legend, text="KONFIDENZ-BALKEN", style="Caps.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        for key, text in (("warning", "niedrig (unter 0.30)"), ("accent", "mittel (0.30 bis 0.69)"), ("success", "hoch (ab 0.70)")):
            sw = tk.Canvas(legend, width=14, height=14)
            self.theme.register(sw, "canvas", bg="surface")
            sw.pack(side=tk.LEFT, padx=(0, 6))
            self._legend_swatches.append((sw, key))
            ttk.Label(legend, text=text, style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(0, 18))
        self._paint_legend_swatches()
        self.theme.on_change(self._paint_legend_swatches)
        box.pack(fill=tk.BOTH, expand=True)

    def _export_tab(self):
        f = self.tabs["Export/Konfig"]
        f.columnconfigure(0, weight=1, uniform="exp")
        f.columnconfigure(1, weight=1, uniform="exp")
        exp = _theme.card(f, "Export", "Schreibt die Dateien in das Arbeitsverzeichnis des Programms.")
        exp.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        for text, cmd, hint in (("Export JSON", self._safe_export_json, "export_ki_system.json"),
                                ("Export Fakten CSV", self._safe_export_facts, "facts.csv")):
            r = ttk.Frame(exp, style="Inner.TFrame"); r.pack(fill=tk.X, pady=(0, 8))
            ttk.Button(r, text=text, command=cmd, width=20).pack(side=tk.LEFT)
            ttk.Label(r, text="→  " + hint, style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(12, 0))

        cfg = _theme.card(f, "Import-Konfiguration", "Obergrenze für Artikel pro ZIM-Import.")
        cfg.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(cfg, text="Max. ZIM-Artikel beim Import", style="Card.TLabel").pack(anchor=tk.W)
        r = ttk.Frame(cfg, style="Inner.TFrame"); r.pack(fill=tk.X, pady=(6, 0))
        self.max_articles = tk.IntVar(value=int(self.mem.get_setting("max_articles", 2000) or 2000))
        ttk.Spinbox(r, from_=1, to=1000000, textvariable=self.max_articles, width=12).pack(side=tk.LEFT)
        ttk.Button(r, text="Speichern", style="Accent.TButton", command=self.save_config).pack(side=tk.LEFT, padx=(8, 0))
        self.config_value = ttk.Label(cfg, text="Aktueller Wert: " + str(self.mem.get_setting("max_articles", 2000)),
                                      style="CardMuted.TLabel")
        self.config_value.pack(anchor=tk.W, pady=(8, 0))

        f.rowconfigure(4, weight=1)
        fb = ttk.Frame(f, style="Footer.TFrame", padding=(14, 8, 14, 8))
        fb.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Label(fb, text="LETZTE AKTION", style="FooterCaps.TLabel").pack(side=tk.LEFT, padx=(0, 12))
        self.config_status = ttk.Label(fb, text="\u25cb  Noch keine Aktion in dieser Sitzung", style="FootStatusIdle.TLabel")
        self.config_status.pack(side=tk.LEFT)

        info = _theme.card(f, "Dateien & Speicherorte", "Wohin Exporte, CSV-Logs und Sicherungen geschrieben werden.")
        info.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        grid = ttk.Frame(info, style="Inner.TFrame"); grid.pack(fill=tk.X)
        grid.columnconfigure(1, weight=1)
        project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backup = os.path.join(os.path.dirname(project), os.path.basename(project) + "_fullbackup_before_learning_reset_<Datum_Uhrzeit>")
        for i, (label, path, folder) in enumerate((("Datenbank", os.path.abspath(self.db_path), os.path.dirname(os.path.abspath(self.db_path))),
                                                   ("Exporte & CSV-Logs", os.path.abspath(os.getcwd()), os.path.abspath(os.getcwd())),
                                                   ("Reset-Backup", backup, os.path.dirname(project)))):
            ttk.Label(grid, text=label, style="CardMuted.TLabel").grid(row=i, column=0, sticky="w", pady=3)
            plabel = ttk.Label(grid, text=self._middle_ellipsis(path, 130), style="Card.TLabel")
            plabel.grid(row=i, column=1, sticky="w", padx=(12, 8), pady=3)
            ptip = NeuroTooltip(plabel, self.theme)
            plabel.bind("<Enter>", lambda e, t=ptip, p=path: t.show(e.x_root, e.y_root, p))
            plabel.bind("<Leave>", lambda e, t=ptip: t.hide())
            ttk.Button(grid, text="Kopieren", style="Small.TButton", width=9,
                       command=lambda p=path, l=label: self._copy_path(p, l)).grid(row=i, column=2, padx=(0, 6), pady=3)
            ttk.Button(grid, text="Ordner öffnen", style="Small.TButton", width=14,
                       command=lambda d=folder: self._open_folder(d)).grid(row=i, column=3, pady=3)

        dz = _theme.card(f, "Gefahrenzone", style="Danger.Card.TFrame", title_style="Danger.CardTitle.TLabel")
        dz.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        ttk.Label(dz, text="Achtung: entfernt alle gelernten Daten, ZIM-Korpus bleibt erhalten.",
                  style="Card.TLabel").pack(anchor=tk.W)
        ttk.Label(dz, text="Vorher wird automatisch ein Backup (Projektkopie neben dem Projektordner) angelegt und eine "
                           "Sicherheitsabfrage gestellt. Während Import, Lernen oder Drift-Test ist der Knopf gesperrt.",
                  style="CardSmall.TLabel", wraplength=1100, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 10))
        self.reset_btn = ttk.Button(dz, text="Lernsystem zurücksetzen (Korpus bleibt) …", style="Danger.TButton",
                                    command=self.reset_learning_gui)
        self.reset_btn.pack(anchor=tk.W)

    def _choose_theme(self, name):
        if name != self.theme.name:
            self.toggle_theme()

    @staticmethod
    def _middle_ellipsis(text, limit):
        text = str(text)
        if len(text) <= limit:
            return text
        keep = (limit - 1) // 2
        return text[:keep] + "…" + text[-(limit - 1 - keep):]

    def _copy_path(self, path, label):
        try:
            self.clipboard_clear(); self.clipboard_append(path)
            self._feedback("%s-Pfad kopiert" % label)
        except Exception as exc:
            self._feedback("Kopieren fehlgeschlagen: " + str(exc), ok=False)

    def _open_folder(self, folder):
        try:
            os.startfile(folder)
            self._feedback("Ordner geöffnet: " + folder)
        except Exception as exc:
            self._feedback("Ordner nicht geöffnet: " + str(exc), ok=False)

    def _feedback(self, text, ok=True):
        try:
            self.config_status.configure(text=("\u2713  " if ok else "\u2715  ") + text + "   \u00b7   " +
                                         datetime.now().strftime("%H:%M:%S"),
                                         style="FootStatusRun.TLabel" if ok else "FootStatusStop.TLabel")
        except Exception:
            pass

    # ------------------------------------------------------------ mood window
    def _create_floating_head(self):
        self.head = tk.Toplevel(self)
        self.head.overrideredirect(True)
        self.head.attributes("-topmost", True)
        frame = tk.Frame(self.head, relief=tk.FLAT, borderwidth=0, highlightthickness=1)
        frame.pack()
        self._head_frame = frame
        self.mood_caption = tk.Label(frame, text="STIMMUNG", anchor="center")
        self.mood_caption.pack(padx=12, pady=(8, 0))
        self.mood_emoji = tk.Label(frame, text="(^_^)", width=11, anchor="center")
        self.mood_emoji.pack(padx=12, pady=(0, 0))
        self.mood_name = tk.Label(frame, text="Ausgewogen", anchor="center")
        self.mood_name.pack(padx=12, pady=(0, 2))
        self.mood_detail = tk.Label(frame, text="", anchor="center")
        self.mood_detail.pack(padx=12, pady=(0, 10))
        self._style_head()
        self.update_idletasks()
        try:
            hx = self.winfo_x() + self.winfo_width() + 8
            hy = self.winfo_y() + 40
        except Exception:
            hx, hy = 100, 100
        self.head.geometry("+%d+%d" % (hx, hy))
        self._drag = {"x": 0, "y": 0}
        for w in (self.head, frame, self.mood_caption, self.mood_emoji, self.mood_name, self.mood_detail):
            w.bind("<Button-1>", self._head_press)
            w.bind("<B1-Motion>", self._head_drag)

    def _style_head(self):
        if getattr(self, "_head_frame", None) is None:
            return
        p = self.theme.p; fonts = self.theme.fonts
        try:
            self._head_frame.configure(bg=p["surface"], highlightbackground=p["border_strong"], highlightcolor=p["border_strong"])
            self.mood_caption.configure(bg=p["surface"], fg=p["subtle"], font=fonts["caps"])
            self.mood_emoji.configure(bg=p["surface"], fg=p["text"], font=fonts["face"])
            self.mood_name.configure(bg=p["surface"], fg=p["text"], font=fonts["bold"])
            self.mood_detail.configure(bg=p["surface"], fg=p["muted"], font=fonts["small"])
        except Exception:
            pass

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
            self._update_mode_pill()
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
            self._feedback("Export JSON gespeichert: export_ki_system.json")
        except Exception as e:
            self._feedback("Export JSON Fehler: " + str(e), ok=False)
    def _safe_export_facts(self):
        try:
            self.mem.export_facts_csv("facts.csv")
            self._feedback("Fakten CSV gespeichert: facts.csv")
        except Exception as e:
            self._feedback("Fakten CSV Fehler: " + str(e), ok=False)
    def save_config(self):
        try:
            value = max(1, int(self.max_articles.get()))
            self.mem.set_setting("max_articles", value)
            self._feedback("Gespeichert. Aktueller Wert: %d" % value)
            self.config_value.configure(text="Aktueller Wert: %d" % value)
        except Exception as e:
            self._feedback("Speichern fehlgeschlagen: " + str(e), ok=False)
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
    @staticmethod
    def _log_tag(line):
        text = line.strip()
        upper = text.upper()
        if text.startswith("!!") or "FEHLER" in upper or "ABGEBROCHEN" in upper:
            return "err"
        if text.startswith("==="):
            return "head"
        if "degradiert" in text or "WARN" in upper or "uebersprungen" in text and not text.startswith("(i)"):
            return "warn"
        if text.startswith("(i)"):
            return "info"
        if text.startswith("FERTIG") or "gestartet" in text:
            return "ok"
        return ()

    def _log_display_lines(self, line):
        """Display-only layout: long ' | '-separated status lines are broken
        at their separators instead of mid-value (log text is unchanged)."""
        width = getattr(self, "_log_chars", 120)
        if len(line) <= width or " | " not in line:
            return [line]
        parts = line.split(" | ")
        out, cur = [], parts[0]
        for part in parts[1:]:
            if len(cur) + 3 + len(part) <= width:
                cur += " | " + part
            else:
                out.append(cur)
                cur = "    " + part
        out.append(cur)
        return out

    def println(self, msg):
        def _do():
            try:
                for line in str(msg).split("\n"):
                    tag = self._log_tag(line)
                    base = ((tag,) if tag else ()) + ("wrapind", "cat_problem" if tag in ("err", "warn") else "cat_plain")
                    for shown in self._log_display_lines(line):
                        pieces = shown.split(" | ")
                        for k, piece in enumerate(pieces):
                            if k:
                                self.log.insert(tk.END, " | ", base + ("sep",))
                            self.log.insert(tk.END, piece, base)
                        self.log.insert(tk.END, "\n", base)
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
        self._gui_enqueue(lambda: (self.bar_cycle.configure(value=c / max(1, t) * 100),
                                   self.cycle_label.configure(text="%s / %s" % (c, t)),
                                   self.status.configure(text='%s/%s %s' % (c, t, msg))))
    def _set_cycle_bar(self, step, total):
        self._gui_enqueue(lambda: (self.bar_cycle.configure(value=step / max(1, total) * 100),
                                   self.cycle_label.configure(text="%d / %d" % (step, total))))
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
            if getattr(self, "_chat_placeholder", False):
                self.chat_out.delete("1.0", tk.END)
                self._chat_placeholder = False
            self.chat_out.insert(tk.END, "Du: ", "you")
            self.chat_out.insert(tk.END, t + "\n\n")
            self.chat_out.insert(tk.END, "Antwort:\n", ("bot", "answer"))
            self.chat_out.insert(tk.END, r.response + note + "\n", "answer")
            self.chat_out.insert(tk.END, "\n")
            self.chat_out.see(tk.END)
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
            self._update_mode_pill()
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
        hits = list(semantic_search(self.mem, self.q.get(), 25))
        _theme.render_hits(self.out, hits, self.q.get())
    def do_answer(self):
        self.out.delete("1.0", tk.END)
        self.out.insert(tk.END, json.dumps(answer(self.mem, self.q.get()), ensure_ascii=False, indent=2), "mono")
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
        self._logger_pill()

    def _logger_pill(self):
        try:
            text = str(self.logger_status.cget("text"))
            if "Fehler" in text:
                style, dot = "StatusStop.TLabel", "\u25cf"
            elif getattr(self, "_logger_file", None) is not None:
                style, dot = "StatusRun.TLabel", "\u25cf"
            else:
                style, dot = "StatusIdle.TLabel", "\u25cb"
            if not text.startswith(("\u25cf", "\u25cb")):
                text = dot + "  " + text
            elif text[0] != dot:
                text = dot + text[1:]
            self.logger_status.configure(style=style, text=text)
        except Exception:
            pass

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
        sep = "   ·   "
        self.neuro_text.configure(text=sep.join("%s %.2f" % (NEURO_LABELS[k], vals.get(k, 0.0)) for k in NEURO_CORE))
        self.behavior_text.configure(text=sep.join((
            "Orexin %s (%.2f)" % (regimes.get("orexin", "n/a"), vals.get("orexin", 0.0)),
            "BDNF %s (%.2f)" % (regimes.get("bdnf", "n/a"), vals.get("bdnf", 0.0)),
            "Cortisol %s (%.2f)" % (regimes.get("cortisol", "n/a"), vals.get("cortisol", 0.0)),
            "Histamin %s (%.2f)" % (regimes.get("histamine", "n/a"), vals.get("histamine", 0.0)))))
        self.trend_text.configure(text="ADE %.2f%sECB %.2f%sHIS %.2f" % (
            vals.get("adenosine", 0.0), sep, vals.get("endocannabinoid", 0.0), sep, vals.get("histamine", 0.0)))
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
        self.integration_text.configure(text=("phasisch/tonisch, w = %.2f%s" % (tw, sep)) + sep.join(
            "%s %.2f/%.2f" % (NEURO_LABELS[k], integ.get(k + "_phasic", 0.0), vals.get(k, 0.0))
            for k in ("dopamine", "serotonin", "noradrenaline", "acetylcholine")))
        self.evidence_text.configure(text=str(integ.get("phase6a_evidence_state", "n/a")))
        self._update_sleep_panel(vals, regimes)
        emoji, name = compute_mood(vals, regimes)
        name = MOOD_DISPLAY.get(name, name)  # UI-only spelling; CSV keeps compute_mood()
        if self.mood_emoji is not None:
            self.mood_emoji.configure(text=emoji)
        if self.mood_name is not None:
            self.mood_name.configure(text=name)
        if getattr(self, "header_mood", None) is not None:
            self.header_mood.configure(text="%s  %s" % (emoji, name))
        self.neuro_bars.draw(vals)

    def _update_sleep_panel(self, vals, regimes):
        state = regimes.get("sleep_state", "n/a")
        pressure = int(round(100 * regimes.get("sleep_position", 0.0)))
        if state == "sleep":
            self.sleep_pill.configure(text="☾  Schlaf  ·  Druck %d %%" % pressure, style="PillSleep.TLabel")
        elif state == "wake":
            self.sleep_pill.configure(text="☀  Wach  ·  Druck %d %%" % pressure, style="PillWarn.TLabel")
        else:
            self.sleep_pill.configure(text="Zustand n/a", style="PillIdle.TLabel")
        ade = vals.get("adenosine", 0.0)
        upper = regimes.get("sleep_upper", 0.0); lower = regimes.get("sleep_lower", 0.0)
        self.sleep_gauge.set(ade, lower, upper, regimes.get("_asleep", False))
        self.sleep_values["pressure"].configure(text="%.3f   ·   Druck %d %%" % (ade, int(round(100 * regimes.get("sleep_position", 0.0)))))
        dwell = regimes.get("sleep_dwell", 0)
        self.sleep_values["dwell"].configure(text="%d %s" % (dwell, "Zyklus" if dwell == 1 else "Zyklen"))
        self.sleep_values["reason"].configure(text=str(regimes.get("sleep_reason", "n/a")))
        if getattr(self, "mood_detail", None) is not None:
            self.mood_detail.configure(text="%s   \u00b7   Schlafdruck %d %%" % (
                {"sleep": "Schlaf", "wake": "Wach"}.get(state, "n/a"), int(round(100 * regimes.get("sleep_position", 0.0)))))
        mat = 100.0 * regimes.get("maturity", 0.0)
        self.bar_maturity.configure(value=mat)
        self.maturity_label.configure(text="%.1f %%" % mat)

    def _chunk_rate(self, covered):
        """Reading speed while learning/importing, from the coverage history."""
        now = time.time()
        hist = getattr(self, "_rate_hist", None)
        if hist is None or not (self.auto_running or self.mode == "import"):
            self._rate_hist = [(now, covered)]
            return ""
        hist.append((now, covered))
        while len(hist) > 2 and now - hist[1][0] >= 300:
            hist.pop(0)
        dt = now - hist[0][0]
        if dt < 20:
            return ""
        return "   \u00b7   \u2248 %.0f Chunks/min" % (60.0 * (covered - hist[0][1]) / dt)

    def _mode_text(self):
        if getattr(self, "_closing", False):
            return "\u25cf  Wird beendet", "PillStop.TLabel"
        if self.mode == "import":
            return "\u25cf  Import l\u00e4uft", "PillWarn.TLabel"
        if self.auto_running:
            return "\u25cf  Autonomes Lernen l\u00e4uft", "PillInfo.TLabel"
        if getattr(self, "drift_running", False):
            return "\u25cf  Drift-Test l\u00e4uft", "PillSleep.TLabel"
        return "\u25cf  Bereit", "PillRun.TLabel"

    def _update_mode_pill(self):
        try:
            text, style = self._mode_text()
            self.mode_pill.configure(text=text, style=style)
            if getattr(self, "mode_pill_ctl", None) is not None:
                self.mode_pill_ctl.configure(text=text, style=style)
            if getattr(self, "abort_btn", None) is not None:
                busy = self.mode == "import" or self.auto_running
                self.abort_btn.configure(state=tk.NORMAL if busy else tk.DISABLED)
        except Exception:
            pass
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
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=3)
        f.rowconfigure(2, weight=0)
        top = _theme.card(f, "Sensorischer Entzug / Drift-Kalibrierung",
                          "Input AUS (keine neuen Chunks), innere Dynamik läuft weiter. Log als CSV im Projekt-Root. "
                          "Gezählt werden Systemzyklen.")
        top.grid(row=0, column=0, sticky="ew")
        ctl = ttk.Frame(top, style="Inner.TFrame")
        ctl.pack(fill=tk.X)
        self.drift_start_btn = ttk.Button(ctl, text="▶  Start", style="Accent.TButton", command=self.drift_start)
        self.drift_start_btn.pack(side=tk.LEFT)
        self.drift_stop_btn = ttk.Button(ctl, text="■  Stop", command=self.drift_stop_now, state=tk.DISABLED)
        self.drift_stop_btn.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Separator(ctl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=18)
        self.drift_limit_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctl, text="Zyklenzahl begrenzen", variable=self.drift_limit_on, style="Card.TCheckbutton",
                        command=self._drift_toggle_limit).pack(side=tk.LEFT, padx=(0, 8))
        self.drift_cycles = tk.IntVar(value=100)
        self.drift_spin = ttk.Spinbox(ctl, from_=1, to=9999, textvariable=self.drift_cycles, width=8, state=tk.DISABLED)
        self.drift_spin.pack(side=tk.LEFT)
        ttk.Label(ctl, text="Systemzyklen", style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(8, 0))
        st = ttk.Frame(top, style="Inner.TFrame"); st.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(st, text="STATUS", style="Caps.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        self.drift_status = ttk.Label(st, text="Bereit.", style="Card.TLabel")
        self.drift_status.pack(side=tk.LEFT)

        graph = _theme.card(f, "Verlauf", "Alle Größen auf 0 bis 1 normiert. Linienstil und Farbe unterscheiden die Kurven.")
        graph.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        legend = ttk.Frame(graph, style="Inner.TFrame"); legend.pack(fill=tk.X, pady=(0, 6))
        self.drift_legend_values = {}
        self._drift_swatches = []
        for key, label, color, dash in _theme.DRIFT_SERIES:
            item = ttk.Frame(legend, style="Inner.TFrame"); item.pack(side=tk.LEFT, padx=(0, 22))
            sw = tk.Canvas(item, width=28, height=12)
            self.theme.register(sw, "canvas", bg="surface")
            sw.pack(side=tk.LEFT, padx=(0, 6))
            self._drift_swatches.append((sw, color, dash))
            ttk.Label(item, text=label, style="Card.TLabel").pack(side=tk.LEFT)
            v = ttk.Label(item, text="", style="CardBold.TLabel")
            v.pack(side=tk.LEFT, padx=(6, 0))
            self.drift_legend_values[key] = v
        self.drift_canvas = tk.Canvas(graph, height=220)
        self.theme.register(self.drift_canvas, "canvas", bg="field")
        self.drift_canvas.pack(fill=tk.BOTH, expand=True)
        self.drift_canvas.bind("<Configure>", lambda e: self._drift_draw())
        self.theme.on_change(self._drift_draw)

        rep = _theme.card(f, "Bericht & Zyklusprotokoll")
        rep.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        box, self.drift_report = _theme.scrolled_text(self.theme, rep, font="mono", height=4)
        box.pack(fill=tk.BOTH, expand=True)
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
        # Read the Tk settings here, in the main thread; the worker thread must
        # not touch Tk variables.
        self._drift_cfg = (bool(self.drift_limit_on.get()), int(self.drift_cycles.get()))
        self.drift_running = True
        self.drift_stop = False
        self.drift_rows = []
        self.drift_start_btn.configure(state=tk.DISABLED)
        self.drift_stop_btn.configure(state=tk.NORMAL)
        self.drift_report.delete("1.0", tk.END)
        self._update_mode_pill()
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
        limit_on, limit_cycles = getattr(self, "_drift_cfg", (False, 100))
        cycles = limit_cycles if limit_on else None
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
        self.after(0, self._update_mode_pill)
    def _drift_draw(self):
        c = self.drift_canvas
        p = self.theme.p; fonts = self.theme.fonts
        for sw, color, dash in getattr(self, "_drift_swatches", []):
            sw.delete("all")
            _theme.dashed_line(sw, [2, 6, 26, 6], self.theme.series_color(color), 3, dash)
        c.delete("all")
        w = max(int(c.winfo_width()), 200); h = max(int(c.winfo_height()), 120)
        left, right, top, bottom = 48, 18, 22, 26
        pw = w - left - right; ph = h - top - bottom
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = top + ph - frac * ph
            c.create_line(left, y, left + pw, y, fill=p["grid"] if frac not in (0.0,) else p["border_strong"],
                          dash=(2, 4) if frac not in (0.0, 1.0) else None)
            c.create_text(left - 8, y, text="%.2f" % frac, anchor="e", fill=p["subtle"], font=fonts["small"])
        rows = self.drift_rows
        n = len(rows)
        c.create_text(left + pw, 2, text="Entzug-Zyklus (Systemzyklen) \u2192", anchor="ne", fill=p["subtle"], font=fonts["small"])
        if n < 2:
            c.create_text(left + pw / 2.0, top + ph / 2.0, fill=p["muted"], font=fonts["ui"],
                          text="Noch keine Daten. „Start“ beginnt einen Entzugslauf; die Kurven erscheinen ab dem 2. Zyklus.")
            for key, v in getattr(self, "drift_legend_values", {}).items():
                v.configure(text="")
            return
        step = next((st for st in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000) if n / float(st) <= 8), 10000)
        for cyc in [1] + list(range(step, n + 1, step)):
            x = left + pw * ((cyc - 1) / float(max(1, n - 1)))
            c.create_line(x, top + ph, x, top + ph + 4, fill=p["border_strong"])
            if abs(cyc - n) * pw / float(max(1, n - 1)) > 24 or cyc == n:
                c.create_text(x, top + ph + 6, text=str(cyc), anchor="n", fill=p["subtle"], font=fonts["small"])
        if (n - 1) % step:
            x = left + pw
            c.create_line(x, top + ph, x, top + ph + 4, fill=p["border_strong"])
            c.create_text(x, top + ph + 6, text=str(n), anchor="n", fill=p["text"], font=fonts["small"])
        maxpts = 200
        if n > maxpts:
            step = n / float(maxpts)
            idxs = [int(i * step) for i in range(maxpts)]
            if idxs[-1] != n - 1:
                idxs.append(n - 1)
        else:
            idxs = list(range(n))
        m = len(idxs)
        for key, label, color, dash in _theme.DRIFT_SERIES:
            pts = []
            v = 0.0
            for j, i in enumerate(idxs):
                v = rows[i].get(key, 0.0)
                try: v = float(v)
                except Exception: v = 0.0
                if v < 0.0: v = 0.0
                if v > 1.0: v = 1.0
                x = left + pw * (j / max(1, m - 1))
                y = top + ph - v * ph
                pts.extend((x, y))
            _theme.dashed_line(c, pts, self.theme.series_color(color), 2.5, dash)
            if key in getattr(self, "drift_legend_values", {}):
                self.drift_legend_values[key].configure(text="%.3f" % v)
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
            try:
                self.kpi["chunks"].configure(text="%d / %d" % (covered, total))
                for key in ("facts", "relations", "ontology", "questions"):
                    self.kpi[key].configure(text="%d" % st.get(key, 0))
                self.kpi["hypotheses"].configure(text="%d" % hypo)
                self.total_pct_label.configure(text="%.1f %%" % pct)
            except Exception:
                pass
            self._update_mode_pill()
            if self.mode != "import" and not getattr(self, "_closing", False):
                rate = self._chunk_rate(covered)
                self.status.configure(text="%s%s   \u00b7   Anzeige aktualisiert %s" % (
                    self._mode_text()[0].replace("\u25cf  ", ""), rate, datetime.now().strftime("%H:%M:%S")))
            try:
                self.bar_total.configure(value=pct)
            except Exception:
                pass
            if hasattr(self, "neuro_text"):
                try:
                    self._update_neuro_dashboard()
                except Exception as exc:
                    self.neuro_text.configure(text="Neuromodulatoren nicht verfuegbar: " + str(exc))
            if hasattr(self, "gui_logger_enabled"):
                self._logger_write_row_if_enabled()
                self._logger_pill()
            if hasattr(self, "docs") and self._current_tab_name == "Datenbank":
                rows = [(d["id"], d["title"], d["kind"], d["path"])
                        for d in self.mem.rows("SELECT * FROM documents ORDER BY created_at DESC LIMIT 2000")]
                self._fill_tree(self.docs, rows, self.docs_count, "Dokumente")
            if hasattr(self, "facts") and self._current_tab_name == "Fakten/Relationen":
                rows = [(f["subject"], f["relation"], f["value"], self._conf_cell(f["confidence"]))
                        for f in self.mem.rows("SELECT * FROM facts ORDER BY created_at DESC LIMIT 2000")]
                self._fill_tree(self.facts, rows, self.facts_count, "Fakten")
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
