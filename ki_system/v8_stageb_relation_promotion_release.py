# -*- coding: utf-8 -*-
"""Stage-B relation promotion: graduated relation hypotheses become relations;
a revised hypothesis retracts its relation again.

Structurally an exact mirror of v8_stageb_fact_promotion_release.py -- same
promote-then-retract-on-reversal pattern, same guarded-write discipline,
same event-log design -- applied to a different graduated role
('stable_relation_hypothesis' instead of 'stable_hypothesis') and a
different target table (relations instead of facts).

source/relation/target are taken directly from the hypothesis's own
already-populated subject/relation_hint/object fields (filled in by
v8_phase0b_relational_binding_observation_release.py's Gate-&-Direction
mechanism) -- no new text generation happens here, exactly matching fact
promotion's own "no new scoring or classification logic" discipline.
"""
from __future__ import annotations
import json
import time
from typing import Any, Dict

PHASE = "stageb_relation_promotion_release"
STATE_TABLE = "stageb_relation_promotion_state"
EVENTS_TABLE = "stageb_relation_promotion_events"
PROTECTED_EXCLUDING_RELATIONS = ("facts", "questions")
DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    "last_promoted_graduation_event_id": "0",
    "last_processed_revision_id": "0",
    "relations_promoted_total": "0",
    "relations_retracted_total": "0",
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
    from ki_system.semantic_evidence import ensure_schema as ensure_evidence
    ensure_evidence(con)
    if _table_exists(con, "relations") and "source_hypothesis_id" not in _columns(con, "relations"):
        con.execute("ALTER TABLE relations ADD COLUMN source_hypothesis_id INTEGER")
    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    if not _table_exists(con, EVENTS_TABLE):
        con.execute(
            "CREATE TABLE " + EVENTS_TABLE + " ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, hypothesis_id INTEGER, "
            "relation_id INTEGER, source TEXT, relation TEXT, target TEXT, confidence REAL, "
            "reason TEXT, created_at INTEGER)"
        )
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    missing = []
    if "source_hypothesis_id" not in _columns(con, "relations"):
        missing.append("relations.source_hypothesis_id")
    if not _table_exists(con, EVENTS_TABLE):
        missing.append(EVENTS_TABLE)
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if missing:
        raise RuntimeError("stageb relation promotion schema missing: " + repr(missing))
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
    """Relations is intentionally EXCLUDED -- this module's entire purpose
    is to change relations. facts/questions are still monitored: this
    module never intends to touch either, so an unexpected change there is
    still worth catching."""
    return {t: _count(con, t) for t in PROTECTED_EXCLUDING_RELATIONS}


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
    """Counterpart to _close_gaps_for_hypothesis(); see
    v8_stageb_fact_promotion_release.py's own function of the same name
    for the full rationale."""
    if not _table_exists(con, "internal_learning_gaps"):
        return 0
    cols = _columns(con, "internal_learning_gaps")
    if not {"hypothesis_id", "status", "closed_at", "closure_reason"}.issubset(cols):
        return 0
    cur = con.execute(
        "UPDATE internal_learning_gaps SET status='open', closed_at=NULL, closure_reason=? "
        "WHERE hypothesis_id=? AND status='closed'",
        (reason[:200], hypothesis_id),
    )
    return cur.rowcount or 0


def _promote_from_graduations(con, now) -> Dict[str, int]:
    """Read graduation events for the relation-specific role only, and
    create exactly one relation per graduated hypothesis -- reusing the
    hypothesis's own already-populated subject/relation_hint/object fields
    (assigned by the Gate-&-Direction mechanism in
    v8_phase0b_relational_binding_observation_release.py) rather than
    inventing any new content."""
    if not _table_exists(con, "stageb_graduation_events") or not _table_exists(con, "context_hypotheses"):
        return {"promoted": 0}
    state = _read_kv(con, STATE_TABLE)
    last_id = _int(state.get("last_promoted_graduation_event_id"), 0)
    rows = con.execute(
        "SELECT id, hypothesis_id, new_role FROM stageb_graduation_events "
        "WHERE id>? AND decision LIKE 'graduated_to_%' AND new_role='stable_relation_hypothesis' "
        "ORDER BY id LIMIT 200",
        (last_id,),
    ).fetchall()
    # Revisit deferred stable hypotheses round-robin: missing surface evidence
    # must not become a permanent rejection when the event checkpoint advances.
    retry_checkpoint = _int(state.get("surface_retry_checkpoint"), 0)
    def retries(after):
        return con.execute("SELECT MAX(g.id),h.id,h.role FROM context_hypotheses h "
            "JOIN stageb_graduation_events g ON g.hypothesis_id=h.id "
            "WHERE h.id>? AND h.role='stable_relation_hypothesis' "
            "AND g.decision LIKE 'graduated_to_%' AND g.new_role='stable_relation_hypothesis' "
            "AND NOT EXISTS(SELECT 1 FROM relations r WHERE r.source_hypothesis_id=h.id) "
            "GROUP BY h.id ORDER BY h.id LIMIT 50",(after,)).fetchall()
    retry_rows = retries(retry_checkpoint)
    if not retry_rows:
        retry_rows = retries(0)
    if retry_rows:
        _set_kv(con, STATE_TABLE, "surface_retry_checkpoint", retry_rows[-1][1])
    rows = list(rows) + [r for r in retry_rows if r[1] not in {x[1] for x in rows}]
    promoted = 0
    deferred = 0
    max_id_seen = last_id
    for event_id, hid, new_role in rows:
        max_id_seen = max(max_id_seen, event_id)
        hyp = con.execute(
            "SELECT subject, relation_hint, object, confidence, chunk_id, origin, role "
            "FROM context_hypotheses WHERE id=?",
            (hid,),
        ).fetchone()
        if hyp is None:
            continue
        subject, relation_hint, obj, confidence, chunk_id, origin, current_role = hyp
        if current_role != "stable_relation_hypothesis":
            continue
        source_value = (subject or "").strip()[:180]
        target_value = (obj or "").strip()[:180]
        if not source_value or not target_value:
            continue
        from ki_system.semantic_evidence import relation_surface_evidence
        surface_evidence = relation_surface_evidence(con, chunk_id, source_value, target_value)
        if surface_evidence is None:
            deferred += 1
            continue
        relation_value = (relation_hint or "associated_with").strip()[:120] or "associated_with"
        existing_relation = con.execute(
            "SELECT id FROM relations WHERE source_hypothesis_id=?", (hid,)
        ).fetchone()
        if existing_relation:
            continue
        cur = con.execute(
            "INSERT OR IGNORE INTO relations(source,relation,target,confidence,source_chunk_id,"
            "created_at,source_hypothesis_id) VALUES(?,?,?,?,?,?,?)",
            (source_value, relation_value, target_value, _float(confidence, 0.5), chunk_id, now, hid),
        )
        if cur.rowcount:
            relation_id = cur.lastrowid
            con.execute("UPDATE relations SET evidence_kind=?,semantic_status='surface_supported_not_truth' WHERE id=?",
                        (surface_evidence, relation_id))
            con.execute(
                "INSERT INTO " + EVENTS_TABLE + "(event_type,hypothesis_id,relation_id,source,relation,"
                "target,confidence,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("relation_promoted", hid, relation_id, source_value, relation_value, target_value,
                 _float(confidence, 0.5),
                 "graduated_via_stageb_event:" + str(event_id) +
                 (":origin=" + origin if origin else ""), now),
            )
            _close_gaps_for_hypothesis(con, hid, "relation_promoted:relation_id=" + str(relation_id), now)
            promoted += 1
    if max_id_seen != last_id:
        _set_kv(con, STATE_TABLE, "last_promoted_graduation_event_id", max_id_seen)
    return {"promoted": promoted, "deferred_surface_evidence": deferred}


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
        relation_row = con.execute(
            "SELECT id, source, relation, target, confidence FROM relations WHERE source_hypothesis_id=?",
            (hid,),
        ).fetchone()
        if relation_row is None:
            continue
        relation_id, source, relation, target, confidence = relation_row
        con.execute("DELETE FROM relations WHERE id=?", (relation_id,))
        con.execute(
            "INSERT INTO " + EVENTS_TABLE + "(event_type,hypothesis_id,relation_id,source,relation,"
            "target,confidence,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            ("relation_retracted", hid, relation_id, source, relation, target, confidence,
             "hypothesis_revised_" + old_role + "_to_" + new_role + ":revision_id:" + str(rev_id), now),
        )
        _reopen_gaps_for_hypothesis(con, hid, "relation_retracted:revision_id=" + str(rev_id), now)
        retracted += 1
    if max_id_seen != last_id:
        _set_kv(con, STATE_TABLE, "last_processed_revision_id", max_id_seen)
    return {"retracted": retracted}


def run_relation_promotion_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_relation_promotion_disabled", "promoted": 0, "retracted": 0}
    now = _now()

    before_others = _protected_others(con)
    con.execute("SAVEPOINT stageb_relation_promotion")
    try:
        promotion_result = _promote_from_graduations(con, now)
        retraction_result = _retract_from_revisions(con, now)
        after_others = _protected_others(con)
        if after_others != before_others:
            raise RuntimeError("facts_or_questions_changed_unexpectedly")

        _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
        _set_kv(con, STATE_TABLE, "relations_promoted_total",
                _int(state.get("relations_promoted_total"), 0) + promotion_result["promoted"])
        _set_kv(con, STATE_TABLE, "relations_retracted_total",
                _int(state.get("relations_retracted_total"), 0) + retraction_result["retracted"])
        con.execute("RELEASE SAVEPOINT stageb_relation_promotion")
        con.commit()
        return {
            "status": "stageb_relation_promotion_cycle",
            "promoted": promotion_result["promoted"],
            "retracted": retraction_result["retracted"],
            "relations_total": _count(con, "relations"),
        }
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_relation_promotion")
        con.execute("RELEASE SAVEPOINT stageb_relation_promotion")
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
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else \
        {"status": "stageb_relation_promotion_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_relation_promotion_cycle(con)
    except Exception as exc:
        result = {"status": "stageb_relation_promotion_error",
                  "error": type(exc).__name__ + ":" + str(exc), "promoted": 0, "retracted": 0}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_relation_promotion_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_relation_promotion_release = True
    AutonomousLoop.no_word_blacklists = True
    return AutonomousLoop
