# -*- coding: utf-8 -*-
"""One durable commit per learning cycle.

A cycle used to commit about 74 times, because almost every phase ends with
con.commit() and many schema checks commit as well. On the storage pool each
commit writes the changed pages to the WAL again, so the commits took more
time than the computation.

Within a cycle, a commit of the Memory connection now only marks a boundary:
the work up to it is kept in the cycle's transaction (RELEASE of a step
savepoint) and a new step begins. A rollback undoes the work since the last
boundary, the same scope it had before. The cycle ends with exactly one real
commit, also when it raises, so all work done before an error is kept as
before. Savepoints of the phases nest inside the cycle transaction.

Connections that are not a CycleConnection (for example a direct
sqlite3.connect in a tool) run their cycles as before.
"""
import sqlite3

from ki_system import learning_clock

STEP = "bs_cycle_step"


class CycleConnection(sqlite3.Connection):
    """sqlite3.Connection whose commit() is a step boundary inside a cycle."""

    _bundle = False
    real_commits = 0
    boundaries = 0

    def _open_step(self):
        if not self.in_transaction:
            self.execute("BEGIN")
        self.execute("SAVEPOINT " + STEP)

    def begin_cycle(self):
        if self.in_transaction:
            # Work outside a cycle stays as durable as it was.
            sqlite3.Connection.commit(self)
            self.real_commits += 1
        self._open_step()
        self._bundle = True

    def end_cycle(self):
        self._bundle = False
        try:
            self.execute("RELEASE SAVEPOINT " + STEP)
        except sqlite3.OperationalError:
            pass
        if self.in_transaction:
            sqlite3.Connection.commit(self)
            self.real_commits += 1

    def commit(self):
        if not self._bundle:
            sqlite3.Connection.commit(self)
            self.real_commits += 1
            return
        self.boundaries += 1
        try:
            self.execute("RELEASE SAVEPOINT " + STEP)
        except sqlite3.OperationalError:
            # The step savepoint is gone (a phase released an enclosing
            # savepoint); the transaction itself is still open or ended.
            pass
        self._open_step()

    def rollback(self):
        # Cached statistics may describe rolled-back data.
        learning_clock.bump_data_epoch()
        if not self._bundle:
            sqlite3.Connection.rollback(self)
            return
        try:
            self.execute("ROLLBACK TO SAVEPOINT " + STEP)
        except sqlite3.OperationalError:
            sqlite3.Connection.rollback(self)
            self._open_step()


_PREV_CYCLE = None
# Switch for measurements; True in normal operation.
ENABLED = True


def _connection(loop):
    memory = getattr(loop, "memory", None)
    con = getattr(memory, "db", None)
    return con if isinstance(con, CycleConnection) else None


def _tick(con):
    """One tick of the learning clock per cycle (learning_clock.py), kept by
    a step boundary so that a rollback inside a phase cannot undo it."""
    learning_clock.advance(con)
    con.commit()


def managed_cycle(self, *args, **kwargs):
    con = _connection(self)
    if con is not None and con._bundle:
        return _PREV_CYCLE(self, *args, **kwargs)
    if con is None or not ENABLED:
        plain = getattr(getattr(self, "memory", None), "db", None)
        if plain is not None:
            _tick(plain)
        return _PREV_CYCLE(self, *args, **kwargs)
    con.begin_cycle()
    try:
        _tick(con)
        return _PREV_CYCLE(self, *args, **kwargs)
    finally:
        con.end_cycle()


def managed_run(self, cycles=1, progress=None):
    return {"phase": "cycle_transaction",
            "results": [self.cycle(progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle_transaction = True
    return AutonomousLoop
