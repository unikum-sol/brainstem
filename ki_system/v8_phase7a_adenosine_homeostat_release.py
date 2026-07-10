# -*- coding: utf-8 -*-
"""
V8 Phase 7a - Adenosine Homeostat Release

Project compass:
    - No blacklist / filter system.
    - No direct facts / relations / questions writes.
    - No fact promotion.
    - Digital neuromodulators steer the WHOLE learning process.
    - This phase adds adenosine as a natural saturation counter-force.

Biological grounding:
    - Tononi and Cirelli (Synaptic Homeostasis Hypothesis, SHY):
      wake-time learning increases synaptic strength; sleep-driven
      downscaling is required to prevent saturation.
    - Adenosine is the biological signal that builds up during wake
      activity and drives sleep pressure. It naturally enforces
      renormalization once its threshold is reached.

Design:
    - adenosine_level accumulates each "wake" cycle proportional to
      recent learning activity.
    - Above threshold_high: enter "sleep_pressure" mode. Gentle
      global downscaling of saturated bias values back toward mid.
    - After downscale: adenosine drains rapidly (biological recovery).
    - Below threshold_low: pure wake mode, no interference.
    - All parameters live in phase7a_adenosine_state (key/value) and
      are extendable in future phases.

Safety:
    - SCHEMA_TABLES is single source of truth for ALL columns.
    - ensure_schema idempotent.
    - _self_check_schema aborts before any write on missing columns.
    - No touches to facts / relations / questions.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PHASE = "phase7a_adenosine_homeostat_release"
PHASE_VERSION = "phase7a_v1"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


# =========================================================================
# SCHEMA
# =========================================================================

SCHEMA_TABLES = {
    "phase7a_state": [
        ("key",        "TEXT PRIMARY KEY"),
        ("value",      "TEXT"),
        ("updated_at", "INTEGER"),
    ],
    "phase7a_adenosine_state": [
        ("key",        "TEXT PRIMARY KEY"),
        ("value",      "TEXT"),
        ("updated_at", "INTEGER"),
    ],
    "phase7a_adenosine_events": [
        ("id",                       "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",               "INTEGER"),
        ("cycle_index",              "INTEGER"),
        ("event_type",               "TEXT"),
        ("adenosine_level",          "REAL"),
        ("sleep_pressure",           "REAL"),
        ("downscale_factor",         "REAL"),
        ("action_taken",             "TEXT"),
        ("targets_affected",         "TEXT"),
        ("reason",                   "TEXT"),
        ("driver_botenstoff",        "TEXT"),
        ("driver_botenstoff_value",  "REAL"),
    ],
    "phase7a_sleep_pressure_history": [
        ("id",                        "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",                "INTEGER"),
        ("cycle_index",               "INTEGER"),
        ("adenosine_level",           "REAL"),
        ("wake_activity_since",       "REAL"),
        ("downscale_applied",         "REAL"),
        ("effectiveness_before",      "REAL"),
        ("effectiveness_after",       "REAL"),
        ("recovery_delta",            "REAL"),
        ("anchor_stability_before",   "REAL"),
        ("anchor_stability_after",    "REAL"),
        ("notes",                     "TEXT"),
    ],
}

SCHEMA_INDEXES = [
    ("idx_phase7a_events_cyc",  "phase7a_adenosine_events",       "cycle_index"),
    ("idx_phase7a_history_cyc", "phase7a_sleep_pressure_history", "cycle_index"),
]


ADENOSINE_PARAMS = {
    "adenosine_level":              0.0,
    "buildup_rate":                 0.08,
    "activity_scale":               0.5,
    "decay_after_sleep":            0.85,
    "threshold_high":               0.65,
    "threshold_low":                0.15,
    "downscale_min":                0.05,
    "downscale_max":                0.25,
    "wake_activity_last":           0.0,
    "cycles_since_last_downscale":  0,
    "total_wake_cycles":            0,
    "total_downscales":             0,
    "last_adenosine_level":         0.0,
    "last_sleep_pressure":          0.0,
}


BIAS_KEYS = (
    "last_plasticity_level",
    "last_exploration_bias",
    "last_consolidation_bias",
    "last_inhibition_bias",
    "last_revision_bias",
)

BIAS_MIDS = {
    "last_plasticity_level":   0.5,
    "last_exploration_bias":   0.5,
    "last_consolidation_bias": 0.5,
    "last_inhibition_bias":    0.35,
    "last_revision_bias":      0.5,
}


class SchemaCheckError(RuntimeError):
    pass


# =========================================================================
# Helpers
# =========================================================================

def _now():
    return int(time.time())


def _clamp(x, lo=0.0, hi=1.0):
    try:
        x = float(x)
    except Exception:
        x = 0.0
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
    row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def _index_exists(con, index):
    row = con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index,)).fetchone()
    return row is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]


def resolve_db(obj=None):
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            here = Path(__file__).resolve().parent.parent
            cand = here / "ki_memory.sqlite3"
            if cand.exists():
                path = str(cand)
        con = sqlite3.connect(path, timeout=30.0)
        con.row_factory = sqlite3.Row
        return con
    if isinstance(obj, sqlite3.Connection):
        obj.row_factory = sqlite3.Row
        return obj
    for attr in ("db", "connection", "conn", "memory"):
        inner = getattr(obj, attr, None)
        if inner is None:
            continue
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
                if name in existing:
                    continue
                spec_up = spec.upper()
                if "PRIMARY KEY" in spec_up or "AUTOINCREMENT" in spec_up:
                    continue
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
    if not _table_exists(con, table):
        return
    tcols = set(_columns(con, table))
    if "key" not in tcols or "value" not in tcols:
        return
    if isinstance(value, bool):
        v = "true" if value else "false"
    else:
        v = str(value)
    now = _now()
    if "updated_at" in tcols:
        con.execute(
            "INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, v, now),
        )
    else:
        con.execute(
            "INSERT INTO " + table + "(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, v),
        )


def _read_kv(con, table):
    if not _table_exists(con, table):
        return {}
    tcols = set(_columns(con, table))
    if "key" not in tcols or "value" not in tcols:
        return {}
    out = {}
    for r in con.execute("SELECT key, value FROM " + table).fetchall():
        out[r[0]] = r[1]
    return out


def _read_neuromod(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    return {
        "dopamine":      _clamp(_to_float(st.get("dopamine"),      0.5)),
        "serotonin":     _clamp(_to_float(st.get("serotonin"),     0.5)),
        "noradrenaline": _clamp(_to_float(st.get("noradrenaline"), 0.5)),
        "acetylcholine": _clamp(_to_float(st.get("acetylcholine"), 0.5)),
        "glutamate":     _clamp(_to_float(st.get("glutamate"),     0.5)),
        "gaba":          _clamp(_to_float(st.get("gaba"),          0.3)),
    }


# =========================================================================
# Adenosine parameter access
# =========================================================================

def initialize_adenosine_parameters(con):
    ensure_schema(con)
    inserted = []
    for k, v in ADENOSINE_PARAMS.items():
        row = con.execute(
            "SELECT value FROM phase7a_adenosine_state WHERE key=?", (k,)
        ).fetchone()
        if row is None:
            _kv_set(con, "phase7a_adenosine_state", k, v)
            inserted.append(k)
    con.commit()
    return {"inserted": inserted, "total": len(ADENOSINE_PARAMS)}


def _get_ade(con, key, default=0.0):
    st = _read_kv(con, "phase7a_adenosine_state")
    return _to_float(st.get(key), default)


def _set_ade(con, key, value):
    _kv_set(con, "phase7a_adenosine_state", key, value)


# =========================================================================
# Wake activity measurement
# =========================================================================

def _count_rows(con, table):
    if not _table_exists(con, table):
        return None
    try:
        return _to_int(con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 0)
    except Exception:
        return None


def _measure_wake_activity(con):
    st = _read_kv(con, "phase7a_state")
    ch = _count_rows(con, "context_hypotheses")
    out = _count_rows(con, "phase5g_experiment_outcomes")
    cyc = _count_rows(con, "phase6a_sleep_replay_cycles")

    last_ch = _to_int(st.get("last_ch_count"), 0)
    last_out = _to_int(st.get("last_outcome_count"), 0)
    last_cyc = _to_int(st.get("last_cycle_count"), 0)

    d_ch = max(0, (ch or 0) - last_ch) if ch is not None else 0
    d_out = max(0, (out or 0) - last_out) if out is not None else 0
    d_cyc = max(0, (cyc or 0) - last_cyc) if cyc is not None else 0

    _kv_set(con, "phase7a_state", "last_ch_count", ch if ch is not None else last_ch)
    _kv_set(con, "phase7a_state", "last_outcome_count", out if out is not None else last_out)
    _kv_set(con, "phase7a_state", "last_cycle_count", cyc if cyc is not None else last_cyc)
    con.commit()

    if ch is None and out is None and cyc is None:
        # very fresh DB, no learning signals yet
        return {"wake_activity": 0.1, "d_ch": 0, "d_out": 0, "d_cyc": 0,
                "reason": "fresh_db_default"}

    raw = (
        0.5 * math.log1p(d_ch) / math.log1p(1000)
        + 0.3 * math.log1p(d_out) / math.log1p(2000)
        + 0.2 * math.log1p(d_cyc) / math.log1p(50)
    )
    activity = _clamp(raw, 0.0, 1.0)
    return {"wake_activity": activity, "d_ch": d_ch, "d_out": d_out, "d_cyc": d_cyc,
            "reason": "measured"}


# =========================================================================
# Adenosine accumulation
# =========================================================================

def _accumulate_adenosine(con, wake_activity, neuromod, cycle_index):
    old = _get_ade(con, "adenosine_level", 0.0)
    br = _get_ade(con, "buildup_rate", 0.08)
    ascale = _get_ade(con, "activity_scale", 0.5)
    ach = neuromod.get("acetylcholine", 0.5)

    rate = br * (1.0 + ascale * wake_activity)
    # Acetylcholine (wake alertness) slightly reduces adenosine buildup
    rate *= (1.2 - 0.4 * ach)
    new = _clamp(old + rate, 0.0, 1.0)

    _set_ade(con, "adenosine_level", round(new, 6))
    _set_ade(con, "wake_activity_last", round(wake_activity, 6))
    _set_ade(con, "last_adenosine_level", round(old, 6))
    _set_ade(con, "last_sleep_pressure", round(new, 6))

    _log_event(con, cycle_index, "buildup", new, new, 0.0,
               "accumulate", "[]",
               "rate=" + str(round(rate, 6)) + "_wake_activity=" + str(round(wake_activity, 4)),
               "acetylcholine", ach)
    con.commit()
    return {"old": old, "new": new, "rate": rate, "sleep_pressure": new}


# =========================================================================
# Saturation identification and downscale
# =========================================================================

def _identify_saturated_targets(con):
    tol = 0.05
    st = _read_kv(con, "phase6a_meta_plasticity_state")
    out = []
    for k in BIAS_KEYS:
        if k not in st:
            continue
        v = _to_float(st[k], None)
        if v is None:
            continue
        if v <= tol:
            out.append((k, v, "min"))
        elif v >= 1.0 - tol:
            out.append((k, v, "max"))
    return out


def _log_event(con, cycle_index, event_type, ade_level, sleep_pressure,
               downscale_factor, action, targets_json, reason,
               driver_bs, driver_bs_val):
    con.execute(
        "INSERT INTO phase7a_adenosine_events "
        "(created_at, cycle_index, event_type, adenosine_level, sleep_pressure, "
        " downscale_factor, action_taken, targets_affected, reason, "
        " driver_botenstoff, driver_botenstoff_value) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), int(cycle_index), event_type, float(ade_level), float(sleep_pressure),
         float(downscale_factor), action, targets_json, reason,
         driver_bs, float(driver_bs_val)),
    )


def _perform_sleep_downscale(con, adenosine_level, saturated_targets,
                             neuromod, cycle_index):
    th_high = _get_ade(con, "threshold_high", 0.65)
    dmin = _get_ade(con, "downscale_min", 0.05)
    dmax = _get_ade(con, "downscale_max", 0.25)
    decay = _get_ade(con, "decay_after_sleep", 0.85)
    glu = neuromod.get("glutamate", 0.5)
    sero = neuromod.get("serotonin", 0.5)

    # Overshoot above threshold_high scales the pull
    overshoot = max(0.0, adenosine_level - th_high)
    denom = max(1e-6, 1.0 - th_high)
    pull = dmin + overshoot * (dmax - dmin) / denom
    pull *= (0.7 + 0.6 * glu) * (1.0 - 0.3 * sero)
    pull = _clamp(pull, 0.02, 0.4)

    if not saturated_targets:
        # No targets: only decay adenosine (idle sleep cycle)
        new_ade = _clamp(adenosine_level * decay, 0.0, 1.0)
        _set_ade(con, "adenosine_level", round(new_ade, 6))
        _set_ade(con, "cycles_since_last_downscale", 0)
        total = _to_int(_get_ade(con, "total_downscales", 0), 0) + 1
        _set_ade(con, "total_downscales", total)
        _log_event(con, cycle_index, "idle_decay",
                   new_ade, adenosine_level, 0.0,
                   "adenosine_decay_only", "[]",
                   "no_saturated_targets_but_pressure_high",
                   "glutamate", glu)
        con.commit()
        return {"triggered": True, "action": "idle_decay",
                "pull": pull, "new_adenosine": new_ade,
                "targets_affected": []}

    affected = []
    for key, value, side in saturated_targets:
        mid = BIAS_MIDS.get(key, 0.5)
        new_val = _clamp(value + (mid - value) * pull)
        # Write to phase6a bias state
        _kv_set(con, "phase6a_meta_plasticity_state", key, round(new_val, 6))
        _kv_set(con, "phase6a_neuromodulated_sleep_state", key, round(new_val, 6))
        # Also to phase6c target so the sticky bridge does not restore boundary
        if _table_exists(con, "phase6c_target_bias_state"):
            _kv_set(con, "phase6c_target_bias_state", key, round(new_val, 6))
        affected.append({"key": key, "pre": value, "post": new_val, "side": side})

    new_ade = _clamp(adenosine_level * decay, 0.0, 1.0)
    _set_ade(con, "adenosine_level", round(new_ade, 6))
    _set_ade(con, "cycles_since_last_downscale", 0)
    total = _to_int(_get_ade(con, "total_downscales", 0), 0) + 1
    _set_ade(con, "total_downscales", total)

    _log_event(con, cycle_index, "sleep_downscale",
               new_ade, adenosine_level, pull,
               "renormalize_toward_mid",
               json.dumps([a["key"] for a in affected]),
               "adenosine_above_threshold_high_targets_saturated",
               "glutamate", glu)
    con.commit()
    return {"triggered": True, "action": "sleep_downscale",
            "pull": pull, "new_adenosine": new_ade,
            "targets_affected": affected}


# =========================================================================
# Effectiveness recovery
# =========================================================================

def _measure_effectiveness_recovery(con):
    if not _table_exists(con, "phase6b_effectiveness_events"):
        return None
    rows = con.execute(
        "SELECT effectiveness_score, anchor_consistency FROM phase6b_effectiveness_events "
        "ORDER BY id DESC LIMIT 6"
    ).fetchall()
    if not rows:
        return None
    def _avg(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else 0.0
    after = _to_float(rows[0][0], 0.0)
    before = _avg([_to_float(r[0], None) for r in rows[1:]])
    as_after = _to_float(rows[0][1], 0.0)
    as_before = _avg([_to_float(r[1], None) for r in rows[1:]])
    return {"effectiveness_before": before, "effectiveness_after": after,
            "anchor_stability_before": as_before, "anchor_stability_after": as_after,
            "recovery_delta": after - before}


# =========================================================================
# Main cycle
# =========================================================================

def run_phase7a_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj)
    ensure_schema(con)
    missing = _self_check_schema(con)
    if missing:
        return {"phase": PHASE, "status": "schema_check_failed",
                "missing_columns": missing}

    initialize_adenosine_parameters(con)

    if cycle_index is None:
        cur = _to_int(_read_kv(con, "phase7a_state").get("cycle_count"), 0)
        cycle_index = cur + 1

    neuromod = _read_neuromod(con)
    wake = _measure_wake_activity(con)
    accum = _accumulate_adenosine(con, wake["wake_activity"], neuromod, cycle_index)

    th_high = _get_ade(con, "threshold_high", 0.65)
    downscale_result = None
    if accum["new"] >= th_high:
        sat = _identify_saturated_targets(con)
        downscale_result = _perform_sleep_downscale(con, accum["new"], sat,
                                                    neuromod, cycle_index)
    else:
        cslc = _to_int(_get_ade(con, "cycles_since_last_downscale", 0), 0) + 1
        _set_ade(con, "cycles_since_last_downscale", cslc)
        downscale_result = {"triggered": False,
                            "reason": "below_threshold_high",
                            "adenosine_level": accum["new"],
                            "threshold_high": th_high,
                            "cycles_since_last_downscale": cslc}

    total_wake = _to_int(_get_ade(con, "total_wake_cycles", 0), 0) + 1
    _set_ade(con, "total_wake_cycles", total_wake)

    eff_rec = _measure_effectiveness_recovery(con)
    if downscale_result.get("triggered") and eff_rec is not None:
        try:
            con.execute(
                "INSERT INTO phase7a_sleep_pressure_history "
                "(created_at, cycle_index, adenosine_level, wake_activity_since, "
                " downscale_applied, effectiveness_before, effectiveness_after, "
                " recovery_delta, anchor_stability_before, anchor_stability_after, notes) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (_now(), int(cycle_index), float(accum["new"]),
                 float(wake["wake_activity"]),
                 float(downscale_result.get("pull", 0.0)),
                 float(eff_rec["effectiveness_before"]),
                 float(eff_rec["effectiveness_after"]),
                 float(eff_rec["recovery_delta"]),
                 float(eff_rec["anchor_stability_before"]),
                 float(eff_rec["anchor_stability_after"]),
                 json.dumps({"action": downscale_result.get("action"),
                             "targets": [t.get("key") for t in downscale_result.get("targets_affected", []) if isinstance(t, dict)]})),
            )
        except Exception:
            pass

    _kv_set(con, "phase7a_state", "cycle_count", cycle_index)
    _kv_set(con, "phase7a_state", "last_cycle_at", _now())
    _kv_set(con, "phase7a_state", "phase", PHASE)
    _kv_set(con, "phase7a_state", "phase_version", PHASE_VERSION)
    _kv_set(con, "phase7a_state", "learning_mode", LEARNING_MODE)
    _kv_set(con, "phase7a_state", "no_word_blacklists", True)
    _kv_set(con, "phase7a_state", "direct_fact_writes", "disabled")
    _kv_set(con, "phase7a_state", "direct_relation_writes", "disabled")
    _kv_set(con, "phase7a_state", "fact_promotion", "disabled")
    _kv_set(con, "phase7a_state", "adenosine_homeostat", True)

    con.commit()

    return {
        "phase": PHASE,
        "cycle_index": cycle_index,
        "status": "ok",
        "wake_activity": wake,
        "adenosine_accumulation": accum,
        "downscale": downscale_result,
        "effectiveness_recovery": eff_rec,
        "safety": {
            "direct_fact_writes": "disabled",
            "direct_relation_writes": "disabled",
            "fact_promotion": "disabled",
            "no_word_blacklists": True,
            "adenosine_homeostat": True,
        },
    }


# =========================================================================
# AutonomousLoop integration
# =========================================================================

def _run_downstream_cycle(self, progress):
    for mod_name in (
        "v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release",
        "v8_phase6c_bias_persistence_and_self_regulating_meta_release",
        "v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release",
        "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
    ):
        try:
            m = __import__("ki_system." + mod_name, fromlist=["managed_cycle"])
            if hasattr(m, "managed_cycle") and m.managed_cycle is not managed_cycle:
                return m.managed_cycle(self, progress), mod_name
        except Exception as exc:
            continue
    return None, None


def managed_cycle(self, progress=None):
    downstream, dmod = _run_downstream_cycle(self, progress)
    try:
        db = resolve_db(self)
        phase7a = run_phase7a_cycle(db)
    except Exception as exc:
        phase7a = {"status": "phase7a_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "downstream_module": dmod,
            "downstream_result": downstream,
            "phase7a_result": phase7a}


def managed_run(self, cycles=1, progress=None):
    results = []
    try:
        cycles = int(cycles or 1)
    except Exception:
        cycles = 1
    for _ in range(max(1, cycles)):
        results.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(results), "results": results}


def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase7a_adenosine_homeostat_release = True
    AutonomousLoop._phase7a_adenosine_homeostat_release = True
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
    return AutonomousLoop
