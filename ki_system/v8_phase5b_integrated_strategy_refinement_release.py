
# V8-phase5b_integrated_strategy_refinement_release
# Integrated strategy refinement for context-hypothesis learning.
# No word blacklists. No facts/relations/questions writes.
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PHASE = "phase5b_integrated_strategy_refinement_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

_ORIGINAL_RUN = None
_ORIGINAL_CYCLE = None

def _now() -> int:
    return int(time.time())

def _json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"repr": repr(obj)}, ensure_ascii=False)

def _connect_from_memory(memory: Any = None) -> Tuple[sqlite3.Connection, bool]:
    """Return (connection, should_close). Accepts project Memory or falls back to ki_memory.sqlite3."""
    if memory is not None:
        for name in ("conn", "con", "db", "connection", "sqlite", "sqlite_conn"):
            con = getattr(memory, name, None)
            if isinstance(con, sqlite3.Connection):
                return con, False
        # Some memory classes expose a method.
        for name in ("get_connection", "connect", "connection"):
            method = getattr(memory, name, None)
            if callable(method):
                try:
                    con = method()
                    if isinstance(con, sqlite3.Connection):
                        return con, False
                except TypeError:
                    pass
                except Exception:
                    pass
    return sqlite3.connect("ki_memory.sqlite3"), True

def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _columns(cur: sqlite3.Cursor, table: str) -> List[str]:
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]

def _ensure_table(cur: sqlite3.Cursor, table: str, create_sql: str, cols: Dict[str, str], changes: List[str]) -> None:
    cur.execute(create_sql)
    existing = set(_columns(cur, table))
    for col, typ in cols.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            changes.append(f"add_column:{table}.{col}")

def _ensure_unique(cur: sqlite3.Cursor, table: str, col: str, changes: List[str]) -> None:
    if col not in _columns(cur, table):
        return
    # Avoid creating impossible unique index when duplicates exist.
    try:
        dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
        if dup:
            changes.append(f"skip_unique_duplicates:{table}.{col}")
            return
        idx = f"idx_{table}_{col}_uniq"
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")
    except Exception as exc:
        changes.append(f"skip_unique_error:{table}.{col}:{type(exc).__name__}")

def _set_state(cur: sqlite3.Cursor, table: str, key: str, value: Any) -> None:
    now = _now()
    cur.execute(f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, str(value), now))

def _state_float(cur: sqlite3.Cursor, table: str, key: str, default: float) -> float:
    try:
        row = cur.execute(f"SELECT value FROM {table} WHERE key=?", (key,)).fetchone()
        return float(str(row[0]).strip("'\"")) if row and row[0] is not None else default
    except Exception:
        return default

def ensure_phase5b_schema(memory: Any = None) -> Dict[str, Any]:
    con, close = _connect_from_memory(memory)
    cur = con.cursor()
    changes: List[str] = []

    # Phase5b canonical tables.
    _ensure_table(cur, "phase5b_strategy_refinement_state",
        "CREATE TABLE IF NOT EXISTS phase5b_strategy_refinement_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)",
        {"key":"TEXT", "value":"TEXT", "updated_at":"INTEGER"}, changes)

    _ensure_table(cur, "phase5b_strategy_refinement_cycles",
        """CREATE TABLE IF NOT EXISTS phase5b_strategy_refinement_cycles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase TEXT, cycle_kind TEXT, persistent_gaps INTEGER, clustered_questions INTEGER,
            diversity_events INTEGER, neuromodulator_adaptations INTEGER,
            avg_resolution_score REAL, avg_strategy_effectiveness REAL,
            exploration_pressure REAL, inhibition_level REAL, recommendation TEXT,
            details TEXT, created_at INTEGER
        )""",
        {
            "phase":"TEXT", "cycle_kind":"TEXT", "persistent_gaps":"INTEGER", "clustered_questions":"INTEGER",
            "diversity_events":"INTEGER", "neuromodulator_adaptations":"INTEGER",
            "avg_resolution_score":"REAL", "avg_strategy_effectiveness":"REAL",
            "exploration_pressure":"REAL", "inhibition_level":"REAL", "recommendation":"TEXT",
            "details":"TEXT", "created_at":"INTEGER"
        }, changes)

    _ensure_table(cur, "phase5b_persistent_gap_strategy",
        """CREATE TABLE IF NOT EXISTS phase5b_persistent_gap_strategy(
            gap_id INTEGER PRIMARY KEY, gap_key TEXT, gap_type TEXT, role TEXT,
            persistence_score REAL, resolution_score REAL, strategy_effectiveness_score REAL,
            recommended_strategy TEXT, strategy_reason TEXT, priority_before REAL, priority_after REAL,
            reread_diversity_boost REAL, cooldown_suggestion REAL,
            status TEXT, evidence_count INTEGER, updated_at INTEGER
        )""",
        {
            "gap_id":"INTEGER", "gap_key":"TEXT", "gap_type":"TEXT", "role":"TEXT",
            "persistence_score":"REAL", "resolution_score":"REAL", "strategy_effectiveness_score":"REAL",
            "recommended_strategy":"TEXT", "strategy_reason":"TEXT", "priority_before":"REAL", "priority_after":"REAL",
            "reread_diversity_boost":"REAL", "cooldown_suggestion":"REAL",
            "status":"TEXT", "evidence_count":"INTEGER", "updated_at":"INTEGER"
        }, changes)

    _ensure_table(cur, "phase5b_reread_diversity_events",
        """CREATE TABLE IF NOT EXISTS phase5b_reread_diversity_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, gap_id INTEGER, gap_type TEXT, role TEXT,
            old_priority REAL, new_priority REAL, old_attention REAL, new_attention REAL,
            diversity_reason TEXT, exploration_pressure REAL, inhibition_level REAL,
            details TEXT, created_at INTEGER
        )""",
        {
            "chunk_id":"INTEGER", "gap_id":"INTEGER", "gap_type":"TEXT", "role":"TEXT",
            "old_priority":"REAL", "new_priority":"REAL", "old_attention":"REAL", "new_attention":"REAL",
            "diversity_reason":"TEXT", "exploration_pressure":"REAL", "inhibition_level":"REAL",
            "details":"TEXT", "created_at":"INTEGER"
        }, changes)

    _ensure_table(cur, "phase5b_neuromodulator_adaptation_events",
        """CREATE TABLE IF NOT EXISTS phase5b_neuromodulator_adaptation_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, adaptation_key TEXT, target TEXT,
            old_value REAL, new_value REAL, reason TEXT,
            dopamine REAL, serotonin REAL, glutamate REAL, gaba REAL, noradrenaline REAL, acetylcholine REAL,
            details TEXT, created_at INTEGER
        )""",
        {
            "adaptation_key":"TEXT", "target":"TEXT", "old_value":"REAL", "new_value":"REAL", "reason":"TEXT",
            "dopamine":"REAL", "serotonin":"REAL", "glutamate":"REAL", "gaba":"REAL", "noradrenaline":"REAL", "acetylcholine":"REAL",
            "details":"TEXT", "created_at":"INTEGER"
        }, changes)

    _ensure_table(cur, "phase5b_internal_question_clusters",
        """CREATE TABLE IF NOT EXISTS phase5b_internal_question_clusters(
            cluster_key TEXT PRIMARY KEY, question_type TEXT, role TEXT, size INTEGER,
            avg_priority REAL, avg_resolution_score REAL, representative_question TEXT,
            recommended_action TEXT, status TEXT, updated_at INTEGER
        )""",
        {
            "cluster_key":"TEXT", "question_type":"TEXT", "role":"TEXT", "size":"INTEGER",
            "avg_priority":"REAL", "avg_resolution_score":"REAL", "representative_question":"TEXT",
            "recommended_action":"TEXT", "status":"TEXT", "updated_at":"INTEGER"
        }, changes)

    # Future-compatible columns for existing tables.
    existing_specs = {
        "internal_learning_gaps": {
            "phase5b_strategy":"TEXT", "phase5b_strategy_reason":"TEXT", "phase5b_last_refined_at":"INTEGER",
            "persistence_score":"REAL", "diversity_need":"REAL", "strategy_refinement_count":"INTEGER"
        },
        "reading_queue": {
            "phase5b_priority":"REAL", "phase5b_reason":"TEXT", "phase5b_last_adjusted_at":"INTEGER", "cooldown_until":"INTEGER"
        },
        "chunk_attention_scores": {
            "phase5b_score":"REAL", "phase5b_reason":"TEXT", "phase5b_last_adjusted_at":"INTEGER", "diversity_score":"REAL"
        },
    }
    for table, cols in existing_specs.items():
        if _table_exists(cur, table):
            existing = set(_columns(cur, table))
            for col, typ in cols.items():
                if col not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
                    changes.append(f"add_column:{table}.{col}")

    for table, col in [
        ("phase5b_strategy_refinement_state", "key"),
        ("phase5b_persistent_gap_strategy", "gap_id"),
        ("phase5b_internal_question_clusters", "cluster_key"),
        ("internal_learning_gaps", "gap_key"),
        ("reading_queue", "chunk_id"),
        ("chunk_attention_scores", "chunk_id"),
    ]:
        if _table_exists(cur, table):
            _ensure_unique(cur, table, col, changes)

    _set_state(cur, "phase5b_strategy_refinement_state", "phase", PHASE)
    cur.execute("INSERT OR IGNORE INTO phase5b_strategy_refinement_state(key,value,updated_at) VALUES('bias_feedback_gain','0.5',?)", (_now(),))
    _set_state(cur, "phase5b_strategy_refinement_state", "no_word_blacklists", "true")
    _set_state(cur, "phase5b_strategy_refinement_state", "learning_mode", LEARNING_MODE)
    _set_state(cur, "phase5b_strategy_refinement_state", "fact_promotion", "disabled")
    _set_state(cur, "phase5b_strategy_refinement_state", "direct_fact_writes", "disabled")
    _set_state(cur, "phase5b_strategy_refinement_state", "direct_relation_writes", "disabled")
    _set_state(cur, "phase5b_strategy_refinement_state", "question_generation", "stageb_promoted_questions")

    con.commit()
    if close:
        con.close()
    return {"status":"ok", "phase":PHASE, "changes":changes, "no_word_blacklists":True, "fact_promotion":"disabled"}

def _metric(cur: sqlite3.Cursor, table: str, default: int = 0) -> int:
    if not _table_exists(cur, table):
        return default
    return int(cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] or 0)

def _avg(cur: sqlite3.Cursor, table: str, col: str, default: float = 0.0, where: str = "") -> float:
    if not _table_exists(cur, table) or col not in _columns(cur, table):
        return default
    sql = f"SELECT AVG(COALESCE({col},0)) FROM {table} {where}"
    val = cur.execute(sql).fetchone()[0]
    return float(val or default)

def _current_control(cur: sqlite3.Cursor) -> Dict[str, float]:
    from ki_system.v8_learning_controls import current_controls
    return current_controls(cur)

def apply_strategy_refinement(memory: Any = None, limit_gaps: int = 240, limit_chunks: int = 600) -> Dict[str, Any]:
    """Refine strategy using outcomes, persistent gaps, clusters and neuromodulated controls."""
    ensure_phase5b_schema(memory)
    con, close = _connect_from_memory(memory)
    cur = con.cursor()
    now = _now()
    ctrl = _current_control(cur)

    facts = _metric(cur, "facts")
    relations = _metric(cur, "relations")
    questions = _metric(cur, "questions")

    # Aggregate current outcome signals.
    avg_res = _avg(cur, "internal_learning_gaps", "resolution_score", 0.0)
    avg_eff = _avg(cur, "internal_learning_gaps", "strategy_effectiveness_score", 0.0)
    avg_pri = _avg(cur, "internal_learning_gaps", "priority", 0.0)
    persistent = 0
    if _table_exists(cur, "internal_learning_gaps") and "status" in _columns(cur, "internal_learning_gaps"):
        persistent = int(cur.execute("SELECT COUNT(*) FROM internal_learning_gaps WHERE status='open'").fetchone()[0] or 0)

    # Strategy recommendation based on persistent gaps and outcome.
    if avg_res < 0.12 and persistent > 100:
        recommendation = "increase_diversity_and_context_window"
        new_exploration = min(0.75, ctrl["exploration_pressure"] + 0.035)
        new_inhibition = min(0.75, ctrl["inhibition_level"] + 0.015)
    elif avg_eff > 0.55 and avg_res > 0.25:
        recommendation = "reinforce_successful_strategy"
        new_exploration = max(0.15, ctrl["exploration_pressure"] - 0.01)
        new_inhibition = ctrl["inhibition_level"]
    else:
        recommendation = "balanced_refinement_observe"
        new_exploration = min(0.70, ctrl["exploration_pressure"] + 0.015)
        new_inhibition = ctrl["inhibition_level"]

    # Top-down strategy control: many persistent, unresolved gaps push toward
    # exploration, success toward exploitation (Cohen, McClure & Yu 2007).
    # The recommendation moves the persistent bias target (restored by Phase
    # 6c every cycle) by a damped step; Phases 6d (saturation homeostasis)
    # and 7b (anandamide pull toward mid-range) counteract extremes.
    feedback_gain = max(0.0, min(1.0, _state_float(cur, "phase5b_strategy_refinement_state", "bias_feedback_gain", 0.5)))
    applied = {}
    if feedback_gain > 0 and _table_exists(cur, "phase6c_target_bias_state"):
        for key, old, new in (("last_exploration_bias", ctrl["exploration_pressure"], new_exploration),
                              ("last_inhibition_bias", ctrl["inhibition_level"], new_inhibition)):
            value = round(max(0.0, min(1.0, old + feedback_gain * (new - old))), 6)
            if abs(value - old) < 1e-9:
                continue
            for table in ("phase6c_target_bias_state", "phase6a_meta_plasticity_state", "phase6a_neuromodulated_sleep_state"):
                if _table_exists(cur, table):
                    cur.execute("INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
                                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                                (key, str(value), now))
            applied[key] = value

    # Persist neuromodulator adaptation events.
    adaptations = [
        ("exploration_pressure", ctrl["exploration_pressure"], new_exploration, recommendation),
        ("inhibition_level", ctrl["inhibition_level"], new_inhibition, recommendation),
    ]
    for target, old, new, reason in adaptations:
        cur.execute("""INSERT INTO phase5b_neuromodulator_adaptation_events(
            adaptation_key,target,old_value,new_value,reason,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,details,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"{target}:{now}", target, old, new, reason, ctrl["dopamine"], ctrl["serotonin"], ctrl["glutamate"], ctrl["gaba"], ctrl["noradrenaline"], ctrl["acetylcholine"],
             _json({"avg_resolution_score": avg_res, "avg_strategy_effectiveness": avg_eff, "persistent_gaps": persistent,
                    "applied_to_bias_target": applied, "feedback_gain": feedback_gain}), now))

    # Persistent gap strategies.
    updated_gaps = 0
    if _table_exists(cur, "internal_learning_gaps"):
        gap_cols = _columns(cur, "internal_learning_gaps")
        order_col = "priority" if "priority" in gap_cols else "severity"
        rows = cur.execute(f"""SELECT id, gap_key, gap_type, role,
            COALESCE(priority, severity, 0.5), COALESCE(resolution_score,0), COALESCE(strategy_effectiveness_score,0),
            COALESCE(evidence_count,0), COALESCE(resolution_attempts,0)
            FROM internal_learning_gaps
            ORDER BY COALESCE(resolution_score,0) ASC, COALESCE({order_col},0) DESC, id DESC
            LIMIT ?""", (limit_gaps,)).fetchall()
        for gid, gap_key, gap_type, role, priority, res_score, eff_score, evidence_count, attempts in rows:
            persistence = max(0.0, min(1.0, (1.0 - float(res_score or 0)) * 0.65 + float(priority or 0) * 0.35))
            if persistence > 0.72:
                strat = "diversify_context_window"
                reason = "persistent_gap_low_resolution"
                after_priority = max(0.35, float(priority or 0) * 0.92)
                diversity = 0.20 + min(0.35, persistence * 0.25)
                cooldown = 0.15 + min(0.35, persistence * 0.20)
            elif eff_score > 0.45:
                strat = "continue_targeted_learning"
                reason = "strategy_effectiveness_positive"
                after_priority = min(1.0, float(priority or 0) * 1.02)
                diversity = 0.10
                cooldown = 0.05
            else:
                strat = "balanced_observe_and_reread"
                reason = "insufficient_resolution_evidence"
                after_priority = float(priority or 0)
                diversity = 0.15
                cooldown = 0.10
            cur.execute("""INSERT INTO phase5b_persistent_gap_strategy(
                gap_id,gap_key,gap_type,role,persistence_score,resolution_score,strategy_effectiveness_score,
                recommended_strategy,strategy_reason,priority_before,priority_after,reread_diversity_boost,cooldown_suggestion,status,evidence_count,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(gap_id) DO UPDATE SET
                    persistence_score=excluded.persistence_score,
                    resolution_score=excluded.resolution_score,
                    strategy_effectiveness_score=excluded.strategy_effectiveness_score,
                    recommended_strategy=excluded.recommended_strategy,
                    strategy_reason=excluded.strategy_reason,
                    priority_before=excluded.priority_before,
                    priority_after=excluded.priority_after,
                    reread_diversity_boost=excluded.reread_diversity_boost,
                    cooldown_suggestion=excluded.cooldown_suggestion,
                    status=excluded.status,
                    evidence_count=excluded.evidence_count,
                    updated_at=excluded.updated_at""",
                (gid, gap_key, gap_type, role, round(persistence, 6), float(res_score or 0), float(eff_score or 0), strat, reason,
                 float(priority or 0), round(after_priority,6), round(diversity,6), round(cooldown,6), "active", int(evidence_count or 0), now))
            cur.execute("UPDATE internal_learning_gaps SET phase5b_strategy=?, phase5b_strategy_reason=?, phase5b_last_refined_at=?, priority=?, diversity_need=?, persistence_score=?, strategy_refinement_count=COALESCE(strategy_refinement_count,0)+1 WHERE id=?",
                        (strat, reason, now, round(after_priority,6), round(diversity,6), round(persistence,6), gid))
            updated_gaps += 1

    # Cluster the open curiosity questions (Stage-B question promotion) by the
    # type and role of the gap each question came from.
    clustered = 0
    if _table_exists(cur, "questions") and _table_exists(cur, "internal_learning_gaps")             and "source_gap_id" in _columns(cur, "questions"):
        rows = cur.execute("""SELECT COALESCE(g.gap_type,'unknown'), COALESCE(g.role,'unknown'), COUNT(*),
               AVG(COALESCE(q.priority,0.5)), AVG(CASE WHEN q.status='open' THEN 0.0 ELSE 1.0 END),
               MAX(q.question)
               FROM questions q LEFT JOIN internal_learning_gaps g ON g.id=q.source_gap_id
               GROUP BY 1,2 ORDER BY COUNT(*) DESC LIMIT 50""").fetchall()
        for qtype, role, size, avgp, avgres, sample in rows:
            key = f"{qtype}:{role}"
            if (avgres or 0) < 0.15 and (avgp or 0) > 0.55:
                action = "seek_broader_context_and_compare_patterns"
            elif size and size > 20:
                action = "cluster_review_and_sampling"
            else:
                action = "observe_more_evidence"
            cur.execute("""INSERT INTO phase5b_internal_question_clusters(
                cluster_key,question_type,role,size,avg_priority,avg_resolution_score,representative_question,recommended_action,status,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(cluster_key) DO UPDATE SET
                    size=excluded.size, avg_priority=excluded.avg_priority, avg_resolution_score=excluded.avg_resolution_score,
                    representative_question=excluded.representative_question,
                    recommended_action=excluded.recommended_action, status=excluded.status, updated_at=excluded.updated_at""",
                (key, qtype, role, int(size or 0), round(float(avgp or 0),6), round(float(avgres or 0),6),
                 (sample or "")[:500], action, "open", now))
            clustered += int(size or 0)

    # Diversify chunks: down-weight repeated high-priority read_candidate chunks slightly; lift under-read pending chunks.
    diversity_events = 0
    if _table_exists(cur, "reading_queue") and _table_exists(cur, "chunk_attention_scores"):
        rq_cols = _columns(cur, "reading_queue")
        ca_cols = _columns(cur, "chunk_attention_scores")
        top_rows = cur.execute("""SELECT rq.chunk_id, COALESCE(rq.priority,0.5), COALESCE(rq.attention_score,0.5), COALESCE(rq.status,'pending')
                                  FROM reading_queue rq
                                  ORDER BY COALESCE(rq.priority,0) DESC, COALESCE(rq.attention_score,0) DESC LIMIT ?""", (limit_chunks,)).fetchall()
        for chunk_id, pri, att, status in top_rows[:max(50, min(220, len(top_rows)))]:
            oldp, olda = float(pri or 0), float(att or 0)
            if status == "read_candidate" and oldp > 0.70:
                newp = max(0.35, oldp - 0.035)
                newa = max(0.35, olda - 0.025)
                reason = "phase5b_reduce_repeated_high_priority_reread"
            elif status == "pending" and oldp < 0.66:
                newp = min(0.82, oldp + 0.025 + (new_exploration * 0.02))
                newa = min(0.86, olda + 0.025 + (new_exploration * 0.02))
                reason = "phase5b_boost_underread_pending_context"
            else:
                continue
            cur.execute("UPDATE reading_queue SET priority=?, attention_score=?, reason=?, phase5b_priority=?, phase5b_reason=?, phase5b_last_adjusted_at=? WHERE chunk_id=?",
                        (round(newp,6), round(newa,6), reason, round(newp,6), reason, now, chunk_id))
            if "phase5b_score" in ca_cols:
                cur.execute("INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,reward_score,fatigue_score,last_reason,updated_at,phase5b_score,phase5b_reason,phase5b_last_adjusted_at,diversity_score) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET attention_score=excluded.attention_score,last_reason=excluded.last_reason,updated_at=excluded.updated_at,phase5b_score=excluded.phase5b_score,phase5b_reason=excluded.phase5b_reason,phase5b_last_adjusted_at=excluded.phase5b_last_adjusted_at,diversity_score=excluded.diversity_score",
                            (chunk_id, round(newa,6), 0.55, 0.45, 0.0, 0.15, reason, now, round(newa,6), reason, now, round(abs(newa-olda),6)))
            cur.execute("""INSERT INTO phase5b_reread_diversity_events(
                chunk_id,gap_id,gap_type,role,old_priority,new_priority,old_attention,new_attention,diversity_reason,exploration_pressure,inhibition_level,details,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (chunk_id, None, None, None, oldp, round(newp,6), olda, round(newa,6), reason, new_exploration, new_inhibition, _json({"status": status}), now))
            diversity_events += 1

    # Cycle record and state.
    cur.execute("""INSERT INTO phase5b_strategy_refinement_cycles(
        phase,cycle_kind,persistent_gaps,clustered_questions,diversity_events,neuromodulator_adaptations,
        avg_resolution_score,avg_strategy_effectiveness,exploration_pressure,inhibition_level,recommendation,details,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (PHASE, "strategy_refinement", persistent, clustered, diversity_events, len(adaptations), avg_res, avg_eff, new_exploration, new_inhibition, recommendation,
         _json({"avg_priority": avg_pri, "updated_gaps": updated_gaps}), now))

    for k, v in {
        "phase": PHASE,
        "no_word_blacklists": "true",
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "last_updated_gaps": updated_gaps,
        "last_clustered_questions": clustered,
        "last_diversity_events": diversity_events,
        "last_recommendation": recommendation,
        "last_avg_resolution_score": round(avg_res,6),
        "last_avg_strategy_effectiveness": round(avg_eff,6),
        "last_exploration_pressure": round(new_exploration,6),
        "last_inhibition_level": round(new_inhibition,6),
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "stageb_promoted_questions",
    }.items():
        _set_state(cur, "phase5b_strategy_refinement_state", k, v)

    con.commit()
    summary = {
        "status": "phase5b_strategy_refinement_complete",
        "phase": PHASE,
        "persistent_gaps": persistent,
        "updated_gaps": updated_gaps,
        "clustered_questions": clustered,
        "diversity_events": diversity_events,
        "recommendation": recommendation,
        "avg_resolution_score": round(avg_res,6),
        "avg_strategy_effectiveness": round(avg_eff,6),
        "exploration_pressure": round(new_exploration,6),
        "inhibition_level": round(new_inhibition,6),
        "no_word_blacklists": True,
        "fact_promotion": "disabled",
        "facts": facts,
        "relations": relations,
        "questions": questions,
    }
    if close:
        con.close()
    return summary

def _memory_from_loop(loop: Any) -> Any:
    for name in ("mem", "memory", "m", "store", "memory_store"):
        val = getattr(loop, name, None)
        if val is not None:
            return val
    return None

def managed_cycle(self, progress=None):
    result = None
    if _ORIGINAL_CYCLE is not None:
        result = _ORIGINAL_CYCLE(self, progress)
    summary = apply_strategy_refinement(_memory_from_loop(self))
    if isinstance(result, dict):
        result["phase5b_strategy_refinement"] = summary
        return result
    return {"status": PHASE, "previous_result": result, "phase5b_strategy_refinement": summary}

def managed_run(self, cycles=1, progress=None):
    results = []
    if _ORIGINAL_RUN is not None:
        prev = _ORIGINAL_RUN(self, cycles, progress)
        # Run one refinement pass after the wrapped runtime finishes.
        summary = apply_strategy_refinement(_memory_from_loop(self))
        return {"status": PHASE, "wrapped_result": prev, "phase5b_strategy_refinement": summary,
                "direct_fact_writes":"disabled", "direct_relation_writes":"disabled", "fact_promotion":"disabled", "no_word_blacklists": True}
    for _ in range(int(cycles or 1)):
        results.append(managed_cycle(self, progress))
    return results

def patch_autonomous_loop(*args, **kwargs):
    global _ORIGINAL_RUN, _ORIGINAL_CYCLE
    try:
        from ki_system.autonomous import AutonomousLoop
    except Exception:
        return False
    if getattr(AutonomousLoop, "_phase5b_integrated_strategy_refinement_release", False):
        return True
    _ORIGINAL_RUN = getattr(AutonomousLoop, "run", None)
    _ORIGINAL_CYCLE = getattr(AutonomousLoop, "cycle", None)
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    for attr in (
        "phase5b_integrated_strategy_refinement_release",
        "_phase5b_integrated_strategy_refinement_release",
    ):
        setattr(AutonomousLoop, attr, True)
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._learning_mode = LEARNING_MODE
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop._fact_promotion = "disabled"
    AutonomousLoop.fact_promotion = "disabled"
    return True

try:
    patch_autonomous_loop()
except Exception as _phase5b_autoload_exc:
    print("[PHASE5B_AUTOLOAD_ERROR]", _phase5b_autoload_exc)
