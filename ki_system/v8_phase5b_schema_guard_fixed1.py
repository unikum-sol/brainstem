# V8-phase5b_schema_guard_fixed1
# Canonical schema guard for Phase5b integrated strategy refinement.
# Project compass: no word blacklists, no facts/relations/questions writes, no fact promotion.
from __future__ import annotations
import sqlite3, time, json
from pathlib import Path

PHASE = "phase5b_schema_guard_fixed1"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"
FACT_PROMOTION = "disabled"
NO_WORD_BLACKLISTS = True


def _connect(obj=None):
    if isinstance(obj, sqlite3.Connection):
        return obj, False
    if obj is not None:
        for a in ("conn", "con", "connection", "db", "sqlite", "sqlite_conn"):
            c = getattr(obj, a, None)
            if isinstance(c, sqlite3.Connection):
                return c, False
        for a in ("db_path", "path", "filename"):
            p = getattr(obj, a, None)
            if p:
                return sqlite3.connect(str(p)), True
    return sqlite3.connect("ki_memory.sqlite3"), True


def _table(cur, t):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None


def _cols(cur, t):
    if not _table(cur, t): return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()}


def _ensure_table(cur, t, ddl, changes):
    existed = _table(cur, t)
    cur.execute(ddl)
    if not existed:
        changes.append(f"create_table:{t}")


def _add(cur, t, c, spec, changes):
    if not _table(cur, t): return
    if c not in _cols(cur, t):
        cur.execute(f"ALTER TABLE {t} ADD COLUMN {c} {spec}")
        changes.append(f"add_column:{t}.{c}")


def _unique(cur, t, c, changes):
    if not _table(cur, t) or c not in _cols(cur, t): return
    try:
        dup = cur.execute(f"SELECT {c}, COUNT(*) FROM {t} WHERE {c} IS NOT NULL GROUP BY {c} HAVING COUNT(*)>1 LIMIT 1").fetchone()
        if dup:
            changes.append(f"skip_unique_duplicates:{t}.{c}")
            return
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_{c}_phase5b_guard_fixed1_unique ON {t}({c})")
        changes.append(f"unique_index:{t}.{c}")
    except Exception as exc:
        changes.append(f"skip_unique_error:{t}.{c}:{type(exc).__name__}")


def _state(cur, table, key, value, now):
    if not _table(cur, table):
        cur.execute(f"CREATE TABLE IF NOT EXISTS {table}(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)")
    cur.execute(f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, str(value), now))


def ensure_phase5b_schema(obj=None):
    con, close = _connect(obj)
    cur = con.cursor()
    changes = []
    now = int(time.time())

    # Canonical Phase5b tables.
    _ensure_table(cur, "phase5b_strategy_refinement_state", "CREATE TABLE IF NOT EXISTS phase5b_strategy_refinement_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)", changes)
    _ensure_table(cur, "phase5b_strategy_refinement_cycles", """
        CREATE TABLE IF NOT EXISTS phase5b_strategy_refinement_cycles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase TEXT, cycle_kind TEXT, persistent_gaps INTEGER DEFAULT 0, clustered_questions INTEGER DEFAULT 0,
            diversity_events INTEGER DEFAULT 0, neuromodulator_adaptations INTEGER DEFAULT 0,
            avg_resolution_score REAL DEFAULT 0, avg_strategy_effectiveness REAL DEFAULT 0,
            exploration_pressure REAL DEFAULT 0, inhibition_level REAL DEFAULT 0,
            recommendation TEXT, details TEXT, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)
    """, changes)
    _ensure_table(cur, "phase5b_persistent_gap_strategy", """
        CREATE TABLE IF NOT EXISTS phase5b_persistent_gap_strategy(
            gap_id INTEGER PRIMARY KEY, gap_key TEXT, gap_type TEXT, role TEXT,
            persistence_score REAL DEFAULT 0, resolution_score REAL DEFAULT 0, strategy_effectiveness_score REAL DEFAULT 0,
            recommended_strategy TEXT, strategy_reason TEXT, priority_before REAL DEFAULT 0, priority_after REAL DEFAULT 0,
            reread_diversity_boost REAL DEFAULT 0, cooldown_suggestion REAL DEFAULT 0,
            status TEXT, evidence_count INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0, details TEXT)
    """, changes)
    _ensure_table(cur, "phase5b_reread_diversity_events", """
        CREATE TABLE IF NOT EXISTS phase5b_reread_diversity_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, gap_id INTEGER, gap_type TEXT, role TEXT,
            old_priority REAL DEFAULT 0, new_priority REAL DEFAULT 0, old_attention REAL DEFAULT 0, new_attention REAL DEFAULT 0,
            diversity_reason TEXT, exploration_pressure REAL DEFAULT 0, inhibition_level REAL DEFAULT 0,
            details TEXT, created_at INTEGER DEFAULT 0)
    """, changes)
    _ensure_table(cur, "phase5b_neuromodulator_adaptation_events", """
        CREATE TABLE IF NOT EXISTS phase5b_neuromodulator_adaptation_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, adaptation_key TEXT, target TEXT,
            old_value REAL DEFAULT 0, new_value REAL DEFAULT 0, reason TEXT,
            dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0,
            noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0)
    """, changes)
    _ensure_table(cur, "phase5b_internal_question_clusters", """
        CREATE TABLE IF NOT EXISTS phase5b_internal_question_clusters(
            cluster_key TEXT PRIMARY KEY, question_type TEXT, role TEXT, size INTEGER DEFAULT 0,
            avg_priority REAL DEFAULT 0, avg_resolution_score REAL DEFAULT 0, representative_question TEXT,
            recommended_action TEXT, status TEXT, updated_at INTEGER DEFAULT 0, details TEXT)
    """, changes)

    # Broad future-safe schemas for existing tables. This fixes the current missing resolution_score on internal_learning_questions,
    # and also adds all likely future columns that Phase5b/5c strategy logic may reference.
    specs = {
        "internal_learning_questions": {
            "question_key":"TEXT", "gap_key":"TEXT", "question_type":"TEXT", "role":"TEXT", "question_text":"TEXT",
            "priority":"REAL DEFAULT 0", "phase5b_priority":"REAL DEFAULT 0", "cluster_key":"TEXT", "phase5b_clustered_at":"INTEGER DEFAULT 0",
            "phase5b_recommended_action":"TEXT", "resolution_score":"REAL DEFAULT 0", "strategy_effectiveness_score":"REAL DEFAULT 0",
            "learning_outcome_score":"REAL DEFAULT 0", "progress_priority":"REAL DEFAULT 0", "status":"TEXT DEFAULT 'internal_open'",
            "evidence_count":"INTEGER DEFAULT 1", "last_strategy_feedback_at":"INTEGER DEFAULT 0", "strategy_feedback_reason":"TEXT",
            "last_resolution_evaluated_at":"INTEGER DEFAULT 0", "resolution_reason":"TEXT", "updated_at":"INTEGER DEFAULT 0"
        },
        "internal_learning_gaps": {
            "priority":"REAL DEFAULT 0", "phase5b_strategy":"TEXT", "phase5b_strategy_reason":"TEXT", "phase5b_last_refined_at":"INTEGER DEFAULT 0",
            "persistence_score":"REAL DEFAULT 0", "diversity_need":"REAL DEFAULT 0", "strategy_refinement_count":"INTEGER DEFAULT 0",
            "resolution_score":"REAL DEFAULT 0", "resolution_status":"TEXT DEFAULT 'open'", "strategy_effectiveness_score":"REAL DEFAULT 0",
            "learning_outcome_score":"REAL DEFAULT 0", "progress_priority":"REAL DEFAULT 0", "reread_priority":"REAL DEFAULT 0",
            "active_learning_priority":"REAL DEFAULT 0", "selection_count":"INTEGER DEFAULT 0", "last_selected_at":"INTEGER DEFAULT 0",
            "last_strategy_feedback_at":"INTEGER DEFAULT 0", "strategy_feedback_reason":"TEXT", "last_resolution_evaluated_at":"INTEGER DEFAULT 0",
            "resolution_reason":"TEXT", "priority_decay":"REAL DEFAULT 0", "effectiveness_evidence_count":"INTEGER DEFAULT 0",
            "resolution_attempts":"INTEGER DEFAULT 0", "last_resolution_outcome":"TEXT", "resolved_at":"INTEGER DEFAULT 0"
        },
        "reading_queue": {
            "priority":"REAL DEFAULT 0", "attention_score":"REAL DEFAULT 0", "phase5b_priority":"REAL DEFAULT 0", "phase5b_reason":"TEXT",
            "phase5b_last_adjusted_at":"INTEGER DEFAULT 0", "cooldown_until":"INTEGER DEFAULT 0", "status":"TEXT DEFAULT 'pending'", "updated_at":"INTEGER DEFAULT 0"
        },
        "chunk_attention_scores": {
            "attention_score":"REAL DEFAULT 0", "phase5b_score":"REAL DEFAULT 0", "phase5b_reason":"TEXT", "phase5b_last_adjusted_at":"INTEGER DEFAULT 0",
            "diversity_score":"REAL DEFAULT 0", "resolution_support_score":"REAL DEFAULT 0", "strategy_effectiveness_score":"REAL DEFAULT 0",
            "learning_outcome_score":"REAL DEFAULT 0", "active_learning_score":"REAL DEFAULT 0", "progress_adjusted_score":"REAL DEFAULT 0",
            "strategy_reason":"TEXT", "updated_at":"INTEGER DEFAULT 0"
        },
        "strategy_outcome_memory": {
            "phase5b_effectiveness_score":"REAL DEFAULT 0", "phase5b_last_refined_at":"INTEGER DEFAULT 0", "phase5b_recommendation":"TEXT",
            "avg_resolution_score":"REAL DEFAULT 0", "avg_outcome_score":"REAL DEFAULT 0", "updated_at":"INTEGER DEFAULT 0"
        },
        "phase5b_strategy_refinement_cycles": {"updated_at":"INTEGER DEFAULT 0"},
        "phase5b_persistent_gap_strategy": {"details":"TEXT"},
        "phase5b_internal_question_clusters": {"details":"TEXT"},
    }
    for t, cols in specs.items():
        for c, spec in cols.items():
            _add(cur, t, c, spec, changes)

    # Backfills to avoid zero/NULL priority/resolution that breaks strategy refinement.
    if _table(cur, "internal_learning_questions"):
        qcols = _cols(cur, "internal_learning_questions")
        parts = []
        for c in ("priority", "phase5b_priority", "progress_priority", "strategy_effectiveness_score", "learning_outcome_score", "resolution_score"):
            if c in qcols:
                parts.append(f"COALESCE({c},0)")
        if "priority" in qcols and parts:
            cur.execute(f"UPDATE internal_learning_questions SET priority=MAX(COALESCE(priority,0), MIN(1.0, ({' + '.join(parts)})/{len(parts)})) WHERE COALESCE(priority,0)=0")
            changes.append("backfill:internal_learning_questions.priority")
        if "phase5b_priority" in qcols and "priority" in qcols:
            cur.execute("UPDATE internal_learning_questions SET phase5b_priority=MAX(COALESCE(phase5b_priority,0),COALESCE(priority,0))")
            changes.append("backfill:internal_learning_questions.phase5b_priority")

    if _table(cur, "internal_learning_gaps"):
        gcols = _cols(cur, "internal_learning_gaps")
        parts = []
        for c in ("priority", "progress_priority", "active_learning_priority", "reread_priority", "severity", "uncertainty", "strategy_effectiveness_score", "resolution_score"):
            if c in gcols:
                parts.append(f"COALESCE({c},0)")
        if "priority" in gcols and parts:
            cur.execute(f"UPDATE internal_learning_gaps SET priority=MAX(COALESCE(priority,0), MIN(1.0, ({' + '.join(parts)})/{len(parts)}))")
            changes.append("backfill:internal_learning_gaps.priority")
        if "persistence_score" in gcols and "resolution_score" in gcols and "priority" in gcols:
            cur.execute("UPDATE internal_learning_gaps SET persistence_score=MAX(COALESCE(persistence_score,0), MIN(1.0, (1.0-COALESCE(resolution_score,0))*0.65 + COALESCE(priority,0)*0.35))")
            changes.append("backfill:internal_learning_gaps.persistence_score")

    for t, c in [
        ("phase5b_strategy_refinement_state", "key"), ("phase5b_persistent_gap_strategy", "gap_id"),
        ("phase5b_internal_question_clusters", "cluster_key"), ("internal_learning_gaps", "gap_key"),
        ("internal_learning_questions", "question_key"), ("reading_queue", "chunk_id"), ("chunk_attention_scores", "chunk_id")
    ]:
        _unique(cur, t, c, changes)

    for k, v in {
        "phase": PHASE, "schema_guard": "fixed1", "no_word_blacklists": "true", "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled", "direct_fact_writes": "disabled", "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only"
    }.items():
        _state(cur, "phase5b_strategy_refinement_state", k, v, now)

    con.commit()
    if close:
        con.close()
    return {"status":"ok", "phase":PHASE, "changes":changes, "no_word_blacklists":True, "fact_promotion":"disabled"}


def apply_strategy_refinement_safe(memory=None):
    ensure_phase5b_schema(memory)
    try:
        from ki_system import v8_phase5b_integrated_strategy_refinement_release as p5b
        return p5b.apply_strategy_refinement(memory)
    except Exception as exc:
        return {"status":"phase5b_strategy_refinement_error", "phase":PHASE, "error":repr(exc), "no_word_blacklists":True, "fact_promotion":"disabled"}


def _mem(loop):
    for a in ("mem", "memory", "m", "store", "memory_store"):
        v = getattr(loop, a, None)
        if v is not None:
            return v
    return None


def patch_autonomous_loop(*args, **kwargs):
    try:
        from ki_system.autonomous import AutonomousLoop
    except Exception:
        return False
    try:
        from ki_system import v8_phase5b_integrated_strategy_refinement_release as base
    except Exception:
        base = None
    old_run = getattr(base, "managed_run", None) if base else getattr(AutonomousLoop, "run", None)
    old_cycle = getattr(base, "managed_cycle", None) if base else getattr(AutonomousLoop, "cycle", None)
    def managed_cycle(self, progress=None):
        ensure_phase5b_schema(_mem(self))
        if callable(old_cycle):
            return old_cycle(self, progress)
        return apply_strategy_refinement_safe(_mem(self))
    def managed_run(self, cycles=1, progress=None):
        ensure_phase5b_schema(_mem(self))
        if callable(old_run):
            return old_run(self, cycles, progress)
        return apply_strategy_refinement_safe(_mem(self))
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    for name in ["phase5b_schema_guard_fixed1", "_phase5b_schema_guard_fixed1", "phase5b_integrated_strategy_refinement_release", "_phase5b_integrated_strategy_refinement_release", "phase5a_integrated_self_improving_learning_release", "_phase5a_integrated_self_improving_learning_release", "no_word_blacklists", "_no_word_blacklists"]:
        setattr(AutonomousLoop, name, True)
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop._learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop._fact_promotion = "disabled"
    return True

try:
    patch_autonomous_loop()
except Exception as exc:
    print("[PHASE5B_SCHEMA_GUARD_FIXED1_AUTOLOAD_ERROR]", exc)
