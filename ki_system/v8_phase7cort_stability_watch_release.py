# -*- coding: utf-8 -*-
"V8 Phase 7cort - Cortisol / HPA-axis Stability Watcher (Stage 1: pure observer)."
from __future__ import annotations
import json, os, sqlite3, time, statistics
from pathlib import Path

PHASE = "phase7cort_stability_watch_release"
PHASE_VERSION = "phase7cort_v1_observer"
NEUROTRANSMITTER = "cortisol"

SCHEMA_TABLES = {
    "cortisol_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "stability_watch_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("allostatic_load","REAL"),("cortisol_level","REAL"),("regime","TEXT"),("dominant_signal","TEXT"),
        ("threshold_drift","REAL"),("survivor_ratio","REAL"),("survivor_ratio_recent","REAL"),("effectiveness","REAL"),
        ("bias_oscillation","REAL"),("ei_saturation","REAL"),("elevated","INTEGER"),("recommended_json","TEXT"),("note","TEXT")],
}
SCHEMA_INDEXES = [("idx_stability_watch_cyc","stability_watch_events","cycle_index")]

WATCH_PARAMS = {
    "cortisol_level": 0.2, "cortisol_baseline": 0.2, "ewma_alpha": 0.3,
    "drift_weight": 0.25, "survivor_weight": 0.25, "effectiveness_weight": 0.25,
    "oscillation_weight": 0.15, "saturation_weight": 0.10,
    "load_high": 0.6, "load_low": 0.15, "nudge_max": 0.05, "cycle_count": 0,
    "recent_tail": 3, "trig_drift": 0.4, "trig_survivor": 0.4, "trig_effectiveness": 0.3,
    "trig_oscillation": 0.4, "trig_saturation": 0.3, "effectiveness_scale": 10.0,
    "stage": 1, "nudge_cap": 0.05, "cooldown": 3, "cooldown_left": 0,
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

def initialize_watch_params(con):
    ensure_schema(con); ins = []
    for k, v in WATCH_PARAMS.items():
        if con.execute("SELECT value FROM cortisol_state WHERE key=?", (k,)).fetchone() is None:
            _kv_set(con, "cortisol_state", k, v); ins.append(k)
    con.commit(); return {"inserted": ins, "total": len(WATCH_PARAMS)}

def _get_p(con, key, d=0.0):
    return _to_float(_read_kv(con, "cortisol_state").get(key), d)
def _set_p(con, key, val): _kv_set(con, "cortisol_state", key, val)

def _read_recent(con, table, col, limit=10):
    if not _table_exists(con, table): return []
    cols = set(_columns(con, table))
    if col not in cols: return []
    idc = "id" if "id" in cols else "rowid"
    try:
        rows = con.execute("SELECT " + col + " FROM " + table + " ORDER BY " + idc + " DESC LIMIT ?", (limit,)).fetchall()
    except Exception:
        return []
    vals = [_to_float(r[0]) for r in rows if r[0] is not None]
    vals.reverse()
    return vals

def _read_neuromod(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    ei = _read_kv(con, "phase7c_state")
    return {
        "glutamate": _clamp(_to_float(ei.get("glutamate_state", st.get("glutamate")), 0.5)),
        "gaba": _clamp(_to_float(ei.get("gaba_state", st.get("gaba")), 0.5)),
    }

def compute_signals(con):
    # BRAINSTEM_CORTISOL_THRESHOLD_POPULATION_V1
    tail = int(_get_p(con, "recent_tail", 3))

    valid_rows = []
    if _table_exists(con, "phase7d_slow_wave_cycles"):
        cols = set(_columns(con, "phase7d_slow_wave_cycles"))
        required = {"adaptive_threshold_avg", "candidates_participated"}
        if required.issubset(cols):
            idc = "id" if "id" in cols else "rowid"
            reason_filter = " AND reason='self_regulating_slow_wave_sleep'" if "reason" in cols else ""
            valid_rows = con.execute(
                "SELECT adaptive_threshold_avg,candidates_survived,candidates_participated "
                "FROM phase7d_slow_wave_cycles WHERE candidates_participated>0" + reason_filter +
                " ORDER BY " + idc + " DESC LIMIT 10"
            ).fetchall()
            valid_rows.reverse()

    thresholds = [_to_float(row[0]) for row in valid_rows if row[0] is not None]
    threshold_drift_available = len(thresholds) >= 2
    threshold_drift = _clamp(0.5 + (thresholds[-1] - thresholds[0])) if threshold_drift_available else 0.5

    ratios = []
    for row in valid_rows:
        survived = _to_float(row[1])
        participated = _to_float(row[2])
        if participated > 0:
            ratios.append(survived / participated)
    population_available = bool(ratios)
    survivor_ratio = _clamp(sum(ratios) / len(ratios)) if ratios else 0.5
    recent = ratios[-tail:] if ratios else []
    survivor_ratio_recent = _clamp(sum(recent) / len(recent)) if recent else survivor_ratio

    eff_vals = _read_recent(con, "phase6b_effectiveness_events", "effectiveness_score", 5)
    effectiveness = (sum(eff_vals) / len(eff_vals)) if eff_vals else 0.0
    bias_vals = _read_recent(con, "phase6c_bias_history", "exploration_bias", 6)
    bias_oscillation = _clamp(statistics.pstdev(bias_vals) * 2) if len(bias_vals) >= 2 else 0.0
    nm = _read_neuromod(con); glu, gaba = nm["glutamate"], nm["gaba"]
    ei_saturation = _clamp(max(abs(glu - 0.5), abs(gaba - 0.5)) * 2 - 0.6)
    return {"threshold_drift": threshold_drift,
            "threshold_drift_available": threshold_drift_available,
            "valid_threshold_count": len(thresholds),
            "survivor_ratio": survivor_ratio,
            "survivor_ratio_recent": survivor_ratio_recent,
            "population_available": population_available,
            "effectiveness": effectiveness,
            "bias_oscillation": bias_oscillation,
            "ei_saturation": ei_saturation}

def _stress_components(sig, con):
    escale = _get_p(con, "effectiveness_scale", 10.0)
    drift_stress = _clamp((sig["threshold_drift"] - 0.5) * 2) if sig.get("threshold_drift_available", False) else 0.0
    r = sig["survivor_ratio_recent"]
    if sig.get("population_available", False):
        over = _clamp(max(0.0, 0.15 - r) / 0.15)
        explosion = _clamp(max(0.0, r - 0.85) / 0.15)
    else:
        over = 0.0
        explosion = 0.0
    survivor_stress = max(over, explosion)
    eff = sig["effectiveness"]
    effectiveness_stress = _clamp(-eff * escale) if eff < 0 else 0.0
    return {"drift": drift_stress, "survivor": survivor_stress, "over": over, "explosion": explosion,
            "effectiveness": effectiveness_stress, "oscillation": sig["bias_oscillation"],
            "saturation": sig["ei_saturation"]}
def _apply_stage2_nudges(con, recommended, allostatic_load):
    stage = _to_int(_get_p(con, "stage", 1))
    load_high = _get_p(con, "load_high", 0.6)
    cooldown = _to_int(_get_p(con, "cooldown", 3))
    cooldown_left = _to_int(_get_p(con, "cooldown_left", 0))
    nudge_cap = _get_p(con, "nudge_cap", 0.05)
    if cooldown_left > 0:
        _set_p(con, "cooldown_left", cooldown_left - 1)
    if stage != 2 or allostatic_load < load_high or cooldown_left > 0 or not recommended:
        return False, []
    if not _table_exists(con, "phase6a_neuromodulated_sleep_state"):
        return False, []
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    ei = _read_kv(con, "phase7c_state")
    changes = []
    for k, delta in recommended.items():
        d = max(-nudge_cap, min(nudge_cap, _to_float(delta)))
        if k in ("glutamate", "gaba") and _table_exists(con, "phase7c_state"):
            state_key = k + "_state"
            old = _clamp(_to_float(ei.get(state_key, st.get(k)), 0.5))
            new = _clamp(old + d)
            _kv_set(con, "phase7c_state", state_key, round(new, 4))
            _kv_set(con, "phase6a_neuromodulated_sleep_state", k, round(new, 4))
        else:
            old = _clamp(_to_float(st.get(k), 0.5))
            new = _clamp(old + d)
            _kv_set(con, "phase6a_neuromodulated_sleep_state", k, round(new, 4))
        changes.append((k, round(old, 4), round(new, 4)))
    _set_p(con, "cooldown_left", cooldown)
    con.commit()
    return True, changes
def run_stability_watch(con, cycle_index=None):
    con = resolve_db(con); ensure_schema(con)
    missing = _self_check_schema(con)
    if missing: return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_watch_params(con)
    if cycle_index is None:
        cycle_index = _to_int(_get_p(con, "cycle_count", 0)) + 1
    sig = compute_signals(con); st = _stress_components(sig, con)
    nudge = _get_p(con, "nudge_max", 0.05)
    w = {k: _get_p(con, k) for k in ("drift_weight","survivor_weight","effectiveness_weight","oscillation_weight","saturation_weight")}
    weighted_sum = (w["drift_weight"]*st["drift"] + w["survivor_weight"]*st["survivor"] +
                    w["effectiveness_weight"]*st["effectiveness"] + w["oscillation_weight"]*st["oscillation"] +
                    w["saturation_weight"]*st["saturation"])
    max_stress = max(st["drift"], st["survivor"], st["effectiveness"], st["oscillation"], st["saturation"])
    allostatic_load = _clamp(0.6 * max_stress + 0.4 * weighted_sum)
    alpha = _get_p(con, "ewma_alpha", 0.3); prev = _get_p(con, "cortisol_level", 0.2)
    cortisol_level = _clamp((1 - alpha) * prev + alpha * allostatic_load)
    load_high = _get_p(con, "load_high", 0.6); load_low = _get_p(con, "load_low", 0.15)
    t_drift = _get_p(con, "trig_drift", 0.4); t_surv = _get_p(con, "trig_survivor", 0.4)
    t_eff = _get_p(con, "trig_effectiveness", 0.3); t_osc = _get_p(con, "trig_oscillation", 0.4); t_sat = _get_p(con, "trig_saturation", 0.3)
    cands = []
    if st["effectiveness"] > t_eff:
        cands.append(("chronic_stress_depression", "effectiveness", st["effectiveness"], {"dopamine": nudge, "noradrenaline": nudge, "serotonin": -nudge*0.5}))
    if st["survivor"] > t_surv and st["over"] >= st["explosion"]:
        cands.append(("acute_over_selection", "survivor_over_selection", st["survivor"], {"glutamate": nudge, "gaba": -nudge}))
    if st["survivor"] > t_surv and st["explosion"] > st["over"]:
        cands.append(("acute_under_selection", "survivor_explosion", st["survivor"], {"gaba": nudge, "glutamate": -nudge}))
    if st["drift"] > t_drift:
        cands.append(("threshold_drift_rising", "threshold_drift", st["drift"], {"glutamate": nudge, "gaba": -nudge}))
    if st["oscillation"] > t_osc:
        cands.append(("oscillation", "bias_oscillation", st["oscillation"], {"gaba": nudge*0.5, "adenosine": nudge}))
    if st["saturation"] > t_sat:
        cands.append(("ei_saturation", "ei_saturation", st["saturation"], {"adenosine": nudge, "gaba": nudge*0.5}))
    if cands:
        cands.sort(key=lambda x: x[2], reverse=True)
        regime, dominant, _mag, rec = cands[0]
    elif allostatic_load <= load_low:
        regime, dominant, rec = "calm", "none", {}
    else:
        regime, dominant, rec = "normal", "none", {}
    elevated = 1 if allostatic_load >= load_high else 0
    now = _now()
    con.execute("INSERT INTO stability_watch_events(created_at,cycle_index,allostatic_load,cortisol_level,regime,dominant_signal,threshold_drift,survivor_ratio,survivor_ratio_recent,effectiveness,bias_oscillation,ei_saturation,elevated,recommended_json,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (now, int(cycle_index), float(allostatic_load), float(cortisol_level), regime, dominant,
                 float(sig["threshold_drift"]), float(sig["survivor_ratio"]), float(sig["survivor_ratio_recent"]),
                 float(sig["effectiveness"]), float(sig["bias_oscillation"]), float(sig["ei_saturation"]), elevated,
                 json.dumps(rec), "stage1_observer_no_apply"))
    _set_p(con, "cortisol_level", cortisol_level); _set_p(con, "cycle_count", cycle_index)
    _set_p(con, "last_regime", regime); _set_p(con, "last_allostatic_load", allostatic_load)
    con.commit()
    _cort_applied, _cort_changes = _apply_stage2_nudges(con, rec, allostatic_load)

    return {"phase": PHASE, "phase_version": PHASE_VERSION, "neurotransmitter": NEUROTRANSMITTER,
            "cycle_index": cycle_index, "allostatic_load": round(allostatic_load, 4),
            "cortisol_level": round(cortisol_level, 4), "regime": regime, "dominant_signal": dominant, "elevated": bool(elevated),
            "signals": {k: round(v, 4) for k, v in sig.items()},
            "stress": {k: round(v, 4) for k, v in st.items()},
            "recommended": rec, "applied": _cort_applied,
            "safety": {"direct_fact_writes": "disabled", "direct_relation_writes": "disabled",
                       "fact_promotion": "disabled", "no_word_blacklists": True,
                       "stage": _to_int(_get_p(con, "stage", 1)), "applied_changes": _cort_changes}}
def register(AutonomousLoop):
    AutonomousLoop.phase7cort_stability_watch = True
    AutonomousLoop.cortisol_observer = True
    return AutonomousLoop
def _run_downstream_cycle(self, progress):
    for mn in ("v8_phase7g_bdnf_growth_consolidation_release",
               "v8_phase7f_orexin_wake_endurance_release",
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
        db = resolve_db(self)
        res = run_stability_watch(db)
    except Exception as exc:
        res = {"status": "phase7cort_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod, "downstream_result": downstream, "phase7cort_result": res}

def managed_run(self, cycles=1, progress=None):
    res = []
    try:
        cycles = int(cycles or 1)
    except Exception:
        cycles = 1
    for _ in range(max(1, cycles)):
        res.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(res), "results": res}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase7cort_stability_watch = True
    AutonomousLoop.cortisol_observer = True
    AutonomousLoop.cortisol_stage2 = True
    for k, v in (("learning_mode", "context_hypotheses_with_neuromodulators"),
                 ("fact_promotion", "disabled"), ("direct_fact_writes", "disabled"),
                 ("direct_relation_writes", "disabled"), ("no_word_blacklists", True)):
        if not hasattr(AutonomousLoop, k):
            setattr(AutonomousLoop, k, v)
    return AutonomousLoop
