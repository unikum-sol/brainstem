
# -*- coding: utf-8 -*-
"""V8-phase4o_strategy_effectiveness_feedback_loop

Strategy effectiveness feedback for neuromodulated context-hypothesis learning.
No word blacklists. No facts/relations/questions writes. No fact promotion.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

PHASE = "phase4o_strategy_effectiveness_feedback_loop"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _now() -> int:
    return int(time.time())


def _json(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps(str(obj), ensure_ascii=False)


def _project_db_path() -> str:
    return str(Path.cwd() / "ki_memory.sqlite3")


def _connect():
    return sqlite3.connect(_project_db_path())


def _table_exists(cur, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur, table: str) -> set[str]:
    if not _table_exists(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_table(cur, table: str, ddl: str, columns: dict[str, str], changes: list[str]):
    if not _table_exists(cur, table):
        cur.execute(ddl)
        changes.append(f"create_table:{table}")
    existing = _cols(cur, table)
    for col, spec in columns.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {spec}")
            changes.append(f"add_column:{table}.{col}")


def _unique_index(cur, table: str, column: str, changes: list[str]):
    if _table_exists(cur, table) and column in _cols(cur, table):
        idx = f"idx_{table}_{column}_phase4o_unique"
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({column})")
        changes.append(f"unique_index:{table}.{column}")


def ensure_phase4o_schema(db=None):
    own = db is None
    if db is None:
        db = _connect()
    cur = db.cursor()
    changes: list[str] = []

    _ensure_table(cur, "strategy_feedback_events", """
        CREATE TABLE IF NOT EXISTS strategy_feedback_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_key TEXT,
            event_type TEXT,
            progress_score REAL DEFAULT 0,
            error_pressure REAL DEFAULT 0,
            uncertainty_pressure REAL DEFAULT 0,
            stability_gain REAL DEFAULT 0,
            exploration_need REAL DEFAULT 0,
            outcome_score REAL DEFAULT 0,
            recommendation TEXT,
            details TEXT,
            created_at INTEGER DEFAULT 0
        )
    """, {
        "strategy_key": "TEXT", "event_type": "TEXT", "progress_score": "REAL DEFAULT 0",
        "error_pressure": "REAL DEFAULT 0", "uncertainty_pressure": "REAL DEFAULT 0",
        "stability_gain": "REAL DEFAULT 0", "exploration_need": "REAL DEFAULT 0",
        "outcome_score": "REAL DEFAULT 0", "recommendation": "TEXT", "details": "TEXT",
        "created_at": "INTEGER DEFAULT 0"
    }, changes)

    _ensure_table(cur, "strategy_outcome_memory", """
        CREATE TABLE IF NOT EXISTS strategy_outcome_memory(
            strategy_key TEXT PRIMARY KEY,
            observations INTEGER DEFAULT 0,
            avg_progress_score REAL DEFAULT 0,
            avg_error_pressure REAL DEFAULT 0,
            avg_uncertainty_pressure REAL DEFAULT 0,
            avg_stability_gain REAL DEFAULT 0,
            avg_exploration_need REAL DEFAULT 0,
            effectiveness_score REAL DEFAULT 0,
            last_recommendation TEXT,
            last_details TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """, {
        "strategy_key": "TEXT", "observations": "INTEGER DEFAULT 0",
        "avg_progress_score": "REAL DEFAULT 0", "avg_error_pressure": "REAL DEFAULT 0",
        "avg_uncertainty_pressure": "REAL DEFAULT 0", "avg_stability_gain": "REAL DEFAULT 0",
        "avg_exploration_need": "REAL DEFAULT 0", "effectiveness_score": "REAL DEFAULT 0",
        "last_recommendation": "TEXT", "last_details": "TEXT", "updated_at": "INTEGER DEFAULT 0"
    }, changes)

    _ensure_table(cur, "strategy_adjustment_recommendations", """
        CREATE TABLE IF NOT EXISTS strategy_adjustment_recommendations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_key TEXT,
            control_name TEXT,
            current_value REAL DEFAULT 0,
            recommended_value REAL DEFAULT 0,
            reason TEXT,
            strength REAL DEFAULT 0,
            status TEXT DEFAULT 'open',
            created_at INTEGER DEFAULT 0
        )
    """, {
        "strategy_key": "TEXT", "control_name": "TEXT", "current_value": "REAL DEFAULT 0",
        "recommended_value": "REAL DEFAULT 0", "reason": "TEXT", "strength": "REAL DEFAULT 0",
        "status": "TEXT DEFAULT 'open'", "created_at": "INTEGER DEFAULT 0"
    }, changes)

    _ensure_table(cur, "strategy_effectiveness_feedback_state", """
        CREATE TABLE IF NOT EXISTS strategy_effectiveness_feedback_state(
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """, {"key": "TEXT", "value": "TEXT", "updated_at": "INTEGER DEFAULT 0"}, changes)

    # compatibility/extension columns on existing learning tables
    if _table_exists(cur, "context_hypotheses"):
        cols = _cols(cur, "context_hypotheses")
        for col, spec in {
            "strategy_effectiveness_score": "REAL DEFAULT 0",
            "last_strategy_feedback_at": "INTEGER DEFAULT 0",
            "strategy_feedback_reason": "TEXT",
        }.items():
            if col not in cols:
                cur.execute(f"ALTER TABLE context_hypotheses ADD COLUMN {col} {spec}")
                changes.append(f"add_column:context_hypotheses.{col}")
    if _table_exists(cur, "internal_learning_gaps"):
        cols = _cols(cur, "internal_learning_gaps")
        for col, spec in {
            "strategy_effectiveness_score": "REAL DEFAULT 0",
            "strategy_feedback_reason": "TEXT",
            "last_strategy_feedback_at": "INTEGER DEFAULT 0",
        }.items():
            if col not in cols:
                cur.execute(f"ALTER TABLE internal_learning_gaps ADD COLUMN {col} {spec}")
                changes.append(f"add_column:internal_learning_gaps.{col}")
    if _table_exists(cur, "chunk_attention_scores"):
        cols = _cols(cur, "chunk_attention_scores")
        for col, spec in {
            "strategy_effectiveness_score": "REAL DEFAULT 0",
            "strategy_feedback_reason": "TEXT",
            "last_strategy_feedback_at": "INTEGER DEFAULT 0",
        }.items():
            if col not in cols:
                cur.execute(f"ALTER TABLE chunk_attention_scores ADD COLUMN {col} {spec}")
                changes.append(f"add_column:chunk_attention_scores.{col}")

    for table, col in [
        ("strategy_outcome_memory", "strategy_key"),
        ("strategy_effectiveness_feedback_state", "key"),
    ]:
        _unique_index(cur, table, col, changes)

    now = _now()
    state = {
        "phase": PHASE,
        "no_word_blacklists": "true",
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
    }
    for k, v in state.items():
        cur.execute("INSERT INTO strategy_effectiveness_feedback_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, str(v), now))
    db.commit()
    if own:
        db.close()
    return {"status": "ok", "phase": PHASE, "changes": changes}


def _latest_progress(cur):
    if not _table_exists(cur, "learning_progress_evaluations"):
        return None
    cols = _cols(cur, "learning_progress_evaluations")
    want = ["progress_score", "error_pressure", "uncertainty_pressure", "stability_gain", "exploration_need", "created_at"]
    exprs = []
    for w in want:
        exprs.append(w if w in cols else "0 AS " + w)
    row = cur.execute("SELECT " + ",".join(exprs) + " FROM learning_progress_evaluations ORDER BY created_at DESC, rowid DESC LIMIT 1").fetchone()
    return row


def _state_value(cur, table: str, key: str, default=0.0):
    if not _table_exists(cur, table):
        return default
    cols = _cols(cur, table)
    if not {"key", "value"}.issubset(cols):
        return default
    row = cur.execute(f"SELECT value FROM {table} WHERE key=?", (key,)).fetchone()
    if not row:
        return default
    try:
        return float(str(row[0]).strip("'\""))
    except Exception:
        return default


def _recommendations(progress, error, uncertainty, stability, exploration):
    # conservative, neuromodulated strategy feedback without writing facts/relations/questions
    current = {
        "learning_rate": 0.234,
        "error_weight": 0.407,
        "revision_pressure": 0.312,
        "exploration_pressure": 0.310,
        "inhibition_level": 0.349,
        "consolidation_gain": 0.297,
    }
    rec = {}
    reason = {}
    # if progress weak or stability low -> more exploration/revision, less premature consolidation
    if progress < 0.35 or stability < 0.05:
        rec["learning_rate"] = current["learning_rate"] * 0.96
        rec["error_weight"] = min(0.65, current["error_weight"] + 0.025)
        rec["revision_pressure"] = min(0.60, current["revision_pressure"] + 0.018)
        rec["exploration_pressure"] = min(0.60, current["exploration_pressure"] + 0.02)
        rec["inhibition_level"] = min(0.65, current["inhibition_level"] + 0.018)
        rec["consolidation_gain"] = max(0.15, current["consolidation_gain"] - 0.012)
        r = "low_progress_or_low_stability"
    elif progress > 0.75 and stability > 0.08:
        rec["learning_rate"] = min(0.34, current["learning_rate"] + 0.012)
        rec["error_weight"] = current["error_weight"]
        rec["revision_pressure"] = current["revision_pressure"]
        rec["exploration_pressure"] = max(0.20, current["exploration_pressure"] - 0.006)
        rec["inhibition_level"] = current["inhibition_level"]
        rec["consolidation_gain"] = min(0.42, current["consolidation_gain"] + 0.014)
        r = "productive_progress_with_stability_gain"
    else:
        rec = current.copy()
        r = "observe_and_adapt"
    # Persistent error pressure increases correction emphasis
    if error > 0.65:
        rec["error_weight"] = min(0.7, rec["error_weight"] + 0.02)
        rec["revision_pressure"] = min(0.65, rec["revision_pressure"] + 0.012)
        rec["inhibition_level"] = min(0.7, rec["inhibition_level"] + 0.012)
        r += "+high_error_pressure"
    # uncertainty pressure invites context diversity
    if uncertainty > 0.10 or exploration > 0.36:
        rec["exploration_pressure"] = min(0.65, rec["exploration_pressure"] + 0.015)
        r += "+uncertainty_or_exploration_need"
    for k in rec:
        reason[k] = r
    return current, rec, reason


def evaluate_strategy_effectiveness(db=None):
    own = db is None
    if db is None:
        db = _connect()
    ensure_phase4o_schema(db)
    cur = db.cursor()
    now = _now()
    row = _latest_progress(cur)
    if row:
        progress, error, uncertainty, stability, exploration, created_at = [float(x or 0) for x in row]
    else:
        progress = error = uncertainty = stability = exploration = 0.0
    outcome = max(0.0, min(1.0, 0.45*progress + 0.35*stability + 0.20*(1.0 - min(1.0, uncertainty))))
    if progress >= 0.75 and stability >= 0.05:
        recommendation = "reinforce_current_strategy"
    elif error > 0.65 or uncertainty > 0.10:
        recommendation = "increase_revision_and_context_diversity"
    else:
        recommendation = "observe_and_adapt"
    strategy_key = "global_neuromodulated_active_learning_strategy"
    details = {
        "source": "phase4o_strategy_effectiveness_feedback_loop",
        "progress_score": round(progress, 6),
        "error_pressure": round(error, 6),
        "uncertainty_pressure": round(uncertainty, 6),
        "stability_gain": round(stability, 6),
        "exploration_need": round(exploration, 6),
        "outcome_score": round(outcome, 6),
        "no_word_blacklists": True,
    }
    cur.execute("""INSERT INTO strategy_feedback_events(strategy_key,event_type,progress_score,error_pressure,uncertainty_pressure,stability_gain,exploration_need,outcome_score,recommendation,details,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (strategy_key, "progress_feedback", progress, error, uncertainty, stability, exploration, outcome, recommendation, _json(details), now))
    prev = cur.execute("SELECT observations,avg_progress_score,avg_error_pressure,avg_uncertainty_pressure,avg_stability_gain,avg_exploration_need,effectiveness_score FROM strategy_outcome_memory WHERE strategy_key=?", (strategy_key,)).fetchone()
    if prev:
        obs = int(prev[0] or 0) + 1
        avgs = []
        vals = [progress, error, uncertainty, stability, exploration, outcome]
        for old, val in zip(prev[1:], vals):
            avgs.append(((float(old or 0) * (obs-1)) + val) / obs)
    else:
        obs = 1
        avgs = [progress, error, uncertainty, stability, exploration, outcome]
    cur.execute("""INSERT INTO strategy_outcome_memory(strategy_key,observations,avg_progress_score,avg_error_pressure,avg_uncertainty_pressure,avg_stability_gain,avg_exploration_need,effectiveness_score,last_recommendation,last_details,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(strategy_key) DO UPDATE SET observations=excluded.observations, avg_progress_score=excluded.avg_progress_score, avg_error_pressure=excluded.avg_error_pressure, avg_uncertainty_pressure=excluded.avg_uncertainty_pressure, avg_stability_gain=excluded.avg_stability_gain, avg_exploration_need=excluded.avg_exploration_need, effectiveness_score=excluded.effectiveness_score, last_recommendation=excluded.last_recommendation, last_details=excluded.last_details, updated_at=excluded.updated_at""", (strategy_key, obs, *avgs, recommendation, _json(details), now))
    current, recs, reasons = _recommendations(progress, error, uncertainty, stability, exploration)
    inserted_recs = 0
    for name, rec_val in recs.items():
        cur.execute("INSERT INTO strategy_adjustment_recommendations(strategy_key,control_name,current_value,recommended_value,reason,strength,status,created_at) VALUES(?,?,?,?,?,?,?,?)", (strategy_key, name, float(current.get(name, 0)), float(rec_val), reasons.get(name, recommendation), abs(float(rec_val)-float(current.get(name,0))), "open", now))
        inserted_recs += 1
    # Apply as proposals into controller state, not direct fact/relations/questions.
    for k, v in {
        "phase": PHASE,
        "last_strategy_feedback_at": now,
        "last_strategy_outcome_score": round(outcome, 6),
        "last_strategy_recommendation": recommendation,
        "last_strategy_recommendations": inserted_recs,
        "no_word_blacklists": "true",
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
    }.items():
        cur.execute("INSERT INTO strategy_effectiveness_feedback_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, str(v), now))
    # update a small slice of hypothesis/gap/chunk scores for monitoring
    updated_h = updated_g = updated_c = 0
    if _table_exists(cur, "context_hypotheses") and "strategy_effectiveness_score" in _cols(cur, "context_hypotheses"):
        cur.execute("UPDATE context_hypotheses SET strategy_effectiveness_score=?, last_strategy_feedback_at=?, strategy_feedback_reason=? WHERE id IN (SELECT id FROM context_hypotheses ORDER BY COALESCE(active_learning_score,0) DESC, id DESC LIMIT 250)", (outcome, now, PHASE))
        updated_h = cur.rowcount if cur.rowcount != -1 else 0
    if _table_exists(cur, "internal_learning_gaps") and "strategy_effectiveness_score" in _cols(cur, "internal_learning_gaps"):
        cur.execute("UPDATE internal_learning_gaps SET strategy_effectiveness_score=?, last_strategy_feedback_at=?, strategy_feedback_reason=? WHERE rowid IN (SELECT rowid FROM internal_learning_gaps ORDER BY COALESCE(priority,0) DESC, rowid DESC LIMIT 80)", (outcome, now, PHASE))
        updated_g = cur.rowcount if cur.rowcount != -1 else 0
    if _table_exists(cur, "chunk_attention_scores") and "strategy_effectiveness_score" in _cols(cur, "chunk_attention_scores"):
        cur.execute("UPDATE chunk_attention_scores SET strategy_effectiveness_score=?, last_strategy_feedback_at=?, strategy_feedback_reason=? WHERE chunk_id IN (SELECT chunk_id FROM chunk_attention_scores ORDER BY COALESCE(active_learning_score,attention_score,0) DESC LIMIT 400)", (outcome, now, PHASE))
        updated_c = cur.rowcount if cur.rowcount != -1 else 0
    db.commit()
    result = {
        "status": "phase4o_strategy_effectiveness_feedback_complete",
        "phase": PHASE,
        "progress_score": round(progress, 6),
        "error_pressure": round(error, 6),
        "uncertainty_pressure": round(uncertainty, 6),
        "stability_gain": round(stability, 6),
        "exploration_need": round(exploration, 6),
        "outcome_score": round(outcome, 6),
        "recommendation": recommendation,
        "strategy_observations": obs,
        "recommendations_written": inserted_recs,
        "updated_hypotheses": updated_h,
        "updated_gaps": updated_g,
        "updated_chunks": updated_c,
        "no_word_blacklists": True,
        "fact_promotion": "disabled",
    }
    if own:
        db.close()
    return result


def _base_phase4n():
    from ki_system import v8_phase4n_learning_progress_evaluation_and_adaptive_strategy as phase4n
    return phase4n


def managed_cycle(self, progress=None):
    base = _base_phase4n()
    base_result = base.managed_cycle(self, progress)
    feedback = evaluate_strategy_effectiveness()
    return {
        "status": "phase4o_managed_cycle",
        "base": base_result,
        "strategy_effectiveness_feedback": feedback,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
        "fact_promotion": "disabled",
        "no_word_blacklists": True,
    }


def managed_run(self, cycles=5, progress=None):
    base = _base_phase4n()
    base_result = base.managed_run(self, cycles, progress)
    feedback = evaluate_strategy_effectiveness()
    return {
        "status": "phase4o_managed_run",
        "base": base_result,
        "strategy_effectiveness_feedback": feedback,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
        "fact_promotion": "disabled",
        "no_word_blacklists": True,
    }


def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AL
    else:
        AL = AutonomousLoop
    AL.cycle = managed_cycle
    AL.run = managed_run
    for name in [
        "phase4o_strategy_effectiveness_feedback_loop",
        "_phase4o_strategy_effectiveness_feedback_loop",
        "phase4n_learning_progress_evaluation_and_adaptive_strategy",
        "phase4m_active_learning_loop_controller",
    ]:
        setattr(AL, name, True)
    AL.no_word_blacklists = True
    AL._no_word_blacklists = True
    AL.learning_mode = LEARNING_MODE
    AL._rollback_learning_mode = LEARNING_MODE
    AL.fact_promotion = "disabled"
    AL._fact_promotion = "disabled"
    return AL
