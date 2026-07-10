
"""V8 phase4 schema manager canonicalization.

Central schema canonicalizer for Phase4 context learning. This module does not
introduce word blacklists, does not write facts/relations/questions, and does
not promote hypotheses to facts. It only ensures Phase4 learning tables have the
canonical columns and UNIQUE indexes required by the current runtime.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Iterable, Optional

PHASE = "phase4_schema_manager_canonicalization"

# Canonical table/column definitions. Existing tables are migrated with ALTER TABLE.
TABLE_COLUMNS = {
    "reading_queue": [
        ("chunk_id", "INTEGER"),
        ("priority", "REAL DEFAULT 0"),
        ("reason", "TEXT"),
        ("attention_score", "REAL DEFAULT 0"),
        ("read_count", "INTEGER DEFAULT 0"),
        ("status", "TEXT DEFAULT 'pending'"),
        ("last_read", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
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
        ("uncertainty", "REAL DEFAULT 0"),
        ("status", "TEXT DEFAULT 'hypothesis'"),
        ("dopamine", "REAL DEFAULT 0"),
        ("serotonin", "REAL DEFAULT 0"),
        ("glutamate", "REAL DEFAULT 0"),
        ("gaba", "REAL DEFAULT 0"),
        ("noradrenaline", "REAL DEFAULT 0"),
        ("acetylcholine", "REAL DEFAULT 0"),
        ("created_at", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
        ("signature", "TEXT"),
        ("evidence_count", "INTEGER DEFAULT 1"),
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
        ("old_confidence", "REAL DEFAULT 0"),
        ("new_confidence", "REAL DEFAULT 0"),
        ("reason", "TEXT"),
        ("details", "TEXT"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_error_events": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("hypothesis_id", "INTEGER"),
        ("role", "TEXT"),
        ("error_type", "TEXT"),
        ("error_signal", "REAL DEFAULT 0"),
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
        ("details", "TEXT"),
        ("created_at", "INTEGER DEFAULT 0"),
    ],
    "context_role_stats": [
        ("role", "TEXT"),
        ("seen", "INTEGER DEFAULT 0"),
        ("seen_count", "INTEGER DEFAULT 0"),
        ("avg_confidence", "REAL DEFAULT 0"),
        ("avg_uncertainty", "REAL DEFAULT 0"),
        ("feedback_count", "INTEGER DEFAULT 0"),
        ("error_count", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "chunk_attention_scores": [
        ("chunk_id", "INTEGER"),
        ("attention_score", "REAL DEFAULT 0"),
        ("novelty_score", "REAL DEFAULT 0"),
        ("uncertainty_score", "REAL DEFAULT 0"),
        ("reward_score", "REAL DEFAULT 0"),
        ("fatigue_score", "REAL DEFAULT 0"),
        ("last_reason", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "attention_queue_state": [
        ("key", "TEXT"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "reading_strategy_state": [
        ("key", "TEXT"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_clusters": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("cluster_key", "TEXT"),
        ("role", "TEXT"),
        ("size", "INTEGER DEFAULT 0"),
        ("avg_confidence", "REAL DEFAULT 0"),
        ("avg_uncertainty", "REAL DEFAULT 0"),
        ("stability", "REAL DEFAULT 0"),
        ("example", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "hypothesis_stability_scores": [
        ("hypothesis_id", "INTEGER"),
        ("role", "TEXT"),
        ("stability", "REAL DEFAULT 0"),
        ("confidence", "REAL DEFAULT 0"),
        ("uncertainty", "REAL DEFAULT 0"),
        ("evidence_count", "INTEGER DEFAULT 0"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "context_pattern_memory": [
        ("pattern_key", "TEXT"),
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
        ("key", "TEXT"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
    "rollback_safe_core_state": [
        ("key", "TEXT"),
        ("value", "TEXT"),
        ("updated_at", "INTEGER DEFAULT 0"),
    ],
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


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _conn(mem_or_con: Any) -> sqlite3.Connection:
    if isinstance(mem_or_con, sqlite3.Connection):
        return mem_or_con
    if hasattr(mem_or_con, "db") and isinstance(mem_or_con.db, sqlite3.Connection):
        return mem_or_con.db
    if hasattr(mem_or_con, "conn") and isinstance(mem_or_con.conn, sqlite3.Connection):
        return mem_or_con.conn
    raise TypeError("Cannot find sqlite3.Connection on object")


def _q_ident(name: str) -> str:
    # Internal constant names only; still avoid accidental quote breakage.
    return '"' + name.replace('"', '""') + '"'


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    if not _table_exists(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({_q_ident(table)})").fetchall()}


def _create_table_if_missing(cur: sqlite3.Cursor, table: str, cols: list[tuple[str, str]]) -> None:
    if _table_exists(cur, table):
        return
    col_sql = ", ".join(f"{_q_ident(c)} {decl}" for c, decl in cols)
    cur.execute(f"CREATE TABLE IF NOT EXISTS {_q_ident(table)} ({col_sql})")


def _add_missing_columns(cur: sqlite3.Cursor, table: str, cols: list[tuple[str, str]], changes: list[str]) -> None:
    existing = _columns(cur, table)
    for col, decl in cols:
        if col in existing:
            continue
        # SQLite cannot add PRIMARY KEY columns via ALTER TABLE; in that case fall back to INTEGER/TEXT.
        add_decl = decl.replace("PRIMARY KEY AUTOINCREMENT", "").replace("PRIMARY KEY", "").strip()
        if not add_decl:
            add_decl = "TEXT"
        cur.execute(f"ALTER TABLE {_q_ident(table)} ADD COLUMN {_q_ident(col)} {add_decl}")
        changes.append(f"add_column:{table}.{col}")


def _dedupe_for_unique(cur: sqlite3.Cursor, table: str, column: str, changes: list[str]) -> None:
    if not _table_exists(cur, table) or column not in _columns(cur, table):
        return
    rowid_col = "rowid"
    duplicates = cur.execute(
        f"SELECT {_q_ident(column)}, COUNT(*) FROM {_q_ident(table)} "
        f"WHERE {_q_ident(column)} IS NOT NULL GROUP BY {_q_ident(column)} HAVING COUNT(*) > 1 LIMIT 20"
    ).fetchall()
    if not duplicates:
        return
    # Keep the latest rowid for derived/state tables. No facts/relations/questions are touched.
    cur.execute(
        f"DELETE FROM {_q_ident(table)} WHERE {rowid_col} NOT IN "
        f"(SELECT MAX({rowid_col}) FROM {_q_ident(table)} WHERE {_q_ident(column)} IS NOT NULL GROUP BY {_q_ident(column)} "
        f"UNION SELECT {rowid_col} FROM {_q_ident(table)} WHERE {_q_ident(column)} IS NULL)"
    )
    changes.append(f"dedupe:{table}.{column}:{len(duplicates)}keys")


def _ensure_unique_index(cur: sqlite3.Cursor, table: str, column: str, changes: list[str]) -> None:
    if not _table_exists(cur, table) or column not in _columns(cur, table):
        return
    _dedupe_for_unique(cur, table, column, changes)
    idx = f"idx_{table}_{column}_phase4_unique"
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {_q_ident(idx)} ON {_q_ident(table)}({_q_ident(column)})")
    changes.append(f"unique_index:{table}.{column}")


def _seed_state(cur: sqlite3.Cursor, changes: list[str]) -> None:
    now = int(time.time())
    state = {
        "phase": "phase4_schema_manager_canonicalization",
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
    cur.execute(
        "INSERT INTO learning_strategy_state(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        ("schema_manager", _json({"phase": PHASE, "no_word_blacklists": True}), now),
    )
    changes.append("state_seeded")


def ensure_phase4_schema(mem_or_con: Any) -> dict[str, Any]:
    con = _conn(mem_or_con)
    cur = con.cursor()
    changes: list[str] = []

    for table, cols in TABLE_COLUMNS.items():
        _create_table_if_missing(cur, table, cols)
        _add_missing_columns(cur, table, cols, changes)

    # Backfill seen_count from older 'seen' column where applicable.
    if _table_exists(cur, "context_role_stats"):
        cols = _columns(cur, "context_role_stats")
        if "seen" in cols and "seen_count" in cols:
            cur.execute("UPDATE context_role_stats SET seen_count=COALESCE(NULLIF(seen_count,0), seen) WHERE seen IS NOT NULL")
            changes.append("backfill:context_role_stats.seen_count")

    for table, column in UNIQUE_TARGETS:
        _ensure_unique_index(cur, table, column, changes)

    _seed_state(cur, changes)
    con.commit()
    return {"status": "ok", "phase": PHASE, "changes": changes}


def patch_autonomous_loop(loop_cls: Optional[type] = None) -> None:
    if loop_cls is None:
        from ki_system.autonomous import AutonomousLoop as loop_cls  # type: ignore
    try:
        import ki_system.v8_phase4def_context_learning_pack as p4def
    except Exception:
        p4def = None

    base_run = getattr(p4def, "safe_run", None) if p4def is not None else None
    base_cycle = getattr(p4def, "safe_cycle", None) if p4def is not None else None
    if base_run is None:
        base_run = getattr(loop_cls, "run")
    if base_cycle is None:
        base_cycle = getattr(loop_cls, "cycle")

    def managed_cycle(self, progress=None):
        ensure_phase4_schema(self.mem)
        return base_cycle(self, progress)

    def managed_run(self, cycles=1, progress=None):
        ensure_phase4_schema(self.mem)
        return base_run(self, cycles, progress)

    loop_cls.cycle = managed_cycle
    loop_cls.run = managed_run

    # Diagnostic markers — both underscored and non-underscored for tool compatibility.
    for name in [
        "phase4_schema_manager_canonicalization",
        "phase4d_hypothesis_feedback_error_learning",
        "phase4e_neuromodulated_attention_strategy",
        "phase4f_sleep_consolidation_self_improvement",
        "phase4def_context_learning_pack",
        "no_word_blacklists",
    ]:
        setattr(loop_cls, name, True)
        setattr(loop_cls, "_" + name, True)
    setattr(loop_cls, "learning_mode", "context_hypotheses_with_neuromodulators")
    setattr(loop_cls, "_learning_mode", "context_hypotheses_with_neuromodulators")
    setattr(loop_cls, "rollback_learning_mode", "context_hypotheses_with_neuromodulators")
    setattr(loop_cls, "_rollback_learning_mode", "context_hypotheses_with_neuromodulators")
    setattr(loop_cls, "fact_promotion", "disabled")
    setattr(loop_cls, "_fact_promotion", "disabled")

# Allow explicit import side-effect when imported after AutonomousLoop exists.
try:
    from ki_system.autonomous import AutonomousLoop as _AutonomousLoop
    patch_autonomous_loop(_AutonomousLoop)
except Exception:
    pass
