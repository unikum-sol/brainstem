# -*- coding: utf-8 -*-
"""Stage-B contradiction detection: decides cue competitions.

For every open contested gap -- a consolidated sentence hypothesis and the
strongest competing completion of its learned cue (see v8_cue_competition.py)
-- the competition is decided from repetition evidence only (_decide_competition).
A decisively stronger competitor is a prediction error against the stored
memory; the contradiction becomes 'resolvable' and the revision module
destabilizes the stored pattern. The decisive evidence ratio is scaled by
noradrenaline. Unverified surface contrasts from semantic_evidence are recorded
as well but are never resolved automatically.

Literatur: Sevenster, Beckers & Kindt 2013; Yu & Dayan 2005; Aston-Jones & Cohen 2005
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
    from ki_system.semantic_evidence import ensure_schema as ensure_evidence
    ensure_evidence(con)
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
    con.execute(
        "INSERT OR IGNORE INTO hypothesis_stability_scores(hypothesis_id) VALUES(?)",
        (hid,),
    )


def _decide_competition(ev_stored: int, ev_competitor: int, decisive_ratio: float) -> str:
    """Decide stored pattern vs. strongest competing completion of its cue.

    - 'resolvable': competitor >= decisive_ratio x stored evidence
      (prediction error -> the stored pattern is destabilized);
    - 'confirmed': stored >= decisive_ratio x competitor evidence;
    - 'open': neither side is decisively ahead; nothing is forced.
    """
    ev_s = max(0, int(ev_stored or 0))
    ev_c = max(0, int(ev_competitor or 0))
    if ev_c >= decisive_ratio * max(1, ev_s):
        return "resolvable"
    if ev_s >= decisive_ratio * max(1, ev_c):
        return "confirmed"
    return "open"


def run_contradiction_detection_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_contradiction_detection_disabled", "created": 0, "reobserved": 0}
    from ki_system.semantic_evidence import discover_text_contrasts
    text_contrasts = discover_text_contrasts(con)
    scan_limit = max(1, _int(state.get("scan_limit"), 100))
    now = _now()

    base_decisive_ratio = max(1.0, _float(state.get("decisive_evidence_ratio"), 3.0))
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    noradrenaline = _neuromodulators(con)["noradrenaline"]
    decisive_ratio = max(1.0, base_decisive_ratio * (1.0 + na_gain * (0.5 - noradrenaline)))

    created = 0
    reobserved = 0

    if not _table_exists(con, "internal_learning_gaps") or not _table_exists(con, "context_hypotheses"):
        return {"status": "stageb_contradiction_detection_no_input_tables", "created": 0, "reobserved": 0}

    from ki_system import v8_cue_competition as cue_comp
    gap_rows = con.execute(
        "SELECT gap_key, pattern_key, hypothesis_id FROM internal_learning_gaps "
        "WHERE gap_type='contested_subject_multiple_excerpts' AND status='open' "
        "ORDER BY priority DESC, id DESC LIMIT ?",
        (scan_limit,),
    ).fetchall()
    decisions = {"resolvable": 0, "confirmed": 0, "open": 0}

    for gap_key, cue, stored_id in gap_rows:
        if not cue or stored_id is None:
            continue
        stored = con.execute(
            "SELECT id, text_excerpt, COALESCE(evidence_count,0), role FROM context_hypotheses WHERE id=?",
            (stored_id,),
        ).fetchone()
        if stored is None or stored[3] != "stable_hypothesis":
            continue
        comps = cue_comp.competitors(con, cue, stored[0], stored[1] or "", limit=3)
        if not comps:
            continue
        top = comps[0]
        status = _decide_competition(stored[2], top[2], decisive_ratio)
        decisions[status] += 1
        details = {
            "gap_key": gap_key,
            "cue": cue,
            "hypothesis_ids": [stored[0]] + [c[0] for c in comps],
            "evidence": {"stored": stored[2], "competitor": top[2]},
            "decisive_ratio": round(decisive_ratio, 4),
            "resolution": (
                {"weaker_id": stored[0], "stronger_id": top[0]} if status == "resolvable"
                else ({"weaker_id": top[0], "stronger_id": stored[0], "action": "none_prediction_confirmed"}
                      if status == "confirmed" else "ambiguous_no_decision")
            ),
        }
        for hid in (stored[0], top[0]):
            _ensure_stability_row(con, hid)
            con.execute(
                "UPDATE hypothesis_stability_scores SET conflict_count=COALESCE(conflict_count,0)+1, "
                "updated_at=? WHERE hypothesis_id=?",
                (now, hid),
            )
        existing = con.execute(
            "SELECT id, status FROM contradictions WHERE subject=? AND relation=?",
            (gap_key, "conflicting_observation"),
        ).fetchone()
        if existing:
            if existing[1] == "resolved":
                continue
            con.execute(
                "UPDATE contradictions SET value_a=?, value_b=?, status=?, details_json=? WHERE id=?",
                (stored[1], top[1], status, _j(details), existing[0]),
            )
            reobserved += 1
        else:
            con.execute(
                "INSERT INTO contradictions(subject,relation,value_a,value_b,status,details_json,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (gap_key, "conflicting_observation", stored[1], top[1], status, _j(details), now),
            )
            created += 1

    _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
    _set_kv(con, STATE_TABLE, "contradictions_created_total", _int(state.get("contradictions_created_total"), 0) + created)
    _set_kv(con, STATE_TABLE, "contradictions_reobserved_total", _int(state.get("contradictions_reobserved_total"), 0) + reobserved)
    con.commit()

    return {
        "status": "stageb_contradiction_detection_cycle",
        "gaps_examined": len(gap_rows),
        "unverified_text_contrasts": text_contrasts,
        "created": created,
        "reobserved": reobserved,
        "decisions": decisions,
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
