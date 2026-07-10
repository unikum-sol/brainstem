
"""Phase4def schema canonicalizer FIXED8.

Purpose:
- Canonicalize Phase4 context-learning schemas before every cycle/run.
- Add missing columns and unique indexes required by ON CONFLICT clauses.
- Keep no-word-blacklists / no facts / no relations / no questions guarantees.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

FIXED8_MARKER = True

TABLE_COLUMNS = {
    "context_hypotheses": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("chunk_id", "INTEGER"),
        ("role", "TEXT"),
        ("subject", "TEXT"),
        ("relation_hint", "TEXT"),
        ("object", "TEXT"),
        ("text_excerpt", "TEXT"),
        ("source_title", "TEXT"),
        ("confidence", "REAL DEFAULT 0"),
        ("uncertainty", "REAL DEFAULT 1"),
        ("status", "TEXT DEFAULT 'hypothesis'"),
        ("dopamine", "REAL DEFAULT 0"),
        ("serotonin", "REAL DEFAULT 0"),
        ("glutamate", "REAL DEFAULT 0"),
        ("gaba", "REAL DEFAULT 0"),
        ("noradrenaline", "REAL DEFAULT 0"),
        ("acetylcholine", "REAL DEFAULT 0"),
        ("signature", "TEXT"),
        ("evidence_count", "INTEGER DEFAULT 1"),
        ("created_at", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "context_learning_events": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("hypothesis_id", "INTEGER"),
        ("event_type", "TEXT"),
        ("role", "TEXT"),
        ("details", "TEXT"),
        ("dopamine", "REAL DEFAULT 0"),
        ("serotonin", "REAL DEFAULT 0"),
        ("glutamate", "REAL DEFAULT 0"),
        ("gaba", "REAL DEFAULT 0"),
        ("noradrenaline", "REAL DEFAULT 0"),
        ("acetylcholine", "REAL DEFAULT 0"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_feedback": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("hypothesis_id", "INTEGER"),
        ("feedback_type", "TEXT"),
        ("signal", "REAL DEFAULT 0"),
        ("reason", "TEXT"),
        ("details", "TEXT"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_revisions": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("hypothesis_id", "INTEGER"),
        ("old_role", "TEXT"),
        ("new_role", "TEXT"),
        ("reason", "TEXT"),
        ("details", "TEXT"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_error_events": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("hypothesis_id", "INTEGER"),
        ("error_type", "TEXT"),
        ("severity", "REAL DEFAULT 0"),
        ("details", "TEXT"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "neuromodulated_attention_events": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("chunk_id", "INTEGER"),
        ("hypothesis_id", "INTEGER"),
        ("event_type", "TEXT"),
        ("novelty", "REAL DEFAULT 0"),
        ("uncertainty", "REAL DEFAULT 0"),
        ("reward", "REAL DEFAULT 0"),
        ("fatigue", "REAL DEFAULT 0"),
        ("dopamine", "REAL DEFAULT 0"),
        ("serotonin", "REAL DEFAULT 0"),
        ("glutamate", "REAL DEFAULT 0"),
        ("gaba", "REAL DEFAULT 0"),
        ("noradrenaline", "REAL DEFAULT 0"),
        ("acetylcholine", "REAL DEFAULT 0"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "context_role_stats": [
        ("role", "TEXT PRIMARY KEY"),
        ("seen", "INTEGER DEFAULT 0"),
        ("seen_count", "INTEGER DEFAULT 0"),
        ("avg_confidence", "REAL DEFAULT 0"),
        ("avg_uncertainty", "REAL DEFAULT 0"),
        ("feedback_count", "INTEGER DEFAULT 0"),
        ("error_count", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "chunk_attention_scores": [
        ("chunk_id", "INTEGER PRIMARY KEY"),
        ("attention_score", "REAL DEFAULT 0"),
        ("novelty_score", "REAL DEFAULT 0"),
        ("uncertainty_score", "REAL DEFAULT 0"),
        ("reward_score", "REAL DEFAULT 0"),
        ("fatigue_score", "REAL DEFAULT 0"),
        ("last_reason", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "attention_queue_state": [
        ("key", "TEXT PRIMARY KEY"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "reading_strategy_state": [
        ("key", "TEXT PRIMARY KEY"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_clusters": [
        ("cluster_key", "TEXT PRIMARY KEY"),
        ("role", "TEXT"),
        ("size", "INTEGER DEFAULT 0"),
        ("avg_confidence", "REAL DEFAULT 0"),
        ("avg_uncertainty", "REAL DEFAULT 0"),
        ("stability", "REAL DEFAULT 0"),
        ("example", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_stability_scores": [
        ("hypothesis_id", "INTEGER PRIMARY KEY"),
        ("stability", "REAL DEFAULT 0"),
        ("confidence", "REAL DEFAULT 0"),
        ("uncertainty", "REAL DEFAULT 0"),
        ("feedback_count", "INTEGER DEFAULT 0"),
        ("error_count", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "context_pattern_memory": [
        ("pattern_key", "TEXT PRIMARY KEY"),
        ("role", "TEXT"),
        ("seen_count", "INTEGER DEFAULT 0"),
        ("avg_confidence", "REAL DEFAULT 0"),
        ("avg_uncertainty", "REAL DEFAULT 0"),
        ("stability", "REAL DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "neuromodulator_sleep_events": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("event_type", "TEXT"),
        ("details", "TEXT"),
        ("dopamine", "REAL DEFAULT 0"),
        ("serotonin", "REAL DEFAULT 0"),
        ("glutamate", "REAL DEFAULT 0"),
        ("gaba", "REAL DEFAULT 0"),
        ("noradrenaline", "REAL DEFAULT 0"),
        ("acetylcholine", "REAL DEFAULT 0"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "learning_strategy_state": [
        ("key", "TEXT PRIMARY KEY"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "rollback_safe_core_state": [
        ("key", "TEXT PRIMARY KEY"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "reading_queue": [
        ("chunk_id", "INTEGER PRIMARY KEY"),
        ("priority", "REAL DEFAULT 0"),
        ("reason", "TEXT"),
        ("attention_score", "REAL DEFAULT 0"),
        ("read_count", "INTEGER DEFAULT 0"),
        ("status", "TEXT DEFAULT 'pending'"),
        ("last_read", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
}

UNIQUE_TARGETS = [
    ("hypothesis_clusters", "cluster_key"),
    ("context_pattern_memory", "pattern_key"),
    ("chunk_attention_scores", "chunk_id"),
    ("hypothesis_stability_scores", "hypothesis_id"),
    ("context_role_stats", "role"),
    ("reading_queue", "chunk_id"),
]

def _quote_ident(x: str) -> str:
    return '"' + x.replace('"', '""') + '"'

def _get_conn(db_or_mem):
    if isinstance(db_or_mem, sqlite3.Connection):
        return db_or_mem
    for attr in ("db", "conn", "connection"):
        c = getattr(db_or_mem, attr, None)
        if isinstance(c, sqlite3.Connection):
            return c
    # fallback project-local db
    return sqlite3.connect("ki_memory.sqlite3")

def _table_exists(cur, table):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _columns(cur, table):
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({_quote_ident(table)})").fetchall()]

def _create_table_sql(table, cols):
    parts = [f"{_quote_ident(name)} {spec}" for name, spec in cols]
    return f"CREATE TABLE IF NOT EXISTS {_quote_ident(table)} (" + ", ".join(parts) + ")"

def _add_missing_columns(cur, table, cols, changes):
    cur.execute(_create_table_sql(table, cols))
    existing = set(_columns(cur, table))
    for name, spec in cols:
        if name not in existing:
            cur.execute(f"ALTER TABLE {_quote_ident(table)} ADD COLUMN {_quote_ident(name)} {spec}")
            changes.append(f"add_column:{table}.{name}")

def _dedupe_for_unique(cur, table, column, changes):
    if not _table_exists(cur, table) or column not in _columns(cur, table):
        return
    dups = cur.execute(
        f"SELECT {_quote_ident(column)}, COUNT(*) FROM {_quote_ident(table)} GROUP BY {_quote_ident(column)} HAVING COUNT(*) > 1"
    ).fetchall()
    if not dups:
        return
    # Conservative: keep the lowest rowid per key for technical state tables.
    # These tables are derived/cache-like state, not source corpus/facts.
    cur.execute(
        f"DELETE FROM {_quote_ident(table)} WHERE rowid NOT IN (SELECT MIN(rowid) FROM {_quote_ident(table)} GROUP BY {_quote_ident(column)})"
    )
    changes.append(f"dedupe:{table}.{column}:{len(dups)}")

def ensure_phase4def_schema(db_or_mem=None):
    con = _get_conn(db_or_mem) if db_or_mem is not None else sqlite3.connect("ki_memory.sqlite3")
    cur = con.cursor()
    changes = []

    for table, cols in TABLE_COLUMNS.items():
        _add_missing_columns(cur, table, cols, changes)

    for table, column in UNIQUE_TARGETS:
        if _table_exists(cur, table) and column in _columns(cur, table):
            _dedupe_for_unique(cur, table, column, changes)
            idx = f"idx_{table}_{column}_unique_phase4def_fixed8"
            cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {_quote_ident(idx)} ON {_quote_ident(table)}({_quote_ident(column)})")
            changes.append(f"unique_index:{table}.{column}")

    now = int(time.time())
    state = {
        "phase": "phase4def_schema_canonicalizer_fixed8",
        "no_word_blacklists": "true",
        "learning_mode": "context_hypotheses_with_neuromodulators",
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
    }
    for k, v in state.items():
        cur.execute(
            "INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (k, repr(v), now),
        )
    con.commit()
    return changes

_ORIGINALS = {}

def patch_module(*args, **kwargs):
    """Patch phase4def module so schema canonicalization runs before each cycle/run."""
    import sys
    mod = sys.modules.get("ki_system.v8_phase4def_context_learning_pack")
    if mod is None:
        return False

    if not _ORIGINALS.get("safe_cycle") and hasattr(mod, "safe_cycle"):
        _ORIGINALS["safe_cycle"] = mod.safe_cycle
    if not _ORIGINALS.get("safe_run") and hasattr(mod, "safe_run"):
        _ORIGINALS["safe_run"] = mod.safe_run

    orig_cycle = _ORIGINALS.get("safe_cycle")
    orig_run = _ORIGINALS.get("safe_run")
    if orig_cycle is None or orig_run is None:
        return False

    def safe_cycle_fixed8(self, progress=None):
        ensure_phase4def_schema(getattr(self, "mem", None))
        return orig_cycle(self, progress)

    def safe_run_fixed8(self, cycles=5, progress=None):
        ensure_phase4def_schema(getattr(self, "mem", None))
        return orig_run(self, cycles, progress)

    safe_cycle_fixed8.__module__ = mod.__name__
    safe_run_fixed8.__module__ = mod.__name__
    safe_cycle_fixed8.__name__ = "safe_cycle"
    safe_run_fixed8.__name__ = "safe_run"

    mod.safe_cycle = safe_cycle_fixed8
    mod.safe_run = safe_run_fixed8

    try:
        from ki_system.autonomous import AutonomousLoop
        AutonomousLoop.cycle = safe_cycle_fixed8
        AutonomousLoop.run = safe_run_fixed8
        AutonomousLoop.phase4d_hypothesis_feedback_error_learning = True
        AutonomousLoop.phase4e_neuromodulated_attention_strategy = True
        AutonomousLoop.phase4f_sleep_consolidation_self_improvement = True
        AutonomousLoop.phase4def_context_learning_pack = True
        AutonomousLoop.phase4def_schema_canonicalizer_fixed8 = True
        AutonomousLoop.no_word_blacklists = True
        AutonomousLoop._no_word_blacklists = True
        AutonomousLoop.learning_mode = "context_hypotheses_with_neuromodulators"
        AutonomousLoop._rollback_learning_mode = "context_hypotheses_with_neuromodulators"
        AutonomousLoop.fact_promotion = "disabled"
        AutonomousLoop._fact_promotion = "disabled"
    except Exception as exc:
        print("[PHASE4DEF_FIXED8_AUTONOMOUS_MARKER_ERROR]", exc)

    try:
        ensure_phase4def_schema()
    except Exception as exc:
        print("[PHASE4DEF_FIXED8_SCHEMA_ERROR]", exc)
    return True
