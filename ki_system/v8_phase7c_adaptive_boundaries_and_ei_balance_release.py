# -*- coding: utf-8 -*-
"""
V8 Phase 7c - Adaptive Boundaries + Sigmoid Soft-Clipping + Glu-GABA E/I Balance

Three components:
  A) Adaptive Boundaries: the min/max of phase6c_meta_control_parameters are
     no longer fixed. When a parameter sticks at its boundary and the system
     signals it needs more room, the boundary expands (botenstoff-gated,
     bounded by hard limits). When it idles in the middle, the range contracts.
  B) Sigmoid Soft-Clipping: _soft_clamp keeps differential sensitivity near
     the edges instead of a hard cutoff (avoids "gradient death").
  C) Reciprocal Glu-GABA coupling (E/I balance): bidirectional, time-delayed.
     Glutamate drives GABA (feedforward inhibition), GABA dampens glutamate
     (feedback), preventing runaway co-excitation ("digital epilepsy").

Compass: no blacklists, no facts/relations/questions writes, no fact promotion.
Physical [0,1] limits stay hard. Only regulator dynamics get soft edges.
"""

from __future__ import annotations
import json, math, os, sqlite3, time
from pathlib import Path

PHASE = "phase7c_adaptive_boundaries_and_ei_balance_release"
PHASE_VERSION = "phase7c_v1_shadow_recurrence"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7c_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7c_boundary_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7c_parameter_streaks": [
        ("parameter_key","TEXT PRIMARY KEY"),("min_streak","INTEGER DEFAULT 0"),
        ("max_streak","INTEGER DEFAULT 0"),("mid_streak","INTEGER DEFAULT 0"),
        ("last_value","REAL DEFAULT 0"),("updated_at","INTEGER")],
    "phase7c_boundary_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("parameter_key","TEXT"),("boundary","TEXT"),("pre_min","REAL"),("post_min","REAL"),
        ("pre_max","REAL"),("post_max","REAL"),("delta","REAL"),
        ("driver_botenstoff","TEXT"),("driver_botenstoff_value","REAL"),("reason","TEXT")],
    "phase7c_ei_balance_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("glu_pre","REAL"),("glu_post","REAL"),("gaba_pre","REAL"),("gaba_post","REAL"),
        ("gamma","REAL"),("alpha","REAL"),("reason","TEXT")],
    "phase7c_ei_shadow_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("drive_glutamate","REAL"),("drive_gaba","REAL"),
        ("active_glu_pre","REAL"),("active_glu_post","REAL"),
        ("active_gaba_pre","REAL"),("active_gaba_post","REAL"),
        ("shadow_glu_pre","REAL"),("shadow_glu_post","REAL"),
        ("shadow_gaba_pre","REAL"),("shadow_gaba_post","REAL"),
        ("gamma","REAL"),("alpha","REAL"),("applied","INTEGER DEFAULT 0"),("reason","TEXT")],
}

SCHEMA_INDEXES = [
    ("idx_phase7c_boundary_cyc","phase7c_boundary_events","cycle_index"),
    ("idx_phase7c_boundary_key","phase7c_boundary_events","parameter_key"),
    ("idx_phase7c_ei_cyc","phase7c_ei_balance_events","cycle_index"),
    ("idx_phase7c_ei_shadow_cyc","phase7c_ei_shadow_events","cycle_index"),
]

BOUNDARY_PARAMS = {
    "saturation_streak_threshold": 5,
    "expansion_delta": 0.05,
    "contraction_delta": 0.03,
    "mid_pendulum_threshold": 20,
    "ei_gamma": 0.15,
    "ei_alpha": 0.12,
    "sigmoid_softness": 0.08,
    "total_expansions": 0,
    "total_contractions": 0,
    "total_ei_couplings": 0,
}

HARD_BOUNDARIES = {
    "plateau_break_scale": (0.30, 0.995),
    "plateau_eps": (0.0001, 0.1),
    "exploration_delta": (0.005, 0.6),
    "inhibition_delta": (0.005, 0.5),
    "revision_delta": (0.005, 0.4),
    "consolidation_delta": (0.005, 0.35),
    "stabilize_threshold": (0.001, 0.2),
    "novel_ratio_base": (0.15, 0.95),
    "novel_ratio_gaba_weight": (0.02, 0.8),
    "novel_ratio_na_weight": (0.02, 0.7),
    "critic_min_stable_base": (1.0, 20.0),
    "critic_snapshot_p_base": (0.01, 0.5),
    "critic_snapshot_p_range": (0.05, 0.95),
    "gaba_novel_inhibition": (0.05, 0.98),
}


def _now(): return int(time.time())

def _clamp(x, lo=0.0, hi=1.0):
    try: x = float(x)
    except Exception: x = 0.0
    if x < lo: return lo
    if x > hi: return hi
    return x

def _soft_clamp(x, lo=0.0, hi=1.0, softness=0.08):
    try: x = float(x)
    except Exception: x = 0.0
    range_ = hi - lo
    if range_ <= 0: return lo
    t = (x - lo) / range_
    if t <= 0: return lo
    if t >= 1: return hi
    k = 1.0 / max(1e-6, softness)
    log_val = 1.0 / (1.0 + math.exp(-k * (t - 0.5)))
    if t < softness:
        blend = t / softness
        mapped = (1 - blend) * log_val + blend * t
    elif t > 1 - softness:
        blend = (1 - t) / softness
        mapped = (1 - blend) * log_val + blend * t
    else:
        mapped = t
    return lo + mapped * range_

def _to_float(x, default=0.0):
    try: return float(x)
    except Exception: return default

def _to_int(x, default=0):
    try: return int(x)
    except Exception: return default

def _table_exists(con, t):
    return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None

def _index_exists(con, i):
    return con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (i,)).fetchone() is not None

def _columns(con, t):
    if not _table_exists(con, t): return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + t + ")").fetchall()]

def resolve_db(obj=None):
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            here = Path(__file__).resolve().parent.parent
            cand = here / "ki_memory.sqlite3"
            if cand.exists(): path = str(cand)
        con = sqlite3.connect(path, timeout=30.0); con.row_factory = sqlite3.Row
        return con
    if isinstance(obj, sqlite3.Connection):
        obj.row_factory = sqlite3.Row; return obj
    for attr in ("db","connection","conn","memory"):
        inner = getattr(obj, attr, None)
        if inner is None: continue
        if isinstance(inner, sqlite3.Connection):
            inner.row_factory = sqlite3.Row; return inner
        inner2 = getattr(inner, "db", None) or getattr(inner, "connection", None)
        if isinstance(inner2, sqlite3.Connection):
            inner2.row_factory = sqlite3.Row; return inner2
    return resolve_db(None)

def ensure_schema(con):
    report = {"created_tables": [], "added_columns": [], "created_indexes": []}
    for table, cols in SCHEMA_TABLES.items():
        if not _table_exists(con, table):
            col_defs = ", ".join(name + " " + spec for name, spec in cols)
            con.execute("CREATE TABLE " + table + " (" + col_defs + ")")
            report["created_tables"].append(table)
        else:
            existing = set(_columns(con, table))
            for name, spec in cols:
                if name in existing: continue
                su = spec.upper()
                if "PRIMARY KEY" in su or "AUTOINCREMENT" in su: continue
                con.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + spec)
                report["added_columns"].append(table + "." + name)
    for idx, table, col in SCHEMA_INDEXES:
        if not _index_exists(con, idx):
            con.execute("CREATE INDEX " + idx + " ON " + table + "(" + col + ")")
            report["created_indexes"].append(idx)
    con.commit()
    return report

def _self_check_schema(con):
    missing = []
    for table, cols in SCHEMA_TABLES.items():
        existing = set(_columns(con, table))
        for name, _s in cols:
            if name not in existing: missing.append(table + "." + name)
    return missing

def _kv_set(con, table, key, value):
    if not _table_exists(con, table): return
    tc = set(_columns(con, table))
    if "key" not in tc or "value" not in tc: return
    v = ("true" if value else "false") if isinstance(value, bool) else str(value)
    now = _now()
    if "updated_at" in tc:
        con.execute("INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (key, v, now))
    else:
        con.execute("INSERT INTO " + table + "(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, v))

def _read_kv(con, table):
    if not _table_exists(con, table): return {}
    tc = set(_columns(con, table))
    if "key" not in tc or "value" not in tc: return {}
    return {r[0]: r[1] for r in con.execute("SELECT key, value FROM " + table).fetchall()}

def _read_neuromod(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    return {
        "dopamine": _clamp(_to_float(st.get("dopamine"), 0.5)),
        "serotonin": _clamp(_to_float(st.get("serotonin"), 0.5)),
        "noradrenaline": _clamp(_to_float(st.get("noradrenaline"), 0.5)),
        "acetylcholine": _clamp(_to_float(st.get("acetylcholine"), 0.5)),
        "glutamate": _clamp(_to_float(st.get("glutamate"), 0.5)),
        "gaba": _clamp(_to_float(st.get("gaba"), 0.3)),
    }

def initialize_boundary_parameters(con):
    ensure_schema(con)
    inserted = []
    for k, v in BOUNDARY_PARAMS.items():
        row = con.execute("SELECT value FROM phase7c_boundary_state WHERE key=?", (k,)).fetchone()
        if row is None:
            _kv_set(con, "phase7c_boundary_state", k, v)
            inserted.append(k)
    con.commit()
    return {"inserted": inserted, "total": len(BOUNDARY_PARAMS)}

def _get_bp(con, key, default=0.0):
    st = _read_kv(con, "phase7c_boundary_state")
    return _to_float(st.get(key), default)

def _set_bp(con, key, value):
    _kv_set(con, "phase7c_boundary_state", key, value)

def _read_meta_params(con):
    if not _table_exists(con, "phase6c_meta_control_parameters"):
        return []
    cols = set(_columns(con, "phase6c_meta_control_parameters"))
    need = {"parameter_key", "current_value", "min_value", "max_value"}
    if not need.issubset(cols):
        return []
    out = []
    for r in con.execute(
        "SELECT parameter_key, current_value, min_value, max_value FROM phase6c_meta_control_parameters"
    ).fetchall():
        out.append({"key": r[0], "current": _to_float(r[1]), "min": _to_float(r[2]), "max": _to_float(r[3])})
    return out


# ============ Component A: adaptive boundaries ============

def _get_streaks(con, key):
    row = con.execute(
        "SELECT min_streak, max_streak, mid_streak FROM phase7c_parameter_streaks WHERE parameter_key=?",
        (key,)).fetchone()
    if row is None:
        return 0, 0, 0
    return _to_int(row[0]), _to_int(row[1]), _to_int(row[2])

def _set_streaks(con, key, mn, mx, mid, last_value):
    con.execute(
        "INSERT INTO phase7c_parameter_streaks(parameter_key,min_streak,max_streak,mid_streak,last_value,updated_at) "
        "VALUES(?,?,?,?,?,?) ON CONFLICT(parameter_key) DO UPDATE SET "
        "min_streak=excluded.min_streak, max_streak=excluded.max_streak, mid_streak=excluded.mid_streak, "
        "last_value=excluded.last_value, updated_at=excluded.updated_at",
        (key, mn, mx, mid, float(last_value), _now()))

def _log_boundary(con, cyc, key, boundary, pre_min, post_min, pre_max, post_max, driver, driver_val, reason):
    con.execute(
        "INSERT INTO phase7c_boundary_events(created_at,cycle_index,parameter_key,boundary,"
        "pre_min,post_min,pre_max,post_max,delta,driver_botenstoff,driver_botenstoff_value,reason) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), int(cyc), key, boundary, float(pre_min), float(post_min),
         float(pre_max), float(post_max),
         float((post_max - pre_max) + (pre_min - post_min)), driver, float(driver_val), reason))

def _update_streaks_and_adapt(con, cycle_index, neuromod):
    params = _read_meta_params(con)
    threshold = int(_get_bp(con, "saturation_streak_threshold", 5))
    exp_delta = _get_bp(con, "expansion_delta", 0.05)
    con_delta = _get_bp(con, "contraction_delta", 0.03)
    mid_threshold = int(_get_bp(con, "mid_pendulum_threshold", 20))
    da = neuromod["dopamine"]; na = neuromod["noradrenaline"]; sero = neuromod["serotonin"]
    expansions, contractions = [], []

    for p in params:
        key = p["key"]; cur = p["current"]; mn = p["min"]; mx = p["max"]
        rng = mx - mn
        pos = (cur - mn) / rng if rng > 1e-9 else 0.5
        min_s, max_s, mid_s = _get_streaks(con, key)
        if pos >= 0.98:
            max_s += 1; min_s = 0; mid_s = 0
        elif pos <= 0.02:
            min_s += 1; max_s = 0; mid_s = 0
        elif 0.4 <= pos <= 0.6:
            mid_s += 1
        hard_min, hard_max = HARD_BOUNDARIES.get(key, (0.0, 1.0))

        acted = False
        if max_s >= threshold:
            new_max = _clamp(mx + exp_delta * da, mn + 0.01, hard_max)
            if abs(new_max - mx) > 1e-9:
                con.execute("UPDATE phase6c_meta_control_parameters SET max_value=?, updated_at=? WHERE parameter_key=?",
                            (new_max, _now(), key))
                _log_boundary(con, cycle_index, key, "max", mn, mn, mx, new_max, "dopamine", da,
                              "max_streak_" + str(max_s) + "_expand_up")
                _set_bp(con, "total_expansions", int(_get_bp(con, "total_expansions", 0)) + 1)
                expansions.append({"key": key, "boundary": "max", "old": mx, "new": new_max})
                max_s = 0; acted = True
        elif min_s >= threshold:
            new_min = _clamp(mn - exp_delta * na, hard_min, mx - 0.01)
            if abs(new_min - mn) > 1e-9:
                con.execute("UPDATE phase6c_meta_control_parameters SET min_value=?, updated_at=? WHERE parameter_key=?",
                            (new_min, _now(), key))
                _log_boundary(con, cycle_index, key, "min", mn, new_min, mx, mx, "noradrenaline", na,
                              "min_streak_" + str(min_s) + "_expand_down")
                _set_bp(con, "total_expansions", int(_get_bp(con, "total_expansions", 0)) + 1)
                expansions.append({"key": key, "boundary": "min", "old": mn, "new": new_min})
                min_s = 0; acted = True
        elif mid_s >= mid_threshold:
            new_min = _clamp(mn + con_delta * 0.5, hard_min, cur - 0.01)
            new_max = _clamp(mx - con_delta * 0.5, cur + 0.01, hard_max)
            if abs(new_min - mn) > 1e-9 or abs(new_max - mx) > 1e-9:
                con.execute("UPDATE phase6c_meta_control_parameters SET min_value=?, max_value=?, updated_at=? WHERE parameter_key=?",
                            (new_min, new_max, _now(), key))
                _log_boundary(con, cycle_index, key, "both", mn, new_min, mx, new_max, "serotonin", sero,
                              "mid_streak_" + str(mid_s) + "_contract_range")
                _set_bp(con, "total_contractions", int(_get_bp(con, "total_contractions", 0)) + 1)
                contractions.append({"key": key, "old_min": mn, "new_min": new_min, "old_max": mx, "new_max": new_max})
                mid_s = 0; acted = True

        _set_streaks(con, key, min_s, max_s, mid_s, cur)

    con.commit()
    return {"expansions": expansions, "contractions": contractions,
            "adapted_count": len(expansions) + len(contractions)}


# ============ Component C: E/I balance (with soft-clamp = Component B) ============

def _apply_ei_balance(con, cycle_index, neuromod):
    gamma = _get_bp(con, "ei_gamma", 0.15)
    alpha = _get_bp(con, "ei_alpha", 0.12)
    softness = _get_bp(con, "sigmoid_softness", 0.08)
    shared = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    state = _read_kv(con, "phase7c_state")
    drive_glu = _clamp(_to_float(shared.get("glutamate_drive", shared.get("glutamate")), neuromod["glutamate"]))
    drive_gaba = _clamp(_to_float(shared.get("gaba_drive", shared.get("gaba")), neuromod["gaba"]))

    # BRAINSTEM_PHASE7C_SHADOW_RECURRENCE_V1
    # Active path: known one-cycle E/I transform from the current Phase6a drive.
    active_glu_pre = drive_glu
    active_gaba_pre = drive_gaba
    active_gaba_post = _soft_clamp(active_gaba_pre + alpha * active_glu_pre, 0.0, 1.0, softness)
    active_glu_post = _soft_clamp(active_glu_pre - gamma * active_gaba_pre, 0.0, 1.0, softness)

    # BRAINSTEM_PHASE7C_REJECTED_SHADOW_CANDIDATE_V1
    # The first recurrent candidate was falsified in a passive 20-cycle run.
    # Preserve its last state and history, but do not evolve or apply it again.
    shadow_glu_state = _clamp(_to_float(state.get("shadow_glutamate_state", active_glu_post), active_glu_post))
    shadow_gaba_state = _clamp(_to_float(state.get("shadow_gaba_state", active_gaba_post), active_gaba_post))
    shadow_glu_pre = shadow_glu_state
    shadow_glu_post = shadow_glu_state
    shadow_gaba_pre = shadow_gaba_state
    shadow_gaba_post = shadow_gaba_state

    _kv_set(con, "phase7c_state", "glutamate_state", round(active_glu_post, 6))
    _kv_set(con, "phase7c_state", "gaba_state", round(active_gaba_post, 6))
    _kv_set(con, "phase7c_state", "last_glutamate_drive", round(drive_glu, 6))
    _kv_set(con, "phase7c_state", "last_gaba_drive", round(drive_gaba, 6))
    _kv_set(con, "phase7c_state", "shadow_recurrence_applied", False)
    _kv_set(con, "phase7c_state", "shadow_candidate_status", "rejected_glutamate_floor_collapse")
    _kv_set(con, "phase7c_state", "shadow_candidate_active", False)
    _kv_set(con, "phase7c_state", "ei_mode", "active_one_cycle_shadow_rejected")
    _kv_set(con, "phase6a_neuromodulated_sleep_state", "glutamate", round(active_glu_post, 6))
    _kv_set(con, "phase6a_neuromodulated_sleep_state", "gaba", round(active_gaba_post, 6))
    if _table_exists(con, "phase6a_meta_plasticity_state"):
        _kv_set(con, "phase6a_meta_plasticity_state", "glutamate", round(active_glu_post, 6))
        _kv_set(con, "phase6a_meta_plasticity_state", "gaba", round(active_gaba_post, 6))

    con.execute(
        "INSERT INTO phase7c_ei_balance_events(created_at,cycle_index,glu_pre,glu_post,gaba_pre,gaba_post,gamma,alpha,reason) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (_now(), int(cycle_index), float(active_glu_pre), float(active_glu_post),
         float(active_gaba_pre), float(active_gaba_post), float(gamma), float(alpha),
         "active_one_cycle_from_phase6a_drive"))
    _set_bp(con, "total_ei_couplings", int(_get_bp(con, "total_ei_couplings", 0)) + 1)
    con.commit()
    return {"glu_pre": active_glu_pre, "glu_post": active_glu_post,
            "gaba_pre": active_gaba_pre, "gaba_post": active_gaba_post,
            "glutamate_drive": drive_glu, "gaba_drive": drive_gaba,
            "shadow_glu_pre": shadow_glu_pre, "shadow_glu_post": shadow_glu_post,
            "shadow_gaba_pre": shadow_gaba_pre, "shadow_gaba_post": shadow_gaba_post,
            "shadow_applied": False, "shadow_candidate_active": False,
            "shadow_candidate_status": "rejected_glutamate_floor_collapse",
            "gamma": gamma, "alpha": alpha}


def run_phase7c_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj)
    ensure_schema(con)
    missing = _self_check_schema(con)
    if missing:
        return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_boundary_parameters(con)
    if cycle_index is None:
        cycle_index = _to_int(_read_kv(con, "phase7c_state").get("cycle_count"), 0) + 1
    neuromod = _read_neuromod(con)
    boundaries = _update_streaks_and_adapt(con, cycle_index, neuromod)
    ei = _apply_ei_balance(con, cycle_index, neuromod)
    _kv_set(con, "phase7c_state", "cycle_count", cycle_index)
    _kv_set(con, "phase7c_state", "last_cycle_at", _now())
    _kv_set(con, "phase7c_state", "phase", PHASE)
    _kv_set(con, "phase7c_state", "phase_version", PHASE_VERSION)
    _kv_set(con, "phase7c_state", "learning_mode", LEARNING_MODE)
    _kv_set(con, "phase7c_state", "no_word_blacklists", True)
    _kv_set(con, "phase7c_state", "direct_fact_writes", "disabled")
    _kv_set(con, "phase7c_state", "direct_relation_writes", "disabled")
    _kv_set(con, "phase7c_state", "fact_promotion", "disabled")
    _kv_set(con, "phase7c_state", "adaptive_boundaries", True)
    _kv_set(con, "phase7c_state", "ei_balance", True)
    _kv_set(con, "phase7c_state", "sigmoid_soft_clipping", True)
    con.commit()
    return {"phase": PHASE, "cycle_index": cycle_index, "status": "ok",
            "boundaries": boundaries, "ei_balance": ei,
            "safety": {"direct_fact_writes": "disabled", "direct_relation_writes": "disabled",
                       "fact_promotion": "disabled", "no_word_blacklists": True,
                       "adaptive_boundaries": True, "ei_balance": True, "sigmoid_soft_clipping": True}}


def _run_downstream_cycle(self, progress):
    for mod_name in (
        "v8_phase7b1_wake_chain_bridge_release",
        "v8_phase7b_endocannabinoid_retrograde_gain_control_release",
        "v8_phase7a_adenosine_homeostat_release",
        "v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release",
        "v8_phase6c_bias_persistence_and_self_regulating_meta_release",
        "v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release",
        "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
    ):
        try:
            m = __import__("ki_system." + mod_name, fromlist=["managed_cycle"])
            if hasattr(m, "managed_cycle") and m.managed_cycle is not managed_cycle:
                return m.managed_cycle(self, progress), mod_name
        except Exception:
            continue
    return None, None

def managed_cycle(self, progress=None):
    downstream, dmod = _run_downstream_cycle(self, progress)
    try:
        db = resolve_db(self)
        phase7c = run_phase7c_cycle(db)
    except Exception as exc:
        phase7c = {"status": "phase7c_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod, "downstream_result": downstream,
            "phase7c_result": phase7c}

def managed_run(self, cycles=1, progress=None):
    results = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)):
        results.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(results), "results": results}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase7c_adaptive_boundaries_and_ei_balance_release = True
    AutonomousLoop._phase7c_adaptive_boundaries_and_ei_balance_release = True
    AutonomousLoop.adaptive_boundaries = True
    AutonomousLoop.ei_balance = True
    AutonomousLoop.sigmoid_soft_clipping = True
    for flag in ("phase7b1_wake_chain_bridge_release",
                 "phase7b_endocannabinoid_retrograde_gain_control_release",
                 "phase7a_adenosine_homeostat_release",
                 "phase6d_saturation_homeostasis_and_meta_metaplasticity_release",
                 "phase6c_bias_persistence_and_self_regulating_meta_release",
                 "phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release",
                 "phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
                 "no_word_blacklists", "wake_chain_bridge", "adenosine_homeostat",
                 "endocannabinoid_retrograde_gain_control", "saturation_homeostasis",
                 "meta_metaplasticity", "self_regulating_meta_parameters"):
        if not hasattr(AutonomousLoop, flag):
            setattr(AutonomousLoop, flag, True)
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"
    AutonomousLoop.direct_relation_writes = "disabled"
    return AutonomousLoop
