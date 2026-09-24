# -*- coding: utf-8 -*-
"""V8 Stage-B Hypothesis Revision -- fills the previously-empty
hypothesis_revisions table and reverses a previous graduation when a
contradiction resolves clearly against a hypothesis.

BACKGROUND (found via the same project-wide code audit as the other two
new Stage-B modules, 22 September 2026): `hypothesis_revisions` has
existed as a fully-declared table (in db_bootstrap.py's central
SCHEMA_TABLES) with no module anywhere ever writing to it. There has
never been any mechanism in this project that reverses a hypothesis's
role back from 'stable_hypothesis'/'stable_lexical_boundary' to
'uncertain_hypothesis'/'uncertain_lexical_boundary' -- graduation
(v8_stageb_guarded_hypothesis_graduation_release.py) has always been a
one-way street. This directly addresses an explicit requirement from the
project owner: facts derived from hypotheses must remain correctable if a
hypothesis later turns out to be wrong, not permanently fixed once
graduated.

THIS MODULE'S JOB: consume 'resolvable' contradictions already identified
by v8_stageb_contradiction_detection_release.py (reusing its output
rather than re-deciding anything), and for the hypothesis on the losing
side, reverse its role back to its pre-graduation uncertain role -- using
the EXACT SAME protected-write-count safety pattern already established
and tested in v8_stageb_guarded_hypothesis_graduation_release.py
(SAVEPOINT + before/after comparison of facts/relations/questions, with an
automatic rollback if anything protected unexpectedly changes). A
`hypothesis_revisions` row is written recording the old/new role and
confidence/uncertainty, giving this decision the same durable,
inspectable audit trail this project already requires for graduation
itself.

Explicitly NOT part of this module: no fact/relation/question writes of
its own (see v8_stageb_fact_promotion_release.py, which listens for a
revision event and retracts the corresponding fact, if one exists). No
change to contradiction records themselves beyond marking them as acted
upon.
"""
from __future__ import annotations
import json
import sqlite3
import time
from typing import Any, Dict

PHASE = "stageb_hypothesis_revision_release"
STATE_TABLE = "stageb_revision_state"
EVENTS = "hypothesis_revisions"
PROTECTED = ("facts", "relations", "questions")
# Mirrors v8_stageb_guarded_hypothesis_graduation_release.py's own
# ELIGIBLE_ROLES map, inverted: which stable role reverts to which
# uncertain role. Deliberately a small, explicit, easy-to-audit mapping
# (not a generic string-prefix rule) for the same reason that module gives
# for its own ELIGIBLE_ROLES: so no future, unrelated role could ever
# accidentally become revision-eligible via a wildcard match.
REVERT_ROLES = {
    "stable_hypothesis": "uncertain_hypothesis",
    "stable_lexical_boundary": "uncertain_lexical_boundary",
}
DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    # Mirrors the graduation module's own promotion_budget convention: at
    # most this many revisions per real cycle, deliberately conservative.
    "revision_budget": "1",
    "total_revised": "0",
}


def _now() -> int:
    return int(time.time())


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _table_exists(con, table) -> bool:
    return con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return set()
    return {row[1] for row in con.execute("PRAGMA table_info(" + table + ")").fetchall()}


def ensure_schema(con) -> bool:
    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    missing = []
    required_revision_cols = {
        "id", "hypothesis_id", "old_role", "new_role", "reason", "details",
        "created_at", "old_confidence", "new_confidence", "old_uncertainty", "new_uncertainty",
    }
    have = _columns(con, EVENTS)
    missing.extend(EVENTS + "." + c for c in required_revision_cols - have)
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if missing:
        raise RuntimeError("stageb hypothesis revision schema missing: " + repr(missing))
    return True


def _read_kv(con, table) -> Dict[str, str]:
    if not _table_exists(con, table):
        return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())


def _set_kv(con, table, key, value):
    con.execute(
        "INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
        (key, str(value), _now()),
    )


def _int(v, d=0) -> int:
    try:
        return int(float(v))
    except Exception:
        return d


def _float(v, d=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return d


def _count(con, table) -> int:
    if not _table_exists(con, table):
        return 0
    return int(con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])


def _protected(con) -> Dict[str, int]:
    return {t: _count(con, t) for t in PROTECTED}


def _resolvable_candidates(con, limit: int):
    """Read 'resolvable' contradictions and extract the loser id from the
    already-computed details_json (written by
    v8_stageb_contradiction_detection_release.py) -- this module does not
    re-derive who is weaker, it only acts on an already-made, already-
    recorded decision."""
    if not _table_exists(con, "contradictions"):
        return []
    rows = con.execute(
        "SELECT id, subject, details_json FROM contradictions "
        "WHERE status='resolvable' ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
    out = []
    for cid, subject, details_json in rows:
        try:
            details = json.loads(details_json or "{}")
        except Exception:
            continue
        resolution = details.get("resolution")
        if not isinstance(resolution, dict):
            continue
        weaker_id = resolution.get("weaker_id")
        if weaker_id is None:
            continue
        out.append({"contradiction_id": cid, "subject": subject, "hypothesis_id": weaker_id})
    return out


def run_revision_cycle(con, cycle_index=None) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    cycle = _int(cycle_index, _int(state.get("cycle_count"), 0) + 1)
    _set_kv(con, STATE_TABLE, "cycle_count", cycle)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        con.commit()
        return {"phase": PHASE, "revised": 0, "reason": "disabled", "cycle_index": cycle}
    budget = max(0, _int(state.get("revision_budget"), 1))
    if budget == 0:
        con.commit()
        return {"phase": PHASE, "revised": 0, "reason": "zero_budget", "cycle_index": cycle}

    before = _protected(con)
    revised = 0
    decisions = []
    con.execute("SAVEPOINT stageb_revision")
    try:
        for cand in _resolvable_candidates(con, limit=64):
            if revised >= budget:
                break
            hid = cand["hypothesis_id"]
            row = con.execute(
                "SELECT role, confidence, uncertainty FROM context_hypotheses WHERE id=?",
                (hid,),
            ).fetchone()
            if row is None:
                continue
            old_role, old_conf, old_unc = row
            new_role = REVERT_ROLES.get(old_role)
            if new_role is None:
                # Not currently in a revertible (graduated) role -- e.g.
                # already reverted by an earlier cycle, or never
                # graduated in the first place. Skip, do not force.
                continue

            new_conf = 0.0
            new_unc = 1.0
            cur = con.execute(
                "UPDATE context_hypotheses SET role=?, confidence=?, uncertainty=?, updated_at=? "
                "WHERE id=? AND role=? AND COALESCE(status,'active')='active'",
                (new_role, new_conf, new_unc, _now(), hid, old_role),
            )
            after_now = _protected(con)
            if after_now != before:
                raise RuntimeError("protected_productive_counts_changed")
            if cur.rowcount != 1:
                continue

            con.execute(
                "INSERT INTO " + EVENTS + "(hypothesis_id,old_role,new_role,reason,details,created_at,"
                "old_confidence,new_confidence,old_uncertainty,new_uncertainty) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (hid, old_role, new_role, "resolved_contradiction_lost_to_stronger_hypothesis",
                 _j({"contradiction_id": cand["contradiction_id"], "subject": cand["subject"]}),
                 _now(), _float(old_conf, 0.0), new_conf, _float(old_unc, 1.0), new_unc),
            )
            con.execute(
                "UPDATE contradictions SET status='resolved' WHERE id=?",
                (cand["contradiction_id"],),
            )
            revised += 1
            decisions.append({"hypothesis_id": hid, "old_role": old_role, "new_role": new_role})

        after = _protected(con)
        if after != before:
            raise RuntimeError("protected_productive_counts_changed")
        _set_kv(con, STATE_TABLE, "total_revised", _int(state.get("total_revised"), 0) + revised)
        con.execute("RELEASE SAVEPOINT stageb_revision")
        con.commit()
        return {"phase": PHASE, "cycle_index": cycle, "revised": revised, "decisions": decisions, "protected_unchanged": True}
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_revision")
        con.execute("RELEASE SAVEPOINT stageb_revision")
        con.commit()
        raise


def _db(loop):
    memory = getattr(loop, "mem", None) or getattr(loop, "memory", None) or getattr(loop, "db", None)
    connection = getattr(memory, "db", None) or getattr(memory, "conn", None) or memory
    if not hasattr(connection, "execute"):
        raise RuntimeError("sqlite connection not found")
    return connection


_PREV_CYCLE = None
_PREV_RUN = None


def managed_cycle(self, progress=None):
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else {"status": "stageb_hypothesis_revision_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_revision_cycle(con)
    except Exception as exc:
        result = {"phase": PHASE, "status": "error", "error": type(exc).__name__ + ":" + str(exc), "revised": 0}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_hypothesis_revision_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_hypothesis_revision_release = True
    return AutonomousLoop
