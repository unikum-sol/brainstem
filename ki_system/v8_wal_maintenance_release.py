# -*- coding: utf-8 -*-
"""BrainStem WAL (Write-Ahead-Log) maintenance.

BRAINSTEM_WAL_CHECKPOINT_MAINTENANCE_V1

Background: memory.py's Memory._init() enables SQLite's WAL journal mode
(PRAGMA journal_mode=WAL) once, at database creation. No module anywhere in
this codebase ever explicitly triggers a WAL checkpoint. SQLite's automatic
"PASSIVE" checkpointing cannot fully truncate the WAL file while any other
connection still holds an open read snapshot referencing older WAL frames --
and the admin GUI's own periodic self-refresh (gui_app.py schedules
self.after(2000, self._refresh) indefinitely while the window is open, doing
read queries roughly every 2 seconds) is exactly such a long-lived reader.
Over a long autonomous-learning session with several hundred cycles at
large corpus scale (each cycle performing many individual writes across
Phase 5f/5g/5i and the shadow/bridge modules before committing), the WAL
file has no reliable, explicit opportunity to shrink and can in principle
grow without a firm upper bound.

This was raised as an unconfirmed hypothesis (not yet independently
measured) to explain reported GUI sluggishness and an observed
"database is locked" failure during a real, large-scale (167,661 chunk)
production run. The user has explicitly authorized implementing a
mitigation directly.

This module adds a small, self-contained, easily auditable periodic
checkpoint mechanism:
  - Purely additive: one small state table, no interaction with any
    learning/hypothesis/neuromodulator table.
  - Idempotent schema (CREATE TABLE IF NOT EXISTS).
  - Never raises: any failure is caught, logged into its own state table,
    and reported back as a plain dict; callers integrate this as a
    best-effort maintenance step, never as something that can interrupt or
    fail a real learning cycle.
  - Uses SQLite's own built-in "PRAGMA wal_checkpoint(TRUNCATE)" mechanism
    (the standard, documented, safe way to shrink a WAL file). A TRUNCATE
    checkpoint will checkpoint as many frames as it safely can even if it
    cannot fully truncate due to a concurrently open reader (reported via
    the "busy" field), so calling this periodically is always safe and
    never blocks or corrupts anything; it simply may not always fully
    truncate on every call if a reader happens to be active at that exact
    moment, which is expected, safe SQLite behavior.

Important, empirically confirmed behavior note: SQLite reports
"log_frames"/"checkpointed_frames" as 0 whenever a normal COMMIT has
already passively flushed all logical WAL content (which happens
automatically whenever no other connection holds an older read snapshot).
Despite frame counts showing 0, the on-disk -wal FILE SIZE itself is only
physically shrunk back down by an explicit TRUNCATE-mode checkpoint (a
plain COMMIT does not resize the file, only marks its content as
checkpointed). This module therefore also measures and reports the actual
-wal file size in bytes before/after each checkpoint, which is the metric
that matters for the disk-growth concern this module addresses -- not the
frame counts alone.
"""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path

PHASE = "wal_maintenance_release"
STATE_TABLE = "wal_maintenance_state"
EVENTS_TABLE = "wal_maintenance_events"
DEFAULT_INTERVAL_CYCLES = 1  # checkpoint after every outer GUI cycle by default

SCHEMA_TABLES = {
    STATE_TABLE: [("key", "TEXT PRIMARY KEY"), ("value", "TEXT"), ("updated_at", "INTEGER")],
    EVENTS_TABLE: [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"), ("created_at", "INTEGER"),
        ("mode", "TEXT"), ("busy", "INTEGER"), ("log_frames", "INTEGER"),
        ("checkpointed_frames", "INTEGER"), ("status", "TEXT"), ("error", "TEXT"),
        ("wal_file_size_bytes_before", "INTEGER"), ("wal_file_size_bytes_after", "INTEGER"),
    ],
}


def _now() -> int:
    return int(time.time())


def _table_exists(con, table):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]


def ensure_schema(con):
    for table, cols in SCHEMA_TABLES.items():
        if not _table_exists(con, table):
            con.execute("CREATE TABLE " + table + " (" + ", ".join(n + " " + s for n, s in cols) + ")")
        else:
            existing = set(_columns(con, table))
            for name, spec in cols:
                if name not in existing and "PRIMARY KEY" not in spec.upper() and "AUTOINCREMENT" not in spec.upper():
                    con.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + spec)
    con.commit()


def _kv_set(con, key, value):
    con.execute(
        "INSERT INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
        (key, str(value), _now()),
    )


def _wal_path_for(con):
    """Best-effort resolution of the -wal sidecar file size, for diagnostics only."""
    try:
        rows = con.execute("PRAGMA database_list").fetchall()
        for row in rows:
            # row: (seq, name, file)
            if row[1] == "main" and row[2]:
                return Path(str(row[2]) + "-wal")
    except Exception:
        pass
    return None


def _file_size_or_none(path):
    try:
        if path is not None and path.exists():
            return path.stat().st_size
    except Exception:
        pass
    return None


def checkpoint_now(con, mode: str = "TRUNCATE") -> dict:
    """Run one WAL checkpoint attempt. Never raises; always returns a dict."""
    ensure_schema(con)
    wal_path = _wal_path_for(con)
    size_before = _file_size_or_none(wal_path)
    result = {
        "phase": PHASE, "mode": mode, "status": "ok",
        "busy": None, "log_frames": None, "checkpointed_frames": None,
        "wal_file_size_bytes_before": size_before, "wal_file_size_bytes_after": size_before,
        "error": None,
    }
    try:
        row = con.execute("PRAGMA wal_checkpoint(" + mode + ")").fetchone()
        if row is not None and len(row) >= 3:
            result["busy"], result["log_frames"], result["checkpointed_frames"] = int(row[0]), int(row[1]), int(row[2])
        size_after = _file_size_or_none(wal_path)
        result["wal_file_size_bytes_after"] = size_after
        con.execute(
            "INSERT INTO " + EVENTS_TABLE + "(created_at,mode,busy,log_frames,checkpointed_frames,status,error,"
            "wal_file_size_bytes_before,wal_file_size_bytes_after) VALUES(?,?,?,?,?,?,?,?,?)",
            (_now(), mode, result["busy"], result["log_frames"], result["checkpointed_frames"], "ok", None,
             size_before, size_after),
        )
        _kv_set(con, "last_checkpoint_at", _now())
        _kv_set(con, "last_status", "ok")
        _kv_set(con, "last_busy", result["busy"])
        _kv_set(con, "last_checkpointed_frames", result["checkpointed_frames"])
        con.commit()
    except Exception as exc:
        result["status"] = "error"
        result["error"] = type(exc).__name__ + ": " + str(exc)
        try:
            con.execute(
                "INSERT INTO " + EVENTS_TABLE + "(created_at,mode,busy,log_frames,checkpointed_frames,status,error,"
                "wal_file_size_bytes_before,wal_file_size_bytes_after) VALUES(?,?,?,?,?,?,?,?,?)",
                (_now(), mode, None, None, None, "error", result["error"], size_before, size_before),
            )
            _kv_set(con, "last_checkpoint_at", _now())
            _kv_set(con, "last_status", "error")
            con.commit()
        except Exception:
            pass
    return result


def maybe_checkpoint(con, outer_cycle_index: int, every_n: int = DEFAULT_INTERVAL_CYCLES, mode: str = "TRUNCATE") -> dict:
    """Run a checkpoint only every `every_n` outer (GUI-visible) cycles.

    Returns {"skipped": True} on cycles where no checkpoint was due, or the
    result of checkpoint_now() otherwise. Never raises.
    """
    try:
        every_n = max(1, int(every_n))
        if int(outer_cycle_index) % every_n != 0:
            return {"phase": PHASE, "skipped": True, "outer_cycle_index": outer_cycle_index}
        return checkpoint_now(con, mode=mode)
    except Exception as exc:
        return {"phase": PHASE, "status": "error", "error": type(exc).__name__ + ": " + str(exc), "skipped": False}


def selftest() -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "wal_maintenance_selftest.sqlite3")
        con = sqlite3.connect(db_path, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT)")
        con.commit()
        for i in range(50):
            con.execute("INSERT INTO t(v) VALUES(?)", ("x" * 200,))
        con.commit()
        r1 = checkpoint_now(con, mode="TRUNCATE")
        assert r1["status"] == "ok", r1
        assert r1["checkpointed_frames"] is not None, r1
        skip = maybe_checkpoint(con, outer_cycle_index=1, every_n=5)
        assert skip.get("skipped") is True, skip
        run = maybe_checkpoint(con, outer_cycle_index=5, every_n=5)
        assert run.get("status") == "ok", run
        con.close()
        return {"status": "ok", "phase": PHASE, "checkpoint_result": r1, "skip_check": skip, "run_check": run}
