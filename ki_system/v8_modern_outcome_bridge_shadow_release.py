# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import sqlite3
import time
from typing import Any, Dict, List, Tuple

PHASE = "modern_outcome_bridge_shadow_v1"
BRIDGE_MODE = "shadow"
SOURCE_TABLE = "phase5i_outcome_driven_experiments"

SCHEMA_TABLES: Dict[str, List[Tuple[str, str]]] = {'phase5i_outcome_driven_experiments': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                        ('experiment_key', 'TEXT'),
                                        ('gap_id', 'INTEGER'),
                                        ('gap_key', 'TEXT'),
                                        ('gap_type', 'TEXT'),
                                        ('role', 'TEXT'),
                                        ('center_chunk_id', 'INTEGER'),
                                        ('target_chunk_id', 'INTEGER'),
                                        ('selected_strategy', 'TEXT'),
                                        ('previous_strategy', 'TEXT'),
                                        ('strategy_score', 'REAL DEFAULT 0'),
                                        ('expected_outcome_score', 'REAL DEFAULT 0'),
                                        ('expected_closure_delta', 'REAL DEFAULT 0'),
                                        ('expected_overlap_score', 'REAL DEFAULT 0'),
                                        ('expected_no_candidate_rate', 'REAL DEFAULT 0'),
                                        ('learning_rate', 'REAL DEFAULT 0'),
                                        ('error_weight', 'REAL DEFAULT 0'),
                                        ('revision_pressure', 'REAL DEFAULT 0'),
                                        ('exploration_pressure', 'REAL DEFAULT 0'),
                                        ('inhibition_level', 'REAL DEFAULT 0'),
                                        ('consolidation_gain', 'REAL DEFAULT 0'),
                                        ('dopamine', 'REAL DEFAULT 0'),
                                        ('serotonin', 'REAL DEFAULT 0'),
                                        ('glutamate', 'REAL DEFAULT 0'),
                                        ('gaba', 'REAL DEFAULT 0'),
                                        ('noradrenaline', 'REAL DEFAULT 0'),
                                        ('acetylcholine', 'REAL DEFAULT 0'),
                                        ('reason', 'TEXT'),
                                        ('details', 'TEXT'),
                                        ('created_at', 'INTEGER'),
                                        ('updated_at', 'INTEGER')],
 'modern_outcome_bridge_shadow': [('shadow_key', 'TEXT PRIMARY KEY'),
                                  ('source_table', 'TEXT'),
                                  ('source_id', 'INTEGER'),
                                  ('experiment_key', 'TEXT'),
                                  ('gap_id', 'INTEGER'),
                                  ('gap_key', 'TEXT'),
                                  ('gap_type', 'TEXT'),
                                  ('role', 'TEXT'),
                                  ('center_chunk_id', 'INTEGER'),
                                  ('target_chunk_id', 'INTEGER'),
                                  ('selected_strategy', 'TEXT'),
                                  ('strategy_score', 'REAL DEFAULT 0'),
                                  ('expected_outcome_score', 'REAL DEFAULT 0'),
                                  ('expected_closure_delta', 'REAL DEFAULT 0'),
                                  ('expected_overlap_score', 'REAL DEFAULT 0'),
                                  ('expected_no_candidate_rate', 'REAL DEFAULT 0'),
                                  ('observed_read_status', 'TEXT'),
                                  ('observed_read_count', 'INTEGER DEFAULT 0'),
                                  ('observed_attention_score', 'REAL DEFAULT 0'),
                                  ('observation_ready', 'INTEGER DEFAULT 0'),
                                  ('mapped_closure_delta', 'REAL DEFAULT 0'),
                                  ('mapped_overlap_score', 'REAL DEFAULT 0'),
                                  ('mapped_no_candidate_rate', 'REAL DEFAULT 0'),
                                  ('mapped_outcome_score', 'REAL DEFAULT 0'),
                                  ('mapped_outcome_label', 'TEXT'),
                                  ('mapped_recommendation', 'TEXT'),
                                  ('projection_status', 'TEXT'),
                                  ('missing_signals', 'TEXT'),
                                  ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                  ('details', 'TEXT'),
                                  ('source_created_at', 'INTEGER'),
                                  ('created_at', 'INTEGER'),
                                  ('updated_at', 'INTEGER')],
 'modern_outcome_bridge_shadow_cycles': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                         ('phase', 'TEXT'),
                                         ('source_rows_seen', 'INTEGER DEFAULT 0'),
                                         ('shadow_rows_created', 'INTEGER DEFAULT 0'),
                                         ('shadow_rows_updated', 'INTEGER DEFAULT 0'),
                                         ('observation_ready', 'INTEGER DEFAULT 0'),
                                         ('awaiting_observation', 'INTEGER DEFAULT 0'),
                                         ('productive_outcomes_before', 'INTEGER DEFAULT 0'),
                                         ('productive_outcomes_after', 'INTEGER DEFAULT 0'),
                                         ('productive_memory_before', 'INTEGER DEFAULT 0'),
                                         ('productive_memory_after', 'INTEGER DEFAULT 0'),
                                         ('facts_before', 'INTEGER DEFAULT 0'),
                                         ('facts_after', 'INTEGER DEFAULT 0'),
                                         ('relations_before', 'INTEGER DEFAULT 0'),
                                         ('relations_after', 'INTEGER DEFAULT 0'),
                                         ('questions_before', 'INTEGER DEFAULT 0'),
                                         ('questions_after', 'INTEGER DEFAULT 0'),
                                         ('safety_ok', 'INTEGER DEFAULT 1'),
                                         ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                         ('created_at', 'INTEGER')],
 'modern_outcome_bridge_shadow_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')]}

def _now() -> int:
    return int(time.time())

def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        value = float(value)
    except Exception:
        value = 0.0
    return max(lo, min(hi, value))

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    if not _table_exists(con, table):
        return []
    return [row[1] for row in con.execute("PRAGMA table_info(" + table + ")").fetchall()]

def _count(con: sqlite3.Connection, table: str) -> int:
    if not _table_exists(con, table):
        return 0
    return int(con.execute("SELECT COUNT(1) FROM " + table).fetchone()[0])

def ensure_schema(con: sqlite3.Connection) -> Dict[str, Any]:
    report = {"created_tables": [], "added_columns": []}
    for table, definitions in SCHEMA_TABLES.items():
        if not _table_exists(con, table):
            con.execute("CREATE TABLE " + table + " (" + ", ".join(name + " " + decl for name, decl in definitions) + ")")
            report["created_tables"].append(table)
        else:
            existing = set(_columns(con, table))
            for name, decl in definitions:
                if name in existing:
                    continue
                upper = decl.upper()
                if "PRIMARY KEY" in upper or "AUTOINCREMENT" in upper:
                    continue
                con.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + decl)
                report["added_columns"].append(table + "." + name)
    con.execute("CREATE INDEX IF NOT EXISTS idx_modern_outcome_shadow_source ON modern_outcome_bridge_shadow(source_table,source_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_modern_outcome_shadow_ready ON modern_outcome_bridge_shadow(observation_ready,updated_at)")
    con.commit()
    _self_check_schema(con)
    return report

def _self_check_schema(con: sqlite3.Connection) -> bool:
    missing: List[str] = []
    for table, definitions in SCHEMA_TABLES.items():
        existing = set(_columns(con, table))
        if not existing:
            missing.append(table)
            continue
        missing.extend(table + "." + name for name, _decl in definitions if name not in existing)
    if missing:
        raise RuntimeError("Modern outcome shadow schema missing: " + ", ".join(missing))
    return True

def _state_set(con: sqlite3.Connection, key: str, value: Any, now: int) -> None:
    con.execute(
        "INSERT INTO modern_outcome_bridge_shadow_state(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
        (key, str(value).lower() if isinstance(value, bool) else str(value), now),
    )

def _recommendation(outcome: float, closure: float, no_candidate: float, overlap: float) -> str:
    if outcome >= 0.62 and closure >= 0.08:
        return "reinforce_strategy_for_gap_type"
    if no_candidate >= 0.35:
        return "reduce_or_shift_strategy_due_to_no_candidate"
    if overlap >= 0.85 and closure < 0.06:
        return "increase_contrast_and_reduce_overlap"
    if closure < 0.03:
        return "explore_alternative_context_strategy"
    return "observe_and_refine_strategy"

def _mapped_label(outcome: float, closure: float, no_candidate: float, overlap: float) -> str:
    if closure > 0.09 and no_candidate < 0.35:
        return "useful_strategy_signal"
    if no_candidate >= 0.75:
        return "no_candidate_strategy_penalty"
    if overlap >= 0.9 and closure < 0.04:
        return "high_overlap_low_gain"
    if outcome >= 0.5:
        return "promising_strategy_observe"
    return "weak_strategy_signal"

def _resolve_db(obj: Any = None) -> sqlite3.Connection:
    if isinstance(obj, sqlite3.Connection):
        return obj
    if obj is not None:
        for attr in ("mem", "memory", "m", "store", "memory_store"):
            inner = getattr(obj, attr, None)
            if inner is not None and inner is not obj:
                try:
                    return _resolve_db(inner)
                except Exception:
                    pass
        for attr in ("conn", "con", "db", "connection"):
            con = getattr(obj, attr, None)
            if isinstance(con, sqlite3.Connection):
                return con
        for attr in ("db_path", "path", "filename"):
            path = getattr(obj, attr, None)
            if path:
                return sqlite3.connect(str(path))
    return sqlite3.connect("ki_memory.sqlite3")

def observe_shadow(obj: Any = None, limit: int = 1200) -> Dict[str, Any]:
    con = _resolve_db(obj)
    ensure_schema(con)
    _self_check_schema(con)
    now = _now()
    before = {
        "outcomes": _count(con, "phase5g_experiment_outcomes"),
        "memory": _count(con, "phase5h_strategy_outcome_memory"),
        "facts": _count(con, "facts"),
        "relations": _count(con, "relations"),
        "questions": _count(con, "questions"),
    }
    rows = con.execute(
        "SELECT id,experiment_key,gap_id,gap_key,gap_type,role,center_chunk_id,target_chunk_id,selected_strategy,"
        "strategy_score,expected_outcome_score,expected_closure_delta,expected_overlap_score,expected_no_candidate_rate,"
        "reason,details,created_at FROM phase5i_outcome_driven_experiments ORDER BY id DESC LIMIT ?",
        (int(limit),),
    ).fetchall()
    created = updated = ready_count = awaiting = 0
    rq_cols = set(_columns(con, "reading_queue"))
    ca_cols = set(_columns(con, "chunk_attention_scores"))
    for row in rows:
        (source_id, experiment_key, gap_id, gap_key, gap_type, role, center_chunk, target_chunk,
         strategy, strategy_score, expected_outcome, expected_closure, expected_overlap, expected_no_candidate,
         reason, source_details, source_created_at) = row
        read_status = "unknown"
        read_count = 0
        attention = 0.0
        missing: List[str] = []
        if target_chunk is None:
            missing.append("target_chunk_id")
        if target_chunk is not None and {"chunk_id", "status", "read_count"}.issubset(rq_cols):
            rr = con.execute("SELECT status,read_count FROM reading_queue WHERE chunk_id=?", (target_chunk,)).fetchone()
            if rr:
                read_status = str(rr[0] or "unknown")
                read_count = int(rr[1] or 0)
            else:
                missing.append("reading_queue_row")
        else:
            missing.append("reading_queue_status")
        if target_chunk is not None and {"chunk_id", "attention_score"}.issubset(ca_cols):
            ar = con.execute("SELECT attention_score FROM chunk_attention_scores WHERE chunk_id=?", (target_chunk,)).fetchone()
            if ar:
                attention = _clamp(ar[0])
            else:
                missing.append("chunk_attention_row")
        else:
            missing.append("chunk_attention_score")
        observation_ready = int(read_count > 0 or read_status in ("read", "read_no_candidate", "completed", "done"))
        if observation_ready:
            ready_count += 1
        else:
            awaiting += 1
            missing.append("completed_read_observation")
        closure = _clamp(expected_closure, -1.0, 1.0)
        overlap = _clamp(expected_overlap if expected_overlap is not None else 0.5)
        no_candidate = _clamp(expected_no_candidate)
        if read_status == "read_no_candidate":
            no_candidate = 1.0
        score = _clamp(strategy_score if strategy_score is not None else expected_outcome)
        mapped_outcome = _clamp(0.45 * max(closure, 0.0) + 0.25 * (1.0 - no_candidate) + 0.20 * (1.0 - overlap) + 0.10 * score)
        label = _mapped_label(mapped_outcome, closure, no_candidate, overlap)
        recommendation = _recommendation(mapped_outcome, max(closure, 0.0), no_candidate, overlap)
        shadow_key = SOURCE_TABLE + ":" + str(source_id)
        exists = con.execute("SELECT 1 FROM modern_outcome_bridge_shadow WHERE shadow_key=?", (shadow_key,)).fetchone() is not None
        con.execute(
            "INSERT INTO modern_outcome_bridge_shadow("
            "shadow_key,source_table,source_id,experiment_key,gap_id,gap_key,gap_type,role,center_chunk_id,target_chunk_id,selected_strategy,"
            "strategy_score,expected_outcome_score,expected_closure_delta,expected_overlap_score,expected_no_candidate_rate,"
            "observed_read_status,observed_read_count,observed_attention_score,observation_ready,mapped_closure_delta,mapped_overlap_score,"
            "mapped_no_candidate_rate,mapped_outcome_score,mapped_outcome_label,mapped_recommendation,projection_status,missing_signals,"
            "bridge_mode,details,source_created_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(shadow_key) DO UPDATE SET observed_read_status=excluded.observed_read_status,observed_read_count=excluded.observed_read_count,"
            "observed_attention_score=excluded.observed_attention_score,observation_ready=excluded.observation_ready,mapped_closure_delta=excluded.mapped_closure_delta,"
            "mapped_overlap_score=excluded.mapped_overlap_score,mapped_no_candidate_rate=excluded.mapped_no_candidate_rate,"
            "mapped_outcome_score=excluded.mapped_outcome_score,mapped_outcome_label=excluded.mapped_outcome_label,"
            "mapped_recommendation=excluded.mapped_recommendation,projection_status=excluded.projection_status,missing_signals=excluded.missing_signals,"
            "details=excluded.details,updated_at=excluded.updated_at",
            (shadow_key,SOURCE_TABLE,source_id,experiment_key,gap_id,gap_key,gap_type,role,center_chunk,target_chunk,strategy,
             _clamp(strategy_score),_clamp(expected_outcome),closure,overlap,no_candidate,read_status,read_count,attention,observation_ready,
             closure,overlap,no_candidate,mapped_outcome,label,recommendation,
             "observation_ready_projection" if observation_ready else "awaiting_observation_projection",
             _json(sorted(set(missing))),BRIDGE_MODE,
             _json({"source_reason": reason, "source_details": source_details, "projection_only": True}),
             source_created_at,now,now),
        )
        if exists:
            updated += 1
        else:
            created += 1
    after = {
        "outcomes": _count(con, "phase5g_experiment_outcomes"),
        "memory": _count(con, "phase5h_strategy_outcome_memory"),
        "facts": _count(con, "facts"),
        "relations": _count(con, "relations"),
        "questions": _count(con, "questions"),
    }
    safety_ok = int(before == after)
    if not safety_ok:
        con.rollback()
        raise RuntimeError("Shadow bridge changed productive or safety row counts: before=" + repr(before) + " after=" + repr(after))
    con.execute(
        "INSERT INTO modern_outcome_bridge_shadow_cycles(phase,source_rows_seen,shadow_rows_created,shadow_rows_updated,"
        "observation_ready,awaiting_observation,productive_outcomes_before,productive_outcomes_after,productive_memory_before,productive_memory_after,"
        "facts_before,facts_after,relations_before,relations_after,questions_before,questions_after,safety_ok,bridge_mode,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (PHASE,len(rows),created,updated,ready_count,awaiting,before["outcomes"],after["outcomes"],before["memory"],after["memory"],
         before["facts"],after["facts"],before["relations"],after["relations"],before["questions"],after["questions"],1,BRIDGE_MODE,now),
    )
    for key, value in {
        "phase": PHASE, "bridge_mode": BRIDGE_MODE, "source_table": SOURCE_TABLE,
        "productive_outcome_writes": "disabled", "productive_memory_writes": "disabled",
        "direct_fact_writes": "disabled", "direct_relation_writes": "disabled", "question_writes": "disabled",
        "fact_promotion": "disabled", "last_source_rows_seen": len(rows), "last_observation_ready": ready_count,
        "last_awaiting_observation": awaiting, "last_safety_ok": True,
    }.items():
        _state_set(con, key, value, now)
    con.commit()
    return {
        "status": "modern_outcome_bridge_shadow_complete", "phase": PHASE, "bridge_mode": BRIDGE_MODE,
        "source_rows_seen": len(rows), "shadow_rows_created": created, "shadow_rows_updated": updated,
        "observation_ready": ready_count, "awaiting_observation": awaiting,
        "productive_counts_unchanged": True, "facts": after["facts"], "relations": after["relations"], "questions": after["questions"],
    }
