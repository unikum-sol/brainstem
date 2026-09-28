# -*- coding: utf-8 -*-
"""V8 Stage-B Question Promotion -- Modul C, Slice 3 (Fragen-Emergenz,
Neugier aus Informationsluecken).

Full concept: see BrainStem_Relations_Ontology_Questions_Emergence_Concept.md,
Abschnitt 4 (Modul C) and Abschnitt 10 (integration).

WHAT THIS MODULE DOES, AND WHY IT NEEDS NO NEW OBSERVATION MODULE
------------------------------------------------------------------
Unlike Modul A (Relations) and Modul B (Ontologie), Questions Slice 3 needs
NO new context_hypotheses role, NO new Stage-B graduation-gate entry, and NO
change to v8_stageb_guarded_hypothesis_graduation_release.py / v8_stageb_
hypothesis_revision_release.py / v8_stageb_contradiction_detection_release.py.
The reason (Abschnitt 4.2): BrainStem already has the exact biological
precursor Loewenstein's Information-Gap-Theory of curiosity (1994) requires
-- a "specific, already-known-to-the-system" gap -- in the shape of
internal_learning_gaps, already produced by v8_stageb_gap_detection_release.
py. A question is therefore not a new kind of observation; it is the
introspective, durably-confirmed restatement of an ALREADY-EXISTING gap.
This module only ever READS internal_learning_gaps and context_hypotheses
(never writes either) and writes exclusively to `questions` plus its own
small state/event tables.

REAL BUG FOUND AND FIXED IN THE OWNING MODULE (not this one), REQUIRED FOR
THIS MODULE TO EVER PROMOTE ANYTHING
----------------------------------------------------------------------------
A project-wide audit (grep across all ~63 modules) confirmed that
internal_learning_gaps.resolution_attempts -- the exact column the concept
document's Abschnitt 4.2/10.3 named as the persistence gate ("resolution_
attempts hoch") -- was declared and READ (v8_phase5b) but never WRITTEN by
any module, including v8_stageb_gap_detection_release.py, the sole owner of
a gap's lifecycle row. It silently stayed at its schema default of 0
forever. This has now been fixed at the root, in v8_stageb_gap_detection_
release.py's own reobservation branch (see that file's own
BRAINSTEM_GAP_RESOLUTION_ATTEMPTS_DEAD_COLUMN_FIX_V1 comment): each time an
already-known gap is reconfirmed as still open in a later, independent
gap-detection cycle, resolution_attempts is now incremented by 1. This
module's persistence gate below is only meaningful because of that fix.

FOLLOW-UP FIX (BRAINSTEM_GAP_CLOSURE_AND_HABITUATION_V1, 25 September
2026): at first delivery, this module's own _retract_resolved_gaps()
below was real but permanently dormant, since no module ever moved a
gap's status away from 'open' either. This is now fixed too: fact/
relation promotion close a gap when its own hypothesis graduates, and
gap_detection itself now retires (habituates) a gap after sustained,
evidence-free stagnation -- see _retract_resolved_gaps()'s own updated
docstring below for the full mechanism.

internal_learning_gaps.resolution_score is, as of this delivery, a SEPARATE,
still-real limitation, deliberately NOT fixed here (out of this slice's
scope; fixing it would mean giving some currently-unrelated module a new,
unrequested responsibility for scoring gap-closure quality on this specific
table): no module anywhere writes it for internal_learning_gaps rows either,
so it remains permanently 0 for every gap. The "resolution_score niedrig"
half of the concept's original gate is consequently, at this time, ALWAYS
true and contributes no discriminative power -- kept in the query below
purely for forward compatibility (harmless today, becomes meaningful the
moment some future module starts writing a real value there), and disclosed
transparently in this delivery's audit report rather than silently ignored.

QUESTION TEXT: A FIXED, HONEST SYSTEM MARKER, NOT A GENERATED SENTENCE
------------------------------------------------------------------------
Per the concept's own "keine vorab vorgegebene Satzschablone" requirement,
this module does NOT generate a natural-language interrogative sentence
(that would require hand-authored grammar/vocabulary -- e.g. inserting
"Was ist" / "What is" -- which is exactly what this project's "keine
Wortlisten, keine Grammatik" principle forbids). Instead it mirrors the
already-established, already-endorsed pattern of v8_stageb_fact_promotion_
release.py's fixed relation label "observed_as" and v8_stageb_ontology_
promotion_release.py's fixed relation label "is_a": a fixed, explicit,
non-linguistic marker prefix, followed ONLY by already-observed, real
surface text taken verbatim from the referenced hypothesis/hypotheses. This
is a genuine design decision, not fully spelled out at this level of detail
in the concept document -- flagged as an open point for review in this
slice's audit report.
"""
from __future__ import annotations
import json
import time
from typing import Any, Dict, Optional, Tuple

PHASE = "stageb_question_promotion_release"
STATE_TABLE = "stageb_question_promotion_state"
EVENTS_TABLE = "stageb_question_promotion_events"

# Deliberately conservative starting defaults, pending real calibration
# (see this slice's own audit report, "Threshold Calibration" section) --
# all tunable at runtime via STATE_TABLE key/value rows, no code change
# needed to recalibrate, matching every other Stage-B/Phase0(b) module's
# own convention.
DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    # How many newly-eligible gaps this module may promote to a question
    # per real cycle. Deliberately its OWN, independent budget -- a direct
    # audit confirmed there is no shared scarce resource between question
    # promotion and hypothesis graduation / relation promotion / ontology
    # promotion: questions are drawn from internal_learning_gaps, an
    # entirely separate pool that none of the other three promotion paths
    # ever reads from or writes to. Mirrors v8_stageb_ontology_promotion_
    # release.py's own BRAINSTEM rationale for its independent budget.
    "question_promotion_budget": "1",
    # Persistence gate (Abschnitt 4.2's "ueber mehrere Zyklen hinweg nicht
    # geschlossen"): minimum number of INDEPENDENT gap-detection cycles that
    # must have reconfirmed a gap as still open before it is durable enough
    # to motivate a question, matching Loewenstein's requirement that
    # curiosity responds to a specific, repeatedly-noticed gap, not a
    # single fleeting observation.
    #
    # NOT set to 3 (this project's superficially-obvious other "≥3
    # reconfirmations" convention, e.g. Phase-7d hypothesis graduation,
    # v8_stageb_ontology_cluster_observation_release.py's stability_streak_
    # required=3) -- a real, instrumented 50-cycle calibration run (see
    # this slice's own audit report, "Threshold Calibration" section)
    # measured that v8_stageb_gap_detection_release.py's own resolution_
    # attempts counter increments UNCONDITIONALLY on every single
    # AutonomousLoop.cycle(), whereas Phase-7d's "3 survived cycles" only
    # count cycles where the slow-wave-sleep substructure actually ran
    # (gated by the cooperative sleep/wake authority, empirically ~60% of
    # cycles in bursts during that same run, and gated off entirely during
    # sustained wake). A raw value of 3 is therefore NOT the same amount of
    # real persistence as Phase-7d's 3 -- it was crossed within 3 cycles of
    # gap creation in the calibration run, i.e. a few seconds, making the
    # gate nearly a pass-through rather than a genuine "durably confirmed"
    # filter. The same run also measured the system's own sleep/wake
    # rhythm period directly: sleep bursts of 10 cycles separated by wake
    # gaps of 6 cycles, i.e. a ~16-cycle full rhythm period. 15 is chosen
    # so that a gap must persist across at least one complete measured
    # sleep/wake rhythm, not merely within the single burst it was first
    # noticed in -- a real, measured, non-arbitrary number, while still
    # comfortably reachable well within this project's real production
    # cadence (11,500+ cycles). Runtime-tunable, no code change needed to
    # recalibrate against the real 167k-chunk production corpus per the
    # project's own validation-plan convention (Abschnitt 10.6) -- the
    # sleep/wake rhythm period itself is corpus- and load-dependent and
    # should be re-measured there before this default is trusted long-term.
    "min_resolution_attempts_for_question": "15",
    # BRAINSTEM_QUESTION_PROMOTION_NEUROMODULATOR_COUPLING_V1 (28 September
    # 2026)
    #
    # Root cause: this module's own existence gate above (the calibrated
    # base value 15) was, until this delivery, entirely neuromodulator-
    # blind -- unlike v8_stageb_gap_detection_release.py's own existence
    # gate (stalled_min_evidence_count), which this same session already
    # coupled to noradrenaline. Fixed here by applying the EXACT SAME,
    # already-verified formula and reasoning: Aston-Jones & Cohen's
    # Adaptive Gain Theory (2005, Annu. Rev. Neurosci. 28:403-450)
    # describes tonic locus-coeruleus noradrenaline as active "when
    # utility in the task wanes", associated with disengagement from the
    # current task and exploratory search for alternatives -- a system in
    # this state should be MORE receptive to promoting a still-tentative
    # gap into a full question (lower persistence bar), while a low-
    # noradrenaline, exploitative state stays focused, requiring a gap to
    # have persisted longer before it earns a question. Deliberately
    # reuses the SAME gain magnitude and the SAME symmetric
    # (1.0 + gain*(0.5-value)) formula already verified in gap_detection.py
    # (bidirectional baseline-invariance + direction tests), rather than
    # inventing a second, independent convention for what is functionally
    # the same kind of existence gate one stage further down this chain.
    "selection_pressure_na_gain": "0.5",
    # See module docstring: resolution_score is currently always 0 for
    # every internal_learning_gaps row (no writer exists yet), so this
    # threshold is presently non-discriminative. Kept, not removed, for
    # forward compatibility and because a "low resolution_score" gate is
    # still the scientifically correct condition per Loewenstein/Golman &
    # Loewenstein 2016's "the gap must still be open", once some future
    # module begins writing real values here.
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
    # Defense-in-depth, mirroring the exact convention already established
    # by v8_stageb_relation_promotion_release.py / v8_stageb_ontology_
    # promotion_release.py's own ensure_schema(): add the column this
    # module needs itself if missing, in addition to it already being
    # mirrored into db_bootstrap.py's central SCHEMA_TABLES.
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
    """Re-reads context_hypotheses for a second, still-stable hypothesis
    sharing the same subject as the gap's own recorded hypothesis_id --
    exactly the same subject-match criterion v8_stageb_gap_detection_
    release.py's own _detect_contested_pairs() already used to create this
    gap in the first place. This re-reads already-established, already-
    stable data at promotion time (the same principle v8_stageb_relation_
    promotion_release.py already applies when re-reading a hypothesis's
    own subject/relation_hint/object fields), it does not introduce any
    new judgment about which pair is contested."""
    if not subject or not _table_exists(con, "context_hypotheses"):
        return None
    row = con.execute(
        "SELECT text_excerpt FROM context_hypotheses "
        "WHERE subject=? AND id<>? AND role IN ('stable_hypothesis','stable_lexical_boundary') "
        "ORDER BY id ASC LIMIT 1",
        (subject, exclude_id),
    ).fetchone()
    if row is None:
        return None
    return (row[0] or "").strip()


def _question_text_for_gap(con, gap_type: str, hypothesis_id: Optional[int],
                            pattern_key: Optional[str]) -> Optional[str]:
    """See module docstring: fixed, explicit, non-linguistic marker prefix
    + verbatim, already-observed surface text only. No generated sentence,
    no grammar, no word list."""
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
    # BRAINSTEM_QUESTION_PROMOTION_NEUROMODULATOR_COUPLING_V1: see the
    # DEFAULTS block's own comment for selection_pressure_na_gain for the
    # full derivation. Exactly 1.0 (no behavior change) at noradrenaline's
    # own neutral baseline of 0.5.
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
    """BRAINSTEM_GAP_CLOSURE_AND_HABITUATION_V1 (25 September 2026) update:
    at the time this module was first delivered, no module anywhere ever
    moved a gap's status away from 'open', making this function real but
    permanently dormant in live operation (see the Slice 3 audit report's
    disclosed limitation). This is now fixed at the source: v8_stageb_
    fact_promotion_release.py and v8_stageb_relation_promotion_release.py
    each now set a gap's status to 'closed' at their own existing
    promotion write point, right when the gap's own hypothesis_id
    graduates into a durable fact/relation; v8_stageb_gap_detection_
    release.py's own habituation mechanism separately moves a gap's status
    to 'habituated' after sustained, evidence-free stagnation. Both are
    now real, reachable status transitions in production, so this
    function's poll (rather than an event-log reaction -- still no
    dedicated gap-closure event log exists, unlike hypothesis_revisions
    for facts/relations) is no longer dormant. Any already-promoted,
    still-open question whose source gap has either disappeared or moved
    to a status outside the eligible open/persistent set (i.e. 'closed' or
    'habituated') is marked resolved -- never deleted, preserving the
    full, reconstructable history exactly like every other retraction
    path in this project."""
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
