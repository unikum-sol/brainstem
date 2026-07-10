# -*- coding: utf-8 -*-
"V8 Phase 7g - BDNF / activity-dependent growth and consolidation (neurotransmitter #12)."
from __future__ import annotations
import os, sqlite3, time, statistics
from pathlib import Path

PHASE = "phase7g_bdnf_growth_consolidation_release"
PHASE_VERSION = "phase7g_v1"
NEUROTRANSMITTER = "bdnf"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7g_bdnf_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7g_bdnf_cycles": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("bdnf_level","REAL"),("bdnf_target","REAL"),("consolidation_consistency","REAL"),
        ("marginal_progress","REAL"),("activity_level","REAL"),("regime","TEXT"),("note","TEXT")],
}
SCHEMA_INDEXES = [("idx_phase7g_cycles_cyc","phase7g_bdnf_cycles","cycle_index")]

BDNF_PARAMS = {
    "bdnf_level": 0.5, "bdnf_baseline": 0.5, "ewma_alpha": 0.3,
    "consolidation_weight": 0.45, "progress_weight": 0.35, "activity_weight": 0.2,
    "progress_gain": 2.0, "growth_gate": 0.6, "low_gate": 0.35, "cycle_count": 0,
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

def initialize_bdnf_parameters(con):
    ensure_schema(con); ins = []
    for k, v in BDNF_PARAMS.items():
        if con.execute("SELECT value FROM phase7g_bdnf_state WHERE key=?", (k,)).fetchone() is None:
            _kv_set(con, "phase7g_bdnf_state", k, v); ins.append(k)
    con.commit(); return {"inserted": ins, "total": len(BDNF_PARAMS)}

def _get_p(con, key, d=0.0):
    return _to_float(_read_kv(con, "phase7g_bdnf_state").get(key), d)
def _set_p(con, key, val): _kv_set(con, "phase7g_bdnf_state", key, val)

def _consolidation_consistency(con):
    if not _table_exists(con, "phase7d_slow_wave_cycles"): return 0.5
    cset = set(_columns(con, "phase7d_slow_wave_cycles"))
    if "candidates_survived" not in cset: return 0.5
    where = " WHERE reason='self_regulating_slow_wave_sleep'" if "reason" in cset else ""
    idc = "id" if "id" in cset else "rowid"
    try:
        rows = con.execute("SELECT candidates_survived FROM phase7d_slow_wave_cycles" + where + " ORDER BY " + idc + " DESC LIMIT 10").fetchall()
    except Exception:
        return 0.5
    vals = [_to_float(r[0]) for r in rows if r[0] is not None]
    if len(vals) < 2: return 0.5
    mean = sum(vals) / len(vals)
    sd = statistics.pstdev(vals)
    return _clamp(1.0 - (sd / (mean + 1e-6)))

def _marginal_progress(con):
    TH = "context_hypotheses"
    if not _table_exists(con, TH): return 0.0
    cset = set(_columns(con, TH))
    if "uncertainty" not in cset: return 0.0
    order = "created_at" if "created_at" in cset else "id"
    try:
        nu = con.execute("SELECT AVG(u) FROM (SELECT uncertainty u FROM " + TH + " ORDER BY " + order + " DESC LIMIT 2000)").fetchone()[0]
        ou = con.execute("SELECT AVG(u) FROM (SELECT uncertainty u FROM " + TH + " ORDER BY " + order + " ASC LIMIT 2000)").fetchone()[0]
    except Exception:
        return 0.0
    if nu is None or ou is None: return 0.0
    return float(ou) - float(nu)

def _activity_level(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    orx = _to_float(st.get("orexin"), None) if st.get("orexin") is not None else None
    his = _to_float(st.get("histamine"), None) if st.get("histamine") is not None else None
    vals = [v for v in (orx, his) if v is not None]
    if not vals: return 0.5
    return _clamp(max(vals))

def run_phase7g_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj); ensure_schema(con)
    missing = _self_check_schema(con)
    if missing: return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_bdnf_parameters(con)
    if cycle_index is None:
        cycle_index = _to_int(_get_p(con, "cycle_count", 0)) + 1
    cons = _consolidation_consistency(con); prog = _marginal_progress(con); act = _activity_level(con)
    pgain = _get_p(con, "progress_gain", 2.0)
    progress_norm = _clamp(0.5 + prog * pgain)
    wc = _get_p(con, "consolidation_weight", 0.45); wp = _get_p(con, "progress_weight", 0.35); wa = _get_p(con, "activity_weight", 0.2)
    s = wc + wp + wa
    if s <= 0: wc, wp, wa, s = 0.45, 0.35, 0.2, 1.0
    bdnf_target = _clamp((wc / s) * cons + (wp / s) * progress_norm + (wa / s) * act)
    alpha = _get_p(con, "ewma_alpha", 0.3); prev = _get_p(con, "bdnf_level", 0.5)
    bdnf_level = _clamp((1 - alpha) * prev + alpha * bdnf_target)
    growth_gate = _get_p(con, "growth_gate", 0.6); low = _get_p(con, "low_gate", 0.35)
    if bdnf_level >= growth_gate and progress_norm >= 0.58:
        regime = "growth"
    elif act <= 0.3 and progress_norm <= 0.52:
        regime = "low_plasticity"
    else:
        regime = "maintenance"
    if _table_exists(con, "phase6a_neuromodulated_sleep_state"):
        _kv_set(con, "phase6a_neuromodulated_sleep_state", "bdnf", round(bdnf_level, 4))
    now = _now()
    con.execute("INSERT INTO phase7g_bdnf_cycles(created_at,cycle_index,bdnf_level,bdnf_target,consolidation_consistency,marginal_progress,activity_level,regime,note) VALUES(?,?,?,?,?,?,?,?,?)",
                (now, int(cycle_index), float(bdnf_level), float(bdnf_target), float(cons),
                 float(prog), float(act), regime, "activity_dependent_growth_consolidation"))
    _set_p(con, "bdnf_level", bdnf_level); _set_p(con, "cycle_count", cycle_index)
    _set_p(con, "last_regime", regime); _set_p(con, "last_consolidation_consistency", cons)
    _set_p(con, "last_marginal_progress", prog)
    con.commit()
    return {"phase": PHASE, "phase_version": PHASE_VERSION, "neurotransmitter": NEUROTRANSMITTER,
            "cycle_index": cycle_index, "bdnf_level": round(bdnf_level, 4),
            "bdnf_target": round(bdnf_target, 4), "consolidation_consistency": round(cons, 4),
            "marginal_progress": round(prog, 4), "activity_level": round(act, 4), "regime": regime,
            "safety": {"direct_fact_writes": "disabled", "direct_relation_writes": "disabled",
                       "fact_promotion": "disabled", "no_word_blacklists": True}}

def _run_downstream_cycle(self, progress):
    for mn in ("v8_phase7f_orexin_wake_endurance_release",
               "v8_phase7e_histamine_wake_arousal_release",
               "v8_phase7d_slow_wave_sleep_substructure_release",
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
    try:
        db = resolve_db(self); p7g = run_phase7g_cycle(db)
    except Exception as exc:
        p7g = {"status": "phase7g_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod, "downstream_result": downstream, "phase7g_result": p7g}

def managed_run(self, cycles=1, progress=None):
    res = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)): res.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(res), "results": res}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle; AutonomousLoop.run = managed_run
    AutonomousLoop.phase7g_bdnf_growth_consolidation_release = True
    AutonomousLoop.bdnf = True
    for k, v in (("learning_mode", LEARNING_MODE), ("fact_promotion", "disabled"),
                 ("direct_fact_writes", "disabled"), ("direct_relation_writes", "disabled"),
                 ("no_word_blacklists", True)):
        if not hasattr(AutonomousLoop, k): setattr(AutonomousLoop, k, v)
    return AutonomousLoop