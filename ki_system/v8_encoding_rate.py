# -*- coding: utf-8 -*-
"""Effective learning rate: how strongly experience is encoded in wake and
consolidated in sleep (advisory councils of 17 November 2026, pre-registered
in Audits/Lernrate_Wirksam_Vorabregistrierung_2026-11-17.md).

Wake encoding rate eta. Whether a single re-observation leaves a trace is
probabilistic (subsequent-memory effects: Brewer et al. 1998; Wagner et al.
1998), and single synapses potentiate all-or-none (Petersen et al. 1998), so
a re-observation adds one unit of evidence with probability eta. The rate
is set by a neuromodulator: phasic noradrenaline from the locus coeruleus
signals unexpected uncertainty and raises the learning rate (Yu & Dayan
2005; Nassar et al. 2012; Aston-Jones & Cohen 2005), as associability rises
after surprise (Pearce & Hall 1980) and the learning rate at change points
(Nassar et al. 2010; Behrens et al. 2007). Adenosine lowers it when
long wake has saturated the synapses; it falls when long wake has saturated the synapses (Vyazovskiy et al.
2008; Yoo et al. 2007); sleep restores it through the adenosine decay
(Tononi & Cirelli 2014). The first observation of an item always counts
(one-shot episodic encoding), and the character-transition statistics of
Phase 0 always run at full rate (Saffran et al. 1996).

    n     = phasic noradrenaline of the previous cycle (Phase 6a; it contains
            the unsigned prediction error with weight 0.30)
    A    <- A + 0.3 (n - A)                       fast trace (wake only)
    Abar <- Abar + 0.02 (n - Abar)                slow reference (wake only)
    p     = tanh((A - Abar) / 0.045)              phasic deviation, -1 .. 1
    S     = max(0, (adenosine - a_on) / (1 - a_on))   saturation, a_on = 0.594
    eta_raw = 1 + 0.3 max(p,0) - 0.3 S (1 - max(p,0)) - 0.1 max(-p,0)
    eta   = clamp(eta_raw, 0.05, 1)

Sleep consolidation gain g, frozen at sleep onset: slow-wave consolidation
scales with prior wake load (Huber et al. 2004) and with salience tags
(Redondo & Morris 2011):

    g = clamp(1 + 0.5 (ad_on - Adbar) + 0.1 p_on, 0.85, 1.15)

Phase 7d lowers the survival threshold of non-anchor items by 0.5 (g - 1).

Everything is computed at the start of a cycle from the persisted state of
the previous cycle, so it is identical after a restart. The draws come from
learning_clock.uniform and do not depend on iteration order. With mode
'fixed' (eta = 1, g = 1) learning is exactly as before this module.
"""
import math

from ki_system import learning_clock

STATE = "encoding_rate_state"
LOG = "encoding_rate_cycles"
DEFAULTS = {"mode": "adaptive", "a_on": "0.594", "alpha_fast": "0.3", "alpha_slow": "0.02",
            "surprise_scale": "0.045", "boost": "0.3", "saturation_drop": "0.3", "calm_drop": "0.1",
            "eta_min": "0.05", "sleep_gain_load": "0.5", "sleep_gain_surprise": "0.1",
            "sleep_gain_min": "0.85", "sleep_gain_max": "1.15", "sleep_ref_rate": "0.1"}

_current = {"cycle": None, "eta": 1.0, "g": 1.0, "seen": {}, "encoded": 0, "skipped": 0}
_PREV_CYCLE = None


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _kv(con, table):
    try:
        return dict(con.execute("SELECT key,value FROM " + table).fetchall())
    except Exception:
        return {}


def ensure_schema(con):
    con.execute("CREATE TABLE IF NOT EXISTS " + STATE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)")
    con.execute("CREATE TABLE IF NOT EXISTS " + LOG + " (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER, "
                "cycle_index INTEGER, state TEXT, noradrenaline REAL, adenosine REAL, a_fast REAL, a_slow REAL, "
                "phasic REAL, saturation REAL, eta_raw REAL, eta REAL, sleep_gain REAL, plasticity_tonic REAL, "
                "encoded_prev INTEGER, skipped_prev INTEGER)")
    for k, v in DEFAULTS.items():
        con.execute("INSERT OR IGNORE INTO " + STATE + "(key,value,updated_at) VALUES(?,?,?)",
                    (k, v, learning_clock.now()))


def _set(con, key, value):
    con.execute("INSERT INTO " + STATE + "(key,value,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, str(value), learning_clock.now()))


def begin_cycle(con):
    """Compute eta and g for the cycle that starts now."""
    ensure_schema(con)
    st = _kv(con, STATE)
    p = {k: _f(st.get(k), _f(v)) for k, v in DEFAULTS.items() if k != "mode"}
    mode = st.get("mode", "adaptive")
    meta = _kv(con, "phase6a_meta_plasticity_state")
    ad_state = _kv(con, "phase7a_adenosine_state")
    sw = _kv(con, "cooperative_sleep_wake_state")
    state = sw.get("state", "wake") or "wake"
    nm_state = _kv(con, "phase6a_neuromodulated_sleep_state")
    s = _f(nm_state.get("noradrenaline_phasic"), _f(nm_state.get("noradrenaline"), 0.5))
    adenosine = _f(ad_state.get("adenosine_level"), 0.0)
    a_fast = _f(st.get("a_fast"), s) if "a_fast" in st else s
    a_slow = _f(st.get("a_slow"), s) if "a_slow" in st else s
    if state != "sleep":
        a_fast += p["alpha_fast"] * (s - a_fast)
        a_slow += p["alpha_slow"] * (s - a_slow)
    phasic = math.tanh((a_fast - a_slow) / p["surprise_scale"])
    saturation = max(0.0, (adenosine - p["a_on"]) / (1.0 - p["a_on"]))
    up = max(phasic, 0.0)
    eta_raw = 1.0 + p["boost"] * up - p["saturation_drop"] * saturation * (1.0 - up) - p["calm_drop"] * max(-phasic, 0.0)
    eta = _clamp(eta_raw, p["eta_min"], 1.0)
    g = _f(st.get("sleep_gain"), 1.0)
    if state == "sleep" and st.get("last_state", "wake") != "sleep":
        ad_ref = _f(st.get("ad_ref"), adenosine) if "ad_ref" in st else adenosine
        g = _clamp(1.0 + p["sleep_gain_load"] * (adenosine - ad_ref) + p["sleep_gain_surprise"] * phasic,
                   p["sleep_gain_min"], p["sleep_gain_max"])
        ad_ref += p["sleep_ref_rate"] * (adenosine - ad_ref)
        _set(con, "ad_ref", round(ad_ref, 6))
        _set(con, "sleep_gain", round(g, 6))
    if mode == "fixed":
        eta, g = 1.0, 1.0
    for k, v in (("a_fast", a_fast), ("a_slow", a_slow), ("phasic", phasic), ("saturation", saturation),
                 ("eta_raw", eta_raw), ("eta", eta), ("last_state", state)):
        _set(con, k, round(v, 6) if isinstance(v, float) else v)
    con.execute("INSERT INTO " + LOG + "(created_at,cycle_index,state,noradrenaline,adenosine,a_fast,a_slow,phasic,"
                "saturation,eta_raw,eta,sleep_gain,plasticity_tonic,encoded_prev,skipped_prev) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (learning_clock.now(), learning_clock.cycle(), state, round(s, 6), round(adenosine, 6),
                 round(a_fast, 6), round(a_slow, 6), round(phasic, 6), round(saturation, 6), round(eta_raw, 6),
                 round(eta, 6), round(g, 6), round(_f(meta.get("last_plasticity_level"), 0.0), 6),
                 _current["encoded"], _current["skipped"]))
    _current.update({"cycle": learning_clock.cycle(), "eta": eta, "g": g if state == "sleep" else 1.0,
                     "seen": {}, "encoded": 0, "skipped": 0})


def _ensure_current(con=None):
    if _current["cycle"] != learning_clock.cycle() and con is not None:
        begin_cycle(con)


def increment(site, key, con=None):
    """Evidence added by one re-observation: 1 with probability eta, else 0."""
    _ensure_current(con)
    eta = _current["eta"]
    if eta >= 1.0:
        _current["encoded"] += 1
        return 1
    seen = _current["seen"]
    n = seen.get((site, key), 0)
    seen[(site, key)] = n + 1
    if learning_clock.uniform("encode:" + site, "%s|%d" % (key, n)) < eta:
        _current["encoded"] += 1
        return 1
    _current["skipped"] += 1
    return 0


def sleep_gain():
    return _current["g"]


def managed_cycle(self, *args, **kwargs):
    con = getattr(getattr(self, "memory", None), "db", None)
    if con is not None:
        begin_cycle(con)
    return _PREV_CYCLE(self, *args, **kwargs)


def managed_run(self, cycles=1, progress=None):
    return {"phase": "encoding_rate", "results": [self.cycle(progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.encoding_rate = True
    return AutonomousLoop
