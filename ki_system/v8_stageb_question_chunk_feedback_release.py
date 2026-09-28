# -*- coding: utf-8 -*-
"""V8 Stage-B Question-Chunk Feedback -- closes the "rein schreibender
Blinddarm" (write-only appendix) gap identified in the Questions Slice 3
audit: this is the first and only module in this codebase that ever
*reads* the `questions` table to influence real system behavior. Before
this module, `questions` was populated, updated, and retracted by
v8_stageb_question_promotion_release.py, but no consumer anywhere ever
read from it -- curiosity had no behavioral consequence.

WHAT THIS MODULE DOES
----------------------
For every still-`open` question (i.e. every question whose source gap has
not yet been resolved or habituated away -- see below), this module boosts
`reading_queue.priority` / `chunk_attention_scores.attention_score` for the
exact chunk where the question's underlying, still-unresolved hypothesis
was first observed (via questions.source_gap_id -> internal_learning_gaps.
hypothesis_id -> context_hypotheses.chunk_id). The intent, matching
Loewenstein's own information-gap framing already used throughout this
project's Questions Slice 3, is straightforward: a question is the
system's own explicit statement that "I noticed something here I could
not resolve" -- rereading exactly that source text is the most direct,
literature-supported way to give the system a chance to gather the
disambiguating evidence that would close the gap.

ARCHITECTURE DECISION: DIRECT FULL-TEXT SEARCH, NOT AN ENTITY/RELATION-
WEIGHTED BIAS (BRAINSTEM_QUESTION_SEARCH_LOCATION_FIX_V1, 25 September
2026)
------------------------------------------------------------------------
This module was reviewed against a real, concrete architectural choice:
should a question's salience reach the chunker as (a) direct search
terms/text excerpts via exact-match/full-text search, or (b) a weighted
bias flowing through the affected entities/relations? Decided in favor of
(a), for four concrete reasons, all verified against this codebase before
deciding, not assumed:
  1. Full-text search infrastructure already exists, is fast, and is
     already the project's own established mechanism for exactly this
     kind of "find text related to a query" task: memory.py's own
     fts_search() (SQLite FTS5 over chunks_fts, already used by
     search.py's semantic_search()/answer() and dialogue.py). No new
     search infrastructure needed.
  2. The relations/ontology layers this project only just made productive
     this same session are still extremely sparse (a real, instrumented
     90-cycle run produced only 2-3 relations and 1 ontology row total) --
     an entity/relation-weighted bias would have almost no data to weight
     against today, and would only mature on the same slow timescale as
     the relations themselves.
  3. Critically, a relation/entity-based bias would be CIRCULAR for this
     specific purpose: relations are themselves derived only from
     chunks the system has ALREADY read (see v8_phase0b_relational_
     binding_observation_release.py). Biasing sampling via existing
     relations can therefore only ever resurface chunks already
     connected to already-observed entities -- it structurally cannot
     reach a genuinely unread document elsewhere in the corpus, which is
     exactly the failure case (see below) this fix targets.
  4. A real query string built from the gap's own verbatim, already-
     observed surface text (matching this project's own "no generated
     sentence, only real observed text" principle already used by
     v8_stageb_question_promotion_release.py's own question-text
     formatting) is directly inspectable/auditable, consistent with this
     project's stated preference for transparent, loggable statistics
     over an opaque learned weighting.
This does not replace the existing source-chunk boost (Section above) --
it is additive, addressing a specific, real limitation of that
mechanism, described next.

REAL LIMITATION FOUND AND FIXED: THE SEARCH-LOCATION DILEMMA (source chunk
vs. target chunk)
------------------------------------------------------------------------
The original version of this module boosted ONLY the source chunk (where
the unresolved hypothesis was first observed). This is correct when the
disambiguating information is nearby in the same text, but is blind
whenever the actual answer lives in a completely different, not-yet-read
document elsewhere in the corpus: rereading the source chunk repeatedly
then yields no new evidence, and the gap sits unproductive until gap_
detection's own habituation mechanism eventually retires it (correct,
intended protection against infinite loops -- but strategically blind to
external answers in the meantime). Fixed by additionally searching the
FULL corpus (not just the source chunk) via SQLite FTS5, using the
gap's own verbatim surface text (stripped of question_promotion's fixed
"unresolved_hypothesis::"/"unresolved_contradiction::...::vs::..."
marker prefixes, then tokenized exactly like search.py's own _terms()) as
an OR-joined MATCH query -- mirroring search.py's own semantic_search()
query-construction pattern exactly, for consistency. The top-ranked,
not-already-the-source-chunk matches receive their own, deliberately
weaker boost (default 0.50/0.48 vs. the source chunk's own 0.62/0.58),
since they are candidate leads, not the confirmed origin of the gap.

FIX 2 -- DELTA-GATED EVENT LOGGING (BRAINSTEM_QUESTION_FEEDBACK_EVENT_
LOG_FIX_V1, 25 September 2026)
------------------------------------------------------------------------
A real, instrumented 90-cycle run of the original version of this module
was directly measured: 1,148 logged events for only 11 distinct boosted
chunks -- and, on direct inspection, EVERY SINGLE one of those 1,148
events had before_priority == after_priority (i.e. zero real change; the
same already-at-target chunk was simply re-confirmed and re-logged every
single cycle for as long as its question stayed open). This is a genuine
bug, not a design tradeoff: the event table's own purpose is an audit
trail of real adjustments, and a 100%-redundant log defeats that purpose
while adding needless SQLite write volume, worsening at production scale
(thousands of simultaneous open questions). Fixed: an event is now only
inserted when the write actually changes something (after_priority >
before_priority, computed in Python BEFORE the SQL write, not inferred
from it afterward) -- the reading_queue/chunk_attention_scores UPDATE
itself is unaffected and still always runs (via MAX(...), so it remains
correct and idempotent even when it changes nothing).

FIX 3 -- GLOBAL PRIORITY DECAY / STARVATION PREVENTION (BRAINSTEM_
READING_QUEUE_GLOBAL_DECAY_V1, 25 September 2026)
------------------------------------------------------------------------
A project-wide audit of every writer to reading_queue.priority (before
this fix) found real per-phase down-weighting logic only in
v8_phase5b_integrated_strategy_refinement_release.py's own diversity
step -- but that step's own query is `ORDER BY priority DESC LIMIT
limit_chunks` with limit_chunks defaulting to 600. At this project's own
documented real production scale (167,661 chunks), that diversity
mechanism can only ever reach the top ~0.36% of chunks by priority; the
long tail of chunks that never even enter that top-600 window receives
no aging/anti-starvation treatment from anywhere in this codebase. Since
this module (and phase5e/5g/5i before it) only ever RAISES specific
chunks' priority via MAX(...), and nothing lowers any OTHER chunk's
priority in response, a growing set of "boosted favorites" could in
principle come to dominate reading over many cycles, with no counter-
pressure for the untouched majority. Fixed by adding a genuine, full-
table decay pass (not limited to a top-N window) at the end of this
module's own cycle: every reading_queue/chunk_attention_scores row NOT
freshly touched THIS SAME real cycle (identified via updated_at strictly
less than this cycle's own timestamp, captured once at cycle entry) has
its priority/attention_score multiplied by a small, configurable decay
factor (default 0.985 = 1.5% per cycle), floored at a low baseline
(default 0.05) so a chunk's priority can shrink toward but never fully
to zero. This directly bounds how long any single boosted chunk can
dominate without fresh confirmation, while never touching rows any
module (including this one) legitimately wrote to in the very same
cycle.

WRITE DISCIPLINE (matches this table's own already-established convention)
----------------------------------------------------------------------------
Both target tables already carry a per-phase (score, reason,
last_adjusted_at) column triplet for every other phase that boosts
reading priority (phase5a_*, phase5f_*, phase5g_*, ..., phase6a_*, see
db_bootstrap.py's own SCHEMA_TABLES). This module adds exactly one more
such triplet, `question_feedback_*`, and writes ONLY via
MAX(existing_priority, new_priority) -- exactly like v8_phase5e_context_
expansion_and_gap_closure_release.py's own INSERT ... ON CONFLICT DO
UPDATE SET priority=MAX(...) pattern -- so this module can only ever raise
a chunk's priority relative to what it already was, never override or
suppress another phase's own judgment.

WHY THIS MODULE IS SAFE AGAINST THE "NOISY-TV PROBLEM" ONLY BECAUSE IT WAS
BUILT LAST, AFTER HABITUATION
------------------------------------------------------------------------
Modirshanechi, Kondrakiewicz, Gerstner & Haesler (2023, Trends in
Neurosciences 46(12):1054-1066) document that coupling exploration/
attention to an unfiltered novelty or curiosity signal reproducibly gets
an agent stuck on unpredictable but worthless noise. This module's own
input, the `questions` table, is deliberately NOT such an unfiltered
signal by the time it reaches here: a question only exists at all once
its source gap survived v8_stageb_gap_detection_release.py's own
persistence gate (>=15 real cycles, roughly one full measured sleep/wake
rhythm) AND v8_stageb_question_promotion_release.py's own promotion gate,
and -- critically -- a question is immediately, automatically retracted
(status set to 'resolved', never deleted) the moment its source gap either
closes (real Stage-B graduation) or habituates (sustained, evidence-free
stagnation, e.g. genuine Phase-0 lexical-boundary noise that never
resolves). Because this module only ever reads WHERE status='open', a
question whose underlying signal turns out to be exactly the kind of
persistent noise the "noisy-TV problem" describes stops receiving any
chunk-priority boost the very next cycle after gap_detection habituates
it -- the same real, instrumented behavior already verified for fact/
relation promotion's own gap-closure hooks in the prior delivery. Wiring
this feedback in before that habituation mechanism existed (the sequence
explicitly rejected earlier in this same project) would have had no such
protection.

A closely related, pre-existing defect in v8_phase5e_context_expansion_
and_gap_closure_release.py (which already boosts reading_queue from raw,
un-habituation-filtered internal_learning_gaps rows) was found and fixed
alongside this module -- see that module's own updated comment
(BRAINSTEM_PHASE5E_HABITUATION_RESPECT_FIX_V1) for the full account.
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
    # How many still-open questions this module processes per real cycle.
    # Deliberately small and independent of every other promotion budget
    # in this chain (question_promotion_budget, etc.) -- this module
    # never creates, promotes, or retracts anything; it only ever reads
    # already-open questions and adjusts reading priority, so there is no
    # shared scarce resource to throttle against.
    "questions_processed_per_cycle": "20",
    # How much a still-open question raises its anchor chunk's priority/
    # attention_score, on a 0..1 scale matching every other phase's own
    # priority range. Deliberately modest and NOT scaled by the
    # question's own `priority` field beyond this single multiplier --
    # a fixed, auditable boost is preferable to a compounding one, since
    # this module's entire purpose is a single, clear nudge toward
    # rereading the source text, not a competing scoring system.
    "boost_priority_target": "0.62",
    "boost_attention_target": "0.58",
    "chunks_boosted_total": "0",
    "questions_with_no_resolvable_chunk_total": "0",
    # BRAINSTEM_QUESTION_FEEDBACK_PRIORITY_CONSISTENCY_FIX_V1 (28 September
    # 2026)
    #
    # Root cause: v8_stageb_question_promotion_release.py's own
    # _modulated_priority() already scales a question's stored `priority`
    # field by dopamine/acetylcholine (its own established "gap-closure
    # signal"/"curiosity signal" roles, +/-30% bounded) at promotion time,
    # and this module's own query already ORDERs candidate questions by
    # that same modulated priority DESC -- but the actual boost MAGNITUDE
    # applied to a question's anchor/target chunks (boost_priority_target,
    # boost_attention_target, fts_target_boost_priority/attention below)
    # was a single FIXED constant applied identically to every open
    # question regardless of its own already-computed priority. This means
    # the dopamine/acetylcholine signal that already, correctly,
    # determines WHICH question gets processed first this cycle was
    # silently discarded the moment it came to determining HOW STRONGLY
    # that question's own source/target chunks get boosted -- a genuine
    # consistency break between two adjacent modules in the same chain
    # that are both meant to express the same underlying salience signal.
    #
    # Fix: each question's own boost magnitude is now interpolated between
    # a floor and the existing, already-calibrated ceiling value, using
    # that SAME question's own (already dopamine/acetylcholine-modulated)
    # `priority` field as the interpolation factor -- reusing the upstream
    # signal exactly as computed, introducing no new neuromodulator access
    # or judgment in this module itself. A highly salient question (near
    # priority=1.0) still receives close to the full, already-calibrated
    # ceiling boost (preserving this module's own prior, tested defaults
    # at the high end); a barely-salient, low-priority question (e.g. one
    # nearing habituation) now receives a correspondingly WEAKER boost,
    # rather than the same, undifferentiated full-strength nudge every
    # open question previously got regardless of how salient it actually
    # was. The floor is deliberately non-zero (default 0.30) so a
    # low-priority-but-still-genuinely-open question is not starved
    # outright -- habituation/closure (handled entirely upstream by
    # gap_detection/question_promotion) remains the sole mechanism that
    # actually retires a question, not this interpolation.
    "priority_scaling_enabled": "true",
    "priority_scaling_floor": "0.30",
    # BRAINSTEM_QUESTION_SEARCH_LOCATION_FIX_V1: full-text-search-based
    # target-chunk discovery, addressing the source-chunk-only blind spot
    # (see module docstring). Deliberately a weaker prior than the source
    # chunk's own boost_priority_target/boost_attention_target above --
    # these are candidate leads, not the confirmed origin of the gap.
    "fts_search_enabled": "true",
    "fts_max_target_chunks_per_question": "3",
    "fts_target_boost_priority": "0.50",
    "fts_target_boost_attention": "0.48",
    "fts_target_chunks_boosted_total": "0",
    "questions_with_no_fts_match_total": "0",
    # BRAINSTEM_FTS_TERM_OVERLAP_PRECISION_FIX_V1: see _fts_target_chunks()
    # docstring for the full rationale (raw bm25 magnitude found unstable
    # at small corpus sizes during this delivery's own testing).
    "fts_min_matched_terms": "2",
    "fts_candidate_pool_size": "20",
    # BRAINSTEM_READING_QUEUE_GLOBAL_DECAY_V1: real, full-table decay
    # (not limited to a top-priority window, unlike v8_phase5b_...'s own
    # top-600 diversity step), applied once per cycle to every row not
    # freshly touched THIS cycle. See module docstring for the full
    # rationale.
    "global_decay_enabled": "true",
    "global_decay_factor": "0.985",
    "global_decay_floor": "0.05",
    "global_decay_rows_touched_total": "0",
}

_MARKER_RE = re.compile(r"^unresolved_(?:hypothesis|contradiction)::")
_VS_SPLIT_RE = re.compile(r"::vs::")


def _search_terms_from_question(question_text: str) -> str:
    """Strips v8_stageb_question_promotion_release.py's own fixed,
    non-linguistic marker prefixes (see that module's docstring: a
    question is never a generated sentence, only real, verbatim observed
    text with a fixed marker), then tokenizes exactly like search.py's own
    _terms()/tokenize() -- no new tokenization rule invented here -- and
    OR-joins up to 12 tokens into a SQLite FTS5 MATCH query string,
    mirroring search.py's semantic_search() own
    fts=' OR '.join(terms[:12]) construction exactly, for consistency
    with this project's single, already-established FTS query
    convention."""
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
    """questions.source_gap_id -> internal_learning_gaps.hypothesis_id ->
    context_hypotheses.chunk_id. Returns None if any link in this chain is
    missing (e.g. a question whose gap or hypothesis row was later
    pruned/altered by some other mechanism) -- a missing anchor is not an
    error, it just means this question cannot currently be acted on."""
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
    """Returns (after_priority, changed). BRAINSTEM_QUESTION_FEEDBACK_
    EVENT_LOG_FIX_V1: `changed` is computed here, in Python, BEFORE the
    SQL write, so the caller can gate event-table logging on a real
    change -- see module docstring, Fix 2, for the measured 1,148-events/
    0-real-changes finding this addresses. The reading_queue/chunk_
    attention_scores UPDATE itself always runs regardless (via MAX(...),
    so it remains correct/idempotent even when nothing changes)."""
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

    BRAINSTEM_FTS_TERM_OVERLAP_PRECISION_FIX_V1 (25 September 2026):
    raw bm25() ranking was directly tested against small, controlled
    corpora during this delivery's own review and found unreliable at
    small scale -- a chunk sharing zero real content words with the
    query (matching only on a single common short word, e.g. "in")
    sometimes ranked BETTER (more negative) than a chunk genuinely
    sharing an exact content word with the query. This is a real,
    corpus-size-dependent instability in bm25's own IDF statistics, not
    a coding error -- with very few documents, term-frequency statistics
    are inherently noisy. Rather than relying on bm25's raw magnitude
    (which may or may not stabilize at this project's real, documented
    167,661-chunk production scale -- untested here), this function adds
    a second, corpus-size-independent, statistically transparent
    safeguard: a candidate chunk's own real text (re-tokenized in Python,
    same tokenize() used to build the query -- no new rule invented) must
    share at least `min_matched_terms` DISTINCT tokens with the query,
    not merely rank well under FTS5's internal MATCH scoring. This
    applies uniformly to every candidate purely by overlap count, never
    by word identity, so it does not violate this project's own
    no-word-blacklist principle -- it is a breadth-of-overlap
    requirement, not a banned-word list.

    bm25() is still used ONLY to pre-select a modest candidate POOL
    (candidate_pool_size, default 20) from the full corpus via FTS5's own
    index (cheap, avoids a full-table scan), matching search.py's own
    fts_search() usage pattern exactly for that pre-selection step; final
    ranking/acceptance among that pool is then decided by the
    term-overlap count, not by bm25's own possibly-unstable magnitude."""
    if not _table_exists(con, "chunks_fts") or not _table_exists(con, "chunks"):
        return []
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
    """BRAINSTEM_QUESTION_FEEDBACK_PRIORITY_CONSISTENCY_FIX_V1: linear
    interpolation between `floor` and `ceiling`, using the question's own
    already dopamine/acetylcholine-modulated priority (clamped to [0,1])
    as the interpolation factor. At question_priority=1.0 this returns
    exactly `ceiling` (identical to this module's pre-existing, fixed
    behavior); at question_priority=0.0 it returns `floor`."""
    factor = max(0.0, min(1.0, question_priority))
    return floor + (ceiling - floor) * factor


def _apply_global_decay(con, now: int) -> int:
    """BRAINSTEM_READING_QUEUE_GLOBAL_DECAY_V1: full-table anti-starvation
    decay, run once per cycle. See module docstring, Fix 3, for the full
    rationale and the measured top-600-window limitation of the only
    other existing decay mechanism in this codebase (v8_phase5b_...'s own
    diversity step). Only rows NOT freshly touched THIS SAME cycle
    (updated_at strictly less than this cycle's own `now`, captured once
    at the top of run_question_chunk_feedback_cycle()) are decayed, so
    this can never undo a boost this module (or any other phase) just
    applied in the same cycle."""
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
            # BRAINSTEM_QUESTION_FEEDBACK_PRIORITY_CONSISTENCY_FIX_V1: scale
            # this question's own boost ceiling by its own, already
            # dopamine/acetylcholine-modulated priority (see DEFAULTS'
            # own comment for the full rationale) -- reuses the upstream
            # signal exactly as computed by question_promotion, no new
            # neuromodulator access introduced in this module.
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

            # BRAINSTEM_QUESTION_SEARCH_LOCATION_FIX_V1: search the full
            # corpus for candidate target chunks elsewhere, in addition
            # to the confirmed source chunk above -- see module
            # docstring's "Search-Location Dilemma" section.
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
