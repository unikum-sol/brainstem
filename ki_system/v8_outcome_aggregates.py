# -*- coding: utf-8 -*-
"""Incrementally maintained aggregates over phase5g_experiment_outcomes.

Phases 5h and 5i summarize the whole experiment-outcome history every cycle
(group-wise counts and averages). Recomputing them by a full scan grows
linearly with that history (2.3 million rows in production, ~1.4 s per query
per cycle). Instead, per-group sums and non-NULL counts are kept current by
SQLite triggers on INSERT/UPDATE/DELETE (incremental view maintenance), and
the two summaries are read from this small table. Results are the same
averages as the full scans (up to floating-point summation order).

Literatur: Gupta & Mumick 1995; Koch et al. 2014
"""
from __future__ import annotations

import sqlite3
from typing import List

SOURCE = "phase5g_experiment_outcomes"
AGG = "phase5g_outcome_aggregates"
STATE = "phase5g_outcome_aggregates_state"
NULL = "#NULL#"
KEYS = ("selected_strategy", "window_strategy", "strategy", "gap_type", "role")
H_COLS = ("outcome_score", "closure_delta", "no_candidate_rate", "overlap_score", "strategy_score",
          "learning_rate", "error_weight", "revision_pressure", "exploration_pressure",
          "inhibition_level", "consolidation_gain")
I_EXPRS = {
    "i_outcome": "COALESCE({p}outcome_score,{p}effectiveness_score,0)",
    "i_closure": "COALESCE({p}closure_delta,0)",
    "i_overlap": "COALESCE({p}overlap_score,0)",
    "i_nocand": "COALESCE({p}no_candidate_rate,{p}no_candidate_penalty,0)",
}
REQUIRED = set(KEYS) | set(H_COLS) | {"effectiveness_score", "no_candidate_penalty"}
VERSION = "1"


def _columns(con, table):
    return {r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()}


def _values(prefix: str, sign: str) -> List[str]:
    vals = ["COALESCE(%s%s,'%s')" % (prefix, k, NULL) for k in KEYS]
    vals.append(sign + "1")
    for c in H_COLS:
        vals.append("%s COALESCE(%s%s,0)" % (sign, prefix, c))
        vals.append("%s (%s%s IS NOT NULL)" % (sign, prefix, c))
    vals += ["%s %s" % (sign, e.format(p=prefix)) for e in I_EXPRS.values()]
    return vals


def _agg_columns() -> List[str]:
    cols = ["n"]
    for c in H_COLS:
        cols += ["s_" + c, "c_" + c]
    return cols + list(I_EXPRS)


def _upsert(prefix: str, sign: str) -> str:
    cols = list(KEYS) + _agg_columns()
    upd = ", ".join("%s=%s+excluded.%s" % (c, c, c) for c in _agg_columns())
    return ("INSERT INTO %s(%s) VALUES(%s) ON CONFLICT(%s) DO UPDATE SET %s;"
            % (AGG, ",".join(cols), ",".join(_values(prefix, sign)), ",".join(KEYS), upd))


def available(con) -> bool:
    try:
        return REQUIRED.issubset(_columns(con, SOURCE))
    except sqlite3.Error:
        return False


def ensure(con) -> bool:
    """Create aggregate table + triggers and backfill once. False if the
    source table does not (yet) have all required columns."""
    if not available(con):
        return False
    state = {}
    try:
        state = dict(con.execute("SELECT key,value FROM " + STATE).fetchall())
    except sqlite3.Error:
        pass
    if state.get("version") == VERSION and state.get("built") == "1":
        return True
    con.execute("SAVEPOINT outcome_aggregates")
    try:
        for t in ("ins", "upd", "del"):
            con.execute("DROP TRIGGER IF EXISTS trg_%s_%s" % (AGG, t))
        con.execute("DROP TABLE IF EXISTS " + AGG)
        coldefs = ", ".join("%s TEXT NOT NULL" % k for k in KEYS)
        coldefs += ", n INTEGER NOT NULL DEFAULT 0"
        for c in H_COLS:
            coldefs += ", s_%s REAL NOT NULL DEFAULT 0, c_%s INTEGER NOT NULL DEFAULT 0" % (c, c)
        coldefs += "".join(", %s REAL NOT NULL DEFAULT 0" % k for k in I_EXPRS)
        con.execute("CREATE TABLE %s (%s, PRIMARY KEY(%s))" % (AGG, coldefs, ",".join(KEYS)))
        con.execute("CREATE TABLE IF NOT EXISTS %s (key TEXT PRIMARY KEY, value TEXT)" % STATE)
        sel = ["COALESCE(%s,'%s')" % (k, NULL) for k in KEYS] + ["COUNT(*)"]
        for c in H_COLS:
            sel += ["TOTAL(%s)" % c, "COUNT(%s)" % c]
        sel += ["TOTAL(%s)" % e.format(p="") for e in I_EXPRS.values()]
        con.execute("INSERT INTO %s(%s) SELECT %s FROM %s GROUP BY %s"
                    % (AGG, ",".join(list(KEYS) + _agg_columns()), ",".join(sel), SOURCE,
                       ",".join("COALESCE(%s,'%s')" % (k, NULL) for k in KEYS)))
        watched = ",".join(sorted(REQUIRED))
        con.execute("CREATE TRIGGER trg_%s_ins AFTER INSERT ON %s BEGIN %s END" % (AGG, SOURCE, _upsert("NEW.", "")))
        con.execute("CREATE TRIGGER trg_%s_upd AFTER UPDATE OF %s ON %s BEGIN %s %s END"
                    % (AGG, watched, SOURCE, _upsert("OLD.", "-"), _upsert("NEW.", "")))
        con.execute("CREATE TRIGGER trg_%s_del AFTER DELETE ON %s BEGIN %s END" % (AGG, SOURCE, _upsert("OLD.", "-")))
        con.execute("INSERT OR REPLACE INTO %s(key,value) VALUES('version',?),('built','1')" % STATE, (VERSION,))
        con.execute("RELEASE SAVEPOINT outcome_aggregates")
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT outcome_aggregates")
        con.execute("RELEASE SAVEPOINT outcome_aggregates")
        raise
    return True


def _nk(col: str) -> str:
    return "NULLIF(%s,'%s')" % (col, NULL)


def strategy_memory_rows(con):
    """Same rows as: SELECT selected_strategy,gap_type,role,COUNT(*),AVG(<H_COLS>...)
    FROM phase5g_experiment_outcomes GROUP BY selected_strategy,gap_type,role"""
    avgs = ",".join("SUM(s_%s)/NULLIF(SUM(c_%s),0)" % (c, c) for c in H_COLS)
    return con.execute(
        "SELECT %s,%s,%s,SUM(n),%s FROM %s WHERE n>0 GROUP BY selected_strategy,gap_type,role"
        % (_nk("selected_strategy"), _nk("gap_type"), _nk("role"), avgs, AGG)).fetchall()


def diversification_rows(con):
    """Same rows as phase 5i's grouping by COALESCE(gap_type,'unknown'),
    COALESCE(role,'unknown'), COALESCE(selected_strategy,window_strategy,strategy,'unknown_strategy')."""
    g1 = "COALESCE(%s,'unknown')" % _nk("gap_type")
    g2 = "COALESCE(%s,'unknown')" % _nk("role")
    g3 = "COALESCE(%s,%s,%s,'unknown_strategy')" % (_nk("selected_strategy"), _nk("window_strategy"), _nk("strategy"))
    avgs = ",".join("SUM(%s)*1.0/SUM(n)" % k for k in I_EXPRS)
    return con.execute("SELECT %s,%s,%s,SUM(n),%s FROM %s WHERE n>0 GROUP BY 1,2,3"
                       % (g1, g2, g3, avgs, AGG)).fetchall()
