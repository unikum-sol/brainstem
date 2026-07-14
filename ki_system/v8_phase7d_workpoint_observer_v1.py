# -*- coding: utf-8 -*-
"""Phase 7d Workpoint Observer V1.

Observer only: records paired state, learns slow references from stable cycles,
and evaluates virtual proposals. It never applies pressure changes.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time

PHASE = "phase7d_workpoint_observer_v1"
APPLIED = False
_ORIG_CYCLE = None
_ORIG_RUN = None

SCHEMA_TABLES = {
    "phase7d_workpoint_observer_state": {
        "key": "TEXT PRIMARY KEY",
        "value": "TEXT",
        "updated_at": "INTEGER DEFAULT 0",
    },
    "phase7d_workpoint_observer_events": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "created_at": "INTEGER DEFAULT 0",
        "cycle_index": "INTEGER DEFAULT 0",
        "phase7d_event_id": "INTEGER DEFAULT 0",
        "glutamate": "REAL DEFAULT 0",
        "gaba": "REAL DEFAULT 0",
        "selection_pressure": "REAL DEFAULT 0",
        "adaptive_threshold": "REAL DEFAULT 0",
        "up_state_activity": "REAL DEFAULT 0",
        "survivor_ratio": "REAL DEFAULT 0",
        "candidates_participated": "INTEGER DEFAULT 0",
        "candidates_survived": "INTEGER DEFAULT 0",
        "pressure_reference": "REAL DEFAULT 0",
        "glutamate_reference": "REAL DEFAULT 0",
        "gaba_reference": "REAL DEFAULT 0",
        "activity_reference": "REAL DEFAULT 0",
        "survivor_reference": "REAL DEFAULT 0",
        "raw_signal": "REAL DEFAULT 0",
        "bounded_signal": "REAL DEFAULT 0",
        "persistent_signal": "REAL DEFAULT 0",
        "virtual_down_pressure": "REAL DEFAULT 0",
        "virtual_hold_pressure": "REAL DEFAULT 0",
        "virtual_up_pressure": "REAL DEFAULT 0",
        "limited_proposal": "REAL DEFAULT 0",
        "limited_delta": "REAL DEFAULT 0",
        "stable_reference_candidate": "INTEGER DEFAULT 0",
        "reference_updated": "INTEGER DEFAULT 0",
        "reference_freeze_reason": "TEXT",
        "cortisol_regime": "TEXT",
        "allostatic_load": "REAL DEFAULT 0",
        "stability_regime": "TEXT",
        "dominant_signal": "TEXT",
        "ei_saturation": "REAL DEFAULT 0",
        "applied": "INTEGER DEFAULT 0",
        "details": "TEXT",
    },
    "phase7d_workpoint_virtual_outcomes": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "created_at": "INTEGER DEFAULT 0",
        "source_event_id": "INTEGER DEFAULT 0",
        "target_event_id": "INTEGER DEFAULT 0",
        "proposal_kind": "TEXT",
        "proposed_pressure": "REAL DEFAULT 0",
        "predicted_direction": "REAL DEFAULT 0",
        "observed_activity_delta": "REAL DEFAULT 0",
        "observed_survivor_delta": "REAL DEFAULT 0",
        "prediction_alignment": "REAL DEFAULT 0",
        "causal_claim": "INTEGER DEFAULT 0",
        "details": "TEXT",
    },
}

CREATE_TABLES = {
    "phase7d_workpoint_observer_state": (
        "CREATE TABLE IF NOT EXISTS phase7d_workpoint_observer_state "
        "(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)"
    ),
    "phase7d_workpoint_observer_events": (
        "CREATE TABLE IF NOT EXISTS phase7d_workpoint_observer_events "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT)"
    ),
    "phase7d_workpoint_virtual_outcomes": (
        "CREATE TABLE IF NOT EXISTS phase7d_workpoint_virtual_outcomes "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT)"
    ),
}


def _now():
    return int(time.time())


def _clamp(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(value)))


def _to_float(value, default=0.0):
    try:
        return float(str(value).strip().strip('"').strip("'"))
    except Exception:
        return float(default)


def _resolve_db(obj=None):
    if isinstance(obj, sqlite3.Connection):
        return obj
    if obj is not None:
        for attr in ("db", "conn", "con", "connection"):
            value = getattr(obj, attr, None)
            if isinstance(value, sqlite3.Connection):
                return value
        mem = getattr(obj, "memory", None) or getattr(obj, "mem", None)
        if mem is not None:
            return _resolve_db(mem)
    raise RuntimeError("sqlite connection not found")


def _exists(con, table):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con, table):
    if not _exists(con, table):
        return set()
    return {row[1] for row in con.execute("PRAGMA table_info(" + table + ")")}


def ensure_schema(obj=None):
    con = _resolve_db(obj)
    changes = []
    for table, sql in CREATE_TABLES.items():
        if not _exists(con, table):
            con.execute(sql)
            changes.append("create_table:" + table)
        present = _columns(con, table)
        for column, declaration in SCHEMA_TABLES[table].items():
            if column not in present:
                con.execute(
                    "ALTER TABLE " + table + " ADD COLUMN " + column + " " + declaration
                )
                changes.append("add_column:" + table + "." + column)
                present.add(column)
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_p7dwo_events_cycle ON "
        "phase7d_workpoint_observer_events(cycle_index)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_p7dwo_outcomes_source ON "
        "phase7d_workpoint_virtual_outcomes(source_event_id)"
    )
    con.commit()
    return {"phase": PHASE, "status": "ok", "changes": changes, "applied": False}


def _self_check_schema(obj=None):
    con = _resolve_db(obj)
    missing = []
    for table, required in SCHEMA_TABLES.items():
        if not _exists(con, table):
            missing.append(table + ":missing_table")
            continue
        present = _columns(con, table)
        for column in required:
            if column not in present:
                missing.append(table + "." + column)
    return missing


def _read_kv(con, table):
    if not _exists(con, table):
        return {}
    present = _columns(con, table)
    if "key" not in present or "value" not in present:
        return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())


def _state_get(con, key, default=None):
    row = con.execute(
        "SELECT value FROM phase7d_workpoint_observer_state WHERE key=?", (key,)
    ).fetchone()
    return row[0] if row else default


def _state_set(con, key, value):
    con.execute(
        "INSERT INTO phase7d_workpoint_observer_state(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
        (key, str(value), _now()),
    )


def _latest_7d(con):
    if not _exists(con, "phase7d_slow_wave_cycles"):
        return None
    required = {
        "id", "cycle_index", "selection_pressure", "adaptive_threshold_avg",
        "up_state_avg_activity", "candidates_survived", "candidates_participated",
        "reason",
    }
    if not required.issubset(_columns(con, "phase7d_slow_wave_cycles")):
        return None
    row = con.execute(
        "SELECT id,cycle_index,selection_pressure,adaptive_threshold_avg,"
        "up_state_avg_activity,candidates_survived,candidates_participated,reason "
        "FROM phase7d_slow_wave_cycles ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    participated = int(row[6] or 0)
    survived = int(row[5] or 0)
    return {
        "id": int(row[0]), "cycle_index": int(row[1] or 0),
        "pressure": _to_float(row[2]), "threshold": _to_float(row[3]),
        "activity": _to_float(row[4]), "survived": survived,
        "participated": participated,
        "survivor_ratio": (survived / participated) if participated else 0.0,
        "reason": str(row[7] or ""),
    }


def _neuromod(con):
    result = {}
    for table in (
        "phase6a_neuromodulated_sleep_state", "neuromodulator_state", "phase7c_state"
    ):
        state = _read_kv(con, table)
        for key in ("glutamate", "gaba"):
            if key not in result and key in state:
                result[key] = _to_float(state[key], 0.5)
    return {"glutamate": result.get("glutamate", 0.5), "gaba": result.get("gaba", 0.5)}


def _latest_stability(con):
    if not _exists(con, "stability_watch_events"):
        return {}
    present = _columns(con, "stability_watch_events")
    wanted = [
        "regime", "dominant_signal", "survivor_ratio_recent", "threshold_drift",
        "ei_saturation", "elevated",
    ]
    selected = [name for name in wanted if name in present]
    if not selected:
        return {}
    order = "id" if "id" in present else "rowid"
    row = con.execute(
        "SELECT " + ",".join(selected) + " FROM stability_watch_events ORDER BY "
        + order + " DESC LIMIT 1"
    ).fetchone()
    return dict(zip(selected, row)) if row else {}


def _cortisol(con):
    state = _read_kv(con, "cortisol_state")
    return {
        "regime": str(state.get("last_regime", "unknown")),
        "load": _to_float(state.get("last_allostatic_load"), 0.0),
    }


def _reference(con, key, fallback):
    value = _state_get(con, key)
    return _to_float(value, fallback) if value is not None else float(fallback)


def _learn_reference(old, observed, rate):
    return float(old) + float(rate) * (float(observed) - float(old))


def _bounded(value):
    return math.tanh(float(value))


def _evaluate_previous(con, current):
    previous = con.execute(
        "SELECT id,up_state_activity,survivor_ratio,virtual_down_pressure,"
        "virtual_hold_pressure,virtual_up_pressure FROM phase7d_workpoint_observer_events "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not previous:
        return 0
    already = con.execute(
        "SELECT 1 FROM phase7d_workpoint_virtual_outcomes WHERE source_event_id=? LIMIT 1",
        (int(previous[0]),),
    ).fetchone()
    if already:
        return 0
    activity_delta = current["activity"] - _to_float(previous[1])
    survivor_delta = current["survivor_ratio"] - _to_float(previous[2])
    observed_direction = -(activity_delta + survivor_delta)
    proposals = (
        ("down", _to_float(previous[3]), -1.0),
        ("hold", _to_float(previous[4]), 0.0),
        ("up", _to_float(previous[5]), 1.0),
    )
    now = _now()
    for kind, pressure, predicted_direction in proposals:
        if predicted_direction == 0.0:
            alignment = -abs(activity_delta) - abs(survivor_delta)
        else:
            alignment = predicted_direction * observed_direction
        con.execute(
            "INSERT INTO phase7d_workpoint_virtual_outcomes("
            "created_at,source_event_id,target_event_id,proposal_kind,proposed_pressure,"
            "predicted_direction,observed_activity_delta,observed_survivor_delta,"
            "prediction_alignment,causal_claim,details) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                now, int(previous[0]), 0, kind, pressure, predicted_direction,
                activity_delta, survivor_delta, alignment, 0,
                json.dumps({
                    "interpretation": "observational_alignment_only",
                    "not_causal": True,
                }, sort_keys=True),
            ),
        )
    return 3


def observe_cycle(obj=None):
    con = _resolve_db(obj)
    ensure_schema(con)
    missing = _self_check_schema(con)
    if missing:
        return {"phase": PHASE, "status": "schema_check_failed", "missing": missing, "applied": False}

    source = _latest_7d(con)
    if not source:
        return {"phase": PHASE, "status": "no_phase7d_cycle", "applied": False}
    duplicate = con.execute(
        "SELECT id FROM phase7d_workpoint_observer_events WHERE phase7d_event_id=? LIMIT 1",
        (source["id"],),
    ).fetchone()
    if duplicate:
        return {"phase": PHASE, "status": "already_observed", "event_id": int(duplicate[0]), "applied": False}

    nm = _neuromod(con)
    stability = _latest_stability(con)
    cortisol = _cortisol(con)

    previous_count = int(_to_float(_state_get(con, "paired_observations", 0), 0))
    pressure_ref = _reference(con, "pressure_reference", source["pressure"])
    glu_ref = _reference(con, "glutamate_reference", nm["glutamate"])
    gaba_ref = _reference(con, "gaba_reference", nm["gaba"])
    activity_ref = _reference(con, "activity_reference", source["activity"])
    survivor_ref = _reference(con, "survivor_reference", source["survivor_ratio"])
    persistent = _reference(con, "persistent_signal", 0.0)

    activity_scale = max(_reference(con, "activity_scale", 0.02), 0.01)
    survivor_scale = max(_reference(con, "survivor_scale", 0.05), 0.02)
    ei_scale = max(_reference(con, "ei_scale", 0.10), 0.05)

    e_glu = (nm["glutamate"] - glu_ref) / ei_scale
    e_gaba = (gaba_ref - nm["gaba"]) / ei_scale
    e_activity = (source["activity"] - activity_ref) / activity_scale
    e_survivor = (source["survivor_ratio"] - survivor_ref) / survivor_scale
    raw_signal = 0.25 * (e_glu + e_gaba + e_activity + e_survivor)
    bounded_signal = _bounded(raw_signal)
    persistent_new = 0.95 * persistent + 0.05 * bounded_signal

    elevated = bool(int(_to_float(stability.get("elevated"), 0)))
    calm = cortisol["regime"] in ("calm", "unknown") and cortisol["load"] < 0.35
    within_activity = abs(e_activity) <= 2.0
    within_survivor = abs(e_survivor) <= 2.0
    stable_candidate = (
        source["reason"] == "self_regulating_slow_wave_sleep"
        and source["participated"] > 0
        and not elevated and calm and within_activity and within_survivor
        and _to_float(stability.get("ei_saturation"), 0.0) <= 0.0
    )

    reference_updated = False
    freeze_reason = "stable_candidate"
    if stable_candidate:
        rate = 0.005
        pressure_ref = _learn_reference(pressure_ref, source["pressure"], rate)
        glu_ref = _learn_reference(glu_ref, nm["glutamate"], rate)
        gaba_ref = _learn_reference(gaba_ref, nm["gaba"], rate)
        activity_ref = _learn_reference(activity_ref, source["activity"], rate)
        survivor_ref = _learn_reference(survivor_ref, source["survivor_ratio"], rate)
        reference_updated = True
    else:
        reasons = []
        if elevated: reasons.append("stability_elevated")
        if not calm: reasons.append("cortisol_not_calm")
        if not within_activity: reasons.append("activity_outside_reference_gate")
        if not within_survivor: reasons.append("survivor_outside_reference_gate")
        if source["participated"] <= 0: reasons.append("no_participation")
        freeze_reason = ",".join(reasons) or "not_stable_candidate"

    # Virtual candidates only. No value is written to 7d parameters.
    virtual_step = max(_reference(con, "virtual_step", 0.0002), 0.00005)
    response_gain = max(_reference(con, "response_gain", 0.0002), 0.00001)
    limited_delta = max(-virtual_step, min(virtual_step, response_gain * persistent_new))
    limited_proposal = _clamp(source["pressure"] + limited_delta)
    down = _clamp(source["pressure"] - virtual_step)
    hold = source["pressure"]
    up = _clamp(source["pressure"] + virtual_step)

    evaluated = _evaluate_previous(con, source)
    now = _now()
    cursor = con.execute(
        "INSERT INTO phase7d_workpoint_observer_events("
        "created_at,cycle_index,phase7d_event_id,glutamate,gaba,selection_pressure,"
        "adaptive_threshold,up_state_activity,survivor_ratio,candidates_participated,"
        "candidates_survived,pressure_reference,glutamate_reference,gaba_reference,"
        "activity_reference,survivor_reference,raw_signal,bounded_signal,persistent_signal,"
        "virtual_down_pressure,virtual_hold_pressure,virtual_up_pressure,limited_proposal,"
        "limited_delta,stable_reference_candidate,reference_updated,reference_freeze_reason,"
        "cortisol_regime,allostatic_load,stability_regime,dominant_signal,ei_saturation,"
        "applied,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            now, source["cycle_index"], source["id"], nm["glutamate"], nm["gaba"],
            source["pressure"], source["threshold"], source["activity"],
            source["survivor_ratio"], source["participated"], source["survived"],
            pressure_ref, glu_ref, gaba_ref, activity_ref, survivor_ref,
            raw_signal, bounded_signal, persistent_new, down, hold, up,
            limited_proposal, limited_delta, int(stable_candidate), int(reference_updated),
            freeze_reason, cortisol["regime"], cortisol["load"],
            str(stability.get("regime", "unknown")),
            str(stability.get("dominant_signal", "none")),
            _to_float(stability.get("ei_saturation"), 0.0), 0,
            json.dumps({
                "observer_only": True,
                "causal_effect_not_claimed": True,
                "virtual_proposals": True,
            }, sort_keys=True),
        ),
    )

    _state_set(con, "paired_observations", previous_count + 1)
    _state_set(con, "pressure_reference", pressure_ref)
    _state_set(con, "glutamate_reference", glu_ref)
    _state_set(con, "gaba_reference", gaba_ref)
    _state_set(con, "activity_reference", activity_ref)
    _state_set(con, "survivor_reference", survivor_ref)
    _state_set(con, "persistent_signal", persistent_new)
    _state_set(con, "applied", "false")
    _state_set(con, "mode", "observer_only")
    con.commit()
    return {
        "phase": PHASE, "status": "observed", "event_id": int(cursor.lastrowid),
        "paired_observations": previous_count + 1,
        "stable_reference_candidate": stable_candidate,
        "reference_updated": reference_updated,
        "reference_freeze_reason": freeze_reason,
        "bounded_signal": round(bounded_signal, 8),
        "persistent_signal": round(persistent_new, 8),
        "limited_proposal": round(limited_proposal, 8),
        "limited_delta": round(limited_delta, 8),
        "virtual_outcomes_written": evaluated,
        "applied": False,
    }


def managed_cycle(self, progress=None):
    downstream = _ORIG_CYCLE(self, progress) if _ORIG_CYCLE else {"status": "no_downstream"}
    try:
        observer = observe_cycle(self)
    except Exception as exc:
        observer = {"phase": PHASE, "status": "observer_error", "error": str(exc), "applied": False}
    if isinstance(downstream, dict):
        downstream["phase7d_workpoint_observer_v1"] = observer
        return downstream
    return {"downstream": downstream, "phase7d_workpoint_observer_v1": observer}


def managed_run(self, cycles=1, progress=None):
    out = []
    try:
        count = max(1, int(cycles or 1))
    except Exception:
        count = 1
    for _ in range(count):
        out.append(managed_cycle(self, progress))
    return out


def patch_autonomous_loop(loop_cls=None):
    global _ORIG_CYCLE, _ORIG_RUN
    if loop_cls is None:
        from ki_system.autonomous import AutonomousLoop as loop_cls
    if getattr(loop_cls, "phase7d_workpoint_observer_v1", False):
        return True
    _ORIG_CYCLE = getattr(loop_cls, "cycle", None)
    _ORIG_RUN = getattr(loop_cls, "run", None)
    loop_cls.cycle = managed_cycle
    loop_cls.run = managed_run
    loop_cls.phase7d_workpoint_observer_v1 = True
    loop_cls.phase7d_workpoint_observer_applied = False
    return True


def autoload(loop_cls=None):
    """Registry entry point; install the observer wrapper on the supplied loop class."""
    return patch_autonomous_loop(loop_cls)


# No import-time loop patching here. Phase7e calls observe_cycle() explicitly
# after the completed Phase7d downstream result and before Phase7e processing.
