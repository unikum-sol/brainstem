# -*- coding: utf-8 -*-
"""Shared visual theme for the BrainStem Tk GUIs (admin and read-only user GUI).

Pure Tkinter/ttk, no third-party packages. Provides two calm palettes
("dark" is the default for long monitoring sessions, "light" for bright
rooms), one font scale, ttk styles on top of the "clam" engine and helpers
that recolor classic tk widgets (Text, Canvas, Label) when the theme changes.
"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk


PALETTES = {
    "dark": {
        "bg": "#1b1e23", "header": "#16191d", "surface": "#23272e", "surface2": "#2c313a",
        "hover": "#353b45", "field": "#1d2126", "border": "#363c46", "border_strong": "#4a525e",
        "text": "#dce1e7", "muted": "#a9b3be", "subtle": "#97a1ac",
        "accent": "#6aa9e0", "accent_hover": "#82b8e6", "accent_fg": "#0f1720",
        "accent_soft": "#26384a", "selection": "#2e4a66",
        "success": "#86d494", "success_soft": "#1e3325",
        "warning": "#ddb05a", "warning_soft": "#3d3320",
        "danger": "#ec7a72", "danger_soft": "#3d2526", "danger_fg": "#f6b8b2",
        "sleep": "#a59cf0", "sleep_soft": "#2d2a48",
        "track": "#2f343d", "grid": "#30363f",
        "zebra": "#21252b", "disabled_border": "#59626e", "danger_btn": "#b4443d", "danger_btn_hover": "#c9524a", "danger_btn_fg": "#ffffff",
        "series": ("#f08a4b", "#f2c14e", "#a9b6ff", "#3cc9a0", "#e693c4"),
    },
    "light": {
        "bg": "#e8ebef", "header": "#dde2e8", "surface": "#f5f6f8", "surface2": "#e6e9ee",
        "hover": "#d9dee5", "field": "#fafbfc", "border": "#c9d0d8", "border_strong": "#aab3bd",
        "text": "#1e2731", "muted": "#4b5765", "subtle": "#5e6a77",
        "accent": "#245f9e", "accent_hover": "#1d5089", "accent_fg": "#ffffff",
        "accent_soft": "#d6e4f3", "selection": "#c7dbf0",
        "success": "#2b7a3a", "success_soft": "#d9eedd",
        "warning": "#8a5a00", "warning_soft": "#f5e8c8",
        "danger": "#b42318", "danger_soft": "#f8dedb", "danger_fg": "#8f1c13",
        "sleep": "#5a4fc0", "sleep_soft": "#e3e0f7",
        "track": "#dfe3e8", "grid": "#dde1e6",
        "zebra": "#edf0f3", "disabled_border": "#b2bac4", "danger_btn": "#b42318", "danger_btn_hover": "#9a1d14", "danger_btn_fg": "#ffffff",
        "series": ("#c0391b", "#b58300", "#0d4f8b", "#009e73", "#a8437f"),
    },
}

THEME_LABELS = {"dark": "Dunkel", "light": "Hell"}

# Muted, mutually distinguishable bar colors; legible on both palettes.
NEURO_PALETTE = {
    "dopamine": "#d9a72b", "serotonin": "#55b06a", "glutamate": "#e0803f",
    "gaba": "#4f93d6", "noradrenaline": "#9a83d4", "acetylcholine": "#3fb3bf",
    "adenosine": "#b0835f", "endocannabinoid": "#8d9aa8", "cortisol": "#e06464",
    "histamine": "#cf74b1", "orexin": "#e9a23b", "bdnf": "#38a98f",
}

# Okabe-Ito based, colorblind-safe series colors plus distinct dash patterns.
DRIFT_SERIES = [
    ("exploration_bias", "Explorationsneigung", 0, ()),
    ("adenosine", "Adenosin", 1, (14, 6)),
    ("plasticity_level", "Plastizität", 2, (2, 5)),
    ("effectiveness", "Effektivität", 3, (10, 4, 3, 4)),
    ("histamine", "Histamin", 4, (5, 4)),
]


def _family(preferred, fallback):
    try:
        fams = set(tkfont.families())
    except Exception:
        return fallback
    for name in preferred:
        if name in fams:
            return name
    return fallback


class Theme:
    """Owns fonts, the ttk style and a registry of classic tk widgets."""

    def __init__(self, root, name="dark"):
        self.root = root
        self.name = name if name in PALETTES else "dark"
        self.p = dict(PALETTES[self.name])
        ui = _family(["Segoe UI", "Helvetica Neue", "Arial"], "TkDefaultFont")
        semi = _family(["Segoe UI Semibold", "Segoe UI"], ui)
        mono = _family(["Cascadia Mono", "Consolas", "Courier New"], "TkFixedFont")
        self.fonts = {
            "ui": tkfont.Font(root=root, family=ui, size=10),
            "small": tkfont.Font(root=root, family=ui, size=10),
            "bold": tkfont.Font(root=root, family=semi, size=10),
            "title": tkfont.Font(root=root, family=semi, size=11),
            "h1": tkfont.Font(root=root, family=semi, size=14),
            "kpi": tkfont.Font(root=root, family=semi, size=13),
            "caps": tkfont.Font(root=root, family=semi, size=9),
            "mono": tkfont.Font(root=root, family=mono, size=10),
            "face": tkfont.Font(root=root, family=mono, size=20, weight="bold"),
        }
        self._widgets = []
        self._listeners = []
        self.style = ttk.Style(root)
        self.apply(self.name)

    def _paint_tab_lines(self):
        if not hasattr(self, "_tabline"):
            self._tabline = {k: tk.PhotoImage(master=self.root, width=4, height=3) for k in ("off", "on", "hover")}
        p = self.p
        for key, color in (("off", p["header"]), ("on", p["accent"]), ("hover", p["border_strong"])):
            self._tabline[key].put(color, to=(0, 0, 4, 3))

    def series_color(self, index):
        return self.p["series"][index]

    # check box images ---------------------------------------------------------
    def _paint_checks(self):
        if not hasattr(self, "_chk"):
            self._chk = {k: tk.PhotoImage(master=self.root, width=18, height=18)
                         for k in ("off", "on", "off_dis", "on_dis", "off_hover")}
        p = self.p
        spec = {"off": (p["border_strong"], p["field"], None), "off_hover": (p["accent"], p["field"], None),
                "on": (p["accent"], p["accent"], p["accent_fg"]), "off_dis": (p["border"], p["surface"], None),
                "on_dis": (p["border"], p["border"], p["subtle"])}
        for key, (border, fill, mark) in spec.items():
            img = self._chk[key]
            img.blank()
            img.put(border, to=(2, 1, 16, 17)); img.put(border, to=(1, 2, 17, 16))
            img.put(fill, to=(3, 2, 15, 16)); img.put(fill, to=(2, 3, 16, 15))
            if mark:
                for a, b in (((5, 9), (8, 12)), ((8, 12), (13, 6))):
                    steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
                    for i in range(steps + 1):
                        x = round(a[0] + (b[0] - a[0]) * i / float(steps))
                        y = round(a[1] + (b[1] - a[1]) * i / float(steps))
                        img.put(mark, to=(x, y, x + 2, y + 2))

    # registry -------------------------------------------------------------
    def register(self, widget, kind, **opts):
        self._widgets.append((widget, kind, opts))
        self._paint(widget, kind, opts)
        return widget

    def on_change(self, callback):
        self._listeners.append(callback)

    def color(self, key):
        return self.p.get(key, key)

    def _paint(self, widget, kind, opts):
        p = self.p
        try:
            if kind == "text":
                widget.configure(
                    bg=p["field"], fg=p["text"], insertbackground=p["text"],
                    selectbackground=p["selection"], selectforeground=p["text"],
                    inactiveselectbackground=p["selection"], relief=tk.FLAT, borderwidth=0,
                    highlightthickness=0, padx=12, pady=10, spacing1=1, spacing3=1,
                    font=self.fonts[opts.get("font", "ui")])
                for tag, color in (("err", "danger"), ("warn", "warning"), ("info", "subtle"),
                                   ("head", "accent"), ("ok", "success"), ("you", "accent"),
                                   ("bot", "success"), ("hint", "subtle")):
                    widget.tag_configure(tag, foreground=p[color])
                widget.tag_configure("head", font=self.fonts["bold"] if opts.get("font") != "mono" else self.fonts["mono"])
                widget.tag_configure("you", font=self.fonts["bold"])
                widget.tag_configure("bot", font=self.fonts["bold"])
                widget.tag_configure("wrapind", lmargin2=26)
                widget.tag_configure("answer", background=p["surface2"], lmargin1=14, lmargin2=14, rmargin=14,
                                     spacing1=4, spacing3=4)
                widget.tag_configure("hit_title", font=self.fonts["bold"], foreground=p["text"], spacing1=10)
                widget.tag_configure("hit_meta", font=self.fonts["small"], foreground=p["subtle"])
                widget.tag_configure("hit_body", lmargin1=0, spacing3=8)
                widget.tag_configure("mono", font=self.fonts["mono"])
                widget.tag_configure("link", foreground=p["accent"], underline=True)
                widget.tag_configure("sep", foreground=p["border_strong"])
                if getattr(widget, "_snap_fn", None) is not None:
                    widget._snap_fn()
            elif kind == "canvas":
                widget.configure(bg=p[opts.get("bg", "surface")], highlightthickness=0, borderwidth=0)
            elif kind == "label":
                widget.configure(bg=p[opts.get("bg", "surface")], fg=p[opts.get("fg", "text")])
            elif kind == "frame":
                widget.configure(bg=p[opts.get("bg", "surface")])
                if opts.get("border"):
                    widget.configure(highlightbackground=p[opts["border"]], highlightcolor=p[opts["border"]],
                                     highlightthickness=1)
        except tk.TclError:
            pass

    # style ----------------------------------------------------------------
    def apply(self, name):
        self.name = name if name in PALETTES else "dark"
        self.p = dict(PALETTES[self.name])
        p, f, s = self.p, self.fonts, self.style
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg=p["bg"])
        s.configure(".", background=p["bg"], foreground=p["text"], fieldbackground=p["field"],
                    bordercolor=p["border"], lightcolor=p["surface"], darkcolor=p["surface"],
                    troughcolor=p["track"], focuscolor=p["accent"], selectbackground=p["selection"],
                    selectforeground=p["text"], insertcolor=p["text"], arrowcolor=p["muted"],
                    font=f["ui"])
        s.map(".", foreground=[("disabled", p["subtle"])])
        # frames
        s.configure("TFrame", background=p["bg"])
        s.configure("Header.TFrame", background=p["header"])
        s.configure("Card.TFrame", background=p["surface"], bordercolor=p["border"],
                    lightcolor=p["border"], darkcolor=p["border"], relief="solid", borderwidth=1)
        s.configure("Inner.TFrame", background=p["surface"])
        s.configure("Tile.TFrame", background=p["surface2"], relief="flat", borderwidth=0)
        s.configure("Danger.Card.TFrame", background=p["surface"], bordercolor=p["danger"],
                    lightcolor=p["danger"], darkcolor=p["danger"], relief="solid", borderwidth=1)
        # labels
        s.configure("TLabel", background=p["bg"], foreground=p["text"])
        s.configure("Card.TLabel", background=p["surface"], foreground=p["text"])
        s.configure("CardMuted.TLabel", background=p["surface"], foreground=p["muted"])
        s.configure("CardSmall.TLabel", background=p["surface"], foreground=p["muted"], font=f["small"])
        s.configure("CardBold.TLabel", background=p["surface"], foreground=p["text"], font=f["bold"])
        s.configure("CardTitle.TLabel", background=p["surface"], foreground=p["text"], font=f["title"])
        s.configure("Caps.TLabel", background=p["surface"], foreground=p["muted"], font=f["caps"])
        s.configure("CapsBg.TLabel", background=p["bg"], foreground=p["muted"], font=f["caps"])
        s.configure("Danger.CardTitle.TLabel", background=p["surface"], foreground=p["danger"], font=f["title"])
        s.configure("Danger.Card.TLabel", background=p["surface"], foreground=p["danger_fg"])
        s.configure("TileValue.TLabel", background=p["surface2"], foreground=p["text"], font=f["kpi"])
        s.configure("TileLabel.TLabel", background=p["surface2"], foreground=p["muted"], font=f["small"])
        s.configure("H1.TLabel", background=p["header"], foreground=p["text"], font=f["h1"])
        s.configure("HeaderMuted.TLabel", background=p["header"], foreground=p["muted"])
        s.configure("HeaderMood.TLabel", background=p["header"], foreground=p["text"], font=f["bold"])
        for kind, fg in (("Idle", "muted"), ("Run", "success"), ("Stop", "danger"), ("Info", "accent")):
            s.configure("Status%s.TLabel" % kind, background=p["surface"], foreground=p[fg], font=f["bold"])
            s.configure("FootStatus%s.TLabel" % kind, background=p["header"], foreground=p[fg], font=f["bold"])
        s.configure("Footer.TFrame", background=p["header"])
        s.configure("FooterCaps.TLabel", background=p["header"], foreground=p["muted"], font=f["caps"])
        for kind, fg, bg in (("Idle", "muted", "surface2"), ("Run", "success", "success_soft"),
                             ("Info", "accent", "accent_soft"), ("Warn", "warning", "warning_soft"),
                             ("Stop", "danger", "danger_soft"), ("Sleep", "sleep", "sleep_soft")):
            s.configure("Pill%s.TLabel" % kind, background=p[bg], foreground=p[fg], font=f["bold"],
                        padding=(10, 3))
        # buttons
        s.configure("TButton", background=p["surface2"], foreground=p["text"], bordercolor=p["border_strong"],
                    lightcolor=p["surface2"], darkcolor=p["surface2"], focuscolor=p["accent"],
                    focusthickness=2, focussolid=1, padding=(14, 6), relief="flat")
        s.map("TButton",
              relief=[("disabled", "solid")],
              background=[("disabled", p["surface"]), ("pressed", p["border"]), ("active", p["hover"])],
              lightcolor=[("disabled", p["surface"]), ("focus", p["accent"]), ("active", p["hover"])],
              darkcolor=[("disabled", p["surface"]), ("focus", p["accent"]), ("active", p["hover"])],
              bordercolor=[("disabled", p["disabled_border"]), ("focus", p["accent"])],
              foreground=[("disabled", p["subtle"])])
        s.configure("Accent.TButton", background=p["accent"], foreground=p["accent_fg"], bordercolor=p["accent"],
                    lightcolor=p["accent"], darkcolor=p["accent"], font=f["bold"], focuscolor=p["accent_fg"])
        s.map("Accent.TButton",
              background=[("disabled", p["surface"]), ("pressed", p["accent_hover"]), ("active", p["accent_hover"])],
              lightcolor=[("disabled", p["surface"]), ("focus", p["text"]), ("active", p["accent_hover"])],
              darkcolor=[("disabled", p["surface"]), ("focus", p["text"]), ("active", p["accent_hover"])],
              bordercolor=[("disabled", p["border"]), ("focus", p["text"])],
              foreground=[("disabled", p["subtle"])])
        s.configure("Danger.TButton", background=p["danger_btn"], foreground=p["danger_btn_fg"], bordercolor=p["danger_btn"],
                    lightcolor=p["danger_btn"], darkcolor=p["danger_btn"], font=f["bold"], focuscolor=p["danger_btn_fg"])
        s.map("Danger.TButton",
              background=[("disabled", p["surface"]), ("active", p["danger_btn_hover"])],
              lightcolor=[("disabled", p["surface"]), ("active", p["danger_btn_hover"])],
              darkcolor=[("disabled", p["surface"]), ("active", p["danger_btn_hover"])],
              foreground=[("disabled", p["subtle"])],
              bordercolor=[("disabled", p["border"]), ("focus", p["text"])])
        s.configure("Small.TButton", padding=(8, 4))
        s.configure("Link.TButton", background=p["surface"], foreground=p["accent"], bordercolor=p["border_strong"],
                    lightcolor=p["surface"], darkcolor=p["surface"], padding=(10, 3), relief="solid")
        s.map("Link.TButton", background=[("active", p["surface"])], foreground=[("active", p["accent_hover"])],
              lightcolor=[("active", p["surface"])], darkcolor=[("active", p["surface"])],
              bordercolor=[("focus", p["accent"])])
        s.configure("Header.TButton", background=p["header"], foreground=p["muted"], bordercolor=p["border"],
                    lightcolor=p["header"], darkcolor=p["header"], padding=(10, 4))
        s.map("Header.TButton", background=[("active", p["hover"])], foreground=[("active", p["text"])],
              lightcolor=[("active", p["hover"])], darkcolor=[("active", p["hover"])])
        # notebook
        self._paint_tab_lines()
        if not getattr(self, "_tab_element", False):
            try:
                s.element_create("BS.Tab.underline", "image", self._tabline["off"],
                                 ("selected", self._tabline["on"]), ("active", self._tabline["hover"]),
                                 border=0, sticky="ew")
                s.layout("TNotebook.Tab", [("Notebook.tab", {"sticky": "nswe", "children": [
                    ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                        ("Notebook.focus", {"side": "top", "sticky": "", "children": [
                            ("Notebook.label", {"side": "top", "sticky": ""})]})]}),
                    ("BS.Tab.underline", {"side": "bottom", "sticky": "ew"})]})])
                self._tab_element = True
            except tk.TclError:
                self._tab_element = False
        s.configure("TNotebook", background=p["header"], borderwidth=0, tabmargins=(14, 4, 14, 0),
                    bordercolor=p["border"], lightcolor=p["header"], darkcolor=p["header"])
        s.configure("TNotebook.Tab", background=p["header"], foreground=p["muted"], padding=(16, 8, 16, 6),
                    bordercolor=p["header"], lightcolor=p["header"], darkcolor=p["header"], focuscolor=p["header"],
                    borderwidth=0, font=f["ui"], focusthickness=1)
        s.map("TNotebook.Tab",
              background=[("selected", p["header"]), ("active", p["header"])],
              foreground=[("selected", p["text"]), ("active", p["text"])],
              lightcolor=[("selected", p["header"])], bordercolor=[("selected", p["header"])],
              expand=[("selected", (0, 0, 0, 0))], padding=[("selected", (16, 8, 16, 6))],
              focuscolor=[("focus", p["accent"])])
        s.configure("Seg.TButton", background=p["surface2"], foreground=p["text"], bordercolor=p["border_strong"],
                    lightcolor=p["surface2"], darkcolor=p["surface2"], padding=(12, 4), focusthickness=1, focussolid=1)
        s.map("Seg.TButton", background=[("active", p["hover"])], foreground=[("active", p["text"])],
              lightcolor=[("active", p["hover"])], darkcolor=[("active", p["hover"])],
              bordercolor=[("focus", p["accent"])])
        s.configure("SegOn.TButton", background=p["accent"], foreground=p["accent_fg"], bordercolor=p["accent"],
                    lightcolor=p["accent"], darkcolor=p["accent"], padding=(12, 4), font=f["bold"],
                    focusthickness=1)
        s.map("SegOn.TButton", background=[("active", p["accent_hover"])], lightcolor=[("active", p["accent_hover"])],
              darkcolor=[("active", p["accent_hover"])], bordercolor=[("focus", p["text"])])
        # inputs
        for w in ("TEntry", "TCombobox", "TSpinbox"):
            s.configure(w, fieldbackground=p["field"], foreground=p["text"], background=p["surface2"],
                        bordercolor=p["border_strong"], lightcolor=p["field"], darkcolor=p["field"],
                        arrowcolor=p["muted"], insertcolor=p["text"], padding=(8, 5))
            s.map(w, bordercolor=[("focus", p["accent"])], lightcolor=[("focus", p["accent"])],
                  darkcolor=[("focus", p["accent"])],
                  fieldbackground=[("readonly", p["field"]), ("disabled", p["surface"])],
                  foreground=[("disabled", p["subtle"])], arrowcolor=[("disabled", p["border_strong"])])
        s.map("TCombobox", selectbackground=[("readonly", p["field"])], selectforeground=[("readonly", p["text"])])
        s.configure("TSpinbox", arrowsize=13, background=p["surface2"], bordercolor=p["border_strong"],
                    lightcolor=p["field"], darkcolor=p["field"])
        s.map("TSpinbox", background=[("active", p["hover"]), ("disabled", p["surface"])],
              arrowcolor=[("active", p["text"]), ("disabled", p["border_strong"])],
              bordercolor=[("focus", p["accent"])], lightcolor=[("focus", p["accent"])],
              darkcolor=[("focus", p["accent"])],
              fieldbackground=[("disabled", p["surface"])], foreground=[("disabled", p["subtle"])])
        self.root.option_add("*TCombobox*Listbox.background", p["field"])
        self.root.option_add("*TCombobox*Listbox.foreground", p["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", p["selection"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", p["text"])
        self.root.option_add("*TCombobox*Listbox.font", f["ui"])
        # check buttons: image indicator (clear check mark, themed, crisp)
        self._paint_checks()
        if not getattr(self, "_check_element", False):
            try:
                s.element_create("BS.Checkbutton.indicator", "image", self._chk["off"],
                                 ("disabled", "selected", self._chk["on_dis"]), ("disabled", self._chk["off_dis"]),
                                 ("selected", self._chk["on"]), ("active", self._chk["off_hover"]),
                                 border=0, sticky="", padding=(0, 0, 6, 0))
                s.layout("TCheckbutton", [("Checkbutton.padding", {"sticky": "nswe", "children": [
                    ("BS.Checkbutton.indicator", {"side": "left", "sticky": ""}),
                    ("Checkbutton.focus", {"side": "left", "sticky": "w", "children": [
                        ("Checkbutton.label", {"sticky": "nswe"})]})]})])
                self._check_element = True
            except tk.TclError:
                self._check_element = False
        for st, bg in (("TRadiobutton", "bg"), ("Card.TRadiobutton", "surface")):
            s.configure(st, background=p[bg], foreground=p["text"], indicatorbackground=p["field"],
                        indicatorforeground=p["accent"], focuscolor=p["accent"],
                        upperbordercolor=p["border_strong"], lowerbordercolor=p["border_strong"])
            s.map(st, background=[("active", p[bg])], indicatorbackground=[("active", p["hover"])])
        for st, bg in (("TCheckbutton", "bg"), ("Card.TCheckbutton", "surface")):
            s.configure(st, background=p[bg], foreground=p["text"], indicatorbackground=p["field"],
                        indicatorforeground=p["accent"], indicatorrelief="flat", focuscolor=p["accent"],
                        upperbordercolor=p["border_strong"], lowerbordercolor=p["border_strong"])
            s.map(st, background=[("active", p[bg])],
                  indicatorbackground=[("selected", p["field"]), ("active", p["hover"])],
                  foreground=[("disabled", p["subtle"])])
        # progress bars
        s.configure("Horizontal.TProgressbar", troughcolor=p["track"], background=p["accent"],
                    bordercolor=p["track"], lightcolor=p["accent"], darkcolor=p["accent"], thickness=10)
        s.configure("Success.Horizontal.TProgressbar", troughcolor=p["track"], background=p["success"],
                    bordercolor=p["track"], lightcolor=p["success"], darkcolor=p["success"], thickness=10)
        s.configure("Sleep.Horizontal.TProgressbar", troughcolor=p["track"], background=p["sleep"],
                    bordercolor=p["track"], lightcolor=p["sleep"], darkcolor=p["sleep"], thickness=8)
        # tables
        s.configure("Treeview", indent=0, background=p["field"], fieldbackground=p["field"], foreground=p["text"],
                    bordercolor=p["border"], lightcolor=p["field"], darkcolor=p["field"], rowheight=26,
                    borderwidth=0)
        s.map("Treeview", background=[("selected", p["selection"])], foreground=[("selected", p["text"])])
        s.configure("Treeview.Heading", background=p["surface2"], foreground=p["muted"], font=f["bold"],
                    bordercolor=p["border"], lightcolor=p["surface2"], darkcolor=p["surface2"],
                    relief="flat", padding=(8, 6))
        s.map("Treeview.Heading", background=[("active", p["hover"])], foreground=[("active", p["text"])])
        # scrollbars, separators
        for st in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            s.configure(st, troughcolor=p["field"], background=p["surface2"], bordercolor=p["field"],
                        lightcolor=p["surface2"], darkcolor=p["surface2"], arrowcolor=p["muted"],
                        gripcount=0, arrowsize=12)
            s.map(st, background=[("active", p["hover"])])
        s.configure("TSeparator", background=p["border"])
        s.configure("Card.TSeparator", background=p["border"])
        for widget, kind, opts in list(self._widgets):
            self._paint(widget, kind, opts)
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                pass


def dashed_line(canvas, pts, color, width, pattern):
    """Draw a polyline with an explicit dash pattern. Tk on Windows renders
    custom dash patterns on thick lines as dots, so dashes are emitted as
    separate solid segments along the path."""
    if not pattern:
        if len(pts) >= 4:
            canvas.create_line(*pts, fill=color, width=width, capstyle=tk.ROUND, joinstyle=tk.ROUND)
        return
    import math
    pat = list(pattern)
    idx, left, on = 0, float(pat[0]), True
    seg = [pts[0], pts[1]]
    for k in range(2, len(pts), 2):
        x0, y0, x1, y1 = pts[k - 2], pts[k - 1], pts[k], pts[k + 1]
        d = math.hypot(x1 - x0, y1 - y0)
        pos = 0.0
        while d - pos > 1e-9:
            step = min(left, d - pos)
            pos += step
            left -= step
            fx = x0 + (x1 - x0) * pos / d; fy = y0 + (y1 - y0) * pos / d
            if on:
                seg.extend((fx, fy))
            if left <= 1e-9:
                if on and len(seg) >= 4:
                    canvas.create_line(*seg, fill=color, width=width, capstyle=tk.ROUND)
                on = not on
                idx = (idx + 1) % len(pat)
                left = float(pat[idx])
                seg = [fx, fy]
    if on and len(seg) >= 4:
        canvas.create_line(*seg, fill=color, width=width, capstyle=tk.ROUND)


def app_header(root, theme, subtitle, on_choose):
    """Shared top bar: title, subtitle and the Dunkel|Hell segmented switch.
    Returns (bar, update_fn); callers pack further items with side=RIGHT."""
    bar = ttk.Frame(root, style="Header.TFrame", padding=(18, 10, 14, 10))
    bar.pack(fill=tk.X)
    ttk.Label(bar, text="BrainStem V8", style="H1.TLabel").pack(side=tk.LEFT)
    ttk.Label(bar, text=subtitle, style="HeaderMuted.TLabel").pack(side=tk.LEFT, padx=(12, 0), pady=(4, 0))
    seg = ttk.Frame(bar, style="Header.TFrame")
    seg.pack(side=tk.RIGHT, padx=(14, 0))
    ttk.Label(seg, text="Farbschema", style="HeaderMuted.TLabel").pack(side=tk.LEFT, padx=(0, 8))
    buttons = {}
    for key in ("dark", "light"):
        b = ttk.Button(seg, text=THEME_LABELS[key], style="Seg.TButton", width=8, command=lambda k=key: on_choose(k))
        b.pack(side=tk.LEFT, padx=(0, 2))
        buttons[key] = b
    def update():
        for key, b in buttons.items():
            b.configure(style="SegOn.TButton" if key == theme.name else "Seg.TButton")
    update()
    return bar, buttons, update


def render_hits(widget, hits, query, limit=300):
    """Shared search result renderer: count line, numbered titles, a meta line
    and a ~300 character snippet. "Volltext anzeigen" sits at the end of the
    meta line (it never wraps alone) and expands the snippet to the full
    (max. 1000 character) text."""
    widget.insert(tk.END, "%d Treffer für „%s“\n" % (len(hits), query), "hit_meta")
    for i, h in enumerate(hits, 1):
        widget.insert(tk.END, "%d.  %s\n" % (i, h.title), "hit_title")
        widget.insert(tk.END, "Score %.3f   ·   Methode %s   ·   Chunk %s" % (h.score, h.method, h.chunk_id), "hit_meta")
        full = h.text[:1000]
        if len(full) > limit + 20:
            tag = "snip%d" % i; link = "more%d" % i
            widget.insert(tk.END, "   ·   ", "hit_meta")
            widget.insert(tk.END, "Volltext anzeigen", ("hit_meta", link, "link"))
            widget.insert(tk.END, "\n", "hit_meta")
            widget.insert(tk.END, full[:limit].rsplit(" ", 1)[0] + " …\n", ("hit_body", tag))
            def _expand(event, t=tag, txt=full, lk=link):
                lr = widget.tag_ranges(lk)
                if lr:
                    widget.tag_remove("link", lr[0], lr[-1])
                    widget.tag_unbind(lk, "<Button-1>")
                rng = widget.tag_ranges(t)
                if rng:
                    widget.delete(rng[0], rng[-1])
                    widget.insert(rng[0], txt + "\n", "hit_body")
                widget.configure(cursor="")
            widget.tag_bind(link, "<Button-1>", _expand)
            widget.tag_bind(link, "<Enter>", lambda e: widget.configure(cursor="hand2"))
            widget.tag_bind(link, "<Leave>", lambda e: widget.configure(cursor=""))
        else:
            widget.insert(tk.END, "\n", "hit_meta")
            widget.insert(tk.END, full + "\n", "hit_body")
    if not hits:
        widget.insert(tk.END, "Keine Treffer. Anderen Begriff versuchen.", "hint")


def snap_lines(text_widget, base_pad=10):
    """Keep only whole lines visible: pad the Text so its inner height is a
    multiple of the line height (no half-cut first line when scrolled to end)."""
    def _on(event=None):
        try:
            height = event.height if event is not None else text_widget.winfo_height()
            font = tkfont.Font(font=text_widget.cget("font"))
            lh = font.metrics("linespace") + int(text_widget.cget("spacing1")) + int(text_widget.cget("spacing3"))
            avail = height - 2 * base_pad
            rem = avail % lh if lh > 0 else 0
            text_widget.configure(pady=base_pad + rem // 2)
        except Exception:
            pass
    text_widget.bind("<Configure>", _on, add="+")
    text_widget._snap_fn = _on


def scrolled_text(theme, parent, font="ui", height=10, wrap=tk.WORD):
    """Text widget with a themed vertical scrollbar inside a bordered frame.
    Returns (container_frame, text_widget)."""
    box = tk.Frame(parent)
    theme.register(box, "frame", bg="field", border="border")
    text = tk.Text(box, wrap=wrap, height=height)
    theme.register(text, "text", font=font)
    sb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=sb.set)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    return box, text


def card(parent, title=None, subtitle=None, style="Card.TFrame", title_style="CardTitle.TLabel", padding=(16, 10, 16, 12)):
    """A bordered surface with an optional title row. The title row is
    exposed as `frame.header` (pack extra widgets with side=RIGHT)."""
    frame = ttk.Frame(parent, style=style, padding=padding)
    frame.header = None
    if title:
        head = ttk.Frame(frame, style="Inner.TFrame")
        head.pack(fill=tk.X, pady=(0, 2 if subtitle else 6))
        ttk.Label(head, text=title, style=title_style).pack(side=tk.LEFT)
        frame.header = head
        if subtitle:
            ttk.Label(frame, text=subtitle, style="CardSmall.TLabel").pack(anchor=tk.W, pady=(0, 8))
    return frame
