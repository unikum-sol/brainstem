# -*- coding: utf-8 -*-
"""V8 Phase 7b - Endocannabinoid Retrograde Gain Control + Adenosine Coordination Fix."""
from __future__ import annotations
import json, os, sqlite3, time
from pathlib import Path

PHASE = "phase7b_endocannabinoid_retrograde_gain_control_release"
PHASE_VERSION = "phase7b_v1"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7b_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7b_endocannabinoid_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase7b_retrograde_signals": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("signal_type","TEXT"),("source","TEXT"),("magnitude","REAL"),("target_key","TEXT"),
        ("pre_value","REAL"),("post_value","REAL"),("reason","TEXT"),
        ("driver_botenstoff","TEXT"),("driver_botenstoff_value","REAL"),
    ],
    "phase7b_gain_control_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("event_type","TEXT"),("trigger_reason","TEXT"),("action_taken","TEXT"),
        ("anandamide_level","REAL"),("two_ag_level","REAL"),
        ("targets_affected","TEXT"),("dampening_applied","REAL"),("notes","TEXT"),
    ],
    "phase7b_adenosine_override_events": [
        ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
        ("adenosine_level","REAL"),("override_type","TEXT"),("targets_restored","TEXT"),
        ("dampening_factor","REAL"),("pre_state_json","TEXT"),("post_state_json","TEXT"),("reason","TEXT"),
    ],
}

SCHEMA_INDEXES = [
    ("idx_phase7b_retrograde_cyc","phase7b_retrograde_signals","cycle_index"),
    ("idx_phase7b_gain_cyc","phase7b_gain_control_events","cycle_index"),
    ("idx_phase7b_override_cyc","phase7b_adenosine_override_events","cycle_index"),
]

ENDOCANNABINOID_PARAMS = {
    "endocannabinoid_2ag": 0.0, "endocannabinoid_anandamide": 0.1,
    "two_ag_release_gain": 5.0, "two_ag_decay_rate": 0.6,
    "anandamide_lp_alpha": 0.10, "anandamide_baseline": 0.1, "anandamide_max": 0.85,
    "retrograde_dampening_strength": 0.6, "ltd_pull_strength": 0.10,
    "extreme_bias_threshold": 0.35, "adenosine_coordination_threshold": 0.6,
    "adjustment_delta_threshold": 0.08, "override_dampening_factor": 0.6,
    "total_retrograde_signals": 0, "total_ltd_pulls": 0, "total_adenosine_overrides": 0,
}

BIAS_KEYS = ("last_plasticity_level","last_exploration_bias","last_consolidation_bias","last_inhibition_bias","last_revision_bias")
BIAS_MIDS = {"last_plasticity_level":0.5,"last_exploration_bias":0.5,"last_consolidation_bias":0.5,"last_inhibition_bias":0.35,"last_revision_bias":0.5}


class SchemaCheckError(RuntimeError): pass


def _now(): return int(time.time())
def _clamp(x, lo=0.0, hi=1.0):
    try: x = float(x)
    except Exception: x = 0.0
    if x < lo: return lo
    if x > hi: return hi
    return x
def _to_float(x, default=0.0):
    try: return float(x)
    except Exception: return default
def _to_int(x, default=0):
    try: return int(x)
    except Exception: return default
def _table_exists(con, table):
    return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None
def _index_exists(con, index):
    return con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index,)).fetchone() is not None
def _columns(con, table):
    if not _table_exists(con, table): return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]

def resolve_db(obj=None):
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            here = Path(__file__).resolve().parent.parent
            cand = here / "ki_memory.sqlite3"
            if cand.exists(): path = str(cand)
        con = sqlite3.connect(path, timeout=30.0)
        con.row_factory = sqlite3.Row
        return con
    if isinstance(obj, sqlite3.Connection):
        obj.row_factory = sqlite3.Row
        return obj
    for attr in ("db","connection","conn","memory"):
        inner = getattr(obj, attr, None)
        if inner is None: continue
        if isinstance(inner, sqlite3.Connection):
            inner.row_factory = sqlite3.Row
            return inner
        inner2 = getattr(inner, "db", None) or getattr(inner, "connection", None)
        if isinstance(inner2, sqlite3.Connection):
            inner2.row_factory = sqlite3.Row
            return inner2
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
                spec_up = spec.upper()
                if "PRIMARY KEY" in spec_up or "AUTOINCREMENT" in spec_up: continue
                con.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + spec)
                report["added_columns"].append(table + "." + name)
    for idx_name, table, col_expr in SCHEMA_INDEXES:
        if not _index_exists(con, idx_name):
            con.execute("CREATE INDEX " + idx_name + " ON " + table + "(" + col_expr + ")")
            report["created_indexes"].append(idx_name)
    con.commit()
    return report

def _self_check_schema(con):
    missing = []
    for table, cols in SCHEMA_TABLES.items():
        existing = set(_columns(con, table))
        for name, _spec in cols:
            if name not in existing:
                missing.append(table + "." + name)
    return missing

def _kv_set(con, table, key, value):
    if not _table_exists(con, table): return
    tcols = set(_columns(con, table))
    if "key" not in tcols or "value" not in tcols: return
    v = ("true" if value else "false") if isinstance(value, bool) else str(value)
    now = _now()
    if "updated_at" in tcols:
        con.execute("INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (key, v, now))
    else:
        con.execute("INSERT INTO " + table + "(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, v))

def _read_kv(con, table):
    if not _table_exists(con, table): return {}
    tcols = set(_columns(con, table))
    if "key" not in tcols or "value" not in tcols: return {}
    return {r[0]: r[1] for r in con.execute("SELECT key, value FROM " + table).fetchall()}

def _read_neuromod(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    return {"dopamine":_clamp(_to_float(st.get("dopamine"),0.5)),
            "serotonin":_clamp(_to_float(st.get("serotonin"),0.5)),
            "noradrenaline":_clamp(_to_float(st.get("noradrenaline"),0.5)),
            "acetylcholine":_clamp(_to_float(st.get("acetylcholine"),0.5)),
            "glutamate":_clamp(_to_float(st.get("glutamate"),0.5)),
            "gaba":_clamp(_to_float(st.get("gaba"),0.3))}

def initialize_endocannabinoid_parameters(con):
    ensure_schema(con)
    inserted = []
    for k, v in ENDOCANNABINOID_PARAMS.items():
        row = con.execute("SELECT value FROM phase7b_endocannabinoid_state WHERE key=?", (k,)).fetchone()
        if row is None:
            _kv_set(con, "phase7b_endocannabinoid_state", k, v)
            inserted.append(k)
    con.commit()
    return {"inserted": inserted, "total": len(ENDOCANNABINOID_PARAMS)}

def _get_ecb(con, key, default=0.0):
    st = _read_kv(con, "phase7b_endocannabinoid_state")
    return _to_float(st.get(key), default)

def _set_ecb(con, key, value): _kv_set(con, "phase7b_endocannabinoid_state", key, value)

def _get_adenosine_level(con):
    if not _table_exists(con, "phase7a_adenosine_state"): return 0.0
    row = con.execute("SELECT value FROM phase7a_adenosine_state WHERE key='adenosine_level'").fetchone()
    if row is None: return 0.0
    return _to_float(row[0], 0.0)

def _detect_postsynaptic_overload(con):
    if not _table_exists(con, "phase6b_plasticity_adjustments"): return None
    row = con.execute(
        "SELECT id, cycle_index, adjustment_type, "
        " pre_plasticity_level, post_plasticity_level, "
        " pre_exploration_bias, post_exploration_bias, "
        " pre_consolidation_bias, post_consolidation_bias, "
        " pre_inhibition_bias, post_inhibition_bias, "
        " pre_revision_bias, post_revision_bias "
        "FROM phase6b_plasticity_adjustments ORDER BY id DESC LIMIT 1").fetchone()
    if row is None: return None
    keys = ("last_plasticity_level","last_exploration_bias","last_consolidation_bias","last_inhibition_bias","last_revision_bias")
    pres = (row[3], row[5], row[7], row[9], row[11])
    posts = (row[4], row[6], row[8], row[10], row[12])
    deltas = []
    for k, pre, post in zip(keys, pres, posts):
        deltas.append((k, _to_float(pre,0.0), _to_float(post,0.0), abs(_to_float(post,0.0)-_to_float(pre,0.0))))
    deltas.sort(key=lambda x: x[3], reverse=True)
    return {"adjustment_id":_to_int(row[0],0), "adjustment_cycle":_to_int(row[1],0),
            "adjustment_type":row[2] or "",
            "max_delta":deltas[0][3], "target_key":deltas[0][0],
            "pre":{k:p for k,p,_po,_d in deltas},
            "post":{k:po for k,_p,po,_d in deltas},
            "all_deltas":{k:d for k,_p,_po,d in deltas}}

def _log_retrograde_signal(con, cycle_index, signal_type, source, magnitude, target_key,
                           pre_value, post_value, reason, driver_bs, driver_bs_val):
    con.execute("INSERT INTO phase7b_retrograde_signals "
        "(created_at,cycle_index,signal_type,source,magnitude,target_key,pre_value,post_value,reason,driver_botenstoff,driver_botenstoff_value) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (_now(),int(cycle_index),signal_type,source,float(magnitude),target_key,
         float(pre_value),float(post_value),reason,driver_bs,float(driver_bs_val)))

def _log_gain_event(con, cycle_index, event_type, trigger, action, anandamide, two_ag, targets, dampening, notes):
    con.execute("INSERT INTO phase7b_gain_control_events "
        "(created_at,cycle_index,event_type,trigger_reason,action_taken,anandamide_level,two_ag_level,targets_affected,dampening_applied,notes) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (_now(),int(cycle_index),event_type,trigger,action,float(anandamide),float(two_ag),targets,float(dampening),notes))

def _release_2ag(con, overload, cycle_index, neuromod):
    current = _get_ecb(con, "endocannabinoid_2ag", 0.0)
    gain = _get_ecb(con, "two_ag_release_gain", 5.0)
    da = neuromod.get("dopamine",0.5); gaba = neuromod.get("gaba",0.3)
    release = _clamp(overload["max_delta"] * gain * (0.5 + da) * (1.0 - 0.4*gaba), 0.0, 0.6)
    new_2ag = _clamp(current + release, 0.0, 1.0)
    _set_ecb(con, "endocannabinoid_2ag", round(new_2ag,6))
    _kv_set(con, "phase6a_neuromodulated_sleep_state", "endocannabinoid_2ag", round(new_2ag,6))
    total = _to_int(_get_ecb(con,"total_retrograde_signals",0),0) + 1
    _set_ecb(con, "total_retrograde_signals", total)
    _log_retrograde_signal(con, cycle_index, "2ag_release", "postsynaptic_overload",
        release, overload["target_key"], overload["pre"][overload["target_key"]],
        overload["post"][overload["target_key"]],
        "postsynaptic_overshoot_max_delta=" + str(round(overload["max_delta"],4)),
        "dopamine", da)
    con.commit()
    return {"released": release, "new_2ag": new_2ag}

def _decay_2ag(con):
    current = _get_ecb(con, "endocannabinoid_2ag", 0.0)
    decay = _get_ecb(con, "two_ag_decay_rate", 0.6)
    new_val = _clamp(current * decay, 0.0, 1.0)
    _set_ecb(con, "endocannabinoid_2ag", round(new_val,6))
    _kv_set(con, "phase6a_neuromodulated_sleep_state", "endocannabinoid_2ag", round(new_val,6))
    return new_val

def _compute_extreme_bias_score(con):
    st = _read_kv(con, "phase6a_meta_plasticity_state")
    if not st: return 0.0
    vals = []
    for k in BIAS_KEYS:
        if k in st:
            mid = BIAS_MIDS.get(k,0.5)
            v = _to_float(st[k], mid)
            vals.append(abs(v - mid))
    return sum(vals)/len(vals) if vals else 0.0

def _update_anandamide(con, extreme_score):
    current = _get_ecb(con, "endocannabinoid_anandamide", 0.1)
    alpha = _get_ecb(con, "anandamide_lp_alpha", 0.10)
    max_a = _get_ecb(con, "anandamide_max", 0.85)
    target = _clamp(extreme_score * 2.0 * max_a, 0.0, max_a)
    new_val = _clamp((1.0-alpha)*current + alpha*target, 0.0, 1.0)
    _set_ecb(con, "endocannabinoid_anandamide", round(new_val,6))
    _kv_set(con, "phase6a_neuromodulated_sleep_state", "endocannabinoid_anandamide", round(new_val,6))
    return new_val

def _apply_anandamide_ltd(con, anandamide_level, cycle_index, neuromod):
    baseline = _get_ecb(con, "anandamide_baseline", 0.1)
    if anandamide_level <= baseline:
        return {"pulled": 0, "reason": "anandamide_below_baseline"}
    pull_strength = _get_ecb(con, "ltd_pull_strength", 0.10)
    ext_th = _get_ecb(con, "extreme_bias_threshold", 0.35)
    effective_pull = _clamp(pull_strength * (anandamide_level - baseline) * 4.0, 0.0, 0.3)
    st = _read_kv(con, "phase6a_meta_plasticity_state")
    if not st: return {"pulled": 0, "reason": "no_bias_state"}
    pulled = 0; affected = []
    sero = neuromod.get("serotonin", 0.5)
    for k in BIAS_KEYS:
        if k not in st: continue
        mid = BIAS_MIDS.get(k, 0.5)
        v = _to_float(st[k], mid)
        if abs(v - mid) < ext_th: continue
        new_val = _clamp(v + (mid - v) * effective_pull * (1.0 - 0.3*sero))
        _kv_set(con, "phase6a_meta_plasticity_state", k, round(new_val,6))
        _kv_set(con, "phase6a_neuromodulated_sleep_state", k, round(new_val,6))
        if _table_exists(con, "phase6c_target_bias_state"):
            _kv_set(con, "phase6c_target_bias_state", k, round(new_val,6))
        _log_retrograde_signal(con, cycle_index, "anandamide_ltd", "tonic_extreme_bias",
            effective_pull, k, v, new_val,
            "anandamide=" + str(round(anandamide_level,4)) + "_extreme_bias",
            "serotonin", sero)
        pulled += 1; affected.append(k)
    if pulled > 0:
        total = _to_int(_get_ecb(con,"total_ltd_pulls",0),0) + pulled
        _set_ecb(con, "total_ltd_pulls", total)
        _log_gain_event(con, cycle_index, "anandamide_ltd_batch",
            "chronic_extreme_bias", "pull_toward_mid",
            anandamide_level, _get_ecb(con,"endocannabinoid_2ag",0.0),
            json.dumps(affected), effective_pull, "pulled_" + str(pulled) + "_targets")
    con.commit()
    return {"pulled": pulled, "affected_keys": affected, "effective_pull": effective_pull}

def _apply_retrograde_dampening(con, two_ag_level, cycle_index, neuromod):
    if two_ag_level < 0.15: return {"dampened": 0, "reason": "two_ag_below_threshold"}
    if not _table_exists(con, "phase6c_meta_control_parameters"):
        return {"dampened": 0, "reason": "phase6c_missing"}
    strength = _get_ecb(con, "retrograde_dampening_strength", 0.6)
    factor = _clamp(1.0 - strength * two_ag_level, 0.1, 1.0)
    rows = con.execute("SELECT parameter_key, learning_rate FROM phase6c_meta_control_parameters").fetchall()
    dampened = 0
    for r in rows:
        key = r[0]; old_lr = _to_float(r[1], 0.05); new_lr = max(0.005, old_lr * factor)
        if abs(new_lr - old_lr) < 1e-9: continue
        con.execute("UPDATE phase6c_meta_control_parameters SET learning_rate=?, updated_at=? WHERE parameter_key=?",
                    (new_lr, _now(), key))
        _log_retrograde_signal(con, cycle_index, "2ag_dampens_6c_lr", "phase6c_meta_control",
            (old_lr - new_lr), key, old_lr, new_lr,
            "2ag=" + str(round(two_ag_level,4)) + "_factor=" + str(round(factor,4)),
            "gaba", neuromod.get("gaba",0.3))
        dampened += 1
    if dampened > 0:
        _log_gain_event(con, cycle_index, "2ag_retrograde_dampening",
            "2ag_level_high", "reduce_6c_learning_rates",
            _get_ecb(con,"endocannabinoid_anandamide",0.1), two_ag_level,
            json.dumps([r[0] for r in rows]), (1.0 - factor),
            "dampened_" + str(dampened) + "_params_factor=" + str(round(factor,4)))
    con.commit()
    return {"dampened": dampened, "factor": factor}

def _apply_adenosine_ecb_override(con, adenosine_level, cycle_index, overload, neuromod):
    threshold = _get_ecb(con, "adenosine_coordination_threshold", 0.6)
    if adenosine_level < threshold:
        return {"triggered": False, "reason": "adenosine_below_coordination_threshold",
                "adenosine_level": adenosine_level, "threshold": threshold}
    if overload is None:
        return {"triggered": False, "reason": "no_overload_detected", "adenosine_level": adenosine_level}
    if overload.get("adjustment_type") != "plateau_break":
        return {"triggered": False, "reason": "adjustment_not_plateau_break",
                "adjustment_type": overload.get("adjustment_type"), "adenosine_level": adenosine_level}
    dampening = _get_ecb(con, "override_dampening_factor", 0.6)
    pre_state = {}; post_state = {}; restored = []
    for k in BIAS_KEYS:
        pre_v = _to_float(overload["pre"].get(k, 0.5), 0.5)
        post_v = _to_float(overload["post"].get(k, 0.5), 0.5)
        blended = _clamp(dampening * pre_v + (1.0 - dampening) * post_v)
        pre_state[k] = post_v; post_state[k] = blended
        _kv_set(con, "phase6a_meta_plasticity_state", k, round(blended,6))
        _kv_set(con, "phase6a_neuromodulated_sleep_state", k, round(blended,6))
        if _table_exists(con, "phase6c_target_bias_state"):
            _kv_set(con, "phase6c_target_bias_state", k, round(blended,6))
        _log_retrograde_signal(con, cycle_index, "adenosine_ecb_override", "plateau_break_reversal",
            (post_v - blended), k, post_v, blended,
            "adenosine=" + str(round(adenosine_level,4)) + "_dampening=" + str(round(dampening,3)),
            "glutamate", neuromod.get("glutamate",0.5))
        restored.append(k)
    con.execute("INSERT INTO phase7b_adenosine_override_events "
        "(created_at,cycle_index,adenosine_level,override_type,targets_restored,dampening_factor,pre_state_json,post_state_json,reason) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (_now(),int(cycle_index),float(adenosine_level),"adenosine_ecb_retrograde",
         json.dumps(restored),float(dampening),json.dumps(pre_state),json.dumps(post_state),
         "sleep_pressure_high_reverts_6b_plateau_break"))
    total = _to_int(_get_ecb(con,"total_adenosine_overrides",0),0) + 1
    _set_ecb(con, "total_adenosine_overrides", total)
    _log_gain_event(con, cycle_index, "adenosine_ecb_override",
        "adenosine_high_and_6b_plateau_break", "partially_revert_6b_adjustment",
        _get_ecb(con,"endocannabinoid_anandamide",0.1), _get_ecb(con,"endocannabinoid_2ag",0.0),
        json.dumps(restored), dampening, "sleep_pressure_wins_over_6b")
    con.commit()
    return {"triggered": True, "reason": "sleep_pressure_reverts_6b_plateau_break",
            "targets_restored": restored, "dampening_factor": dampening,
            "adenosine_level": adenosine_level}

def run_phase7b_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj)
    ensure_schema(con)
    missing = _self_check_schema(con)
    if missing:
        return {"phase": PHASE, "status": "schema_check_failed", "missing_columns": missing}
    initialize_endocannabinoid_parameters(con)
    if cycle_index is None:
        cur = _to_int(_read_kv(con,"phase7b_state").get("cycle_count"),0)
        cycle_index = cur + 1
    neuromod = _read_neuromod(con)
    ade_level = _get_adenosine_level(con)
    overload = _detect_postsynaptic_overload(con)
    delta_th = _get_ecb(con, "adjustment_delta_threshold", 0.08)
    release_result = None
    if overload is not None and overload["max_delta"] > delta_th:
        release_result = _release_2ag(con, overload, cycle_index, neuromod)
    _decay_2ag(con)
    extreme = _compute_extreme_bias_score(con)
    anandamide = _update_anandamide(con, extreme)
    two_ag_current = _get_ecb(con, "endocannabinoid_2ag", 0.0)
    ltd_result = _apply_anandamide_ltd(con, anandamide, cycle_index, neuromod)
    dampening_result = _apply_retrograde_dampening(con, two_ag_current, cycle_index, neuromod)
    override_result = _apply_adenosine_ecb_override(con, ade_level, cycle_index, overload, neuromod)
    _kv_set(con,"phase7b_state","cycle_count",cycle_index)
    _kv_set(con,"phase7b_state","last_cycle_at",_now())
    _kv_set(con,"phase7b_state","phase",PHASE)
    _kv_set(con,"phase7b_state","phase_version",PHASE_VERSION)
    _kv_set(con,"phase7b_state","learning_mode",LEARNING_MODE)
    _kv_set(con,"phase7b_state","no_word_blacklists",True)
    _kv_set(con,"phase7b_state","direct_fact_writes","disabled")
    _kv_set(con,"phase7b_state","direct_relation_writes","disabled")
    _kv_set(con,"phase7b_state","fact_promotion","disabled")
    _kv_set(con,"phase7b_state","endocannabinoid_retrograde_gain_control",True)
    con.commit()
    return {"phase": PHASE, "cycle_index": cycle_index, "status": "ok",
            "adenosine_level": ade_level, "overload_detected": overload,
            "2ag_release": release_result, "2ag_current": two_ag_current,
            "extreme_bias_score": extreme, "anandamide_level": anandamide,
            "anandamide_ltd": ltd_result, "retrograde_dampening": dampening_result,
            "adenosine_ecb_override": override_result,
            "safety": {"direct_fact_writes":"disabled","direct_relation_writes":"disabled",
                       "fact_promotion":"disabled","no_word_blacklists":True,
                       "endocannabinoid_retrograde_gain_control":True}}

def _run_downstream_cycle(self, progress):
    for mod_name in ("v8_phase7a_adenosine_homeostat_release",
                     "v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release",
                     "v8_phase6c_bias_persistence_and_self_regulating_meta_release",
                     "v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release",
                     "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release"):
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
        phase7b = run_phase7b_cycle(db)
    except Exception as exc:
        phase7b = {"status":"phase7b_error","error":str(exc),"phase":PHASE}
    return {"phase":PHASE,"downstream_module":dmod,"downstream_result":downstream,"phase7b_result":phase7b}

def managed_run(self, cycles=1, progress=None):
    results = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)):
        results.append(managed_cycle(self, progress))
    return {"phase":PHASE,"cycles":len(results),"results":results}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase7b_endocannabinoid_retrograde_gain_control_release = True
    AutonomousLoop._phase7b_endocannabinoid_retrograde_gain_control_release = True
    AutonomousLoop.phase7a_adenosine_homeostat_release = True
    AutonomousLoop.phase6d_saturation_homeostasis_and_meta_metaplasticity_release = True
    AutonomousLoop.phase6c_bias_persistence_and_self_regulating_meta_release = True
    AutonomousLoop.phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release = True
    AutonomousLoop.phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"
    AutonomousLoop.direct_relation_writes = "disabled"
    AutonomousLoop.self_regulating_meta_parameters = True
    AutonomousLoop.saturation_homeostasis = True
    AutonomousLoop.meta_metaplasticity = True
    AutonomousLoop.adenosine_homeostat = True
    AutonomousLoop.endocannabinoid_retrograde_gain_control = True
    return AutonomousLoop
