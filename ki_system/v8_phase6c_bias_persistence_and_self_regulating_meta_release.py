# -*- coding: utf-8 -*-
"""
V8 Phase 6c - Bias Persistence Bridge + Self-Regulating Meta Parameters Release

Project compass:
    - No blacklist / filter system.
    - No direct facts / relations / questions writes.
    - No fact promotion.
    - Digital neuromodulators steer the WHOLE learning process.
    - Meta-parameters (learning rate, error weighting, revision pressure,
      exploration, inhibition, stabilization, consolidation, reading /
      attention strategy) are NOT hardcoded. They live in the DB and are
      adapted every cycle from L2M feedback and neuromodulator state.

Purpose of phase6c:
    (1) Bias Persistence Bridge: keep phase6b's plasticity adjustments
        from being reset by phase6a on the next cycle.
    (2) Self-Regulating Meta Parameters: replace all hardcoded constants
        with DB-backed, adaptively regulated values.

Safety:
    - SCHEMA_TABLES is the single source of truth for ALL columns.
    - ensure_schema() adds missing columns idempotently.
    - _self_check_schema() aborts before any write if a column is missing.
"""

from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PHASE = "phase6c_bias_persistence_and_self_regulating_meta_release"
PHASE_VERSION = "phase6c_v1"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


# =========================================================================
# SCHEMA
# =========================================================================

SCHEMA_TABLES: Dict[str, List[Tuple[str, str]]] = {
    "phase6c_state": [
        ("key",        "TEXT PRIMARY KEY"),
        ("value",      "TEXT"),
        ("updated_at", "INTEGER"),
    ],
    "phase6c_meta_control_parameters": [
        ("parameter_key",       "TEXT PRIMARY KEY"),
        ("current_value",       "REAL"),
        ("default_value",       "REAL"),
        ("min_value",           "REAL"),
        ("max_value",           "REAL"),
        ("learning_rate",       "REAL"),
        ("driver_botenstoff",   "TEXT"),
        ("driver_metric",       "TEXT"),
        ("description",         "TEXT"),
        ("created_at",          "INTEGER"),
        ("updated_at",          "INTEGER"),
    ],
    "phase6c_target_bias_state": [
        ("key",        "TEXT PRIMARY KEY"),
        ("value",      "TEXT"),
        ("updated_at", "INTEGER"),
    ],
    "phase6c_regulation_events": [
        ("id",                       "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",               "INTEGER"),
        ("cycle_index",              "INTEGER"),
        ("parameter_key",            "TEXT"),
        ("pre_value",                "REAL"),
        ("post_value",               "REAL"),
        ("delta",                    "REAL"),
        ("driver_botenstoff",        "TEXT"),
        ("driver_botenstoff_value",  "REAL"),
        ("driver_metric",            "TEXT"),
        ("driver_value",             "REAL"),
        ("reason",                   "TEXT"),
    ],
}

SCHEMA_INDEXES: List[Tuple[str, str, str]] = [
    ("idx_phase6c_regulation_cyc",   "phase6c_regulation_events", "cycle_index"),
    ("idx_phase6c_regulation_param", "phase6c_regulation_events", "parameter_key"),
]


META_PARAMETER_DEFAULTS: List[Dict[str, Any]] = [
    {"parameter_key": "plateau_break_scale",     "default_value": 0.85,  "min_value": 0.55,   "max_value": 0.98,
     "learning_rate": 0.08, "driver_botenstoff": "dopamine",      "driver_metric": "performance_recovery",
     "description":   "Scale factor for plasticity_level during plateau_break; smaller = more aggressive downscale"},
    {"parameter_key": "plateau_eps",             "default_value": 0.005, "min_value": 0.0005, "max_value": 0.05,
     "learning_rate": 0.10, "driver_botenstoff": "acetylcholine", "driver_metric": "delta_variance",
     "description":   "Threshold for classifying a cycle as plateau"},
    {"parameter_key": "exploration_delta",       "default_value": 0.15,  "min_value": 0.02,   "max_value": 0.35,
     "learning_rate": 0.08, "driver_botenstoff": "noradrenaline", "driver_metric": "plateau_persistence",
     "description":   "Increment applied to exploration_bias on plateau_break"},
    {"parameter_key": "inhibition_delta",        "default_value": 0.10,  "min_value": 0.02,   "max_value": 0.30,
     "learning_rate": 0.08, "driver_botenstoff": "gaba",          "driver_metric": "plateau_persistence",
     "description":   "Increment applied to inhibition_bias on plateau_break"},
    {"parameter_key": "revision_delta",          "default_value": 0.10,  "min_value": 0.02,   "max_value": 0.25,
     "learning_rate": 0.06, "driver_botenstoff": "serotonin",     "driver_metric": "backward_transfer",
     "description":   "Increment applied to revision_bias on plateau_break"},
    {"parameter_key": "consolidation_delta",     "default_value": 0.05,  "min_value": 0.01,   "max_value": 0.20,
     "learning_rate": 0.05, "driver_botenstoff": "dopamine",      "driver_metric": "effectiveness_score",
     "description":   "Increment applied to consolidation_bias on positive effectiveness"},
    {"parameter_key": "stabilize_threshold",     "default_value": 0.02,  "min_value": 0.005,  "max_value": 0.10,
     "learning_rate": 0.05, "driver_botenstoff": "dopamine",      "driver_metric": "effectiveness_score",
     "description":   "effectiveness_score threshold above which stabilize_gains is chosen"},
    {"parameter_key": "novel_ratio_base",        "default_value": 0.60,  "min_value": 0.30,   "max_value": 0.85,
     "learning_rate": 0.05, "driver_botenstoff": "noradrenaline", "driver_metric": "anchor_consistency",
     "description":   "Base ratio of novel candidates vs anchors in interleaved replay"},
    {"parameter_key": "novel_ratio_gaba_weight", "default_value": 0.30,  "min_value": 0.05,   "max_value": 0.60,
     "learning_rate": 0.04, "driver_botenstoff": "gaba",          "driver_metric": "plateau_persistence",
     "description":   "How strongly GABA reduces the novel ratio"},
    {"parameter_key": "novel_ratio_na_weight",   "default_value": 0.20,  "min_value": 0.05,   "max_value": 0.50,
     "learning_rate": 0.04, "driver_botenstoff": "noradrenaline", "driver_metric": "forward_transfer",
     "description":   "How strongly noradrenaline boosts the novel ratio"},
    {"parameter_key": "critic_min_stable_base",  "default_value": 3.0,   "min_value": 2.0,    "max_value": 10.0,
     "learning_rate": 0.15, "driver_botenstoff": "serotonin",     "driver_metric": "backward_transfer",
     "description":   "Minimum stable cycles between critic snapshots (base)"},
    {"parameter_key": "critic_snapshot_p_base",  "default_value": 0.05,  "min_value": 0.02,   "max_value": 0.30,
     "learning_rate": 0.05, "driver_botenstoff": "serotonin",     "driver_metric": "anchor_stability",
     "description":   "Base probability for taking a critic snapshot"},
    {"parameter_key": "critic_snapshot_p_range", "default_value": 0.50,  "min_value": 0.10,   "max_value": 0.80,
     "learning_rate": 0.05, "driver_botenstoff": "serotonin",     "driver_metric": "anchor_stability",
     "description":   "Serotonin-scaled additional probability for critic snapshot"},
    {"parameter_key": "gaba_novel_inhibition",   "default_value": 0.50,  "min_value": 0.10,   "max_value": 0.90,
     "learning_rate": 0.06, "driver_botenstoff": "gaba",          "driver_metric": "plateau_persistence",
     "description":   "GABA-driven probabilistic inhibition of novel candidates in batch selection"},
]


class SchemaCheckError(RuntimeError):
    pass


# =========================================================================
# Low-level helpers
# =========================================================================

def _now() -> int:
    return int(time.time())


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        x = float(x)
    except Exception:
        x = 0.0
    if x < lo: return lo
    if x > hi: return hi
    return x


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _to_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def _index_exists(con: sqlite3.Connection, index: str) -> bool:
    row = con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index,)).fetchone()
    return row is not None


def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]


def resolve_db(obj: Any = None) -> sqlite3.Connection:
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            here = Path(__file__).resolve().parent.parent
            candidate = here / "ki_memory.sqlite3"
            if candidate.exists():
                path = str(candidate)
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


def ensure_schema(con: sqlite3.Connection) -> Dict[str, Any]:
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


def _self_check_schema(con: sqlite3.Connection) -> List[str]:
    missing = []
    for table, cols in SCHEMA_TABLES.items():
        existing = set(_columns(con, table))
        for name, _spec in cols:
            if name not in existing:
                missing.append(table + "." + name)
    return missing


def _kv_set(con: sqlite3.Connection, table: str, key: str, value: Any) -> None:
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


def _read_kv(con: sqlite3.Connection, table: str) -> Dict[str, str]:
    if not _table_exists(con, table):
        return {}
    tcols = set(_columns(con, table))
    if "key" not in tcols or "value" not in tcols:
        return {}
    out = {}
    for r in con.execute("SELECT key, value FROM " + table).fetchall():
        out[r[0]] = r[1]
    return out


# =========================================================================
# Meta-parameter initialization and access
# =========================================================================

def initialize_meta_parameters(con: sqlite3.Connection) -> Dict[str, Any]:
    ensure_schema(con)
    now = _now()
    inserted = []
    for p in META_PARAMETER_DEFAULTS:
        row = con.execute(
            "SELECT current_value FROM phase6c_meta_control_parameters WHERE parameter_key=?",
            (p["parameter_key"],),
        ).fetchone()
        if row is None:
            con.execute(
                "INSERT INTO phase6c_meta_control_parameters "
                "(parameter_key, current_value, default_value, min_value, max_value, "
                " learning_rate, driver_botenstoff, driver_metric, description, "
                " created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (p["parameter_key"], p["default_value"], p["default_value"],
                 p["min_value"], p["max_value"], p["learning_rate"],
                 p["driver_botenstoff"], p["driver_metric"], p["description"],
                 now, now),
            )
            inserted.append(p["parameter_key"])
    con.commit()
    return {"inserted": inserted, "total_parameters": len(META_PARAMETER_DEFAULTS)}


def _get_all_meta_params(con: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in con.execute(
        "SELECT parameter_key, current_value, default_value, min_value, max_value, "
        " learning_rate, driver_botenstoff, driver_metric "
        "FROM phase6c_meta_control_parameters"
    ).fetchall():
        out[r[0]] = {
            "current_value":     _to_float(r[1]),
            "default_value":     _to_float(r[2]),
            "min_value":         _to_float(r[3]),
            "max_value":         _to_float(r[4]),
            "learning_rate":     _to_float(r[5]),
            "driver_botenstoff": r[6],
            "driver_metric":     r[7],
        }
    return out


def _get_meta_value(cfg: Dict[str, Dict[str, Any]], key: str, fallback: float) -> float:
    p = cfg.get(key)
    if p is None:
        return fallback
    return _to_float(p.get("current_value"), fallback)


def _set_meta_value(con: sqlite3.Connection, key: str, new_value: float) -> None:
    con.execute(
        "UPDATE phase6c_meta_control_parameters "
        "SET current_value=?, updated_at=? WHERE parameter_key=?",
        (float(new_value), _now(), key),
    )


def _log_regulation_event(con: sqlite3.Connection, cycle_index: int, key: str,
                          pre: float, post: float,
                          driver_bs: Optional[str], bs_value: float,
                          driver_metric: str, driver_value: float,
                          reason: str) -> None:
    con.execute(
        "INSERT INTO phase6c_regulation_events "
        "(created_at, cycle_index, parameter_key, pre_value, post_value, delta, "
        " driver_botenstoff, driver_botenstoff_value, driver_metric, driver_value, reason) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), int(cycle_index), key, float(pre), float(post),
         float(post - pre), driver_bs, float(bs_value),
         driver_metric, float(driver_value), reason),
    )


# =========================================================================
# Neuromodulators and metric readouts
# =========================================================================

def _read_neuromodulators(con: sqlite3.Connection) -> Dict[str, float]:
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    return {
        "dopamine":      _clamp(_to_float(st.get("dopamine"),      0.5)),
        "serotonin":     _clamp(_to_float(st.get("serotonin"),     0.5)),
        "noradrenaline": _clamp(_to_float(st.get("noradrenaline"), 0.5)),
        "acetylcholine": _clamp(_to_float(st.get("acetylcholine"), 0.5)),
        "glutamate":     _clamp(_to_float(st.get("glutamate_drive", st.get("glutamate")), 0.5)),
        "gaba":          _clamp(_to_float(st.get("gaba_drive", st.get("gaba")), 0.3)),
    }


def _read_recent_l2m(con: sqlite3.Connection, n: int = 8) -> List[Dict[str, Any]]:
    if not _table_exists(con, "phase6b_l2m_metrics"):
        return []
    rows = con.execute(
        "SELECT cycle_index, performance_maintenance, forward_transfer, "
        " backward_transfer, sample_efficiency, performance_recovery, "
        " anchor_stability, alert_flag "
        "FROM phase6b_l2m_metrics ORDER BY id DESC LIMIT ?",
        (int(n),),
    ).fetchall()
    keys = ["cycle_index", "performance_maintenance", "forward_transfer",
            "backward_transfer", "sample_efficiency", "performance_recovery",
            "anchor_stability", "alert_flag"]
    return [dict(zip(keys, r)) for r in rows]


def _read_recent_effectiveness(con: sqlite3.Connection, n: int = 8) -> List[Dict[str, Any]]:
    if not _table_exists(con, "phase6b_effectiveness_events"):
        return []
    rows = con.execute(
        "SELECT cycle_index, delta_outcome, delta_closure, delta_overlap, "
        " effectiveness_score, plateau_flag, anchor_consistency "
        "FROM phase6b_effectiveness_events ORDER BY id DESC LIMIT ?",
        (int(n),),
    ).fetchall()
    keys = ["cycle_index", "delta_outcome", "delta_closure", "delta_overlap",
            "effectiveness_score", "plateau_flag", "anchor_consistency"]
    return [dict(zip(keys, r)) for r in rows]


def _analyze_history(l2m: List[Dict[str, Any]], eff: List[Dict[str, Any]]) -> Dict[str, float]:
    def avg(rows, key):
        vals = [_to_float(r.get(key)) for r in rows if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else 0.0

    plateau_ratio = 0.0
    if eff:
        plateau_ratio = sum(int(_to_int(r.get("plateau_flag"))) for r in eff) / len(eff)

    delta_variance = 0.0
    if len(eff) >= 2:
        deltas = [_to_float(r.get("delta_outcome")) for r in eff]
        mean = sum(deltas) / len(deltas)
        delta_variance = sum((d - mean) ** 2 for d in deltas) / len(deltas)

    return {
        "plateau_persistence":     plateau_ratio,
        "avg_effectiveness":       avg(eff, "effectiveness_score"),
        "avg_anchor_consistency":  avg(eff, "anchor_consistency"),
        "avg_performance_recovery": avg(l2m, "performance_recovery"),
        "avg_backward_transfer":   avg(l2m, "backward_transfer"),
        "avg_forward_transfer":    avg(l2m, "forward_transfer"),
        "avg_anchor_stability":    avg(l2m, "anchor_stability"),
        "delta_variance":          delta_variance,
    }


# =========================================================================
# Self-regulation
# =========================================================================

def _regulate_meta_parameters(con: sqlite3.Connection, cycle_index: int,
                              neuromod: Dict[str, float],
                              cfg: Dict[str, Dict[str, Any]],
                              hist: Dict[str, float]) -> Dict[str, Any]:
    """Adapt every meta-parameter based on its declared driver botenstoff
    and driver metric. Every change is logged."""
    changes: List[Dict[str, Any]] = []

    def _param_regulate(key: str, driver_metric_value: float,
                         direction_up_condition: bool,
                         direction_down_condition: bool,
                         up_reason: str, down_reason: str) -> None:
        p = cfg.get(key)
        if p is None:
            return
        bs_key = p["driver_botenstoff"]
        bs_val = neuromod.get(bs_key, 0.5)
        lr = p["learning_rate"]
        pre = p["current_value"]
        post = pre
        reason = "no_change"
        if direction_up_condition:
            post = pre + lr * bs_val
            reason = up_reason
        elif direction_down_condition:
            post = pre - lr * (1.0 - bs_val)
            reason = down_reason
        post = max(p["min_value"], min(p["max_value"], post))
        if abs(post - pre) > 1e-9:
            _set_meta_value(con, key, post)
            _log_regulation_event(con, cycle_index, key, pre, post,
                                  bs_key, bs_val,
                                  p["driver_metric"], driver_metric_value,
                                  reason)
            changes.append({"parameter": key, "pre": pre, "post": post,
                            "reason": reason, "driver_botenstoff": bs_key,
                            "botenstoff_value": bs_val,
                            "driver_metric_value": driver_metric_value})
            cfg[key]["current_value"] = post

    pr = hist["avg_performance_recovery"]
    pp = hist["plateau_persistence"]
    bt = hist["avg_backward_transfer"]
    ft = hist["avg_forward_transfer"]
    ac = hist["avg_anchor_consistency"]
    as_stab = hist["avg_anchor_stability"]
    eff = hist["avg_effectiveness"]
    dv = hist["delta_variance"]

    # plateau_break_scale: more aggressive (smaller) if recovery low
    _param_regulate("plateau_break_scale", pr,
                    direction_up_condition=(pr > 0.6),
                    direction_down_condition=(pr < 0.3 and pp > 0.7),
                    up_reason="high_recovery_less_aggressive",
                    down_reason="low_recovery_more_aggressive")

    # plateau_eps: shrink if delta_variance small (too easy to plateau)
    _param_regulate("plateau_eps", dv,
                    direction_up_condition=(dv > 0.005),
                    direction_down_condition=(dv < 0.0002 and pp > 0.8),
                    up_reason="high_variance_widen_threshold",
                    down_reason="low_variance_tighten_threshold")

    _param_regulate("exploration_delta", pp,
                    direction_up_condition=(pp > 0.7),
                    direction_down_condition=(pp < 0.3 and as_stab < 0.5),
                    up_reason="persistent_plateau_increase_exploration",
                    down_reason="stable_reduce_exploration")

    _param_regulate("inhibition_delta", pp,
                    direction_up_condition=(pp > 0.7),
                    direction_down_condition=(pp < 0.3),
                    up_reason="persistent_plateau_stronger_gaba_inhibition",
                    down_reason="no_plateau_relax_inhibition")

    _param_regulate("revision_delta", bt,
                    direction_up_condition=(bt > 0.01 and pp > 0.5),
                    direction_down_condition=(bt < -0.01),
                    up_reason="positive_bt_more_revision",
                    down_reason="negative_bt_less_revision")

    _param_regulate("consolidation_delta", eff,
                    direction_up_condition=(eff > 0.02),
                    direction_down_condition=(eff < -0.01),
                    up_reason="positive_effectiveness_more_consolidation",
                    down_reason="negative_effectiveness_less_consolidation")

    _param_regulate("stabilize_threshold", eff,
                    direction_up_condition=(eff > 0.05),
                    direction_down_condition=(eff < 0.0),
                    up_reason="high_effectiveness_raise_threshold",
                    down_reason="low_effectiveness_lower_threshold")

    _param_regulate("novel_ratio_base", ac,
                    direction_up_condition=(ac > 0.85),
                    direction_down_condition=(ac < 0.5),
                    up_reason="stable_anchors_more_novel",
                    down_reason="weak_anchors_more_replay_of_anchors")

    _param_regulate("novel_ratio_gaba_weight", pp,
                    direction_up_condition=(pp > 0.7),
                    direction_down_condition=(pp < 0.3),
                    up_reason="persistent_plateau_stronger_gaba_effect",
                    down_reason="stable_less_gaba_effect")

    _param_regulate("novel_ratio_na_weight", ft,
                    direction_up_condition=(ft > 0.01),
                    direction_down_condition=(ft < -0.01),
                    up_reason="positive_forward_transfer_boost_novelty",
                    down_reason="negative_forward_transfer_dampen_novelty")

    _param_regulate("critic_min_stable_base", bt,
                    direction_up_condition=(bt < -0.02),
                    direction_down_condition=(bt > 0.02),
                    up_reason="negative_bt_critic_wait_longer",
                    down_reason="positive_bt_critic_snapshot_sooner")

    _param_regulate("critic_snapshot_p_base", as_stab,
                    direction_up_condition=(as_stab > 0.8),
                    direction_down_condition=(as_stab < 0.4),
                    up_reason="stable_anchors_snapshot_more_often",
                    down_reason="unstable_anchors_snapshot_less_often")

    _param_regulate("critic_snapshot_p_range", as_stab,
                    direction_up_condition=(as_stab > 0.8),
                    direction_down_condition=(as_stab < 0.4),
                    up_reason="stable_anchors_wider_snapshot_range",
                    down_reason="unstable_anchors_narrower_snapshot_range")

    _param_regulate("gaba_novel_inhibition", pp,
                    direction_up_condition=(pp > 0.7),
                    direction_down_condition=(pp < 0.3),
                    up_reason="persistent_plateau_stronger_novel_inhibition",
                    down_reason="stable_less_novel_inhibition")

    con.commit()
    return {"adapted_count": len(changes), "changes": changes}


# =========================================================================
# Sticky bias persistence bridge
# =========================================================================

STICKY_KEYS = ("last_plasticity_level", "last_exploration_bias",
               "last_consolidation_bias", "last_inhibition_bias",
               "last_revision_bias")


def _save_sticky_bias(con: sqlite3.Connection) -> Dict[str, float]:
    """Read current bias values from phase6a_meta_plasticity_state
    and save them into phase6c_target_bias_state as the new target."""
    meta = _read_kv(con, "phase6a_meta_plasticity_state")
    saved = {}
    for k in STICKY_KEYS:
        if k in meta:
            v = _to_float(meta[k], 0.5)
            _kv_set(con, "phase6c_target_bias_state", k, round(v, 6))
            saved[k] = v
    con.commit()
    return saved


def _restore_sticky_bias(con: sqlite3.Connection) -> Dict[str, float]:
    """Overwrite phase6a_meta_plasticity_state AND
    phase6a_neuromodulated_sleep_state with values from
    phase6c_target_bias_state so that phase6a's next cycle starts
    from the phase6b-adapted bias, not from its own reset defaults."""
    target = _read_kv(con, "phase6c_target_bias_state")
    restored = {}
    for k in STICKY_KEYS:
        if k in target:
            v = _to_float(target[k], 0.5)
            _kv_set(con, "phase6a_meta_plasticity_state", k, round(v, 6))
            _kv_set(con, "phase6a_neuromodulated_sleep_state", k, round(v, 6))
            restored[k] = v
    con.commit()
    return restored


# =========================================================================
# Self-regulated replay batch selection
# =========================================================================

def _select_replay_batch_v2(con, neuromod, cfg, batch_size=180):
    gaba = neuromod["gaba"]
    na = neuromod["noradrenaline"]
    base = _get_meta_value(cfg, "novel_ratio_base", 0.6)
    gw = _get_meta_value(cfg, "novel_ratio_gaba_weight", 0.3)
    nw = _get_meta_value(cfg, "novel_ratio_na_weight", 0.2)
    novel_ratio = _clamp(base - gw * gaba + nw * na, 0.3, 0.9)
    n_anchor = int(batch_size * (1.0 - novel_ratio))
    n_novel = batch_size - n_anchor

    now = _now()
    anchors = con.execute(
        "SELECT id, source_table, source_id, stability_score "
        "FROM phase6b_anchor_pool WHERE active=1 "
        "ORDER BY stability_score DESC, last_replayed_at ASC LIMIT ?",
        (n_anchor,),
    ).fetchall()

    novel = []
    if _table_exists(con, "phase5g_experiment_outcomes"):
        ncols = set(_columns(con, "phase5g_experiment_outcomes"))
        id_col = "id" if "id" in ncols else "rowid"
        score_col = "outcome_score" if "outcome_score" in ncols else None
        sql = "SELECT " + id_col + " FROM phase5g_experiment_outcomes "
        if score_col:
            sql += "ORDER BY " + score_col + " ASC LIMIT ?"
        else:
            sql += "ORDER BY " + id_col + " DESC LIMIT ?"
        raw = con.execute(sql, (int(n_novel * 3),)).fetchall()
        inhibit_strength = _get_meta_value(cfg, "gaba_novel_inhibition", 0.5)
        rnd = random.Random(now)
        for r in raw:
            if rnd.random() < gaba * inhibit_strength:
                continue
            novel.append(_to_int(r[0]))
            if len(novel) >= n_novel:
                break

    if anchors:
        anchor_ids = [a[0] for a in anchors]
        placeholders = ",".join("?" for _ in anchor_ids)
        con.execute(
            "UPDATE phase6b_anchor_pool "
            "SET replay_count = COALESCE(replay_count,0) + 1, "
            "    last_replayed_at = ?, updated_at = ? "
            "WHERE id IN (" + placeholders + ")",
            [now, now] + anchor_ids,
        )
    con.commit()

    return {
        "batch_size": batch_size,
        "novel_ratio_target": round(novel_ratio, 3),
        "anchor_count": len(anchors),
        "novel_count": len(novel),
        "anchor_ids": [a[0] for a in anchors],
        "novel_ids": novel,
    }


def _measure_effectiveness_v2(con, recent, batch, neuromod, cycle_index, cfg, window_size=5):
    if len(recent) >= 2:
        cur = recent[0]
        prev_window = recent[1:1 + window_size]
    else:
        cur = recent[0] if recent else {}
        prev_window = []

    def _avg(rows, key):
        vals = [_to_float(r.get(key), None) for r in rows]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else 0.0

    pre_o = _avg(prev_window, "avg_outcome_score")
    pre_c = _avg(prev_window, "avg_closure_delta")
    pre_ov = _avg(prev_window, "avg_overlap_score")
    post_o = _to_float(cur.get("avg_outcome_score"), pre_o)
    post_c = _to_float(cur.get("avg_closure_delta"), pre_c)
    post_ov = _to_float(cur.get("avg_overlap_score"), pre_ov)

    d_o = post_o - pre_o
    d_c = post_c - pre_c
    d_ov = post_ov - pre_ov

    da = neuromod["dopamine"]
    na = neuromod["noradrenaline"]
    ach = neuromod["acetylcholine"]
    w_out = 0.5 + 0.3 * da
    w_clo = 0.3 + 0.2 * na
    w_ovl = 0.2 + 0.2 * ach
    eff = w_out * d_o + w_clo * d_c + w_ovl * d_ov

    eps = _get_meta_value(cfg, "plateau_eps", 0.005)
    plateau = 1 if (abs(d_o) < eps and abs(d_c) < eps and abs(d_ov) < eps) else 0

    row = con.execute(
        "SELECT AVG(stability_score) FROM phase6b_anchor_pool WHERE active=1"
    ).fetchone()
    anchor_stab = _to_float(row[0] if row else 0.0, 0.0)

    notes = json.dumps({
        "novel_ratio_target": batch.get("novel_ratio_target"),
        "anchor_count": batch.get("anchor_count"),
        "novel_count": batch.get("novel_count"),
        "plateau_eps": eps,
        "phase6c_managed": True,
    })

    con.execute(
        "INSERT INTO phase6b_effectiveness_events ("
        "created_at, cycle_index, window_size, replay_batch_size, "
        "novel_count, anchor_count, "
        "pre_outcome_score, post_outcome_score, "
        "pre_closure_delta, post_closure_delta, "
        "pre_overlap_score, post_overlap_score, "
        "delta_outcome, delta_closure, delta_overlap, "
        "effectiveness_score, plateau_flag, critic_penalty, anchor_consistency, "
        "dopamine, serotonin, noradrenaline, acetylcholine, glutamate, gaba, "
        "notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), cycle_index, window_size, batch.get("batch_size", 0),
         batch.get("novel_count", 0), batch.get("anchor_count", 0),
         pre_o, post_o, pre_c, post_c, pre_ov, post_ov,
         d_o, d_c, d_ov, eff, plateau, 0.0, anchor_stab,
         neuromod["dopamine"], neuromod["serotonin"], neuromod["noradrenaline"],
         neuromod["acetylcholine"], neuromod["glutamate"], neuromod["gaba"],
         notes),
    )
    con.commit()
    return {
        "cycle_index": cycle_index,
        "window_size": window_size,
        "pre_outcome_score": pre_o, "post_outcome_score": post_o,
        "pre_closure_delta": pre_c, "post_closure_delta": post_c,
        "pre_overlap_score": pre_ov, "post_overlap_score": post_ov,
        "delta_outcome": d_o, "delta_closure": d_c, "delta_overlap": d_ov,
        "effectiveness_score": eff, "plateau_flag": plateau,
        "anchor_consistency": anchor_stab,
        "plateau_eps_used": eps,
    }


def _apply_self_regulated_adjustment(con, eff, neuromod, meta_state, cfg):
    """Applies plasticity adjustment with all deltas coming from cfg
    (self-regulated). Uses phase6b._critic_gate for gating."""
    pre_plast = _to_float(meta_state.get("last_plasticity_level"), 0.5)
    pre_expl  = _to_float(meta_state.get("last_exploration_bias"), 0.5)
    pre_cons  = _to_float(meta_state.get("last_consolidation_bias"), 0.5)
    pre_inh   = _to_float(meta_state.get("last_inhibition_bias"), 0.3)
    pre_rev   = _to_float(meta_state.get("last_revision_bias"), 0.5)

    da = neuromod["dopamine"]; sero = neuromod["serotonin"]
    na = neuromod["noradrenaline"]; ach = neuromod["acetylcholine"]
    glu = neuromod["glutamate"]; gaba = neuromod["gaba"]

    plateau = int(eff.get("plateau_flag", 0))
    eff_score = _to_float(eff.get("effectiveness_score"), 0.0)

    plateau_scale     = _get_meta_value(cfg, "plateau_break_scale", 0.85)
    exp_delta         = _get_meta_value(cfg, "exploration_delta",   0.15)
    inh_delta         = _get_meta_value(cfg, "inhibition_delta",    0.10)
    rev_delta         = _get_meta_value(cfg, "revision_delta",      0.10)
    cons_delta        = _get_meta_value(cfg, "consolidation_delta", 0.05)
    stab_threshold    = _get_meta_value(cfg, "stabilize_threshold", 0.02)

    post_plast, post_expl, post_cons, post_inh, post_rev = (
        pre_plast, pre_expl, pre_cons, pre_inh, pre_rev
    )
    reason_parts = []
    adj_type = "no_change"
    scale = 1.0

    if plateau == 1:
        adj_type = "plateau_break"
        # scale is now derived from meta-param, still gaba-modulated
        scale = _clamp(plateau_scale - 0.10 * gaba, 0.55, 0.98)
        post_plast = _clamp(pre_plast * scale)
        post_expl  = _clamp(pre_expl + exp_delta * (1.0 - gaba) + 0.05 * na)
        post_inh   = _clamp(pre_inh + inh_delta * gaba + 0.05 * (1.0 - da))
        post_rev   = _clamp(pre_rev + rev_delta * sero + 0.05 * ach)
        post_cons  = _clamp(pre_cons - 0.05 * (1.0 - eff_score))
        reason_parts.append("plateau_break_self_regulated")
    elif eff_score > stab_threshold:
        adj_type = "stabilize_gains"
        post_cons  = _clamp(pre_cons + cons_delta * da + 0.05 * glu)
        post_rev   = _clamp(pre_rev - 0.03 * sero)
        post_plast = _clamp(pre_plast + 0.02 * da)
        reason_parts.append("stabilize_positive_effectiveness")
    else:
        adj_type = "hold"
        reason_parts.append("hold_within_normal_variance")

    # Critic gate from 6b module
    try:
        from ki_system import v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release as p6b
        proposed = {
            "plasticity_level": post_plast, "exploration_bias": post_expl,
            "consolidation_bias": post_cons, "inhibition_bias": post_inh,
            "revision_bias": post_rev,
        }
        anchor_cons = _to_float(eff.get("anchor_consistency"), 0.0)
        allowed, penalty, critic_reason = p6b._critic_gate(con, proposed, anchor_cons)
    except Exception as exc:
        allowed, penalty, critic_reason = True, 0.0, "critic_unavailable:" + str(exc)

    if not allowed:
        post_plast, post_expl, post_cons, post_inh, post_rev = (
            pre_plast, pre_expl, pre_cons, pre_inh, pre_rev
        )
        reason_parts.append("critic_rejected:" + critic_reason)
        adj_type = "critic_rejected"
    elif penalty > 0.0:
        def _blend(pre, post):
            return _clamp(pre + (post - pre) * (1.0 - penalty))
        post_plast = _blend(pre_plast, post_plast)
        post_expl  = _blend(pre_expl,  post_expl)
        post_cons  = _blend(pre_cons,  post_cons)
        post_inh   = _blend(pre_inh,   post_inh)
        post_rev   = _blend(pre_rev,   post_rev)
        reason_parts.append("critic_scaled:" + critic_reason)

    reason = ";".join(reason_parts) if reason_parts else "n/a"

    con.execute(
        "INSERT INTO phase6b_plasticity_adjustments ("
        "created_at, cycle_index, adjustment_type, reason, scale_factor, "
        "window_size, "
        "pre_plasticity_level, post_plasticity_level, "
        "pre_exploration_bias, post_exploration_bias, "
        "pre_consolidation_bias, post_consolidation_bias, "
        "pre_inhibition_bias, post_inhibition_bias, "
        "pre_revision_bias, post_revision_bias, "
        "dopamine, serotonin, noradrenaline, acetylcholine, glutamate, gaba, "
        "critic_gate_result, notes) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), int(eff.get("cycle_index", 0)), adj_type, reason, scale,
         int(eff.get("window_size", 5)),
         pre_plast, post_plast, pre_expl, post_expl,
         pre_cons, post_cons, pre_inh, post_inh, pre_rev, post_rev,
         da, sero, na, ach, glu, gaba,
         critic_reason,
         json.dumps({"eff": eff_score, "plateau": plateau,
                     "cfg_plateau_scale": plateau_scale,
                     "cfg_exp_delta": exp_delta,
                     "cfg_inh_delta": inh_delta,
                     "cfg_rev_delta": rev_delta,
                     "cfg_cons_delta": cons_delta,
                     "cfg_stab_th": stab_threshold})),
    )

    if allowed:
        for k, v in (
            ("last_plasticity_level",  post_plast),
            ("last_exploration_bias",  post_expl),
            ("last_consolidation_bias", post_cons),
            ("last_inhibition_bias",   post_inh),
            ("last_revision_bias",     post_rev),
        ):
            _kv_set(con, "phase6a_meta_plasticity_state", k, round(v, 6))
            _kv_set(con, "phase6a_neuromodulated_sleep_state", k, round(v, 6))

    con.commit()
    return {
        "adjustment_type": adj_type,
        "scale_factor": scale,
        "pre":  {"plasticity_level": pre_plast,  "exploration_bias": pre_expl,
                 "consolidation_bias": pre_cons, "inhibition_bias": pre_inh,
                 "revision_bias": pre_rev},
        "post": {"plasticity_level": post_plast, "exploration_bias": post_expl,
                 "consolidation_bias": post_cons, "inhibition_bias": post_inh,
                 "revision_bias": post_rev},
        "critic_gate_result": critic_reason,
        "critic_penalty": penalty,
    }


def _maybe_snapshot_critic_v2(con, neuromod, eff_score, adj, cfg):
    sero = neuromod["serotonin"]
    p_base = _get_meta_value(cfg, "critic_snapshot_p_base", 0.05)
    p_range = _get_meta_value(cfg, "critic_snapshot_p_range", 0.5)
    min_base = _get_meta_value(cfg, "critic_min_stable_base", 3.0)
    p = _clamp(p_base + p_range * sero, 0.02, 0.85)

    stable_count = _to_int(_read_kv(con, "phase6c_state").get("stable_cycles_since_critic_snapshot"), 0)
    if eff_score >= 0.0 and adj.get("adjustment_type") != "critic_rejected":
        stable_count += 1
    _kv_set(con, "phase6c_state", "stable_cycles_since_critic_snapshot", stable_count)

    # min_stable adaptively derived from serotonin as well
    min_stable = max(2, int(round(min_base + (1.0 - sero) * 4)))
    if stable_count < min_stable:
        con.commit()
        return {"snapshot": False, "reason": "not_enough_stable_cycles",
                "stable_cycles": stable_count, "min_required": min_stable,
                "probability": p}

    rnd = random.random()
    if rnd > p:
        con.commit()
        return {"snapshot": False, "reason": "probabilistic_skip",
                "probability": p, "roll": rnd}

    con.execute("UPDATE phase6b_critic_snapshot SET active=0 WHERE active=1")
    row = con.execute(
        "SELECT COUNT(*) FROM phase6b_anchor_pool WHERE active=1"
    ).fetchone()
    anchor_count = _to_int(row[0] if row else 0, 0)
    state_dump = json.dumps({"eff_score": eff_score,
                             "adjustment": adj.get("adjustment_type"),
                             "neuromod": neuromod,
                             "phase6c_managed": True})
    post = adj.get("post", {})
    con.execute(
        "INSERT INTO phase6b_critic_snapshot ("
        "created_at, reason, dopamine, serotonin, noradrenaline, "
        "acetylcholine, glutamate, gaba, plasticity_level, "
        "exploration_bias, consolidation_bias, inhibition_bias, revision_bias, "
        "anchor_count, effectiveness_avg, state_json, active) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (_now(), "phase6c_self_regulated_snapshot",
         neuromod["dopamine"], neuromod["serotonin"], neuromod["noradrenaline"],
         neuromod["acetylcholine"], neuromod["glutamate"], neuromod["gaba"],
         _to_float(post.get("plasticity_level")),
         _to_float(post.get("exploration_bias")),
         _to_float(post.get("consolidation_bias")),
         _to_float(post.get("inhibition_bias")),
         _to_float(post.get("revision_bias")),
         anchor_count, eff_score, state_dump),
    )
    _kv_set(con, "phase6c_state", "stable_cycles_since_critic_snapshot", 0)
    con.commit()
    return {"snapshot": True, "reason": "phase6c_self_regulated",
            "probability": p, "anchor_count": anchor_count,
            "stable_cycles_since_previous": stable_count,
            "min_required": min_stable}


# =========================================================================
# Main cycle
# =========================================================================

def run_phase6c_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj)
    ensure_schema(con)
    missing = _self_check_schema(con)
    if missing:
        return {"phase": PHASE, "status": "schema_check_failed",
                "missing_columns": missing}

    initialize_meta_parameters(con)

    if cycle_index is None:
        cur_count = _to_int(_read_kv(con, "phase6c_state").get("cycle_count"), 0)
        cycle_index = cur_count + 1

    # Step 1: restore sticky bias BEFORE 6a runs, so 6a starts from adapted values
    restored_pre = _restore_sticky_bias(con)

    # Step 2: run 6a (wake+sleep). Ignore errors so we can still learn.
    base6a_result = None
    try:
        from ki_system import v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release as p6a
        base6a_result = {'status': 'phase6a_replay_already_completed_by_phase7b1', 'skipped': True}
    except Exception as exc:
        base6a_result = {"phase6a_error": str(exc)}

    # Step 3: restore sticky bias AGAIN, overriding 6a's reset
    restored_post = _restore_sticky_bias(con)

    # Step 4: neuromodulators and meta cfg
    neuromod = _read_neuromodulators(con)
    cfg = _get_all_meta_params(con)

    # Step 5: promote anchors (delegate to 6b)
    anchors_promoted = {"error": "phase6b_missing"}
    recent = []
    try:
        from ki_system import v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release as p6b
        anchors_promoted = p6b._promote_anchors(con)
        recent = p6b._read_recent_cycles(con, 20)
    except Exception as exc:
        anchors_promoted = {"phase6b_promote_error": str(exc)}

    # Step 6: self-regulated batch + effectiveness + adjustment
    batch = _select_replay_batch_v2(con, neuromod, cfg)
    eff = _measure_effectiveness_v2(con, recent, batch, neuromod, cycle_index, cfg)
    meta_state = _read_kv(con, "phase6a_meta_plasticity_state")
    adj = _apply_self_regulated_adjustment(con, eff, neuromod, meta_state, cfg)

    # Step 7: save sticky bias (now containing the phase6c-adjusted post values)
    saved = _save_sticky_bias(con)

    # Step 8: l2m + distill + critic snapshot
    l2m = {"skipped": True}
    dist = {"skipped": True}
    try:
        from ki_system import v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release as p6b
        l2m = p6b._compute_l2m_metrics(con, cycle_index, eff)
        dist = p6b._distill_knowledge(con, cycle_index, eff.get("effectiveness_score", 0.0))
    except Exception as exc:
        l2m = {"phase6b_l2m_error": str(exc)}
    snap = _maybe_snapshot_critic_v2(con, neuromod, eff.get("effectiveness_score", 0.0), adj, cfg)

    # Step 9: self-regulate meta parameters based on all fresh history
    l2m_hist = _read_recent_l2m(con, 8)
    eff_hist = _read_recent_effectiveness(con, 8)
    hist = _analyze_history(l2m_hist, eff_hist)
    regulated = _regulate_meta_parameters(con, cycle_index, neuromod, cfg, hist)

    # Step 10: state + safety
    _kv_set(con, "phase6c_state", "cycle_count", cycle_index)
    _kv_set(con, "phase6c_state", "last_cycle_at", _now())
    _kv_set(con, "phase6c_state", "phase", PHASE)
    _kv_set(con, "phase6c_state", "phase_version", PHASE_VERSION)
    _kv_set(con, "phase6c_state", "learning_mode", LEARNING_MODE)
    _kv_set(con, "phase6c_state", "no_word_blacklists", True)
    _kv_set(con, "phase6c_state", "direct_fact_writes", "disabled")
    _kv_set(con, "phase6c_state", "direct_relation_writes", "disabled")
    _kv_set(con, "phase6c_state", "fact_promotion", "disabled")
    _kv_set(con, "phase6c_state", "self_regulating_meta_parameters", True)
    _kv_set(con, "phase6c_state", "question_generation", "internal_learning_questions_only")

    con.commit()

    return {
        "phase": PHASE,
        "cycle_index": cycle_index,
        "status": "ok",
        "restored_sticky_bias_pre":  restored_pre,
        "restored_sticky_bias_post": restored_post,
        "phase6a_result_summary": (
            "ok" if isinstance(base6a_result, dict) and "phase6a_error" not in base6a_result
            else base6a_result
        ),
        "anchors_promoted": anchors_promoted,
        "replay_batch": {"batch_size": batch.get("batch_size"),
                         "novel_count": batch.get("novel_count"),
                         "anchor_count": batch.get("anchor_count"),
                         "novel_ratio_target": batch.get("novel_ratio_target")},
        "effectiveness": eff,
        "plasticity_adjustment": adj,
        "saved_sticky_bias": saved,
        "l2m_metrics": l2m,
        "distilled": dist,
        "critic_snapshot": snap,
        "meta_regulation": regulated,
        "history_snapshot": hist,
        "safety": {"direct_fact_writes": "disabled",
                   "direct_relation_writes": "disabled",
                   "fact_promotion": "disabled",
                   "no_word_blacklists": True,
                   "self_regulating_meta_parameters": True},
    }


# =========================================================================
# AutonomousLoop integration
# =========================================================================

def managed_cycle(self, progress=None):
    try:
        db = resolve_db(self)
        result = run_phase6c_cycle(db)
    except Exception as exc:
        result = {"status": "phase6c_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "phase6c_result": result}


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
    AutonomousLoop.phase6c_bias_persistence_and_self_regulating_meta_release = True
    AutonomousLoop._phase6c_bias_persistence_and_self_regulating_meta_release = True
    AutonomousLoop.phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release = True
    AutonomousLoop.phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"
    AutonomousLoop.direct_relation_writes = "disabled"
    AutonomousLoop.self_regulating_meta_parameters = True
    return AutonomousLoop
