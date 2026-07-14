# -*- coding: utf-8 -*-
"V8 Phase 7e - Histamine / wake-arousal (neurotransmitter #10, reciprocal antagonist to adenosine)."
from __future__ import annotations
import os, sqlite3, time
from pathlib import Path

PHASE = "phase7e_histamine_wake_arousal_release"
PHASE_VERSION = "phase7e_v1"
NEUROTRANSMITTER = "histamine"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7e_histamine_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7e_histamine_cycles": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("histamine_level","REAL"),("histamine_target","REAL"),("adenosine_level","REAL"),
        ("wake_activity","REAL"),("wake_drive","REAL"),("sleep_pressure","REAL"),
        ("reciprocal_gate","REAL"),("regime","TEXT"),("note","TEXT")],
}
SCHEMA_INDEXES = [("idx_phase7e_cycles_cyc","phase7e_histamine_cycles","cycle_index")]

HISTAMINE_PARAMS = {
    "histamine_level": 0.5, "histamine_baseline": 0.5, "ewma_alpha": 0.3,
    "adenosine_coupling": 0.6, "wake_activity_gain": 0.4,
    "sleep_gate_low": 0.35, "wake_gate_high": 0.65, "cycle_count": 0,
}

def _now(): return int(time.time())
def _clamp(x, lo=0.0, hi=1.0):
    try: x = float(x)
    except Exception: x = 0.0
    if x < lo: return lo
    if x > hi: return hi
    return x
def _to_float(x, d=0.0):
    try: return float(x)
    except Exception: return d
def _to_int(x, d=0):
    try: return int(x)
    except Exception: return d
def _table_exists(con, t): return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def _index_exists(con, i): return con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (i,)).fetchone() is not None
def _columns(con, t):
    if not _table_exists(con, t): return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + t + ")").fetchall()]

def resolve_db(obj=None):
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            cand = Path(__file__).resolve().parent.parent / "ki_memory.sqlite3"
            if cand.exists(): path = str(cand)
        con = sqlite3.connect(path, timeout=30.0); con.row_factory = sqlite3.Row; return con
    if isinstance(obj, sqlite3.Connection):
        obj.row_factory = sqlite3.Row; return obj
    for a in ("db", "connection", "conn", "memory"):
        inner = getattr(obj, a, None)
        if isinstance(inner, sqlite3.Connection):
            inner.row_factory = sqlite3.Row; return inner
    return resolve_db(None)

def ensure_schema(con):
    rep = {"created_tables": [], "added_columns": [], "created_indexes": []}
    for t, cols in SCHEMA_TABLES.items():
        if not _table_exists(con, t):
            con.execute("CREATE TABLE " + t + " (" + ", ".join(n + " " + s for n, s in cols) + ")")
            rep["created_tables"].append(t)
        else:
            ex = set(_columns(con, t))
            for n, s in cols:
                if n in ex: continue
                su = s.upper()
                if "PRIMARY KEY" in su or "AUTOINCREMENT" in su: continue
                con.execute("ALTER TABLE " + t + " ADD COLUMN " + n + " " + s); rep["added_columns"].append(t + "." + n)
    for i, t, c in SCHEMA_INDEXES:
        if not _index_exists(con, i):
            con.execute("CREATE INDEX " + i + " ON " + t + "(" + c + ")"); rep["created_indexes"].append(i)
    con.commit(); return rep

def _self_check_schema(con):
    m = []
    for t, cols in SCHEMA_TABLES.items():
        ex = set(_columns(con, t))
        for n, _s in cols:
            if n not in ex: m.append(t + "." + n)
    return m

def _kv_set(con, table, key, value):
    if not _table_exists(con, table): return
    tc = set(_columns(con, table))
    if "key" not in tc or "value" not in tc: return
    v = ("true" if value else "false") if isinstance(value, bool) else str(value)
    con.execute("INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (key, v, _now()))

def _read_kv(con, table):
    if not _table_exists(con, table): return {}
    tc = set(_columns(con, table))
    if "key" not in tc or "value" not in tc: return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())

def initialize_histamine_parameters(con):
    ensure_schema(con); ins = []
    for k, v in HISTAMINE_PARAMS.items():
        if con.execute("SELECT value FROM phase7e_histamine_state WHERE key=?", (k,)).fetchone() is None:
            _kv_set(con, "phase7e_histamine_state", k, v); ins.append(k)
    con.commit(); return {"inserted": ins, "total": len(HISTAMINE_PARAMS)}

def _get_p(con, key, d=0.0):
    return _to_float(_read_kv(con, "phase7e_histamine_state").get(key), d)
def _set_p(con, key, val): _kv_set(con, "phase7e_histamine_state", key, val)

def _get_adenosine(con):
    if not _table_exists(con, "phase7a_adenosine_state"): return 0.5
    r = con.execute("SELECT value FROM phase7a_adenosine_state WHERE key='adenosine_level'").fetchone()
    return _clamp(_to_float(r[0], 0.5)) if r else 0.5

def _get_wake_activity(con):
    if not _table_exists(con, "phase7a_adenosine_state"): return 0.5
    r = con.execute("SELECT value FROM phase7a_adenosine_state WHERE key='wake_activity'").fetchone()
    return _clamp(_to_float(r[0], 0.5)) if r else 0.5

def _read_neuromod(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    return {k: _clamp(_to_float(st.get(k), d)) for k, d in [("glutamate", 0.5), ("gaba", 0.5)]}

def run_phase7e_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj); ensure_schema(con)
    missing = _self_check_schema(con)
    if missing: return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_histamine_parameters(con)
    if cycle_index is None:
        cycle_index = _to_int(_get_p(con, "cycle_count", 0)) + 1
    ade = _get_adenosine(con); wake = _get_wake_activity(con)
    w_ade = _get_p(con, "adenosine_coupling", 0.6); w_wake = _get_p(con, "wake_activity_gain", 0.4)
    s = w_ade + w_wake
    if s <= 0: w_ade, w_wake, s = 0.5, 0.5, 1.0
    histamine_target = _clamp((w_ade / s) * (1.0 - ade) + (w_wake / s) * wake)
    alpha = _get_p(con, "ewma_alpha", 0.3); prev = _get_p(con, "histamine_level", 0.5)
    histamine_level = _clamp((1 - alpha) * prev + alpha * histamine_target)
    wake_drive = histamine_level; sleep_pressure = ade
    reciprocal_gate = _clamp(histamine_level - ade + 0.5)
    wake_hi = _get_p(con, "wake_gate_high", 0.65); sleep_lo = _get_p(con, "sleep_gate_low", 0.35)
    if histamine_level >= wake_hi and histamine_level > ade:
        regime = "wake_active"
    elif histamine_level <= sleep_lo and ade > histamine_level:
        regime = "sleep_permissive"
    else:
        regime = "transition"
    if _table_exists(con, "phase6a_neuromodulated_sleep_state"):
        _kv_set(con, "phase6a_neuromodulated_sleep_state", "histamine", round(histamine_level, 4))
    now = _now()
    con.execute("INSERT INTO phase7e_histamine_cycles(created_at,cycle_index,histamine_level,histamine_target,adenosine_level,wake_activity,wake_drive,sleep_pressure,reciprocal_gate,regime,note) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (now, int(cycle_index), float(histamine_level), float(histamine_target), float(ade), float(wake),
                 float(wake_drive), float(sleep_pressure), float(reciprocal_gate), regime, "reciprocal_adenosine_wake_switch"))
    _set_p(con, "histamine_level", histamine_level); _set_p(con, "cycle_count", cycle_index)
    _set_p(con, "last_regime", regime); _set_p(con, "last_reciprocal_gate", reciprocal_gate)
    _set_p(con, "last_adenosine", ade)
    con.commit()
    return {"phase": PHASE, "phase_version": PHASE_VERSION, "neurotransmitter": NEUROTRANSMITTER,
            "cycle_index": cycle_index, "histamine_level": round(histamine_level, 4),
            "histamine_target": round(histamine_target, 4), "adenosine_level": round(ade, 4),
            "wake_activity": round(wake, 4), "wake_drive": round(wake_drive, 4),
            "sleep_pressure": round(sleep_pressure, 4), "reciprocal_gate": round(reciprocal_gate, 4),
            "regime": regime,
            "safety": {"direct_fact_writes": "disabled", "direct_relation_writes": "disabled",
                       "fact_promotion": "disabled", "no_word_blacklists": True}}

def _run_downstream_cycle(self, progress):
    for mn in ("v8_phase7d_slow_wave_sleep_substructure_release",
               "v8_phase7c_adaptive_boundaries_and_ei_balance_release",
               "v8_phase7b1_wake_chain_bridge_release",
               "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release"):
        try:
            m = __import__("ki_system." + mn, fromlist=["managed_cycle"])
            if hasattr(m, "managed_cycle") and m.managed_cycle is not managed_cycle:
                return m.managed_cycle(self, progress), mn
        except Exception:
            continue
    return None, None

def managed_cycle(self, progress=None):
    downstream, dmod = _run_downstream_cycle(self, progress)
    observer = {"phase": "phase7d_workpoint_observer_v1", "status": "not_run", "applied": False}
    try:
        db = resolve_db(self)
        from ki_system import v8_phase7d_workpoint_observer_v1 as _workpoint_observer
        observer = _workpoint_observer.observe_cycle(db)
    except Exception as exc:
        observer = {"phase": "phase7d_workpoint_observer_v1", "status": "observer_error", "error": str(exc), "applied": False}
    try:
        db = resolve_db(self); p7e = run_phase7e_cycle(db)
    except Exception as exc:
        p7e = {"status": "phase7e_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod, "downstream_result": downstream, "phase7d_workpoint_observer_v1": observer, "phase7e_result": p7e}

def managed_run(self, cycles=1, progress=None):
    res = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)): res.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(res), "results": res}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle; AutonomousLoop.run = managed_run
    AutonomousLoop.phase7e_histamine_wake_arousal_release = True
    AutonomousLoop.histamine = True
    for k, v in (("learning_mode", LEARNING_MODE), ("fact_promotion", "disabled"),
                 ("direct_fact_writes", "disabled"), ("direct_relation_writes", "disabled"),
                 ("no_word_blacklists", True)):
        if not hasattr(AutonomousLoop, k): setattr(AutonomousLoop, k, v)
    return AutonomousLoop
