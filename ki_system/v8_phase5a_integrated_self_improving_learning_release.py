# V8-phase5a_integrated_self_improving_learning_release
# Projekt-Kompass:
# - kein Filter-/Blacklist-System
# - Kontext-Hypothesen, Fehlerlernen, digitale Botenstoffe, Konsolidierung, Selbstverbesserung
# - keine facts/relations/questions, keine Fact-Promotion
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from ki_system import v8_modern_gap_phase5f_shadow_observation_release as gap_phase5f_shadow_observation

PHASE = "phase5a_integrated_self_improving_learning_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"
FACT_PROMOTION = "disabled"
NO_WORD_BLACKLISTS = True

_PREV_RUN = None
_PREV_CYCLE = None

CORE_PHASE_MARKERS = [
    "phase4p_gap_resolution_and_learning_outcome_tracking",
    "phase4o_strategy_effectiveness_feedback_loop",
    "phase4n_learning_progress_evaluation_and_adaptive_strategy",
    "phase4m_active_learning_loop_controller",
    "phase4l_gap_cluster_planning_and_strategy_balance",
    "phase4k_gap_driven_rereading_and_learning_strategy",
    "phase4j_internal_learning_questions_and_gap_detection",
    "phase4i_long_term_memory_and_pattern_stability",
    "phase4h_self_evaluation_and_revision_core",
    "phase4g_neuromodulated_learning_control",
]


def _db_path() -> Path:
    candidates = [Path.cwd() / "ki_memory.sqlite3", Path(__file__).resolve().parents[1] / "ki_memory.sqlite3"]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _connect(mem: Any = None) -> Tuple[sqlite3.Connection, bool]:
    for attr in ("conn", "con", "connection", "db"):
        obj = getattr(mem, attr, None) if mem is not None else None
        if isinstance(obj, sqlite3.Connection):
            return obj, False
    return sqlite3.connect(str(_db_path())), True


def _has_table(cur: sqlite3.Cursor, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur: sqlite3.Cursor, table: str) -> set[str]:
    if not _has_table(cur, table):
        return set()
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_col(cur: sqlite3.Cursor, table: str, col: str, decl: str, changes: list[str]) -> None:
    if _has_table(cur, table) and col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        changes.append(f"add_column:{table}.{col}")


def _unique(cur: sqlite3.Cursor, table: str, col: str, changes: list[str]) -> None:
    if not _has_table(cur, table) or col not in _cols(cur, table):
        return
    try:
        dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
        if dup:
            changes.append(f"skip_unique_duplicates:{table}.{col}")
            return
        idx = f"idx_{table}_{col}_phase5a_unique"
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")
    except Exception as exc:
        changes.append(f"skip_unique_error:{table}.{col}:{exc}")


def _count(cur: sqlite3.Cursor, table: str) -> int:
    if not _has_table(cur, table):
        return 0
    try:
        return int(cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return 0


def _state_get(cur: sqlite3.Cursor, table: str, key: str, default: float = 0.0) -> float:
    if not _has_table(cur, table):
        return default
    try:
        row = cur.execute(f"SELECT value FROM {table} WHERE key=?", (key,)).fetchone()
        return float(row[0]) if row else default
    except Exception:
        return default


def _json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"repr": repr(obj)}, ensure_ascii=False)


def ensure_phase5a_schema(mem: Any = None) -> Dict[str, Any]:
    db, owns = _connect(mem)
    cur = db.cursor()
    changes: list[str] = []

    # Zentrale Release-/Runtime-Tabellen.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5a_integrated_runtime_state (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5a_learning_release_cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase TEXT,
        hypotheses INTEGER DEFAULT 0,
        gaps INTEGER DEFAULT 0,
        internal_questions INTEGER DEFAULT 0,
        reread_actions INTEGER DEFAULT 0,
        active_decisions INTEGER DEFAULT 0,
        progress_evaluations INTEGER DEFAULT 0,
        strategy_feedback_events INTEGER DEFAULT 0,
        gap_resolution_outcomes INTEGER DEFAULT 0,
        long_term_patterns INTEGER DEFAULT 0,
        neuromodulator_states INTEGER DEFAULT 0,
        learning_updates INTEGER DEFAULT 0,
        sleep_decisions INTEGER DEFAULT 0,
        learning_rate REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        exploration_pressure REAL DEFAULT 0,
        inhibition_level REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0,
        integrated_health_score REAL DEFAULT 0,
        safety_ok INTEGER DEFAULT 1,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5a_component_health (
        component_key TEXT PRIMARY KEY,
        component_name TEXT,
        active INTEGER DEFAULT 0,
        table_count INTEGER DEFAULT 0,
        last_status TEXT,
        last_checked_at INTEGER DEFAULT 0,
        details TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5a_schema_audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        target TEXT,
        detail TEXT,
        created_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5a_integrated_learning_summary (
        summary_key TEXT PRIMARY KEY,
        value TEXT,
        numeric_value REAL DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )
    """)

    # Kritische Zukunftsspalten der wichtigsten Phase4-Tabellen: idempotent und bewusst breit.
    for table, defs in {
        "context_hypotheses": [
            ("phase5a_integrated_score", "REAL DEFAULT 0"),
            ("phase5a_last_integrated_at", "INTEGER DEFAULT 0"),
            ("phase5a_integrated_reason", "TEXT"),
        ],
        "internal_learning_gaps": [
            ("phase5a_priority", "REAL DEFAULT 0"),
            ("phase5a_resolution_pressure", "REAL DEFAULT 0"),
            ("phase5a_last_integrated_at", "INTEGER DEFAULT 0"),
            ("phase5a_integrated_reason", "TEXT"),
        ],
        "chunk_attention_scores": [
            ("phase5a_attention_score", "REAL DEFAULT 0"),
            ("phase5a_strategy_reason", "TEXT"),
            ("phase5a_last_integrated_at", "INTEGER DEFAULT 0"),
        ],
        "reading_queue": [
            ("phase5a_priority", "REAL DEFAULT 0"),
            ("phase5a_reason", "TEXT"),
            ("phase5a_updated_at", "INTEGER DEFAULT 0"),
        ],
    }.items():
        for col, decl in defs:
            _add_col(cur, table, col, decl, changes)

    for table, col in [
        ("phase5a_integrated_runtime_state", "key"),
        ("phase5a_component_health", "component_key"),
        ("phase5a_integrated_learning_summary", "summary_key"),
        ("reading_queue", "chunk_id"),
        ("chunk_attention_scores", "chunk_id"),
        ("internal_learning_gaps", "gap_key"),
        ("long_term_pattern_memory", "pattern_key"),
        ("strategy_outcome_memory", "strategy_key"),
        ("strategy_gap_resolution_memory", "strategy_key"),
        ("active_learning_loop_state", "key"),
        ("progress_evaluation_state", "key"),
        ("strategy_effectiveness_feedback_state", "key"),
        ("gap_resolution_state", "key"),
    ]:
        _unique(cur, table, col, changes)

    now = int(time.time())
    for k, v in {
        "phase": PHASE,
        "learning_mode": LEARNING_MODE,
        "no_word_blacklists": "true",
        "fact_promotion": FACT_PROMOTION,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
        "release_goal": "integrated_self_improving_learning_runtime",
    }.items():
        cur.execute("INSERT OR REPLACE INTO phase5a_integrated_runtime_state(key,value,updated_at) VALUES(?,?,?)", (k, v, now))

    for ch in changes:
        cur.execute("INSERT INTO phase5a_schema_audit_events(event_type,target,detail,created_at) VALUES(?,?,?,?)", ("schema_change", PHASE, ch, now))
    db.commit()
    if owns:
        db.close()
    return {"status": "ok", "phase": PHASE, "changes": changes, "no_word_blacklists": True, "fact_promotion": FACT_PROMOTION}


def _component(cur: sqlite3.Cursor, key: str, name: str, tables: list[str], now: int) -> None:
    counts = {t: _count(cur, t) for t in tables}
    active = 1 if any(v > 0 for v in counts.values()) else 0
    cur.execute("""
        INSERT OR REPLACE INTO phase5a_component_health(component_key,component_name,active,table_count,last_status,last_checked_at,details)
        VALUES(?,?,?,?,?,?,?)
    """, (key, name, active, sum(counts.values()), "active" if active else "available_empty", now, _json(counts)))


def integrated_control_step(mem: Any = None) -> Dict[str, Any]:
    ensure_phase5a_schema(mem)
    db, owns = _connect(mem)
    cur = db.cursor()
    now = int(time.time())

    metrics = {
        "hypotheses": _count(cur, "context_hypotheses"),
        "gaps": _count(cur, "internal_learning_gaps"),
        "internal_questions": _count(cur, "internal_learning_questions"),
        "reread_actions": _count(cur, "gap_driven_rereading_actions"),
        "active_decisions": _count(cur, "active_learning_decisions"),
        "progress_evaluations": _count(cur, "learning_progress_evaluations"),
        "strategy_feedback_events": _count(cur, "strategy_feedback_events"),
        "gap_resolution_outcomes": _count(cur, "gap_resolution_outcomes"),
        "long_term_patterns": _count(cur, "long_term_pattern_memory"),
        "neuromodulator_states": _count(cur, "neuromodulator_learning_state"),
        "learning_updates": _count(cur, "hypothesis_learning_updates"),
        "sleep_decisions": _count(cur, "sleep_consolidation_decisions"),
    }
    learning_rate = _state_get(cur, "active_learning_loop_state", "last_learning_rate", 0.234)
    error_weight = _state_get(cur, "active_learning_loop_state", "last_error_weight", 0.407)
    revision_pressure = _state_get(cur, "active_learning_loop_state", "last_revision_pressure", 0.312)
    exploration_pressure = _state_get(cur, "active_learning_loop_state", "last_exploration_pressure", 0.31)
    inhibition_level = _state_get(cur, "active_learning_loop_state", "last_inhibition_level", 0.349)
    consolidation_gain = _state_get(cur, "active_learning_loop_state", "last_consolidation_gain", 0.297)

    facts = _count(cur, "facts")
    relations = _count(cur, "relations")
    questions = _count(cur, "questions")
    safety_ok = 1 if facts == 0 and relations == 0 and questions == 0 else 0

    # Gesundheitswert: Integration vorhanden + Safety + Aktivität, keine Qualitätsbehauptung.
    activity = min(1.0, (metrics["hypotheses"] + metrics["learning_updates"] + metrics["long_term_patterns"]) / 50000.0)
    control_presence = sum(1 for k in ["gaps", "reread_actions", "active_decisions", "progress_evaluations", "strategy_feedback_events", "gap_resolution_outcomes"] if metrics[k] > 0) / 6.0
    health = max(0.0, min(1.0, (0.45 * activity) + (0.45 * control_presence) + (0.10 * safety_ok)))

    cur.execute("""
        INSERT INTO phase5a_learning_release_cycles(
            phase,hypotheses,gaps,internal_questions,reread_actions,active_decisions,progress_evaluations,
            strategy_feedback_events,gap_resolution_outcomes,long_term_patterns,neuromodulator_states,learning_updates,
            sleep_decisions,learning_rate,error_weight,revision_pressure,exploration_pressure,inhibition_level,
            consolidation_gain,integrated_health_score,safety_ok,details,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (PHASE, metrics["hypotheses"], metrics["gaps"], metrics["internal_questions"], metrics["reread_actions"], metrics["active_decisions"], metrics["progress_evaluations"], metrics["strategy_feedback_events"], metrics["gap_resolution_outcomes"], metrics["long_term_patterns"], metrics["neuromodulator_states"], metrics["learning_updates"], metrics["sleep_decisions"], learning_rate, error_weight, revision_pressure, exploration_pressure, inhibition_level, consolidation_gain, health, safety_ok, _json({"metrics": metrics, "project_compass": "no_blacklists_neuromodulated_self_improving_learning"}), now))

    components = [
        ("phase4g", "neuromodulated_learning_control", ["neuromodulator_learning_state", "hypothesis_learning_updates", "sleep_consolidation_decisions"]),
        ("phase4h", "self_evaluation_revision", ["hypothesis_self_evaluations", "hypothesis_role_revisions", "self_evaluation_cycles"]),
        ("phase4i", "long_term_memory", ["long_term_pattern_memory", "pattern_stability_history", "neuromodulator_pattern_profiles"]),
        ("phase4j", "internal_learning_gaps", ["internal_learning_gaps", "internal_learning_questions", "gap_detection_events"]),
        ("phase4k", "gap_driven_rereading", ["gap_driven_rereading_actions", "rereading_candidate_links"]),
        ("phase4l", "gap_cluster_strategy_balance", ["gap_clusters", "reread_cooldowns", "exploration_exploitation_events"]),
        ("phase4m", "active_learning_loop", ["active_learning_decisions", "learning_control_cycles", "neuromodulator_control_history"]),
        ("phase4n", "progress_evaluation", ["learning_progress_evaluations", "adaptive_strategy_adjustments", "strategy_effectiveness_memory"]),
        ("phase4o", "strategy_effectiveness_feedback", ["strategy_feedback_events", "strategy_adjustment_recommendations", "strategy_outcome_memory"]),
        ("phase4p", "gap_resolution_tracking", ["gap_resolution_outcomes", "learning_outcome_tracking_events", "strategy_gap_resolution_memory"]),
    ]
    for key, name, tables in components:
        _component(cur, key, name, tables, now)

    summary = {
        "phase": PHASE,
        "integrated_health_score": round(health, 6),
        "safety_ok": bool(safety_ok),
        "facts": facts,
        "relations": relations,
        "questions": questions,
        "learning_rate": learning_rate,
        "error_weight": error_weight,
        "revision_pressure": revision_pressure,
        "exploration_pressure": exploration_pressure,
        "inhibition_level": inhibition_level,
        "consolidation_gain": consolidation_gain,
        **metrics,
    }
    for k, v in summary.items():
        cur.execute("INSERT OR REPLACE INTO phase5a_integrated_learning_summary(summary_key,value,numeric_value,updated_at) VALUES(?,?,?,?)", (str(k), str(v), float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0, now))
    for k, v in {
        "last_integrated_at": str(now),
        "last_integrated_health_score": str(round(health, 6)),
        "last_safety_ok": str(bool(safety_ok)).lower(),
    }.items():
        cur.execute("INSERT OR REPLACE INTO phase5a_integrated_runtime_state(key,value,updated_at) VALUES(?,?,?)", (k, v, now))

    db.commit()
    if owns:
        db.close()
    return {"status": "phase5a_integrated_control_complete", "phase": PHASE, "summary": summary, "no_word_blacklists": True, "fact_promotion": FACT_PROMOTION}


def managed_cycle(self, progress=None):
    ensure_phase5a_schema(getattr(self, "mem", None))
    result = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else {"status": "phase5a_no_previous_cycle"}
    try:
        from ki_system import v8_modern_gap_candidate_bridge_shadow_release as gap_shadow
        shadow = gap_shadow.observe_shadow(getattr(self, "mem", None))
        gap_phase5f_shadow_observation.observe_shadow(getattr(self, "mem", None), limit=512)
    except Exception as exc:
        shadow = {"status": "modern_gap_candidate_shadow_error", "error": str(exc), "bridge_mode": "shadow"}
    summary = integrated_control_step(getattr(self, "mem", None))
    summary["modern_gap_candidate_shadow"] = shadow
    if isinstance(result, dict):
        result["phase5a_integrated_release"] = summary
        return result
    return {"previous_result": result, "phase5a_integrated_release": summary}


def managed_run(self, cycles=1, progress=None):
    ensure_phase5a_schema(getattr(self, "mem", None))
    result = _PREV_RUN(self, cycles, progress) if _PREV_RUN is not None else [managed_cycle(self, progress) for _ in range(cycles or 1)]
    summary = integrated_control_step(getattr(self, "mem", None))
    if isinstance(result, list):
        result.append({"phase5a_integrated_release": summary})
        return result
    if isinstance(result, dict):
        result["phase5a_integrated_release"] = summary
        return result
    return {"previous_result": result, "phase5a_integrated_release": summary}


def patch_autonomous_loop(AutonomousLoop=None):
    global _PREV_RUN, _PREV_CYCLE
    if AutonomousLoop is None:
        try:
            from ki_system.autonomous import AutonomousLoop as AL
            AutonomousLoop = AL
        except Exception:
            return False
    if getattr(AutonomousLoop, "phase5a_integrated_self_improving_learning_release", False):
        return True
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.phase5a_integrated_self_improving_learning_release = True
    AutonomousLoop._phase5a_integrated_self_improving_learning_release = True
    for marker in CORE_PHASE_MARKERS:
        setattr(AutonomousLoop, marker, True)
        setattr(AutonomousLoop, "_" + marker, True)
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop._learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = FACT_PROMOTION
    AutonomousLoop._fact_promotion = FACT_PROMOTION
    return True
