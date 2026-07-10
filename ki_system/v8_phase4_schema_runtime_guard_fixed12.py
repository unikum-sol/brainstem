
# v8_phase4_schema_runtime_guard_fixed12.py
# Canonical Phase4 runtime schema manager FIXED12.
# Purpose: end recurring SQLite schema drift errors by enforcing all currently used
# and expected Phase4 columns/indices before every autonomous learning cycle.
# Safety: no word blacklists, no fact writes, no relation writes, no questions.
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

PHASE = "phase4_schema_runtime_guard_fixed12"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

# Canonical schema definition. All columns are added if missing. SQLite cannot add
# table constraints to existing tables, therefore ON CONFLICT targets are backed
# by UNIQUE INDEXes below.
TABLE_COLUMNS = {
    "reading_queue": {
        "chunk_id": "INTEGER", "priority": "REAL DEFAULT 0", "reason": "TEXT",
        "attention_score": "REAL DEFAULT 0", "read_count": "INTEGER DEFAULT 0",
        "status": "TEXT DEFAULT 'pending'", "last_read": "INTEGER DEFAULT 0", "updated_at": "INTEGER DEFAULT 0",
    },
    "context_hypotheses": {
        "chunk_id": "INTEGER", "role": "TEXT", "subject": "TEXT", "relation_hint": "TEXT", "object": "TEXT",
        "text_excerpt": "TEXT", "source_title": "TEXT", "confidence": "REAL DEFAULT 0", "uncertainty": "REAL DEFAULT 1",
        "status": "TEXT DEFAULT 'hypothesis'", "dopamine": "REAL DEFAULT 0", "serotonin": "REAL DEFAULT 0",
        "glutamate": "REAL DEFAULT 0", "gaba": "REAL DEFAULT 0", "noradrenaline": "REAL DEFAULT 0",
        "acetylcholine": "REAL DEFAULT 0", "signature": "TEXT", "evidence_count": "INTEGER DEFAULT 1",
        "created_at": "INTEGER DEFAULT 0", "updated_at": "INTEGER DEFAULT 0",
    },
    "context_learning_events": {
        "hypothesis_id": "INTEGER", "event_type": "TEXT", "role": "TEXT", "details": "TEXT",
        "dopamine": "REAL DEFAULT 0", "serotonin": "REAL DEFAULT 0", "glutamate": "REAL DEFAULT 0",
        "gaba": "REAL DEFAULT 0", "noradrenaline": "REAL DEFAULT 0", "acetylcholine": "REAL DEFAULT 0",
        "created_at": "INTEGER DEFAULT 0",
    },
    "hypothesis_feedback": {
        "hypothesis_id": "INTEGER", "feedback_type": "TEXT", "signal": "REAL DEFAULT 0",
        "reason": "TEXT", "details": "TEXT", "created_at": "INTEGER DEFAULT 0",
    },
    "hypothesis_revisions": {
        "hypothesis_id": "INTEGER", "old_role": "TEXT", "new_role": "TEXT",
        "old_confidence": "REAL DEFAULT 0", "new_confidence": "REAL DEFAULT 0",
        "reason": "TEXT", "details": "TEXT", "created_at": "INTEGER DEFAULT 0",
    },
    "hypothesis_error_events": {
        "hypothesis_id": "INTEGER", "error_type": "TEXT", "severity": "REAL DEFAULT 0",
        "reason": "TEXT", "details": "TEXT", "role": "TEXT", "error_signal": "REAL DEFAULT 0",
        "created_at": "INTEGER DEFAULT 0",
    },
    "neuromodulated_attention_events": {
        "chunk_id": "INTEGER", "hypothesis_id": "INTEGER", "attention_reason": "TEXT",
        "novelty": "REAL DEFAULT 0", "uncertainty": "REAL DEFAULT 0", "reward": "REAL DEFAULT 0", "fatigue": "REAL DEFAULT 0",
        "dopamine": "REAL DEFAULT 0", "serotonin": "REAL DEFAULT 0", "glutamate": "REAL DEFAULT 0", "gaba": "REAL DEFAULT 0",
        "noradrenaline": "REAL DEFAULT 0", "acetylcholine": "REAL DEFAULT 0", "summary": "TEXT", "details": "TEXT",
        "created_at": "INTEGER DEFAULT 0",
    },
    "context_role_stats": {
        "role": "TEXT", "seen": "INTEGER DEFAULT 0", "seen_count": "INTEGER DEFAULT 0",
        "avg_confidence": "REAL DEFAULT 0", "avg_uncertainty": "REAL DEFAULT 0",
        "feedback_count": "INTEGER DEFAULT 0", "error_count": "INTEGER DEFAULT 0", "updated_at": "INTEGER DEFAULT 0",
    },
    "chunk_attention_scores": {
        "chunk_id": "INTEGER", "attention_score": "REAL DEFAULT 0", "novelty_score": "REAL DEFAULT 0",
        "uncertainty_score": "REAL DEFAULT 0", "reward_score": "REAL DEFAULT 0", "fatigue_score": "REAL DEFAULT 0",
        "last_reason": "TEXT", "updated_at": "INTEGER DEFAULT 0",
    },
    "attention_queue_state": {"key": "TEXT", "value": "TEXT", "updated_at": "INTEGER DEFAULT 0"},
    "reading_strategy_state": {"key": "TEXT", "value": "TEXT", "updated_at": "INTEGER DEFAULT 0"},
    "hypothesis_clusters": {
        "cluster_key": "TEXT", "role": "TEXT", "size": "INTEGER DEFAULT 0",
        "avg_confidence": "REAL DEFAULT 0", "avg_uncertainty": "REAL DEFAULT 0", "stability": "REAL DEFAULT 0",
        "example": "TEXT", "updated_at": "INTEGER DEFAULT 0",
    },
    "hypothesis_stability_scores": {
        "hypothesis_id": "INTEGER", "stability": "REAL DEFAULT 0", "confidence": "REAL DEFAULT 0",
        "uncertainty": "REAL DEFAULT 0", "evidence_count": "INTEGER DEFAULT 0",
        "feedback_count": "INTEGER DEFAULT 0", "error_count": "INTEGER DEFAULT 0", "conflict_count": "INTEGER DEFAULT 0",
        "last_reason": "TEXT", "role": "TEXT", "updated_at": "INTEGER DEFAULT 0",
    },
    "context_pattern_memory": {
        "pattern_key": "TEXT", "role": "TEXT", "seen_count": "INTEGER DEFAULT 0",
        "avg_confidence": "REAL DEFAULT 0", "avg_uncertainty": "REAL DEFAULT 0", "stability": "REAL DEFAULT 0",
        "updated_at": "INTEGER DEFAULT 0",
    },
    "neuromodulator_sleep_events": {
        "event_type": "TEXT", "summary": "TEXT", "details": "TEXT",
        "dopamine": "REAL DEFAULT 0", "serotonin": "REAL DEFAULT 0", "glutamate": "REAL DEFAULT 0", "gaba": "REAL DEFAULT 0",
        "noradrenaline": "REAL DEFAULT 0", "acetylcholine": "REAL DEFAULT 0", "created_at": "INTEGER DEFAULT 0",
    },
    "learning_strategy_state": {"key": "TEXT", "value": "TEXT", "updated_at": "INTEGER DEFAULT 0"},
    "rollback_safe_core_state": {"key": "TEXT", "value": "TEXT", "updated_at": "INTEGER DEFAULT 0"},
}

UNIQUE_TARGETS = [
    ("reading_queue", "chunk_id"),
    ("context_role_stats", "role"),
    ("chunk_attention_scores", "chunk_id"),
    ("attention_queue_state", "key"),
    ("reading_strategy_state", "key"),
    ("hypothesis_clusters", "cluster_key"),
    ("hypothesis_stability_scores", "hypothesis_id"),
    ("context_pattern_memory", "pattern_key"),
    ("learning_strategy_state", "key"),
    ("rollback_safe_core_state", "key"),
]


def _conn_from_mem(mem):
    if isinstance(mem, sqlite3.Connection):
        return mem, False
    for attr in ("db", "conn", "connection"):
        obj = getattr(mem, attr, None)
        if isinstance(obj, sqlite3.Connection):
            return obj, False
    path = getattr(mem, "path", None) or getattr(mem, "db_path", None) or mem or "ki_memory.sqlite3"
    return sqlite3.connect(str(path)), True


def _mem_from_loop(loop):
    for name in ("mem", "memory", "m", "store", "memory_store"):
        obj = getattr(loop, name, None)
        if obj is not None:
            return obj
    for obj in getattr(loop, "__dict__", {}).values():
        if isinstance(obj, sqlite3.Connection) or isinstance(getattr(obj, "db", None), sqlite3.Connection):
            return obj
    return "ki_memory.sqlite3"


def _table_exists(cur, table):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur, table):
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _create_table(cur, table, columns):
    # id column is only added to event/history tables where row identity is useful, not to state/upsert tables.
    no_id = {"reading_queue", "context_role_stats", "chunk_attention_scores", "attention_queue_state", "reading_strategy_state", "hypothesis_clusters", "hypothesis_stability_scores", "context_pattern_memory", "learning_strategy_state", "rollback_safe_core_state"}
    parts=[] if table in no_id else ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    parts += [f"{c} {t}" for c,t in columns.items()]
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(parts)})")


def _add_missing_columns(cur, table, columns, changes):
    existing = set(_cols(cur, table))
    for col, typ in columns.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            changes.append(f"add_column:{table}.{col}")


def _unique_index(cur, table, col, changes):
    if not _table_exists(cur, table) or col not in _cols(cur, table):
        return
    # Remove duplicate cache/state rows only for derived state tables.
    dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
    if dup:
        cur.execute(f"DELETE FROM {table} WHERE rowid NOT IN (SELECT MIN(rowid) FROM {table} GROUP BY {col})")
        changes.append(f"dedupe:{table}.{col}")
    idx = f"idx_{table}_{col}_phase4_fixed12_unique"
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
    changes.append(f"unique_index:{table}.{col}")


def ensure_phase4_schema(mem=None):
    con, close = _conn_from_mem(mem)
    cur = con.cursor()
    changes=[]
    now=int(time.time())
    for table, columns in TABLE_COLUMNS.items():
        _create_table(cur, table, columns)
        _add_missing_columns(cur, table, columns, changes)
    # Backfills / aliases
    if _table_exists(cur, "context_role_stats"):
        cur.execute("UPDATE context_role_stats SET seen_count=COALESCE(NULLIF(seen_count,0), COALESCE(seen,0))")
    for table,col in UNIQUE_TARGETS:
        _unique_index(cur, table, col, changes)
    # Seed / update state
    state = {
        "phase": PHASE,
        "no_word_blacklists": "true",
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
    }
    for k,v in state.items():
        cur.execute("INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, repr(v), now))
    con.commit()
    if close:
        con.close()
    return {"status": PHASE, "changes": changes}


def patch_autonomous_loop(*args, **kwargs):
    from ki_system.autonomous import AutonomousLoop
    import ki_system.v8_phase4def_context_learning_pack as phase4def
    orig_run = phase4def.safe_run
    orig_cycle = phase4def.safe_cycle
    def guarded_cycle(self, progress=None):
        ensure_phase4_schema(_mem_from_loop(self))
        return orig_cycle(self, progress)
    def guarded_run(self, cycles=5, progress=None):
        ensure_phase4_schema(_mem_from_loop(self))
        return orig_run(self, cycles, progress)
    AutonomousLoop.cycle = guarded_cycle
    AutonomousLoop.run = guarded_run
    markers = {
        "phase4_schema_runtime_guard_fixed12": True,
        "phase4_schema_manager_canonicalization": True,
        "phase4d_hypothesis_feedback_error_learning": True,
        "phase4e_neuromodulated_attention_strategy": True,
        "phase4f_sleep_consolidation_self_improvement": True,
        "phase4def_context_learning_pack": True,
        "no_word_blacklists": True,
        "learning_mode": LEARNING_MODE,
        "rollback_learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
    }
    for k,v in markers.items():
        setattr(AutonomousLoop, k, v)
        setattr(AutonomousLoop, '_' + k, v)
    return True

try:
    patch_autonomous_loop()
except Exception as exc:
    print('[PHASE4_SCHEMA_RUNTIME_GUARD_FIXED12_AUTOLOAD_ERROR]', exc)
