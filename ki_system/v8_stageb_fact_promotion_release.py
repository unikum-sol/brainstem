# -*- coding: utf-8 -*-
"""Stage-B fact promotion: graduated sentence and lexical hypotheses become
facts; a revised hypothesis retracts its fact again.

Reads (never re-derives) its promotion candidates directly from
stageb_graduation_events (decision LIKE 'graduated_to_%'), and its
retraction candidates directly from hypothesis_revisions -- both already-
existing, already-populated-by-other-modules event logs. This module adds
no new judgment about hypothesis quality of its own.
"""
from __future__ import annotations
import json
import sqlite3
import time
from typing import Any, Dict, Optional

PHASE = "stageb_fact_promotion_release"
STATE_TABLE = "stageb_fact_promotion_state"
EVENTS_TABLE = "stageb_fact_promotion_events"
PROTECTED_EXCLUDING_FACTS = ("relations", "questions")
DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    "last_promoted_graduation_event_id": "0",
    "last_processed_revision_id": "0",
    "facts_promoted_total": "0",
    "facts_retracted_total": "0",
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
    if _table_exists(con, "facts") and "source_hypothesis_id" not in _columns(con, "facts"):
        con.execute("ALTER TABLE facts ADD COLUMN source_hypothesis_id INTEGER")
    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    if not _table_exists(con, EVENTS_TABLE):
        con.execute(
            "CREATE TABLE " + EVENTS_TABLE + " ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, hypothesis_id INTEGER, "
            "fact_id INTEGER, subject TEXT, relation TEXT, value TEXT, confidence REAL, "
            "reason TEXT, created_at INTEGER)"
        )
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    missing = []
    if "source_hypothesis_id" not in _columns(con, "facts"):
        missing.append("facts.source_hypothesis_id")
    if not _table_exists(con, EVENTS_TABLE):
        missing.append(EVENTS_TABLE)
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if missing:
        raise RuntimeError("stageb fact promotion schema missing: " + repr(missing))
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


def _close_gaps_for_hypothesis(con, hypothesis_id, reason, now) -> int:
    if not _table_exists(con, "internal_learning_gaps"):
        return 0
    cols = _columns(con, "internal_learning_gaps")
    if not {"hypothesis_id", "status", "closed_at", "closure_reason"}.issubset(cols):
        return 0
    cur = con.execute(
        "UPDATE internal_learning_gaps SET status='closed', closed_at=?, closure_reason=? "
        "WHERE hypothesis_id=? AND status IN ('open','persistent_gap','habituated') "
        "AND COALESCE(gap_type,'')<>'unverified_text_contrast'",
        (now, reason[:200], hypothesis_id),
    )
    return cur.rowcount or 0


def _reopen_gaps_for_hypothesis(con, hypothesis_id, reason, now) -> int:
    if not _table_exists(con, "internal_learning_gaps"):
        return 0
    cols = _columns(con, "internal_learning_gaps")
    if not {"hypothesis_id", "status", "closed_at", "closure_reason"}.issubset(cols):
        return 0
    cur = con.execute(
        "UPDATE internal_learning_gaps SET status='open', closed_at=NULL, closure_reason=? "
        "WHERE hypothesis_id=? AND status='closed' "
        "AND COALESCE(gap_type,'')<>'contested_subject_multiple_excerpts'",
        (reason[:200], hypothesis_id),
    )
    return cur.rowcount or 0


def _protected_others(con) -> Dict[str, int]:
    """Facts is intentionally EXCLUDED from this check -- this module's
    entire purpose is to change facts. relations/questions are still
    monitored: this module never intends to touch either, so an
    unexpected change there is still worth catching."""
    return {t: _count(con, t) for t in PROTECTED_EXCLUDING_FACTS}


def _promote_from_graduations(con, now) -> Dict[str, int]:
    """Read graduation events that have not yet been turned into a fact,
    and create exactly one fact per graduated hypothesis -- reusing the
    hypothesis's own already-observed text_excerpt/consistency rather than
    inventing any new content."""
    if not _table_exists(con, "stageb_graduation_events") or not _table_exists(con, "context_hypotheses"):
        return {"promoted": 0}
    state = _read_kv(con, STATE_TABLE)
    last_id = _int(state.get("last_promoted_graduation_event_id"), 0)
    rows = con.execute(
        "SELECT id, hypothesis_id, new_role FROM stageb_graduation_events "
        "WHERE id>? AND decision LIKE 'graduated_to_%' AND new_role='stable_hypothesis' "
        "ORDER BY id LIMIT 200",
        (last_id,),
    ).fetchall()
    promoted = 0
    max_id_seen = last_id
    for event_id, hid, new_role in rows:
        max_id_seen = max(max_id_seen, event_id)
        hyp = con.execute(
            "SELECT text_excerpt, subject, confidence, chunk_id FROM context_hypotheses WHERE id=?",
            (hid,),
        ).fetchone()
        if hyp is None:
            continue
        text_excerpt, subject, confidence, chunk_id = hyp
        subject_value = (subject or text_excerpt or "").strip()[:180]
        if not subject_value:
            continue
        existing_fact = con.execute(
            "SELECT id FROM facts WHERE source_hypothesis_id=?", (hid,)
        ).fetchone()
        if existing_fact:
            continue
        cur = con.execute(
            "INSERT OR IGNORE INTO facts(subject,relation,value,confidence,source_chunk_id,"
            "created_at,source_hypothesis_id) VALUES(?,?,?,?,?,?,?)",
            (subject_value, "observed_as", (text_excerpt or subject_value)[:500],
             _float(confidence, 0.5), chunk_id, now, hid),
        )
        if cur.rowcount:
            fact_id = cur.lastrowid
            con.execute(
                "INSERT INTO " + EVENTS_TABLE + "(event_type,hypothesis_id,fact_id,subject,relation,"
                "value,confidence,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("fact_promoted", hid, fact_id, subject_value, "observed_as",
                 (text_excerpt or subject_value)[:500], _float(confidence, 0.5),
                 "graduated_via_stageb_event:" + str(event_id), now),
            )
            _close_gaps_for_hypothesis(con, hid, "fact_promoted:fact_id=" + str(fact_id), now)
            promoted += 1
    if max_id_seen != last_id:
        _set_kv(con, STATE_TABLE, "last_promoted_graduation_event_id", max_id_seen)
    return {"promoted": promoted}


def _retract_from_revisions(con, now) -> Dict[str, int]:
    if not _table_exists(con, "hypothesis_revisions"):
        return {"retracted": 0}
    state = _read_kv(con, STATE_TABLE)
    last_id = _int(state.get("last_processed_revision_id"), 0)
    rows = con.execute(
        "SELECT id, hypothesis_id, old_role, new_role FROM hypothesis_revisions "
        "WHERE id>? ORDER BY id LIMIT 200",
        (last_id,),
    ).fetchall()
    retracted = 0
    max_id_seen = last_id
    for rev_id, hid, old_role, new_role in rows:
        max_id_seen = max(max_id_seen, rev_id)
        fact_row = con.execute(
            "SELECT id, subject, relation, value, confidence FROM facts WHERE source_hypothesis_id=?",
            (hid,),
        ).fetchone()
        if fact_row is None:
            continue
        fact_id, subject, relation, value, confidence = fact_row
        con.execute("DELETE FROM facts WHERE id=?", (fact_id,))
        con.execute(
            "INSERT INTO " + EVENTS_TABLE + "(event_type,hypothesis_id,fact_id,subject,relation,"
            "value,confidence,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            ("fact_retracted", hid, fact_id, subject, relation, value, confidence,
             "hypothesis_revised_" + old_role + "_to_" + new_role + ":revision_id:" + str(rev_id), now),
        )
        _reopen_gaps_for_hypothesis(con, hid, "fact_retracted:revision_id=" + str(rev_id), now)
        retracted += 1
    if max_id_seen != last_id:
        _set_kv(con, STATE_TABLE, "last_processed_revision_id", max_id_seen)
    return {"retracted": retracted}


def run_fact_promotion_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_fact_promotion_disabled", "promoted": 0, "retracted": 0}
    now = _now()

    before_others = _protected_others(con)
    con.execute("SAVEPOINT stageb_fact_promotion")
    try:
        promotion_result = _promote_from_graduations(con, now)
        retraction_result = _retract_from_revisions(con, now)
        after_others = _protected_others(con)
        if after_others != before_others:
            raise RuntimeError("relations_or_questions_changed_unexpectedly")

        _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
        _set_kv(con, STATE_TABLE, "facts_promoted_total",
                _int(state.get("facts_promoted_total"), 0) + promotion_result["promoted"])
        _set_kv(con, STATE_TABLE, "facts_retracted_total",
                _int(state.get("facts_retracted_total"), 0) + retraction_result["retracted"])
        con.execute("RELEASE SAVEPOINT stageb_fact_promotion")
        con.commit()
        return {
            "status": "stageb_fact_promotion_cycle",
            "promoted": promotion_result["promoted"],
            "retracted": retraction_result["retracted"],
            "facts_total": _count(con, "facts"),
        }
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_fact_promotion")
        con.execute("RELEASE SAVEPOINT stageb_fact_promotion")
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
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else {"status": "stageb_fact_promotion_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_fact_promotion_cycle(con)
    except Exception as exc:
        result = {"status": "stageb_fact_promotion_error", "error": type(exc).__name__ + ":" + str(exc), "promoted": 0, "retracted": 0}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_fact_promotion_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_fact_promotion_release = True
    AutonomousLoop.fact_promotion = "enabled"
    return AutonomousLoop
