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
    "gaps_created_total": "0",
    "gaps_reobserved_total": "0",
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


def _upsert_gap(con, gap_key, gap_type, gap_reason, role, priority, severity,
                 hypothesis_id, uncertainty, pattern_key, evidence_count, now):
    existing = con.execute(
        "SELECT id, evidence_count FROM internal_learning_gaps WHERE gap_key=?",
        (gap_key,),
    ).fetchone()
    if existing:
        gid, prior_ev = existing
        con.execute(
            "UPDATE internal_learning_gaps SET priority=?, severity=?, uncertainty=?, "
            "evidence_count=?, updated_at=? WHERE id=?",
            (priority, severity, uncertainty, max(int(prior_ev or 0), evidence_count), now, gid),
        )
        return "reobserved"
    con.execute(
        "INSERT INTO internal_learning_gaps(gap_key,gap_type,gap_reason,role,priority,"
        "severity,hypothesis_id,uncertainty,pattern_key,status,resolution_score,"
        "evidence_count,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (gap_key, gap_type, gap_reason, role, priority, severity, hypothesis_id,
         uncertainty, pattern_key, "open", 0.0, evidence_count, now, now),
    )
    return "created"


def _detect_stalled_hypotheses(con, scan_limit, min_evidence, now) -> Dict[str, int]:
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
            hid, unc, pattern_key, ev, now,
        )
        if decision == "created":
            created += 1
        else:
            reobserved += 1
    return {"created": created, "reobserved": reobserved}


def _detect_contested_pairs(con, scan_limit, now) -> Dict[str, int]:
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
    min_evidence = max(1, _int(state.get("stalled_min_evidence_count"), 20))
    now = _now()

    stalled = _detect_stalled_hypotheses(con, scan_limit, min_evidence, now)
    contested = _detect_contested_pairs(con, scan_limit, now)

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
