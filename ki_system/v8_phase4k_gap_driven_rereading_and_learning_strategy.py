# V8-phase4k_gap_driven_rereading_and_learning_strategy
# Ziel: interne Lernlücken steuern Wiederlesen und Lernstrategie.
# Keine Wort-Blacklists, keine facts/relations/questions Writes.

import json
import sqlite3
import time
from collections import defaultdict

PHASE = "phase4k_gap_driven_rereading_and_learning_strategy"

_ORIG_RUN = None
_ORIG_CYCLE = None


def _now():
    return int(time.time())


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _connect_from_memory(mem):
    """Return sqlite3 connection from flexible Memory-like object."""
    if isinstance(mem, sqlite3.Connection):
        return mem
    for attr in ("con", "conn", "connection", "db", "sqlite", "_con", "_conn"):
        val = getattr(mem, attr, None)
        if isinstance(val, sqlite3.Connection):
            return val
    # fallback: common project database path
    return sqlite3.connect("ki_memory.sqlite3")


def _memory_from_loop(loop):
    for attr in ("mem", "memory", "m", "store", "memory_store"):
        val = getattr(loop, attr, None)
        if val is not None:
            return val
    # fallback: inspect object dict for something that has sqlite connection
    for val in getattr(loop, "__dict__", {}).values():
        if isinstance(val, sqlite3.Connection):
            return val
        if any(isinstance(getattr(val, a, None), sqlite3.Connection) for a in ("con", "conn", "connection", "db")):
            return val
    return sqlite3.connect("ki_memory.sqlite3")


def _table_exists(db, table):
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(db, table):
    if not _table_exists(db, table):
        return []
    return [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]


def _add_col(db, table, col, typ):
    if col not in _cols(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        return True
    return False


def _safe_count(db, table):
    if not _table_exists(db, table):
        return 0
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def ensure_phase4k_schema(mem_or_db):
    db = _connect_from_memory(mem_or_db)
    changes = []

    # Core existing tables are not assumed to be perfect; this patch only adds what it needs.
    db.execute("""CREATE TABLE IF NOT EXISTS reading_queue(
        chunk_id INTEGER PRIMARY KEY,
        priority REAL DEFAULT 0,
        reason TEXT,
        attention_score REAL DEFAULT 0,
        read_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        last_read INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")

    db.execute("""CREATE TABLE IF NOT EXISTS gap_driven_rereading_actions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gap_id INTEGER,
        question_id INTEGER,
        gap_key TEXT,
        gap_type TEXT,
        role TEXT,
        chunk_id INTEGER,
        action_type TEXT,
        priority_boost REAL DEFAULT 0,
        attention_score REAL DEFAULT 0,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        reason TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")

    db.execute("""CREATE TABLE IF NOT EXISTS gap_reread_strategy_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")

    db.execute("""CREATE TABLE IF NOT EXISTS gap_question_resolution_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        gap_id INTEGER,
        event_type TEXT,
        old_status TEXT,
        new_status TEXT,
        confidence_delta REAL DEFAULT 0,
        uncertainty_delta REAL DEFAULT 0,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")

    db.execute("""CREATE TABLE IF NOT EXISTS rereading_candidate_links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gap_key TEXT,
        pattern_key TEXT,
        chunk_id INTEGER,
        role TEXT,
        link_strength REAL DEFAULT 0,
        reason TEXT,
        created_at INTEGER DEFAULT 0
    )""")

    # Ensure phase4j tables tolerate action metadata, if present.
    if _table_exists(db, "internal_learning_gaps"):
        for col, typ in [
            ("last_action_at", "INTEGER DEFAULT 0"),
            ("action_count", "INTEGER DEFAULT 0"),
            ("reread_priority", "REAL DEFAULT 0"),
            ("learning_strategy", "TEXT"),
        ]:
            if _add_col(db, "internal_learning_gaps", col, typ): changes.append(f"add_column:internal_learning_gaps.{col}")
    if _table_exists(db, "internal_learning_questions"):
        for col, typ in [
            ("last_action_at", "INTEGER DEFAULT 0"),
            ("action_count", "INTEGER DEFAULT 0"),
            ("reread_priority", "REAL DEFAULT 0"),
            ("learning_strategy", "TEXT"),
        ]:
            if _add_col(db, "internal_learning_questions", col, typ): changes.append(f"add_column:internal_learning_questions.{col}")

    # Make attention/strategy tables exist if previous phases did not create them.
    db.execute("""CREATE TABLE IF NOT EXISTS chunk_attention_scores(
        chunk_id INTEGER PRIMARY KEY,
        attention_score REAL DEFAULT 0,
        novelty_score REAL DEFAULT 0,
        uncertainty_score REAL DEFAULT 0,
        reward_score REAL DEFAULT 0,
        fatigue_score REAL DEFAULT 0,
        last_reason TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS reading_strategy_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS attention_queue_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")

    # Unique indexes for stable UPSERTs.
    for table, col in [
        ("reading_queue", "chunk_id"),
        ("chunk_attention_scores", "chunk_id"),
        ("gap_reread_strategy_state", "key"),
        ("reading_strategy_state", "key"),
        ("attention_queue_state", "key"),
    ]:
        if col in _cols(db, table):
            name = f"idx_{table}_{col}_phase4k_unique"
            db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table}({col})")
            changes.append(f"unique_index:{table}.{col}")

    now = _now()
    for k, v in [
        ("phase", PHASE),
        ("no_word_blacklists", "true"),
        ("learning_mode", "context_hypotheses_with_neuromodulators"),
        ("fact_promotion", "disabled"),
        ("question_generation", "internal_learning_questions_only"),
    ]:
        db.execute("INSERT INTO gap_reread_strategy_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, v, now))
    db.commit()
    return {"status": "ok", "phase": PHASE, "changes": changes}


def _get_recent_learning_state(db):
    defaults = {
        "learning_rate": 0.22,
        "error_weight": 0.40,
        "revision_pressure": 0.30,
        "consolidation_gain": 0.28,
        "exploration_pressure": 0.31,
        "inhibition_level": 0.34,
    }
    if not _table_exists(db, "neuromodulator_learning_state"):
        return defaults
    cols = _cols(db, "neuromodulator_learning_state")
    wanted = [c for c in defaults if c in cols]
    if not wanted:
        return defaults
    row = db.execute(f"SELECT {', '.join(wanted)} FROM neuromodulator_learning_state ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return defaults
    out = defaults.copy()
    for c, v in zip(wanted, row):
        if v is not None:
            out[c] = float(v)
    return out


def _select_open_gaps(db, limit=80):
    if not _table_exists(db, "internal_learning_gaps"):
        return []
    cols = _cols(db, "internal_learning_gaps")
    select_cols = []
    for c in ["id", "gap_key", "gap_type", "role", "severity", "priority", "status", "details", "reread_priority"]:
        select_cols.append(c if c in cols else f"NULL AS {c}")
    status_filter = ""
    if "status" in cols:
        status_filter = "WHERE status IS NULL OR status IN ('open','internal_open','active','observe')"
    order_terms = []
    if "reread_priority" in cols: order_terms.append("COALESCE(reread_priority,0) DESC")
    if "priority" in cols: order_terms.append("COALESCE(priority,0) DESC")
    if "severity" in cols: order_terms.append("COALESCE(severity,0) DESC")
    order = "ORDER BY " + ", ".join(order_terms) if order_terms else "ORDER BY id DESC"
    sql = f"SELECT {', '.join(select_cols)} FROM internal_learning_gaps {status_filter} {order} LIMIT ?"
    rows = db.execute(sql, (limit,)).fetchall()
    keys = ["id", "gap_key", "gap_type", "role", "severity", "priority", "status", "details", "reread_priority"]
    return [dict(zip(keys, r)) for r in rows]


def _candidate_chunks_for_gap(db, gap, limit=8):
    role = gap.get("role")
    gap_key = (gap.get("gap_key") or "")[:80]
    out = []
    seen = set()

    # Prefer high-uncertainty hypotheses of the same role.
    if _table_exists(db, "context_hypotheses"):
        cols = _cols(db, "context_hypotheses")
        if "chunk_id" in cols:
            where = []
            params = []
            if role and "role" in cols:
                where.append("role=?")
                params.append(role)
            if "uncertainty" in cols:
                where.append("COALESCE(uncertainty,0) >= 0.45")
            sql = "SELECT DISTINCT chunk_id FROM context_hypotheses"
            if where:
                sql += " WHERE " + " AND ".join(where)
            order = ""
            if "uncertainty" in cols:
                order = " ORDER BY uncertainty DESC"
            sql += order + " LIMIT ?"
            params.append(limit)
            try:
                for (cid,) in db.execute(sql, tuple(params)).fetchall():
                    if cid is not None and cid not in seen:
                        out.append(int(cid)); seen.add(int(cid))
            except Exception:
                pass

    # Fallback from context_pattern_memory pattern text if available.
    if len(out) < limit and _table_exists(db, "context_pattern_memory") and _table_exists(db, "context_hypotheses"):
        cp_cols = _cols(db, "context_pattern_memory")
        ch_cols = _cols(db, "context_hypotheses")
        if "pattern_key" in cp_cols and "chunk_id" in ch_cols and "text_excerpt" in ch_cols:
            token = ""
            if ":" in gap_key:
                token = gap_key.split(":", 1)[1].strip()[:24]
            if token:
                try:
                    for (cid,) in db.execute("SELECT DISTINCT chunk_id FROM context_hypotheses WHERE text_excerpt LIKE ? LIMIT ?", (f"%{token}%", limit)).fetchall():
                        if cid is not None and cid not in seen:
                            out.append(int(cid)); seen.add(int(cid))
                except Exception:
                    pass

    # Last resort: pending/read candidate chunks from reading_queue.
    if len(out) < limit and _table_exists(db, "reading_queue"):
        try:
            for (cid,) in db.execute("SELECT chunk_id FROM reading_queue WHERE status='pending' ORDER BY priority DESC, attention_score DESC LIMIT ?", (limit-len(out),)).fetchall():
                if cid is not None and cid not in seen:
                    out.append(int(cid)); seen.add(int(cid))
        except Exception:
            pass
    return out[:limit]


def _neuromodulators_for_gap(gap, state):
    severity = float(gap.get("severity") or gap.get("priority") or 0.5)
    # Bound to useful range.
    sev = max(0.0, min(1.0, severity))
    return {
        "dopamine": round(0.35 + 0.25 * max(0.0, 1.0 - sev), 3),
        "serotonin": round(0.38 + 0.18 * state.get("consolidation_gain", 0.28), 3),
        "glutamate": round(0.40 + 0.35 * state.get("exploration_pressure", 0.31), 3),
        "gaba": round(0.30 + 0.45 * state.get("inhibition_level", 0.34), 3),
        "noradrenaline": round(0.35 + 0.45 * sev, 3),
        "acetylcholine": round(0.35 + 0.35 * state.get("revision_pressure", 0.30), 3),
    }


def activate_gap_driven_rereading(mem_or_db, max_gaps=30, chunks_per_gap=6):
    db = _connect_from_memory(mem_or_db)
    ensure_phase4k_schema(db)
    now = _now()
    state = _get_recent_learning_state(db)
    gaps = _select_open_gaps(db, max_gaps)
    actions = 0
    linked_chunks = 0
    updated_gaps = 0
    per_type = defaultdict(int)

    for gap in gaps:
        gap_id = gap.get("id")
        gap_key = gap.get("gap_key") or f"gap:{gap_id}"
        gap_type = gap.get("gap_type") or "unknown_gap"
        role = gap.get("role") or "unknown_role"
        severity = float(gap.get("severity") or gap.get("priority") or 0.5)
        nm = _neuromodulators_for_gap(gap, state)
        # Strategy score: high uncertainty/gap severity should drive rereading, moderated by inhibition.
        priority_boost = max(0.05, min(1.0, 0.20 + 0.50*severity + 0.20*state.get("revision_pressure",0.3) + 0.10*state.get("exploration_pressure",0.31) - 0.15*state.get("inhibition_level",0.34)))
        attention_score = max(0.05, min(1.0, 0.35 + priority_boost*0.45 + nm["noradrenaline"]*0.15 + nm["acetylcholine"]*0.10 - nm["gaba"]*0.10))

        chunks = _candidate_chunks_for_gap(db, gap, chunks_per_gap)
        if chunks:
            for cid in chunks:
                # Upsert queue priority. Does not write facts/relations/questions.
                db.execute("""INSERT INTO reading_queue(chunk_id,priority,reason,attention_score,read_count,status,last_read,updated_at)
                              VALUES(?,?,?,?,0,'pending',0,?)
                              ON CONFLICT(chunk_id) DO UPDATE SET
                                priority = MAX(priority, excluded.priority),
                                attention_score = MAX(attention_score, excluded.attention_score),
                                reason = excluded.reason,
                                status = CASE WHEN reading_queue.status='read_no_candidate' THEN 'pending' ELSE reading_queue.status END,
                                updated_at = excluded.updated_at""",
                           (cid, round(priority_boost,3), "phase4k_gap_driven_rereading", round(attention_score,3), now))
                db.execute("""INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,reward_score,fatigue_score,last_reason,updated_at)
                              VALUES(?,?,?,?,?,?,?,?)
                              ON CONFLICT(chunk_id) DO UPDATE SET
                                attention_score=MAX(attention_score, excluded.attention_score),
                                uncertainty_score=MAX(uncertainty_score, excluded.uncertainty_score),
                                reward_score=MAX(reward_score, excluded.reward_score),
                                last_reason=excluded.last_reason,
                                updated_at=excluded.updated_at""",
                           (cid, round(attention_score,3), round(state.get("exploration_pressure",0.31),3), round(severity,3), round(nm["dopamine"],3), round(nm["gaba"],3), "phase4k_gap_driven_rereading", now))
                db.execute("""INSERT INTO gap_driven_rereading_actions(gap_id,question_id,gap_key,gap_type,role,chunk_id,action_type,priority_boost,attention_score,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,reason,details,created_at)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (gap_id, None, gap_key, gap_type, role, cid, "reread_prioritize_chunk", round(priority_boost,3), round(attention_score,3), nm["dopamine"], nm["serotonin"], nm["glutamate"], nm["gaba"], nm["noradrenaline"], nm["acetylcholine"], "internal_gap_drives_rereading", _json({"severity": severity, "learning_state": state}), now))
                db.execute("""INSERT INTO rereading_candidate_links(gap_key,pattern_key,chunk_id,role,link_strength,reason,created_at)
                              VALUES(?,?,?,?,?,?,?)""", (gap_key, gap_key, cid, role, round(attention_score,3), "phase4k_gap_chunk_link", now))
                actions += 1
                linked_chunks += 1
        else:
            db.execute("""INSERT INTO gap_driven_rereading_actions(gap_id,question_id,gap_key,gap_type,role,chunk_id,action_type,priority_boost,attention_score,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,reason,details,created_at)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (gap_id, None, gap_key, gap_type, role, None, "reread_no_chunk_found", round(priority_boost,3), round(attention_score,3), nm["dopamine"], nm["serotonin"], nm["glutamate"], nm["gaba"], nm["noradrenaline"], nm["acetylcholine"], "gap_detected_but_no_candidate_chunk", _json({"severity": severity}), now))
            actions += 1

        per_type[gap_type] += 1
        # Mark gap/question as acted upon, but not closed; it remains an internal learning problem until resolved by evidence.
        if _table_exists(db, "internal_learning_gaps"):
            cols = _cols(db, "internal_learning_gaps")
            pieces = []
            params = []
            if "last_action_at" in cols: pieces.append("last_action_at=?"); params.append(now)
            if "action_count" in cols: pieces.append("action_count=COALESCE(action_count,0)+1")
            if "reread_priority" in cols: pieces.append("reread_priority=?"); params.append(round(priority_boost,3))
            if "learning_strategy" in cols: pieces.append("learning_strategy=?"); params.append("gap_driven_rereading")
            if pieces and gap_id is not None and "id" in cols:
                params.append(gap_id)
                db.execute(f"UPDATE internal_learning_gaps SET {', '.join(pieces)} WHERE id=?", tuple(params))
                updated_gaps += 1

    # State snapshots for tools and future strategy.
    state_rows = {
        "phase": PHASE,
        "last_gap_rereading_at": str(now),
        "last_gaps_considered": str(len(gaps)),
        "last_reread_actions": str(actions),
        "last_linked_chunks": str(linked_chunks),
        "last_learning_rate": str(state.get("learning_rate")),
        "last_error_weight": str(state.get("error_weight")),
        "last_revision_pressure": str(state.get("revision_pressure")),
        "last_exploration_pressure": str(state.get("exploration_pressure")),
        "last_inhibition_level": str(state.get("inhibition_level")),
        "no_word_blacklists": "true",
        "fact_promotion": "disabled",
        "question_generation": "internal_learning_questions_only",
    }
    for table in ("gap_reread_strategy_state", "reading_strategy_state", "attention_queue_state"):
        for k, v in state_rows.items():
            db.execute(f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, v, now))

    # Safety state propagation.
    if _table_exists(db, "rollback_safe_core_state"):
        for k, v in [("phase", PHASE), ("no_word_blacklists", "true"), ("fact_promotion", "disabled")]:
            try:
                db.execute("INSERT INTO rollback_safe_core_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, _json(v)))
            except Exception:
                pass

    db.commit()
    return {
        "status": "phase4k_gap_driven_rereading_complete",
        "phase": PHASE,
        "gaps_considered": len(gaps),
        "actions": actions,
        "linked_chunks": linked_chunks,
        "updated_gaps": updated_gaps,
        "gap_types": dict(per_type),
        "no_word_blacklists": True,
        "fact_promotion": "disabled",
    }


def managed_cycle(self, progress=None):
    mem = _memory_from_loop(self)
    ensure_phase4k_schema(mem)
    base_result = None
    if _ORIG_CYCLE is not None and _ORIG_CYCLE is not managed_cycle:
        base_result = _ORIG_CYCLE(self, progress)
    summary = activate_gap_driven_rereading(mem)
    if isinstance(base_result, dict):
        base_result["phase4k_gap_driven_rereading"] = summary
        return base_result
    return {"status": "phase4k_managed_cycle", "base_result": base_result, "phase4k_gap_driven_rereading": summary}


def managed_run(self, cycles=1, progress=None):
    mem = _memory_from_loop(self)
    ensure_phase4k_schema(mem)
    results = []
    if _ORIG_RUN is not None and _ORIG_RUN is not managed_run:
        base = _ORIG_RUN(self, cycles, progress)
        # Run additional strategy once after the base run to avoid excessive queue churn.
        summary = activate_gap_driven_rereading(mem)
        return {"status": "phase4k_managed_run", "base_result": base, "phase4k_gap_driven_rereading": summary}
    for _ in range(cycles or 1):
        results.append(managed_cycle(self, progress))
    return results


def patch_autonomous_loop(AutonomousLoop=None):
    global _ORIG_RUN, _ORIG_CYCLE
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AL
        AutonomousLoop = AL
    current_run = getattr(AutonomousLoop, "run", None)
    current_cycle = getattr(AutonomousLoop, "cycle", None)
    if current_run is not managed_run:
        _ORIG_RUN = current_run
    if current_cycle is not managed_cycle:
        _ORIG_CYCLE = current_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    # Set both marker styles for compatibility with older test tools.
    for name in [
        "phase4k_gap_driven_rereading_and_learning_strategy",
        "_phase4k_gap_driven_rereading_and_learning_strategy",
        "phase4j_internal_learning_questions_and_gap_detection",
        "_phase4j_internal_learning_questions_and_gap_detection",
        "phase4i_long_term_memory_and_pattern_stability",
        "_phase4i_long_term_memory_and_pattern_stability",
    ]:
        setattr(AutonomousLoop, name, True)
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.learning_mode = "context_hypotheses_with_neuromodulators"
    AutonomousLoop._rollback_learning_mode = "context_hypotheses_with_neuromodulators"
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop._fact_promotion = "disabled"
    return AutonomousLoop
