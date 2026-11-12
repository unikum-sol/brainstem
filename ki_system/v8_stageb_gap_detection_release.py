# -*- coding: utf-8 -*-
"""THIS MODULE'S JOB: produce plausible, genuinely-motivated candidate gaps
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
    "scan_limit": "200",
    "contested_scan_per_cycle": "50",
    "contested_scan_cursor": "0",
    # A hypothesis is only considered "stalled" (gap type
    # "stalled_uncertain_hypothesis") if it has been observed at least this
    # many times without yet graduating -- avoids flagging brand-new,
    # simply-not-yet-consolidated hypotheses as gaps.
    "stalled_min_evidence_count": "20",
    # Literatur: Hochner et al. 1986; Cohen et al. 1997
    "selection_pressure_na_gain": "0.5",
    # Literatur: Kang et al. 2009; Ten et al. 2025; Ueda et al. 2021
    "habituation_max_stagnant_cycles": "64",
    # Literatur: Hochner et al. 1986; Cohen et al. 1997
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
    # Literatur: Ueda et al. 2021; Smart et al. 2026
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
        "AND evidence_count >= ? "
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


def _revision_generation(con, hypothesis_id) -> int:
    """How often this hypothesis has already been revised. Part of the
    contested gap's identity so a hypothesis that lost a competition, later
    re-consolidated and again meets a competitor raises a NEW gap instead of
    hitting its old, already-closed one."""
    if not _table_exists(con, "hypothesis_revisions"):
        return 0
    row = con.execute("SELECT COUNT(*) FROM hypothesis_revisions WHERE hypothesis_id=?",
                      (hypothesis_id,)).fetchone()
    return _int(row[0] if row else 0, 0)


def _detect_contested_pairs(con, scan_limit, now, habituation_max=64, acetylcholine=0.5) -> Dict[str, int]:
    """A stable (consolidated) sentence hypothesis is retrieved by a LEARNED
    partial cue (prefix ending at a boundary the Phase-0 lexical layer
    learned itself, covering an acetylcholine-dependent fraction of the
    pattern). Every other observed completion of that same cue that differs
    from the stored pattern is a competitor; their coexistence is a gap
    ("contested_subject_multiple_excerpts", gap type name kept for the
    downstream contradiction/question modules). This module does not decide
    who is right -- v8_stageb_contradiction_detection_release.py does, from
    evidence only. See v8_cue_competition.py for the neuroscience grounding
    (pattern completion, retrieval competition, prediction error, ACh
    separation/completion balance).
    """
    from ki_system import v8_cue_competition as cue_comp
    created = reobserved = no_cue = no_competitor = 0
    if not _table_exists(con, "context_hypotheses"):
        return {"created": 0, "reobserved": 0}
    cols = _columns(con, "context_hypotheses")
    if not {"subject", "role", "text_excerpt"}.issubset(cols):
        return {"created": 0, "reobserved": 0}
    state = _read_kv(con, STATE_TABLE)
    per_cycle = max(1, min(scan_limit, _int(state.get("contested_scan_per_cycle"), 50)))
    cursor = _int(state.get("contested_scan_cursor"), 0)
    rows = con.execute(
        "SELECT id, text_excerpt, uncertainty FROM context_hypotheses "
        "WHERE role='stable_hypothesis' AND COALESCE(status,'active')='active' AND id>? "
        "ORDER BY id LIMIT ?",
        (cursor, per_cycle),
    ).fetchall()
    if len(rows) < per_cycle and cursor > 0:
        rows += con.execute(
            "SELECT id, text_excerpt, uncertainty FROM context_hypotheses "
            "WHERE role='stable_hypothesis' AND COALESCE(status,'active')='active' AND id<=? "
            "ORDER BY id LIMIT ?",
            (cursor, per_cycle - len(rows)),
        ).fetchall()
    last_id = cursor
    for hid, excerpt, unc in rows:
        last_id = hid
        cue = cue_comp.learned_cue(con, excerpt or "", acetylcholine)
        if not cue:
            no_cue += 1
            continue
        comps = cue_comp.competitors(con, cue, hid, excerpt or "", limit=3)
        if not comps:
            no_competitor += 1
            continue
        gap_key = "contested:" + str(hid) + ":g" + str(_revision_generation(con, hid))
        priority = min(1.0, 0.3 + 0.1 * len(comps))
        severity = priority
        decision = _upsert_gap(
            con, gap_key, "contested_subject_multiple_excerpts",
            "learned_cue_competing_completion", "stable_hypothesis",
            priority, severity, hid, _float(unc, 1.0), cue, int(comps[0][2]), now,
            habituation_max,
        )
        if decision == "created":
            created += 1
        else:
            reobserved += 1
    _set_kv(con, STATE_TABLE, "contested_scan_cursor", last_id)
    return {"created": created, "reobserved": reobserved, "scanned": len(rows),
            "no_learned_cue": no_cue, "no_competitor": no_competitor}


def run_gap_detection_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_gap_detection_disabled", "created": 0, "reobserved": 0}
    scan_limit = max(1, _int(state.get("scan_limit"), 200))
    base_min_evidence = max(1, _int(state.get("stalled_min_evidence_count"), 20))
    base_habituation_max = max(1, _int(state.get("habituation_max_stagnant_cycles"), 64))
    now = _now()

    neuromod = _neuromodulators(con)
    na = neuromod["noradrenaline"]
    serotonin = neuromod["serotonin"]
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    serotonin_gain = _float(state.get("selection_pressure_serotonin_gain"), 0.5)

    min_evidence = max(1, round(base_min_evidence * (1.0 + na_gain * (0.5 - na))))
    habituation_max = max(1, round(base_habituation_max * (1.0 + serotonin_gain * (serotonin - 0.5))))

    stalled = _detect_stalled_hypotheses(con, scan_limit, min_evidence, now, habituation_max)
    contested = _detect_contested_pairs(con, scan_limit, now, habituation_max,
                                        acetylcholine=neuromod.get("acetylcholine", 0.5))

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
