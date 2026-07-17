# -*- coding: utf-8 -*-
"""
V8 Phase 6b - Sleep Replay Effectiveness and Plasticity Adjustment Release

Project compass:
    - No blacklist / filter system.
    - No direct facts / relations / questions writes.
    - No fact promotion.
    - Digital neuromodulators steer the WHOLE learning process
      (learning rate, error weighting, revision pressure, uncertainty,
       confidence, exploration, inhibition, stabilization, consolidation,
       reading / attention strategy).
    - Anti-hallucination: interleaved replay of novel + stable anchors,
      actor / critic gating, weight renormalization, knowledge distillation,
      L2M metrics.

This module measures the effectiveness of phase6a sleep-replay cycles and
applies homeostatic, neuromodulator-gated plasticity adjustments so the
system escapes plateaus without burning in self-generated hallucinations.

Schema safety:
    - SCHEMA_TABLES is the single source of truth for ALL columns.
    - ensure_schema() creates missing tables and ADDs missing columns.
    - _self_check_schema() aborts the cycle BEFORE any write if a column
      is missing. This is the explicit safeguard against the previous
      column errors.
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

PHASE = "phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release"
PHASE_VERSION = "phase6b_v1"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


# =========================================================================
# SCHEMA - single source of truth
# =========================================================================

SCHEMA_TABLES: Dict[str, List[Tuple[str, str]]] = {
    "phase6b_state": [
        ("key",        "TEXT PRIMARY KEY"),
        ("value",      "TEXT"),
        ("updated_at", "INTEGER"),
    ],
    "phase6b_anchor_pool": [
        ("id",                 "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("source_table",       "TEXT"),
        ("source_id",          "INTEGER"),
        ("anchor_key",         "TEXT"),
        ("stability_score",    "REAL DEFAULT 0.0"),
        ("replay_count",       "INTEGER DEFAULT 0"),
        ("last_replayed_at",   "INTEGER DEFAULT 0"),
        ("delta_variance",     "REAL DEFAULT 0.0"),
        ("overlap_score_avg",  "REAL DEFAULT 0.0"),
        ("outcome_score_avg",  "REAL DEFAULT 0.0"),
        ("promoted_from",      "TEXT"),
        ("active",             "INTEGER DEFAULT 1"),
        ("created_at",         "INTEGER"),
        ("updated_at",         "INTEGER"),
    ],
    "phase6b_critic_snapshot": [
        ("snapshot_id",         "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",          "INTEGER"),
        ("reason",              "TEXT"),
        ("dopamine",            "REAL"),
        ("serotonin",           "REAL"),
        ("noradrenaline",       "REAL"),
        ("acetylcholine",       "REAL"),
        ("glutamate",           "REAL"),
        ("gaba",                "REAL"),
        ("plasticity_level",    "REAL"),
        ("exploration_bias",    "REAL"),
        ("consolidation_bias",  "REAL"),
        ("inhibition_bias",     "REAL"),
        ("revision_bias",       "REAL"),
        ("anchor_count",        "INTEGER"),
        ("effectiveness_avg",   "REAL"),
        ("state_json",          "TEXT"),
        ("active",              "INTEGER DEFAULT 1"),
    
        ('measurement_event_id', 'INTEGER'),
        ('evidence_state', 'TEXT'),
        ('snapshot_owner', 'TEXT')
    ],
    "phase6b_effectiveness_events": [
        ("id",                    "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",            "INTEGER"),
        ("cycle_index",           "INTEGER"),
        ("window_size",           "INTEGER"),
        ("replay_batch_size",     "INTEGER"),
        ("novel_count",           "INTEGER"),
        ("anchor_count",          "INTEGER"),
        ("pre_outcome_score",     "REAL"),
        ("post_outcome_score",    "REAL"),
        ("pre_closure_delta",     "REAL"),
        ("post_closure_delta",    "REAL"),
        ("pre_overlap_score",     "REAL"),
        ("post_overlap_score",    "REAL"),
        ("delta_outcome",         "REAL"),
        ("delta_closure",         "REAL"),
        ("delta_overlap",         "REAL"),
        ("effectiveness_score",   "REAL"),
        ("plateau_flag",          "INTEGER DEFAULT 0"),
        ("critic_penalty",        "REAL DEFAULT 0.0"),
        ("anchor_consistency",    "REAL DEFAULT 0.0"),
        ("dopamine",              "REAL"),
        ("serotonin",             "REAL"),
        ("noradrenaline",         "REAL"),
        ("acetylcholine",         "REAL"),
        ("glutamate",             "REAL"),
        ("gaba",                  "REAL"),
        ("notes",                 "TEXT"),
    
        ('measurement_owner', 'TEXT'),
        ('population_available', 'INTEGER DEFAULT 0'),
        ('outcome_observation_available', 'INTEGER DEFAULT 0'),
        ('comparison_window_available', 'INTEGER DEFAULT 0'),
        ('evidence_state', 'TEXT'),
        ('evidence_reason', 'TEXT')
    ,
        ('source_phase6a_cycle_id', 'INTEGER'),
        ('source_phase6a_created_at', 'INTEGER'),
        ('source_phase6a_fresh', 'INTEGER DEFAULT 0')
    ],
    "phase6b_plasticity_adjustments": [
        ("id",                        "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",                "INTEGER"),
        ("cycle_index",               "INTEGER"),
        ("adjustment_type",           "TEXT"),
        ("reason",                    "TEXT"),
        ("scale_factor",              "REAL"),
        ("window_size",               "INTEGER"),
        ("pre_plasticity_level",      "REAL"),
        ("post_plasticity_level",     "REAL"),
        ("pre_exploration_bias",      "REAL"),
        ("post_exploration_bias",     "REAL"),
        ("pre_consolidation_bias",    "REAL"),
        ("post_consolidation_bias",   "REAL"),
        ("pre_inhibition_bias",       "REAL"),
        ("post_inhibition_bias",      "REAL"),
        ("pre_revision_bias",         "REAL"),
        ("post_revision_bias",        "REAL"),
        ("dopamine",                  "REAL"),
        ("serotonin",                 "REAL"),
        ("noradrenaline",             "REAL"),
        ("acetylcholine",             "REAL"),
        ("glutamate",                 "REAL"),
        ("gaba",                      "REAL"),
        ("critic_gate_result",        "TEXT"),
        ("notes",                     "TEXT"),
    
        ('measurement_event_id', 'INTEGER'),
        ('evidence_state', 'TEXT'),
        ('state_change_allowed', 'INTEGER DEFAULT 0')
    ],
    "phase6b_distilled_knowledge": [
        ("id",                    "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",            "INTEGER"),
        ("cycle_index",           "INTEGER"),
        ("source_kind",           "TEXT"),
        ("source_ref",            "TEXT"),
        ("knowledge_key",         "TEXT"),
        ("stability_score",       "REAL"),
        ("effectiveness_score",   "REAL"),
        ("anchor_alignment",      "REAL"),
        ("confidence",            "REAL"),
        ("distilled_from_count",  "INTEGER"),
        ("notes",                 "TEXT"),
    ],
    "phase6b_l2m_metrics": [
        ("id",                       "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("created_at",               "INTEGER"),
        ("cycle_index",              "INTEGER"),
        ("performance_maintenance",  "REAL"),
        ("forward_transfer",         "REAL"),
        ("backward_transfer",        "REAL"),
        ("sample_efficiency",        "REAL"),
        ("performance_recovery",     "REAL"),
        ("anchor_stability",         "REAL"),
        ("alert_flag",               "INTEGER DEFAULT 0"),
        ("alert_reason",             "TEXT"),
    
        ('measurement_event_id', 'INTEGER'),
        ('evidence_state', 'TEXT')
    ],
}

SCHEMA_INDEXES: List[Tuple[str, str, str]] = [
    ("idx_phase6b_anchor_pool_key",     "phase6b_anchor_pool",            "anchor_key"),
    ("idx_phase6b_anchor_pool_active",  "phase6b_anchor_pool",            "active"),
    ("idx_phase6b_anchor_pool_source",  "phase6b_anchor_pool",            "source_table, source_id"),
    ("idx_phase6b_critic_active",       "phase6b_critic_snapshot",        "active"),
    ("idx_phase6b_effectiveness_cyc",   "phase6b_effectiveness_events",   "cycle_index"),
    ("idx_phase6b_adjustments_cyc",     "phase6b_plasticity_adjustments", "cycle_index"),
    ("idx_phase6b_distilled_key",       "phase6b_distilled_knowledge",    "knowledge_key"),
    ("idx_phase6b_l2m_cyc",             "phase6b_l2m_metrics",            "cycle_index"),
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
    if x < lo:
        return lo
    if x > hi:
        return hi
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
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _index_exists(con: sqlite3.Connection, index: str) -> bool:
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index,),
    ).fetchone()
    return row is not None


def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]


def resolve_db(obj: Any = None) -> sqlite3.Connection:
    """Accept sqlite3.Connection, Memory/AutonomousLoop with .db attribute,
    or None. Falls back to 'ki_memory.sqlite3' in CWD."""
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
    """Idempotent DDL. Creates missing tables, adds missing columns,
    creates missing indexes. Never destructive."""
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
    """Return list of missing 'table.column' entries. Empty list == OK."""
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


def _read_kv(con, table):
    if not _table_exists(con, table):
        return {}
    tc = set(_columns(con, table))
    if "key" not in tc or "value" not in tc:
        return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())


def _phase6c_cfg(con):
    if not _table_exists(con, "phase6c_meta_control_parameters"):
        return {}
    try:
        return {str(k): _to_float(v, 0.0) for k,v in con.execute("SELECT parameter_key,current_value FROM phase6c_meta_control_parameters").fetchall()}
    except Exception:
        return {}

def _cfg_value(cfg, key, default):
    return _to_float(cfg.get(key), default) if key in cfg else default


def _read_recent_cycles(con: sqlite3.Connection, n: int = 20) -> List[Dict[str, Any]]:
    if not _table_exists(con, "phase6a_sleep_replay_cycles"):
        return []
    wanted = ["id","candidate_count","replay_events","avg_outcome_score","avg_closure_delta","avg_overlap_score",
              "persistent_gap_pressure","plasticity_level","exploration_bias","consolidation_bias","created_at",
              "population_available","outcome_observation_available","outcome_observation_count","evidence_state","evidence_reason"]
    existing=set(_columns(con,"phase6a_sleep_replay_cycles")); select_cols=[c for c in wanted if c in existing]
    if not select_cols: return []
    order_col="id" if "id" in existing else ("created_at" if "created_at" in existing else "rowid")
    sql="SELECT "+", ".join(select_cols)+" FROM phase6a_sleep_replay_cycles ORDER BY "+order_col+" DESC LIMIT ?"
    return [dict(zip(select_cols,r)) for r in con.execute(sql,(int(n),)).fetchall()]






def _neuromodulators(sleep_state: Dict[str, Any]) -> Dict[str, float]:
    return {
        "dopamine":      _clamp(_to_float(sleep_state.get("dopamine"),      0.5)),
        "serotonin":     _clamp(_to_float(sleep_state.get("serotonin"),     0.5)),
        "noradrenaline": _clamp(_to_float(sleep_state.get("noradrenaline"), 0.5)),
        "acetylcholine": _clamp(_to_float(sleep_state.get("acetylcholine"), 0.5)),
        "glutamate":     _clamp(_to_float(sleep_state.get("glutamate"),     0.5)),
        "gaba":          _clamp(_to_float(sleep_state.get("gaba"),          0.3)),
    }


def _promote_anchors(con: sqlite3.Connection,
                     min_survived_cycles: int = 3,
                     target_limit: int = 400) -> Dict[str, Any]:
    # BRAINSTEM_PHASE6B_SURVIVOR_ANCHOR_V1
    promoted = {"context_hypotheses": 0, "updated": 0, "eligible": 0,
                "checkpoint_id": 0, "mode": "phase7d_survivor_n3_post_rotation"}
    now = _now()
    if not _table_exists(con, "phase7d_consolidation_survivors"):
        return promoted
    if not _table_exists(con, "phase6b_anchor_pool"):
        return promoted

    state = _read_kv(con, "phase6b_state")
    checkpoint = _to_int(state.get("phase7d_survivor_anchor_checkpoint_id"), 0)
    if checkpoint <= 0:
        row = con.execute(
            "SELECT COALESCE(MAX(id),0) FROM phase7d_consolidation_survivors"
        ).fetchone()
        checkpoint = _to_int(row[0] if row else 0, 0)
        _kv_set(con, "phase6b_state", "phase7d_survivor_anchor_checkpoint_id", checkpoint)
        _kv_set(con, "phase6b_state", "phase7d_survivor_anchor_mode", "phase7d_survivor_n3_post_rotation")
        _kv_set(con, "phase6b_state", "phase7d_survivor_anchor_min_cycles", int(min_survived_cycles))
        con.commit()
        promoted["checkpoint_id"] = checkpoint
        promoted["initialized_checkpoint"] = True
        return promoted

    promoted["checkpoint_id"] = checkpoint
    rows = con.execute(
        "SELECT source_table,source_id,COUNT(DISTINCT cycle_index) AS survived_cycles,"
        "AVG(final_consistency) AS avg_consistency,MIN(final_consistency) AS min_consistency,"
        "AVG(up_states_survived) AS avg_up_states "
        "FROM phase7d_consolidation_survivors "
        "WHERE id>? AND reinforced=1 AND source_table='context_hypotheses' "
        "GROUP BY source_table,source_id "
        "HAVING COUNT(DISTINCT cycle_index)>=? "
        "ORDER BY survived_cycles DESC,avg_consistency DESC LIMIT ?",
        (int(checkpoint), int(min_survived_cycles), int(target_limit)),
    ).fetchall()
    promoted["eligible"] = len(rows)

    for source_table, source_id, survived_cycles, avg_consistency, min_consistency, avg_up_states in rows:
        sid = _to_int(source_id)
        cycles = _to_int(survived_cycles)
        stability = _clamp(_to_float(avg_consistency, 0.0))
        akey = str(source_table) + ":" + str(sid)
        existing = con.execute(
            "SELECT id FROM phase6b_anchor_pool WHERE anchor_key=?", (akey,)
        ).fetchone()
        if existing is None:
            con.execute(
                "INSERT INTO phase6b_anchor_pool "
                "(source_table,source_id,anchor_key,stability_score,replay_count,"
                "last_replayed_at,delta_variance,overlap_score_avg,outcome_score_avg,"
                "promoted_from,active,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(source_table), sid, akey, stability, 0, 0, 0.0, 0.0, 0.0,
                 "phase7d_survivor_n3_post_rotation", 1, now, now),
            )
            promoted["context_hypotheses"] += 1
        else:
            con.execute(
                "UPDATE phase6b_anchor_pool SET stability_score=?,promoted_from=?,"
                "active=1,updated_at=? WHERE id=?",
                (stability, "phase7d_survivor_n3_post_rotation", now, existing[0]),
            )
            promoted["updated"] += 1

    _kv_set(con, "phase6b_state", "phase7d_survivor_anchor_last_scan_at", now)
    _kv_set(con, "phase6b_state", "phase7d_survivor_anchor_last_eligible", len(rows))
    con.commit()
    return promoted


def _select_replay_batch(con: sqlite3.Connection, neuromod: Dict[str, float], batch_size: int = 180) -> Dict[str, Any]:
    cfg=_phase6c_cfg(con); gaba=neuromod["gaba"]; na=neuromod["noradrenaline"]
    base=_cfg_value(cfg,"novel_ratio_base",0.6); gw=_cfg_value(cfg,"novel_ratio_gaba_weight",0.3); nw=_cfg_value(cfg,"novel_ratio_na_weight",0.2)
    novel_ratio=_clamp(base-gw*gaba+nw*na,0.3,0.9); n_anchor=int(batch_size*(1.0-novel_ratio)); n_novel=batch_size-n_anchor; now=_now()
    anchors=con.execute("SELECT id,source_table,source_id,stability_score FROM phase6b_anchor_pool WHERE active=1 ORDER BY stability_score DESC,last_replayed_at ASC LIMIT ?",(n_anchor,)).fetchall()
    novel=[]
    if _table_exists(con,"phase5g_experiment_outcomes"):
        ncols=set(_columns(con,"phase5g_experiment_outcomes")); id_col="id" if "id" in ncols else "rowid"; score_col="outcome_score" if "outcome_score" in ncols else None
        sql="SELECT "+id_col+" FROM phase5g_experiment_outcomes ORDER BY "+(score_col+" ASC" if score_col else id_col+" DESC")+" LIMIT ?"
        raw=con.execute(sql,(int(n_novel*3),)).fetchall(); inhibit=_cfg_value(cfg,"gaba_novel_inhibition",0.5); rnd=random.Random(now)
        for r in raw:
            if rnd.random() < gaba*inhibit: continue
            novel.append(_to_int(r[0]))
            if len(novel)>=n_novel: break
    if anchors:
        ids=[a[0] for a in anchors]; ph=",".join("?" for _ in ids)
        con.execute("UPDATE phase6b_anchor_pool SET replay_count=COALESCE(replay_count,0)+1,last_replayed_at=?,updated_at=? WHERE id IN ("+ph+")",[now,now]+ids)
    con.commit()
    return {"batch_size":batch_size,"novel_ratio_target":round(novel_ratio,3),"anchor_count":len(anchors),"novel_count":len(novel),"anchor_ids":[a[0] for a in anchors],"novel_ids":novel}




def _measure_effectiveness(con, recent, batch, neuromod, cycle_index, window_size=5):
    cur=recent[0] if recent else {}; source_id=_to_int(cur.get("id"),0); source_created=_to_int(cur.get("created_at"),0)
    state_kv=_read_kv(con,"phase6b_state"); last_source=_to_int(state_kv.get("last_consumed_phase6a_cycle_id"),0)
    fresh=1 if source_id>0 and source_id>last_source else 0
    if not fresh:
        return {"skip_no_fresh_source":True,"measurement_event_id":None,"cycle_index":cycle_index,"window_size":window_size,
                "effectiveness_score":0.0,"plateau_flag":0,"anchor_consistency":0.0,"population_available":0,
                "outcome_observation_available":0,"comparison_window_available":0,"evidence_state":"stale_source_observation",
                "evidence_reason":"no_unconsumed_phase6a_cycle","state_change_allowed":0,
                "source_phase6a_cycle_id":source_id,"source_phase6a_created_at":source_created,"source_phase6a_fresh":0}
    population=1 if (_to_int(cur.get("population_available"),0)>0 or _to_int(cur.get("candidate_count"),0)>0 or _to_int(cur.get("replay_events"),0)>0) else 0
    outcome_obs=1 if _to_int(cur.get("outcome_observation_available"),0)>0 else 0
    observed_prev=[r for r in recent[1:1+window_size] if _to_int(r.get("outcome_observation_available"),0)>0]
    comparison=1 if outcome_obs and observed_prev else 0
    def avg(rows,key):
        vals=[_to_float(r.get(key),None) for r in rows]; vals=[v for v in vals if v is not None]; return sum(vals)/len(vals) if vals else 0.0
    pre_o=avg(observed_prev,"avg_outcome_score"); pre_c=avg(observed_prev,"avg_closure_delta"); pre_ov=avg(observed_prev,"avg_overlap_score")
    post_o=_to_float(cur.get("avg_outcome_score"),pre_o); post_c=_to_float(cur.get("avg_closure_delta"),pre_c); post_ov=_to_float(cur.get("avg_overlap_score"),pre_ov)
    d_o=post_o-pre_o if comparison else 0.0; d_c=post_c-pre_c if comparison else 0.0; d_ov=post_ov-pre_ov if comparison else 0.0
    cfg=_phase6c_cfg(con); eps=_cfg_value(cfg,"plateau_eps",0.005)
    if not population: state="no_population"; reason="no_replay_population_observed"
    elif not outcome_obs: state="population_without_outcome_observation"; reason="population_present_but_outcome_observation_absent"
    elif not comparison: state="outcome_observed_insufficient_comparison"; reason="outcome_observed_without_prior_observed_window"
    elif abs(d_o)<eps and abs(d_c)<eps and abs(d_ov)<eps: state="outcome_observed_no_change"; reason="observed_comparison_within_plateau_epsilon"
    else: state="outcome_observed_change"; reason="observed_comparison_changed"
    allowed=1 if state in ("outcome_observed_change","outcome_observed_no_change") else 0; plateau=1 if state=="outcome_observed_no_change" else 0
    eff=(0.5+0.3*neuromod["dopamine"])*d_o+(0.3+0.2*neuromod["noradrenaline"])*d_c+(0.2+0.2*neuromod["acetylcholine"])*d_ov if allowed else 0.0
    row=con.execute("SELECT AVG(stability_score) FROM phase6b_anchor_pool WHERE active=1").fetchone(); anchor=_to_float(row[0] if row else 0.0,0.0)
    notes=json.dumps({"novel_ratio_target":batch.get("novel_ratio_target"),"anchor_count":batch.get("anchor_count"),"novel_count":batch.get("novel_count"),"plateau_eps":eps,"source_phase6a_cycle_id":source_id})
    sql="INSERT INTO phase6b_effectiveness_events (created_at,cycle_index,window_size,replay_batch_size,novel_count,anchor_count,pre_outcome_score,post_outcome_score,pre_closure_delta,post_closure_delta,pre_overlap_score,post_overlap_score,delta_outcome,delta_closure,delta_overlap,effectiveness_score,plateau_flag,critic_penalty,anchor_consistency,dopamine,serotonin,noradrenaline,acetylcholine,glutamate,gaba,notes,measurement_owner,population_available,outcome_observation_available,comparison_window_available,evidence_state,evidence_reason,source_phase6a_cycle_id,source_phase6a_created_at,source_phase6a_fresh) VALUES("+",".join("?" for _ in range(35))+")"
    curx=con.execute(sql,(_now(),cycle_index,window_size,batch.get("batch_size",0),batch.get("novel_count",0),batch.get("anchor_count",0),pre_o,post_o,pre_c,post_c,pre_ov,post_ov,d_o,d_c,d_ov,eff,plateau,0.0,anchor,neuromod["dopamine"],neuromod["serotonin"],neuromod["noradrenaline"],neuromod["acetylcholine"],neuromod["glutamate"],neuromod["gaba"],notes,"canonical_phase6b",population,outcome_obs,comparison,state,reason,source_id,source_created,1))
    _kv_set(con,"phase6b_state","last_consumed_phase6a_cycle_id",source_id); _kv_set(con,"phase6b_state","last_consumed_phase6a_created_at",source_created); con.commit()
    return {"skip_no_fresh_source":False,"measurement_event_id":int(curx.lastrowid),"cycle_index":cycle_index,"window_size":window_size,"delta_outcome":d_o,"delta_closure":d_c,"delta_overlap":d_ov,"effectiveness_score":eff,"plateau_flag":plateau,"anchor_consistency":anchor,"population_available":population,"outcome_observation_available":outcome_obs,"comparison_window_available":comparison,"evidence_state":state,"evidence_reason":reason,"state_change_allowed":allowed,"source_phase6a_cycle_id":source_id,"source_phase6a_created_at":source_created,"source_phase6a_fresh":1}






def _critic_gate(con: sqlite3.Connection,
                 proposed: Dict[str, float],
                 anchor_consistency: float) -> Tuple[bool, float, str]:
    """Compare proposed post-values against last active critic snapshot.
    Return (allowed, penalty, reason)."""
    row = con.execute(
        "SELECT plasticity_level, exploration_bias, consolidation_bias, "
        "inhibition_bias, revision_bias "
        "FROM phase6b_critic_snapshot WHERE active=1 "
        "ORDER BY snapshot_id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return True, 0.0, "no_critic_snapshot"
    baseline = {
        "plasticity_level":   _to_float(row[0], 0.5),
        "exploration_bias":   _to_float(row[1], 0.5),
        "consolidation_bias": _to_float(row[2], 0.5),
        "inhibition_bias":    _to_float(row[3], 0.3),
        "revision_bias":      _to_float(row[4], 0.5),
    }
    max_dev = 0.0
    for k, v in proposed.items():
        if k in baseline:
            d = abs(_to_float(v) - baseline[k])
            if d > max_dev:
                max_dev = d
    if max_dev < 0.15:
        return True, 0.0, "within_critic_tolerance"
    if anchor_consistency < 0.3:
        return False, min(1.0, max_dev), "low_anchor_consistency"
    penalty = _clamp((max_dev - 0.15) * 2.0, 0.0, 0.8)
    return True, penalty, "scaled_by_critic_deviation"


def _apply_plasticity_adjustment(con, eff, neuromod, meta_state):
    if eff.get("skip_no_fresh_source"):
        return {"adjustment_type":"skipped_no_fresh_source","pre":{},"post":{},"critic_gate_result":"not_run",
                "critic_penalty":0.0,"evidence_state":"stale_source_observation","state_change_allowed":0}
    pre_plast=_to_float(meta_state.get("last_plasticity_level"),0.5); pre_expl=_to_float(meta_state.get("last_exploration_bias"),0.5); pre_cons=_to_float(meta_state.get("last_consolidation_bias"),0.5); pre_inh=_to_float(meta_state.get("last_inhibition_bias"),0.3); pre_rev=_to_float(meta_state.get("last_revision_bias"),0.5)
    post_plast,post_expl,post_cons,post_inh,post_rev=pre_plast,pre_expl,pre_cons,pre_inh,pre_rev
    state=str(eff.get("evidence_state") or "historical_unclassified"); allowed_state=1 if _to_int(eff.get("state_change_allowed"),0)>0 else 0; plateau=_to_int(eff.get("plateau_flag"),0); score=_to_float(eff.get("effectiveness_score"),0.0)
    cfg=_phase6c_cfg(con); adj="hold_no_evidence" if not allowed_state else "hold"; scale=1.0; reasons=["evidence_state:"+state]
    if allowed_state and plateau:
        adj="plateau_break"; scale=_clamp(_cfg_value(cfg,"plateau_break_scale",0.85)-0.10*neuromod["gaba"],0.55,0.98)
        post_plast=_clamp(pre_plast*scale); post_expl=_clamp(pre_expl+_cfg_value(cfg,"exploration_delta",0.15)*(1-neuromod["gaba"])+0.05*neuromod["noradrenaline"]); post_inh=_clamp(pre_inh+_cfg_value(cfg,"inhibition_delta",0.10)*neuromod["gaba"]+0.05*(1-neuromod["dopamine"])); post_rev=_clamp(pre_rev+_cfg_value(cfg,"revision_delta",0.10)*neuromod["serotonin"]+0.05*neuromod["acetylcholine"]); post_cons=_clamp(pre_cons-0.05*(1-score)); reasons.append("plateau_break_canonical")
    elif allowed_state and score>_cfg_value(cfg,"stabilize_threshold",0.02):
        adj="stabilize_gains"; post_cons=_clamp(pre_cons+_cfg_value(cfg,"consolidation_delta",0.05)*neuromod["dopamine"]+0.05*neuromod["glutamate"]); post_rev=_clamp(pre_rev-0.03*neuromod["serotonin"]); post_plast=_clamp(pre_plast+0.02*neuromod["dopamine"]); reasons.append("stabilize_positive_effectiveness")
    proposed={"plasticity_level":post_plast,"exploration_bias":post_expl,"consolidation_bias":post_cons,"inhibition_bias":post_inh,"revision_bias":post_rev}
    if allowed_state: gate,penalty,critic=_critic_gate(con,proposed,_to_float(eff.get("anchor_consistency"),0.0))
    else: gate,penalty,critic=False,0.0,"state_change_blocked_by_evidence_state"
    if not gate: post_plast,post_expl,post_cons,post_inh,post_rev=pre_plast,pre_expl,pre_cons,pre_inh,pre_rev
    elif penalty>0:
        blend=lambda a,b:_clamp(a+(b-a)*(1-penalty)); post_plast=blend(pre_plast,post_plast); post_expl=blend(pre_expl,post_expl); post_cons=blend(pre_cons,post_cons); post_inh=blend(pre_inh,post_inh); post_rev=blend(pre_rev,post_rev)
    con.execute("INSERT INTO phase6b_plasticity_adjustments (created_at,cycle_index,adjustment_type,reason,scale_factor,window_size,pre_plasticity_level,post_plasticity_level,pre_exploration_bias,post_exploration_bias,pre_consolidation_bias,post_consolidation_bias,pre_inhibition_bias,post_inhibition_bias,pre_revision_bias,post_revision_bias,dopamine,serotonin,noradrenaline,acetylcholine,glutamate,gaba,critic_gate_result,notes,measurement_event_id,evidence_state,state_change_allowed) VALUES("+",".join("?" for _ in range(27))+")",
      (_now(),_to_int(eff.get("cycle_index"),0),adj,";".join(reasons),scale,_to_int(eff.get("window_size"),5),pre_plast,post_plast,pre_expl,post_expl,pre_cons,post_cons,pre_inh,post_inh,pre_rev,post_rev,neuromod["dopamine"],neuromod["serotonin"],neuromod["noradrenaline"],neuromod["acetylcholine"],neuromod["glutamate"],neuromod["gaba"],critic,json.dumps({"eff":score,"plateau":plateau}),eff.get("measurement_event_id"),state,1 if gate and allowed_state else 0))
    if gate and allowed_state:
        for k,v in (("last_plasticity_level",post_plast),("last_exploration_bias",post_expl),("last_consolidation_bias",post_cons),("last_inhibition_bias",post_inh),("last_revision_bias",post_rev)):
            _kv_set(con,"phase6a_meta_plasticity_state",k,round(v,6)); _kv_set(con,"phase6a_neuromodulated_sleep_state",k,round(v,6))
    con.commit(); return {"adjustment_type":adj,"pre":{"plasticity_level":pre_plast,"exploration_bias":pre_expl,"consolidation_bias":pre_cons,"inhibition_bias":pre_inh,"revision_bias":pre_rev},"post":{"plasticity_level":post_plast,"exploration_bias":post_expl,"consolidation_bias":post_cons,"inhibition_bias":post_inh,"revision_bias":post_rev},"critic_gate_result":critic,"critic_penalty":penalty,"evidence_state":state,"state_change_allowed":1 if gate and allowed_state else 0}






def _distill_knowledge(con, cycle_index, eff_score, stability_threshold=0.7):
    if eff_score <= 0.0:
        return {"distilled": 0, "reason": "non_positive_effectiveness"}
    rows = con.execute(
        "SELECT id, anchor_key, stability_score, outcome_score_avg, "
        " overlap_score_avg, replay_count "
        "FROM phase6b_anchor_pool "
        "WHERE active=1 AND stability_score >= ? "
        "ORDER BY stability_score DESC LIMIT 50",
        (float(stability_threshold),),
    ).fetchall()
    inserted = 0
    for r in rows:
        akey = r[1]
        exists = con.execute(
            "SELECT id FROM phase6b_distilled_knowledge "
            "WHERE cycle_index=? AND knowledge_key=?",
            (int(cycle_index), akey),
        ).fetchone()
        if exists is not None:
            continue
        conf = _clamp(_to_float(r[2]) * 0.6 + _clamp(eff_score * 10.0) * 0.4)
        con.execute(
            "INSERT INTO phase6b_distilled_knowledge ("
            "created_at, cycle_index, source_kind, source_ref, "
            "knowledge_key, stability_score, effectiveness_score, "
            "anchor_alignment, confidence, distilled_from_count, notes) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (_now(), int(cycle_index), "anchor", akey.split(":", 1)[0],
             akey, _to_float(r[2]), float(eff_score),
             _to_float(r[4]), conf, _to_int(r[5]),
             "distilled_from_stable_anchor"),
        )
        inserted += 1
    con.commit()
    return {"distilled": inserted, "threshold": stability_threshold}


def _compute_l2m_metrics(con, cycle_index, eff):
    if eff.get("skip_no_fresh_source"):
        return {"skipped":True,"reason":"no_fresh_phase6a_source","evidence_state":"stale_source_observation"}
    row=con.execute("SELECT AVG(stability_score) FROM phase6b_anchor_pool WHERE active=1").fetchone(); anchor=_to_float(row[0] if row else 0.0,0.0)
    prev=con.execute("SELECT anchor_consistency FROM phase6b_effectiveness_events WHERE cycle_index<? AND measurement_owner='canonical_phase6b' ORDER BY id DESC LIMIT 1",(int(cycle_index),)).fetchone(); prev_stab=_to_float(prev[0] if prev else anchor,anchor)
    ft=_to_float(eff.get("delta_outcome"),0.0); bt=anchor-prev_stab; se=_to_float(eff.get("effectiveness_score"),0.0)/max(1,_to_int(eff.get("window_size"),1)); state=str(eff.get("evidence_state") or "historical_unclassified")
    alert=1 if bt < -0.05 else 0; reason="backward_transfer_negative" if alert else ("evidence_unavailable" if not state.startswith("outcome_observed_") else "ok")
    con.execute("INSERT INTO phase6b_l2m_metrics (created_at,cycle_index,performance_maintenance,forward_transfer,backward_transfer,sample_efficiency,performance_recovery,anchor_stability,alert_flag,alert_reason,measurement_event_id,evidence_state) VALUES("+",".join("?" for _ in range(12))+")",(_now(),int(cycle_index),anchor,ft,bt,se,0.0,anchor,alert,reason,eff.get("measurement_event_id"),state)); con.commit()
    return {"performance_maintenance":anchor,"forward_transfer":ft,"backward_transfer":bt,"sample_efficiency":se,"performance_recovery":0.0,"anchor_stability":anchor,"alert_flag":alert,"alert_reason":reason,"evidence_state":state}






def _maybe_snapshot_critic(con, neuromod, eff_score, adj, eff=None):
    eff=eff or {}; state=str(eff.get("evidence_state") or adj.get("evidence_state") or "historical_unclassified")
    if _to_int(adj.get("state_change_allowed"),0)<=0:
        return {"snapshot":False,"reason":"evidence_state_blocks_snapshot","evidence_state":state}
    sero=neuromod["serotonin"]; cfg=_phase6c_cfg(con); p=_clamp(_cfg_value(cfg,"critic_snapshot_p_base",0.05)+_cfg_value(cfg,"critic_snapshot_p_range",0.5)*sero,0.02,0.85)
    stable=_to_int(_read_kv(con,"phase6b_state").get("stable_cycles_since_snapshot"),0)+1; _kv_set(con,"phase6b_state","stable_cycles_since_snapshot",stable)
    minimum=max(3,int(round(_cfg_value(cfg,"critic_min_stable_base",3.0)+(1-sero)*4)))
    if stable<minimum: con.commit(); return {"snapshot":False,"reason":"not_enough_stable_cycles"}
    if random.random()>p: con.commit(); return {"snapshot":False,"reason":"probabilistic_skip"}
    con.execute("UPDATE phase6b_critic_snapshot SET active=0 WHERE active=1"); cnt=_to_int(con.execute("SELECT COUNT(*) FROM phase6b_anchor_pool WHERE active=1").fetchone()[0],0); post=adj.get("post",{})
    con.execute("INSERT INTO phase6b_critic_snapshot (created_at,reason,dopamine,serotonin,noradrenaline,acetylcholine,glutamate,gaba,plasticity_level,exploration_bias,consolidation_bias,inhibition_bias,revision_bias,anchor_count,effectiveness_avg,state_json,active,measurement_event_id,evidence_state,snapshot_owner) VALUES("+",".join("?" for _ in range(20))+")",(_now(),"canonical_phase6b_snapshot",neuromod["dopamine"],neuromod["serotonin"],neuromod["noradrenaline"],neuromod["acetylcholine"],neuromod["glutamate"],neuromod["gaba"],_to_float(post.get("plasticity_level")),_to_float(post.get("exploration_bias")),_to_float(post.get("consolidation_bias")),_to_float(post.get("inhibition_bias")),_to_float(post.get("revision_bias")),cnt,eff_score,json.dumps({"evidence_state":state}),1,eff.get("measurement_event_id"),state,"canonical_phase6b")); _kv_set(con,"phase6b_state","stable_cycles_since_snapshot",0); con.commit(); return {"snapshot":True,"reason":"canonical_phase6b","evidence_state":state}




def run_phase6b_cycle(db_or_obj=None, cycle_index=None):
    con = resolve_db(db_or_obj)
    ensure_schema(con)
    missing = _self_check_schema(con)
    if missing:
        return {"phase": PHASE, "status": "schema_check_failed",
                "missing_columns": missing}

    if cycle_index is None:
        cur_count = _to_int(_read_kv(con, "phase6b_state").get("cycle_count"), 0)
        cycle_index = cur_count + 1

    meta_state = _read_kv(con, "phase6a_meta_plasticity_state")
    sleep_state = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    neuromod = _neuromodulators(sleep_state)
    recent = _read_recent_cycles(con, 20)

    promoted = _promote_anchors(con)
    batch = _select_replay_batch(con, neuromod)
    eff = _measure_effectiveness(con, recent, batch, neuromod, cycle_index)
    adj = _apply_plasticity_adjustment(con, eff, neuromod, meta_state)
    l2m = _compute_l2m_metrics(con, cycle_index, eff)
    dist = _distill_knowledge(con, cycle_index, eff.get("effectiveness_score", 0.0))
    snap = _maybe_snapshot_critic(con, neuromod, eff.get("effectiveness_score", 0.0), adj, eff)

    _kv_set(con, "phase6b_state", "cycle_count", cycle_index)
    _kv_set(con, "phase6b_state", "last_cycle_at", _now())
    _kv_set(con, "phase6b_state", "phase", PHASE)
    _kv_set(con, "phase6b_state", "phase_version", PHASE_VERSION)
    _kv_set(con, "phase6b_state", "learning_mode", LEARNING_MODE)
    _kv_set(con, "phase6b_state", "no_word_blacklists", True)
    _kv_set(con, "phase6b_state", "direct_fact_writes", "disabled")
    _kv_set(con, "phase6b_state", "direct_relation_writes", "disabled")
    _kv_set(con, "phase6b_state", "fact_promotion", "disabled")
    _kv_set(con, "phase6b_state", "question_generation", "internal_learning_questions_only")

    con.commit()

    return {
        "phase": PHASE,
        "cycle_index": cycle_index,
        "status": "ok",
        "anchors_promoted": promoted,
        "replay_batch": {"batch_size": batch.get("batch_size"),
                         "novel_count": batch.get("novel_count"),
                         "anchor_count": batch.get("anchor_count"),
                         "novel_ratio_target": batch.get("novel_ratio_target")},
        "effectiveness": eff,
        "plasticity_adjustment": adj,
        "l2m_metrics": l2m,
        "distilled": dist,
        "critic_snapshot": snap,
        "safety": {"direct_fact_writes": "disabled",
                   "direct_relation_writes": "disabled",
                   "fact_promotion": "disabled",
                   "no_word_blacklists": True},
    }


# =========================================================================
# AutonomousLoop integration
# =========================================================================

def managed_cycle(self, progress=None):
    base_result = None
    try:
        from ki_system import v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release as base6a
        if getattr(base6a, "managed_cycle", None) is not managed_cycle:
            base_result = base6a.managed_cycle(self, progress)
    except Exception as exc:
        base_result = {"base6a_cycle_error": str(exc)}
    try:
        db = resolve_db(self)
        phase6b = run_phase6b_cycle(db)
    except Exception as exc:
        phase6b = {"status": "phase6b_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "wake_and_sleep_result": base_result,
            "phase6b_effectiveness_and_plasticity": phase6b}


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
    AutonomousLoop.phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release = True
    AutonomousLoop._phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release = True
    AutonomousLoop.phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"
    AutonomousLoop.direct_relation_writes = "disabled"
    return AutonomousLoop
