# -*- coding: utf-8 -*-
"""Learning clock and seeded randomness: learning does not depend on the wall
clock or on chance, so two runs from the same state end in the same state.

Time inside learning is experience time. One learning cycle advances the
clock by one tick; decay, recency and ordering therefore count cycles, not
seconds of computation. Forgetting depends on intervening events more than
on elapsed time (Jenkins & Dallenbach 1924; Wixted 2004), and the brain's
sense of time is built from the flow of experience (Howard & Kahana 2002;
Tsao et al. 2018). On this machine, wall-clock seconds would only measure
how fast the CPU and the storage pool are.

    now()  = base + cycle          (constant within a cycle)
    rng()  = random.Random(seed)   seed = blake2b(run_seed|cycle|phase|purpose)

`base` is set once, at the first use on a database, to one second after the
newest timestamp found in it, so learning timestamps continue the existing
ones in order and the value is the same for byte-identical copies. The
counter-based seeds keep every random stream independent and repeatable
(Salmon et al. 2011); a different `run_seed` gives a replicate run for
benchmarks. The noise keeps its distribution, only its source is fixed
(Faisal, Selen & Wolpert 2008).

Wall-clock time stays in use outside learning: GUI, imports, logs, log
compaction and WAL maintenance.
"""
import hashlib
import random
import re
import time

TABLE = "learning_clock"
_TIME_COL = re.compile(r"(_at$|^ts$|timestamp)", re.I)
# Tables above this size are checked by their newest rows only.
_FULL_SCAN_LIMIT = 200000
FRESH_BASE = 1700000000

_state = {"base": None, "cycle": None, "run_seed": None, "data_epoch": 0}


def _ensure(con):
    con.execute("CREATE TABLE IF NOT EXISTS " + TABLE + " (key TEXT PRIMARY KEY, value TEXT)")


def _newest_timestamp(con):
    newest = 0
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "AND name<>? ORDER BY name", (TABLE,))]
    for name in tables:
        try:
            cols = [r[1] for r in con.execute('PRAGMA table_info("%s")' % name)]
        except Exception:
            continue
        tcols = [c for c in cols if _TIME_COL.search(c)]
        if not tcols:
            continue
        try:
            n = con.execute('SELECT MAX(rowid) FROM "%s"' % name).fetchone()[0] or 0
        except Exception:
            continue
        for c in tcols:
            if n <= _FULL_SCAN_LIMIT:
                sql = 'SELECT MAX("%s") FROM "%s" WHERE typeof("%s") IN (\'integer\',\'real\')' % (c, name, c)
            else:
                sql = ('SELECT MAX("%s") FROM (SELECT "%s" FROM "%s" ORDER BY rowid DESC LIMIT 2000) '
                       'WHERE typeof("%s") IN (\'integer\',\'real\')' % (c, c, name, c))
            try:
                v = con.execute(sql).fetchone()[0]
            except Exception:
                continue
            if v is not None and v < 4e9:
                newest = max(newest, int(v))
    return newest


def attach(con, writable=True):
    """Load the clock of this database; create it on first use."""
    try:
        if writable:
            _ensure(con)
        rows = dict(con.execute("SELECT key,value FROM " + TABLE).fetchall())
    except Exception:
        rows = {}
    if not rows and writable:
        # A fresh database starts at a fixed date (14 November 2023) instead of 1970.
        base = max(_newest_timestamp(con) + 1, FRESH_BASE)
        con.executemany("INSERT OR IGNORE INTO " + TABLE + "(key,value) VALUES(?,?)",
                        [("base", str(base)), ("cycle", "0"), ("run_seed", "0"), ("step", "1")])
        con.commit()
        rows = dict(con.execute("SELECT key,value FROM " + TABLE).fetchall())
    if rows:
        _state["base"] = int(rows["base"])
        _state["cycle"] = int(rows["cycle"])
        _state["run_seed"] = str(rows.get("run_seed", "0"))


def advance(con):
    """Start a new learning cycle: one tick, written in the cycle's transaction."""
    if _state["base"] is None:
        attach(con)
    con.execute("UPDATE " + TABLE + " SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT) WHERE key='cycle'")
    _state["cycle"] = int(con.execute("SELECT value FROM " + TABLE + " WHERE key='cycle'").fetchone()[0])
    return _state["cycle"]


def rewind():
    """The cycle transaction was rolled back; reload on next use."""
    _state["base"] = None


def now():
    """Learning time in seconds-like ticks; wall clock only if no clock is attached."""
    if _state["base"] is None:
        return int(time.time())
    return _state["base"] + _state["cycle"]


def cycle():
    return _state["cycle"] or 0


def rng(phase, purpose=""):
    """A random generator for one phase and purpose in the current cycle."""
    key = "%s|%d|%s|%s" % (_state["run_seed"] or "0", cycle(), phase, purpose)
    seed = int.from_bytes(hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest(), "big")
    return random.Random(seed)


def set_run_seed(con, seed):
    """Choose another replicate for benchmarks (stored in the database)."""
    attach(con)
    con.execute("UPDATE " + TABLE + " SET value=? WHERE key='run_seed'", (str(seed),))
    con.commit()
    _state["run_seed"] = str(seed)


def data_epoch():
    """Changes whenever cached learned statistics may be stale: on every
    write of the transition counts (Phase 0) and on every rollback."""
    return _state["data_epoch"]


def bump_data_epoch():
    _state["data_epoch"] += 1


def uniform(phase, key):
    """A uniform number in [0, 1) for one item in the current cycle, fixed by
    run seed, cycle, phase and item key; cheaper than a generator per item."""
    text = "%s|%d|%s|%s" % (_state["run_seed"] or "0", cycle(), phase, key)
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big") / 18446744073709551616.0
