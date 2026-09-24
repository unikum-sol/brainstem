# -*- coding: utf-8 -*-
"""V8 Stage-B Fact Promotion -- the only module that actually calls
memory.py's add_fact()/add_relation() (previously guarded to a no-op) and
retracts a fact again if its source hypothesis is later reversed.

BACKGROUND: this module is part of a user-requested, explicitly framed
experiment (full project backup taken beforehand, with an explicit intent
to revert if the outcome is not productive) to lift the previously-closed
productive Facts/Relations write locks. A project-wide code audit
confirmed before this change that memory.py's BRAINSTEM_PURE_WRITE_GUARD
had zero call sites anywhere in the codebase -- removing it alone would
have had no effect, since nothing called the guarded methods. This module
is the first and only caller.

DESIGN, per the project owner's explicit requirements (22 September 2026):
1. The threshold for "a hypothesis is well-enough observed to become a
   fact" is the ALREADY-EXISTING, unmodified Stage-B graduation gate
   (three separate Phase-7d consolidation survival cycles + the critic
   gate in v8_phase6b_..._critic_gate) -- no new, separate, or lower
   threshold is introduced. This module does not decide who graduates; it
   only reacts, once per real graduation event, to a decision the
   existing, already-tested graduation module already made.
2. A fact is NOT permanently fixed: if the hypothesis it came from is
   later reversed (see v8_stageb_hypothesis_revision_release.py, itself
   only triggered by v8_stageb_contradiction_detection_release.py finding
   a clear, resolvable contradiction), the corresponding fact is deleted
   again. facts has no separate status column (adding one would have been
   a larger, not-requested schema change), so retraction is a real DELETE,
   not a soft-flag -- this is a deliberate, explicitly documented design
   choice, not an oversight (see CHANGES.txt for the full discussion).
   The full history remains reconstructable via stageb_fact_promotion_
   events (this module's own append-only log, never deleted) and via
   hypothesis_revisions (already written by the revision module).

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
    # BRAINSTEM_SCHEMA_CENTRALIZATION_GAP_FIX_V1 (23.09.2026)
    #
    # Root cause, confirmed against a fresh, bootstrap-only database:
    # facts.source_hypothesis_id (declared only in memory.py's own
    # Memory.CORE_IMPORT_SCHEMA / _ensure_core_import_schema()) was never
    # added by this module's own ensure_schema(), nor was it mirrored into
    # db_bootstrap.py's central SCHEMA_TABLES. The self-check further below
    # correctly detected this and refused to write (per this project's
    # "idempotentes ensure_schema, _self_check_schema, alle Spalten vorab
    # in SCHEMA_TABLES" rule) -- but that rule requires the column to
    # actually be addable BY this check, not merely verified by it. In the
    # real GUI/main.py startup path this was silently masked because
    # main.py always calls db_bootstrap.ensure_database_exists() AND
    # constructs a Memory() (which runs its own ALTER TABLE ADD COLUMN for
    # this column) before any AutonomousLoop cycle ever runs -- but that
    # made this module's correctness depend on call order across two
    # unrelated bootstrap paths instead of being self-contained.
    #
    # Fix: this module's own ensure_schema() now adds the column itself if
    # missing (idempotent ALTER TABLE ADD COLUMN, nullable INTEGER matching
    # memory.py's own declaration exactly, so both remain fully compatible
    # regardless of which runs first, and no pre-existing facts row is
    # affected), matching the same self-contained "idempotentes
    # ensure_schema" convention already used by every other phase module in
    # this codebase. Also mirrored into db_bootstrap.py's central
    # SCHEMA_TABLES as defense-in-depth.
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
        "WHERE id>? AND decision LIKE 'graduated_to_%' ORDER BY id LIMIT 200",
        (last_id,),
    ).fetchall()
    promoted = 0
    max_id_seen = last_id
    for event_id, hid, new_role in rows:
        max_id_seen = max(max_id_seen, event_id)
        hyp = con.execute(
            "SELECT text_excerpt, subject, confidence FROM context_hypotheses WHERE id=?",
            (hid,),
        ).fetchone()
        if hyp is None:
            continue
        text_excerpt, subject, confidence = hyp
        subject_value = (subject or text_excerpt or "").strip()[:180]
        if not subject_value:
            continue
        # Deliberately simple, transparent fact shape: subject is the
        # hypothesis's own already-recorded subject (or its text_excerpt
        # if subject is empty, e.g. for a lexical boundary), relation is a
        # fixed, explicit label naming exactly what this fact asserts (an
        # observation the system itself made, not an externally-supplied
        # ground truth), value is the full observed excerpt, confidence is
        # the hypothesis's own already-computed confidence score. No new
        # scoring or classification logic is introduced here.
        existing_fact = con.execute(
            "SELECT id FROM facts WHERE source_hypothesis_id=?", (hid,)
        ).fetchone()
        if existing_fact:
            continue
        cur = con.execute(
            "INSERT OR IGNORE INTO facts(subject,relation,value,confidence,source_chunk_id,"
            "created_at,source_hypothesis_id) VALUES(?,?,?,?,?,?,?)",
            (subject_value, "observed_as", (text_excerpt or subject_value)[:500],
             _float(confidence, 0.5), None, now, hid),
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
            promoted += 1
    if max_id_seen != last_id:
        _set_kv(con, STATE_TABLE, "last_promoted_graduation_event_id", max_id_seen)
    return {"promoted": promoted}


def _retract_from_revisions(con, now) -> Dict[str, int]:
    """Read revision events (a hypothesis being reversed back to an
    uncertain role, see v8_stageb_hypothesis_revision_release.py) that
    have not yet been acted on, and delete the corresponding fact, if one
    exists. This is the mechanism that keeps a fact correctable rather
    than permanently fixed, per the project owner's explicit requirement."""
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
    return AutonomousLoop
