
# V8 Phase5h Schema Guard FIXED1
# Ziel: Phase5h Outcome-Learning robust gegen alte/teilweise Schemas absichern.
# Keine Wort-Blacklists, keine facts/relations/questions Writes, keine Fact-Promotion.
from __future__ import annotations
import sqlite3, time, json, traceback
from pathlib import Path

PHASE = "phase5h_schema_guard_fixed1"
BASE_PHASE = "phase5h_strategy_experiment_outcome_learning_release"

TEXT = "TEXT"
REAL = "REAL"
INTEGER = "INTEGER"

TABLE_COLUMNS = {
    "phase5g_strategy_experiments": {
        "id": "INTEGER",
        "experiment_key": TEXT,
        "gap_id": INTEGER,
        "gap_key": TEXT,
        "gap_type": TEXT,
        "role": TEXT,
        "source_chunk_id": INTEGER,
        "target_chunk_id": INTEGER,
        "selected_strategy": TEXT,
        "window_strategy": TEXT,
        "window_radius": INTEGER,
        "read_status": TEXT,
        "closure_delta": REAL,
        "no_candidate_rate": REAL,
        "overlap_score": REAL,
        "strategy_score": REAL,
        "outcome_score": REAL,
        "phase5h_outcome_score": REAL,
        "phase5h_outcome_label": TEXT,
        "phase5h_last_evaluated_at": INTEGER,
        "phase5h_memory_key": TEXT,
        "phase5h_reason": TEXT,
        "details": TEXT,
        "created_at": INTEGER,
        "updated_at": INTEGER,
    },
    "phase5g_experiment_outcomes": {
        "id": "INTEGER",
        "outcome_key": TEXT,
        "experiment_key": TEXT,
        "experiment_id": INTEGER,
        "gap_id": INTEGER,
        "gap_key": TEXT,
        "gap_type": TEXT,
        "role": TEXT,
        "source_chunk_id": INTEGER,
        "target_chunk_id": INTEGER,
        "selected_strategy": TEXT,
        "window_strategy": TEXT,
        "window_radius": INTEGER,
        "read_status": TEXT,
        "closure_delta": REAL,
        "no_candidate_rate": REAL,
        "overlap_score": REAL,
        "strategy_score": REAL,
        "outcome_score": REAL,
        "outcome_label": TEXT,
        "recommendation": TEXT,
        "learning_rate": REAL,
        "error_weight": REAL,
        "revision_pressure": REAL,
        "exploration_pressure": REAL,
        "inhibition_level": REAL,
        "consolidation_gain": REAL,
        "dopamine": REAL,
        "serotonin": REAL,
        "glutamate": REAL,
        "gaba": REAL,
        "noradrenaline": REAL,
        "acetylcholine": REAL,
        "details": TEXT,
        "created_at": INTEGER,
        "updated_at": INTEGER,
    },
    "phase5g_strategy_selection_memory": {
        "memory_key": TEXT,
        "gap_type": TEXT,
        "role": TEXT,
        "selected_strategy": TEXT,
        "observations": INTEGER,
        "avg_closure_delta": REAL,
        "avg_no_candidate_rate": REAL,
        "avg_overlap_score": REAL,
        "avg_strategy_score": REAL,
        "avg_outcome_score": REAL,
        "success_count": INTEGER,
        "failure_count": INTEGER,
        "recommendation": TEXT,
        "neuromodulator_profile": TEXT,
        "created_at": INTEGER,
        "updated_at": INTEGER,
    },
    "phase5h_strategy_outcome_memory": {
        "memory_key": TEXT,
        "gap_type": TEXT,
        "role": TEXT,
        "selected_strategy": TEXT,
        "observations": INTEGER,
        "avg_outcome_score": REAL,
        "avg_closure_delta": REAL,
        "avg_no_candidate_rate": REAL,
        "avg_overlap_score": REAL,
        "success_count": INTEGER,
        "failure_count": INTEGER,
        "recommendation": TEXT,
        "created_at": INTEGER,
        "updated_at": INTEGER,
    },
    "phase5h_experiment_outcome_cycles": {
        "id": "INTEGER",
        "phase": TEXT,
        "experiments_seen": INTEGER,
        "outcomes_written": INTEGER,
        "memory_updates": INTEGER,
        "avg_outcome_score": REAL,
        "avg_closure_delta": REAL,
        "avg_no_candidate_rate": REAL,
        "avg_overlap_score": REAL,
        "facts": INTEGER,
        "relations": INTEGER,
        "questions": INTEGER,
        "created_at": INTEGER,
    },
    "phase5h_experiment_learning_events": {
        "id": "INTEGER",
        "event_type": TEXT,
        "experiment_key": TEXT,
        "memory_key": TEXT,
        "selected_strategy": TEXT,
        "outcome_score": REAL,
        "closure_delta": REAL,
        "no_candidate_rate": REAL,
        "overlap_score": REAL,
        "recommendation": TEXT,
        "details": TEXT,
        "created_at": INTEGER,
    },
    "phase5h_runtime_state": {"key": TEXT, "value": TEXT, "updated_at": INTEGER},
    "internal_learning_gaps": {
        "phase5h_strategy_outcome_score": REAL,
        "phase5h_strategy_memory_key": TEXT,
        "phase5h_last_outcome_at": INTEGER,
        "phase5h_recommendation": TEXT,
        "phase5h_reason": TEXT,
    },
    "chunk_attention_scores": {
        "phase5h_strategy_outcome_score": REAL,
        "phase5h_strategy_memory_key": TEXT,
        "phase5h_last_outcome_at": INTEGER,
        "phase5h_recommendation": TEXT,
        "phase5h_reason": TEXT,
    },
    "reading_queue": {
        "phase5h_strategy_outcome_score": REAL,
        "phase5h_strategy_memory_key": TEXT,
        "phase5h_last_outcome_at": INTEGER,
        "phase5h_recommendation": TEXT,
        "phase5h_reason": TEXT,
    },
    "phase5g_neuromodulator_strategy_profiles": {
        "avg_outcome_score": REAL,
        "avg_no_candidate_rate": REAL,
        "avg_overlap_score": REAL,
        "phase5h_last_updated_at": INTEGER,
        "phase5h_recommendation": TEXT,
    },
}

CREATE_SQL = {
    "phase5g_strategy_experiments": "CREATE TABLE IF NOT EXISTS phase5g_strategy_experiments (id INTEGER PRIMARY KEY AUTOINCREMENT)",
    "phase5g_experiment_outcomes": "CREATE TABLE IF NOT EXISTS phase5g_experiment_outcomes (id INTEGER PRIMARY KEY AUTOINCREMENT)",
    "phase5g_strategy_selection_memory": "CREATE TABLE IF NOT EXISTS phase5g_strategy_selection_memory (memory_key TEXT PRIMARY KEY)",
    "phase5h_strategy_outcome_memory": "CREATE TABLE IF NOT EXISTS phase5h_strategy_outcome_memory (memory_key TEXT PRIMARY KEY)",
    "phase5h_experiment_outcome_cycles": "CREATE TABLE IF NOT EXISTS phase5h_experiment_outcome_cycles (id INTEGER PRIMARY KEY AUTOINCREMENT)",
    "phase5h_experiment_learning_events": "CREATE TABLE IF NOT EXISTS phase5h_experiment_learning_events (id INTEGER PRIMARY KEY AUTOINCREMENT)",
    "phase5h_runtime_state": "CREATE TABLE IF NOT EXISTS phase5h_runtime_state (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)",
}

UNIQUE_INDEXES = [
    ("phase5g_experiment_outcomes", "outcome_key"),
    ("phase5g_strategy_selection_memory", "memory_key"),
    ("phase5h_strategy_outcome_memory", "memory_key"),
    ("phase5h_runtime_state", "key"),
    ("internal_learning_gaps", "gap_key"),
    ("reading_queue", "chunk_id"),
    ("chunk_attention_scores", "chunk_id"),
]

def _conn(mem_or_path=None):
    if isinstance(mem_or_path, sqlite3.Connection):
        return mem_or_path, False
    if mem_or_path is not None:
        for attr in ("conn", "con", "db", "connection"):
            c = getattr(mem_or_path, attr, None)
            if isinstance(c, sqlite3.Connection):
                return c, False
        p = getattr(mem_or_path, "path", None) or getattr(mem_or_path, "db_path", None)
        if p:
            return sqlite3.connect(str(p)), True
    return sqlite3.connect("ki_memory.sqlite3"), True

def _table_exists(cur, table):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _cols(cur, table):
    if not _table_exists(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}

def _add_col(cur, table, col, typ, changes):
    cols = _cols(cur, table)
    if col not in cols:
        if col == "id":
            return
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        changes.append(f"add_column:{table}.{col}")

def ensure_phase5h_schema(mem_or_path=None):
    db, close = _conn(mem_or_path)
    cur = db.cursor()
    changes=[]
    for table, sql in CREATE_SQL.items():
        if not _table_exists(cur, table):
            cur.execute(sql)
            changes.append(f"create_table:{table}")
    # Existing tables not created here stay optional; add columns only if table exists or create_sql created it.
    for table, cols in TABLE_COLUMNS.items():
        if not _table_exists(cur, table):
            # only create known standalone phase5 tables; don't create core tables blindly except optional support tables
            if table in CREATE_SQL:
                cur.execute(CREATE_SQL[table])
            else:
                continue
        for col, typ in cols.items():
            _add_col(cur, table, col, typ, changes)
    # Backfill experiment_key/outcome_key for existing experiments/outcomes
    if _table_exists(cur, "phase5g_strategy_experiments"):
        cols = _cols(cur, "phase5g_strategy_experiments")
        if "experiment_key" in cols:
            cur.execute("UPDATE phase5g_strategy_experiments SET experiment_key='exp:'||COALESCE(id,rowid) WHERE experiment_key IS NULL OR experiment_key='' ")
            if cur.rowcount:
                changes.append("backfill:phase5g_strategy_experiments.experiment_key")
    if _table_exists(cur, "phase5g_experiment_outcomes"):
        cols = _cols(cur, "phase5g_experiment_outcomes")
        if "outcome_key" in cols:
            cur.execute("UPDATE phase5g_experiment_outcomes SET outcome_key='out:'||COALESCE(experiment_key, id, rowid) WHERE outcome_key IS NULL OR outcome_key='' ")
            if cur.rowcount:
                changes.append("backfill:phase5g_experiment_outcomes.outcome_key")
    for table, col in UNIQUE_INDEXES:
        if _table_exists(cur, table) and col in _cols(cur, table):
            idx = f"idx_{table}_{col}_phase5h_fixed1_unique"
            try:
                cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
                changes.append(f"unique_index:{table}.{col}")
            except sqlite3.IntegrityError:
                changes.append(f"skip_unique_duplicates:{table}.{col}")
    now = int(time.time())
    if _table_exists(cur, "phase5h_runtime_state"):
        for k,v in {
            "phase": PHASE,
            "no_word_blacklists": "true",
            "fact_promotion": "disabled",
            "direct_fact_writes": "disabled",
            "direct_relation_writes": "disabled",
            "question_generation": "internal_learning_questions_only",
            "learning_mode": "context_hypotheses_with_neuromodulators",
        }.items():
            cur.execute("INSERT INTO phase5h_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k,v,now))
    db.commit()
    if close: db.close()
    return {"status":"ok", "phase":PHASE, "changes":changes, "no_word_blacklists":True, "fact_promotion":"disabled"}

def _count(cur, table):
    if not _table_exists(cur, table): return 0
    return cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

def _safety(cur):
    return {t:_count(cur,t) for t in ("facts","relations","questions")}

def evaluate_strategy_experiment_outcomes(mem_or_path=None, limit=1200):
    db, close = _conn(mem_or_path)
    ensure_phase5h_schema(db)
    cur = db.cursor()
    now = int(time.time())
    if not _table_exists(cur, "phase5g_strategy_experiments"):
        return {"status":"no_experiments_table", "phase":PHASE}
    cols = _cols(cur, "phase5g_strategy_experiments")
    # Make a robust select with ensured columns.
    rows = cur.execute(f"""
        SELECT rowid, COALESCE(experiment_key,'exp:'||rowid),
               COALESCE(gap_id,0), COALESCE(gap_key,''), COALESCE(gap_type,'unknown'), COALESCE(role,'unknown'),
               COALESCE(source_chunk_id,0), COALESCE(target_chunk_id,0),
               COALESCE(selected_strategy, window_strategy, 'unknown_strategy'), COALESCE(window_strategy, selected_strategy, 'unknown_strategy'),
               COALESCE(window_radius,0), COALESCE(read_status,''),
               COALESCE(closure_delta, phase5h_outcome_score, outcome_score, 0.0),
               COALESCE(no_candidate_rate, CASE WHEN read_status='read_no_candidate' THEN 1.0 ELSE 0.0 END),
               COALESCE(overlap_score, 0.5), COALESCE(strategy_score,0.0)
        FROM phase5g_strategy_experiments
        ORDER BY rowid DESC LIMIT ?
    """, (limit,)).fetchall()
    outcomes=0
    sums={}
    for r in rows:
        (rowid, exp_key, gap_id, gap_key, gap_type, role, src, tgt, selected, window, radius, read_status, closure, no_cand, overlap, strat_score) = r
        closure = float(closure or 0.0)
        no_cand = float(no_cand or 0.0)
        overlap = float(overlap if overlap is not None else 0.5)
        strat_score = float(strat_score or 0.0)
        outcome_score = max(0.0, min(1.0, 0.45*closure + 0.25*strat_score + 0.20*(1-no_cand) + 0.10*(1-min(1.0,overlap))))
        if outcome_score >= 0.55:
            label="effective_strategy"
            rec="reinforce_strategy"
        elif no_cand > 0.6:
            label="weak_no_candidate"
            rec="dampen_or_shift_strategy"
        elif overlap > 0.85:
            label="weak_high_overlap"
            rec="seek_lower_overlap_or_contrastive_context"
        else:
            label="observe_strategy"
            rec="observe_and_compare_strategy"
        outcome_key=f"out:{exp_key}"
        details=json.dumps({"source":"phase5h_fixed1", "safe":"no_facts_relations_questions"}, ensure_ascii=False)
        cur.execute("""
            INSERT INTO phase5g_experiment_outcomes(outcome_key,experiment_key,experiment_id,gap_id,gap_key,gap_type,role,source_chunk_id,target_chunk_id,selected_strategy,window_strategy,window_radius,read_status,closure_delta,no_candidate_rate,overlap_score,strategy_score,outcome_score,outcome_label,recommendation,details,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(outcome_key) DO UPDATE SET
              outcome_score=excluded.outcome_score, outcome_label=excluded.outcome_label, recommendation=excluded.recommendation,
              closure_delta=excluded.closure_delta, no_candidate_rate=excluded.no_candidate_rate, overlap_score=excluded.overlap_score,
              strategy_score=excluded.strategy_score, updated_at=excluded.updated_at
        """, (outcome_key, exp_key, int(rowid), int(gap_id or 0), gap_key, gap_type, role, int(src or 0), int(tgt or 0), selected, window, int(radius or 0), read_status, closure, no_cand, overlap, strat_score, outcome_score, label, rec, details, now, now))
        cur.execute("UPDATE phase5g_strategy_experiments SET phase5h_outcome_score=?, phase5h_outcome_label=?, phase5h_last_evaluated_at=?, phase5h_memory_key=?, phase5h_reason=? WHERE rowid=?", (outcome_score,label,now,f"{gap_type}:{role}:{selected}",rec,rowid))
        outcomes += 1
        key=(gap_type,role,selected)
        s=sums.setdefault(key, [0,0,0,0,0,0,0])
        s[0]+=1; s[1]+=outcome_score; s[2]+=closure; s[3]+=no_cand; s[4]+=overlap; s[5]+=strat_score; s[6]+=1 if outcome_score>=0.55 else 0
    memory_updates=0
    for (gap_type,role,strategy), s in sums.items():
        n=s[0]
        avg_out=s[1]/n; avg_cl=s[2]/n; avg_nc=s[3]/n; avg_ov=s[4]/n; avg_st=s[5]/n; succ=int(s[6]); fail=n-succ
        if avg_out>=0.55: rec="prefer_strategy_for_gap_role"
        elif avg_nc>0.5: rec="avoid_no_candidate_strategy"
        elif avg_ov>0.85: rec="reduce_overlap_before_reuse"
        else: rec="compare_with_alternative_strategy"
        mem_key=f"{gap_type}:{role}:{strategy}"
        profile=json.dumps({"learning_rate":0.234,"error_weight":0.407,"revision_pressure":0.312,"exploration_pressure":0.31,"inhibition_level":0.349}, ensure_ascii=False)
        cur.execute("""
            INSERT INTO phase5g_strategy_selection_memory(memory_key,gap_type,role,selected_strategy,observations,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,avg_strategy_score,avg_outcome_score,success_count,failure_count,recommendation,neuromodulator_profile,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(memory_key) DO UPDATE SET observations=phase5g_strategy_selection_memory.observations+excluded.observations,
              avg_closure_delta=excluded.avg_closure_delta, avg_no_candidate_rate=excluded.avg_no_candidate_rate,
              avg_overlap_score=excluded.avg_overlap_score, avg_strategy_score=excluded.avg_strategy_score,
              avg_outcome_score=excluded.avg_outcome_score, success_count=phase5g_strategy_selection_memory.success_count+excluded.success_count,
              failure_count=phase5g_strategy_selection_memory.failure_count+excluded.failure_count,
              recommendation=excluded.recommendation, neuromodulator_profile=excluded.neuromodulator_profile, updated_at=excluded.updated_at
        """, (mem_key,gap_type,role,strategy,n,avg_cl,avg_nc,avg_ov,avg_st,avg_out,succ,fail,rec,profile,now,now))
        cur.execute("""
            INSERT INTO phase5h_strategy_outcome_memory(memory_key,gap_type,role,selected_strategy,observations,avg_outcome_score,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,success_count,failure_count,recommendation,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(memory_key) DO UPDATE SET observations=phase5h_strategy_outcome_memory.observations+excluded.observations,
              avg_outcome_score=excluded.avg_outcome_score, avg_closure_delta=excluded.avg_closure_delta,
              avg_no_candidate_rate=excluded.avg_no_candidate_rate, avg_overlap_score=excluded.avg_overlap_score,
              success_count=phase5h_strategy_outcome_memory.success_count+excluded.success_count,
              failure_count=phase5h_strategy_outcome_memory.failure_count+excluded.failure_count,
              recommendation=excluded.recommendation, updated_at=excluded.updated_at
        """, (mem_key,gap_type,role,strategy,n,avg_out,avg_cl,avg_nc,avg_ov,succ,fail,rec,now,now))
        memory_updates += 1
    avg_outcome = (sum(v[1] for v in sums.values()) / max(1, sum(v[0] for v in sums.values()))) if sums else 0.0
    avg_closure = (sum(v[2] for v in sums.values()) / max(1, sum(v[0] for v in sums.values()))) if sums else 0.0
    avg_no_candidate = (sum(v[3] for v in sums.values()) / max(1, sum(v[0] for v in sums.values()))) if sums else 0.0
    avg_overlap = (sum(v[4] for v in sums.values()) / max(1, sum(v[0] for v in sums.values()))) if sums else 0.0
    safety=_safety(cur)
    cur.execute("INSERT INTO phase5h_experiment_outcome_cycles(phase,experiments_seen,outcomes_written,memory_updates,avg_outcome_score,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,facts,relations,questions,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (PHASE,len(rows),outcomes,memory_updates,avg_outcome,avg_closure,avg_no_candidate,avg_overlap,safety['facts'],safety['relations'],safety['questions'],now))
    for k,v in {"phase":PHASE,"last_outcomes_written":str(outcomes),"last_memory_updates":str(memory_updates),"last_avg_outcome_score":str(round(avg_outcome,6)),"no_word_blacklists":"true","fact_promotion":"disabled","direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_generation":"internal_learning_questions_only"}.items():
        cur.execute("INSERT INTO phase5h_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k,v,now))
    db.commit()
    if close: db.close()
    return {"status":"phase5h_strategy_outcome_learning_complete", "phase":PHASE, "experiments_seen":len(rows), "outcomes_written":outcomes, "memory_updates":memory_updates, "avg_outcome_score":round(avg_outcome,6), "avg_closure_delta":round(avg_closure,6), "avg_no_candidate_rate":round(avg_no_candidate,6), "avg_overlap_score":round(avg_overlap,6), "facts":safety['facts'], "relations":safety['relations'], "questions":safety['questions'], "no_word_blacklists":True, "fact_promotion":"disabled"}

def _base_module():
    try:
        from ki_system import v8_phase5h_strategy_experiment_outcome_learning_release as base
        return base
    except Exception:
        return None

def managed_cycle(self, progress=None):
    ensure_phase5h_schema(getattr(self,"mem",None) or getattr(self,"memory",None) or self)
    base=_base_module()
    if base and hasattr(base,"managed_cycle"):
        res=base.managed_cycle(self, progress)
    elif base and hasattr(base,"safe_cycle"):
        res=base.safe_cycle(self, progress)
    else:
        res={"status":"phase5h_base_missing", "phase":PHASE}
    try:
        evaluate_strategy_experiment_outcomes(getattr(self,"mem",None) or getattr(self,"memory",None) or self)
    except Exception as exc:
        res={"status":"phase5h_fixed1_outcome_error", "error":str(exc), "base_result":res}
    return res

def managed_run(self, cycles=1, progress=None):
    ensure_phase5h_schema(getattr(self,"mem",None) or getattr(self,"memory",None) or self)
    base=_base_module()
    if base and hasattr(base,"managed_run"):
        res=base.managed_run(self, cycles, progress)
    elif base and hasattr(base,"safe_run"):
        res=base.safe_run(self, cycles, progress)
    else:
        res=[]
        for _ in range(cycles or 1): res.append(managed_cycle(self, progress))
    try:
        summary=evaluate_strategy_experiment_outcomes(getattr(self,"mem",None) or getattr(self,"memory",None) or self)
        if isinstance(res, dict): res["phase5h_fixed1_outcome_learning"]=summary
        elif isinstance(res, list): res.append({"phase5h_fixed1_outcome_learning":summary})
    except Exception as exc:
        if isinstance(res, dict): res["phase5h_fixed1_error"]=str(exc)
        elif isinstance(res, list): res.append({"phase5h_fixed1_error":str(exc)})
    return res

def patch_autonomous_loop(*args, **kwargs):
    try:
        from ki_system.autonomous import AutonomousLoop
        AutonomousLoop.run = managed_run
        AutonomousLoop.cycle = managed_cycle
        for name,val in {
            "phase5h_schema_guard_fixed1": True,
            "phase5h_strategy_experiment_outcome_learning_release": True,
            "no_word_blacklists": True,
            "learning_mode": "context_hypotheses_with_neuromodulators",
            "fact_promotion": "disabled",
        }.items():
            setattr(AutonomousLoop, name, val); setattr(AutonomousLoop, "_"+name, val)
        return True
    except Exception:
        traceback.print_exc()
        return False

# best effort on import
try:
    patch_autonomous_loop()
except Exception:
    pass
