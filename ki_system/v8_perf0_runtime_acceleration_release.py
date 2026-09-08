# -*- coding: utf-8 -*-
"""
V8 Perf0 - Runtime Acceleration

Pure performance booster. Does NOT hook into the managed_cycle chain.
    - Sets fast SQLite PRAGMAs (per connection).
    - Creates missing indexes on the big hot tables.
    - Runs ANALYZE so the query planner uses them.

No learning logic, no botenstoff logic, no schema for phases.
Only speed. Safe and reversible (indexes can be dropped, pragmas are per-connection).
"""
from __future__ import annotations
import json, os, sqlite3, time
from pathlib import Path
from typing import Any

PHASE = "perf0_runtime_acceleration"

FAST_PRAGMAS = [
    ("journal_mode", "WAL"),
    ("synchronous", "NORMAL"),
    ("cache_size", "-262144"),      # 256 MB page cache
    ("temp_store", "MEMORY"),
    ("mmap_size", "1073741824"),    # 1 GB memory-mapped I/O
]

# (index_name, table, [(col, order), ...])
PERF_INDEXES = [
    ("idx_ch_replay_weight",       "context_hypotheses",          [("phase6a_replay_weight", "DESC")]),
    ("idx_ch_replay_count",        "context_hypotheses",          [("phase6a_sleep_replay_count", "DESC")]),
    ("idx_ch_last_replayed",       "context_hypotheses",          [("phase6a_last_replayed_at", "")]),
    ("idx_5g_outcome",             "phase5g_experiment_outcomes", [("outcome_score", "")]),
    ("idx_anchor_active_stab",     "phase6b_anchor_pool",         [("active", ""), ("stability_score", "DESC")]),
    ("idx_anchor_key",             "phase6b_anchor_pool",         [("anchor_key", "")]),
    ("idx_questions_status",       "questions",                   [("status", "")]),
    ("idx_reading_queue_priority", "reading_queue",               [("priority", "DESC")]),
    ("idx_chunk_attention_score",  "chunk_attention_scores",      [("attention_score", "DESC")]),
]


def resolve_db(obj: Any = None):
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


def _table_exists(con, table):
    return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _columns(con, table):
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]

def _index_exists(con, name):
    return con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone() is not None


def apply_fast_pragmas(con):
    report = {}
    for name, value in FAST_PRAGMAS:
        try:
            con.execute("PRAGMA " + name + "=" + value)
        except Exception as exc:
            report[name] = "error: " + str(exc)
            continue
        try:
            got = con.execute("PRAGMA " + name).fetchone()
            report[name] = got[0] if got else None
        except Exception:
            report[name] = "set"
    return report


def create_perf_indexes(con):
    created, skipped = [], []
    for idx_name, table, cols in PERF_INDEXES:
        if not _table_exists(con, table):
            skipped.append(idx_name + " (no table " + table + ")")
            continue
        existing = set(_columns(con, table))
        missing_cols = [c for c, _o in cols if c not in existing]
        if missing_cols:
            skipped.append(idx_name + " (missing cols: " + ",".join(missing_cols) + ")")
            continue
        if _index_exists(con, idx_name):
            skipped.append(idx_name + " (already exists)")
            continue
        col_expr = ", ".join((c + (" " + o if o else "")) for c, o in cols)
        try:
            con.execute("CREATE INDEX IF NOT EXISTS " + idx_name + " ON " + table + "(" + col_expr + ")")
            created.append(idx_name)
        except Exception as exc:
            skipped.append(idx_name + " (error: " + str(exc) + ")")
    con.commit()
    return {"created": created, "skipped": skipped}


def ensure_schema(con):
    con.execute("CREATE TABLE IF NOT EXISTS perf0_state (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)")
    con.commit()


def _set_state(con, key, value):
    con.execute(
        "INSERT INTO perf0_state(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, str(value), int(time.time())),
    )


def apply_all(con):
    ensure_schema(con)
    pragmas = apply_fast_pragmas(con)
    indexes = create_perf_indexes(con)
    try:
        con.execute("ANALYZE")
    except Exception:
        pass
    _set_state(con, "last_applied_at", int(time.time()))
    _set_state(con, "pragmas_json", json.dumps(pragmas))
    _set_state(con, "indexes_created_json", json.dumps(indexes["created"]))
    con.commit()
    return {"phase": PHASE, "pragmas": pragmas, "indexes": indexes}


def autoload(AutonomousLoop):
    # Pure accelerator: does NOT override cycle/run.
    AutonomousLoop.perf0_runtime_acceleration = True
    try:
        db = resolve_db(AutonomousLoop.memory if hasattr(AutonomousLoop, "memory") else None)
    except Exception:
        db = None
    if db is not None:
        try:
            apply_fast_pragmas(db)
        except Exception:
            pass
    return AutonomousLoop
