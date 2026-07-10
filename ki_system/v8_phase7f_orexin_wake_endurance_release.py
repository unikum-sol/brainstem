# -*- coding: utf-8 -*-
"V8 Phase 7f - Orexin / wake-endurance drive (neurotransmitter #11, reading-endurance / curiosity)."
from __future__ import annotations
import os, sqlite3, time
from pathlib import Path

PHASE = "phase7f_orexin_wake_endurance_release"
PHASE_VERSION = "phase7f_v1"
NEUROTRANSMITTER = "orexin"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7f_orexin_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7f_orexin_cycles": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("orexin_level","REAL"),("orexin_target","REAL"),("unread_fraction","REAL"),
        ("marginal_progress","REAL"),("histamine_level","REAL"),("regime","TEXT"),("note","TEXT")],
}
SCHEMA_INDEXES = [("idx_phase7f_cycles_cyc","phase7f_orexin_cycles","cycle_index")]

OREXIN_PARAMS = {
    "orexin_level": 0.5, "orexin_baseline": 0.5, "ewma_alpha": 0.3,
    "unread_weight": 0.5, "progress_weight": 0.3, "histamine_weight": 0.2,
    "progress_gain": 2.0, "high_gate": 0.6, "low_gate": 0.35, "cycle_count": 0,
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

def initialize_orexin_parameters(con):
    ensure_schema(con); ins = []
    for k, v in OREXIN_PARAMS.items():
        if con.execute("SELECT value FROM phase7f_orexin_state WHERE key=?", (k,)).fetchone() is None:
            _kv_set(con, "phase7f_orexin_state", k, v); ins.append(k)
    con.commit(); return {"inserted": ins, "total": len(OREXIN_PARAMS)}

def _get_p(con, key, d=0.0):
    return _to_float(_read_kv(con, "phase7f_orexin_state").get(key), d)
def _set_p(con, key, val): _kv_set(con, "phase7f_orexin_state", key, val)

def _find_chunk_table(con):
    tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    cand = [t for t in tabs if "chunk" in t.lower()]
    if "chunks" in cand: return "chunks"
    best = None; bestscore = -1
    for t in cand:
        n = con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
        textish = any(c in set(_columns(con, t)) for c in ("text", "content", "body"))
        score = n + (1000000 if textish else 0)
        if score > bestscore: bestscore = score; best = t
    return best

def _corpus_unread_fraction(con):
    ch = _find_chunk_table(con)
    if not ch: return 0.5, 0, 0
    total = con.execute("SELECT COUNT(*) FROM " + ch).fetchone()[0]
    covered = 0
    if _table_exists(con, "chunk_attention_scores") and "chunk_id" in set(_columns(con, "chunk_attention_scores")):
        covered = con.execute("SELECT COUNT(DISTINCT chunk_id) FROM chunk_attention_scores").fetchone()[0]
    unread = _clamp(1.0 - (covered / total)) if total > 0 else 0.5
    return unread, total, covered

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

def _get_histamine(con):
    return _clamp(_to_float(_read_kv(con, "phase6a_neuromodulated_sleep_state").get("histamine"), 0.5))

def run_phase7f_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj); ensure_schema(con)
    missing = _self_check_schema(con)
    if missing: return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_orexin_parameters(con)
    if cycle_index is None:
        cycle_index = _to_int(_get_p(con, "cycle_count", 0)) + 1
    unread, total, covered = _corpus_unread_fraction(con)
    prog = _marginal_progress(con); hist = _get_histamine(con)
    pgain = _get_p(con, "progress_gain", 2.0)
    progress_norm = _clamp(0.5 + prog * pgain)
    wu = _get_p(con, "unread_weight", 0.5); wp = _get_p(con, "progress_weight", 0.3); wh = _get_p(con, "histamine_weight", 0.2)
    s = wu + wp + wh
    if s <= 0: wu, wp, wh, s = 0.5, 0.3, 0.2, 1.0
    orexin_target = _clamp((wu / s) * unread + (wp / s) * progress_norm + (wh / s) * hist)
    alpha = _get_p(con, "ewma_alpha", 0.3); prev = _get_p(con, "orexin_level", 0.5)
    orexin_level = _clamp((1 - alpha) * prev + alpha * orexin_target)
    high = _get_p(con, "high_gate", 0.6); low = _get_p(con, "low_gate", 0.35)
    if orexin_level >= high and unread > 0.3:
        regime = "curious_drive"
    elif orexin_level <= low and unread < 0.1:
        regime = "satiated"
    else:
        regime = "balanced"
    if _table_exists(con, "phase6a_neuromodulated_sleep_state"):
        _kv_set(con, "phase6a_neuromodulated_sleep_state", "orexin", round(orexin_level, 4))
    now = _now()
    con.execute("INSERT INTO phase7f_orexin_cycles(created_at,cycle_index,orexin_level,orexin_target,unread_fraction,marginal_progress,histamine_level,regime,note) VALUES(?,?,?,?,?,?,?,?,?)",
                (now, int(cycle_index), float(orexin_level), float(orexin_target), float(unread),
                 float(prog), float(hist), regime, "reading_endurance_curiosity_drive"))
    _set_p(con, "orexin_level", orexin_level); _set_p(con, "cycle_count", cycle_index)
    _set_p(con, "last_regime", regime); _set_p(con, "last_unread_fraction", unread)
    _set_p(con, "last_marginal_progress", prog)
    con.commit()
    return {"phase": PHASE, "phase_version": PHASE_VERSION, "neurotransmitter": NEUROTRANSMITTER,
            "cycle_index": cycle_index, "orexin_level": round(orexin_level, 4),
            "orexin_target": round(orexin_target, 4), "unread_fraction": round(unread, 4),
            "corpus_total": total, "corpus_covered": covered, "marginal_progress": round(prog, 4),
            "histamine_level": round(hist, 4), "regime": regime,
            "safety": {"direct_fact_writes": "disabled", "direct_relation_writes": "disabled",
                       "fact_promotion": "disabled", "no_word_blacklists": True}}

def _run_downstream_cycle(self, progress):
    for mn in ("v8_phase7e_histamine_wake_arousal_release",
               "v8_phase7d_slow_wave_sleep_substructure_release",
               "v8_phase7c_adaptive_boundaries_and_ei_balance_release",
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
        db = resolve_db(self); p7f = run_phase7f_cycle(db)
    except Exception as exc:
        p7f = {"status": "phase7f_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod, "downstream_result": downstream, "phase7f_result": p7f}

def managed_run(self, cycles=1, progress=None):
    res = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)): res.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(res), "results": res}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle; AutonomousLoop.run = managed_run
    AutonomousLoop.phase7f_orexin_wake_endurance_release = True
    AutonomousLoop.orexin = True
    for k, v in (("learning_mode", LEARNING_MODE), ("fact_promotion", "disabled"),
                 ("direct_fact_writes", "disabled"), ("direct_relation_writes", "disabled"),
                 ("no_word_blacklists", True)):
        if not hasattr(AutonomousLoop, k): setattr(AutonomousLoop, k, v)
    return AutonomousLoop
