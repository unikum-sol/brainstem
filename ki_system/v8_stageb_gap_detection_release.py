# -*- coding: utf-8 -*-
"""V8 Stage-B Gap Detection -- fills the previously-empty internal_learning_gaps.

BACKGROUND (found via a project-wide code audit, 22 September 2026, as part
of the user-requested experiment to lift the previously-closed productive
write locks): internal_learning_gaps has been a fully-declared, centrally
maintained table (see db_bootstrap.py's SCHEMA_TABLES, including several
historical fixes to keep its column set complete: severity, hypothesis_id,
uncertainty, pattern_key, resolution_attempts, revision_pressure) since
long before this module existed -- but NO module anywhere in the entire
project ever actually wrote a single row into it. A code comment in
v8_phase5a_integrated_self_improving_learning_release.py references a
historical module, "phase4j_internal_learning_questions_and_gap_detection",
that appears to have been removed as part of this project's own Legacy
Cleanup contract without its gap-generation responsibility ever being
reimplemented. Several already-existing, already-tested downstream modules
(v8_phase5b, v8_phase5e, v8_phase5g, v8_phase5i, v8_phase6a) all already
contain real, working logic to CONSUME rows from this table -- they simply
never received any, because nothing produced them.

THIS MODULE'S JOB: produce plausible, genuinely-motivated candidate gaps
from the existing, real context_hypotheses population -- reusing already-
observed signals (evidence_count, confidence, uncertainty, role,
signature) rather than inventing a new, separate scoring mechanism. Two
independent gap-detection heuristics are implemented, matching this
project's stated goal of surfacing hypotheses that are either (a)
repeatedly observed but never progressing, or (b) apparently in tension
with another already-established hypothesis (the latter is also the raw
material Stage-B contradiction detection, see
v8_stageb_contradiction_detection_release.py, needs to have something to
examine).

Explicitly NOT part of this module: no fact/relation/question writes, no
change to context_hypotheses.role, no consolidation logic. This module
only ever writes to internal_learning_gaps (an already-existing, already-
declared table) and its own small runtime-state table.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
from typing import Any, Dict, List

PHASE = "stageb_gap_detection_release"
STATE_TABLE = "stageb_gap_detection_state"
DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    # How many candidate hypotheses to scan per real cycle -- deliberately
    # bounded, matching the project's own established convention (e.g.
    # Phase 0's chunk_batch_size) of processing a fixed, small slice per
    # cycle rather than the entire table at once.
    "scan_limit": "200",
    # A hypothesis is only considered "stalled" (gap type
    # "stalled_uncertain_hypothesis") if it has been observed at least this
    # many times without yet graduating -- avoids flagging brand-new,
    # simply-not-yet-consolidated hypotheses as gaps.
    "stalled_min_evidence_count": "20",
    # BRAINSTEM_GAP_DETECTION_NEUROMODULATOR_COUPLING_V1 (28 September 2026)
    #
    # Root cause: this module reads context_hypotheses (evidence_count,
    # confidence, uncertainty) but never once read the project's own
    # neuromodulator state -- despite phase6a_neuromodulated_sleep_state
    # already being read by every comparable Stage-B/Phase module
    # (v8_stageb_question_promotion_release.py, v8_phase7d_..., etc.). Two
    # couplings are added here, each grounded in a specific, causally
    # demonstrated neuroscience mechanism -- not a generic "add all six"
    # pass:
    #
    # (1) Noradrenaline -> stalled_min_evidence_count (the existence gate
    #     itself). Aston-Jones & Cohen's Adaptive Gain Theory (2005, Annu.
    #     Rev. Neurosci. 28:403-450) describes locus-coeruleus
    #     noradrenaline as switching between a tonic mode -- active
    #     "when utility in the task wanes", associated with "disengagement
    #     from the current task and a search for alternative behaviors"
    #     (exploration) -- and a phasic mode tied to already-committed,
    #     task-relevant decisions (exploitation). A system in a high-
    #     noradrenaline, exploratory state should therefore be MORE
    #     receptive to weaker, less-repeated candidate signals (a lower
    #     evidence-count bar before something is even considered a gap);
    #     a low-noradrenaline, exploitative state should stay focused on
    #     only the most robustly, repeatedly observed candidates (a higher
    #     bar). This also composes correctly with this project's own
    #     pre-existing noradrenaline-generating pathway (cooperative_core's
    #     own target formula already feeds persistent_gap_pressure INTO
    #     noradrenaline) -- a system already carrying elevated
    #     noradrenaline from unresolved pressure becomes appropriately MORE
    #     receptive to further candidate gaps, not less.
    #
    # (2) Serotonin -> habituation_max_stagnant_cycles (see that
    #     parameter's own comment below for the full derivation and
    #     citations -- Hochner/Klein/Schacher/Kandel 1986; Cohen/Kaplan/
    #     Kandel/Hawkins 1997).
    #
    # Both couplings use the same symmetric, self-regulating gain pattern
    # already established in v8_phase7d_slow_wave_sleep_substructure_
    # release.py's own acetylcholine gate: a multiplicative factor of
    # (1.0 +/- gain*(value-0.5)) that is EXACTLY 1.0 at the neutral
    # baseline (0.5) -- so at baseline neuromodulator levels, both
    # thresholds remain numerically identical to their pre-coupling
    # values, and only move as the corresponding neuromodulator deviates
    # from neutral.
    "selection_pressure_na_gain": "0.5",
    # BRAINSTEM_GAP_CLOSURE_AND_HABITUATION_V1 (25 September 2026)
    #
    # How many consecutive REOBSERVATION cycles a gap may go without any
    # real growth in its own evidence_count (i.e. no genuinely new
    # supporting evidence, only a re-confirmation that it is still
    # unresolved) before it is retired into a terminal 'habituated' status
    # -- reversible the moment real new evidence does arrive (see
    # _upsert_gap()'s dishabituation branch below). This directly
    # implements the empirically-established inverted-U relationship
    # between resolvability and curiosity (Kang et al. 2009, Psychological
    # Science 20(8):963-973: curiosity peaks at moderate resolvability and
    # falls off at both extremes; synthesized further in Ten/Oudeyer/
    # Sakaki/Murayama 2025, Open Mind 9:1763-1785) and habituation as a
    # process driven by absence of new information gain specifically, not
    # by elapsed time/attempts alone (Ueda/Sekoguchi/Yanagisawa 2021, PLoS
    # One 16(6):e0237278) -- gaps that keep gaining real evidence every
    # cycle NEVER accumulate a stagnation streak, no matter how many
    # cycles pass; only genuinely unproductive, evidence-frozen gaps do
    # (e.g. Phase-0 lexical-boundary parsing artifacts that were observed
    # a handful of times and then never recur).
    #
    # Calibrated, not guessed: v8_stageb_question_promotion_release.py's
    # own min_resolution_attempts_for_question=15 was measured (see the
    # Questions Slice 3 audit report) against this project's own real,
    # instrumented sleep/wake rhythm period of 16 real AutonomousLoop.
    # cycle() calls (10 sleep-phase cycles + 6 wake-phase cycles). That
    # same 16-cycle unit is reused here as the calibration basis: a gap
    # must persist across roughly ONE full rhythm (~15-16 cycles) before
    # it is even eligible to motivate a question, but must then remain
    # UNPRODUCTIVE (no evidence growth at all) across FOUR full rhythms
    # (4x16=64 cycles) before it is judged conclusively unresolvable and
    # habituated -- deliberately much longer than the eligibility bar, so
    # that a gap is never habituated while still in its productive,
    # rising-curiosity phase, only once sustained unproductiveness is
    # itself well-established. Verified reproducible against a real,
    # instrumented multi-cycle run with a deliberately unproductive,
    # frozen synthetic hypothesis (see this delivery's own audit report,
    # \"Habituation Calibration\" section) before this default was set.
    # Runtime-tunable via this state table, no code change needed to
    # recalibrate against the real 167k-chunk production corpus.
    "habituation_max_stagnant_cycles": "64",
    # BRAINSTEM_GAP_DETECTION_NEUROMODULATOR_COUPLING_V1 (28 September 2026)
    #
    # Serotonin -> habituation_max_stagnant_cycles. This is the strongest,
    # most directly cellularly-demonstrated neuromodulator coupling found
    # across this entire tracking exercise: Hochner, Klein, Schacher &
    # Kandel (1986, PNAS 83:8794-8798) show that habituation IS synaptic
    # depression at the sensory-neuron synapse, and that serotonin drives
    # a SEPARATE, second facilitatory process -- independent of the
    # classic action-potential-broadening mechanism -- that specifically
    # counteracts this depression: "since homosynaptic depression
    # underlies the behavioral process of habituation, [this] second set
    # of processes, by counteracting the consequences of the depression,
    # seems to mediate the effects of dishabituation". Cohen, Kaplan,
    # Kandel & Hawkins (1997, J Neurosci 17:2886-2899) confirm the same
    # division directly in the intact gill-withdrawal reflex: habituation
    # is attributable to synapse depression, while dishabituation is
    # driven by facilitation at that same synapse.
    #
    # Applied here as a multiplicative modulation of the effective
    # habituation threshold itself (not as a separate, evidence-free
    # dishabituation trigger -- this project's own "erst messen, dann
    # aendern" discipline requires that dishabituation continue to require
    # a real evidence_count gain, exactly as the existing state machine in
    # _upsert_gap() already enforces): high serotonin raises the effective
    # threshold a gap must sustain before habituating (facilitation
    # counteracting depression, i.e. resisting habituation, matching
    # serotonin's demonstrated cellular role), low serotonin lowers it
    # (weaker facilitation, depression proceeds unopposed, matching this
    # project's own pre-existing framing of serotonin as the consolidation/
    # stability messenger). At the neutral baseline (serotonin=0.5) this
    # is exactly 1.0, so the calibrated default of 64 remains unchanged
    # unless serotonin genuinely deviates from neutral.
    "selection_pressure_serotonin_gain": "0.5",
    "gaps_created_total": "0",
    "gaps_reobserved_total": "0",
    "gaps_habituated_total": "0",
    "gaps_dishabituated_total": "0",
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
    required_gap_cols = {
        "id", "gap_key", "gap_type", "gap_reason", "role", "priority",
        "severity", "hypothesis_id", "uncertainty", "pattern_key", "status",
        "resolution_score", "evidence_count", "created_at", "updated_at",
        # BRAINSTEM_GAP_CLOSURE_AND_HABITUATION_V1 (25 September 2026)
        "closed_at", "closure_reason", "habituated_at", "stagnant_streak",
        "evidence_count_at_last_gain",
    }
    have = _columns(con, "internal_learning_gaps")
    missing.extend("internal_learning_gaps." + c for c in required_gap_cols - have)
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if missing:
        raise RuntimeError("stageb gap detection schema missing: " + repr(missing))
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
    """BRAINSTEM_GAP_DETECTION_NEUROMODULATOR_COUPLING_V1: identical
    access pattern to every other module in this chain that reads the
    shared six-core neuromodulator snapshot (e.g. v8_stageb_question_
    promotion_release.py's own _neuromodulators()) -- no new messenger
    responsibility introduced, this module simply reads the same,
    already-existing state everyone else already reads."""
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


def _upsert_gap(con, gap_key, gap_type, gap_reason, role, priority, severity,
                 hypothesis_id, uncertainty, pattern_key, evidence_count, now,
                 habituation_max=64):
    # BRAINSTEM_GAP_RESOLUTION_ATTEMPTS_DEAD_COLUMN_FIX_V1 (25 September 2026)
    #
    # Root cause, found while implementing Questions Slice 3 and confirmed
    # via a project-wide grep audit of every reference to
    # "resolution_attempts" across all ~63 modules: internal_learning_gaps.
    # resolution_attempts is declared in db_bootstrap.py's SCHEMA_TABLES and
    # is READ, via COALESCE(resolution_attempts,0), by v8_phase5b_integrated_
    # strategy_refinement_release.py's own persistent-gap-strategy query --
    # but no module anywhere, including this one (the sole owner/writer of
    # a gap's base lifecycle row), ever increments it. On every real cycle,
    # for every gap, it silently stays at its schema default of 0 forever.
    # This was not merely a latent risk: the Relations/Ontology/Questions
    # Emergence Concept document's own Abschnitt 4.2/10.3 explicitly
    # specified gating question promotion on "resolution_attempts hoch,
    # resolution_score niedrig" -- a criterion that, against the real,
    # unmodified codebase, could never once become true, since the left-
    # hand side never leaves 0. Verified reproducible against a fresh
    # bootstrap plus a real multi-cycle gap-detection run (see the Slice 3
    # audit report, "Threshold Calibration" section) before this fix.
    #
    # Fix, scoped narrowly to this module's own already-existing
    # reobservation branch (no other module touched, no new judgment
    # introduced): each time an already-known gap is reobserved --
    # i.e. the system re-encounters, in a later, independent gap-detection
    # cycle, the same stalled hypothesis or contested pair still unresolved
    # -- resolution_attempts is incremented by exactly 1. This gives the
    # column the real, monotonically-growing meaning its name and its
    # existing downstream readers already assumed it had: "how many
    # separate cycles have reconfirmed this gap is still open", the same
    # per-gap reconfirmation-count principle already used project-wide
    # (e.g. v8_stageb_ontology_cluster_observation_release.py's own
    # stability streak, phase5e's phase5e_expansion_attempts,
    # phase5g/5i's own *_experiment_count columns).
    # BRAINSTEM_GAP_CLOSURE_AND_HABITUATION_V1 (25 September 2026)
    #
    # Habituation/dishabituation state machine, added alongside the
    # already-existing resolution_attempts increment. Reads and updates
    # exactly one additional pair of columns this module itself owns
    # (evidence_count_at_last_gain, stagnant_streak) plus the pre-existing
    # `status` column -- no other module ever writes stagnant_streak or
    # evidence_count_at_last_gain; fact/relation promotion only ever set
    # status to 'closed' (and back to 'open' on retraction) at their own
    # separate write points, never touching these two columns, so there is
    # no write-write conflict between the two mechanisms.
    #
    # Real information gain (Ueda/Sekoguchi/Yanagisawa 2021) is defined
    # here as: this reobservation's raw evidence_count (passed in fresh
    # from the calling detector, BEFORE the max()-clamped value stored
    # below) exceeds the evidence_count recorded at the LAST cycle that
    # itself showed a gain -- not merely the previously stored (already
    # max()-clamped) evidence_count, which would never allow detecting
    # "no further gain" once evidence_count had ever grown once.
    #
    # Three cases, in order:
    #   1. status=='closed'  -> positively resolved via graduation
    #      (v8_stageb_fact_promotion_release.py / v8_stageb_relation_
    #      promotion_release.py); untouched by this state machine entirely,
    #      so a subsequent stalled/contested reobservation can never
    #      silently reopen a gap that was actually, correctly resolved.
    #   2. status=='habituated' AND real gain this cycle -> dishabituate:
    #      genuinely new evidence arrived for something the system had
    #      given up on -- exactly the reversible "renewed salience"
    #      behavior real habituation exhibits (Groves & Thompson's classic
    #      dual-process habituation/sensitization framework; Smart/
    #      Shvartsman/Moennigmann 2026's fading-memory formalization).
    #   3. status in ('open','persistent_gap') AND stagnant_streak reaches
    #      habituation_max with NO gain this cycle -> habituate.
    existing = con.execute(
        "SELECT id, evidence_count, resolution_attempts, status, "
        "COALESCE(evidence_count_at_last_gain,0), COALESCE(stagnant_streak,0), habituated_at "
        "FROM internal_learning_gaps WHERE gap_key=?",
        (gap_key,),
    ).fetchone()
    if existing:
        gid, prior_ev, prior_attempts, cur_status, prior_gain_ev, prior_streak, prior_habituated_at = existing
        gained = evidence_count > prior_gain_ev
        if gained:
            new_gain_ev, new_streak = evidence_count, 0
        else:
            new_gain_ev, new_streak = prior_gain_ev, prior_streak + 1

        new_status = cur_status
        new_habituated_at = prior_habituated_at
        habituated_delta = 0
        dishabituated_delta = 0
        if cur_status == "closed":
            pass
        elif cur_status == "habituated":
            if gained:
                new_status = "open"
                new_habituated_at = None
                dishabituated_delta = 1
        else:
            if (not gained) and new_streak >= max(1, int(habituation_max)):
                new_status = "habituated"
                new_habituated_at = now
                habituated_delta = 1

        con.execute(
            "UPDATE internal_learning_gaps SET priority=?, severity=?, uncertainty=?, "
            "evidence_count=?, resolution_attempts=?, evidence_count_at_last_gain=?, "
            "stagnant_streak=?, status=?, habituated_at=?, updated_at=? WHERE id=?",
            (priority, severity, uncertainty, max(int(prior_ev or 0), evidence_count),
             int(prior_attempts or 0) + 1, new_gain_ev, new_streak, new_status,
             new_habituated_at, now, gid),
        )
        if habituated_delta:
            _set_kv(con, STATE_TABLE, "gaps_habituated_total",
                    _int(_read_kv(con, STATE_TABLE).get("gaps_habituated_total"), 0) + 1)
        if dishabituated_delta:
            _set_kv(con, STATE_TABLE, "gaps_dishabituated_total",
                    _int(_read_kv(con, STATE_TABLE).get("gaps_dishabituated_total"), 0) + 1)
        return "reobserved" if new_status == cur_status else "reobserved_" + new_status
    con.execute(
        "INSERT INTO internal_learning_gaps(gap_key,gap_type,gap_reason,role,priority,"
        "severity,hypothesis_id,uncertainty,pattern_key,status,resolution_score,"
        "evidence_count,evidence_count_at_last_gain,stagnant_streak,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (gap_key, gap_type, gap_reason, role, priority, severity, hypothesis_id,
         uncertainty, pattern_key, "open", 0.0, evidence_count, evidence_count, 0, now, now),
    )
    return "created"


def _detect_stalled_hypotheses(con, scan_limit, min_evidence, now, habituation_max=64) -> Dict[str, int]:
    """Heuristic A: a hypothesis that has been observed many times (high
    evidence_count) but never graduated is a plausible "gap" -- something
    the system keeps re-encountering without ever resolving further.
    Reuses evidence_count exactly as already recorded by
    v8_context_observation_learning_release.py / v8_phase0_lexical_
    boundary_observation_release.py; does not introduce a new metric."""
    created = reobserved = 0
    if not _table_exists(con, "context_hypotheses"):
        return {"created": 0, "reobserved": 0}
    cols = _columns(con, "context_hypotheses")
    if "evidence_count" not in cols or "role" not in cols:
        return {"created": 0, "reobserved": 0}
    rows = con.execute(
        "SELECT id, role, evidence_count, uncertainty, text_excerpt FROM context_hypotheses "
        "WHERE role IN ('uncertain_hypothesis','uncertain_lexical_boundary') "
        "AND COALESCE(evidence_count,0) >= ? "
        "ORDER BY evidence_count DESC LIMIT ?",
        (min_evidence, scan_limit),
    ).fetchall()
    for hid, role, ev, unc, excerpt in rows:
        ev = _int(ev, 0)
        unc = _float(unc, 1.0)
        gap_key = "stalled:" + str(hid)
        pattern_key = hashlib.sha1(("stalled|" + str(excerpt or "")).encode("utf-8", "ignore")).hexdigest()
        priority = min(1.0, ev / 2000.0)
        severity = min(1.0, ev / 2000.0)
        decision = _upsert_gap(
            con, gap_key, "stalled_uncertain_hypothesis",
            "high_evidence_count_never_graduated", role, priority, severity,
            hid, unc, pattern_key, ev, now, habituation_max,
        )
        if decision == "created":
            created += 1
        else:
            reobserved += 1
    return {"created": created, "reobserved": reobserved}


def _detect_contested_pairs(con, scan_limit, now, habituation_max=64) -> Dict[str, int]:
    """Heuristic B: two DIFFERENT, already-existing hypotheses that share
    the exact same normalized subject prefix (already computed and stored
    as context_hypotheses.subject by the existing observation modules) but
    have a DIFFERENT text_excerpt are a plausible sign of tension between
    two competing observations about "the same thing". This does not
    itself decide who is right -- it only surfaces the pair as a gap for
    v8_stageb_contradiction_detection_release.py to examine more closely.
    Deliberately scoped to already-STABLE hypotheses only (both sentence
    and lexical-boundary), since a contested pair is only actionable once
    both sides have already survived this project's own multi-cycle
    consolidation -- comparing two barely-observed, still-uncertain
    hypotheses would be noise, not a genuine signal."""
    created = reobserved = 0
    if not _table_exists(con, "context_hypotheses"):
        return {"created": 0, "reobserved": 0}
    cols = _columns(con, "context_hypotheses")
    if not {"subject", "role", "text_excerpt"}.issubset(cols):
        return {"created": 0, "reobserved": 0}
    rows = con.execute(
        "SELECT id, subject, text_excerpt, evidence_count, uncertainty FROM context_hypotheses "
        "WHERE role IN ('stable_hypothesis','stable_lexical_boundary') "
        "AND subject IS NOT NULL AND subject <> '' "
        "ORDER BY subject, id LIMIT ?",
        (scan_limit,),
    ).fetchall()
    by_subject: Dict[str, List] = {}
    for hid, subject, excerpt, ev, unc in rows:
        by_subject.setdefault(subject, []).append((hid, excerpt, ev, unc))
    for subject, items in by_subject.items():
        if len(items) < 2:
            continue
        distinct_excerpts = {excerpt for _hid, excerpt, _ev, _unc in items}
        if len(distinct_excerpts) < 2:
            continue
        ids_sorted = sorted(hid for hid, _e, _ev, _unc in items)
        pair_key = "contested:" + subject + ":" + ",".join(str(i) for i in ids_sorted[:2])
        total_ev = sum(_int(ev, 0) for _hid, _e, ev, _unc in items)
        avg_unc = sum(_float(unc, 1.0) for _hid, _e, _ev, unc in items) / len(items)
        priority = min(1.0, 0.3 + 0.1 * len(items))
        severity = min(1.0, 0.3 + 0.1 * len(items))
        decision = _upsert_gap(
            con, pair_key, "contested_subject_multiple_excerpts",
            "same_subject_conflicting_text_excerpt", "stable_hypothesis",
            priority, severity, ids_sorted[0], avg_unc, subject, total_ev, now,
            habituation_max,
        )
        if decision == "created":
            created += 1
        else:
            reobserved += 1
    return {"created": created, "reobserved": reobserved}


def run_gap_detection_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_gap_detection_disabled", "created": 0, "reobserved": 0}
    scan_limit = max(1, _int(state.get("scan_limit"), 200))
    base_min_evidence = max(1, _int(state.get("stalled_min_evidence_count"), 20))
    base_habituation_max = max(1, _int(state.get("habituation_max_stagnant_cycles"), 64))
    now = _now()

    # BRAINSTEM_GAP_DETECTION_NEUROMODULATOR_COUPLING_V1 (28 September
    # 2026): see the DEFAULTS block's own comments for
    # selection_pressure_na_gain / selection_pressure_serotonin_gain for
    # the full derivation and citations. Both factors are exactly 1.0 at
    # the neutral neuromodulator baseline (0.5), so calibrated defaults
    # remain unchanged unless the corresponding messenger genuinely
    # deviates from neutral.
    neuromod = _neuromodulators(con)
    na = neuromod["noradrenaline"]
    serotonin = neuromod["serotonin"]
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    serotonin_gain = _float(state.get("selection_pressure_serotonin_gain"), 0.5)

    min_evidence = max(1, round(base_min_evidence * (1.0 + na_gain * (0.5 - na))))
    habituation_max = max(1, round(base_habituation_max * (1.0 + serotonin_gain * (serotonin - 0.5))))

    stalled = _detect_stalled_hypotheses(con, scan_limit, min_evidence, now, habituation_max)
    contested = _detect_contested_pairs(con, scan_limit, now, habituation_max)

    created = stalled["created"] + contested["created"]
    reobserved = stalled["reobserved"] + contested["reobserved"]

    _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
    _set_kv(con, STATE_TABLE, "gaps_created_total", _int(state.get("gaps_created_total"), 0) + created)
    _set_kv(con, STATE_TABLE, "gaps_reobserved_total", _int(state.get("gaps_reobserved_total"), 0) + reobserved)
    con.commit()

    return {
        "status": "stageb_gap_detection_cycle",
        "stalled_hypotheses": stalled,
        "contested_pairs": contested,
        "created": created,
        "reobserved": reobserved,
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
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else {"status": "stageb_gap_detection_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_gap_detection_cycle(con)
    except Exception as exc:
        result = {"status": "stageb_gap_detection_error", "error": type(exc).__name__ + ":" + str(exc)}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_gap_detection_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_gap_detection_release = True
    return AutonomousLoop
