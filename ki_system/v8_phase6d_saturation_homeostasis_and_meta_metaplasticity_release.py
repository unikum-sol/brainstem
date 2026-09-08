# -*- coding: utf-8 -*-
"""
V8 Phase 6d - Saturation Homeostasis and Meta-Metaplasticity Release

Project compass:
    - No blacklist / filter system.
    - No direct facts / relations / questions writes.
    - No fact promotion.
    - Digital neuromodulators steer the WHOLE learning process.
    - Meta parameters are self-regulating.
    - This phase adds the missing counter-force: sliding-threshold /
      synaptic scaling / meta-metaplasticity so the self-regulation
      cannot run into permanent saturation.

Purpose of phase6d:
    (1) Detect when bias values (phase6a) or meta control parameters
        (phase6c) get stuck at their min/max boundaries.
    (2) Apply sliding-threshold homeostasis (Lee and Kirkwood 2019):
        if a parameter moved only in one direction for N cycles, the
        counter-direction is made easier next time.
    (3) Meta-metaplasticity: adapt the learning_rate of each meta
        parameter based on saturation (dampen if nervous, boost if
        stable).
    (4) Controlled bias renormalization (Bazhenov slow-wave downscaling):
        when saturation + effectiveness=0 co-occur, pull the saturated
        bias values gently back toward mid-range.
    (5) Critic-lock protection: a critic snapshot must not carry any
        bias at the boundary; such snapshots are refused.

Safety:
    - SCHEMA_TABLES is single source of truth for ALL columns.
    - ensure_schema() adds missing tables and columns idempotently.
    - _self_check_schema() aborts before any write on missing columns.
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

PHASE = "phase6d_saturation_homeostasis_and_meta_metaplasticity_release"
PHASE_VERSION = "phase6d_v1"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


# =========================================================================
# SCHEMA
# =========================================================================

SCHEMA_TABLES = {
    "phase6d_state": [
        ("key",        "TEXT PRIMARY KEY"),
        ("value",      "TEXT"),
        ("updated_at", "INTEGER"),
    ],
    "phase6d_meta_metaplasticity_state": [
        ("parameter_key",     "TEXT PRIMARY KEY"),
        ("kind",              "TEXT"),
        ("current_lr",        "REAL"),
        ("default_lr",        "REAL"),
        ("min_lr",            "REAL"),
        ("max_lr",            "REAL"),
        ("direction_bias",    "REAL"),
        ("saturation_count",  "INTEGER DEFAULT 0"),
        ("last_direction",    "TEXT"),
        ("last_value",        "REAL"),
        ("description",       "TEXT"),
        ("created_at",        "INTEGER"),
        ("updated_at",        "INTEGER"),
    ],
    "phase6d_saturation_events": [
        ("id",                       "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",               "INTEGER"),
        ("cycle_index",              "INTEGER"),
        ("target_kind",              "TEXT"),
        ("target_key",               "TEXT"),
        ("value",                    "REAL"),
        ("threshold_side",           "TEXT"),
        ("saturation_streak",        "INTEGER"),
        ("action_taken",             "TEXT"),
        ("reason",                   "TEXT"),
        ("driver_botenstoff",        "TEXT"),
        ("driver_botenstoff_value",  "REAL"),
    ],
    "phase6d_bias_reset_events": [
        ("id",                       "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",               "INTEGER"),
        ("cycle_index",              "INTEGER"),
        ("bias_key",                 "TEXT"),
        ("pre_value",                "REAL"),
        ("post_value",               "REAL"),
        ("scale_factor",             "REAL"),
        ("reason",                   "TEXT"),
        ("driver_botenstoff",        "TEXT"),
        ("driver_botenstoff_value",  "REAL"),
    ],
}

SCHEMA_INDEXES = [
    ("idx_phase6d_saturation_cyc",  "phase6d_saturation_events",  "cycle_index"),
    ("idx_phase6d_saturation_key",  "phase6d_saturation_events",  "target_key"),
    ("idx_phase6d_bias_reset_cyc",  "phase6d_bias_reset_events",  "cycle_index"),
    ("idx_phase6d_bias_reset_key",  "phase6d_bias_reset_events",  "bias_key"),
]


BIAS_KEYS = (
    "last_plasticity_level",
    "last_exploration_bias",
    "last_consolidation_bias",
    "last_inhibition_bias",
    "last_revision_bias",
)


META_LR_DEFAULTS = [
    ("plateau_break_scale",       "meta_param", 0.05, 0.01, 0.2,  "6c: aggressiveness of plateau_break"),
    ("plateau_eps",               "meta_param", 0.05, 0.01, 0.2,  "6c: plateau detection epsilon"),
    ("exploration_delta",         "meta_param", 0.05, 0.01, 0.2,  "6c: exploration boost delta"),
    ("inhibition_delta",          "meta_param", 0.05, 0.01, 0.2,  "6c: GABA inhibition delta"),
    ("revision_delta",            "meta_param", 0.05, 0.01, 0.2,  "6c: serotonin revision delta"),
    ("consolidation_delta",       "meta_param", 0.05, 0.01, 0.2,  "6c: consolidation delta"),
    ("stabilize_threshold",       "meta_param", 0.05, 0.01, 0.2,  "6c: stabilize_gains threshold"),
    ("novel_ratio_base",          "meta_param", 0.05, 0.01, 0.2,  "6c: novel batch ratio base"),
    ("novel_ratio_gaba_weight",   "meta_param", 0.05, 0.01, 0.2,  "6c: GABA weight in novel_ratio"),
    ("novel_ratio_na_weight",     "meta_param", 0.05, 0.01, 0.2,  "6c: NA weight in novel_ratio"),
    ("critic_min_stable_base",    "meta_param", 0.05, 0.01, 0.2,  "6c: critic min stable base"),
    ("critic_snapshot_p_base",    "meta_param", 0.05, 0.01, 0.2,  "6c: critic snapshot p base"),
    ("critic_snapshot_p_range",   "meta_param", 0.05, 0.01, 0.2,  "6c: critic snapshot p range"),
    ("gaba_novel_inhibition",     "meta_param", 0.05, 0.01, 0.2,  "6c: GABA novel inhibition strength"),
    ("last_plasticity_level",     "bias", 0.08, 0.02, 0.25, "6a: plasticity level"),
    ("last_exploration_bias",     "bias", 0.08, 0.02, 0.25, "6a: exploration bias"),
    ("last_consolidation_bias",   "bias", 0.08, 0.02, 0.25, "6a: consolidation bias"),
    ("last_inhibition_bias",      "bias", 0.08, 0.02, 0.25, "6a: inhibition bias"),
    ("last_revision_bias",        "bias", 0.08, 0.02, 0.25, "6a: revision bias"),
]


class SchemaCheckError(RuntimeError):
    pass


# =========================================================================
# Low-level helpers
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
    try:
        return float(x)
    except Exception:
        return default


def _to_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


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


def _read_neuromodulators(con):
    st = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    return {
        "dopamine":      _clamp(_to_float(st.get("dopamine"),      0.5)),
        "serotonin":     _clamp(_to_float(st.get("serotonin"),     0.5)),
        "noradrenaline": _clamp(_to_float(st.get("noradrenaline"), 0.5)),
        "acetylcholine": _clamp(_to_float(st.get("acetylcholine"), 0.5)),
        "glutamate":     _clamp(_to_float(st.get("glutamate_drive", st.get("glutamate")), 0.5)),
        "gaba":          _clamp(_to_float(st.get("gaba_drive", st.get("gaba")), 0.3)),
    }


def initialize_meta_metaplasticity_parameters(con):
    ensure_schema(con)
    now = _now()
    inserted = []
    for pk, kind, default_lr, min_lr, max_lr, desc in META_LR_DEFAULTS:
        row = con.execute(
            "SELECT current_lr FROM phase6d_meta_metaplasticity_state WHERE parameter_key=?",
            (pk,),
        ).fetchone()
        if row is None:
            con.execute(
                "INSERT INTO phase6d_meta_metaplasticity_state "
                "(parameter_key, kind, current_lr, default_lr, min_lr, max_lr, "
                " direction_bias, saturation_count, last_direction, last_value, "
                " description, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pk, kind, default_lr, default_lr, min_lr, max_lr,
                 0.0, 0, "none", 0.0, desc, now, now),
            )
            inserted.append(pk)
    con.commit()
    return {"inserted": inserted, "total": len(META_LR_DEFAULTS)}


# =========================================================================
# Saturation detection and sliding-threshold updates
# =========================================================================

SATURATION_STREAK_THRESHOLD = 3
BOUNDARY_TOLERANCE = 1e-4


def _current_values_for_key(con, key, kind):
    if kind == "meta_param":
        if not _table_exists(con, "phase6c_meta_control_parameters"):
            return None
        row = con.execute(
            "SELECT current_value, min_value, max_value "
            "FROM phase6c_meta_control_parameters WHERE parameter_key=?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return (_to_float(row[0]), _to_float(row[1]), _to_float(row[2]))
    elif kind == "bias":
        val = _read_kv(con, "phase6a_meta_plasticity_state").get(key)
        if val is None:
            return None
        return (_to_float(val), 0.0, 1.0)
    return None


def _boundary_side(value, lo, hi):
    if value <= lo + BOUNDARY_TOLERANCE:
        return "min"
    if value >= hi - BOUNDARY_TOLERANCE:
        return "max"
    return None


def _detect_and_react_saturation(con, cycle_index, neuromod):
    now = _now()
    summary = {"saturation_events": [], "bias_resets_scheduled": []}

    for pk, kind, default_lr, min_lr, max_lr, _desc in META_LR_DEFAULTS:
        vals = _current_values_for_key(con, pk, kind)
        if vals is None:
            continue
        current, lo, hi = vals
        side = _boundary_side(current, lo, hi)

        row = con.execute(
            "SELECT current_lr, direction_bias, saturation_count, last_direction, last_value "
            "FROM phase6d_meta_metaplasticity_state WHERE parameter_key=?",
            (pk,),
        ).fetchone()
        if row is None:
            continue
        cur_lr = _to_float(row[0], default_lr)
        dir_bias = _to_float(row[1], 0.0)
        sat_count = _to_int(row[2], 0)
        last_dir = row[3] if row[3] else "none"
        last_val = _to_float(row[4], current)

        if current > last_val + 1e-9:
            cur_dir = "up"
        elif current < last_val - 1e-9:
            cur_dir = "down"
        else:
            cur_dir = "flat"

        action = "none"
        reason = ""
        driver_bs = "acetylcholine"
        driver_bs_val = neuromod.get(driver_bs, 0.5)

        if side is not None:
            new_streak = sat_count + 1 if last_dir != "counter" else max(0, sat_count - 1)
            if new_streak >= SATURATION_STREAK_THRESHOLD:
                new_lr = _clamp(cur_lr * (0.7 + 0.2 * neuromod.get("serotonin", 0.5)),
                                min_lr, max_lr)
                target_dir_bias = -0.5 if side == "max" else 0.5
                new_dir_bias = _clamp(dir_bias * 0.5 + target_dir_bias * 0.5, -1.0, 1.0)
                con.execute(
                    "UPDATE phase6d_meta_metaplasticity_state "
                    "SET current_lr=?, direction_bias=?, saturation_count=?, "
                    "    last_direction=?, last_value=?, updated_at=? "
                    "WHERE parameter_key=?",
                    (new_lr, new_dir_bias, new_streak, "counter",
                     float(current), now, pk),
                )
                action = "sliding_threshold_applied"
                reason = ("boundary_" + side + "_streak_" + str(new_streak) +
                          "_lr_" + str(round(cur_lr, 4)) + "_to_" + str(round(new_lr, 4)) +
                          "_dir_bias_" + str(round(new_dir_bias, 3)))
                if kind == "bias" and new_streak >= SATURATION_STREAK_THRESHOLD + 1:
                    summary["bias_resets_scheduled"].append({
                        "key": pk, "value": current, "side": side,
                        "streak": new_streak,
                    })
            else:
                con.execute(
                    "UPDATE phase6d_meta_metaplasticity_state "
                    "SET saturation_count=?, last_direction=?, last_value=?, updated_at=? "
                    "WHERE parameter_key=?",
                    (new_streak, cur_dir, float(current), now, pk),
                )
                action = "streak_incremented"
                reason = "boundary_" + side + "_streak_" + str(new_streak)
            con.execute(
                "INSERT INTO phase6d_saturation_events "
                "(created_at, cycle_index, target_kind, target_key, value, "
                " threshold_side, saturation_streak, action_taken, reason, "
                " driver_botenstoff, driver_botenstoff_value) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (now, int(cycle_index), kind, pk, float(current),
                 side, new_streak, action, reason,
                 driver_bs, float(driver_bs_val)),
            )
            summary["saturation_events"].append({
                "parameter": pk, "kind": kind, "value": current,
                "side": side, "streak": new_streak, "action": action,
            })
        else:
            if sat_count > 0 or cur_lr < default_lr:
                restore_lr = _clamp(cur_lr + (default_lr - cur_lr) * 0.2,
                                    min_lr, max_lr)
                new_dir_bias = dir_bias * 0.8
                con.execute(
                    "UPDATE phase6d_meta_metaplasticity_state "
                    "SET current_lr=?, direction_bias=?, saturation_count=?, "
                    "    last_direction=?, last_value=?, updated_at=? "
                    "WHERE parameter_key=?",
                    (restore_lr, new_dir_bias, 0, cur_dir, float(current), now, pk),
                )
            else:
                con.execute(
                    "UPDATE phase6d_meta_metaplasticity_state "
                    "SET last_direction=?, last_value=?, updated_at=? "
                    "WHERE parameter_key=?",
                    (cur_dir, float(current), now, pk),
                )

    con.commit()
    return summary


# =========================================================================
# Bias renormalization
# =========================================================================

MID_TARGETS = {
    "last_plasticity_level":   0.5,
    "last_exploration_bias":   0.5,
    "last_consolidation_bias": 0.5,
    "last_inhibition_bias":    0.35,
    "last_revision_bias":      0.5,
}


def _read_recent_effectiveness_zero_streak(con):
    if not _table_exists(con, "phase6b_effectiveness_events"):
        return 0
    rows = con.execute(
        "SELECT effectiveness_score, plateau_flag "
        "FROM phase6b_effectiveness_events ORDER BY id DESC LIMIT 10"
    ).fetchall()
    streak = 0
    for r in rows:
        eff = _to_float(r[0], 0.0)
        p = _to_int(r[1], 0)
        if abs(eff) < 1e-5 and p == 1:
            streak += 1
        else:
            break
    return streak


def _renormalize_bias(con, cycle_index, scheduled_resets, neuromod):
    if not scheduled_resets:
        return {"resets_done": 0, "reason": "no_scheduled_resets"}

    eff_zero_streak = _read_recent_effectiveness_zero_streak(con)
    if eff_zero_streak < 3:
        return {"resets_done": 0, "reason": "effectiveness_not_flat_enough",
                "eff_zero_streak": eff_zero_streak}

    now = _now()
    sero = neuromod.get("serotonin", 0.5)
    glu = neuromod.get("glutamate", 0.5)
    base_pull = 0.15 + 0.05 * min(5, eff_zero_streak - 3)
    pull = _clamp(base_pull * (0.6 + 0.6 * glu) * (1.0 - 0.4 * sero), 0.05, 0.35)

    driver_bs = "glutamate"
    driver_bs_val = glu

    done = 0
    for item in scheduled_resets:
        key = item["key"]
        pre_val = _to_float(item["value"], 0.5)
        target = MID_TARGETS.get(key, 0.5)
        post_val = _clamp(pre_val + (target - pre_val) * pull)
        _kv_set(con, "phase6a_meta_plasticity_state", key, round(post_val, 6))
        _kv_set(con, "phase6a_neuromodulated_sleep_state", key, round(post_val, 6))
        _kv_set(con, "phase6c_target_bias_state", key, round(post_val, 6))
        con.execute(
            "INSERT INTO phase6d_bias_reset_events "
            "(created_at, cycle_index, bias_key, pre_value, post_value, "
            " scale_factor, reason, driver_botenstoff, driver_botenstoff_value) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (now, int(cycle_index), key, pre_val, post_val, pull,
             "saturation_plus_zero_effectiveness_streak_" + str(eff_zero_streak),
             driver_bs, float(driver_bs_val)),
        )
        done += 1

    con.commit()
    return {"resets_done": done, "pull": pull, "eff_zero_streak": eff_zero_streak}


# =========================================================================
# Critic-lock protection
# =========================================================================

def _protect_critic_from_boundary_snapshots(con, cycle_index):
    if not _table_exists(con, "phase6b_critic_snapshot"):
        return {"deactivated": 0, "reason": "no_critic_table"}
    row = con.execute(
        "SELECT snapshot_id, plasticity_level, exploration_bias, "
        "consolidation_bias, inhibition_bias, revision_bias "
        "FROM phase6b_critic_snapshot WHERE active=1 "
        "ORDER BY snapshot_id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return {"deactivated": 0, "reason": "no_active_snapshot"}
    snap_id = _to_int(row[0])
    vals = [_to_float(v) for v in row[1:]]
    at_boundary = any(v <= BOUNDARY_TOLERANCE or v >= 1.0 - BOUNDARY_TOLERANCE
                      for v in vals)
    if not at_boundary:
        return {"deactivated": 0, "reason": "critic_within_healthy_range",
                "snapshot_id": snap_id}
    con.execute(
        "UPDATE phase6b_critic_snapshot SET active=0 WHERE snapshot_id=?",
        (snap_id,),
    )
    _kv_set(con, "phase6d_state", "last_critic_lock_protection_at", _now())
    _kv_set(con, "phase6d_state", "last_critic_lock_snapshot_id", snap_id)
    con.commit()
    return {"deactivated": 1, "reason": "critic_had_boundary_bias",
            "snapshot_id": snap_id}


def _sync_learning_rates_to_phase6c(con):
    if not _table_exists(con, "phase6c_meta_control_parameters"):
        return {"synced": 0, "reason": "phase6c_missing"}
    synced = 0
    for pk, kind, _def_lr, _min_lr, _max_lr, _desc in META_LR_DEFAULTS:
        if kind != "meta_param":
            continue
        row = con.execute(
            "SELECT current_lr FROM phase6d_meta_metaplasticity_state WHERE parameter_key=?",
            (pk,),
        ).fetchone()
        if row is None:
            continue
        con.execute(
            "UPDATE phase6c_meta_control_parameters "
            "SET learning_rate=?, updated_at=? WHERE parameter_key=?",
            (_to_float(row[0]), _now(), pk),
        )
        synced += 1
    con.commit()
    return {"synced": synced}


# =========================================================================
# Main cycle
# =========================================================================

def run_phase6d_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj)
    ensure_schema(con)
    missing = _self_check_schema(con)
    if missing:
        return {"phase": PHASE, "status": "schema_check_failed",
                "missing_columns": missing}

    initialize_meta_metaplasticity_parameters(con)

    if cycle_index is None:
        cur_count = _to_int(_read_kv(con, "phase6d_state").get("cycle_count"), 0)
        cycle_index = cur_count + 1

    phase6c_result = None
    try:
        from ki_system import v8_phase6c_bias_persistence_and_self_regulating_meta_release as p6c
        phase6c_result = {'status': 'phase6c_already_completed_by_phase7b1', 'skipped': True}
    except Exception as exc:
        phase6c_result = {"phase6c_error": str(exc)}

    neuromod = _read_neuromodulators(con)
    sat_summary = _detect_and_react_saturation(con, cycle_index, neuromod)
    reset_summary = _renormalize_bias(con, cycle_index,
                                      sat_summary.get("bias_resets_scheduled", []),
                                      neuromod)
    sync_summary = _sync_learning_rates_to_phase6c(con)
    critic_protect = _protect_critic_from_boundary_snapshots(con, cycle_index)

    _kv_set(con, "phase6d_state", "cycle_count", cycle_index)
    _kv_set(con, "phase6d_state", "last_cycle_at", _now())
    _kv_set(con, "phase6d_state", "phase", PHASE)
    _kv_set(con, "phase6d_state", "phase_version", PHASE_VERSION)
    _kv_set(con, "phase6d_state", "learning_mode", LEARNING_MODE)
    _kv_set(con, "phase6d_state", "no_word_blacklists", True)
    _kv_set(con, "phase6d_state", "direct_fact_writes", "disabled")
    _kv_set(con, "phase6d_state", "direct_relation_writes", "disabled")
    _kv_set(con, "phase6d_state", "fact_promotion", "disabled")
    _kv_set(con, "phase6d_state", "saturation_homeostasis", True)
    _kv_set(con, "phase6d_state", "meta_metaplasticity", True)

    con.commit()

    return {
        "phase": PHASE,
        "cycle_index": cycle_index,
        "status": "ok",
        "phase6c_summary": (
            "ok" if isinstance(phase6c_result, dict) and phase6c_result.get("status") == "ok"
            else phase6c_result
        ),
        "saturation": sat_summary,
        "bias_renormalization": reset_summary,
        "phase6c_lr_sync": sync_summary,
        "critic_protection": critic_protect,
        "safety": {
            "direct_fact_writes": "disabled",
            "direct_relation_writes": "disabled",
            "fact_promotion": "disabled",
            "no_word_blacklists": True,
            "saturation_homeostasis": True,
            "meta_metaplasticity": True,
        },
    }


# =========================================================================
# AutonomousLoop integration
# =========================================================================

def managed_cycle(self, progress=None):
    try:
        db = resolve_db(self)
        result = run_phase6d_cycle(db)
    except Exception as exc:
        result = {"status": "phase6d_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "phase6d_result": result}


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
    AutonomousLoop.phase6d_saturation_homeostasis_and_meta_metaplasticity_release = True
    AutonomousLoop._phase6d_saturation_homeostasis_and_meta_metaplasticity_release = True
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
    return AutonomousLoop
