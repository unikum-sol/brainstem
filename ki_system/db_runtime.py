"""Connection identity and WAL-consistent snapshots. No learning-data deletion."""
import sqlite3
from pathlib import Path


def resolve_connection(obj=None):
    """Resolve explicit objects recursively; never fall back for an invalid object."""
    if obj is None:
        path = Path(__file__).resolve().parents[1] / "ki_memory.sqlite3"
        con = sqlite3.connect(str(path), timeout=60)
        con.row_factory = sqlite3.Row
        return con
    seen = set()
    def visit(value):
        if isinstance(value, sqlite3.Connection):
            value.row_factory = sqlite3.Row
            return value
        if value is None or id(value) in seen:
            return None
        seen.add(id(value))
        for attr in ("db", "conn", "con", "connection", "memory", "mem", "store", "memory_store"):
            found = visit(getattr(value, attr, None))
            if found is not None:
                return found
        return None
    con = visit(obj)
    if con is None:
        raise TypeError("Explicit database object has no SQLite connection; refusing default fallback")
    return con


def sqlite_snapshot(source, destination):
    """Copy committed SQLite state, including WAL, without writing to the source."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Snapshot source and destination must differ")
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=60)
    try:
        dst = sqlite3.connect(str(destination), timeout=60)
        try:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Snapshot integrity check failed")
        finally:
            dst.close()
    finally:
        src.close()
    return destination
