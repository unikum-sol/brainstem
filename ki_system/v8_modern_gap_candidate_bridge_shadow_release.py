# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import sqlite3
import time
from typing import Any, Dict, List, Tuple

PHASE = "modern_gap_candidate_bridge_shadow_v1"
BRIDGE_MODE = "shadow"
BATCH_LIMIT = 512
SCHEMA_TABLES: Dict[str, List[Tuple[str, str]]] = {'modern_gap_candidate_shadow': [('shadow_key', 'TEXT PRIMARY KEY'),
                                 ('hypothesis_id', 'INTEGER'),
                                 ('signature', 'TEXT'),
                                 ('chunk_id', 'INTEGER'),
                                 ('role', 'TEXT'),
                                 ('status', 'TEXT'),
                                 ('hypothesis_confidence', 'REAL DEFAULT 0'),
                                 ('hypothesis_uncertainty', 'REAL DEFAULT 0'),
                                 ('evidence_count', 'INTEGER DEFAULT 0'),
                                 ('raw_observation_count', 'INTEGER DEFAULT 0'),
                                 ('raw_created_count', 'INTEGER DEFAULT 0'),
                                 ('raw_reobserved_count', 'INTEGER DEFAULT 0'),
                                 ('stability', 'REAL'),
                                 ('stability_confidence', 'REAL'),
                                 ('stability_uncertainty', 'REAL'),
                                 ('feedback_count', 'INTEGER DEFAULT 0'),
                                 ('error_count', 'INTEGER DEFAULT 0'),
                                 ('conflict_count', 'INTEGER DEFAULT 0'),
                                 ('dopamine', 'REAL DEFAULT 0'),
                                 ('serotonin', 'REAL DEFAULT 0'),
                                 ('glutamate', 'REAL DEFAULT 0'),
                                 ('gaba', 'REAL DEFAULT 0'),
                                 ('noradrenaline', 'REAL DEFAULT 0'),
                                 ('acetylcholine', 'REAL DEFAULT 0'),
                                 ('phase6a_replay_weight', 'REAL DEFAULT 0'),
                                 ('phase6a_meta_plasticity', 'REAL DEFAULT 0'),
                                 ('phase6a_sleep_replay_count', 'INTEGER DEFAULT 0'),
                                 ('last_replayed_at', 'INTEGER'),
                                 ('first_observed_at', 'INTEGER'),
                                 ('last_observed_at', 'INTEGER'),
                                 ('signal_presence', 'TEXT'),
                                 ('missing_signals', 'TEXT'),
                                 ('candidate_state', "TEXT DEFAULT 'observed_only'"),
                                 ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                 ('details', 'TEXT'),
                                 ('created_at', 'INTEGER'),
                                 ('updated_at', 'INTEGER')],
 'modern_gap_candidate_shadow_cycles': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                        ('phase', 'TEXT'),
                                        ('source_rows_seen', 'INTEGER DEFAULT 0'),
                                        ('shadow_rows_created', 'INTEGER DEFAULT 0'),
                                        ('shadow_rows_updated', 'INTEGER DEFAULT 0'),
                                        ('rows_with_reobservation', 'INTEGER DEFAULT 0'),
                                        ('rows_with_stability', 'INTEGER DEFAULT 0'),
                                        ('rows_with_feedback', 'INTEGER DEFAULT 0'),
                                        ('rows_with_errors', 'INTEGER DEFAULT 0'),
                                        ('rows_with_replay', 'INTEGER DEFAULT 0'),
                                        ('productive_gaps_before', 'INTEGER DEFAULT 0'),
                                        ('productive_gaps_after', 'INTEGER DEFAULT 0'),
                                        ('attention_before', 'INTEGER DEFAULT 0'),
                                        ('attention_after', 'INTEGER DEFAULT 0'),
                                        ('phase5f_experiments_before', 'INTEGER DEFAULT 0'),
                                        ('phase5f_experiments_after', 'INTEGER DEFAULT 0'),
                                        ('phase5g_experiments_before', 'INTEGER DEFAULT 0'),
                                        ('phase5g_experiments_after', 'INTEGER DEFAULT 0'),
                                        ('phase5i_experiments_before', 'INTEGER DEFAULT 0'),
                                        ('phase5i_experiments_after', 'INTEGER DEFAULT 0'),
                                        ('facts_before', 'INTEGER DEFAULT 0'),
                                        ('facts_after', 'INTEGER DEFAULT 0'),
                                        ('relations_before', 'INTEGER DEFAULT 0'),
                                        ('relations_after', 'INTEGER DEFAULT 0'),
                                        ('questions_before', 'INTEGER DEFAULT 0'),
                                        ('questions_after', 'INTEGER DEFAULT 0'),
                                        ('safety_ok', 'INTEGER DEFAULT 1'),
                                        ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                        ('created_at', 'INTEGER')],
 'modern_gap_candidate_shadow_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')]}
PROTECTED_TABLES = (
    "internal_learning_gaps", "chunk_attention_scores", "phase5f_context_window_experiments",
    "phase5g_strategy_experiments", "phase5i_outcome_driven_experiments", "facts", "relations", "questions",
)

def _now() -> int:
    return int(time.time())

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]

def _count(con: sqlite3.Connection, table: str) -> int:
    if not _table_exists(con, table):
        return 0
    return int(con.execute("SELECT COUNT(1) FROM " + table).fetchone()[0])

def _protected_counts(con: sqlite3.Connection) -> Dict[str, int]:
    return {table: _count(con, table) for table in PROTECTED_TABLES}

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
    con.execute("CREATE INDEX IF NOT EXISTS idx_gap_shadow_hypothesis ON modern_gap_candidate_shadow(hypothesis_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_gap_shadow_updated ON modern_gap_candidate_shadow(updated_at)")
    if _table_exists(con, "context_hypotheses"):
        con.execute("CREATE INDEX IF NOT EXISTS idx_gap_shadow_source_checkpoint ON context_hypotheses(updated_at,id)")
    if _table_exists(con, "context_learning_events"):
        con.execute("CREATE INDEX IF NOT EXISTS idx_gap_shadow_learning_events_hyp ON context_learning_events(hypothesis_id)")
    if _table_exists(con, "hypothesis_feedback"):
        con.execute("CREATE INDEX IF NOT EXISTS idx_gap_shadow_feedback_hyp ON hypothesis_feedback(hypothesis_id)")
    if _table_exists(con, "hypothesis_error_events"):
        con.execute("CREATE INDEX IF NOT EXISTS idx_gap_shadow_errors_hyp ON hypothesis_error_events(hypothesis_id)")
    con.commit()
    _self_check_schema(con)
    return report

def _self_check_schema(con: sqlite3.Connection) -> bool:
    missing: List[str] = []
    for table, definitions in SCHEMA_TABLES.items():
        existing = set(_columns(con, table))
        if not existing:
            missing.append(table)
        else:
            missing.extend(table + "." + name for name, _decl in definitions if name not in existing)
    if missing:
        raise RuntimeError("Modern gap shadow schema missing: " + ", ".join(missing))
    return True

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

def _state_set(con: sqlite3.Connection, key: str, value: Any, now: int) -> None:
    con.execute(
        "INSERT INTO modern_gap_candidate_shadow_state(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
        (key, str(value).lower() if isinstance(value, bool) else str(value), now),
    )

def _state_int(con: sqlite3.Connection, key: str, default: int = 0) -> int:
    row = con.execute("SELECT value FROM modern_gap_candidate_shadow_state WHERE key=?", (key,)).fetchone()
    try:
        return int(row[0]) if row else int(default)
    except Exception:
        return int(default)

def observe_shadow(obj: Any = None, limit: int = BATCH_LIMIT) -> Dict[str, Any]:
    con = _resolve_db(obj)
    ensure_schema(con)
    _self_check_schema(con)
    now = _now()
    before = _protected_counts(con)
    checkpoint_updated = _state_int(con, "checkpoint_updated_at", 0)
    checkpoint_id = _state_int(con, "checkpoint_hypothesis_id", 0)
    rows = con.execute(
        "SELECT h.id,h.signature,h.chunk_id,h.role,h.status,h.confidence,h.uncertainty,h.evidence_count,"
        "h.dopamine,h.serotonin,h.glutamate,h.gaba,h.noradrenaline,h.acetylcholine,"
        "h.phase6a_replay_weight,h.phase6a_meta_plasticity,h.phase6a_sleep_replay_count,h.phase6a_last_replayed_at,h.created_at,h.updated_at,"
        "s.stability,s.confidence,s.uncertainty,s.feedback_count,s.error_count,s.conflict_count "
        "FROM context_hypotheses h LEFT JOIN hypothesis_stability_scores s ON s.hypothesis_id=h.id "
        "WHERE (COALESCE(h.updated_at,0)>? OR (COALESCE(h.updated_at,0)=? AND h.id>?)) "
        "ORDER BY COALESCE(h.updated_at,0),h.id LIMIT ?",
        (checkpoint_updated, checkpoint_updated, checkpoint_id, max(1, min(int(limit), BATCH_LIMIT))),
    ).fetchall()
    created = updated = with_reobs = with_stability = with_feedback = with_errors = with_replay = 0
    last_updated = checkpoint_updated
    last_id = checkpoint_id
    for row in rows:
        (hid,signature,chunk_id,role,status,hconf,hunc,evidence,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,
         replay_weight,meta_plasticity,replay_count,last_replayed,created_at,updated_at,stability,sconf,sunc,feedback_count,error_count,conflict_count)=row
        ev = con.execute(
            "SELECT COUNT(1),SUM(CASE WHEN event_type='raw_observation_created' THEN 1 ELSE 0 END),"
            "SUM(CASE WHEN event_type='raw_observation_reobserved' THEN 1 ELSE 0 END),MIN(created_at),MAX(created_at) "
            "FROM context_learning_events WHERE hypothesis_id=?", (hid,)
        ).fetchone()
        raw_count=int((ev and ev[0]) or 0); raw_created=int((ev and ev[1]) or 0); raw_reobs=int((ev and ev[2]) or 0)
        first_obs=(ev and ev[3]) or created_at; last_obs=(ev and ev[4]) or updated_at
        fb_total=int(con.execute("SELECT COUNT(1) FROM hypothesis_feedback WHERE hypothesis_id=?",(hid,)).fetchone()[0]) if _table_exists(con,"hypothesis_feedback") else 0
        err_total=int(con.execute("SELECT COUNT(1) FROM hypothesis_error_events WHERE hypothesis_id=?",(hid,)).fetchone()[0]) if _table_exists(con,"hypothesis_error_events") else 0
        feedback_total=max(int(feedback_count or 0),int(fb_total or 0)); error_total=max(int(error_count or 0),int(err_total or 0))
        presence={"raw_observation":raw_count>0,"reobservation":raw_reobs>0,"stability":stability is not None,"feedback":feedback_total>0,
                  "error":error_total>0,"conflict":int(conflict_count or 0)>0,"replay":int(replay_count or 0)>0 or float(replay_weight or 0)>0}
        missing=sorted(k for k,v in presence.items() if not v)
        key="context_hypothesis:"+str(hid)
        existed=con.execute("SELECT 1 FROM modern_gap_candidate_shadow WHERE shadow_key=?",(key,)).fetchone() is not None
        con.execute(
            "INSERT INTO modern_gap_candidate_shadow(shadow_key,hypothesis_id,signature,chunk_id,role,status,hypothesis_confidence,hypothesis_uncertainty,evidence_count,"
            "raw_observation_count,raw_created_count,raw_reobserved_count,stability,stability_confidence,stability_uncertainty,feedback_count,error_count,conflict_count,"
            "dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,phase6a_replay_weight,phase6a_meta_plasticity,phase6a_sleep_replay_count,last_replayed_at,"
            "first_observed_at,last_observed_at,signal_presence,missing_signals,candidate_state,bridge_mode,details,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(shadow_key) DO UPDATE SET signature=excluded.signature,chunk_id=excluded.chunk_id,role=excluded.role,status=excluded.status,"
            "hypothesis_confidence=excluded.hypothesis_confidence,hypothesis_uncertainty=excluded.hypothesis_uncertainty,evidence_count=excluded.evidence_count,"
            "raw_observation_count=excluded.raw_observation_count,raw_created_count=excluded.raw_created_count,raw_reobserved_count=excluded.raw_reobserved_count,"
            "stability=excluded.stability,stability_confidence=excluded.stability_confidence,stability_uncertainty=excluded.stability_uncertainty,"
            "feedback_count=excluded.feedback_count,error_count=excluded.error_count,conflict_count=excluded.conflict_count,dopamine=excluded.dopamine,"
            "serotonin=excluded.serotonin,glutamate=excluded.glutamate,gaba=excluded.gaba,noradrenaline=excluded.noradrenaline,acetylcholine=excluded.acetylcholine,"
            "phase6a_replay_weight=excluded.phase6a_replay_weight,phase6a_meta_plasticity=excluded.phase6a_meta_plasticity,"
            "phase6a_sleep_replay_count=excluded.phase6a_sleep_replay_count,last_replayed_at=excluded.last_replayed_at,last_observed_at=excluded.last_observed_at,"
            "signal_presence=excluded.signal_presence,missing_signals=excluded.missing_signals,details=excluded.details,updated_at=excluded.updated_at",
            (key,hid,signature,chunk_id,role,status,float(hconf or 0),float(hunc or 0),int(evidence or 0),raw_count,raw_created,raw_reobs,
             stability,sconf,sunc,feedback_total,error_total,int(conflict_count or 0),float(dopamine or 0),float(serotonin or 0),float(glutamate or 0),
             float(gaba or 0),float(noradrenaline or 0),float(acetylcholine or 0),float(replay_weight or 0),float(meta_plasticity or 0),int(replay_count or 0),
             last_replayed,first_obs,last_obs,_json(presence),_json(missing),"observed_only",BRIDGE_MODE,
             _json({"projection_only":True,"no_gap_classification":True,"source":"context_hypotheses"}),now,now)
        )
        if existed: updated+=1
        else: created+=1
        with_reobs+=int(raw_reobs>0); with_stability+=int(stability is not None); with_feedback+=int(feedback_total>0)
        with_errors+=int(error_total>0); with_replay+=int(presence["replay"])
        last_updated=int(updated_at or 0); last_id=int(hid)
    after = _protected_counts(con)
    if before != after:
        con.rollback()
        raise RuntimeError("Shadow bridge changed protected tables: before="+repr(before)+" after="+repr(after))
    values=(PHASE,len(rows),created,updated,with_reobs,with_stability,with_feedback,with_errors,with_replay,
            before["internal_learning_gaps"],after["internal_learning_gaps"],before["chunk_attention_scores"],after["chunk_attention_scores"],
            before["phase5f_context_window_experiments"],after["phase5f_context_window_experiments"],before["phase5g_strategy_experiments"],after["phase5g_strategy_experiments"],
            before["phase5i_outcome_driven_experiments"],after["phase5i_outcome_driven_experiments"],before["facts"],after["facts"],before["relations"],after["relations"],
            before["questions"],after["questions"],1,BRIDGE_MODE,now)
    con.execute("INSERT INTO modern_gap_candidate_shadow_cycles(phase,source_rows_seen,shadow_rows_created,shadow_rows_updated,rows_with_reobservation,rows_with_stability,"
                "rows_with_feedback,rows_with_errors,rows_with_replay,productive_gaps_before,productive_gaps_after,attention_before,attention_after,phase5f_experiments_before,"
                "phase5f_experiments_after,phase5g_experiments_before,phase5g_experiments_after,phase5i_experiments_before,phase5i_experiments_after,facts_before,facts_after,"
                "relations_before,relations_after,questions_before,questions_after,safety_ok,bridge_mode,created_at) VALUES("+",".join(["?"]*28)+")",values)
    if rows:
        _state_set(con,"checkpoint_updated_at",last_updated,now); _state_set(con,"checkpoint_hypothesis_id",last_id,now)
    for key,value in {"phase":PHASE,"bridge_mode":BRIDGE_MODE,"candidate_state":"observed_only","productive_gap_writes":"disabled",
                      "attention_writes":"disabled","phase5f_writes":"disabled","phase5g_writes":"disabled","phase5i_writes":"disabled",
                      "direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_writes":"disabled","fact_promotion":"disabled",
                      "last_source_rows_seen":len(rows),"last_safety_ok":True}.items():
        _state_set(con,key,value,now)
    con.commit()
    return {"status":"modern_gap_candidate_shadow_complete","phase":PHASE,"bridge_mode":BRIDGE_MODE,"source_rows_seen":len(rows),
            "shadow_rows_created":created,"shadow_rows_updated":updated,"rows_with_reobservation":with_reobs,"rows_with_stability":with_stability,
            "rows_with_feedback":with_feedback,"rows_with_errors":with_errors,"rows_with_replay":with_replay,"protected_counts_unchanged":True,
            "facts":after["facts"],"relations":after["relations"],"questions":after["questions"]}
