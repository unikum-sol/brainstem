# V8-phase5d_integrated_observation_and_strategy_memory_release
# Integrated observation + strategy memory release.
# Project compass: no word blacklists, no direct facts/relations/questions, no fact promotion.

from __future__ import annotations
import os, time, json, sqlite3, traceback
from pathlib import Path

PHASE = "phase5d_integrated_observation_and_strategy_memory_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"
NO_WORD_BLACKLISTS = True
FACT_PROMOTION = "disabled"

_PREV_RUN = None
_PREV_CYCLE = None


def _now() -> int:
    return int(time.time())


def _json(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"repr": repr(obj)}, ensure_ascii=False)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _open_default_db():
    return sqlite3.connect(str(_project_root() / "ki_memory.sqlite3"))


def _resolve_conn(source=None):
    """Return (conn, should_close). Be tolerant of Memory wrappers and old runtimes."""
    if isinstance(source, sqlite3.Connection):
        return source, False
    candidates = []
    if source is not None:
        candidates.append(source)
        for attr in ("mem", "memory", "m", "store", "memory_store", "db", "database"):
            if hasattr(source, attr):
                try: candidates.append(getattr(source, attr))
                except Exception: pass
    for obj in candidates:
        if isinstance(obj, sqlite3.Connection):
            return obj, False
        for attr in ("conn", "con", "connection", "db", "sqlite", "sqlite_conn"):
            if hasattr(obj, attr):
                try:
                    val = getattr(obj, attr)
                    if isinstance(val, sqlite3.Connection):
                        return val, False
                except Exception:
                    pass
        for attr in ("db_path", "path", "filename"):
            if hasattr(obj, attr):
                try:
                    p = getattr(obj, attr)
                    if p and Path(str(p)).exists():
                        return sqlite3.connect(str(p)), True
                except Exception:
                    pass
        if hasattr(obj, "execute") and hasattr(obj, "cursor"):
            return obj, False
    return _open_default_db(), True


def _table_exists(cur, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur, table: str):
    if not _table_exists(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_col(cur, table: str, col: str, decl: str, changes: list):
    if not _table_exists(cur, table):
        return
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        changes.append(f"add_column:{table}.{col}")


def _unique(cur, table: str, col: str, changes: list):
    if not _table_exists(cur, table) or col not in _cols(cur, table):
        return
    idx = f"idx_{table}_{col}_phase5d_unique"
    try:
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")
    except sqlite3.IntegrityError:
        # Existing duplicates: do not destructively cleanup here. Keep learning safe.
        changes.append(f"skip_unique_duplicates:{table}.{col}")


def ensure_phase5d_schema(db_or_mem=None):
    db, close = _resolve_conn(db_or_mem)
    cur = db.cursor()
    changes = []
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5d_observation_memory(
        memory_key TEXT PRIMARY KEY,
        observation_type TEXT,
        scope TEXT,
        observations INTEGER DEFAULT 0,
        avg_outcome_score REAL DEFAULT 0,
        avg_resolution_score REAL DEFAULT 0,
        avg_error_pressure REAL DEFAULT 0,
        avg_uncertainty_pressure REAL DEFAULT 0,
        avg_stability_gain REAL DEFAULT 0,
        avg_strategy_effectiveness REAL DEFAULT 0,
        persistent_gap_pressure REAL DEFAULT 0,
        read_no_candidate_pressure REAL DEFAULT 0,
        trend TEXT,
        recommendation TEXT,
        details TEXT,
        first_seen INTEGER DEFAULT 0,
        last_seen INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5d_strategy_memory_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        memory_key TEXT,
        metric_name TEXT,
        old_value REAL DEFAULT 0,
        new_value REAL DEFAULT 0,
        delta REAL DEFAULT 0,
        recommendation TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5d_observation_cycles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase TEXT,
        hypotheses INTEGER DEFAULT 0,
        gaps INTEGER DEFAULT 0,
        internal_questions INTEGER DEFAULT 0,
        feedback_events INTEGER DEFAULT 0,
        resolution_events INTEGER DEFAULT 0,
        progress_evaluations INTEGER DEFAULT 0,
        strategy_feedback_events INTEGER DEFAULT 0,
        long_term_patterns INTEGER DEFAULT 0,
        outcome_score REAL DEFAULT 0,
        avg_resolution_score REAL DEFAULT 0,
        avg_error_pressure REAL DEFAULT 0,
        avg_uncertainty_pressure REAL DEFAULT 0,
        avg_stability_gain REAL DEFAULT 0,
        persistent_gap_count INTEGER DEFAULT 0,
        read_no_candidate_penalties INTEGER DEFAULT 0,
        integrated_health_score REAL DEFAULT 0,
        safety_ok INTEGER DEFAULT 0,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5d_strategy_recommendations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_key TEXT,
        recommendation_type TEXT,
        target TEXT,
        strength REAL DEFAULT 0,
        reason TEXT,
        neuromodulator_adjustment TEXT,
        status TEXT DEFAULT 'open',
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5d_runtime_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    # Future-tolerant columns in existing tables.
    for table in ("internal_learning_gaps", "internal_learning_questions", "context_hypotheses", "chunk_attention_scores", "reading_queue", "strategy_outcome_memory", "strategy_gap_resolution_memory"):
        if _table_exists(cur, table):
            for col, decl in [
                ("phase5d_observation_score", "REAL DEFAULT 0"),
                ("phase5d_strategy_memory_score", "REAL DEFAULT 0"),
                ("phase5d_trend", "TEXT"),
                ("phase5d_recommendation", "TEXT"),
                ("phase5d_last_observed_at", "INTEGER DEFAULT 0"),
                ("phase5d_reason", "TEXT"),
                ("phase5d_outcome_score", "REAL DEFAULT 0"),
                ("phase5d_resolution_score", "REAL DEFAULT 0"),
                ("phase5d_persistent_pressure", "REAL DEFAULT 0"),
            ]:
                _add_col(cur, table, col, decl, changes)
    for table, col in [
        ("phase5d_observation_memory", "memory_key"),
        ("phase5d_runtime_state", "key"),
        ("internal_learning_gaps", "gap_key"),
        ("internal_learning_questions", "question_key"),
        ("reading_queue", "chunk_id"),
        ("chunk_attention_scores", "chunk_id"),
        ("phase5a_integrated_runtime_state", "key"),
        ("phase5b_strategy_refinement_state", "key"),
        ("phase5c_runtime_state", "key"),
    ]:
        _unique(cur, table, col, changes)
    now = _now()
    for k, v in {
        "phase": PHASE,
        "learning_mode": LEARNING_MODE,
        "no_word_blacklists": "true",
        "fact_promotion": FACT_PROMOTION,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "internal_learning_questions_only",
    }.items():
        cur.execute("INSERT INTO phase5d_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, str(v), now))
    db.commit()
    if close: db.close()
    return {"status": "ok", "phase": PHASE, "changes": changes, "no_word_blacklists": True, "fact_promotion": FACT_PROMOTION}


def _count(cur, table):
    if not _table_exists(cur, table): return 0
    try: return int(cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] or 0)
    except Exception: return 0


def _avg(cur, table, col, where="1=1"):
    if not _table_exists(cur, table) or col not in _cols(cur, table): return 0.0
    try:
        v = cur.execute(f"SELECT AVG(COALESCE({col},0)) FROM {table} WHERE {where}").fetchone()[0]
        return float(v or 0.0)
    except Exception:
        return 0.0


def _latest_state_float(cur, table, key, default=0.0):
    if not _table_exists(cur, table): return default
    cols = _cols(cur, table)
    if not {"key", "value"}.issubset(cols): return default
    row = cur.execute(f"SELECT value FROM {table} WHERE key=?", (key,)).fetchone()
    if not row: return default
    try: return float(str(row[0]).strip("'\""))
    except Exception: return default


def _upsert_memory(cur, key, observation_type, scope, values, recommendation, details, now):
    old = cur.execute("SELECT avg_outcome_score, avg_resolution_score, avg_error_pressure, avg_uncertainty_pressure, avg_stability_gain, observations FROM phase5d_observation_memory WHERE memory_key=?", (key,)).fetchone()
    observations = int((old[5] if old else 0) or 0) + 1
    def evolve(old_val, new_val):
        if old is None: return new_val
        return round((float(old_val or 0) * 0.75) + (float(new_val or 0) * 0.25), 6)
    avg_outcome = evolve(old[0] if old else 0, values.get("outcome_score", 0))
    avg_resolution = evolve(old[1] if old else 0, values.get("resolution_score", 0))
    avg_error = evolve(old[2] if old else 0, values.get("error_pressure", 0))
    avg_unc = evolve(old[3] if old else 0, values.get("uncertainty_pressure", 0))
    avg_stab = evolve(old[4] if old else 0, values.get("stability_gain", 0))
    trend = "improving" if values.get("resolution_score", 0) > avg_resolution else "observe"
    cur.execute("""INSERT INTO phase5d_observation_memory(
        memory_key,observation_type,scope,observations,avg_outcome_score,avg_resolution_score,avg_error_pressure,
        avg_uncertainty_pressure,avg_stability_gain,avg_strategy_effectiveness,persistent_gap_pressure,
        read_no_candidate_pressure,trend,recommendation,details,first_seen,last_seen,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(memory_key) DO UPDATE SET observations=excluded.observations, avg_outcome_score=excluded.avg_outcome_score,
        avg_resolution_score=excluded.avg_resolution_score, avg_error_pressure=excluded.avg_error_pressure,
        avg_uncertainty_pressure=excluded.avg_uncertainty_pressure, avg_stability_gain=excluded.avg_stability_gain,
        avg_strategy_effectiveness=excluded.avg_strategy_effectiveness, persistent_gap_pressure=excluded.persistent_gap_pressure,
        read_no_candidate_pressure=excluded.read_no_candidate_pressure, trend=excluded.trend, recommendation=excluded.recommendation,
        details=excluded.details, last_seen=excluded.last_seen, updated_at=excluded.updated_at""",
        (key, observation_type, scope, observations, avg_outcome, avg_resolution, avg_error, avg_unc, avg_stab,
         values.get("strategy_effectiveness", 0), values.get("persistent_gap_pressure", 0), values.get("read_no_candidate_pressure", 0),
         trend, recommendation, _json(details), now, now, now))
    cur.execute("INSERT INTO phase5d_strategy_memory_events(event_type,memory_key,metric_name,old_value,new_value,delta,recommendation,details,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("strategy_memory_update", key, "resolution_score", float(old[1] if old else 0), values.get("resolution_score", 0), values.get("resolution_score", 0)-float(old[1] if old else 0), recommendation, _json(details), now))


def apply_integrated_observation_and_strategy_memory(db_or_mem=None):
    db, close = _resolve_conn(db_or_mem)
    ensure_phase5d_schema(db)
    cur = db.cursor(); now = _now()
    facts, relations, questions = _count(cur,"facts"), _count(cur,"relations"), _count(cur,"questions")
    safety_ok = int(facts == 0 and relations == 0 and questions == 0)
    metrics = {
        "hypotheses": _count(cur, "context_hypotheses"),
        "gaps": _count(cur, "internal_learning_gaps"),
        "internal_questions": _count(cur, "internal_learning_questions"),
        "feedback_events": _count(cur, "strategy_feedback_events"),
        "resolution_events": _count(cur, "gap_resolution_outcomes"),
        "progress_evaluations": _count(cur, "learning_progress_evaluations"),
        "strategy_feedback_events": _count(cur, "strategy_feedback_events"),
        "long_term_patterns": _count(cur, "long_term_pattern_memory"),
    }
    outcome = _avg(cur, "strategy_feedback_events", "outcome_score") or _avg(cur, "strategy_outcome_memory", "avg_outcome_score")
    resolution = _avg(cur, "gap_resolution_outcomes", "resolution_score") or _avg(cur, "internal_learning_gaps", "resolution_score")
    error_pressure = _latest_state_float(cur, "progress_evaluation_state", "last_error_pressure", _avg(cur,"internal_learning_gaps","error_weight"))
    unc_pressure = _latest_state_float(cur, "progress_evaluation_state", "last_uncertainty_pressure", _avg(cur,"internal_learning_gaps","uncertainty"))
    stability_gain = _latest_state_float(cur, "progress_evaluation_state", "last_stability_gain", _avg(cur,"long_term_pattern_memory","stability"))
    persistent = 0
    if _table_exists(cur, "internal_learning_gaps") and "resolution_status" in _cols(cur, "internal_learning_gaps"):
        persistent = int(cur.execute("SELECT COUNT(*) FROM internal_learning_gaps WHERE COALESCE(resolution_status,'open') IN ('persistent_gap','open','persistent')").fetchone()[0] or 0)
    read_no_candidate = 0
    if _table_exists(cur, "reading_queue"):
        read_no_candidate = int(cur.execute("SELECT COUNT(*) FROM reading_queue WHERE status='read_no_candidate' AND COALESCE(priority,0) >= 0.6").fetchone()[0] or 0)
    persistent_pressure = min(1.0, persistent / max(1, metrics["gaps"]))
    read_no_candidate_pressure = min(1.0, read_no_candidate / max(1, _count(cur,"reading_queue")))
    recommendation = "observe_and_keep_strategy"
    if persistent_pressure > 0.4 and resolution < 0.25:
        recommendation = "increase_diverse_context_and_strengthen_gap_closure"
    elif outcome > 0.65 and stability_gain > 0.05:
        recommendation = "reinforce_current_strategy_memory"
    elif read_no_candidate_pressure > 0.05:
        recommendation = "reduce_unproductive_read_no_candidate_paths"
    values = {
        "outcome_score": round(outcome,6), "resolution_score": round(resolution,6), "error_pressure": round(error_pressure,6),
        "uncertainty_pressure": round(unc_pressure,6), "stability_gain": round(stability_gain,6),
        "strategy_effectiveness": round((outcome + resolution + stability_gain) / 3.0, 6),
        "persistent_gap_pressure": round(persistent_pressure,6), "read_no_candidate_pressure": round(read_no_candidate_pressure,6)
    }
    _upsert_memory(cur, "global_integrated_strategy_memory", "global_strategy", "global", values, recommendation, metrics, now)
    _upsert_memory(cur, "persistent_gap_strategy_memory", "gap_resolution", "internal_learning_gaps", values, recommendation, {"persistent": persistent}, now)
    _upsert_memory(cur, "read_outcome_strategy_memory", "read_outcome", "reading_queue", values, recommendation, {"read_no_candidate_high_priority": read_no_candidate}, now)
    # Backpropagate scores to existing tables, tolerant and bounded.
    for table, order_col in [("internal_learning_gaps", "priority"), ("internal_learning_questions", "priority"), ("chunk_attention_scores", "attention_score")]:
        if _table_exists(cur, table):
            cols = _cols(cur, table)
            sets=[]; params=[]
            if "phase5d_observation_score" in cols: sets.append("phase5d_observation_score=?"); params.append(round((outcome+resolution)/2, 6))
            if "phase5d_strategy_memory_score" in cols: sets.append("phase5d_strategy_memory_score=?"); params.append(values["strategy_effectiveness"])
            if "phase5d_trend" in cols: sets.append("phase5d_trend=?"); params.append("persistent" if persistent_pressure>0.4 else "observe")
            if "phase5d_recommendation" in cols: sets.append("phase5d_recommendation=?"); params.append(recommendation)
            if "phase5d_last_observed_at" in cols: sets.append("phase5d_last_observed_at=?"); params.append(now)
            if "phase5d_reason" in cols: sets.append("phase5d_reason=?"); params.append(PHASE)
            if sets:
                sql = f"UPDATE {table} SET "+", ".join(sets)+f" WHERE rowid IN (SELECT rowid FROM {table} ORDER BY COALESCE({order_col},0) DESC, rowid DESC LIMIT 250)"
                try: cur.execute(sql, tuple(params))
                except Exception: pass
    cur.execute("INSERT INTO phase5d_observation_cycles(phase,hypotheses,gaps,internal_questions,feedback_events,resolution_events,progress_evaluations,strategy_feedback_events,long_term_patterns,outcome_score,avg_resolution_score,avg_error_pressure,avg_uncertainty_pressure,avg_stability_gain,persistent_gap_count,read_no_candidate_penalties,integrated_health_score,safety_ok,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (PHASE, metrics["hypotheses"], metrics["gaps"], metrics["internal_questions"], metrics["feedback_events"], metrics["resolution_events"], metrics["progress_evaluations"], metrics["strategy_feedback_events"], metrics["long_term_patterns"], values["outcome_score"], values["resolution_score"], values["error_pressure"], values["uncertainty_pressure"], values["stability_gain"], persistent, read_no_candidate, 1.0 if safety_ok else 0.0, safety_ok, _json({"recommendation": recommendation}), now))
    cur.execute("INSERT INTO phase5d_strategy_recommendations(strategy_key,recommendation_type,target,strength,reason,neuromodulator_adjustment,status,details,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                ("integrated_strategy_memory", recommendation, "global", values["strategy_effectiveness"], PHASE, _json({"error_weight":"adaptive", "exploration":"adaptive", "inhibition":"adaptive"}), "open", _json(values), now))
    for k, v in {
        "phase": PHASE, "learning_mode": LEARNING_MODE, "no_word_blacklists": "true", "fact_promotion": FACT_PROMOTION,
        "direct_fact_writes": "disabled", "direct_relation_writes": "disabled", "question_generation": "internal_learning_questions_only",
        "last_outcome_score": values["outcome_score"], "last_resolution_score": values["resolution_score"],
        "last_strategy_effectiveness": values["strategy_effectiveness"], "last_persistent_gap_pressure": values["persistent_gap_pressure"],
        "last_read_no_candidate_pressure": values["read_no_candidate_pressure"], "last_recommendation": recommendation,
        "last_safety_ok": str(bool(safety_ok)).lower()
    }.items():
        cur.execute("INSERT INTO phase5d_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, str(v), now))
    db.commit()
    result = {"status": "phase5d_observation_strategy_memory_complete", "phase": PHASE, "metrics": metrics, "values": values, "recommendation": recommendation, "safety_ok": bool(safety_ok), "no_word_blacklists": True, "fact_promotion": FACT_PROMOTION}
    if close: db.close()
    return result


def managed_cycle(self, progress=None):
    result = None
    if _PREV_CYCLE is not None:
        result = _PREV_CYCLE(self, progress)
    summary = apply_integrated_observation_and_strategy_memory(self)
    if isinstance(result, dict):
        result["phase5d_integrated_observation_and_strategy_memory"] = summary
        return result
    return {"cycle_result": result, "phase5d_integrated_observation_and_strategy_memory": summary}


def managed_run(self, cycles=1, progress=None):
    result = None
    if _PREV_RUN is not None:
        result = _PREV_RUN(self, cycles, progress)
    summary = apply_integrated_observation_and_strategy_memory(self)
    if isinstance(result, list):
        result.append({"phase5d_integrated_observation_and_strategy_memory": summary})
        return result
    if isinstance(result, dict):
        result["phase5d_integrated_observation_and_strategy_memory"] = summary
        return result
    return [{"run_result": result, "phase5d_integrated_observation_and_strategy_memory": summary}]


def patch_autonomous_loop(cls=None):
    global _PREV_RUN, _PREV_CYCLE
    if cls is None:
        from ki_system.autonomous import AutonomousLoop as cls
    if getattr(cls, "phase5d_integrated_observation_and_strategy_memory_release", False):
        return cls
    current_run = getattr(cls, "run", None)
    current_cycle = getattr(cls, "cycle", None)
    if getattr(current_run, "__module__", "") != __name__:
        _PREV_RUN = current_run
    if getattr(current_cycle, "__module__", "") != __name__:
        _PREV_CYCLE = current_cycle
    cls.run = managed_run
    cls.cycle = managed_cycle
    cls.phase5d_integrated_observation_and_strategy_memory_release = True
    cls._phase5d_integrated_observation_and_strategy_memory_release = True
    cls.no_word_blacklists = True
    cls._no_word_blacklists = True
    cls.learning_mode = LEARNING_MODE
    cls._learning_mode = LEARNING_MODE
    cls.fact_promotion = FACT_PROMOTION
    cls._fact_promotion = FACT_PROMOTION
    return cls

try:
    patch_autonomous_loop()
except Exception:
    # Import-time patch can fail during isolated compilation; installer autoload retries in project runtime.
    pass
