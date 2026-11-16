"""Retention of experiment and event logs.

The experiment phases (5b to 5i, 6a, 6c, 7d) append event rows every cycle.
After a few cycles these rows are read only through summaries
(`v8_outcome_aggregates`, the strategy memories of 5g, 5h and 5i) or not at
all. Kept forever they made the database grow by about 3 GB per 1,000 cycles
and made every commit slow (production run of 13 November 2026).

This maintenance step runs after the whole phase chain:
- every MARK_EVERY cycles it records the highest row id of each log table;
- during sleep, at most every PRUNE_EVERY cycles, it deletes the rows that
  are older than RETENTION_CYCLES cycles, up to ROW_BUDGET rows per table and
  run, so that no single cycle is blocked for long.

Long-term knowledge is not affected: the summaries of the experiment outcomes
keep their lifetime totals because the delete trigger of
`phase5g_outcome_aggregates` is suspended while old outcome rows are removed.
Every reader of the pruned tables only looks at recent rows (at most the
latest 1,200 experiments, the latest 500 outcomes, the tag window of 7d of at
most 375 cycles) or looks rows up by key; RETENTION_CYCLES is well above all
these windows.
"""
from typing import Any, Dict

PHASE = "log_retention_maintenance"
STATE_TABLE = "log_retention_state"
MARKS_TABLE = "log_retention_marks"
RETENTION_CYCLES = 1000
MARK_EVERY = 10
PRUNE_EVERY = 50
ROW_BUDGET = 200000

# Append-only log tables. The outcomes of 5g need the aggregate trigger
# handling below; all others are plain event logs.
LOG_TABLES = (
    "phase5h_experiment_learning_events",
    "phase5g_experiment_outcomes",
    "phase5g_strategy_experiments",
    "phase5i_outcome_driven_experiments",
    "context_expansion_actions",
    "phase5f_context_window_experiments",
    "phase5f_adaptive_window_events",
    "gap_closure_attempts",
    "phase6a_sleep_replay_events",
    "context_learning_events",
    "phase5b_reread_diversity_events",
    "phase6c_regulation_events",
    "phase7d_up_state_events",
)
OUTCOMES = "phase5g_experiment_outcomes"
OUTCOME_DELETE_TRIGGER = "trg_phase5g_outcome_aggregates_del"


def _table_exists(con, name) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def ensure_schema(con) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS " + MARKS_TABLE + " (cycle INTEGER NOT NULL, table_name TEXT NOT NULL, "
                "max_rowid INTEGER NOT NULL, PRIMARY KEY(cycle, table_name))")


def _state(con) -> Dict[str, str]:
    return dict(con.execute("SELECT key, value FROM " + STATE_TABLE).fetchall())


def _set(con, key, value) -> None:
    con.execute("INSERT INTO " + STATE_TABLE + "(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)))


def _int(v, d=0) -> int:
    try:
        return int(float(v))
    except Exception:
        return d


def _sleeping(con) -> bool:
    if not _table_exists(con, "cooperative_sleep_wake_state"):
        return False
    row = con.execute("SELECT value FROM cooperative_sleep_wake_state WHERE key='state'").fetchone()
    return bool(row) and str(row[0]) == "sleep"


def record_marks(con, cycle: int) -> int:
    n = 0
    for table in LOG_TABLES:
        if not _table_exists(con, table):
            continue
        mx = con.execute("SELECT MAX(rowid) FROM " + table).fetchone()[0]
        if mx is None:
            continue
        con.execute("INSERT OR REPLACE INTO " + MARKS_TABLE + "(cycle, table_name, max_rowid) VALUES(?, ?, ?)",
                    (cycle, table, int(mx)))
        n += 1
    return n


def _delete_upto(con, table: str, upto: int, budget: int) -> int:
    lo = con.execute("SELECT MIN(rowid) FROM " + table).fetchone()[0]
    if lo is None or lo > upto:
        return 0
    hi = min(upto, int(lo) + budget - 1)
    if table != OUTCOMES:
        return con.execute("DELETE FROM " + table + " WHERE rowid <= ?", (hi,)).rowcount or 0
    # Old outcomes leave the raw log but stay counted in the lifetime
    # summaries: suspend the aggregate delete trigger for this delete only.
    row = con.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (OUTCOME_DELETE_TRIGGER,)).fetchone()
    con.execute("SAVEPOINT log_retention_outcomes")
    try:
        if row:
            con.execute("DROP TRIGGER " + OUTCOME_DELETE_TRIGGER)
        n = con.execute("DELETE FROM " + table + " WHERE rowid <= ?", (hi,)).rowcount or 0
        if row:
            con.execute(row[0])
        con.execute("RELEASE SAVEPOINT log_retention_outcomes")
        return n
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT log_retention_outcomes")
        con.execute("RELEASE SAVEPOINT log_retention_outcomes")
        raise


def prune(con, cycle: int, retention: int = None, budget: int = None) -> Dict[str, int]:
    """Deletes log rows older than `retention` cycles (at most `budget` rows
    per table). Returns the deleted rows per table."""
    retention = RETENTION_CYCLES if retention is None else retention
    budget = ROW_BUDGET if budget is None else budget
    deleted: Dict[str, int] = {}
    for table in LOG_TABLES:
        if not _table_exists(con, table):
            continue
        row = con.execute("SELECT max_rowid FROM " + MARKS_TABLE + " WHERE table_name=? AND cycle<=? "
                          "ORDER BY cycle DESC LIMIT 1", (table, cycle - retention)).fetchone()
        if not row:
            continue
        n = _delete_upto(con, table, int(row[0]), budget)
        if n:
            deleted[table] = n
    con.execute("DELETE FROM " + MARKS_TABLE + " WHERE cycle < ?", (cycle - retention - PRUNE_EVERY * 4,))
    return deleted


def run_log_retention_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    st = _state(con)
    if str(st.get("enabled", "true")).lower() != "true":
        return {"status": "log_retention_disabled"}
    cycle = _int(st.get("cycle_count"), 0) + 1
    _set(con, "cycle_count", cycle)
    marks = record_marks(con, cycle) if cycle % MARK_EVERY == 0 else 0
    deleted: Dict[str, int] = {}
    if _sleeping(con) and cycle - _int(st.get("last_prune_cycle"), 0) >= PRUNE_EVERY:
        deleted = prune(con, cycle)
        _set(con, "last_prune_cycle", cycle)
        if deleted:
            _set(con, "rows_deleted_total", _int(st.get("rows_deleted_total"), 0) + sum(deleted.values()))
    con.commit()
    return {"status": "log_retention_cycle", "cycle": cycle, "marks_recorded": marks,
            "rows_deleted": sum(deleted.values()), "deleted_per_table": deleted}


def _db(loop):
    memory = getattr(loop, "mem", None) or getattr(loop, "memory", None) or getattr(loop, "db", None)
    connection = getattr(memory, "db", None) or getattr(memory, "conn", None) or memory
    if not hasattr(connection, "execute"):
        raise RuntimeError("sqlite connection not found")
    return connection


_PREV_CYCLE = None
_PREV_RUN = None


def managed_cycle(self, progress=None):
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else {"status": "log_retention_no_previous_cycle"}
    try:
        result = run_log_retention_cycle(_db(self))
    except Exception as exc:
        result = {"status": "log_retention_error", "error": type(exc).__name__ + ":" + str(exc)}
    return {"phase": PHASE, "downstream_result": result_prev, "log_retention_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.log_retention_maintenance = True
    return AutonomousLoop
