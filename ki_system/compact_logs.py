"""One-time compaction of the experiment and event logs.

Deletes log rows older than the last `--keep-seconds` of activity (default:
the time span of the last RETENTION_CYCLES cycles, measured from the
production run timing of about 11 s per cycle), keeps the lifetime totals of
the outcome summaries, and optionally runs VACUUM.

Usage (always on a copy first):
    python -m ki_system.compact_logs <db> [--cutoff-ts EPOCH] [--vacuum]
Without --cutoff-ts the cutoff is the newest created_at of the outcome log
minus RETENTION_CYCLES * 11 seconds.
"""
import argparse
import sqlite3
import time

from ki_system.v8_log_retention import LOG_TABLES, OUTCOMES, OUTCOME_DELETE_TRIGGER, RETENTION_CYCLES, ensure_schema


def _cols(con, t):
    return {r[1] for r in con.execute("PRAGMA table_info(" + t + ")")}


def compact(db_path: str, cutoff_ts: int = None, vacuum: bool = False) -> dict:
    con = sqlite3.connect(db_path, timeout=60)
    t0 = time.time()
    if cutoff_ts is None:
        newest = con.execute("SELECT MAX(created_at) FROM " + OUTCOMES).fetchone()[0] or 0
        cutoff_ts = int(newest) - RETENTION_CYCLES * 11
    report = {"cutoff_ts": cutoff_ts, "deleted": {}}
    trig = con.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (OUTCOME_DELETE_TRIGGER,)).fetchone()
    con.execute("BEGIN")
    if trig:
        con.execute("DROP TRIGGER " + OUTCOME_DELETE_TRIGGER)
    for t in LOG_TABLES:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone():
            continue
        if "created_at" not in _cols(con, t):
            report["deleted"][t] = "no created_at, skipped"
            continue
        upto = con.execute("SELECT MAX(rowid) FROM " + t + " WHERE created_at < ?", (cutoff_ts,)).fetchone()[0]
        n = con.execute("DELETE FROM " + t + " WHERE rowid <= ?", (upto,)).rowcount if upto is not None else 0
        report["deleted"][t] = n
    if trig:
        con.execute(trig[0])
    ensure_schema(con)
    con.commit()
    report["delete_seconds"] = round(time.time() - t0, 1)
    if vacuum:
        t1 = time.time()
        con.execute("VACUUM")
        report["vacuum_seconds"] = round(time.time() - t1, 1)
    report["quick_check"] = con.execute("PRAGMA quick_check").fetchone()[0]
    con.close()
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--cutoff-ts", type=int, default=None)
    ap.add_argument("--vacuum", action="store_true")
    a = ap.parse_args()
    print(compact(a.db, a.cutoff_ts, a.vacuum))
