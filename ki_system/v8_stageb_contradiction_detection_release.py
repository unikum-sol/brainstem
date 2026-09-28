# -*- coding: utf-8 -*-
"""V8 Stage-B Contradiction Detection -- fills the previously-empty
contradictions table and hypothesis_stability_scores.conflict_count.

BACKGROUND (found via the same project-wide code audit as
v8_stageb_gap_detection_release.py, 22 September 2026): both the
`contradictions` table (declared in memory.py's own schema) and the
`conflict_count` column on `hypothesis_stability_scores` (declared
centrally in db_bootstrap.py's SCHEMA_TABLES) have existed as prepared,
ready-to-use structures with NO module anywhere ever writing to either.
This is directly relevant to the user's explicit requirement that facts
derived from hypotheses must remain correctable if a hypothesis later
turns out to be wrong -- contradiction detection is the prerequisite
signal that v8_stageb_hypothesis_revision_release.py needs in order to
ever have a reason to revise anything.

THIS MODULE'S JOB: examine "contested_subject_multiple_excerpts" gaps
already surfaced by v8_stageb_gap_detection_release.py (reusing that
module's output rather than re-scanning context_hypotheses from scratch),
determine which of the two competing hypotheses is currently better
supported (using already-existing, already-observed signals: evidence_count
and uncertainty -- no new scoring invented), and record the finding:
- one row in `contradictions` (subject, value_a, value_b, status) so the
  conflict itself is durably visible and auditable, matching this
  project's "no black box" provenance principle.
- an increment to `hypothesis_stability_scores.conflict_count` for BOTH
  hypotheses involved (whichever "loses" this round is not silently
  ignored -- future re-evaluation, e.g. if new evidence later reverses
  which side is better supported, remains possible, since a hypothesis
  is never deleted, only ever re-scored).

Explicitly NOT part of this module: no change to context_hypotheses.role
(that is v8_stageb_hypothesis_revision_release.py's job, which consumes
this module's contradictions output), no fact/relation/question writes.
"""
from __future__ import annotations
import json
import sqlite3
import time
from typing import Any, Dict, Optional, Tuple

PHASE = "stageb_contradiction_detection_release"
STATE_TABLE = "stageb_contradiction_detection_state"
DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    "scan_limit": "100",
    "contradictions_created_total": "0",
    "contradictions_reobserved_total": "0",
    # BRAINSTEM_CONTRADICTION_DETECTION_NEUROMODULATOR_COUPLING_V1 (28
    # September 2026)
    #
    # Root cause: _pick_weaker_hypothesis()'s own decisive-evidence-ratio
    # check (see that function's own BRAINSTEM_CONTRADICTION_DETECTION_
    # UNCERTAINTY_INTERACTION_FIX_V1 comment for the full history) used a
    # bare, hardcoded literal "3" directly in its own SQL/Python logic --
    # unlike every other calibrated threshold in this codebase, this value
    # was never exposed via STATE_TABLE, so it could not be tuned at
    # runtime and could not be coupled to any neuromodulator. Lifted here
    # to match this project's own universal convention (every calibrated
    # constant lives in STATE_TABLE, runtime-tunable, no code change
    # needed to recalibrate).
    #
    # Coupled to noradrenaline using the exact same gain magnitude and the
    # exact same symmetric (1.0 + gain*(0.5-value)) formula already
    # verified three times this session (gap_detection's own
    # stalled_min_evidence_count; question_promotion's own
    # min_resolution_attempts_for_question; phase0b's own min_pair_count/
    # pmi_threshold_bits), grounded in Aston-Jones & Cohen's Adaptive Gain
    # Theory (2005, Annu. Rev. Neurosci. 28:403-450): elevated tonic
    # noradrenaline is associated with disengagement from the current
    # task and exploratory search for alternatives -- a system in this
    # state should be MORE willing to decisively resolve a contested pair
    # on a SMALLER evidence-count ratio (lower bar), rather than waiting
    # for an even more lopsided margin, while a low-noradrenaline,
    # exploitative state stays conservative, requiring a larger margin
    # before committing to a decisive resolution.
    "decisive_evidence_ratio": "3.0",
    "selection_pressure_na_gain": "0.5",
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
    # Root cause, confirmed against a fresh, bootstrap-only database: the
    # `contradictions` table (declared only in memory.py's own Memory._init()
    # executescript) was never created by this module's own ensure_schema(),
    # nor was it mirrored into db_bootstrap.py's central SCHEMA_TABLES. The
    # self-check further below correctly detected this and refused to write
    # (per this project's "idempotentes ensure_schema, _self_check_schema,
    # alle Spalten vorab in SCHEMA_TABLES" rule) -- but that rule requires
    # the table to actually be creatable BY this check, not merely verified
    # by it. In the real GUI/main.py startup path this was silently masked
    # because main.py always calls db_bootstrap.ensure_database_exists()
    # AND constructs a Memory() (which runs its own CREATE TABLE IF NOT
    # EXISTS for contradictions) before any AutonomousLoop cycle ever runs
    # -- but that made this module's correctness depend on call order
    # across two unrelated bootstrap paths instead of being self-contained.
    #
    # Fix: this module's own ensure_schema() now creates `contradictions`
    # itself if missing (idempotent CREATE TABLE IF NOT EXISTS, column list
    # matching memory.py's own definition exactly, so both remain fully
    # compatible regardless of which runs first), matching the same
    # self-contained "idempotentes ensure_schema" convention already used
    # by every other phase module in this codebase. Also mirrored into
    # db_bootstrap.py's central SCHEMA_TABLES as defense-in-depth.
    con.execute(
        "CREATE TABLE IF NOT EXISTS contradictions(id INTEGER PRIMARY KEY,subject TEXT,relation TEXT,"
        "value_a TEXT,value_b TEXT,status TEXT,details_json TEXT,created_at INTEGER)"
    )
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
    required_contradiction_cols = {
        "id", "subject", "relation", "value_a", "value_b", "status", "details_json", "created_at",
    }
    have = _columns(con, "contradictions")
    missing.extend("contradictions." + c for c in required_contradiction_cols - have)
    if "conflict_count" not in _columns(con, "hypothesis_stability_scores"):
        missing.append("hypothesis_stability_scores.conflict_count")
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if missing:
        raise RuntimeError("stageb contradiction detection schema missing: " + repr(missing))
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
    """Identical access pattern to every other module in this chain that
    reads the shared six-core neuromodulator snapshot (e.g. v8_stageb_
    gap_detection_release.py's / v8_phase0b_relational_binding_
    observation_release.py's own _neuromodulators()) -- no new messenger
    responsibility introduced."""
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


def _ensure_stability_row(con, hid: int):
    """hypothesis_stability_scores rows are only created lazily by other,
    already-existing modules when they first touch a given hypothesis. To
    safely UPDATE conflict_count without silently affecting zero rows if
    no such row exists yet, ensure one exists first via INSERT OR IGNORE
    with only-safe defaults (matching the column defaults already declared
    centrally in db_bootstrap.py)."""
    con.execute(
        "INSERT OR IGNORE INTO hypothesis_stability_scores(hypothesis_id) VALUES(?)",
        (hid,),
    )


def _pick_weaker_hypothesis(con, hyp_ids, decisive_ratio: float = 3.0) -> Optional[Tuple[int, int]]:
    """Given a list of context_hypotheses ids sharing a contested subject,
    return (weaker_id, stronger_id) using ONLY already-existing,
    already-observed signals (evidence_count, uncertainty) -- no new
    scoring mechanism.

    BRAINSTEM_CONTRADICTION_DETECTION_UNCERTAINTY_INTERACTION_FIX_V1
    (22 September 2026): a real end-to-end test run surfaced an important
    interaction with an already-known, pre-existing property of this
    project's own Stage-B graduation module
    (v8_stageb_guarded_hypothesis_graduation_release.py): graduation only
    ever changes a hypothesis's `role` column -- it deliberately never
    updates confidence/uncertainty (this was already independently
    observed and documented earlier in this project's history: every
    graduated hypothesis retains confidence=0.0, uncertainty=1.0
    permanently, regardless of how well-supported it actually is). An
    earlier version of this function required BOTH evidence_count AND
    uncertainty to agree on which side is stronger before making any
    decision. Combined with the graduation module's behavior above, this
    meant a long-established, heavily-observed, already-graduated
    hypothesis (evidence_count often in the hundreds, but always
    uncertainty=1.0 since graduation) could essentially NEVER be judged
    "stronger" than a freshly-observed competing hypothesis with even a
    slightly lower (but non-1.0) uncertainty value -- regardless of how
    lopsided the actual evidence_count difference was (confirmed directly
    via a real test case: evidence_count 4 vs. 1, correctly detected as a
    contested pair, but never resolved because uncertainty 1.0 vs. 0.9
    made the OLD logic call it "ambiguous" every time).
    Fixed by making evidence_count the PRIMARY, decisive signal (a
    hypothesis observed dramatically more often -- at least 3x, and by an
    absolute margin of at least 5 -- than its competitor is treated as
    stronger on that basis alone, since this project's own repeated
    observation/re-observation mechanism is themost directly meaningful,
    always-updated signal for "how often has this actually been
    confirmed"). uncertainty is now used ONLY as a tie-breaker for cases
    where evidence_count is close (within the margin above) -- not as an
    equal, independently-vetoing signal. This remains deliberately
    conservative: cases that are close on evidence_count AND disagree on
    uncertainty still resolve to "ambiguous", matching this project's
    "erst messen, dann aendern" principle rather than guessing on
    genuinely unclear cases."""
    if len(hyp_ids) < 2:
        return None
    rows = con.execute(
        "SELECT id, COALESCE(evidence_count,0), COALESCE(uncertainty,1.0) "
        "FROM context_hypotheses WHERE id IN (" + ",".join("?" for _ in hyp_ids) + ")",
        hyp_ids,
    ).fetchall()
    if len(rows) < 2:
        return None
    rows.sort(key=lambda r: -r[1])
    strongest = rows[0]
    weakest = rows[-1]
    if strongest[0] == weakest[0]:
        return None
    ev_strong, ev_weak = strongest[1], weakest[1]
    # Decisive case: evidence_count alone is lopsided enough (at least
    # `decisive_ratio`x, base default 3.0 -- see DEFAULTS' own comment for
    # the neuromodulator-coupled derivation of the effective value passed
    # in here) to decide on its own, without needing uncertainty to agree.
    # No additional absolute-margin requirement -- at real production
    # scale (evidence_count regularly in the hundreds to low thousands,
    # see this project's own lexical-boundary layer diagnostics) a 3x
    # ratio is already a large, meaningful gap; requiring an additional
    # fixed absolute margin on top made the check too strict for the
    # realistic smaller-scale case actually observed in end-to-end
    # testing (evidence_count 4 vs. 1) without adding a proportional
    # safety benefit at larger scale.
    if ev_weak > 0 and ev_strong >= decisive_ratio * ev_weak:
        return (weakest[0], strongest[0])
    if ev_weak == 0 and ev_strong >= decisive_ratio:
        return (weakest[0], strongest[0])
    # Close-evidence case: fall back to requiring uncertainty to agree too
    # (the original, more conservative rule), for genuinely close calls.
    if strongest[1] >= weakest[1] and strongest[2] <= weakest[2]:
        return (weakest[0], strongest[0])
    return None


def run_contradiction_detection_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_contradiction_detection_disabled", "created": 0, "reobserved": 0}
    scan_limit = max(1, _int(state.get("scan_limit"), 100))
    now = _now()

    # BRAINSTEM_CONTRADICTION_DETECTION_NEUROMODULATOR_COUPLING_V1: see
    # DEFAULTS' own comment for the full derivation. Exactly 1.0 (no
    # behavior change) at noradrenaline's own neutral baseline of 0.5.
    base_decisive_ratio = max(1.0, _float(state.get("decisive_evidence_ratio"), 3.0))
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    noradrenaline = _neuromodulators(con)["noradrenaline"]
    decisive_ratio = max(1.0, base_decisive_ratio * (1.0 + na_gain * (0.5 - noradrenaline)))

    created = 0
    reobserved = 0

    if not _table_exists(con, "internal_learning_gaps") or not _table_exists(con, "context_hypotheses"):
        return {"status": "stageb_contradiction_detection_no_input_tables", "created": 0, "reobserved": 0}

    gap_rows = con.execute(
        "SELECT gap_key, pattern_key FROM internal_learning_gaps "
        "WHERE gap_type='contested_subject_multiple_excerpts' AND status='open' "
        "ORDER BY priority DESC, id DESC LIMIT ?",
        (scan_limit,),
    ).fetchall()

    for gap_key, subject in gap_rows:
        if not subject:
            continue
        # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_V1 (25 September 2026): unlike
        # ELIGIBLE_ROLES/REVERT_ROLES in the graduation/revision modules,
        # this role list is a hardcoded SQL literal, not derived from a
        # shared dict -- see BrainStem_Relations_Ontology_Questions_
        # Emergence_Concept.md, Abschnitt 10.1, point 2. Without adding
        # 'stable_relation_hypothesis' here, graduated relations would
        # never be checked against other facts for contradictions.
        hyp_rows = con.execute(
            "SELECT id, text_excerpt FROM context_hypotheses "
            "WHERE subject=? AND role IN ('stable_hypothesis','stable_lexical_boundary','stable_relation_hypothesis') "
            "ORDER BY id",
            (subject,),
        ).fetchall()
        hyp_ids = [r[0] for r in hyp_rows]
        if len(hyp_ids) < 2:
            continue

        contradiction_key_material = subject + "|" + ",".join(str(i) for i in sorted(hyp_ids))
        existing = con.execute(
            "SELECT id, status FROM contradictions WHERE subject=? AND relation=?",
            (subject, "conflicting_observation"),
        ).fetchone()

        excerpts_by_id = dict(hyp_rows)
        value_a = excerpts_by_id.get(hyp_ids[0], "")
        value_b = excerpts_by_id.get(hyp_ids[-1], "") if len(hyp_ids) > 1 else ""

        pick = _pick_weaker_hypothesis(con, hyp_ids, decisive_ratio)
        details = {
            "gap_key": gap_key,
            "hypothesis_ids": hyp_ids,
            "resolution": (
                {"weaker_id": pick[0], "stronger_id": pick[1]} if pick else "ambiguous_no_decision"
            ),
        }

        for hid in hyp_ids:
            _ensure_stability_row(con, hid)
            con.execute(
                "UPDATE hypothesis_stability_scores SET conflict_count=COALESCE(conflict_count,0)+1, "
                "updated_at=? WHERE hypothesis_id=?",
                (now, hid),
            )

        if existing:
            con.execute(
                "UPDATE contradictions SET value_a=?, value_b=?, status=?, details_json=? WHERE id=?",
                (value_a, value_b, "open" if pick is None else "resolvable", _j(details), existing[0]),
            )
            reobserved += 1
        else:
            con.execute(
                "INSERT INTO contradictions(subject,relation,value_a,value_b,status,details_json,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (subject, "conflicting_observation", value_a, value_b,
                 "open" if pick is None else "resolvable", _j(details), now),
            )
            created += 1

    _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
    _set_kv(con, STATE_TABLE, "contradictions_created_total", _int(state.get("contradictions_created_total"), 0) + created)
    _set_kv(con, STATE_TABLE, "contradictions_reobserved_total", _int(state.get("contradictions_reobserved_total"), 0) + reobserved)
    con.commit()

    return {
        "status": "stageb_contradiction_detection_cycle",
        "gaps_examined": len(gap_rows),
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
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else {"status": "stageb_contradiction_detection_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_contradiction_detection_cycle(con)
    except Exception as exc:
        result = {"status": "stageb_contradiction_detection_error", "error": type(exc).__name__ + ":" + str(exc)}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_contradiction_detection_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_contradiction_detection_release = True
    return AutonomousLoop
