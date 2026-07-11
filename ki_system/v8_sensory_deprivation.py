# -*- coding: utf-8 -*-
"Sensory Deprivation flag for BrainStem: toggles whether the wake/read step is skipped (input off)."
import os, sqlite3, time
from pathlib import Path

PHASE = "sensory_deprivation_release"
SCHEMA_TABLES = {"deprivation_state": [("key", "TEXT PRIMARY KEY"), ("value", "TEXT"), ("updated_at", "INTEGER")]}

def _now():
    return int(time.time())

def _table_exists(con, t):
    try:
        return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
    except Exception:
        return False

def resolve_db(obj=None):
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            cand = Path(__file__).resolve().parent.parent / "ki_memory.sqlite3"
            if cand.exists():
                path = str(cand)
        return sqlite3.connect(path, timeout=30.0)
    if isinstance(obj, sqlite3.Connection):
        return obj
    for a in ("db", "con", "conn", "connection", "memory"):
        inner = getattr(obj, a, None)
        if isinstance(inner, sqlite3.Connection):
            return inner
        inner2 = getattr(inner, "db", None) or getattr(inner, "con", None) or getattr(inner, "conn", None)
        if isinstance(inner2, sqlite3.Connection):
            return inner2
    return resolve_db(None)

def ensure_schema(con):
    for t, cols in SCHEMA_TABLES.items():
        if not _table_exists(con, t):
            con.execute("CREATE TABLE " + t + " (" + ", ".join(n + " " + s for n, s in cols) + ")")
    con.commit()

def _read_kv(con):
    if not _table_exists(con, "deprivation_state"):
        return {}
    try:
        return dict(con.execute("SELECT key,value FROM deprivation_state").fetchall())
    except Exception:
        return {}

def _kv_set(con, key, value):
    con.execute("INSERT INTO deprivation_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                (key, value, _now()))

def set_deprivation(con_or_mem, active):
    try:
        con = resolve_db(con_or_mem)
        ensure_schema(con)
        _kv_set(con, "active", "true" if active else "false")
        con.commit()
        return bool(active)
    except Exception:
        return False

def is_deprivation_active(con_or_mem=None):
    try:
        con = resolve_db(con_or_mem)
        ensure_schema(con)
        v = _read_kv(con).get("active", "false")
        return str(v).strip().lower() == "true"
    except Exception:
        return False