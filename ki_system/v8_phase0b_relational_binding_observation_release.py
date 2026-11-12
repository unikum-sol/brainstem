# -*- coding: utf-8 -*-
"""WHAT THIS MODULE IS FOR: the existing runtime graduates individual
hypotheses (sentence-level facts, lexical-boundary word units) but never
binds two already-stable elements into a directed, S-P-O-like relation --
every promoted fact's `relation` column is hardcoded to the placeholder
"observed_as" (see v8_stageb_fact_promotion_release.py). This module adds
exactly that binding step, as a new observation layer reusing the existing
context_hypotheses machinery (confidence, uncertainty, neuromodulator
columns, Phase 7d slow-wave consolidation, Stage-B guarded graduation)
rather than inventing a parallel mechanism -- the same discipline already
used for the Lexical Layer (Phase 0).

Literatur: Dal Ben et al. 2023; Yurovsky, Yu & Smith 2012; Zhang, Yurovsky & Yu 2015
"""
from __future__ import annotations

import hashlib
import math
import re
import time

from ki_system.db_bootstrap import ensure_schema_for

PHASE = "phase0b_relational_binding_observation_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

STATE_TABLE = "phase0b_relational_state"

_SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WS_RE = re.compile(r"\s+")

DEFAULTS = {
    "enabled": "true",
    "pmi_threshold_bits": "1.0",
    # Minimum joint co-occurrence count before PMI is even computed
    # (avoids drawing conclusions from a single chance encounter).
    "min_pair_count": "3",
    "direction_threshold_de": "0.72",
    "direction_threshold_en": "0.62",
    # Minimum total first-position observations before the direction
    # asymmetry above is trusted at all (same "do not trust noisy small
    # samples" principle already used by Phase 0's min_observations).
    "min_direction_observations": "6",
    "min_candidate_evidence_count": "4",
    "chunk_batch_size": "16",
    "cursor_chunk_id": "0",
    "cycle_count": "0",
    "pairs_created_total": "0",
    "pairs_reobserved_total": "0",
    "selection_pressure_na_gain": "0.5",
    "selection_pressure_ach_direction_gain": "0.3",
}


def _now() -> int:
    return int(time.time())


def _norm(value, limit=3000) -> str:
    return _WS_RE.sub(" ", (value or "").replace("\x00", " ")).strip()[:limit]


def _sentences(text) -> list:
    return [part.strip() for part in _SENT_RE.split(_norm(text)) if part.strip()]


def _table_exists(con, table) -> bool:
    return con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return set()
    return {row[1] for row in con.execute("PRAGMA table_info(" + table + ")").fetchall()}


def ensure_schema(con):
    ensure_schema_for(con)
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
    return _self_check_schema(con)


def _self_check_schema(con):
    missing = []
    for table in (STATE_TABLE, "relational_cooccurrence_counts", "context_hypotheses"):
        if not _table_exists(con, table):
            missing.append(table)
    if "origin" not in _columns(con, "context_hypotheses"):
        missing.append("context_hypotheses.origin")
    if missing:
        raise RuntimeError("phase0b relational schema missing: " + repr(missing))
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


def _corpus_language(con):
    """Reads the GUI-set corpus_language setting (settings table, same
    mechanism as max_articles) fresh every cycle -- no restart required
    when the user changes the dropdown. Defaults to 'de' (matching this
    project's own imported corpus) if unset or invalid."""
    if not _table_exists(con, "settings"):
        return "de"
    row = con.execute("SELECT value FROM settings WHERE key=?", ("corpus_language",)).fetchone()
    if not row or not row[0]:
        return "de"
    try:
        import json
        value = json.loads(row[0])
    except Exception:
        value = row[0]
    value = str(value).strip().strip('"').strip("'").lower()
    return value if value in ("de", "en") else "de"


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


def _next_chunk_batch(con, cursor_id, batch_size):
    """Own, independent rotating cursor over chunks.id, wraps around --
    same pattern already used by Phase 0's lexical layer."""
    rows = con.execute(
        "SELECT id, text FROM chunks WHERE id>? ORDER BY id ASC LIMIT ?",
        (cursor_id, batch_size),
    ).fetchall()
    if not rows:
        rows = con.execute(
            "SELECT id, text FROM chunks ORDER BY id ASC LIMIT ?", (batch_size,)
        ).fetchall()
    return rows


def _candidate_word_spans_for_chunk(con, chunk_id, chunk_text_norm, min_candidate_evidence_count):
    """Derive real, substring-of-the-actual-text word-like spans for this
    chunk, by pairing adjacent boundary hypotheses -- mirroring Phase 0's
    own _derive_lexical_units() exactly, EXCEPT that eligibility is
    deliberately widened from role='stable_lexical_boundary' only (i.e.
    already Stage-B-graduated) to ALSO include 'uncertain_lexical_boundary'
    CANDIDATES whose own evidence_count has already cleared
    min_candidate_evidence_count.

    Returned surface forms are real substrings of chunk_text_norm, so the
    sentence-local position lookup in observe_relational_bindings() finds
    them exactly like it already does for sentence-level 'stable_hypothesis'
    subjects (which are themselves already real sentence-prefix substrings
    of the raw text, requiring no special handling here).

    Literatur: Dal Ben et al. 2023; Yurovsky, Yu & Smith 2012; Zhang, Yurovsky & Yu 2015
    """
    rows = con.execute(
        "SELECT id, lexical_offset, role, evidence_count FROM context_hypotheses "
        "WHERE chunk_id=? AND role IN ('stable_lexical_boundary','uncertain_lexical_boundary') "
        "AND lexical_offset IS NOT NULL ORDER BY lexical_offset ASC",
        (chunk_id,),
    ).fetchall()
    eligible = []
    for hid, offset, role, evidence_count in rows:
        if role == "uncertain_lexical_boundary" and int(evidence_count or 0) < min_candidate_evidence_count:
            continue
        eligible.append((offset, hid))
    spans = []
    for idx in range(len(eligible) - 1):
        start_offset, _left_id = eligible[idx]
        end_offset, _right_id = eligible[idx + 1]
        if end_offset <= start_offset:
            continue
        surface = chunk_text_norm[start_offset:end_offset].strip()
        if surface:
            spans.append((start_offset, surface))
    return spans


def _stable_elements_for_chunk(con, chunk_id, chunk_text_norm, min_candidate_evidence_count):
    rows = con.execute(
        "SELECT id, subject, text_excerpt FROM context_hypotheses "
        "WHERE chunk_id=? AND role='stable_hypothesis' ORDER BY id",
        (chunk_id,),
    ).fetchall()
    out = []
    for hid, subject, text_excerpt in rows:
        surface = (subject or text_excerpt or "").strip()
        if surface:
            out.append((hid, surface))
    for offset, surface in _candidate_word_spans_for_chunk(con, chunk_id, chunk_text_norm, min_candidate_evidence_count):
        out.append((-1, surface))
    return out


def _pair_signature(surface_a, surface_b) -> str:
    material = "relational_pair|" + surface_a.lower()[:120] + "\u2758" + surface_b.lower()[:120]
    return hashlib.sha1(material.encode("utf-8", "ignore")).hexdigest()


def _symmetric_pmi_bits(pair_count, count_a, count_b, total_pairs_observed):
    total = max(1, total_pairs_observed)
    p_ab = pair_count / total
    p_a = count_a / total
    p_b = count_b / total
    if p_ab <= 0 or p_a <= 0 or p_b <= 0:
        return 0.0
    ratio = p_ab / (p_a * p_b)
    if ratio <= 0:
        return 0.0
    return math.log2(ratio)


def _process_sentence(con, chunk_id, sentence_elements, neuromod, pmi_threshold,
                       min_pair_count, direction_threshold, min_direction_obs, now):
    """Binds every unordered pair of stable elements observed within one
    sentence. Both directions of each pair share the same
    relational_cooccurrence_counts row (signature is built from a
    canonical, sorted ordering of the two surface forms) so pair_count/
    count_a/count_b are unambiguous; first_as_a_count/first_as_b_count
    track which of the two textually appeared first in THIS sentence,
    independent of which one is stored as "a" vs "b" in the row."""
    created = 0
    reobserved = 0
    n = len(sentence_elements)
    for i in range(n):
        pos_i, hid_i, surface_i = sentence_elements[i]
        for j in range(i + 1, n):
            pos_j, hid_j, surface_j = sentence_elements[j]
            if surface_i.lower() == surface_j.lower():
                continue
            # Canonical ordering for the co-occurrence ledger row itself
            # (independent of which appeared first in this sentence) so
            # the SAME pair always accumulates into the SAME row.
            if surface_i.lower() <= surface_j.lower():
                surf_a, surf_b = surface_i, surface_j
                first_is_a = pos_i < pos_j
            else:
                surf_a, surf_b = surface_j, surface_i
                first_is_a = pos_j < pos_i
            sig_a = hashlib.sha1(surf_a.lower()[:180].encode("utf-8", "ignore")).hexdigest()
            sig_b = hashlib.sha1(surf_b.lower()[:180].encode("utf-8", "ignore")).hexdigest()

            existing = con.execute(
                "SELECT id, pair_count, count_a, count_b, first_as_a_count, first_as_b_count "
                "FROM relational_cooccurrence_counts WHERE signature_a=? AND signature_b=?",
                (sig_a, sig_b),
            ).fetchone()
            if existing:
                row_id, pair_count, count_a, count_b, first_as_a, first_as_b = existing
                pair_count = int(pair_count or 0) + 1
                count_a = int(count_a or 0) + 1
                count_b = int(count_b or 0) + 1
                first_as_a = int(first_as_a or 0) + (1 if first_is_a else 0)
                first_as_b = int(first_as_b or 0) + (0 if first_is_a else 1)
                con.execute(
                    "UPDATE relational_cooccurrence_counts SET pair_count=?, count_a=?, count_b=?, "
                    "first_as_a_count=?, first_as_b_count=?, updated_at=? WHERE id=?",
                    (pair_count, count_a, count_b, first_as_a, first_as_b, now, row_id),
                )
            else:
                pair_count, count_a, count_b = 1, 1, 1
                first_as_a = 1 if first_is_a else 0
                first_as_b = 0 if first_is_a else 1
                con.execute(
                    "INSERT INTO relational_cooccurrence_counts("
                    "signature_a,signature_b,subject_a,subject_b,pair_count,count_a,count_b,"
                    "first_as_a_count,first_as_b_count,first_seen_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (sig_a, sig_b, surf_a[:180], surf_b[:180], pair_count, count_a, count_b,
                     first_as_a, first_as_b, now, now),
                )

            if pair_count < min_pair_count:
                continue
            # total_pairs_observed approximated by this row's own pair_count
            # sum as the local frequency universe -- deliberately simple
            # and auditable rather than a global corpus-wide normalizer,
            # matching this project's "erst messen, dann aendern" bias
            # toward transparent, inspectable statistics over a single
            # opaque global constant.
            pmi = _symmetric_pmi_bits(pair_count, count_a, count_b, pair_count + count_a + count_b)
            if pmi < pmi_threshold:
                continue

            total_direction_obs = first_as_a + first_as_b
            subject_surface, object_surface, relation_hint, origin = surf_a, surf_b, "", None
            if total_direction_obs >= min_direction_obs:
                share_a = first_as_a / total_direction_obs
                if share_a >= direction_threshold:
                    subject_surface, object_surface = surf_a, surf_b
                    relation_hint, origin = "associated_with", "positional_prior"
                elif (1.0 - share_a) >= direction_threshold:
                    subject_surface, object_surface = surf_b, surf_a
                    relation_hint, origin = "associated_with", "positional_prior"
                else:
                    relation_hint = "associated_with"
            else:
                relation_hint = "associated_with"

            signature = _pair_signature(surf_a, surf_b)
            hyp_existing = con.execute(
                "SELECT id, evidence_count FROM context_hypotheses WHERE signature=? LIMIT 1",
                (signature,),
            ).fetchone()
            if hyp_existing:
                hyp_id, ev = hyp_existing
                new_evidence_count = int(ev or 1) + 1
                new_confidence = 1.0 - (1.0 / (1.0 + new_evidence_count))
                new_uncertainty = 1.0 / (1.0 + new_evidence_count)
                con.execute(
                    "UPDATE context_hypotheses SET evidence_count=?, confidence=?, uncertainty=?, "
                    "subject=?, relation_hint=?, object=?, origin=?, updated_at=? WHERE id=?",
                    (new_evidence_count, new_confidence, new_uncertainty,
                     subject_surface[:180], relation_hint,
                     object_surface[:180] if origin else "", origin, now, hyp_id),
                )
                reobserved += 1
            else:
                con.execute(
                    "INSERT INTO context_hypotheses(chunk_id,role,subject,relation_hint,object,"
                    "text_excerpt,source_title,confidence,uncertainty,status,dopamine,serotonin,"
                    "glutamate,gaba,noradrenaline,acetylcholine,signature,evidence_count,origin,"
                    "created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        chunk_id, "uncertain_relation_hypothesis", subject_surface[:180],
                        relation_hint, object_surface[:180] if origin else "",
                        (subject_surface + " " + object_surface)[:500], "",
                        0.0, 1.0, "active",
                        neuromod["dopamine"], neuromod["serotonin"], neuromod["glutamate"],
                        neuromod["gaba"], neuromod["noradrenaline"], neuromod["acetylcholine"],
                        signature, 1, origin, now, now,
                    ),
                )
                created += 1
    return created, reobserved


def observe_relational_bindings(con, neuromod):
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "phase0b_disabled", "created": 0, "reobserved": 0}

    base_pmi_threshold = _float(state.get("pmi_threshold_bits"), 1.0)
    base_min_pair_count = max(1, _int(state.get("min_pair_count"), 3))
    min_direction_obs = max(1, _int(state.get("min_direction_observations"), 6))
    min_candidate_evidence_count = max(1, _int(state.get("min_candidate_evidence_count"), 8))
    batch_size = max(1, _int(state.get("chunk_batch_size"), 16))
    cursor = _int(state.get("cursor_chunk_id"), 0)

    language = _corpus_language(con)
    threshold_key = "direction_threshold_" + language
    base_direction_threshold = _float(state.get(threshold_key), 0.72 if language == "de" else 0.62)

    noradrenaline = neuromod.get("noradrenaline", 0.3)
    acetylcholine = neuromod.get("acetylcholine", 0.5)
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    ach_gain = _float(state.get("selection_pressure_ach_direction_gain"), 0.3)
    min_pair_count = max(1, round(base_min_pair_count * (1.0 + na_gain * (0.5 - noradrenaline))))
    pmi_threshold = max(0.0, base_pmi_threshold * (1.0 + na_gain * (0.5 - noradrenaline)))
    direction_threshold = max(0.50, min(0.95, base_direction_threshold * (1.0 + ach_gain * (0.5 - acetylcholine))))

    if not _table_exists(con, "chunks"):
        return {"status": "phase0b_no_chunks", "created": 0, "reobserved": 0}

    batch = _next_chunk_batch(con, cursor, batch_size)
    if not batch:
        return {"status": "phase0b_no_chunks", "created": 0, "reobserved": 0}

    now = _now()
    total_created = 0
    total_reobserved = 0
    last_id = cursor
    for chunk_id, raw_text in batch:
        last_id = chunk_id
        chunk_text_norm = _norm(raw_text, 3000)
        elements = _stable_elements_for_chunk(con, chunk_id, chunk_text_norm, min_candidate_evidence_count)
        if len(elements) < 2:
            continue
        sentences = _sentences(raw_text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            in_sentence = []
            for hid, surface in elements:
                pos = sentence_lower.find(surface.lower())
                if pos >= 0:
                    in_sentence.append((pos, hid, surface))
            if len(in_sentence) < 2:
                continue
            in_sentence.sort(key=lambda item: item[0])
            created, reobserved = _process_sentence(
                con, chunk_id, in_sentence, neuromod, pmi_threshold, min_pair_count,
                direction_threshold, min_direction_obs, now,
            )
            total_created += created
            total_reobserved += reobserved

    _set_kv(con, STATE_TABLE, "cursor_chunk_id", last_id)
    _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
    _set_kv(con, STATE_TABLE, "pairs_created_total", _int(state.get("pairs_created_total"), 0) + total_created)
    _set_kv(con, STATE_TABLE, "pairs_reobserved_total",
            _int(state.get("pairs_reobserved_total"), 0) + total_reobserved)
    con.commit()

    return {
        "status": "phase0b_relational_binding_cycle",
        "chunks_processed": len(batch),
        "corpus_language": language,
        "direction_threshold_used": direction_threshold,
        "created": total_created,
        "reobserved": total_reobserved,
    }


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
        {"status": "phase0b_no_previous_cycle"}
    try:
        con = _db(self)
        ensure_schema(con)
        neuromod = _neuromodulators(con)
        obs_result = observe_relational_bindings(con, neuromod)
    except Exception as exc:
        obs_result = {"status": "phase0b_error", "error": type(exc).__name__ + ":" + str(exc)}
    return {
        "phase": PHASE,
        "downstream_result": result_prev,
        "phase0b_relational_result": obs_result,
    }


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase0b_relational_binding_observation_release = True
    AutonomousLoop.no_word_blacklists = True
    return AutonomousLoop
