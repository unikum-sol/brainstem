
# V8 Phase6a - Neuromodulated Sleep Replay and Meta-Plasticity Release
# Project compass: no blacklist/filter system, no facts/relations/questions writes.
# This module adds an offline-style replay/consolidation layer after the active learning loop.

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PHASE = "phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _now() -> int:
    return int(time.time())


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        x = float(x)
    except Exception:
        x = 0.0
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _has_execute(obj: Any) -> bool:
    return hasattr(obj, "execute") and callable(getattr(obj, "execute"))


def resolve_db(obj: Any = None) -> sqlite3.Connection:
    """Resolve sqlite connection from AutonomousLoop/Memory/Connection or fallback path.

    This intentionally avoids assumptions about the Memory class used by the project.
    """
    if isinstance(obj, sqlite3.Connection):
        return obj
    if _has_execute(obj):
        return obj  # type: ignore[return-value]
    for name in ("mem", "memory", "m", "store", "memory_store"):
        child = getattr(obj, name, None)
        if isinstance(child, sqlite3.Connection):
            return child
        if _has_execute(child):
            return child  # type: ignore[return-value]
        for sub in ("conn", "con", "db", "sqlite", "connection"):
            grand = getattr(child, sub, None)
            if isinstance(grand, sqlite3.Connection):
                return grand
            if _has_execute(grand):
                return grand  # type: ignore[return-value]
    for sub in ("conn", "con", "db", "sqlite", "connection"):
        child = getattr(obj, sub, None)
        if isinstance(child, sqlite3.Connection):
            return child
        if _has_execute(child):
            return child  # type: ignore[return-value]
    # Project default: tools run from project root.
    return sqlite3.connect("ki_memory.sqlite3")


def table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def cols(db: sqlite3.Connection, table: str) -> List[str]:
    if not table_exists(db, table):
        return []
    return [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]


def add_col(db: sqlite3.Connection, table: str, column: str, decl: str, changes: List[str]) -> None:
    if not table_exists(db, table):
        return
    if column not in cols(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        changes.append(f"add_column:{table}.{column}")


def safe_unique_index(db: sqlite3.Connection, table: str, column: str, name: str, changes: List[str]) -> None:
    if not table_exists(db, table) or column not in cols(db, table):
        return
    try:
        db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table}({column})")
        changes.append(f"unique_index:{table}.{column}")
    except sqlite3.IntegrityError:
        # Existing duplicates should not crash learning. Keep schema guard non-destructive.
        changes.append(f"skip_unique_duplicates:{table}.{column}")
    except sqlite3.OperationalError as exc:
        changes.append(f"skip_unique_error:{table}.{column}:{exc}")


def kv_set(db: sqlite3.Connection, table: str, key: str, value: Any, now: Optional[int] = None) -> None:
    if now is None:
        now = _now()
    if not table_exists(db, table):
        return
    db.execute(
        f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) "
        f"ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, str(value).lower() if isinstance(value, bool) else str(value), now),
    )


def ensure_phase6a_schema(db: sqlite3.Connection) -> Dict[str, Any]:
    changes: List[str] = []

    db.execute("""
    CREATE TABLE IF NOT EXISTS phase6a_sleep_replay_cycles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        replay_mode TEXT,
        candidate_count INTEGER DEFAULT 0,
        replay_events INTEGER DEFAULT 0,
        avg_outcome_score REAL DEFAULT 0,
        avg_closure_delta REAL DEFAULT 0,
        avg_overlap_score REAL DEFAULT 0,
        persistent_gap_pressure REAL DEFAULT 0,
        plasticity_level REAL DEFAULT 0,
        exploration_bias REAL DEFAULT 0,
        consolidation_bias REAL DEFAULT 0,
        inhibition_bias REAL DEFAULT 0,
        revision_bias REAL DEFAULT 0,
        safety_ok INTEGER DEFAULT 1,
        details TEXT,
        created_at INTEGER
    )""")

    db.execute("""
    CREATE TABLE IF NOT EXISTS phase6a_sleep_replay_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        replay_key TEXT,
        source_table TEXT,
        source_id INTEGER,
        candidate_type TEXT,
        gap_key TEXT,
        role TEXT,
        replay_priority REAL DEFAULT 0,
        replay_weight REAL DEFAULT 0,
        outcome_score REAL DEFAULT 0,
        closure_delta REAL DEFAULT 0,
        overlap_score REAL DEFAULT 0,
        no_candidate_rate REAL DEFAULT 0,
        plasticity_level REAL DEFAULT 0,
        neuromodulator_profile TEXT,
        replay_decision TEXT,
        details TEXT,
        created_at INTEGER
    )""")

    db.execute("""
    CREATE TABLE IF NOT EXISTS phase6a_replay_candidates(
        candidate_key TEXT PRIMARY KEY,
        source_table TEXT,
        source_id INTEGER,
        candidate_type TEXT,
        gap_key TEXT,
        role TEXT,
        priority REAL DEFAULT 0,
        outcome_score REAL DEFAULT 0,
        closure_delta REAL DEFAULT 0,
        overlap_score REAL DEFAULT 0,
        no_candidate_rate REAL DEFAULT 0,
        replay_count INTEGER DEFAULT 0,
        last_replayed_at INTEGER,
        status TEXT DEFAULT 'candidate',
        details TEXT,
        created_at INTEGER,
        updated_at INTEGER
    )""")

    db.execute("""
    CREATE TABLE IF NOT EXISTS phase6a_meta_plasticity_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER
    )""")

    db.execute("""
    CREATE TABLE IF NOT EXISTS phase6a_neuromodulated_sleep_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER
    )""")

    db.execute("""
    CREATE TABLE IF NOT EXISTS phase6a_replay_memory(
        memory_key TEXT PRIMARY KEY,
        memory_type TEXT,
        observations INTEGER DEFAULT 0,
        avg_replay_weight REAL DEFAULT 0,
        avg_outcome_score REAL DEFAULT 0,
        avg_closure_delta REAL DEFAULT 0,
        avg_overlap_score REAL DEFAULT 0,
        avg_no_candidate_rate REAL DEFAULT 0,
        avg_plasticity_level REAL DEFAULT 0,
        recommendation TEXT,
        neuromodulator_profile TEXT,
        details TEXT,
        created_at INTEGER,
        updated_at INTEGER
    )""")

    db.execute("""
    CREATE TABLE IF NOT EXISTS phase6a_plasticity_adjustments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_table TEXT,
        target_id INTEGER,
        adjustment_type TEXT,
        old_value REAL DEFAULT 0,
        new_value REAL DEFAULT 0,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        reason TEXT,
        details TEXT,
        created_at INTEGER
    )""")

    # Future-tolerant columns in existing tables frequently touched by later phases.
    extensions = {
        "internal_learning_gaps": [
            ("phase6a_replay_priority", "REAL DEFAULT 0"),
            ("phase6a_replay_weight", "REAL DEFAULT 0"),
            ("phase6a_meta_plasticity", "REAL DEFAULT 0"),
            ("phase6a_plasticity_level", "REAL DEFAULT 0"),
            ("phase6a_sleep_replay_count", "INTEGER DEFAULT 0"),
            ("phase6a_last_replayed_at", "INTEGER"),
            ("phase6a_replay_decision", "TEXT"),
            ("phase6a_replay_reason", "TEXT"),
            ("phase6a_consolidation_bias", "REAL DEFAULT 0"),
            ("phase6a_exploration_bias", "REAL DEFAULT 0"),
            ("phase6a_inhibition_bias", "REAL DEFAULT 0"),
            ("phase6a_revision_bias", "REAL DEFAULT 0"),
            ("phase6a_dopamine", "REAL DEFAULT 0"),
            ("phase6a_serotonin", "REAL DEFAULT 0"),
            ("phase6a_glutamate", "REAL DEFAULT 0"),
            ("phase6a_gaba", "REAL DEFAULT 0"),
            ("phase6a_noradrenaline", "REAL DEFAULT 0"),
            ("phase6a_acetylcholine", "REAL DEFAULT 0"),
        ],
        "context_hypotheses": [
            ("phase6a_replay_priority", "REAL DEFAULT 0"),
            ("phase6a_replay_weight", "REAL DEFAULT 0"),
            ("phase6a_meta_plasticity", "REAL DEFAULT 0"),
            ("phase6a_sleep_replay_count", "INTEGER DEFAULT 0"),
            ("phase6a_last_replayed_at", "INTEGER"),
            ("phase6a_replay_reason", "TEXT"),
        ],
        "phase5g_experiment_outcomes": [
            ("phase6a_replay_priority", "REAL DEFAULT 0"),
            ("phase6a_replay_weight", "REAL DEFAULT 0"),
            ("phase6a_meta_plasticity", "REAL DEFAULT 0"),
            ("phase6a_sleep_replay_count", "INTEGER DEFAULT 0"),
            ("phase6a_last_replayed_at", "INTEGER"),
            ("phase6a_replay_decision", "TEXT"),
            ("phase6a_replay_reason", "TEXT"),
        ],
        "phase5h_strategy_outcome_memory": [
            ("phase6a_replay_weight", "REAL DEFAULT 0"),
            ("phase6a_meta_plasticity", "REAL DEFAULT 0"),
            ("phase6a_last_replayed_at", "INTEGER"),
            ("phase6a_replay_recommendation", "TEXT"),
        ],
        "chunk_attention_scores": [
            ("phase6a_sleep_priority", "REAL DEFAULT 0"),
            ("phase6a_replay_weight", "REAL DEFAULT 0"),
            ("phase6a_meta_plasticity", "REAL DEFAULT 0"),
            ("phase6a_last_adjusted_at", "INTEGER"),
            ("phase6a_reason", "TEXT"),
        ],
        "reading_queue": [
            ("phase6a_sleep_priority", "REAL DEFAULT 0"),
            ("phase6a_replay_weight", "REAL DEFAULT 0"),
            ("phase6a_meta_plasticity", "REAL DEFAULT 0"),
            ("phase6a_last_adjusted_at", "INTEGER"),
            ("phase6a_reason", "TEXT"),
        ],
    }
    for table, columns in extensions.items():
        for column, decl in columns:
            add_col(db, table, column, decl, changes)

    # Required indexes. Non-destructive if duplicates exist.
    safe_unique_index(db, "phase6a_replay_candidates", "candidate_key", "idx_phase6a_replay_candidates_candidate_key_unique", changes)
    safe_unique_index(db, "phase6a_meta_plasticity_state", "key", "idx_phase6a_meta_plasticity_state_key_unique", changes)
    safe_unique_index(db, "phase6a_neuromodulated_sleep_state", "key", "idx_phase6a_neuromodulated_sleep_state_key_unique", changes)
    safe_unique_index(db, "phase6a_replay_memory", "memory_key", "idx_phase6a_replay_memory_memory_key_unique", changes)
    for table, col, idx in [
        ("internal_learning_gaps", "gap_key", "idx_phase6a_internal_learning_gaps_gap_key_unique"),
        ("reading_queue", "chunk_id", "idx_phase6a_reading_queue_chunk_id_unique"),
        ("chunk_attention_scores", "chunk_id", "idx_phase6a_chunk_attention_scores_chunk_id_unique"),
        ("phase5g_experiment_outcomes", "outcome_key", "idx_phase6a_phase5g_experiment_outcomes_outcome_key_unique"),
    ]:
        safe_unique_index(db, table, col, idx, changes)

    now = _now()
    for t in ("phase6a_meta_plasticity_state", "phase6a_neuromodulated_sleep_state"):
        kv_set(db, t, "phase", PHASE, now)
        kv_set(db, t, "learning_mode", LEARNING_MODE, now)
        kv_set(db, t, "no_word_blacklists", "true", now)
        kv_set(db, t, "fact_promotion", "disabled", now)
        kv_set(db, t, "direct_fact_writes", "disabled", now)
        kv_set(db, t, "direct_relation_writes", "disabled", now)
        kv_set(db, t, "question_generation", "internal_learning_questions_only", now)

    return {"status": "ok", "phase": PHASE, "changes": changes, "no_word_blacklists": True, "fact_promotion": "disabled"}


def _count(db: sqlite3.Connection, table: str) -> int:
    if not table_exists(db, table):
        return 0
    try:
        return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return 0


_AVG_CACHE = {}

def _avg(db: sqlite3.Connection, table: str, column: str, default: float = 0.0) -> float:
    _ck = (id(db), table, column)
    if _ck in _AVG_CACHE:
        return _AVG_CACHE[_ck]
    if not table_exists(db, table) or column not in cols(db, table):
        _AVG_CACHE[_ck] = default
        return default
    try:
        val = db.execute(f"SELECT AVG(COALESCE({column},0)) FROM {table}").fetchone()[0]
        _res = float(val or default)
    except Exception:
        _res = default
    _AVG_CACHE[_ck] = _res
    return _res


def _safety(db: sqlite3.Connection) -> Dict[str, int]:
    return {"facts": _count(db, "facts"), "relations": _count(db, "relations"), "questions": _count(db, "questions")}


def _select_replay_candidates(db: sqlite3.Connection, limit: int = 180) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    now = _now()
    _AVG_CACHE.clear()  # PERF1B: fresh averages per cycle, cached within cycle

    if table_exists(db, "internal_learning_gaps"):
        columns = cols(db, "internal_learning_gaps")
        priority_expr = "COALESCE(phase5i_diversification_pressure, phase5e_expected_gain, priority, severity, 0)" if "phase5i_diversification_pressure" in columns else "COALESCE(priority, severity, 0)"
        res_expr = "COALESCE(resolution_score,0)" if "resolution_score" in columns else "0"
        rows = db.execute(
            f"SELECT rowid, COALESCE(gap_key,''), COALESCE(gap_type,'gap'), COALESCE(role,'unknown'), {priority_expr}, {res_expr} "
            f"FROM internal_learning_gaps ORDER BY {priority_expr} DESC, {res_expr} ASC, rowid DESC LIMIT ?",
            (limit // 3,),
        ).fetchall()
        for rid, gap_key, gap_type, role, priority, resolution in rows:
            pr = _clamp(float(priority or 0))
            out.append({
                "source_table": "internal_learning_gaps",
                "source_id": int(rid),
                "candidate_type": str(gap_type or "gap"),
                "gap_key": str(gap_key or f"gap:{rid}"),
                "role": str(role or "unknown"),
                "priority": pr,
                "outcome": _clamp(float(resolution or 0)),
                "closure": _clamp(float(resolution or 0)),
                "overlap": _avg(db, "phase5g_experiment_outcomes", "overlap_score", 0.0),
                "no_candidate": _avg(db, "phase5g_experiment_outcomes", "no_candidate_rate", 0.0),
            })

    if table_exists(db, "phase5g_experiment_outcomes"):
        c = cols(db, "phase5g_experiment_outcomes")
        outcome_col = "outcome_score" if "outcome_score" in c else "effectiveness_score" if "effectiveness_score" in c else "0"
        closure_col = "closure_delta" if "closure_delta" in c else "0"
        overlap_col = "overlap_score" if "overlap_score" in c else "0"
        no_cand_col = "no_candidate_rate" if "no_candidate_rate" in c else "no_candidate_penalty" if "no_candidate_penalty" in c else "0"
        rows = db.execute(
            f"SELECT rowid, COALESCE(gap_key,''), COALESCE(gap_type,'experiment'), COALESCE(role,'unknown'), "
            f"COALESCE({outcome_col},0), COALESCE({closure_col},0), COALESCE({overlap_col},0), COALESCE({no_cand_col},0) "
            f"FROM phase5g_experiment_outcomes "
            f"ORDER BY COALESCE({outcome_col},0) ASC, COALESCE({overlap_col},0) DESC, rowid DESC LIMIT ?",
            (limit // 3,),
        ).fetchall()
        for rid, gap_key, gap_type, role, outcome, closure, overlap, no_candidate in rows:
            out.append({
                "source_table": "phase5g_experiment_outcomes",
                "source_id": int(rid),
                "candidate_type": "weak_strategy_experiment",
                "gap_key": str(gap_key or f"experiment:{rid}"),
                "role": str(role or "unknown"),
                "priority": _clamp(1.0 - float(outcome or 0)),
                "outcome": _clamp(float(outcome or 0)),
                "closure": _clamp(float(closure or 0)),
                "overlap": _clamp(float(overlap or 0)),
                "no_candidate": _clamp(float(no_candidate or 0)),
            })

    if table_exists(db, "context_hypotheses"):
        c = cols(db, "context_hypotheses")
        unc = "uncertainty" if "uncertainty" in c else "0"
        conf = "confidence" if "confidence" in c else "0"
        role_col = "role" if "role" in c else "'hypothesis'"
        rows = db.execute(
            f"SELECT rowid, COALESCE({role_col},'hypothesis'), COALESCE({conf},0), COALESCE({unc},0) "
            f"FROM context_hypotheses ORDER BY COALESCE({unc},0) DESC, rowid DESC LIMIT ?",
            (limit // 3,),
        ).fetchall()
        for rid, role, confv, uncv in rows:
            uncertainty = _clamp(float(uncv or 0))
            confidence = _clamp(float(confv or 0))
            out.append({
                "source_table": "context_hypotheses",
                "source_id": int(rid),
                "candidate_type": "uncertain_hypothesis_replay",
                "gap_key": f"hypothesis:{rid}",
                "role": str(role or "hypothesis"),
                "priority": uncertainty,
                "outcome": confidence,
                "closure": max(0.0, confidence - (1.0 - uncertainty)),
                "overlap": _avg(db, "phase5g_experiment_outcomes", "overlap_score", 0.0),
                "no_candidate": _avg(db, "phase5g_experiment_outcomes", "no_candidate_rate", 0.0),
            })

    # Stable deterministic order.
    out.sort(key=lambda x: (float(x.get("priority", 0)), float(x.get("overlap", 0))), reverse=True)
    return out[:limit]


def sleep_replay_and_meta_plasticity(db_or_obj: Any = None, replay_limit: int = 180) -> Dict[str, Any]:
    db = resolve_db(db_or_obj)
    ensure_phase6a_schema(db)
    now = _now()

    candidates = _select_replay_candidates(db, replay_limit)
    if not candidates:
        candidates = []

    n = max(1, len(candidates))
    avg_outcome = sum(float(c.get("outcome", 0)) for c in candidates) / n
    avg_closure = sum(float(c.get("closure", 0)) for c in candidates) / n
    avg_overlap = sum(float(c.get("overlap", 0)) for c in candidates) / n
    avg_no_candidate = sum(float(c.get("no_candidate", 0)) for c in candidates) / n
    persistent_pressure = _clamp(1.0 - avg_closure + avg_overlap * 0.35 + (1.0 - avg_outcome) * 0.25)

    plasticity = _clamp(0.28 + persistent_pressure * 0.35 + avg_overlap * 0.18 + (1.0 - avg_outcome) * 0.15)
    exploration_bias = _clamp(0.30 + avg_overlap * 0.35 + (1.0 - avg_outcome) * 0.20 + avg_no_candidate * 0.10)
    consolidation_bias = _clamp(0.25 + avg_closure * 0.45 + avg_outcome * 0.25 - persistent_pressure * 0.18)
    inhibition_bias = _clamp(0.20 + avg_no_candidate * 0.35 + avg_overlap * 0.12)
    revision_bias = _clamp(0.25 + persistent_pressure * 0.40 + (1.0 - avg_outcome) * 0.20)

    dopamine = _clamp(0.25 + avg_outcome * 0.45 + avg_closure * 0.25)
    serotonin = _clamp(0.25 + consolidation_bias * 0.55)
    glutamate = _clamp(0.30 + exploration_bias * 0.55)
    gaba = _clamp(0.20 + inhibition_bias * 0.60)
    noradrenaline = _clamp(0.25 + persistent_pressure * 0.45 + avg_overlap * 0.15)
    acetylcholine = _clamp(0.30 + (1.0 - avg_overlap) * 0.25 + revision_bias * 0.25)
    nm = {
        "dopamine": round(dopamine, 6),
        "serotonin": round(serotonin, 6),
        "glutamate_drive": round(glutamate, 6),
        "gaba_drive": round(gaba, 6),
        "noradrenaline": round(noradrenaline, 6),
        "acetylcholine": round(acetylcholine, 6),
    }
    # BRAINSTEM_EI_DRIVE_STATE_SPLIT_V1: Phase6a emits drive, not persistent E/I state.

    replayed = 0
    for c in candidates:
        src = c["source_table"]
        sid = int(c["source_id"])
        key = f"{src}:{sid}:{c.get('candidate_type')}"
        priority = _clamp(float(c.get("priority", 0)))
        outcome = _clamp(float(c.get("outcome", 0)))
        closure = _clamp(float(c.get("closure", 0)))
        overlap = _clamp(float(c.get("overlap", 0)))
        no_candidate = _clamp(float(c.get("no_candidate", 0)))
        replay_weight = _clamp(priority * 0.35 + (1.0 - outcome) * 0.25 + overlap * 0.20 + persistent_pressure * 0.20)
        decision = "replay_for_reorganization" if replay_weight >= 0.55 else "observe_low_replay_weight"
        details = {
            "source_table": src,
            "source_id": sid,
            "persistent_pressure": persistent_pressure,
            "plasticity": plasticity,
            "exploration_bias": exploration_bias,
            "consolidation_bias": consolidation_bias,
            "inhibition_bias": inhibition_bias,
            "revision_bias": revision_bias,
        }
        db.execute(
            "INSERT INTO phase6a_replay_candidates(candidate_key,source_table,source_id,candidate_type,gap_key,role,priority,outcome_score,closure_delta,overlap_score,no_candidate_rate,replay_count,last_replayed_at,status,details,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(candidate_key) DO UPDATE SET priority=excluded.priority,outcome_score=excluded.outcome_score,closure_delta=excluded.closure_delta,overlap_score=excluded.overlap_score,no_candidate_rate=excluded.no_candidate_rate,replay_count=phase6a_replay_candidates.replay_count+1,last_replayed_at=excluded.last_replayed_at,status=excluded.status,details=excluded.details,updated_at=excluded.updated_at",
            (key, src, sid, c.get("candidate_type"), c.get("gap_key"), c.get("role"), priority, outcome, closure, overlap, no_candidate, 1, now, "replayed", _j(details), now, now),
        )
        db.execute(
            "INSERT INTO phase6a_sleep_replay_events(replay_key,source_table,source_id,candidate_type,gap_key,role,replay_priority,replay_weight,outcome_score,closure_delta,overlap_score,no_candidate_rate,plasticity_level,neuromodulator_profile,replay_decision,details,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (key, src, sid, c.get("candidate_type"), c.get("gap_key"), c.get("role"), priority, replay_weight, outcome, closure, overlap, no_candidate, plasticity, _j(nm), decision, _j(details), now),
        )
        # Non-destructive target updates.
        if src == "internal_learning_gaps" and table_exists(db, src):
            db.execute(
                "UPDATE internal_learning_gaps SET phase6a_replay_priority=?, phase6a_replay_weight=?, phase6a_meta_plasticity=?, phase6a_plasticity_level=?, phase6a_sleep_replay_count=COALESCE(phase6a_sleep_replay_count,0)+1, phase6a_last_replayed_at=?, phase6a_replay_decision=?, phase6a_replay_reason=?, phase6a_consolidation_bias=?, phase6a_exploration_bias=?, phase6a_inhibition_bias=?, phase6a_revision_bias=?, phase6a_dopamine=?, phase6a_serotonin=?, phase6a_glutamate=?, phase6a_gaba=?, phase6a_noradrenaline=?, phase6a_acetylcholine=? WHERE rowid=?",
                (priority, replay_weight, plasticity, plasticity, now, decision, PHASE, consolidation_bias, exploration_bias, inhibition_bias, revision_bias, dopamine, serotonin, glutamate, gaba, noradrenaline, acetylcholine, sid),
            )
        elif src == "context_hypotheses" and table_exists(db, src):
            db.execute(
                "UPDATE context_hypotheses SET phase6a_replay_priority=?, phase6a_replay_weight=?, phase6a_meta_plasticity=?, phase6a_sleep_replay_count=COALESCE(phase6a_sleep_replay_count,0)+1, phase6a_last_replayed_at=?, phase6a_replay_reason=? WHERE rowid=?",
                (priority, replay_weight, plasticity, now, PHASE, sid),
            )
        elif src == "phase5g_experiment_outcomes" and table_exists(db, src):
            db.execute(
                "UPDATE phase5g_experiment_outcomes SET phase6a_replay_priority=?, phase6a_replay_weight=?, phase6a_meta_plasticity=?, phase6a_sleep_replay_count=COALESCE(phase6a_sleep_replay_count,0)+1, phase6a_last_replayed_at=?, phase6a_replay_decision=?, phase6a_replay_reason=? WHERE rowid=?",
                (priority, replay_weight, plasticity, now, decision, PHASE, sid),
            )
        replayed += 1

    # Update global memories.
    for memory_key, memory_type in (
        ("global_sleep_replay_memory", "global"),
        ("persistent_gap_sleep_replay_memory", "persistent_gap"),
        ("strategy_outcome_sleep_replay_memory", "strategy_outcome"),
    ):
        existing = db.execute("SELECT observations FROM phase6a_replay_memory WHERE memory_key=?", (memory_key,)).fetchone()
        obs = int(existing[0]) + 1 if existing else 1
        recommendation = "increase_exploration_and_replay" if persistent_pressure > 0.75 else "consolidate_observed_patterns"
        db.execute(
            "INSERT INTO phase6a_replay_memory(memory_key,memory_type,observations,avg_replay_weight,avg_outcome_score,avg_closure_delta,avg_overlap_score,avg_no_candidate_rate,avg_plasticity_level,recommendation,neuromodulator_profile,details,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(memory_key) DO UPDATE SET observations=excluded.observations, avg_replay_weight=excluded.avg_replay_weight, avg_outcome_score=excluded.avg_outcome_score, avg_closure_delta=excluded.avg_closure_delta, avg_overlap_score=excluded.avg_overlap_score, avg_no_candidate_rate=excluded.avg_no_candidate_rate, avg_plasticity_level=excluded.avg_plasticity_level, recommendation=excluded.recommendation, neuromodulator_profile=excluded.neuromodulator_profile, details=excluded.details, updated_at=excluded.updated_at",
            (memory_key, memory_type, obs, plasticity, avg_outcome, avg_closure, avg_overlap, avg_no_candidate, plasticity, recommendation, _j(nm), _j({"persistent_gap_pressure": persistent_pressure}), now, now),
        )

    db.execute(
        "INSERT INTO phase6a_sleep_replay_cycles(replay_mode,candidate_count,replay_events,avg_outcome_score,avg_closure_delta,avg_overlap_score,persistent_gap_pressure,plasticity_level,exploration_bias,consolidation_bias,inhibition_bias,revision_bias,safety_ok,details,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("offline_replay_after_wake_cycle", len(candidates), replayed, avg_outcome, avg_closure, avg_overlap, persistent_pressure, plasticity, exploration_bias, consolidation_bias, inhibition_bias, revision_bias, 1 if _safety(db) == {"facts": 0, "relations": 0, "questions": 0} else 0, _j({"neuromodulators": nm, "no_word_blacklists": True}), now),
    )

    # State tables.
    state_vals = {
        "last_replay_at": now,
        "last_candidate_count": len(candidates),
        "last_replay_events": replayed,
        "last_avg_outcome_score": round(avg_outcome, 6),
        "last_avg_closure_delta": round(avg_closure, 6),
        "last_avg_overlap_score": round(avg_overlap, 6),
        "last_avg_no_candidate_rate": round(avg_no_candidate, 6),
        "last_persistent_gap_pressure": round(persistent_pressure, 6),
        "last_plasticity_level": round(plasticity, 6),
        "last_exploration_bias": round(exploration_bias, 6),
        "last_consolidation_bias": round(consolidation_bias, 6),
        "last_inhibition_bias": round(inhibition_bias, 6),
        "last_revision_bias": round(revision_bias, 6),
        "phase": PHASE,
        "no_word_blacklists": "true",
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
    }
    for k, v in state_vals.items():
        kv_set(db, "phase6a_meta_plasticity_state", k, v, now)
    for k, v in {**state_vals, **nm}.items():
        kv_set(db, "phase6a_neuromodulated_sleep_state", k, v, now)

    db.commit()
    return {
        "status": "phase6a_sleep_replay_meta_plasticity_complete",
        "phase": PHASE,
        "candidate_count": len(candidates),
        "replay_events": replayed,
        "avg_outcome_score": round(avg_outcome, 6),
        "avg_closure_delta": round(avg_closure, 6),
        "avg_overlap_score": round(avg_overlap, 6),
        "avg_no_candidate_rate": round(avg_no_candidate, 6),
        "persistent_gap_pressure": round(persistent_pressure, 6),
        "plasticity_level": round(plasticity, 6),
        "exploration_bias": round(exploration_bias, 6),
        "consolidation_bias": round(consolidation_bias, 6),
        "inhibition_bias": round(inhibition_bias, 6),
        "revision_bias": round(revision_bias, 6),
        "neuromodulators": nm,
        **_safety(db),
        "no_word_blacklists": True,
        "fact_promotion": "disabled",
    }


def managed_cycle(self, progress=None):
    # Wake phase: use current top runtime if available.
    base_result: Any = None
    try:
        from ki_system import v8_phase5i_outcome_driven_context_strategy_diversification_release as base
        if getattr(base, "managed_cycle", None) is not managed_cycle:
            base_result = base.managed_cycle(self, progress)
    except Exception as exc:
        base_result = {"base_cycle_error": str(exc)}
    # Sleep phase: replay/consolidation after wake processing.
    try:
        db = resolve_db(self)
        replay = sleep_replay_and_meta_plasticity(db)
    except Exception as exc:
        replay = {"status": "phase6a_sleep_replay_error", "error": str(exc), "phase": PHASE}
    return {"phase": PHASE, "wake_result": base_result, "sleep_replay": replay}


def managed_run(self, cycles=1, progress=None):
    results = []
    try:
        cycles = int(cycles or 1)
    except Exception:
        cycles = 1
    for i in range(max(1, cycles)):
        results.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(results), "results": results}


def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release = True
    AutonomousLoop._phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = "disabled"
    return AutonomousLoop
