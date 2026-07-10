# V8-phase4p_gap_resolution_and_learning_outcome_tracking
# Projekt-Kompass: keine Wort-Blacklists, keine facts/relations/questions, Hypothesen bleiben Hypothesen.
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

PHASE = "phase4p_gap_resolution_and_learning_outcome_tracking"
NO_WORD_BLACKLISTS = True
LEARNING_MODE = "context_hypotheses_with_neuromodulators"
FACT_PROMOTION = "disabled"

_PREV_RUN = None
_PREV_CYCLE = None


def _clamp(x: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        v = float(x)
    except Exception:
        v = 0.0
    return max(lo, min(hi, v))


def _json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"repr": repr(obj)}, ensure_ascii=False)


def _db_path() -> Path:
    # GUI und Tools laufen im Projektwurzelordner. Falls nicht, Eltern prüfen.
    candidates = [Path.cwd() / "ki_memory.sqlite3", Path(__file__).resolve().parents[1] / "ki_memory.sqlite3"]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _connect(mem: Any = None) -> sqlite3.Connection:
    # Bewusst robust: falls Memory eine Connection besitzt, nutzen; sonst Projekt-DB.
    for attr in ("conn", "con", "connection", "db"):
        obj = getattr(mem, attr, None) if mem is not None else None
        if isinstance(obj, sqlite3.Connection):
            return obj
    return sqlite3.connect(str(_db_path()))


def _has_table(cur: sqlite3.Cursor, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(cur: sqlite3.Cursor, table: str) -> set:
    if not _has_table(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_col(cur: sqlite3.Cursor, table: str, name: str, decl: str, changes: list) -> None:
    if not _has_table(cur, table):
        return
    if name not in _columns(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
        changes.append(f"add_column:{table}.{name}")


def _unique(cur: sqlite3.Cursor, table: str, col: str, changes: list) -> None:
    if not _has_table(cur, table):
        return
    if col not in _columns(cur, table):
        return
    # Nur setzen, wenn keine Duplikate bestehen; ansonsten nicht crashen.
    try:
        dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
        if dup:
            changes.append(f"skip_unique_duplicates:{table}.{col}")
            return
        idx = f"idx_{table}_{col}_phase4p_unique"
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")
    except Exception as exc:
        changes.append(f"skip_unique_error:{table}.{col}:{exc}")


def ensure_phase4p_schema(mem: Any = None) -> Dict[str, Any]:
    db = _connect(mem)
    owns = not any(isinstance(getattr(mem, a, None), sqlite3.Connection) for a in ("conn", "con", "connection", "db")) if mem is not None else True
    cur = db.cursor()
    changes = []

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gap_resolution_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gap_id INTEGER,
        gap_key TEXT,
        gap_type TEXT,
        role TEXT,
        before_priority REAL DEFAULT 0,
        after_priority REAL DEFAULT 0,
        before_effectiveness REAL DEFAULT 0,
        after_effectiveness REAL DEFAULT 0,
        evidence_before REAL DEFAULT 0,
        evidence_after REAL DEFAULT 0,
        uncertainty_before REAL DEFAULT 0,
        uncertainty_after REAL DEFAULT 0,
        stability_before REAL DEFAULT 0,
        stability_after REAL DEFAULT 0,
        resolution_score REAL DEFAULT 0,
        outcome TEXT,
        action TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS learning_outcome_tracking_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        target_table TEXT,
        target_id INTEGER,
        target_key TEXT,
        outcome_score REAL DEFAULT 0,
        progress_delta REAL DEFAULT 0,
        error_pressure REAL DEFAULT 0,
        uncertainty_pressure REAL DEFAULT 0,
        stability_gain REAL DEFAULT 0,
        recommendation TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS strategy_gap_resolution_memory (
        strategy_key TEXT PRIMARY KEY,
        observations INTEGER DEFAULT 0,
        avg_resolution_score REAL DEFAULT 0,
        avg_outcome_score REAL DEFAULT 0,
        resolved_count INTEGER DEFAULT 0,
        persistent_count INTEGER DEFAULT 0,
        last_recommendation TEXT,
        updated_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gap_resolution_state (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )
    """)

    # Robust future-proof columns for core tables.
    for col, decl in [
        ("priority", "REAL DEFAULT 0"),
        ("strategy_effectiveness_score", "REAL DEFAULT 0"),
        ("strategy_feedback_reason", "TEXT"),
        ("last_strategy_feedback_at", "INTEGER DEFAULT 0"),
        ("resolution_score", "REAL DEFAULT 0"),
        ("resolution_status", "TEXT DEFAULT 'open'"),
        ("last_resolution_evaluated_at", "INTEGER DEFAULT 0"),
        ("resolution_reason", "TEXT"),
        ("learning_outcome_score", "REAL DEFAULT 0"),
        ("priority_decay", "REAL DEFAULT 0"),
        ("effectiveness_evidence_count", "INTEGER DEFAULT 0"),
        ("last_resolution_outcome", "TEXT"),
        ("resolution_attempts", "INTEGER DEFAULT 0"),
        ("resolved_at", "INTEGER DEFAULT 0"),
    ]:
        _add_col(cur, "internal_learning_gaps", col, decl, changes)

    for col, decl in [
        ("learning_outcome_score", "REAL DEFAULT 0"),
        ("last_outcome_tracked_at", "INTEGER DEFAULT 0"),
        ("outcome_tracking_reason", "TEXT"),
        ("resolution_support_score", "REAL DEFAULT 0"),
    ]:
        _add_col(cur, "context_hypotheses", col, decl, changes)

    for col, decl in [
        ("learning_outcome_score", "REAL DEFAULT 0"),
        ("last_outcome_tracked_at", "INTEGER DEFAULT 0"),
        ("outcome_tracking_reason", "TEXT"),
    ]:
        _add_col(cur, "chunk_attention_scores", col, decl, changes)

    for table, col in [
        ("internal_learning_gaps", "gap_key"),
        ("gap_resolution_state", "key"),
        ("strategy_gap_resolution_memory", "strategy_key"),
        ("reading_queue", "chunk_id"),
        ("chunk_attention_scores", "chunk_id"),
        ("active_learning_loop_state", "key"),
        ("strategy_effectiveness_feedback_state", "key"),
        ("progress_evaluation_state", "key"),
    ]:
        _unique(cur, table, col, changes)

    now = int(time.time())
    # Backfill priority/effectiveness if empty/zero.
    if _has_table(cur, "internal_learning_gaps") and "priority" in _columns(cur, "internal_learning_gaps"):
        cur.execute("""
            UPDATE internal_learning_gaps
            SET priority = CASE
                WHEN COALESCE(priority,0)=0 THEN MIN(1.0, MAX(COALESCE(severity,0), COALESCE(uncertainty,0), COALESCE(revision_pressure,0), COALESCE(error_weight,0)))
                ELSE priority END
        """)
        changes.append("backfill:internal_learning_gaps.priority")

    state = {
        "phase": PHASE,
        "no_word_blacklists": "true",
        "fact_promotion": FACT_PROMOTION,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
        "learning_mode": LEARNING_MODE,
    }
    for k, v in state.items():
        cur.execute("INSERT OR REPLACE INTO gap_resolution_state(key,value,updated_at) VALUES(?,?,?)", (k, str(v), now))

    db.commit()
    if owns:
        db.close()
    return {"status": "ok", "phase": PHASE, "changes": changes, "no_word_blacklists": True, "fact_promotion": FACT_PROMOTION}


def _state_float(cur: sqlite3.Cursor, table: str, key: str, default: float) -> float:
    if not _has_table(cur, table):
        return default
    try:
        row = cur.execute(f"SELECT value FROM {table} WHERE key=?", (key,)).fetchone()
        return float(row[0]) if row else default
    except Exception:
        return default


def _pattern_stability(cur: sqlite3.Cursor, pattern_key: Optional[str]) -> float:
    if not pattern_key or not _has_table(cur, "long_term_pattern_memory"):
        return 0.0
    cols = _columns(cur, "long_term_pattern_memory")
    if "pattern_key" not in cols or "stability" not in cols:
        return 0.0
    row = cur.execute("SELECT stability FROM long_term_pattern_memory WHERE pattern_key=?", (pattern_key,)).fetchone()
    return _clamp(row[0]) if row else 0.0


def evaluate_gap_resolutions(mem: Any = None, limit: int = 240) -> Dict[str, Any]:
    ensure_phase4p_schema(mem)
    db = _connect(mem)
    owns = not any(isinstance(getattr(mem, a, None), sqlite3.Connection) for a in ("conn", "con", "connection", "db")) if mem is not None else True
    cur = db.cursor()
    now = int(time.time())
    if not _has_table(cur, "internal_learning_gaps"):
        return {"status": "skip", "reason": "internal_learning_gaps_missing", "phase": PHASE}

    cols = _columns(cur, "internal_learning_gaps")
    select_cols = ["id", "gap_key", "gap_type", "role", "pattern_key", "severity", "uncertainty", "revision_pressure", "error_weight", "evidence_count", "priority", "strategy_effectiveness_score", "status", "resolution_attempts"]
    for c in select_cols:
        if c not in cols:
            # schema guard should handle this, but keep runtime safe.
            return {"status": "schema_incomplete", "missing": c, "phase": PHASE}
    rows = cur.execute(f"""
        SELECT {','.join(select_cols)}
        FROM internal_learning_gaps
        WHERE COALESCE(status,'open') NOT IN ('closed','resolved')
        ORDER BY COALESCE(priority,0) DESC, COALESCE(severity,0) DESC, id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    learning_rate = _state_float(cur, "active_learning_loop_state", "last_learning_rate", 0.234)
    error_weight_state = _state_float(cur, "active_learning_loop_state", "last_error_weight", 0.407)
    revision_state = _state_float(cur, "active_learning_loop_state", "last_revision_pressure", 0.312)
    exploration = _state_float(cur, "active_learning_loop_state", "last_exploration_pressure", 0.31)
    inhibition = _state_float(cur, "active_learning_loop_state", "last_inhibition_level", 0.349)

    evaluated = improved = persistent = monitoring = closed = 0
    total_resolution = 0.0
    total_priority = 0.0
    sample = []
    for row in rows:
        (gid, gap_key, gap_type, role, pattern_key, severity, uncertainty, revision_pressure, err_weight, evidence, before_priority, before_eff, status, attempts) = row
        sev = _clamp(severity)
        unc = _clamp(uncertainty)
        rev = _clamp(revision_pressure if revision_pressure is not None else revision_state)
        err = _clamp(err_weight if err_weight is not None else error_weight_state)
        ev = max(0.0, float(evidence or 0.0))
        before_p = _clamp(before_priority)
        before_e = _clamp(before_eff)
        attempts = int(attempts or 0)
        st = _pattern_stability(cur, pattern_key)
        evidence_gain = _clamp(ev / 10.0)

        # Effectiveness darf nicht dauerhaft 0 bleiben, wenn Fortschrittssignale vorhanden sind.
        inferred_effectiveness = _clamp((st * 0.35) + ((1.0 - unc) * 0.20) + (evidence_gain * 0.15) + (learning_rate * 0.15) + ((1.0 - inhibition) * 0.15))
        after_eff = max(before_e, inferred_effectiveness)

        resolution_score = _clamp((after_eff * 0.35) + (st * 0.25) + ((1.0 - unc) * 0.20) + (evidence_gain * 0.10) + ((1.0 - sev) * 0.10))
        # Offene Priorität bleibt hoch, wenn Unsicherheit/Fehlerdruck hoch; sinkt leicht bei Evidenz/Stabilität.
        base_priority = _clamp((sev * 0.30) + (unc * 0.25) + (rev * 0.15) + (err * 0.15) + ((1.0 - resolution_score) * 0.15))
        decay = _clamp(resolution_score * 0.22, 0.0, 0.22)
        after_priority = _clamp(base_priority * (1.0 - decay))

        if resolution_score >= 0.74 and unc < 0.45 and st > 0.55:
            outcome = "partially_resolved"
            new_status = "monitoring"
            improved += 1
            monitoring += 1
        elif resolution_score >= before_e + 0.08:
            outcome = "improving"
            new_status = "open"
            improved += 1
        else:
            outcome = "persistent_gap"
            new_status = status or "open"
            persistent += 1

        # Phase4p löst nicht aggressiv endgültig; es trackt Outcome. Vollständiges Schließen späterer Freigabe vorbehalten.
        if outcome == "partially_resolved" and attempts >= 3 and resolution_score > 0.82:
            new_status = "monitoring"

        details = {
            "severity": sev,
            "uncertainty": unc,
            "revision_pressure": rev,
            "error_weight": err,
            "pattern_stability": st,
            "evidence_count": ev,
            "learning_rate": learning_rate,
            "exploration_pressure": exploration,
            "inhibition_level": inhibition,
            "project_compass": "no_word_blacklists_context_hypotheses_neuromodulated_learning",
        }
        cur.execute("""
            INSERT INTO gap_resolution_outcomes(
                gap_id,gap_key,gap_type,role,before_priority,after_priority,before_effectiveness,after_effectiveness,
                evidence_before,evidence_after,uncertainty_before,uncertainty_after,stability_before,stability_after,
                resolution_score,outcome,action,details,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (gid, gap_key, gap_type, role, before_p, after_priority, before_e, after_eff, ev, ev, unc, unc, st, st, resolution_score, outcome, "phase4p_gap_resolution_tracking", _json(details), now))
        cur.execute("""
            UPDATE internal_learning_gaps
            SET priority=?, strategy_effectiveness_score=?, resolution_score=?, resolution_status=?,
                last_resolution_evaluated_at=?, resolution_reason=?, learning_outcome_score=?, priority_decay=?,
                effectiveness_evidence_count=COALESCE(effectiveness_evidence_count,0)+1,
                resolution_attempts=COALESCE(resolution_attempts,0)+1,
                last_resolution_outcome=?, updated_at=?
            WHERE id=?
        """, (after_priority, after_eff, resolution_score, new_status, now, PHASE, resolution_score, decay, outcome, now, gid))
        total_resolution += resolution_score
        total_priority += after_priority
        evaluated += 1
        if len(sample) < 12:
            sample.append({"gap_id": gid, "type": gap_type, "role": role, "before_priority": round(before_p,3), "after_priority": round(after_priority,3), "resolution_score": round(resolution_score,3), "outcome": outcome})

    avg_resolution = total_resolution / evaluated if evaluated else 0.0
    avg_priority = total_priority / evaluated if evaluated else 0.0
    strategy_key = "gap_resolution_tracking_global"
    old = cur.execute("SELECT observations, avg_resolution_score, avg_outcome_score, resolved_count, persistent_count FROM strategy_gap_resolution_memory WHERE strategy_key=?", (strategy_key,)).fetchone()
    if old:
        obs, old_res, old_out, old_resolved, old_persist = old
        obs = int(obs or 0) + 1
        new_res = ((float(old_res or 0) * (obs-1)) + avg_resolution) / obs
        new_out = ((float(old_out or 0) * (obs-1)) + (1.0 if improved > persistent else 0.45)) / obs
        resolved_count = int(old_resolved or 0) + improved
        persistent_count = int(old_persist or 0) + persistent
        cur.execute("UPDATE strategy_gap_resolution_memory SET observations=?, avg_resolution_score=?, avg_outcome_score=?, resolved_count=?, persistent_count=?, last_recommendation=?, updated_at=? WHERE strategy_key=?",
                    (obs, new_res, new_out, resolved_count, persistent_count, "observe_and_refine_gap_resolution", now, strategy_key))
    else:
        cur.execute("INSERT INTO strategy_gap_resolution_memory(strategy_key,observations,avg_resolution_score,avg_outcome_score,resolved_count,persistent_count,last_recommendation,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (strategy_key, 1, avg_resolution, 1.0 if improved > persistent else 0.45, improved, persistent, "observe_and_refine_gap_resolution", now))

    cur.execute("INSERT INTO learning_outcome_tracking_events(event_type,target_table,target_key,outcome_score,progress_delta,error_pressure,uncertainty_pressure,stability_gain,recommendation,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("gap_resolution_evaluation", "internal_learning_gaps", strategy_key, avg_resolution, avg_resolution - avg_priority, error_weight_state, avg_priority, avg_resolution, "observe_and_refine_gap_resolution", _json({"evaluated": evaluated, "improved": improved, "persistent": persistent, "sample": sample}), now))

    state = {
        "phase": PHASE,
        "last_evaluated_gaps": str(evaluated),
        "last_improved_gaps": str(improved),
        "last_persistent_gaps": str(persistent),
        "last_monitoring_gaps": str(monitoring),
        "last_avg_resolution_score": str(round(avg_resolution, 6)),
        "last_avg_priority": str(round(avg_priority, 6)),
        "no_word_blacklists": "true",
        "learning_mode": LEARNING_MODE,
        "fact_promotion": FACT_PROMOTION,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
    }
    for k, v in state.items():
        cur.execute("INSERT OR REPLACE INTO gap_resolution_state(key,value,updated_at) VALUES(?,?,?)", (k, v, now))
    db.commit()
    if owns:
        db.close()
    return {"status": "phase4p_gap_resolution_tracking_complete", "phase": PHASE, "evaluated_gaps": evaluated, "improved_gaps": improved, "persistent_gaps": persistent, "monitoring_gaps": monitoring, "avg_resolution_score": round(avg_resolution,6), "avg_priority": round(avg_priority,6), "no_word_blacklists": True, "fact_promotion": FACT_PROMOTION, "sample": sample}


def managed_cycle(self, progress=None):
    ensure_phase4p_schema(getattr(self, 'mem', None))
    result = None
    if _PREV_CYCLE is not None:
        result = _PREV_CYCLE(self, progress)
    else:
        result = {"status": "phase4p_no_previous_cycle"}
    summary = evaluate_gap_resolutions(getattr(self, 'mem', None))
    if isinstance(result, dict):
        result["gap_resolution_outcome_tracking"] = summary
        return result
    return {"previous_result": result, "gap_resolution_outcome_tracking": summary}


def managed_run(self, cycles=1, progress=None):
    ensure_phase4p_schema(getattr(self, 'mem', None))
    result = None
    if _PREV_RUN is not None:
        result = _PREV_RUN(self, cycles, progress)
    else:
        out = []
        for _ in range(cycles or 1):
            out.append(managed_cycle(self, progress))
        result = out
    summary = evaluate_gap_resolutions(getattr(self, 'mem', None))
    # GUI erwartet JSON-serialisierbare Struktur.
    if isinstance(result, list):
        result.append({"phase4p_gap_resolution_outcome_tracking": summary})
        return result
    if isinstance(result, dict):
        result["phase4p_gap_resolution_outcome_tracking"] = summary
        return result
    return {"previous_result": result, "phase4p_gap_resolution_outcome_tracking": summary}


def patch_autonomous_loop(AutonomousLoop=None):
    global _PREV_RUN, _PREV_CYCLE
    if AutonomousLoop is None:
        try:
            from ki_system.autonomous import AutonomousLoop as AL
            AutonomousLoop = AL
        except Exception:
            return False
    if getattr(AutonomousLoop, "phase4p_gap_resolution_and_learning_outcome_tracking", False):
        return True
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    # Marka both with and without underscore for older tests.
    AutonomousLoop.phase4p_gap_resolution_and_learning_outcome_tracking = True
    AutonomousLoop._phase4p_gap_resolution_and_learning_outcome_tracking = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop._learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = FACT_PROMOTION
    AutonomousLoop._fact_promotion = FACT_PROMOTION
    # Keep previous phase markers visible.
    for name in [
        "phase4o_strategy_effectiveness_feedback_loop",
        "phase4n_learning_progress_evaluation_and_adaptive_strategy",
        "phase4m_active_learning_loop_controller",
        "phase4l_gap_cluster_planning_and_strategy_balance",
        "phase4k_gap_driven_rereading_and_learning_strategy",
        "phase4j_internal_learning_questions_and_gap_detection",
        "phase4i_long_term_memory_and_pattern_stability",
        "phase4h_self_evaluation_and_revision_core",
        "phase4g_neuromodulated_learning_control",
    ]:
        setattr(AutonomousLoop, name, True)
        setattr(AutonomousLoop, "_" + name, True)
    return True
