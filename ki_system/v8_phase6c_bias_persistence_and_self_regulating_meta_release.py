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













# =========================================================================
# Main cycle
# =========================================================================

def run_phase6c_cycle(db_or_obj=None, cycle_index=None):
    con=resolve_db(db_or_obj); ensure_schema(con); missing=_self_check_schema(con)
    if missing: return {"phase":PHASE,"status":"schema_check_failed","missing_columns":missing}
    initialize_meta_parameters(con)
    if cycle_index is None: cycle_index=_to_int(_read_kv(con,"phase6c_state").get("cycle_count"),0)+1
    latest=None
    if _table_exists(con,"phase6b_effectiveness_events"):
        cols=set(_columns(con,"phase6b_effectiveness_events")); wanted=[c for c in ("id","cycle_index","effectiveness_score","plateau_flag","anchor_consistency","evidence_state","outcome_observation_available","comparison_window_available") if c in cols]
        row=con.execute("SELECT "+",".join(wanted)+" FROM phase6b_effectiveness_events WHERE "+("measurement_owner='canonical_phase6b'" if "measurement_owner" in cols else "1=1")+" ORDER BY id DESC LIMIT 1").fetchone()
        if row: latest=dict(zip(wanted,row))
    l2m_hist=_read_recent_l2m(con,8); eff_hist=_read_recent_effectiveness(con,8); hist=_analyze_history(l2m_hist,eff_hist)
    state=str((latest or {}).get("evidence_state") or "historical_unclassified")
    if state in ("outcome_observed_change","outcome_observed_no_change"):
        neuromod=_read_neuromodulators(con); cfg=_get_all_meta_params(con); regulated=_regulate_meta_parameters(con,cycle_index,neuromod,cfg,hist)
    else:
        regulated={"regulated":0,"reason":"neutral_evidence_state","evidence_state":state}
    _kv_set(con,"phase6c_state","cycle_count",cycle_index); _kv_set(con,"phase6c_state","last_cycle_at",_now()); _kv_set(con,"phase6c_state","last_evidence_state",state); _kv_set(con,"phase6c_state","canonical_single_pass",True); _kv_set(con,"phase6c_state","direct_fact_writes","disabled"); _kv_set(con,"phase6c_state","direct_relation_writes","disabled"); _kv_set(con,"phase6c_state","fact_promotion","disabled"); con.commit()
    return {"phase":PHASE,"cycle_index":cycle_index,"status":"ok","canonical_phase6b_measurement":latest,"meta_regulation":regulated,"history_snapshot":hist,"safety":{"canonical_single_pass":True,"direct_fact_writes":"disabled","direct_relation_writes":"disabled","fact_promotion":"disabled"}}




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
