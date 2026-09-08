# -*- coding: utf-8 -*-
"""BrainStem Non-Productive Real Outcome Observation & Delayed Eligibility Shadow Contract V1.

This phase is intentionally non-productive. It reads canonical hypothesis,
observation and delayed reobservation evidence, and writes only its own shadow
contract tables. It never writes Phase-5i, gaps, attention, facts, relations,
questions, or productive memory/outcome tables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

VERSION = "non_productive_real_outcome_delayed_eligibility_shadow_v1"
PHASE = VERSION
LIMIT = 512
SOURCE_TABLE = "modern_gap_phase5f_shadow_observation_v2_latest"
CANDIDATE_TABLE = "modern_gap_candidate_shadow"
EVENT_TABLE = "context_learning_events"
STABILITY_TABLE = "hypothesis_stability_scores"
READ_TABLE = "reading_queue"
SHADOW_TABLE = "non_productive_real_outcome_observation_shadow"
CYCLE_TABLE = "non_productive_real_outcome_observation_shadow_cycles"
STATE_TABLE = "non_productive_real_outcome_observation_shadow_state"

PROTECTED_TABLES = (
    "facts", "relations", "questions", "internal_learning_gaps",
    "chunk_attention_scores", "phase5f_context_window_experiments",
    "phase5g_strategy_experiments", "phase5g_experiment_outcomes",
    "phase5i_outcome_driven_experiments", "modern_outcome_bridge_shadow",
)

SCHEMA_TABLES = {
    SHADOW_TABLE: [
        "eligibility_key", "stable_observation_key", "shadow_key",
        "hypothesis_id", "baseline_source_updated_at",
        "baseline_projection_fingerprint", "delayed_event_count",
        "delayed_reobservation_count", "first_delayed_event_at",
        "last_delayed_event_at", "stability_available", "stability",
        "real_outcome_observation_available", "non_productive_eligible",
        "eligibility_state", "source_provenance", "missing_signals",
        "productive_write", "details", "first_seen_at", "last_seen_at",
        "version_count",
    ],
    CYCLE_TABLE: [
        "id", "phase", "source_rows_seen", "shadow_rows_created",
        "shadow_rows_updated", "real_outcome_available",
        "non_productive_eligible", "awaiting_delayed_reobservation",
        "awaiting_stability", "checkpoint_updated_at_before",
        "checkpoint_hypothesis_id_before", "checkpoint_updated_at_after",
        "checkpoint_hypothesis_id_after", "protected_before",
        "protected_after", "safety_ok", "mode", "created_at", "details",
    ],
    STATE_TABLE: ["key", "value", "updated_at"],
}


def _now() -> int:
    return int(time.time())


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _q(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    if not _table_exists(con, table):
        return []
    return [str(row[1]) for row in con.execute("PRAGMA table_info(" + _q(table) + ")")]


def _count(con: sqlite3.Connection, table: str) -> Optional[int]:
    if not _table_exists(con, table):
        return None
    return int(con.execute("SELECT COUNT(*) FROM " + _q(table)).fetchone()[0])


def _read_kv(con: sqlite3.Connection, table: str) -> Dict[str, Any]:
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())


def _write_kv(con: sqlite3.Connection, values: Dict[str, Any], now: int) -> None:
    for key, value in values.items():
        con.execute(
            "INSERT INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (str(key), str(value).lower() if isinstance(value, bool) else str(value), now),
        )


def ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS " + SHADOW_TABLE + "("
        "eligibility_key TEXT PRIMARY KEY,"
        "stable_observation_key TEXT NOT NULL,"
        "shadow_key TEXT NOT NULL,"
        "hypothesis_id INTEGER NOT NULL,"
        "baseline_source_updated_at INTEGER NOT NULL DEFAULT 0,"
        "baseline_projection_fingerprint TEXT NOT NULL DEFAULT '',"
        "delayed_event_count INTEGER NOT NULL DEFAULT 0,"
        "delayed_reobservation_count INTEGER NOT NULL DEFAULT 0,"
        "first_delayed_event_at INTEGER,"
        "last_delayed_event_at INTEGER,"
        "stability_available INTEGER NOT NULL DEFAULT 0,"
        "stability REAL,"
        "real_outcome_observation_available INTEGER NOT NULL DEFAULT 0,"
        "non_productive_eligible INTEGER NOT NULL DEFAULT 0,"
        "eligibility_state TEXT NOT NULL,"
        "source_provenance TEXT NOT NULL DEFAULT '{}',"
        "missing_signals TEXT NOT NULL DEFAULT '[]',"
        "productive_write INTEGER NOT NULL DEFAULT 0,"
        "details TEXT NOT NULL DEFAULT '{}',"
        "first_seen_at INTEGER NOT NULL,"
        "last_seen_at INTEGER NOT NULL,"
        "version_count INTEGER NOT NULL DEFAULT 1)"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS " + CYCLE_TABLE + "("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,phase TEXT NOT NULL,"
        "source_rows_seen INTEGER NOT NULL DEFAULT 0,"
        "shadow_rows_created INTEGER NOT NULL DEFAULT 0,"
        "shadow_rows_updated INTEGER NOT NULL DEFAULT 0,"
        "real_outcome_available INTEGER NOT NULL DEFAULT 0,"
        "non_productive_eligible INTEGER NOT NULL DEFAULT 0,"
        "awaiting_delayed_reobservation INTEGER NOT NULL DEFAULT 0,"
        "awaiting_stability INTEGER NOT NULL DEFAULT 0,"
        "checkpoint_updated_at_before INTEGER NOT NULL DEFAULT 0,"
        "checkpoint_hypothesis_id_before INTEGER NOT NULL DEFAULT 0,"
        "checkpoint_updated_at_after INTEGER NOT NULL DEFAULT 0,"
        "checkpoint_hypothesis_id_after INTEGER NOT NULL DEFAULT 0,"
        "protected_before TEXT NOT NULL DEFAULT '{}',"
        "protected_after TEXT NOT NULL DEFAULT '{}',"
        "safety_ok INTEGER NOT NULL DEFAULT 0,mode TEXT NOT NULL DEFAULT 'shadow',"
        "created_at INTEGER NOT NULL,details TEXT NOT NULL DEFAULT '{}')"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS " + STATE_TABLE + "("
        "key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at INTEGER NOT NULL)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_np_real_outcome_hyp ON "
        + SHADOW_TABLE + "(hypothesis_id,last_seen_at)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_np_real_outcome_state ON "
        + SHADOW_TABLE + "(non_productive_eligible,real_outcome_observation_available,last_seen_at)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_np_real_outcome_checkpoint ON "
        + SHADOW_TABLE + "(baseline_source_updated_at,hypothesis_id)"
    )
    defaults = {
        "phase": PHASE,
        "mode": "shadow",
        "contract": "non_productive_delayed_eligibility",
        "source_table": SOURCE_TABLE,
        "delayed_event_table": EVENT_TABLE,
        "checkpoint_updated_at": "0",
        "checkpoint_hypothesis_id": "0",
        "last_source_rows_seen": "0",
        "last_real_outcome_available": "0",
        "last_non_productive_eligible": "0",
        "productive_writes": "disabled",
        "phase5i_writes": "disabled",
        "productive_gap_writes": "disabled",
        "attention_writes": "disabled",
        "fact_writes": "disabled",
        "relation_writes": "disabled",
        "question_writes": "disabled",
        "causal_effect_claimed": "false",
        "last_safety_ok": "true",
    }
    now = _now()
    for key, value in defaults.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (key, value, now),
        )


def _self_check_schema(con: sqlite3.Connection) -> None:
    for table, expected in SCHEMA_TABLES.items():
        actual = _columns(con, table)
        missing = [column for column in expected if column not in actual]
        if missing:
            raise RuntimeError("Schema missing for " + table + ": " + ", ".join(missing))


def _protected_counts(con: sqlite3.Connection) -> Dict[str, Optional[int]]:
    return {table: _count(con, table) for table in PROTECTED_TABLES}


def _parse_targets(value: Any) -> List[int]:
    if value is None:
        return []
    parsed = value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            parsed = []
    if not isinstance(parsed, list):
        return []
    out = []
    for item in parsed:
        try:
            out.append(int(item))
        except Exception:
            continue
    return sorted(set(out))


def _fingerprint(parts: Sequence[Any]) -> str:
    return hashlib.sha256(_canon(list(parts)).encode("utf-8")).hexdigest()


def _event_type_column(con: sqlite3.Connection) -> Optional[str]:
    columns = set(_columns(con, EVENT_TABLE))
    for name in ("event_type", "type", "kind"):
        if name in columns:
            return name
    return None


def _event_time_column(con: sqlite3.Connection) -> Optional[str]:
    columns = set(_columns(con, EVENT_TABLE))
    for name in ("created_at", "observed_at", "updated_at", "timestamp"):
        if name in columns:
            return name
    return None


def _delayed_events(
    con: sqlite3.Connection, hypothesis_id: int, baseline: int
) -> Dict[str, Any]:
    if not _table_exists(con, EVENT_TABLE):
        return {"available": False, "reason": "event_table_missing", "count": 0, "reobserved": 0}
    columns = set(_columns(con, EVENT_TABLE))
    if "hypothesis_id" not in columns:
        return {"available": False, "reason": "hypothesis_identity_missing", "count": 0, "reobserved": 0}
    time_column = _event_time_column(con)
    type_column = _event_type_column(con)
    if time_column is None or type_column is None:
        return {"available": False, "reason": "event_contract_incomplete", "count": 0, "reobserved": 0}
    sql = (
        "SELECT COUNT(*),"
        "SUM(CASE WHEN " + _q(type_column) + "='raw_observation_reobserved' THEN 1 ELSE 0 END),"
        "MIN(" + _q(time_column) + "),MAX(" + _q(time_column) + ") "
        "FROM " + _q(EVENT_TABLE) + " WHERE hypothesis_id=? AND COALESCE("
        + _q(time_column) + ",0)>?"
    )
    row = con.execute(sql, (int(hypothesis_id), int(baseline))).fetchone()
    return {
        "available": True,
        "reason": "delayed_context_event_query",
        "count": int(row[0] or 0),
        "reobserved": int(row[1] or 0),
        "first_at": row[2],
        "last_at": row[3],
        "time_column": time_column,
        "type_column": type_column,
    }


def _stability(con: sqlite3.Connection, hypothesis_id: int) -> Dict[str, Any]:
    if not _table_exists(con, STABILITY_TABLE):
        return {"available": False, "value": None, "reason": "stability_table_missing"}
    columns = set(_columns(con, STABILITY_TABLE))
    if "hypothesis_id" not in columns or "stability" not in columns:
        return {"available": False, "value": None, "reason": "stability_contract_incomplete"}
    order = "updated_at DESC" if "updated_at" in columns else "rowid DESC"
    row = con.execute(
        "SELECT stability FROM " + _q(STABILITY_TABLE)
        + " WHERE hypothesis_id=? ORDER BY " + order + " LIMIT 1",
        (int(hypothesis_id),),
    ).fetchone()
    return {
        "available": bool(row and row[0] is not None),
        "value": float(row[0]) if row and row[0] is not None else None,
        "reason": "latest_hypothesis_stability" if row else "stability_not_found",
    }


def _read_outcome(con: sqlite3.Connection, target_chunk_ids: Sequence[int], baseline: int) -> Dict[str, Any]:
    if not target_chunk_ids or not _table_exists(con, READ_TABLE):
        return {"available": False, "reason": "read_outcome_source_missing", "matched": 0}
    columns = set(_columns(con, READ_TABLE))
    if "chunk_id" not in columns:
        return {"available": False, "reason": "read_identity_missing", "matched": 0}
    time_column = next((name for name in ("updated_at", "completed_at", "last_read_at", "created_at") if name in columns), None)
    if time_column is None:
        return {"available": False, "reason": "read_time_missing", "matched": 0}
    status_column = next((name for name in ("status", "read_status") if name in columns), None)
    count_column = next((name for name in ("read_count", "reads", "times_read") if name in columns), None)
    if status_column is None and count_column is None:
        return {"available": False, "reason": "read_result_missing", "matched": 0}
    placeholders = ",".join("?" for _ in target_chunk_ids)
    status_expr = "COALESCE(" + _q(status_column) + ",'')" if status_column else "''"
    count_expr = "COALESCE(" + _q(count_column) + ",0)" if count_column else "0"
    sql = (
        "SELECT COUNT(*),SUM(CASE WHEN " + count_expr + ">0 OR lower(" + status_expr
        + ") IN ('read','read_no_candidate','completed','done') THEN 1 ELSE 0 END),"
        "MAX(" + count_expr + "),MAX(" + _q(time_column) + ") FROM " + _q(READ_TABLE)
        + " WHERE chunk_id IN (" + placeholders + ") AND COALESCE(" + _q(time_column) + ",0)>?"
    )
    row = con.execute(sql, tuple(int(x) for x in target_chunk_ids) + (int(baseline),)).fetchone()
    positive = int(row[1] or 0)
    return {
        "available": positive > 0,
        "reason": "delayed_target_read_outcome" if positive > 0 else "no_delayed_target_read_outcome",
        "matched": int(row[0] or 0),
        "positive": positive,
        "max_read_count": int(row[2] or 0),
        "last_read_at": row[3],
        "time_column": time_column,
        "status_column": status_column,
        "count_column": count_column,
    }


def _source_rows(
    con: sqlite3.Connection, checkpoint_time: int, checkpoint_id: int, limit: int
) -> List[sqlite3.Row]:
    if not _table_exists(con, SOURCE_TABLE):
        return []
    columns = set(_columns(con, SOURCE_TABLE))
    required = {"stable_observation_key", "shadow_key", "hypothesis_id", "latest_source_updated_at"}
    if not required.issubset(columns):
        raise RuntimeError("Source contract missing: " + ", ".join(sorted(required - columns)))
    projection = "latest_projection_fingerprint" if "latest_projection_fingerprint" in columns else "''"
    targets = "target_chunk_ids" if "target_chunk_ids" in columns else "'[]'"
    sql = (
        "SELECT stable_observation_key,shadow_key,hypothesis_id,latest_source_updated_at,"
        + projection + " AS projection_fingerprint," + targets + " AS target_chunk_ids "
        "FROM " + SOURCE_TABLE + " WHERE (COALESCE(latest_source_updated_at,0)>? "
        "OR (COALESCE(latest_source_updated_at,0)=? AND hypothesis_id>?)) "
        "ORDER BY COALESCE(latest_source_updated_at,0),hypothesis_id LIMIT ?"
    )
    return con.execute(sql, (checkpoint_time, checkpoint_time, checkpoint_id, min(max(1, int(limit)), LIMIT))).fetchall()


def run_phase(con: sqlite3.Connection, limit: int = LIMIT) -> Dict[str, Any]:
    ensure_schema(con)
    _self_check_schema(con)
    before = _protected_counts(con)
    state = _read_kv(con, STATE_TABLE)
    cp_time = int(state.get("checkpoint_updated_at", 0) or 0)
    cp_id = int(state.get("checkpoint_hypothesis_id", 0) or 0)
    rows = _source_rows(con, cp_time, cp_id, limit)
    now = _now()
    created = updated = real_count = eligible_count = awaiting_reobs = awaiting_stability = 0
    after_cp_time, after_cp_id = cp_time, cp_id
    errors: List[Dict[str, Any]] = []

    for row in rows:
        try:
            stable_key = str(row[0])
            shadow_key = str(row[1])
            hypothesis_id = int(row[2])
            baseline = int(row[3] or 0)
            projection_fingerprint = str(row[4] or "")
            targets = _parse_targets(row[5])
            events = _delayed_events(con, hypothesis_id, baseline)
            stability = _stability(con, hypothesis_id)
            read_outcome = _read_outcome(con, targets, baseline)
            real_available = bool(events.get("available") and int(events.get("reobserved", 0)) > 0 and read_outcome.get("available"))
            eligible = bool(real_available and stability.get("available"))
            missing = []
            if not real_available:
                if int(events.get("reobserved", 0)) <= 0:
                    missing.append("delayed_raw_reobservation")
                if not read_outcome.get("available"):
                    missing.append("delayed_target_read_outcome")
                awaiting_reobs += 1
            if not stability.get("available"):
                missing.append("hypothesis_stability")
                awaiting_stability += 1
            state_name = "eligible_shadow" if eligible else "awaiting_evidence"
            eligibility_key = _fingerprint([stable_key, hypothesis_id, baseline, VERSION])
            provenance = {
                "baseline_table": SOURCE_TABLE,
                "baseline_identity": stable_key,
                "delayed_event_table": EVENT_TABLE,
                "delayed_identity": hypothesis_id,
                "stability_table": STABILITY_TABLE,
                "read_outcome_table": READ_TABLE,
                "time_order_required": True,
                "causal_effect_claimed": False,
                "target_chunk_ids": targets,
            }
            details = {
                "contract": VERSION,
                "event_reason": events.get("reason"),
                "stability_reason": stability.get("reason"),
                "read_outcome": read_outcome,
                "productive_handoff": False,
                "phase5i_write": False,
            }
            existed = con.execute(
                "SELECT 1 FROM " + SHADOW_TABLE + " WHERE eligibility_key=?", (eligibility_key,)
            ).fetchone() is not None
            con.execute(
                "INSERT INTO " + SHADOW_TABLE + "("
                "eligibility_key,stable_observation_key,shadow_key,hypothesis_id,"
                "baseline_source_updated_at,baseline_projection_fingerprint,delayed_event_count,"
                "delayed_reobservation_count,first_delayed_event_at,last_delayed_event_at,"
                "stability_available,stability,real_outcome_observation_available,"
                "non_productive_eligible,eligibility_state,source_provenance,missing_signals,"
                "productive_write,details,first_seen_at,last_seen_at,version_count) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1) "
                "ON CONFLICT(eligibility_key) DO UPDATE SET "
                "delayed_event_count=excluded.delayed_event_count,"
                "delayed_reobservation_count=excluded.delayed_reobservation_count,"
                "first_delayed_event_at=excluded.first_delayed_event_at,"
                "last_delayed_event_at=excluded.last_delayed_event_at,"
                "stability_available=excluded.stability_available,stability=excluded.stability,"
                "real_outcome_observation_available=excluded.real_outcome_observation_available,"
                "non_productive_eligible=excluded.non_productive_eligible,"
                "eligibility_state=excluded.eligibility_state,source_provenance=excluded.source_provenance,"
                "missing_signals=excluded.missing_signals,productive_write=0,details=excluded.details,"
                "last_seen_at=excluded.last_seen_at,version_count=" + SHADOW_TABLE + ".version_count+1",
                (
                    eligibility_key, stable_key, shadow_key, hypothesis_id, baseline,
                    projection_fingerprint, int(events.get("count", 0)),
                    int(events.get("reobserved", 0)), events.get("first_at"), events.get("last_at"),
                    1 if stability.get("available") else 0, stability.get("value"),
                    1 if real_available else 0, 1 if eligible else 0, state_name,
                    _canon(provenance), _canon(missing), 0, _canon(details), now, now,
                ),
            )
            if existed:
                updated += 1
            else:
                created += 1
            real_count += int(real_available)
            eligible_count += int(eligible)
            after_cp_time, after_cp_id = baseline, hypothesis_id
        except Exception as exc:
            errors.append({"hypothesis_id": row[2] if len(row) > 2 else None, "error": type(exc).__name__ + ":" + str(exc)})
            break

    after = _protected_counts(con)
    safety = before == after and not errors
    con.execute(
        "INSERT INTO " + CYCLE_TABLE + "(phase,source_rows_seen,shadow_rows_created,"
        "shadow_rows_updated,real_outcome_available,non_productive_eligible,"
        "awaiting_delayed_reobservation,awaiting_stability,checkpoint_updated_at_before,"
        "checkpoint_hypothesis_id_before,checkpoint_updated_at_after,checkpoint_hypothesis_id_after,"
        "protected_before,protected_after,safety_ok,mode,created_at,details) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            PHASE, len(rows), created, updated, real_count, eligible_count, awaiting_reobs,
            awaiting_stability, cp_time, cp_id, after_cp_time, after_cp_id,
            _canon(before), _canon(after), 1 if safety else 0, "shadow", now,
            _canon({"errors": errors[:20], "limit": min(max(1, int(limit)), LIMIT)}),
        ),
    )
    if rows and not errors:
        cp_time, cp_id = after_cp_time, after_cp_id
    _write_kv(
        con,
        {
            "checkpoint_updated_at": cp_time,
            "checkpoint_hypothesis_id": cp_id,
            "last_source_rows_seen": len(rows),
            "last_shadow_rows_created": created,
            "last_shadow_rows_updated": updated,
            "last_real_outcome_available": real_count,
            "last_non_productive_eligible": eligible_count,
            "last_safety_ok": safety,
            "productive_writes": "disabled",
            "phase5i_writes": "disabled",
            "causal_effect_claimed": "false",
        },
        now,
    )
    if not safety:
        raise RuntimeError("Non-productive outcome shadow safety failure: " + repr(errors))
    return {
        "phase": PHASE,
        "mode": "shadow",
        "source_rows_seen": len(rows),
        "shadow_rows_created": created,
        "shadow_rows_updated": updated,
        "real_outcome_observation_available": real_count,
        "non_productive_eligible": eligible_count,
        "awaiting_delayed_reobservation": awaiting_reobs,
        "awaiting_stability": awaiting_stability,
        "productive_writes": 0,
        "phase5i_writes": 0,
        "safety_ok": True,
    }


def run_database(db_path: Path, limit: int = LIMIT) -> Dict[str, Any]:
    con = sqlite3.connect(str(db_path))
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("BEGIN IMMEDIATE")
        result = run_phase(con, limit)
        con.commit()
        return result
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.sqlite3"
        con = sqlite3.connect(str(db))
        con.executescript(
            "CREATE TABLE modern_gap_phase5f_shadow_observation_v2_latest("
            "stable_observation_key TEXT PRIMARY KEY,shadow_key TEXT,hypothesis_id INTEGER,"
            "latest_source_updated_at INTEGER,latest_projection_fingerprint TEXT,target_chunk_ids TEXT);"
            "CREATE TABLE modern_gap_candidate_shadow(shadow_key TEXT,hypothesis_id INTEGER);"
            "CREATE TABLE context_learning_events(id INTEGER PRIMARY KEY,event_type TEXT,"
            "hypothesis_id INTEGER,created_at INTEGER);"
            "CREATE TABLE hypothesis_stability_scores(hypothesis_id INTEGER,stability REAL,updated_at INTEGER);"
            "CREATE TABLE reading_queue(chunk_id INTEGER,status TEXT,read_count INTEGER,updated_at INTEGER);"
            "CREATE TABLE facts(id INTEGER);CREATE TABLE relations(id INTEGER);CREATE TABLE questions(id INTEGER);"
            "CREATE TABLE internal_learning_gaps(id INTEGER);CREATE TABLE phase5i_outcome_driven_experiments(id INTEGER);"
            "CREATE TABLE modern_outcome_bridge_shadow(id INTEGER);"
            "INSERT INTO modern_gap_phase5f_shadow_observation_v2_latest VALUES('obs-1','shadow-1',1,100,'pf','[10,11]');"
            "INSERT INTO context_learning_events VALUES(1,'raw_observation_created',1,90);"
            "INSERT INTO context_learning_events VALUES(2,'raw_observation_reobserved',1,120);"
            "INSERT INTO hypothesis_stability_scores VALUES(1,0.2,121);"
            "INSERT INTO reading_queue VALUES(10,'read',1,122);"
        )
        con.commit()
        ensure_schema(con)
        _self_check_schema(con)
        first = run_phase(con, 512)
        con.commit()
        assert first["source_rows_seen"] == 1
        assert first["real_outcome_observation_available"] == 1
        assert first["non_productive_eligible"] == 1
        assert first["productive_writes"] == 0 and first["phase5i_writes"] == 0
        assert _count(con, "phase5i_outcome_driven_experiments") == 0
        assert _count(con, "facts") == 0
        row = con.execute(
            "SELECT real_outcome_observation_available,non_productive_eligible,productive_write "
            "FROM " + SHADOW_TABLE
        ).fetchone()
        assert tuple(row) == (1, 1, 0)
        second = run_phase(con, 512)
        con.commit()
        assert second["source_rows_seen"] == 0
        assert _read_kv(con, STATE_TABLE)["causal_effect_claimed"] == "false"
        con.close()
    print("SELFTEST PASS")
    print(_canon({
        "read_only_sources": True,
        "own_shadow_writes": True,
        "delayed_reobservation": True,
        "stability_gate": True,
        "idempotent_checkpoint": True,
        "productive_writes": False,
        "phase5i_writes": False,
        "causal_effect_claimed": False,
    }))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    run = sub.add_parser("run")
    run.add_argument("--db", default="ki_memory.sqlite3")
    run.add_argument("--limit", type=int, default=LIMIT)
    args = parser.parse_args()
    if args.cmd == "selftest":
        return selftest()
    result = run_database(Path(args.db), args.limit)
    print(_canon(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
