# -*- coding: utf-8 -*-
"""Stage-B question-chunk feedback (curiosity-directed reading).

For every open question, the reading priority and attention score of the
chunk where the underlying gap was first observed are raised, and not-yet-read
chunks that an FTS5 search finds for the question's surface text are boosted
as well. The boost scales with the question's own (dopamine/acetylcholine
modulated) priority; a global decay keeps old boosts from accumulating. This
is the path by which unresolved information gaps steer what the system reads
next.

Literatur: Loewenstein 1994; Kang et al. 2009; Modirshanechi et al. 2023
"""
from __future__ import annotations
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ki_system.text_utils import tokenize

PHASE = "stageb_question_chunk_feedback_release"
STATE_TABLE = "stageb_question_chunk_feedback_state"
EVENTS_TABLE = "stageb_question_chunk_feedback_events"

DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    "questions_processed_per_cycle": "20",
    "boost_priority_target": "0.62",
    "boost_attention_target": "0.58",
    "chunks_boosted_total": "0",
    "questions_with_no_resolvable_chunk_total": "0",
    "priority_scaling_enabled": "true",
    "priority_scaling_floor": "0.30",
    "fts_search_enabled": "true",
    "fts_max_target_chunks_per_question": "3",
    "fts_target_boost_priority": "0.50",
    "fts_target_boost_attention": "0.48",
    "fts_target_chunks_boosted_total": "0",
    "questions_with_no_fts_match_total": "0",
    "fts_min_matched_terms": "2",
    "fts_candidate_pool_size": "20",
    "global_decay_enabled": "true",
    "global_decay_factor": "0.985",
    "global_decay_floor": "0.05",
    "global_decay_rows_touched_total": "0",
}

_MARKER_RE = re.compile(r"^unresolved_(?:hypothesis|contradiction)::")
_VS_SPLIT_RE = re.compile(r"::vs::")


def _search_terms_from_question(question_text: str) -> str:
    if not question_text:
        return ""
    stripped = _MARKER_RE.sub("", question_text)
    stripped = _VS_SPLIT_RE.sub(" ", stripped)
    terms = tokenize(stripped)
    if not terms:
        return ""
    return " OR ".join(terms[:12])


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


def _json(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"repr": repr(obj)}, ensure_ascii=False)


def ensure_schema(con) -> bool:
    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    if not _table_exists(con, EVENTS_TABLE):
        con.execute(
            "CREATE TABLE " + EVENTS_TABLE + " ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER, gap_id INTEGER, "
            "hypothesis_id INTEGER, chunk_id INTEGER, before_priority REAL, after_priority REAL, "
            "reason TEXT, created_at INTEGER)"
        )
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    missing = []
    for table, required in (
        ("reading_queue", {"question_feedback_priority", "question_feedback_reason",
                            "question_feedback_question_id", "question_feedback_last_adjusted_at"}),
        ("chunk_attention_scores", {"question_feedback_score", "question_feedback_reason",
                                     "question_feedback_question_id", "question_feedback_last_adjusted_at"}),
    ):
        have = _columns(con, table)
        missing.extend(table + "." + c for c in required - have)
    if not _table_exists(con, "questions"):
        missing.append("questions")
    if not _table_exists(con, "internal_learning_gaps"):
        missing.append("internal_learning_gaps")
    if not _table_exists(con, "context_hypotheses"):
        missing.append("context_hypotheses")
    if missing:
        raise RuntimeError("stageb question chunk feedback schema missing: " + repr(missing))
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


def _anchor_chunk_for_question(con, source_gap_id: int) -> Optional[int]:
    row = con.execute(
        "SELECT hypothesis_id FROM internal_learning_gaps WHERE id=?", (source_gap_id,)
    ).fetchone()
    if row is None or row[0] is None:
        return None
    hypothesis_id = row[0]
    row2 = con.execute(
        "SELECT chunk_id FROM context_hypotheses WHERE id=?", (hypothesis_id,)
    ).fetchone()
    if row2 is None or row2[0] is None:
        return None
    return row2[0]


def _boost_chunk(con, chunk_id: int, question_id: int, gap_id: int, hypothesis_id: Optional[int],
                  priority_target: float, attention_target: float, now: int,
                  reason_suffix: str = "") -> Tuple[float, bool]:
    row = con.execute("SELECT COALESCE(priority,0) FROM reading_queue WHERE chunk_id=?", (chunk_id,)).fetchone()
    before_priority = row[0] if row else 0.0
    after_priority = max(before_priority, priority_target)
    changed = after_priority > before_priority
    reason = "question_chunk_feedback:" + reason_suffix + ":question_id=" + str(question_id) + ":gap_id=" + str(gap_id)

    con.execute(
        "INSERT INTO reading_queue(chunk_id,priority,reason,attention_score,read_count,status,last_read,"
        "updated_at,question_feedback_priority,question_feedback_reason,question_feedback_question_id,"
        "question_feedback_last_adjusted_at) VALUES(?,?,?,?,0,'pending',0,?,?,?,?,?) "
        "ON CONFLICT(chunk_id) DO UPDATE SET "
        "priority=MAX(reading_queue.priority,excluded.priority),"
        "attention_score=MAX(reading_queue.attention_score,excluded.attention_score),"
        "reason=excluded.reason,updated_at=excluded.updated_at,"
        "question_feedback_priority=excluded.question_feedback_priority,"
        "question_feedback_reason=excluded.question_feedback_reason,"
        "question_feedback_question_id=excluded.question_feedback_question_id,"
        "question_feedback_last_adjusted_at=excluded.question_feedback_last_adjusted_at",
        (chunk_id, after_priority, reason, attention_target, now,
         after_priority, reason, question_id, now),
    )
    con.execute(
        "INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,"
        "reward_score,fatigue_score,last_reason,updated_at,question_feedback_score,question_feedback_reason,"
        "question_feedback_question_id,question_feedback_last_adjusted_at) "
        "VALUES(?,?,0,0.5,0,0,?,?,?,?,?,?) "
        "ON CONFLICT(chunk_id) DO UPDATE SET "
        "attention_score=MAX(chunk_attention_scores.attention_score,excluded.attention_score),"
        "last_reason=excluded.last_reason,updated_at=excluded.updated_at,"
        "question_feedback_score=excluded.question_feedback_score,"
        "question_feedback_reason=excluded.question_feedback_reason,"
        "question_feedback_question_id=excluded.question_feedback_question_id,"
        "question_feedback_last_adjusted_at=excluded.question_feedback_last_adjusted_at",
        (chunk_id, attention_target, reason, now, attention_target, reason, question_id, now),
    )
    if changed:
        con.execute(
            "INSERT INTO " + EVENTS_TABLE + "(question_id,gap_id,hypothesis_id,chunk_id,before_priority,"
            "after_priority,reason,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (question_id, gap_id, hypothesis_id, chunk_id, before_priority, after_priority, reason, now),
        )
    return after_priority, changed


def _fts_target_chunks(con, question_text: str, exclude_chunk_id: Optional[int], max_targets: int,
                        min_matched_terms: int = 2, candidate_pool_size: int = 20) -> List[int]:
    """Searches the FULL, already-imported corpus (not just the source
    chunk) via SQLite FTS5, using the question's own verbatim, already-
    observed surface text. See module docstring, "Architecture Decision"
    and "Search-Location Dilemma" sections, for the full rationale.

    bm25() is still used ONLY to pre-select a modest candidate POOL
    (candidate_pool_size, default 20) from the full corpus via FTS5's own
    index (cheap, avoids a full-table scan), matching search.py's own
    fts_search() usage pattern exactly for that pre-selection step; final
    ranking/acceptance among that pool is then decided by the
    term-overlap count, not by bm25's own possibly-unstable magnitude.
    """
    if not _table_exists(con, "chunks_fts") or not _table_exists(con, "chunks"):
        return []
    # The result depends only on the question text and the corpus, so it is
    # cached until the corpus changes (new import -> new max chunk id).
    db_file = (con.execute("PRAGMA database_list").fetchone() or (0, "", ""))[2]
    corpus_version = con.execute("SELECT MAX(id) FROM chunks").fetchone()[0]
    cache_key = (db_file, corpus_version, question_text, exclude_chunk_id, max_targets,
                 min_matched_terms, candidate_pool_size)
    cached = _FTS_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)
    result = _fts_target_chunks_uncached(con, question_text, exclude_chunk_id, max_targets,
                                         min_matched_terms, candidate_pool_size)
    if len(_FTS_CACHE) > 4096:
        _FTS_CACHE.clear()
    _FTS_CACHE[cache_key] = tuple(result)
    return result


_FTS_CACHE: Dict[tuple, tuple] = {}


def _fts_target_chunks_uncached(con, question_text, exclude_chunk_id, max_targets,
                                min_matched_terms, candidate_pool_size) -> List[int]:
    fts_query = _search_terms_from_question(question_text)
    if not fts_query:
        return []
    query_terms = set(tokenize(_MARKER_RE.sub("", question_text) or ""))
    if not query_terms:
        return []
    try:
        pool_rows = con.execute(
            "SELECT chunks_fts.rowid AS rowid FROM chunks_fts "
            "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
            (fts_query, candidate_pool_size),
        ).fetchall()
    except Exception:
        # A malformed MATCH query (e.g. an FTS5 reserved-token collision
        # from raw tokenized text) must not abort the whole cycle -- the
        # source-chunk boost above already succeeded independently.
        return []
    pool_ids = [row[0] for row in pool_rows if row[0] != exclude_chunk_id]
    if not pool_ids:
        return []
    placeholders = ",".join("?" for _ in pool_ids)
    text_rows = con.execute(
        "SELECT id, text FROM chunks WHERE id IN (" + placeholders + ")", pool_ids
    ).fetchall()
    scored: List[Tuple[int, int]] = []
    for chunk_id, chunk_text in text_rows:
        candidate_terms = set(tokenize(chunk_text or ""))
        overlap = len(query_terms & candidate_terms)
        if overlap >= min_matched_terms:
            scored.append((chunk_id, overlap))
    scored.sort(key=lambda item: item[1], reverse=True)
    return [chunk_id for chunk_id, _overlap in scored[:max_targets]]


def _scaled_target(ceiling: float, floor: float, question_priority: float) -> float:
    factor = max(0.0, min(1.0, question_priority))
    return floor + (ceiling - floor) * factor


def _apply_global_decay(con, now: int) -> int:
    if not _table_exists(con, "reading_queue"):
        return 0
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("global_decay_enabled", "true")).strip().lower() != "true":
        return 0
    factor = max(0.0, min(1.0, _float(state.get("global_decay_factor"), 0.985)))
    floor = max(0.0, min(1.0, _float(state.get("global_decay_floor"), 0.05)))

    cur = con.execute(
        "UPDATE reading_queue SET priority=MAX(?, priority*?) "
        "WHERE updated_at IS NOT NULL AND updated_at < ? AND priority > ?",
        (floor, factor, now, floor),
    )
    rows_touched = cur.rowcount or 0
    if _table_exists(con, "chunk_attention_scores"):
        con.execute(
            "UPDATE chunk_attention_scores SET attention_score=MAX(?, attention_score*?) "
            "WHERE updated_at IS NOT NULL AND updated_at < ? AND attention_score > ?",
            (floor, factor, now, floor),
        )
    if rows_touched:
        _set_kv(con, STATE_TABLE, "global_decay_rows_touched_total",
                _int(state.get("global_decay_rows_touched_total"), 0) + rows_touched)
    return rows_touched


def run_question_chunk_feedback_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_question_chunk_feedback_disabled", "boosted": 0}
    now = _now()

    limit = max(1, _int(state.get("questions_processed_per_cycle"), 20))
    priority_target = max(0.0, min(1.0, _float(state.get("boost_priority_target"), 0.62)))
    attention_target = max(0.0, min(1.0, _float(state.get("boost_attention_target"), 0.58)))
    fts_enabled = str(state.get("fts_search_enabled", "true")).strip().lower() == "true"
    fts_max_targets = max(0, _int(state.get("fts_max_target_chunks_per_question"), 3))
    fts_priority_target = max(0.0, min(1.0, _float(state.get("fts_target_boost_priority"), 0.50)))
    fts_attention_target = max(0.0, min(1.0, _float(state.get("fts_target_boost_attention"), 0.48)))
    fts_min_matched_terms = max(1, _int(state.get("fts_min_matched_terms"), 2))
    fts_candidate_pool_size = max(1, _int(state.get("fts_candidate_pool_size"), 20))
    priority_scaling_enabled = str(state.get("priority_scaling_enabled", "true")).strip().lower() == "true"
    priority_scaling_floor = max(0.0, min(1.0, _float(state.get("priority_scaling_floor"), 0.30)))

    con.execute("SAVEPOINT stageb_question_chunk_feedback")
    try:
        rows = con.execute(
            "SELECT id, source_gap_id, question, COALESCE(priority,0.5) FROM questions "
            "WHERE status='open' AND source_gap_id IS NOT NULL "
            "ORDER BY priority DESC, id ASC LIMIT ?",
            (limit,),
        ).fetchall()

        boosted = 0
        changed_source = 0
        no_anchor = 0
        fts_boosted = 0
        changed_fts = 0
        no_fts_match = 0
        for question_id, gap_id, question_text, question_priority in rows:
            gap_row = con.execute(
                "SELECT hypothesis_id FROM internal_learning_gaps WHERE id=?", (gap_id,)
            ).fetchone()
            hypothesis_id = gap_row[0] if gap_row else None
            chunk_id = _anchor_chunk_for_question(con, gap_id)
            if chunk_id is None:
                no_anchor += 1
                continue
            if priority_scaling_enabled:
                effective_priority_target = _scaled_target(priority_target, priority_scaling_floor, question_priority)
                effective_attention_target = _scaled_target(attention_target, priority_scaling_floor, question_priority)
            else:
                effective_priority_target, effective_attention_target = priority_target, attention_target
            _after, changed = _boost_chunk(con, chunk_id, question_id, gap_id, hypothesis_id,
                                            effective_priority_target, effective_attention_target, now,
                                            reason_suffix="source_chunk")
            boosted += 1
            if changed:
                changed_source += 1

            if fts_enabled and fts_max_targets > 0:
                targets = _fts_target_chunks(con, question_text, chunk_id, fts_max_targets,
                                              min_matched_terms=fts_min_matched_terms,
                                              candidate_pool_size=fts_candidate_pool_size)
                if not targets:
                    no_fts_match += 1
                if priority_scaling_enabled:
                    effective_fts_priority_target = _scaled_target(fts_priority_target, priority_scaling_floor, question_priority)
                    effective_fts_attention_target = _scaled_target(fts_attention_target, priority_scaling_floor, question_priority)
                else:
                    effective_fts_priority_target, effective_fts_attention_target = fts_priority_target, fts_attention_target
                for target_chunk_id in targets:
                    _after_t, changed_t = _boost_chunk(
                        con, target_chunk_id, question_id, gap_id, hypothesis_id,
                        effective_fts_priority_target, effective_fts_attention_target, now,
                        reason_suffix="fts_target_chunk",
                    )
                    fts_boosted += 1
                    if changed_t:
                        changed_fts += 1

        decayed_rows = _apply_global_decay(con, now)

        _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
        _set_kv(con, STATE_TABLE, "chunks_boosted_total",
                _int(state.get("chunks_boosted_total"), 0) + boosted)
        _set_kv(con, STATE_TABLE, "questions_with_no_resolvable_chunk_total",
                _int(state.get("questions_with_no_resolvable_chunk_total"), 0) + no_anchor)
        _set_kv(con, STATE_TABLE, "fts_target_chunks_boosted_total",
                _int(state.get("fts_target_chunks_boosted_total"), 0) + fts_boosted)
        _set_kv(con, STATE_TABLE, "questions_with_no_fts_match_total",
                _int(state.get("questions_with_no_fts_match_total"), 0) + no_fts_match)
        con.execute("RELEASE SAVEPOINT stageb_question_chunk_feedback")
        con.commit()
        return {
            "status": "stageb_question_chunk_feedback_cycle",
            "questions_considered": len(rows),
            "source_chunks_boosted": boosted,
            "source_chunks_changed": changed_source,
            "no_resolvable_anchor": no_anchor,
            "fts_target_chunks_boosted": fts_boosted,
            "fts_target_chunks_changed": changed_fts,
            "questions_with_no_fts_match": no_fts_match,
            "global_decay_rows_touched": decayed_rows,
        }
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_question_chunk_feedback")
        con.execute("RELEASE SAVEPOINT stageb_question_chunk_feedback")
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
        {"status": "stageb_question_chunk_feedback_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_question_chunk_feedback_cycle(con)
    except Exception as exc:
        result = {"status": "stageb_question_chunk_feedback_error",
                  "error": type(exc).__name__ + ":" + str(exc), "boosted": 0}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_question_chunk_feedback_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_question_chunk_feedback_release = True
    return AutonomousLoop
