# -*- coding: utf-8 -*-
"""V8 Phase 0b -- Relational Binding Observation (Modul A, Slice 1).

Full concept and scientific grounding: see
BrainStem_Relations_Ontology_Questions_Emergence_Concept.md, Abschnitt 2
(Modul A -- Relations-Emergenz) and Abschnitt 10.3 (concrete integration).

WHAT THIS MODULE IS FOR: the existing runtime graduates individual
hypotheses (sentence-level facts, lexical-boundary word units) but never
binds two already-stable elements into a directed, S-P-O-like relation --
every promoted fact's `relation` column is hardcoded to the placeholder
"observed_as" (see v8_stageb_fact_promotion_release.py). This module adds
exactly that binding step, as a new observation layer reusing the existing
context_hypotheses machinery (confidence, uncertainty, neuromodulator
columns, Phase 7d slow-wave consolidation, Stage-B guarded graduation)
rather than inventing a parallel mechanism -- the same discipline already
used for the Lexical Layer (Phase 0).

MECHANISM (Gate & Direction, Abschnitt 2.4.5): a Relations Hypothesis is
never a single "decision", it is a two-stage, purely statistical
generation process:

  Stage 1 -- Existence Gate (symmetric PMI, Abschnitt 2.4.2):
      For every ordered pair of already-stable elements (role
      'stable_hypothesis' or 'stable_lexical_boundary') co-occurring
      within the SAME sentence (Abschnitt 2.4.3 -- NOT the whole chunk,
      to avoid binding elements from unrelated clauses), a symmetric PMI
      is computed from three raw counters already accumulated in
      relational_cooccurrence_counts: pair_count (joint co-occurrence),
      count_a/count_b (marginal frequencies). Only pairs whose PMI clears
      a minimum threshold are eligible to become a
      'uncertain_relation_hypothesis' row at all -- this stage makes NO
      directional claim; it only answers "is this association stronger
      than chance frequency alone would predict?" (this is exactly what
      PMI is mathematically suited for, and exactly what it is NOT suited
      for is direction -- PMI(A;B) == PMI(B;A) by definition).

  Stage 2 -- Direction Signal (Positions-Heuristik, Abschnitt 2.4.1):
      Only position -- which element is observed to occur first within
      the sentence -- is used to propose a direction, because it is
      genuinely asymmetric (P(A before B) != P(B before A) are two
      distinct, mutually exclusive events, unlike PMI). The
      `corpus_language` setting (GUI dropdown next to the Import button,
      persisted via memory.set_setting, read fresh every cycle) is used
      ONLY to calibrate how large the positional asymmetry must be before
      a direction is proposed at all -- German has a well-documented,
      much weaker "position implies role" signal than English due to
      Vorfeld topicalization (Abschnitt 2.4.4, point 2), so "de" requires
      a stronger positional skew than "en" before committing to a
      direction; below that threshold the hypothesis stays in the
      ungirected 'associated_with' form.

Both signals are themselves nothing more than additional, observation-
derived quantities -- like every other hypothesis in this project, a
generated relation is a low-initial-confidence hypothesis, not a
decision, and remains fully correctable via the existing
contradiction_detection/hypothesis_revision chain (Abschnitt 6).

WHICH ELEMENTS ARE "STABLE ENOUGH" TO BIND (scientific grounding for
NOT requiring full Stage-B graduation of lexical-boundary units):
An initial implementation attempt required both bound elements to already
carry role 'stable_hypothesis' or 'stable_lexical_boundary' (i.e. already
fully Stage-B-graduated). Against this project's own real corpus this
produced zero relations even after 70 real cycles, because
'uncertain_lexical_boundary' hypotheses are, by this project's own
deliberate design (see v8_phase0_lexical_boundary_observation_release.py's
own docstring), excluded from the Phase 7d consolidation candidate pool
by default -- so they never reach 'stable_lexical_boundary' at all unless
a human deliberately lifts that isolation via
activate_lexical_layer_step4.py, a separate decision point this module
does not make on its own.

A literature search for how to resolve this found direct, converging
evidence that the "wait for full graduation first, then bind" ordering
this project's own Abschnitt 2 originally assumed is actually the WRONG
ordering, empirically: word segmentation and relational/referential
learning are not sequential stages in human learners, they run in
PARALLEL and mutually reinforce each other. Dal Ben, Toselli Prequero,
de Hollanda Souza & Hay (2023, Open Mind) directly tested this: adult
learners who segment continuous speech and cross-situationally map words
to referents AT THE SAME TIME perform BETTER than learners doing either
task alone. <cite>turn51search2</cite> Räsänen & Rasilo's computational
model goes further, showing that word segmentation emerges as a BY-PRODUCT
of joint relational/meaning learning rather than needing to complete
first. <cite>turn51search10</cite> Yurovsky, Yu & Smith (2012, Frontiers
in Psychology) demonstrate the same parallel scaffolding effect directly
on child-directed speech. <cite>turn51search26</cite> Zhang, Yurovsky &
Yu (2015) further show that statistical word learning is a continuous,
cumulative process in which partial, still-uncertain knowledge from
earlier observations is carried forward and improves later learning,
rather than learners waiting for a binary "segmentation complete" state.
<cite>turn51search24</cite>

Consequence for this module: eligible "stable enough to bind" elements
(see _stable_elements_for_chunk() below) deliberately include
'uncertain_lexical_boundary' hypotheses once their OWN evidence_count
clears a minimum threshold (min_candidate_evidence_count, tunable via
STATE_TABLE exactly like Phase 0's own min_observations) -- NOT only
already-graduated 'stable_lexical_boundary' units. This is a genuinely
different, and better-grounded, design than the module's own initial
draft, and it deliberately does NOT touch or depend on lifting Phase 7d's
existing lexical-boundary consolidation isolation -- that remains a
separate, human-made decision point, completely orthogonal to this
module's own candidate-eligibility threshold.

Every uncertain_relation_hypothesis row reuses insert-or-reobserve exactly
like Phase 0 and the sentence layer: SHA1 signature over the pair,
evidence_count increment on reobservation (including the same
BRAINSTEM_HYPOTHESIS_CONFIDENCE_FREEZE_FIX_V1 Bayesian pseudo-count update
already applied to those two layers), full INSERT with role/subject/
relation_hint/object/origin/neuromodulator snapshot on first observation.
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

# Deliberately conservative starting defaults, pending real calibration
# against this project's own already-imported corpus (see Abschnitt 10.6's
# validation plan). All tunable at runtime via STATE_TABLE key/value rows --
# no code change is needed to recalibrate them.
DEFAULTS = {
    "enabled": "true",
    # Minimum symmetric PMI (in bits, log base 2) a pair must clear before
    # any relation hypothesis is created at all (Stage 1, Abschnitt 2.4.2).
    "pmi_threshold_bits": "1.0",
    # Minimum joint co-occurrence count before PMI is even computed
    # (avoids drawing conclusions from a single chance encounter).
    "min_pair_count": "3",
    # Minimum positional asymmetry (fraction of "first_as_a" vs total
    # first-position observations, 0.5 = perfectly balanced) required
    # before a direction is proposed at all, PER corpus_language (Abschnitt
    # 2.4.4 point 2 / 2.4.5): German's much weaker positional signal (V2
    # word order, Vorfeld topicalization) gets a higher bar than English's
    # comparatively reliable SVO/agent-first ordering.
    "direction_threshold_de": "0.72",
    "direction_threshold_en": "0.62",
    # Minimum total first-position observations before the direction
    # asymmetry above is trusted at all (same "do not trust noisy small
    # samples" principle already used by Phase 0's min_observations).
    "min_direction_observations": "6",
    # Minimum evidence_count an 'uncertain_lexical_boundary' hypothesis
    # must have reached before this module treats it as "stable enough to
    # bind" (see module docstring's literature-grounded rationale for why
    # this module deliberately does NOT wait for full Stage-B graduation
    # of lexical-boundary units). Mirrors Phase 0's own min_observations
    # philosophy of not trusting a barely-seen candidate's statistics.
    #
    # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_CALIBRATION_V1 (25 September 2026)
    #
    # Lowered from the original, uncalibrated starting value of 8 to 4,
    # based on a controlled synthetic-corpus experiment (six values swept
    # from 2 to 64, ~55-60 real cycles each, against 70 short German
    # sentences with known ground-truth word boundaries -- full derivation
    # in the Slice 1 Review Report shipped with this delivery). Key finding:
    # within that experiment's reachable observation depth, single-word
    # span PRECISION did not meaningfully differ across threshold values
    # 2/4/8/16 (all in the 35-42% single-word-span range) -- the dominant
    # bottleneck was found to be Phase 0's own boundary DETECTION density
    # (entropy_threshold_bits=1.0), not this threshold, since only ~1
    # boundary was detected per ~8.6-word sentence on average, regardless
    # of how many additional reobservation cycles were run. Given precision
    # was statistically indistinguishable across low-to-moderate threshold
    # values, YIELD became the deciding factor: threshold=4 produced
    # meaningfully more co-occurrence data and relation hypotheses than the
    # original default of 8 (22 vs 5 relation hypotheses at matched cycle
    # count), without a measurable precision cost. Threshold=8 is not wrong,
    # but was an arbitrary starting guess (borrowed directly from Phase 0's
    # own min_observations default) rather than a value derived from
    # evidence -- exactly the kind of unvalidated constant this project's
    # own "erst messen, dann aendern" principle warns against carrying
    # forward unexamined.
    #
    # IMPORTANT, EXPLICIT CAVEAT: this synthetic experiment's reobservation
    # RATE (a ~70-chunk corpus reread by Phase 0's own cursor roughly every
    # 8-9 cycles) is dramatically faster, per chunk, than this project's
    # real, ~167,661-chunk production corpus would ever achieve at the same
    # per-cycle batch size (order of ~2,400x fewer chunk-revisits per unit
    # time on the real corpus) -- so this value is a validated, defensible
    # STARTING point given the evidence available, not a final, production-
    # calibrated number. Before relying on this value in production, run
    # the companion read-only diagnostic script
    # (tools/diagnose_relational_binding_calibration.py) against the real
    # database to measure actual boundary density and eligible-pool size
    # there, and adjust this value (or, if density is confirmed too low
    # there too, prioritize recalibrating Phase 0's own
    # entropy_threshold_bits instead -- see that script's own guidance).
    "min_candidate_evidence_count": "4",
    # How many sentences (across however many chunks needed) this module
    # processes per real cycle, using its OWN independent rotating cursor
    # over chunks.id -- deliberately NOT coupled to reading_queue/Phase 1's
    # own bookkeeping or Phase 0's own cursor, so this module can never
    # interfere with either.
    "chunk_batch_size": "16",
    "cursor_chunk_id": "0",
    "cycle_count": "0",
    "pairs_created_total": "0",
    "pairs_reobserved_total": "0",
    # BRAINSTEM_PHASE0B_NEUROMODULATOR_COUPLING_V1 (28 September 2026)
    #
    # Root cause: this module already reads the shared neuromodulator
    # snapshot (_neuromodulators() below, called every real cycle) and
    # even stores it on every newly-created relation hypothesis row -- but
    # none of its own three thresholds (min_pair_count, pmi_threshold_bits,
    # direction_threshold_de/en) ever actually USED that snapshot to
    # modulate a decision. This mirrors the exact same class of gap
    # already found and fixed this session in v8_stageb_gap_detection_
    # release.py's own existence gate and v8_stageb_question_promotion_
    # release.py's own persistence gate.
    #
    # (1)+(2) Noradrenaline -> min_pair_count / pmi_threshold_bits (both
    #     Stage 1 EXISTENCE gates, Abschnitt 2.4.2): reuses the exact same
    #     gain magnitude and symmetric (1.0 + gain*(0.5-value)) formula
    #     already verified twice this session (gap_detection's own
    #     stalled_min_evidence_count; question_promotion's own
    #     min_resolution_attempts_for_question), grounded in Aston-Jones &
    #     Cohen's Adaptive Gain Theory (2005, Annu. Rev. Neurosci.
    #     28:403-450): tonic locus-coeruleus noradrenaline is active "when
    #     utility in the task wanes", associated with disengagement and
    #     exploratory search for alternatives -- a system in this state
    #     should be MORE receptive to a weaker, less-repeated candidate
    #     association (lower bars on both existence-gate thresholds),
    #     while a low-noradrenaline, exploitative state stays focused on
    #     only the most robustly, repeatedly observed pairs.
    #
    # (3) Acetylcholine -> direction_threshold_de/en (Stage 2 STRUCTURAL
    #     interpretation, Abschnitt 2.4.1): deliberately NOT grounded in a
    #     brand-new external citation, but in this project's OWN, already-
    #     established internal convention -- v8_phase6a_neuromodulated_
    #     sleep_replay_and_meta_plasticity_release.py's own formula
    #     already ties acetylcholine directly to "revision_bias" (this
    #     project's own structural-revision signal; see that module's
    #     "acetylcholine": .18+.33*revision+... formula). Assigning a
    #     directional subject/object interpretation to a pair is exactly
    #     this same kind of structural interpretation decision -- so high
    #     acetylcholine (elevated revision/structural-encoding tendency)
    #     lowers the positional-asymmetry bar required before committing
    #     to a direction, while low acetylcholine keeps the pair in the
    #     more conservative, undirected 'associated_with' form for longer.
    #     Explicitly clamped to a narrower [0.50, 0.95] range (unlike the
    #     two count-based gates above) since this threshold is itself a
    #     probability-like share value, not an open-ended count.
    #
    # All three are exactly inert (no behavior change from before this
    # delivery) at their respective messenger's neutral baseline of 0.5.
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

    IMPORTANT DISTINCTION FROM AN EARLIER, BUGGY DRAFT OF THIS FUNCTION:
    a context_hypotheses row with role='uncertain_lexical_boundary' does
    NOT itself hold a usable word span in its subject/text_excerpt field --
    Phase 0 stores a fixed LOCAL CONTEXT WINDOW around the boundary
    position there (e.g. "nd |lie", built with an internal U+2758
    separator character that never occurs in the real text), not the word
    itself (confirmed directly against real, produced rows during
    validation of this module). A real, bindable surface form only ever
    exists as the TEXT BETWEEN TWO boundaries -- exactly what Phase 0's
    own _derive_lexical_units() already computes, but only for already-
    graduated boundaries. This function performs the identical pairing
    computation, on the widened, evidence_count-gated candidate set
    described in this module's own docstring (Dal Ben et al. 2023;
    Raesaenen & Rasilo; Yurovsky, Yu & Smith 2012; Zhang, Yurovsky & Yu
    2015), so a genuine, findable substring of the chunk's own text is
    always what gets bound, never a raw boundary-window signature.

    Returned surface forms are real substrings of chunk_text_norm, so the
    sentence-local position lookup in observe_relational_bindings() finds
    them exactly like it already does for sentence-level 'stable_hypothesis'
    subjects (which are themselves already real sentence-prefix substrings
    of the raw text, requiring no special handling here)."""
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
    """Combines the two eligible input sources for this module's binding:
    (1) already-stable sentence-level hypotheses (role 'stable_hypothesis'),
        whose subject field is already a real substring of the raw
        sentence text -- used directly, no derivation needed;
    (2) real word-like spans derived from adjacent lexical-boundary
        candidates via _candidate_word_spans_for_chunk() above (see that
        function's docstring for why this replaced a direct, but broken,
        earlier attempt to bind raw boundary-window subjects directly).
    """
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
    """Standard, symmetric Pointwise Mutual Information, in bits.
    log2( P(A,B) / (P(A)*P(B)) ), estimated from raw counts. Deliberately
    symmetric (PMI(A;B) == PMI(B;A)) -- see module docstring and Abschnitt
    2.4.2: this stage answers ONLY "does a real association exist", never
    "which direction". Frequency-normalized by construction, which is
    exactly why it replaces the raw transitional-probability approach that
    an earlier draft of this concept used (that approach was found, on
    external review, to conflate semantic role asymmetry with pure
    collocation/frequency asymmetry -- e.g. "Kaffee trinken")."""
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

            # --- Stage 1: symmetric PMI existence gate (Abschnitt 2.4.2) ---
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

            # --- Stage 2: positional direction signal (Abschnitt 2.4.1) ---
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

            # Identity is ALWAYS the canonical, symmetric pair (surf_a,
            # surf_b) -- deliberately independent of the current subject/
            # object direction assignment above. If the signature were
            # built from subject_surface/object_surface instead, a pair
            # whose direction assessment later flips (or newly resolves
            # from undirected to directed, as more evidence accumulates)
            # would silently spawn a SECOND, disconnected
            # context_hypotheses row for the same underlying pair instead
            # of being reobserved -- exactly the kind of split-identity bug
            # Phase 0's own fixed-local-window signature was designed to
            # avoid for lexical boundaries. Subject/object/relation_hint/
            # origin below are instead treated as the row's current best
            # DIRECTION ASSESSMENT, refined on every reobservation, while
            # the row's IDENTITY stays fixed to the pair.
            signature = _pair_signature(surf_a, surf_b)
            hyp_existing = con.execute(
                "SELECT id, evidence_count FROM context_hypotheses WHERE signature=? LIMIT 1",
                (signature,),
            ).fetchone()
            if hyp_existing:
                hyp_id, ev = hyp_existing
                new_evidence_count = int(ev or 1) + 1
                # Same Bayesian pseudo-count update already applied to the
                # sentence and lexical layers
                # (BRAINSTEM_HYPOTHESIS_CONFIDENCE_FREEZE_FIX_V1) -- applied
                # here from the start, so relation hypotheses never suffer
                # the same freeze bug those two layers had before it was
                # found and fixed.
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

    # BRAINSTEM_PHASE0B_NEUROMODULATOR_COUPLING_V1: see DEFAULTS' own
    # comment for the full derivation. All three factors are exactly 1.0
    # (no behavior change) at their messenger's own neutral baseline of
    # 0.5, so calibrated defaults remain unchanged unless the
    # corresponding messenger genuinely deviates from neutral.
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
        # Phase 0's own lexical_offset values are computed against ITS OWN
        # normalized/truncated chunk text (_norm() with chunk_text_limit,
        # default 3000 -- see v8_phase0_lexical_boundary_observation_
        # release.py's own DEFAULTS). This module's _norm() uses the same
        # default limit, so offsets index consistently into the same
        # string here. If a deployment ever changes Phase 0's own
        # chunk_text_limit away from its default, this value should be
        # changed to match -- not re-derived independently, to avoid the
        # two modules silently drifting apart on what "the chunk text" is.
        chunk_text_norm = _norm(raw_text, 3000)
        # Re-derive per-sentence position ordering directly from the
        # already-stable hypotheses recorded for this chunk, matched
        # against the chunk's own sentence split (same _sentences() split
        # already used by the sentence-level layer) so elements are only
        # ever bound within the SAME sentence (Abschnitt 2.4.3), never
        # across sentence boundaries within a chunk.
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
