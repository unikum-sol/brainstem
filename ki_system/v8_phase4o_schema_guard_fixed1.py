# V8-phase4o schema guard FIXED1
# Ensures phase4o strategy effectiveness schema is canonical before migration/runtime.
# Project compass: no word blacklists, no facts/relations/questions writes.
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

PHASE = "phase4o_schema_guard_fixed1"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _connect(db_or_memory=None):
    """Return (connection, should_close). Accepts sqlite3.Connection, Memory-like, or path."""
    if isinstance(db_or_memory, sqlite3.Connection):
        return db_or_memory, False
    if db_or_memory is not None:
        for attr in ("con", "conn", "connection", "db"):
            obj = getattr(db_or_memory, attr, None)
            if isinstance(obj, sqlite3.Connection):
                return obj, False
        db_path = getattr(db_or_memory, "db_path", None) or getattr(db_or_memory, "path", None)
        if db_path:
            return sqlite3.connect(str(db_path)), True
    return sqlite3.connect("ki_memory.sqlite3"), True


def _table_exists(cur, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(cur, table: str):
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _ensure_table(cur, table: str, ddl: str, changes: list[str]):
    if not _table_exists(cur, table):
        cur.execute(ddl)
        changes.append(f"create_table:{table}")


def _ensure_col(cur, table: str, col: str, decl: str, changes: list[str]):
    if not _table_exists(cur, table):
        return
    if col not in _columns(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        changes.append(f"add_column:{table}.{col}")


def _ensure_unique(cur, table: str, col: str, changes: list[str]):
    if not _table_exists(cur, table) or col not in _columns(cur, table):
        return
    # Avoid creating unique index if duplicates exist.
    dup = cur.execute(
        f"SELECT {col}, COUNT(*) FROM {table} WHERE {col} IS NOT NULL GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1"
    ).fetchone()
    if dup:
        changes.append(f"skip_unique_duplicates:{table}.{col}")
        return
    idx = f"idx_{table}_{col}_phase4o_fixed1_unique"
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
    changes.append(f"unique_index:{table}.{col}")


def ensure_phase4o_schema(db_or_memory=None):
    con, close = _connect(db_or_memory)
    cur = con.cursor()
    changes: list[str] = []

    # Core phase4o tables.
    _ensure_table(cur, "strategy_feedback_events", """
        CREATE TABLE strategy_feedback_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_key TEXT,
            target_type TEXT,
            target_id INTEGER,
            outcome_score REAL DEFAULT 0,
            progress_score REAL DEFAULT 0,
            error_pressure REAL DEFAULT 0,
            uncertainty_pressure REAL DEFAULT 0,
            stability_gain REAL DEFAULT 0,
            recommendation TEXT,
            details TEXT,
            created_at INTEGER DEFAULT 0
        )
    """, changes)
    _ensure_table(cur, "strategy_outcome_memory", """
        CREATE TABLE strategy_outcome_memory(
            strategy_key TEXT PRIMARY KEY,
            observations INTEGER DEFAULT 0,
            avg_outcome_score REAL DEFAULT 0,
            avg_error_pressure REAL DEFAULT 0,
            avg_uncertainty_pressure REAL DEFAULT 0,
            avg_stability_gain REAL DEFAULT 0,
            last_recommendation TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """, changes)
    _ensure_table(cur, "strategy_adjustment_recommendations", """
        CREATE TABLE strategy_adjustment_recommendations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parameter TEXT,
            old_value REAL DEFAULT 0,
            recommended_value REAL DEFAULT 0,
            reason TEXT,
            source_phase TEXT,
            created_at INTEGER DEFAULT 0
        )
    """, changes)
    _ensure_table(cur, "strategy_effectiveness_feedback_state", """
        CREATE TABLE strategy_effectiveness_feedback_state(
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """, changes)

    # Future-safe columns touched by phase4o and expected downstream.
    for table in ("context_hypotheses",):
        _ensure_col(cur, table, "strategy_effectiveness_score", "REAL DEFAULT 0", changes)
        _ensure_col(cur, table, "last_strategy_feedback_at", "INTEGER DEFAULT 0", changes)
        _ensure_col(cur, table, "strategy_feedback_reason", "TEXT", changes)
        _ensure_col(cur, table, "progress_score", "REAL DEFAULT 0", changes)
        _ensure_col(cur, table, "last_progress_evaluated_at", "INTEGER DEFAULT 0", changes)
        _ensure_col(cur, table, "progress_reason", "TEXT", changes)

    # The missing priority column that caused the crash is protected here.
    if _table_exists(cur, "internal_learning_gaps"):
        for col, decl in [
            ("priority", "REAL DEFAULT 0"),
            ("active_learning_priority", "REAL DEFAULT 0"),
            ("progress_priority", "REAL DEFAULT 0"),
            ("strategy_effectiveness_score", "REAL DEFAULT 0"),
            ("last_strategy_feedback_at", "INTEGER DEFAULT 0"),
            ("strategy_feedback_reason", "TEXT"),
            ("last_progress_evaluated_at", "INTEGER DEFAULT 0"),
            ("progress_reason", "TEXT"),
            ("last_selected_at", "INTEGER DEFAULT 0"),
            ("selection_count", "INTEGER DEFAULT 0"),
            ("status", "TEXT DEFAULT 'open'"),
        ]:
            _ensure_col(cur, "internal_learning_gaps", col, decl, changes)
        # Backfill priority from best available signal without any filtering/blacklist logic.
        cols = _columns(cur, "internal_learning_gaps")
        expr_parts = []
        for c in ("active_learning_priority", "progress_priority", "severity", "error_weight", "avg_uncertainty"):
            if c in cols:
                expr_parts.append(f"COALESCE({c},0)")
        if expr_parts:
            expr = "MAX(" + ",".join(expr_parts + ["0"]) + ")"
            cur.execute(f"UPDATE internal_learning_gaps SET priority={expr} WHERE COALESCE(priority,0)=0")
            changes.append("backfill:internal_learning_gaps.priority")

    if _table_exists(cur, "internal_learning_questions"):
        for col, decl in [
            ("priority", "REAL DEFAULT 0"),
            ("strategy_effectiveness_score", "REAL DEFAULT 0"),
            ("last_strategy_feedback_at", "INTEGER DEFAULT 0"),
            ("strategy_feedback_reason", "TEXT"),
            ("status", "TEXT DEFAULT 'internal_open'"),
        ]:
            _ensure_col(cur, "internal_learning_questions", col, decl, changes)

    if _table_exists(cur, "chunk_attention_scores"):
        for col, decl in [
            ("strategy_effectiveness_score", "REAL DEFAULT 0"),
            ("last_strategy_feedback_at", "INTEGER DEFAULT 0"),
            ("strategy_feedback_reason", "TEXT"),
            ("progress_adjusted_score", "REAL DEFAULT 0"),
            ("progress_adjustment_reason", "TEXT"),
            ("active_learning_score", "REAL DEFAULT 0"),
            ("strategy_reason", "TEXT"),
        ]:
            _ensure_col(cur, "chunk_attention_scores", col, decl, changes)

    # Unique indexes used by upsert patterns.
    for t, c in [
        ("strategy_outcome_memory", "strategy_key"),
        ("strategy_effectiveness_feedback_state", "key"),
        ("reading_queue", "chunk_id"),
        ("chunk_attention_scores", "chunk_id"),
        ("active_learning_loop_state", "key"),
        ("progress_evaluation_state", "key"),
    ]:
        _ensure_unique(cur, t, c, changes)

    # Safety/state marker.
    now = int(time.time())
    if _table_exists(cur, "strategy_effectiveness_feedback_state"):
        state = {
            "phase": PHASE,
            "learning_mode": LEARNING_MODE,
            "no_word_blacklists": "true",
            "fact_promotion": "disabled",
            "direct_fact_writes": "disabled",
            "direct_relation_writes": "disabled",
            "question_generation": "internal_learning_questions_only",
        }
        for k, v in state.items():
            cur.execute(
                "INSERT INTO strategy_effectiveness_feedback_state(key,value,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (k, v, now),
            )

    con.commit()
    if close:
        con.close()
    return {"status": "ok", "phase": PHASE, "changes": changes}


def evaluate_strategy_effectiveness_safe():
    """Run the existing phase4o evaluator after canonical schema is guaranteed."""
    ensure_phase4o_schema("ki_memory.sqlite3")
    try:
        from ki_system import v8_phase4o_strategy_effectiveness_feedback_loop as phase4o
        return phase4o.evaluate_strategy_effectiveness()
    except Exception as exc:
        # Do not hide facts/relations errors; return a diagnostic for tools.
        return {"status": "phase4o_evaluator_error", "phase": PHASE, "error": repr(exc), "no_word_blacklists": True, "fact_promotion": "disabled"}


def _get_memory(loop):
    for attr in ("mem", "memory", "m", "store", "memory_store"):
        obj = getattr(loop, attr, None)
        if obj is not None:
            return obj
    return None


def managed_cycle(self, progress=None):
    mem = _get_memory(self)
    ensure_phase4o_schema(mem)
    from ki_system import v8_phase4o_strategy_effectiveness_feedback_loop as phase4o
    result = phase4o.managed_cycle(self, progress) if hasattr(phase4o, "managed_cycle") else phase4o.safe_cycle(self, progress)
    ensure_phase4o_schema(mem)
    try:
        phase4o.evaluate_strategy_effectiveness()
    except Exception:
        # Schema guard should prevent known errors; do not crash learning loop for status-only feedback.
        pass
    return result


def managed_run(self, cycles=1, progress=None):
    mem = _get_memory(self)
    ensure_phase4o_schema(mem)
    from ki_system import v8_phase4o_strategy_effectiveness_feedback_loop as phase4o
    result = phase4o.managed_run(self, cycles, progress) if hasattr(phase4o, "managed_run") else phase4o.safe_run(self, cycles, progress)
    ensure_phase4o_schema(mem)
    try:
        phase4o.evaluate_strategy_effectiveness()
    except Exception:
        pass
    return result


def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as _AL
        AutonomousLoop = _AL
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    setattr(AutonomousLoop, "phase4o_schema_guard_fixed1", True)
    setattr(AutonomousLoop, "phase4o_strategy_effectiveness_feedback_loop", True)
    setattr(AutonomousLoop, "no_word_blacklists", True)
    setattr(AutonomousLoop, "_no_word_blacklists", True)
    setattr(AutonomousLoop, "learning_mode", LEARNING_MODE)
    setattr(AutonomousLoop, "_fact_promotion", "disabled")
    return AutonomousLoop
