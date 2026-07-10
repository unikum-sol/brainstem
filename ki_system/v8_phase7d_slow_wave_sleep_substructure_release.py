# -*- coding: utf-8 -*-
"V8 Phase 7d - Slow-Wave Sleep Substructure (self-regulating down-selection)."
from __future__ import annotations
import json, os, random, sqlite3, time
from pathlib import Path

PHASE = "phase7d_slow_wave_sleep_substructure_release"
PHASE_VERSION = "phase7d_v2_self_regulating"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7d_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7d_slow_wave_params": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7d_slow_wave_cycles": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("n_oscillations","INTEGER"),("adenosine_level","REAL"),("up_state_avg_activity","REAL"),
        ("down_state_scale","REAL"),("candidates_reactivated","INTEGER"),("candidates_survived","INTEGER"),
        ("anchors_interleaved","INTEGER"),("reinforced","INTEGER"),("weakened","INTEGER"),("reason","TEXT"),
        ("selection_pressure","REAL"),("adaptive_threshold_avg","REAL"),("pool_size","INTEGER"),("candidates_participated","INTEGER")],
    "phase7d_up_state_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("oscillation_index","INTEGER"),("source_table","TEXT"),("source_id","INTEGER"),
        ("activity_score","REAL"),("is_anchor","INTEGER"),("active_flag","INTEGER")],
    "phase7d_consolidation_survivors": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("source_table","TEXT"),("source_id","INTEGER"),("up_states_survived","INTEGER"),
        ("final_consistency","REAL"),("reinforced","INTEGER")],
}
SCHEMA_INDEXES = [
    ("idx_phase7d_cycles_cyc","phase7d_slow_wave_cycles","cycle_index"),
    ("idx_phase7d_upstate_cyc","phase7d_up_state_events","cycle_index"),
    ("idx_phase7d_survivors_cyc","phase7d_consolidation_survivors","cycle_index"),
]
SLOW_WAVE_PARAMS = {
    "n_oscillations": 5, "up_state_reactivation_size": 30, "down_state_scale": 0.9,
    "survival_threshold": 3, "anchor_interleave_ratio": 0.3, "activity_threshold": 0.5,
    "slow_wave_freq_hz": 0.8, "reinforce_delta": 0.02, "weaken_delta": 0.01,
    "adenosine_sleep_threshold": 0.5, "total_slow_wave_sleeps": 0,
    "total_reinforced": 0, "total_weakened": 0,
    "reactivation_pool_factor": 4.0, "survival_consistency_ratio": 0.6,
    "min_participation_ratio": 0.4, "activity_threshold_floor": 0.15,
    "selection_pressure_gaba_gain": 0.6, "selection_pressure_glu_gain": 0.4,
    "selection_pressure_base": 0.5,
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

def _quantile(sorted_vals, p):
    n = len(sorted_vals)
    if n == 0: return 0.0
    p = _clamp(p, 0.0, 1.0)
    if n == 1: return float(sorted_vals[0])
    idx = p * (n - 1)
    lo = int(idx); hi = min(lo + 1, n - 1); frac = idx - lo
    return float(sorted_vals[lo]) * (1.0 - frac) + float(sorted_vals[hi]) * frac

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
        if inner is None: continue
        if isinstance(inner, sqlite3.Connection):
            inner.row_factory = sqlite3.Row; return inner
        inner2 = getattr(inner, "db", None) or getattr(inner, "connection", None)
        if isinstance(inner2, sqlite3.Connection):
            inner2.row_factory = sqlite3.Row; return inner2
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
    return {r[0]: r[1] for r in con.execute("SELECT key,value FROM " + table).fetchall()}

def _read_neuromod(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    return {k: _clamp(_to_float(st.get(k), d)) for k, d in [
        ("dopamine", 0.5), ("serotonin", 0.5), ("noradrenaline", 0.5), ("acetylcholine", 0.5), ("glutamate", 0.5), ("gaba", 0.3)]}

def initialize_slow_wave_parameters(con):
    ensure_schema(con); ins = []
    for k, v in SLOW_WAVE_PARAMS.items():
        if con.execute("SELECT value FROM phase7d_slow_wave_params WHERE key=?", (k,)).fetchone() is None:
            _kv_set(con, "phase7d_slow_wave_params", k, v); ins.append(k)
    con.commit(); return {"inserted": ins, "total": len(SLOW_WAVE_PARAMS)}

def _get_sw(con, key, d=0.0):
    return _to_float(_read_kv(con, "phase7d_slow_wave_params").get(key), d)
def _set_sw(con, key, value): _kv_set(con, "phase7d_slow_wave_params", key, value)

def _get_adenosine_level(con):
    if not _table_exists(con, "phase7a_adenosine_state"): return 0.0
    r = con.execute("SELECT value FROM phase7a_adenosine_state WHERE key='adenosine_level'").fetchone()
    return _to_float(r[0], 0.0) if r else 0.0

def _build_candidate_pool(con, pool_size, anchor_ratio):
    n_anchor = int(pool_size * anchor_ratio); n_novel = pool_size - n_anchor
    out = []
    if _table_exists(con, "phase6b_anchor_pool"):
        for r in con.execute("SELECT id,stability_score FROM phase6b_anchor_pool WHERE active=1 ORDER BY stability_score DESC LIMIT ?", (n_anchor,)).fetchall():
            out.append({"source_table": "phase6b_anchor_pool", "source_id": _to_int(r[0]), "is_anchor": True, "base_score": _clamp(_to_float(r[1], 0.5))})
    if _table_exists(con, "phase5g_experiment_outcomes"):
        c = set(_columns(con, "phase5g_experiment_outcomes"))
        sc = "effectiveness_score" if "effectiveness_score" in c else ("outcome_score" if "outcome_score" in c else None)
        idc = "id" if "id" in c else "rowid"
        sql = "SELECT " + idc + ((", " + sc) if sc else "") + " FROM phase5g_experiment_outcomes " + (("ORDER BY " + sc + " ASC ") if sc else "") + "LIMIT ?"
        for r in con.execute(sql, (n_novel,)).fetchall():
            base = _clamp(1.0 - _to_float(r[1], 0.5)) if sc else 0.5
            out.append({"source_table": "phase5g_experiment_outcomes", "source_id": _to_int(r[0]), "is_anchor": False, "base_score": base})
    elif _table_exists(con, "context_hypotheses"):
        for r in con.execute("SELECT id FROM context_hypotheses LIMIT ?", (n_novel,)).fetchall():
            out.append({"source_table": "context_hypotheses", "source_id": _to_int(r[0]), "is_anchor": False, "base_score": 0.5})
    return out

def _run_slow_wave_sleep(con, cycle_index, neuromod, adenosine_level):
    n_osc = int(_get_sw(con, "n_oscillations", 5)); size = int(_get_sw(con, "up_state_reactivation_size", 30))
    anchor_ratio = _get_sw(con, "anchor_interleave_ratio", 0.3); down_scale = _get_sw(con, "down_state_scale", 0.9)
    reinforce_delta = _get_sw(con, "reinforce_delta", 0.02); weaken_delta = _get_sw(con, "weaken_delta", 0.01)
    pool_factor = _get_sw(con, "reactivation_pool_factor", 4.0)
    surv_ratio = _get_sw(con, "survival_consistency_ratio", 0.6)
    min_part_ratio = _get_sw(con, "min_participation_ratio", 0.4)
    thr_floor = _get_sw(con, "activity_threshold_floor", 0.15)
    sp_base = _get_sw(con, "selection_pressure_base", 0.5)
    sp_gaba = _get_sw(con, "selection_pressure_gaba_gain", 0.6)
    sp_glu = _get_sw(con, "selection_pressure_glu_gain", 0.4)
    now = _now(); rnd = random.Random(now + cycle_index * 7919)
    glu = neuromod["glutamate"]; gaba = neuromod["gaba"]
    # self-regulating selection pressure from the system's own neuromodulator state
    sel_pressure = _clamp(sp_base + sp_gaba * gaba - sp_glu * glu)
    pool_size = max(size, int(size * pool_factor))
    pool = _build_candidate_pool(con, pool_size, anchor_ratio)
    if not pool:
        con.execute("INSERT INTO phase7d_slow_wave_cycles(created_at,cycle_index,n_oscillations,adenosine_level,up_state_avg_activity,down_state_scale,candidates_reactivated,candidates_survived,anchors_interleaved,reinforced,weakened,reason,selection_pressure,adaptive_threshold_avg,pool_size,candidates_participated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (now, int(cycle_index), n_osc, float(adenosine_level), 0.0, float(down_scale), 0, 0, 0, 0, 0, "empty_pool", float(sel_pressure), 0.0, pool_size, 0))
        _set_sw(con, "total_slow_wave_sleeps", int(_get_sw(con, "total_slow_wave_sleeps", 0)) + 1); con.commit()
        return {"n_oscillations": n_osc, "pool_size": pool_size, "candidates": 0, "survivors": 0, "reinforced": 0, "weakened": 0, "anchors_interleaved": 0, "selection_pressure": round(sel_pressure,4), "adaptive_threshold_avg": 0.0, "up_state_avg_activity": 0.0, "reason": "empty_pool"}
    participation = {}; active_cnt = {}; meta = {}; anchors_interleaved = 0; thresholds = []
    for osc in range(1, n_osc + 1):
        acts = []
        for it in pool:
            noise = (rnd.random() - 0.5) * 0.3
            a = _clamp(it["base_score"] * (0.6 + 0.5 * glu) * (1.0 - 0.3 * gaba) + noise + (0.12 if it["is_anchor"] else 0.0))
            acts.append((it, a))
        # Efraimidis-Spirakis weighted sampling without replacement
        keyed = [(rnd.random() ** (1.0 / max(1e-6, a)), it, a) for (it, a) in acts]
        keyed.sort(key=lambda x: x[0], reverse=True)
        selected = keyed[:size]
        sel_acts = sorted(a for (_k, _it, a) in selected)
        threshold = max(thr_floor, _quantile(sel_acts, sel_pressure)); thresholds.append(threshold)
        for _k, it, a in selected:
            key = (it["source_table"], it["source_id"])
            if it["is_anchor"]: anchors_interleaved += 1
            participation[key] = participation.get(key, 0) + 1
            act = 1 if a >= threshold else 0
            if act: active_cnt[key] = active_cnt.get(key, 0) + 1
            meta[key] = {"is_anchor": it["is_anchor"], "last_activity": a}
            con.execute("INSERT INTO phase7d_up_state_events(created_at,cycle_index,oscillation_index,source_table,source_id,activity_score,is_anchor,active_flag) VALUES(?,?,?,?,?,?,?,?)",
                        (now, int(cycle_index), osc, it["source_table"], int(it["source_id"]), float(a), 1 if it["is_anchor"] else 0, act))
    min_part = max(1, int(round(min_part_ratio * n_osc)))
    reinforced = 0; weakened = 0; survivors = []
    for key, part in participation.items():
        st, sid = key; ac = active_cnt.get(key, 0); consistency = ac / max(1, part)
        if part >= min_part and consistency >= surv_ratio:
            reinforced += 1; survivors.append(key)
            if st == "phase6b_anchor_pool" and _table_exists(con, "phase6b_anchor_pool"):
                con.execute("UPDATE phase6b_anchor_pool SET stability_score=MIN(1.0,COALESCE(stability_score,0)+?) WHERE id=?", (reinforce_delta, int(sid)))
            con.execute("INSERT INTO phase7d_consolidation_survivors(created_at,cycle_index,source_table,source_id,up_states_survived,final_consistency,reinforced) VALUES(?,?,?,?,?,?,1)",
                        (now, int(cycle_index), st, int(sid), int(ac), float(consistency)))
        else:
            weakened += 1
            if st == "phase6b_anchor_pool" and _table_exists(con, "phase6b_anchor_pool"):
                con.execute("UPDATE phase6b_anchor_pool SET stability_score=MAX(0.0,COALESCE(stability_score,0)-?) WHERE id=?", (weaken_delta, int(sid)))
    up_avg = sum(m["last_activity"] for m in meta.values()) / max(1, len(meta))
    thr_avg = sum(thresholds) / max(1, len(thresholds))
    con.execute("INSERT INTO phase7d_slow_wave_cycles(created_at,cycle_index,n_oscillations,adenosine_level,up_state_avg_activity,down_state_scale,candidates_reactivated,candidates_survived,anchors_interleaved,reinforced,weakened,reason,selection_pressure,adaptive_threshold_avg,pool_size,candidates_participated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (now, int(cycle_index), n_osc, float(adenosine_level), float(up_avg), float(down_scale), len(participation), len(survivors), anchors_interleaved, reinforced, weakened, "self_regulating_slow_wave_sleep", float(sel_pressure), float(thr_avg), pool_size, len(participation)))
    _set_sw(con, "total_slow_wave_sleeps", int(_get_sw(con, "total_slow_wave_sleeps", 0)) + 1)
    _set_sw(con, "total_reinforced", int(_get_sw(con, "total_reinforced", 0)) + reinforced)
    _set_sw(con, "total_weakened", int(_get_sw(con, "total_weakened", 0)) + weakened)
    con.commit()
    return {"n_oscillations": n_osc, "pool_size": pool_size, "candidates": len(participation), "survivors": len(survivors),
            "reinforced": reinforced, "weakened": weakened, "anchors_interleaved": anchors_interleaved,
            "selection_pressure": round(sel_pressure, 4), "adaptive_threshold_avg": round(thr_avg, 4), "up_state_avg_activity": round(up_avg, 4)}

def run_phase7d_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj); ensure_schema(con)
    missing = _self_check_schema(con)
    if missing: return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_slow_wave_parameters(con)
    if cycle_index is None:
        cycle_index = _to_int(_read_kv(con, "phase7d_state").get("cycle_count"), 0) + 1
    neuromod = _read_neuromod(con); ade = _get_adenosine_level(con)
    sleep_th = _get_sw(con, "adenosine_sleep_threshold", 0.5)
    if ade >= sleep_th:
        sw = _run_slow_wave_sleep(con, cycle_index, neuromod, ade); status = "slow_wave_sleep_executed"
    else:
        sw = {"skipped": True, "reason": "adenosine_below_sleep_threshold", "adenosine": ade, "threshold": sleep_th}; status = "awake_no_slow_wave"
    for k, v in [("cycle_count", cycle_index), ("last_cycle_at", _now()), ("phase", PHASE), ("phase_version", PHASE_VERSION),
                 ("learning_mode", LEARNING_MODE), ("no_word_blacklists", True), ("direct_fact_writes", "disabled"),
                 ("direct_relation_writes", "disabled"), ("fact_promotion", "disabled"), ("slow_wave_sleep", True)]:
        _kv_set(con, "phase7d_state", k, v)
    con.commit()
    return {"phase": PHASE, "cycle_index": cycle_index, "status": status, "slow_wave": sw,
            "safety": {"direct_fact_writes": "disabled", "direct_relation_writes": "disabled", "fact_promotion": "disabled", "no_word_blacklists": True, "slow_wave_sleep": True}}

def _run_downstream_cycle(self, progress):
    for mn in ("v8_phase7c_adaptive_boundaries_and_ei_balance_release", "v8_phase7b1_wake_chain_bridge_release",
               "v8_phase7b_endocannabinoid_retrograde_gain_control_release", "v8_phase7a_adenosine_homeostat_release",
               "v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "v8_phase6c_bias_persistence_and_self_regulating_meta_release",
               "v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release"):
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
        db = resolve_db(self); p7d = run_phase7d_cycle(db)
    except Exception as exc:
        p7d = {"status": "phase7d_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod, "downstream_result": downstream, "phase7d_result": p7d}

def managed_run(self, cycles=1, progress=None):
    res = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)): res.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(res), "results": res}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle; AutonomousLoop.run = managed_run
    AutonomousLoop.phase7d_slow_wave_sleep_substructure_release = True
    AutonomousLoop._phase7d_slow_wave_sleep_substructure_release = True
    AutonomousLoop.slow_wave_sleep = True
    for f in ("phase7c_adaptive_boundaries_and_ei_balance_release", "phase7b1_wake_chain_bridge_release",
              "phase7b_endocannabinoid_retrograde_gain_control_release", "phase7a_adenosine_homeostat_release",
              "phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "phase6c_bias_persistence_and_self_regulating_meta_release",
              "phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
              "no_word_blacklists", "adaptive_boundaries", "ei_balance", "sigmoid_soft_clipping", "adenosine_homeostat",
              "endocannabinoid_retrograde_gain_control", "wake_chain_bridge", "saturation_homeostasis", "meta_metaplasticity", "self_regulating_meta_parameters"):
        if not hasattr(AutonomousLoop, f): setattr(AutonomousLoop, f, True)
    AutonomousLoop.learning_mode = LEARNING_MODE; AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"; AutonomousLoop.direct_relation_writes = "disabled"
    return AutonomousLoop
