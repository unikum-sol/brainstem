# -*- coding: utf-8 -*-
"""V8 Phase 0 -- Autonomous Lexical Boundary Observation.

THE SEGMENTATION SIGNAL (the only one used, chosen to satisfy the explicit
"no linguistic priors, start from the raw unbroken character stream"
requirement): local branching entropy. For a short preceding character
context (default: the last 3 characters), this module maintains a running,
purely statistical count of which character has historically followed that
exact context, across every chunk already read. The Shannon entropy of that
distribution is a direct, quantitative generalization of the transitional-
probability statistic that has been shown, in real infant-language-
acquisition research, to allow segmentation of a continuous, unbroken
speech stream into recurring word-like units from statistics alone -- see
Saffran, Aslin & Newport (1996, Science); Aslin, Saffran & Newport (1998,
Psychological Science); Flo, Benjamin, Palu & Dehaene-Lambertz (2022,
Scientific Reports, showing the same mechanism operating in sleeping,
full-term neonates). A closely related, already-published, fully
unsupervised algorithm (branching entropy + minimum description length;
Zhikov, Takamura & Okumura) demonstrates this exact statistic is usable for
real, rule-free word segmentation without any dictionary or grammar.
"""
from __future__ import annotations
import hashlib
import math
import re
import time

from ki_system.db_bootstrap import ensure_schema_for

PHASE = "phase0_lexical_boundary_observation_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

STATE_TABLE = "phase0_lexical_state"
TRANSITIONS_TABLE = "lexical_context_transitions"
UNITS_TABLE = "lexical_units"

DEFAULTS = {
    "enabled": "true",
    "context_length": "3",
    "min_observations": "8",
    # Minimum branching entropy (bits) for a position to be proposed as a
    # boundary candidate.
    "entropy_threshold_bits": "1.0",
    "chunk_batch_size": "8",
    # Matches Phase 1's own _sentences() text-length cap for the same
    # source chunks.
    "chunk_text_limit": "3000",
    # Phase 0's OWN rotating cursor over chunks.id. Deliberately NOT
    # coupled to reading_queue/Phase 1's own bookkeeping in any way, so
    # Phase 0 can never interfere with Phase 1's state or vice versa.
    "cursor_chunk_id": "0",
    "cycle_count": "0",
    "boundaries_created_total": "0",
    "boundaries_reobserved_total": "0",
    # Safety cap: maximum number of new-or-reobserved boundary candidates
    # recorded per single chunk, to bound worst-case per-cycle write volume
    # against a pathological chunk.
    "max_candidates_per_chunk": "64",
}

_WS_RE = re.compile(r"\s+")


def _now():
    return int(time.time())


def _norm(value, limit):
    return _WS_RE.sub(" ", (value or "").replace("\x00", " ")).strip()[:limit]


def _table_exists(con, table):
    return con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _index_exists(con, name):
    return con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return set()
    return {row[1] for row in con.execute("PRAGMA table_info(" + table + ")").fetchall()}


def ensure_schema(con):
    # Central authority first (adds context_hypotheses.lexical_offset if
    # missing, and anything else central bootstrap owns) -- mirrors the
    # exact pattern already used by every other phase module in this
    # codebase (e.g. v8_context_observation_learning_release.ensure_schema).
    ensure_schema_for(con)

    try:
        con.execute("PRAGMA wal_autocheckpoint=8000")
    except Exception:
        pass

    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    if not _table_exists(con, TRANSITIONS_TABLE):
        con.execute(
            "CREATE TABLE " + TRANSITIONS_TABLE + " ("
            "context TEXT NOT NULL, next_char TEXT NOT NULL, count INTEGER DEFAULT 0, "
            "PRIMARY KEY(context, next_char))"
        )
    if not _table_exists(con, UNITS_TABLE):
        con.execute(
            "CREATE TABLE " + UNITS_TABLE + " ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, surface_form TEXT, chunk_id INTEGER, "
            "start_offset INTEGER, end_offset INTEGER, "
            "left_boundary_hypothesis_id INTEGER, right_boundary_hypothesis_id INTEGER, "
            "first_seen_at INTEGER, last_seen_at INTEGER, observation_count INTEGER DEFAULT 1, "
            "status TEXT DEFAULT 'candidate', created_at INTEGER, updated_at INTEGER, "
            "UNIQUE(chunk_id, start_offset, end_offset))"
        )
    if not _index_exists(con, "idx_lexical_context_transitions_context_covering"):
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_lexical_context_transitions_context_covering "
            "ON " + TRANSITIONS_TABLE + "(context, next_char, count)"
        )
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    return _self_check_schema(con)


def _self_check_schema(con):
    missing = []
    for table in (STATE_TABLE, TRANSITIONS_TABLE, UNITS_TABLE):
        if not _table_exists(con, table):
            missing.append(table)
    if "lexical_offset" not in _columns(con, "context_hypotheses"):
        missing.append("context_hypotheses.lexical_offset")
    if missing:
        raise RuntimeError("phase0 lexical schema missing: " + repr(missing))
    return True


def _read_kv(con, table):
    if not _table_exists(con, table):
        return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())


def _set_kv(con, table, key, value):
    con.execute(
        "INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
        (key, str(value), _now()),
    )


def _int(v, d=0):
    try:
        return int(float(v))
    except Exception:
        return d


def _float(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _entropy_bits(counts):
    total = sum(counts)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


def _next_chunk_batch(con, cursor_id, batch_size):
    """Phase 0's OWN, independent rotating cursor over chunks.id --
    deliberately NOT coupled to reading_queue/Phase 1's own bookkeeping, so
    Phase 0 can never interfere with Phase 1's state, and vice versa."""
    rows = con.execute(
        "SELECT id, text FROM chunks WHERE id>? ORDER BY id ASC LIMIT ?",
        (cursor_id, batch_size),
    ).fetchall()
    if not rows:
        rows = con.execute(
            "SELECT id, text FROM chunks ORDER BY id ASC LIMIT ?",
            (batch_size,),
        ).fetchall()
    return rows


def _fetch_context_counts(con, contexts):
    result = {}
    contexts = [c for c in contexts if c]
    if not contexts:
        return result
    placeholders = ",".join("?" for _ in contexts)
    rows = con.execute(
        "SELECT context, next_char, count FROM " + TRANSITIONS_TABLE +
        " WHERE context IN (" + placeholders + ")",
        contexts,
    ).fetchall()
    for context, next_char, count in rows:
        result.setdefault(context, {})[next_char] = count
    return result


def _signature_for_boundary(text, position, k):
    """A boundary hypothesis's identity is the small, LOCAL character
    window around it (k characters before + k characters after) -- NOT the
    whole chunk and NOT a numeric offset. This is what makes the SAME
    recurring local pattern re-observable (evidence_count growth) across
    many different chunks, mirroring exactly how Phase 1 already
    re-observes an identical whole sentence verbatim."""
    left = text[max(0, position - k):position]
    right = text[position:position + k]
    # U+2758 (LIGHT VERTICAL BAR) as an unambiguous separator unlikely to
    # collide with ordinary running text, purely for signature construction
    # (never shown to the user, never interpreted linguistically).
    return left + "\u2758" + right


def observe_lexical_boundaries(con, neuromodulators):
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "phase0_disabled", "candidates_created": 0, "candidates_reobserved": 0}

    k = max(1, _int(state.get("context_length"), 3))
    min_obs = max(1, _int(state.get("min_observations"), 8))
    threshold = _float(state.get("entropy_threshold_bits"), 1.0)
    batch_size = max(1, _int(state.get("chunk_batch_size"), 8))
    text_limit = max(100, _int(state.get("chunk_text_limit"), 3000))
    cursor = _int(state.get("cursor_chunk_id"), 0)
    max_per_chunk = max(1, _int(state.get("max_candidates_per_chunk"), 64))

    batch = _next_chunk_batch(con, cursor, batch_size)
    if not batch:
        return {"status": "phase0_no_chunks", "candidates_created": 0, "candidates_reobserved": 0}

    created = 0
    reobserved = 0
    total_candidates = 0
    now = _now()
    last_id = cursor

    pending_transition_updates = {}

    for chunk_id, raw_text in batch:
        last_id = chunk_id
        text = _norm(raw_text, text_limit)
        if len(text) <= k:
            continue

        distinct_contexts = {text[i - k:i] for i in range(k, len(text))}
        historical = _fetch_context_counts(con, distinct_contexts)
        for (ctx, nc), cnt in pending_transition_updates.items():
            if ctx in distinct_contexts:
                historical.setdefault(ctx, {})
                historical[ctx][nc] = historical[ctx].get(nc, 0) + cnt

        candidate_positions = []
        for i in range(k, len(text)):
            context = text[i - k:i]
            dist = historical.get(context)
            if not dist:
                continue
            total = sum(dist.values())
            if total < min_obs:
                continue
            h = _entropy_bits(dist.values())
            if h >= threshold:
                candidate_positions.append(i)

        for i in candidate_positions[:max_per_chunk]:
            sig_text = _signature_for_boundary(text, i, k)
            signature = hashlib.sha1(
                ("lexical_boundary|" + sig_text).encode("utf-8", "ignore")
            ).hexdigest()
            existing = con.execute(
                "SELECT id, evidence_count FROM context_hypotheses WHERE signature=? LIMIT 1",
                (signature,),
            ).fetchone()
            if existing:
                hid, ev = existing
                new_evidence_count = int(ev or 1) + 1
                new_confidence = 1.0 - (1.0 / (1.0 + new_evidence_count))
                new_uncertainty = 1.0 / (1.0 + new_evidence_count)
                con.execute(
                    "UPDATE context_hypotheses SET evidence_count=?, confidence=?, uncertainty=?, updated_at=? WHERE id=?",
                    (new_evidence_count, new_confidence, new_uncertainty, now, hid),
                )
                reobserved += 1
            else:
                con.execute(
                    "INSERT INTO context_hypotheses(chunk_id,role,subject,relation_hint,object,"
                    "text_excerpt,source_title,confidence,uncertainty,status,dopamine,serotonin,"
                    "glutamate,gaba,noradrenaline,acetylcholine,signature,evidence_count,"
                    "created_at,updated_at,lexical_offset) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        chunk_id, "uncertain_lexical_boundary", sig_text[:180], "", "",
                        sig_text, "", 0.0, 1.0, "active",
                        neuromodulators["dopamine"], neuromodulators["serotonin"],
                        neuromodulators["glutamate"], neuromodulators["gaba"],
                        neuromodulators["noradrenaline"], neuromodulators["acetylcholine"],
                        signature, 1, now, now, i,
                    ),
                )
                created += 1
            total_candidates += 1

        for i in range(k, len(text)):
            context = text[i - k:i]
            next_char = text[i]
            key = (context, next_char)
            pending_transition_updates[key] = pending_transition_updates.get(key, 0) + 1

    if pending_transition_updates:
        con.executemany(
            "INSERT INTO " + TRANSITIONS_TABLE + "(context,next_char,count) VALUES(?,?,?) "
            "ON CONFLICT(context,next_char) DO UPDATE SET count=count+excluded.count",
            [(c, n, cnt) for (c, n), cnt in pending_transition_updates.items()],
        )

    _set_kv(con, STATE_TABLE, "cursor_chunk_id", last_id)
    _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
    _set_kv(con, STATE_TABLE, "boundaries_created_total", _int(state.get("boundaries_created_total"), 0) + created)
    _set_kv(con, STATE_TABLE, "boundaries_reobserved_total", _int(state.get("boundaries_reobserved_total"), 0) + reobserved)
    con.commit()

    return {
        "status": "phase0_lexical_observation_cycle",
        "chunks_processed": len(batch),
        "candidates_created": created,
        "candidates_reobserved": reobserved,
        "candidates_total": total_candidates,
    }


def _derive_lexical_units(con):
    """Maintenance pass: for every context_hypotheses row with
    role='stable_lexical_boundary' (i.e. already guarded-graduated by
    Stage-B, exactly like any other hypothesis), attempt to pair it with
    the adjacent, ALSO-stable boundary within the same first-seen chunk to
    derive a lexical_units row. This is a pure, idempotent, read-mostly
    derivation from already-graduated boundary hypotheses -- it introduces
    NO new regulation or consolidation mechanism of its own, and performs
    no schema/behavior change to Phase 7d or Stage-B.

    Scoping note (deliberate, documented limitation): because a
    context_hypotheses row only ever records its FIRST-seen chunk_id/
    lexical_offset (mirroring the exact, already-established convention
    Phase 1 itself uses for sentence hypotheses -- re-observations only
    bump evidence_count, never chunk_id), unit derivation here only pairs
    boundaries using their first-seen occurrence, not every occurrence.
    """
    if not _table_exists(con, "context_hypotheses"):
        return {"units_derived": 0}
    cols = _columns(con, "context_hypotheses")
    if "lexical_offset" not in cols:
        return {"units_derived": 0, "reason": "lexical_offset_column_missing"}

    rows = con.execute(
        "SELECT id, chunk_id, lexical_offset FROM context_hypotheses "
        "WHERE role='stable_lexical_boundary' AND lexical_offset IS NOT NULL "
        "ORDER BY chunk_id ASC, lexical_offset ASC"
    ).fetchall()
    by_chunk = {}
    for hid, chunk_id, offset in rows:
        by_chunk.setdefault(chunk_id, []).append((offset, hid))

    now = _now()
    derived = 0
    for chunk_id, boundaries in by_chunk.items():
        boundaries.sort()
        for idx in range(len(boundaries) - 1):
            start_offset, left_id = boundaries[idx]
            end_offset, right_id = boundaries[idx + 1]
            if end_offset <= start_offset:
                continue
            existing = con.execute(
                "SELECT id FROM " + UNITS_TABLE + " WHERE chunk_id=? AND start_offset=? AND end_offset=?",
                (chunk_id, start_offset, end_offset),
            ).fetchone()
            if existing:
                continue
            surface_row = con.execute("SELECT text FROM chunks WHERE id=?", (chunk_id,)).fetchone()
            surface = ""
            if surface_row and surface_row[0]:
                normalized = _norm(surface_row[0], 20000)
                surface = normalized[start_offset:end_offset]
            con.execute(
                "INSERT OR IGNORE INTO " + UNITS_TABLE +
                "(surface_form,chunk_id,start_offset,end_offset,left_boundary_hypothesis_id,"
                "right_boundary_hypothesis_id,first_seen_at,last_seen_at,observation_count,"
                "status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (surface, chunk_id, start_offset, end_offset, left_id, right_id, now, now, 1,
                 "candidate", now, now),
            )
            derived += 1
    if derived:
        con.commit()
    return {"units_derived": derived}


def _neuromodulators(con):
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


def _db(loop):
    memory = getattr(loop, "mem", None) or getattr(loop, "memory", None) or getattr(loop, "db", None)
    connection = getattr(memory, "db", None) or getattr(memory, "conn", None) or memory
    if not hasattr(connection, "execute"):
        raise RuntimeError("sqlite connection not found")
    return connection


_PREV_CYCLE = None
_PREV_RUN = None


def managed_cycle(self, progress=None):
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else {"status": "phase0_no_previous_cycle"}
    try:
        con = _db(self)
        ensure_schema(con)
        neuromod = _neuromodulators(con)
        obs_result = observe_lexical_boundaries(con, neuromod)
        unit_result = _derive_lexical_units(con)
    except Exception as exc:
        obs_result = {"status": "phase0_error", "error": type(exc).__name__ + ":" + str(exc)}
        unit_result = {"units_derived": 0}
    return {
        "phase": PHASE,
        "downstream_result": result_prev,
        "phase0_lexical_result": obs_result,
        "phase0_units_result": unit_result,
    }


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase0_lexical_boundary_observation_release = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"
    AutonomousLoop.direct_relation_writes = "disabled"
    return AutonomousLoop
