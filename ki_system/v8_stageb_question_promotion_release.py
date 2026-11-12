# -*- coding: utf-8 -*-
"""Stage-B question promotion (curiosity from persistent information gaps).

An internal learning gap that stays open and is reconfirmed often enough
(noradrenaline-scaled attempt threshold) becomes a durable question. The
question text is a fixed, non-linguistic marker followed by already observed
surface text; no sentence is generated. Priority is modulated by dopamine and
acetylcholine. A question is resolved when its gap closes and retracted when
its gap habituates.

Literatur: Loewenstein 1994; Golman & Loewenstein 2016
"""
from __future__ import annotations
import json
import time
from typing import Any, Dict, Optional, Tuple

PHASE = "stageb_question_promotion_release"
STATE_TABLE = "stageb_question_promotion_state"
EVENTS_TABLE = "stageb_question_promotion_events"

DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    "question_promotion_budget": "1",
    "min_resolution_attempts_for_question": "15",
    "selection_pressure_na_gain": "0.5",
    # Literatur: Golman & Loewenstein 2016
    "max_resolution_score_for_question": "0.5",
    "questions_promoted_total": "0",
    "questions_resolved_total": "0",
}

_ELIGIBLE_GAP_STATUSES = ("open", "persistent_gap")


def _now() -> int:
    return int(time.time())


def _table_exists(con, table) -> bool:
    return con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return set()
    return {row[1] for row in con.execute("PRAGMA table_info(" + table + ")").fetchall()}


def ensure_schema(con) -> bool:
    if _table_exists(con, "questions") and "source_gap_id" not in _columns(con, "questions"):
        con.execute("ALTER TABLE questions ADD COLUMN source_gap_id INTEGER")
    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    if not _table_exists(con, EVENTS_TABLE):
        con.execute(
            "CREATE TABLE " + EVENTS_TABLE + " ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, gap_id INTEGER, "
            "question_id INTEGER, question TEXT, priority REAL, "
            "reason TEXT, created_at INTEGER)"
        )
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    missing = []
    if "source_gap_id" not in _columns(con, "questions"):
        missing.append("questions.source_gap_id")
    required_gap_cols = {"gap_key", "gap_type", "role", "priority", "status",
                          "resolution_score", "resolution_attempts", "hypothesis_id",
                          "pattern_key"}
    have_gap_cols = _columns(con, "internal_learning_gaps")
    missing.extend("internal_learning_gaps." + c for c in required_gap_cols - have_gap_cols)
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if not _table_exists(con, EVENTS_TABLE):
        missing.append(EVENTS_TABLE)
    if missing:
        raise RuntimeError("stageb question promotion schema missing: " + repr(missing))
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


def _neuromodulators(con) -> Dict[str, float]:
    """Identical access pattern to v8_phase0b_relational_binding_
    observation_release.py's own _neuromodulators(): reads the same,
    already-existing Six-Core snapshot, no new messenger responsibility
    introduced."""
    defaults = {
        "dopamine": 0.5, "serotonin": 0.6, "glutamate": 0.4,
        "gaba": 0.4, "noradrenaline": 0.3, "acetylcholine": 0.5,
    }
    if not _table_exists(con, "phase6a_neuromodulated_sleep_state"):
        return defaults
    values = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    for key in tuple(defaults):
        try:
            defaults[key] = float(values.get(key, defaults[key]))
        except (TypeError, ValueError):
            pass
    return defaults


def _modulated_priority(base_priority: float, neuromod: Dict[str, float]) -> float:
    """Dopamine (already documented project-wide as the 'gap-closure
    signal') and acetylcholine (curiosity/attention signal) modulate a
    question's priority upward when currently elevated above their neutral
    baseline (0.5) -- reusing the two roles' already-established meanings,
    no new messenger responsibility introduced. Deliberately small,
    symmetric, and bounded: a fully saturated pair of messengers can at
    most raise priority by 30%, never invert or dominate the base,
    evidence-derived priority the gap already carries."""
    dopamine = neuromod.get("dopamine", 0.5)
    acetylcholine = neuromod.get("acetylcholine", 0.5)
    boost = 0.3 * (dopamine - 0.5) + 0.3 * (acetylcholine - 0.5)
    return max(0.0, min(1.0, base_priority * (1.0 + boost)))


def _hypothesis_text(con, hypothesis_id: Optional[int]) -> Optional[Tuple[str, str]]:
    if not hypothesis_id or not _table_exists(con, "context_hypotheses"):
        return None
    row = con.execute(
        "SELECT subject, text_excerpt FROM context_hypotheses WHERE id=?",
        (hypothesis_id,),
    ).fetchone()
    if row is None:
        return None
    subject, text_excerpt = row
    return (subject or "").strip(), (text_excerpt or "").strip()


def _second_contested_excerpt(con, subject: str, exclude_id: int) -> Optional[str]:
    if not subject or not _table_exists(con, "context_hypotheses"):
        return None
    from ki_system import v8_cue_competition as cue_comp
    own = con.execute("SELECT text_excerpt FROM context_hypotheses WHERE id=?", (exclude_id,)).fetchone()
    comps = cue_comp.competitors(con, subject, exclude_id, (own[0] if own else "") or "", limit=1)
    if not comps:
        return None
    return (comps[0][1] or "").strip()


def _question_text_for_gap(con, gap_type: str, hypothesis_id: Optional[int],
                            pattern_key: Optional[str]) -> Optional[str]:
    hyp = _hypothesis_text(con, hypothesis_id)
    if hyp is None:
        return None
    subject, text_excerpt = hyp
    surface = (text_excerpt or subject).strip()
    if not surface:
        return None
    if gap_type == "contested_subject_multiple_excerpts":
        second = _second_contested_excerpt(con, pattern_key or subject, hypothesis_id)
        if second and second != surface:
            return ("unresolved_contradiction::" + surface[:220] + "::vs::" + second[:220])[:500]
        return ("unresolved_contradiction::" + surface[:460])[:500]
    # Default / stalled_uncertain_hypothesis and any future gap_type this
    # module does not yet special-case: same honest, generic marker.
    return ("unresolved_hypothesis::" + surface[:480])[:500]


def _promote_from_gaps(con, now) -> Dict[str, int]:
    if not _table_exists(con, "internal_learning_gaps"):
        return {"promoted": 0}
    state = _read_kv(con, STATE_TABLE)
    budget = max(0, _int(state.get("question_promotion_budget"), 1))
    if budget <= 0:
        return {"promoted": 0}
    base_min_attempts = max(1, _int(state.get("min_resolution_attempts_for_question"), 15))
    max_resolution = _float(state.get("max_resolution_score_for_question"), 0.5)
    neuromod = _neuromodulators(con)
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    min_attempts = max(1, round(base_min_attempts * (1.0 + na_gain * (0.5 - neuromod["noradrenaline"]))))

    status_list = ",".join("'" + s + "'" for s in _ELIGIBLE_GAP_STATUSES)
    rows = con.execute(
        "SELECT id, gap_key, gap_type, role, priority, hypothesis_id, pattern_key "
        "FROM internal_learning_gaps "
        "WHERE status IN (" + status_list + ") "
        "AND COALESCE(resolution_attempts,0)>=? AND COALESCE(resolution_score,0)<=? "
        "AND id NOT IN (SELECT COALESCE(source_gap_id,-1) FROM questions) "
        "ORDER BY priority DESC, id ASC LIMIT ?",
        (min_attempts, max_resolution, budget),
    ).fetchall()

    promoted = 0
    for gap_id, gap_key, gap_type, role, priority, hypothesis_id, pattern_key in rows:
        question_text = _question_text_for_gap(con, gap_type or "", hypothesis_id, pattern_key)
        if not question_text:
            continue
        final_priority = _modulated_priority(_float(priority, 0.5), neuromod)
        cur = con.execute(
            "INSERT OR IGNORE INTO questions(question,priority,status,created_at,updated_at,"
            "source_gap_id) VALUES(?,?,?,?,?,?)",
            (question_text, final_priority, "open", now, now, gap_id),
        )
        if cur.rowcount:
            question_id = cur.lastrowid
            con.execute(
                "INSERT INTO " + EVENTS_TABLE + "(event_type,gap_id,question_id,question,priority,"
                "reason,created_at) VALUES(?,?,?,?,?,?,?)",
                ("question_promoted", gap_id, question_id, question_text, final_priority,
                 "persistent_gap_reconfirmed_" + str(min_attempts) + "_times:gap_key:" + str(gap_key), now),
            )
            promoted += 1
    return {"promoted": promoted}


def _retract_resolved_gaps(con, now) -> Dict[str, int]:
    if not _table_exists(con, "questions"):
        return {"resolved": 0}
    status_list = ",".join("'" + s + "'" for s in _ELIGIBLE_GAP_STATUSES)
    rows = con.execute(
        "SELECT q.id, q.source_gap_id, g.status FROM questions q "
        "LEFT JOIN internal_learning_gaps g ON g.id=q.source_gap_id "
        "WHERE q.status='open' AND q.source_gap_id IS NOT NULL "
        "AND (g.id IS NULL OR g.status NOT IN (" + status_list + "))"
    ).fetchall()
    resolved = 0
    for question_id, gap_id, gap_status in rows:
        con.execute(
            "UPDATE questions SET status=?, updated_at=? WHERE id=?",
            ("resolved", now, question_id),
        )
        con.execute(
            "INSERT INTO " + EVENTS_TABLE + "(event_type,gap_id,question_id,question,priority,"
            "reason,created_at) VALUES(?,?,?,?,?,?,?)",
            ("question_resolved", gap_id, question_id, None, None,
             "source_gap_closed_or_removed:status=" + str(gap_status), now),
        )
        resolved += 1
    return {"resolved": resolved}


def run_question_promotion_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_question_promotion_disabled", "promoted": 0, "resolved": 0}
    now = _now()

    con.execute("SAVEPOINT stageb_question_promotion")
    try:
        promotion_result = _promote_from_gaps(con, now)
        resolution_result = _retract_resolved_gaps(con, now)

        _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
        _set_kv(con, STATE_TABLE, "questions_promoted_total",
                _int(state.get("questions_promoted_total"), 0) + promotion_result["promoted"])
        _set_kv(con, STATE_TABLE, "questions_resolved_total",
                _int(state.get("questions_resolved_total"), 0) + resolution_result["resolved"])
        con.execute("RELEASE SAVEPOINT stageb_question_promotion")
        con.commit()
        return {
            "status": "stageb_question_promotion_cycle",
            "promoted": promotion_result["promoted"],
            "resolved": resolution_result["resolved"],
            "questions_total": con.execute("SELECT COUNT(*) FROM questions").fetchone()[0],
        }
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_question_promotion")
        con.execute("RELEASE SAVEPOINT stageb_question_promotion")
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
        {"status": "stageb_question_promotion_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_question_promotion_cycle(con)
    except Exception as exc:
        result = {"status": "stageb_question_promotion_error",
                  "error": type(exc).__name__ + ":" + str(exc), "promoted": 0, "resolved": 0}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_question_promotion_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_question_promotion_release = True
    return AutonomousLoop
