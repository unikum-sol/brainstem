
# V8-phase5h_strategy_experiment_outcome_learning_release
# Integrated strategy experiment outcome learning.
# Project compass: no word blacklists, no direct facts/relations/questions, no fact promotion.
from __future__ import annotations
import json, time, sqlite3, math
from typing import Any, Dict, List, Tuple, Optional

PHASE = "phase5h_strategy_experiment_outcome_learning_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _now() -> int:
    return int(time.time())


def _clamp(x: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return max(lo, min(hi, x))


def _j(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps(str(obj), ensure_ascii=False)


def _get_db(mem_or_conn: Any) -> sqlite3.Connection:
    """Return a sqlite3 connection from either Memory, AutonomousLoop, or direct connection."""
    if isinstance(mem_or_conn, sqlite3.Connection):
        return mem_or_conn
    # AutonomousLoop instance
    for attr in ("mem", "memory", "m", "store", "memory_store"):
        obj = getattr(mem_or_conn, attr, None)
        if obj is not None and obj is not mem_or_conn:
            try:
                return _get_db(obj)
            except Exception:
                pass
    # Memory-like object
    for attr in ("conn", "con", "db", "connection"):
        con = getattr(mem_or_conn, attr, None)
        if isinstance(con, sqlite3.Connection):
            return con
    # Some Memory classes expose path
    for attr in ("db_path", "path", "filename"):
        p = getattr(mem_or_conn, attr, None)
        if p:
            return sqlite3.connect(str(p))
    # Fallback current db
    return sqlite3.connect("ki_memory.sqlite3")


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(db: sqlite3.Connection, table: str) -> List[str]:
    if not _table_exists(db, table):
        return []
    return [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]


def _add_col(db: sqlite3.Connection, table: str, col: str, decl: str, changes: List[str]) -> None:
    if not _table_exists(db, table):
        return
    if col not in _cols(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        changes.append(f"add_column:{table}.{col}")


def _unique(db: sqlite3.Connection, table: str, col: str, changes: List[str]) -> None:
    if not _table_exists(db, table) or col not in _cols(db, table):
        return
    idx = f"idx_{table}_{col}_phase5h_unique"
    try:
        db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")
    except sqlite3.IntegrityError:
        # Duplicate historical rows: leave non-unique but don't crash.
        changes.append(f"skip_unique_duplicate:{table}.{col}")


def ensure_schema(mem_or_conn: Any = None) -> Dict[str, Any]:
    db = _get_db(mem_or_conn)
    cur = db.cursor()
    changes: List[str] = []
    # New / canonical Phase5h tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5h_experiment_outcome_cycles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase TEXT,
        experiments_seen INTEGER DEFAULT 0,
        outcomes_written INTEGER DEFAULT 0,
        memory_updates INTEGER DEFAULT 0,
        avg_outcome_score REAL DEFAULT 0,
        avg_closure_delta REAL DEFAULT 0,
        avg_no_candidate_rate REAL DEFAULT 0,
        avg_overlap_score REAL DEFAULT 0,
        recommendation TEXT,
        safety_ok INTEGER DEFAULT 1,
        no_word_blacklists TEXT DEFAULT 'true',
        fact_promotion TEXT DEFAULT 'disabled',
        created_at INTEGER
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5h_strategy_outcome_memory(
        memory_key TEXT PRIMARY KEY,
        selected_strategy TEXT,
        gap_type TEXT,
        role TEXT,
        observations INTEGER DEFAULT 0,
        avg_outcome_score REAL DEFAULT 0,
        avg_closure_delta REAL DEFAULT 0,
        avg_no_candidate_rate REAL DEFAULT 0,
        avg_overlap_score REAL DEFAULT 0,
        avg_strategy_score REAL DEFAULT 0,
        avg_learning_rate REAL DEFAULT 0,
        avg_error_weight REAL DEFAULT 0,
        avg_revision_pressure REAL DEFAULT 0,
        avg_exploration_pressure REAL DEFAULT 0,
        avg_inhibition_level REAL DEFAULT 0,
        avg_consolidation_gain REAL DEFAULT 0,
        recommendation TEXT,
        neuromodulator_profile TEXT,
        details TEXT,
        first_seen INTEGER,
        last_seen INTEGER,
        updated_at INTEGER
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5h_experiment_learning_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_key TEXT,
        outcome_key TEXT,
        selected_strategy TEXT,
        gap_type TEXT,
        role TEXT,
        target_chunk_id INTEGER,
        outcome_score REAL DEFAULT 0,
        closure_delta REAL DEFAULT 0,
        no_candidate_rate REAL DEFAULT 0,
        overlap_score REAL DEFAULT 0,
        strategy_score REAL DEFAULT 0,
        recommendation TEXT,
        event_type TEXT,
        details TEXT,
        created_at INTEGER
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5h_runtime_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER
    )""")
    # Ensure Phase5g outcome table exists even if previous release did not fill it.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5g_experiment_outcomes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_key TEXT,
        outcome_key TEXT,
        gap_id INTEGER,
        gap_key TEXT,
        gap_type TEXT,
        role TEXT,
        center_chunk_id INTEGER,
        target_chunk_id INTEGER,
        selected_strategy TEXT,
        window_strategy TEXT,
        window_radius INTEGER,
        read_status TEXT,
        before_score REAL DEFAULT 0,
        after_score REAL DEFAULT 0,
        closure_delta REAL DEFAULT 0,
        no_candidate_rate REAL DEFAULT 0,
        overlap_score REAL DEFAULT 0,
        strategy_score REAL DEFAULT 0,
        outcome_score REAL DEFAULT 0,
        outcome_label TEXT,
        recommendation TEXT,
        learning_rate REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        exploration_pressure REAL DEFAULT 0,
        inhibition_level REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        evidence_count INTEGER DEFAULT 1,
        details TEXT,
        created_at INTEGER,
        updated_at INTEGER
    )""")
    # Ensure Phase5g strategy memory exists and has future columns.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS phase5g_strategy_selection_memory(
        memory_key TEXT PRIMARY KEY,
        selected_strategy TEXT,
        gap_type TEXT,
        role TEXT,
        observations INTEGER DEFAULT 0,
        avg_outcome_score REAL DEFAULT 0,
        avg_closure_delta REAL DEFAULT 0,
        avg_no_candidate_rate REAL DEFAULT 0,
        avg_overlap_score REAL DEFAULT 0,
        avg_strategy_score REAL DEFAULT 0,
        recommendation TEXT,
        neuromodulator_profile TEXT,
        details TEXT,
        first_seen INTEGER,
        last_seen INTEGER,
        updated_at INTEGER
    )""")
    # Future-proof important tables.
    table_cols = {
        'phase5g_strategy_experiments': {
            'experiment_key':'TEXT','gap_id':'INTEGER','gap_key':'TEXT','gap_type':'TEXT','role':'TEXT',
            'center_chunk_id':'INTEGER','target_chunk_id':'INTEGER','selected_strategy':'TEXT','window_strategy':'TEXT',
            'window_radius':'INTEGER','read_status':'TEXT','strategy_score':'REAL DEFAULT 0','closure_delta':'REAL DEFAULT 0',
            'no_candidate_rate':'REAL DEFAULT 0','overlap_score':'REAL DEFAULT 0','outcome_score':'REAL DEFAULT 0',
            'phase5h_outcome_score':'REAL DEFAULT 0','phase5h_outcome_label':'TEXT','phase5h_last_evaluated_at':'INTEGER',
            'phase5h_memory_key':'TEXT','phase5h_reason':'TEXT','created_at':'INTEGER','updated_at':'INTEGER'
        },
        'phase5g_experiment_outcomes': {
            'outcome_key':'TEXT','target_chunk_id':'INTEGER','selected_strategy':'TEXT','gap_type':'TEXT','role':'TEXT',
            'closure_delta':'REAL DEFAULT 0','no_candidate_rate':'REAL DEFAULT 0','overlap_score':'REAL DEFAULT 0',
            'strategy_score':'REAL DEFAULT 0','outcome_score':'REAL DEFAULT 0','outcome_label':'TEXT','recommendation':'TEXT',
            'learning_rate':'REAL DEFAULT 0','error_weight':'REAL DEFAULT 0','revision_pressure':'REAL DEFAULT 0',
            'exploration_pressure':'REAL DEFAULT 0','inhibition_level':'REAL DEFAULT 0','consolidation_gain':'REAL DEFAULT 0',
            'details':'TEXT','created_at':'INTEGER','updated_at':'INTEGER'
        },
        'phase5g_strategy_selection_memory': {
            'avg_outcome_score':'REAL DEFAULT 0','avg_closure_delta':'REAL DEFAULT 0','avg_no_candidate_rate':'REAL DEFAULT 0',
            'avg_overlap_score':'REAL DEFAULT 0','avg_strategy_score':'REAL DEFAULT 0','recommendation':'TEXT',
            'neuromodulator_profile':'TEXT','first_seen':'INTEGER','last_seen':'INTEGER','updated_at':'INTEGER'
        },
        'internal_learning_gaps': {
            'phase5h_strategy_outcome_score':'REAL DEFAULT 0','phase5h_strategy_memory_key':'TEXT',
            'phase5h_last_outcome_at':'INTEGER','phase5h_recommendation':'TEXT','phase5h_reason':'TEXT'
        },
        'chunk_attention_scores': {
            'phase5h_strategy_outcome_score':'REAL DEFAULT 0','phase5h_strategy_memory_key':'TEXT',
            'phase5h_last_outcome_at':'INTEGER','phase5h_recommendation':'TEXT','phase5h_reason':'TEXT'
        },
        'reading_queue': {
            'phase5h_strategy_outcome_score':'REAL DEFAULT 0','phase5h_strategy_memory_key':'TEXT',
            'phase5h_last_outcome_at':'INTEGER','phase5h_recommendation':'TEXT','phase5h_reason':'TEXT'
        },
        'phase5g_neuromodulator_strategy_profiles': {
            'avg_outcome_score':'REAL DEFAULT 0','avg_closure_delta':'REAL DEFAULT 0','avg_no_candidate_rate':'REAL DEFAULT 0',
            'avg_overlap_score':'REAL DEFAULT 0','phase5h_last_updated_at':'INTEGER','phase5h_recommendation':'TEXT'
        }
    }
    for tbl, cols in table_cols.items():
        if _table_exists(db, tbl):
            for col, decl in cols.items():
                _add_col(db, tbl, col, decl, changes)
    for tbl, col in [
        ('phase5g_experiment_outcomes','outcome_key'),
        ('phase5g_strategy_selection_memory','memory_key'),
        ('phase5h_strategy_outcome_memory','memory_key'),
        ('phase5h_runtime_state','key'),
        ('internal_learning_gaps','gap_key'),
        ('reading_queue','chunk_id'),
        ('chunk_attention_scores','chunk_id'),
    ]:
        _unique(db, tbl, col, changes)
    # Safety state
    now = _now()
    for k, v in {
        'phase': PHASE,
        'learning_mode': LEARNING_MODE,
        'no_word_blacklists': 'true',
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'internal_learning_questions_only'
    }.items():
        db.execute("INSERT INTO phase5h_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, str(v), now))
    db.commit()
    return {'status':'ok','phase':PHASE,'changes':changes,'no_word_blacklists':True,'fact_promotion':'disabled'}


def _rowdict(cur: sqlite3.Cursor, row: Tuple[Any, ...]) -> Dict[str, Any]:
    return {d[0]: row[i] for i, d in enumerate(cur.description)}


def _first(d: Dict[str, Any], names: List[str], default: Any = None) -> Any:
    for n in names:
        if n in d and d[n] is not None:
            return d[n]
    return default


def _current_controls(db: sqlite3.Connection) -> Dict[str, float]:
    # Prefer active_learning_loop_state, fallback constants observed in previous phases.
    defaults = {
        'learning_rate':0.234, 'error_weight':0.407, 'revision_pressure':0.312,
        'exploration_pressure':0.31, 'inhibition_level':0.349, 'consolidation_gain':0.297,
        'dopamine':0.5, 'serotonin':0.4, 'glutamate':0.31, 'gaba':0.349, 'noradrenaline':0.407, 'acetylcholine':0.312
    }
    for table in ('active_learning_loop_state','progress_evaluation_state','phase5a_integrated_runtime_state'):
        if _table_exists(db, table):
            try:
                rows = db.execute(f"SELECT key,value FROM {table}").fetchall()
                kv = {str(k): str(v).strip("'\"") for k,v in rows}
                for key in list(defaults):
                    lk = 'last_' + key
                    if lk in kv:
                        defaults[key] = _clamp(kv[lk], 0, 10)
                    elif key in kv:
                        defaults[key] = _clamp(kv[key], 0, 10)
            except Exception:
                pass
    return defaults


def _read_status(db: sqlite3.Connection, chunk_id: Optional[int]) -> str:
    if chunk_id is None or not _table_exists(db, 'reading_queue'):
        return 'unknown'
    cols = _cols(db, 'reading_queue')
    if 'status' not in cols or 'chunk_id' not in cols:
        return 'unknown'
    r = db.execute("SELECT status FROM reading_queue WHERE chunk_id=?", (chunk_id,)).fetchone()
    return str(r[0]) if r and r[0] is not None else 'unknown'


def _fetch_recent_experiments(db: sqlite3.Connection, limit: int = 1200) -> List[Dict[str, Any]]:
    if not _table_exists(db, 'phase5g_strategy_experiments'):
        return []
    cols = _cols(db, 'phase5g_strategy_experiments')
    order = 'id' if 'id' in cols else 'rowid'
    cur = db.execute(f"SELECT rowid,* FROM phase5g_strategy_experiments ORDER BY {order} DESC LIMIT ?", (limit,))
    return [_rowdict(cur, row) for row in cur.fetchall()]


def _memory_recommendation(avg_outcome: float, avg_closure: float, no_cand: float, overlap: float) -> str:
    if avg_outcome >= 0.62 and avg_closure >= 0.08:
        return 'reinforce_strategy_for_gap_type'
    if no_cand >= 0.35:
        return 'reduce_or_shift_strategy_due_to_no_candidate'
    if overlap >= 0.85 and avg_closure < 0.06:
        return 'increase_contrast_and_reduce_overlap'
    if avg_closure < 0.03:
        return 'explore_alternative_context_strategy'
    return 'observe_and_refine_strategy'


def evaluate_strategy_experiment_outcomes(mem_or_conn: Any = None, limit: int = 1200) -> Dict[str, Any]:
    db = _get_db(mem_or_conn)
    ensure_schema(db)
    now = _now()
    controls = _current_controls(db)
    experiments = _fetch_recent_experiments(db, limit=limit)
    outcomes_written = 0
    events_written = 0
    outcome_scores: List[float] = []
    closure_scores: List[float] = []
    no_cand_scores: List[float] = []
    overlap_scores: List[float] = []

    for e in experiments:
        rowid = _first(e, ['rowid','id'], 0)
        gap_id = _first(e, ['gap_id','internal_gap_id'], None)
        gap_key = _first(e, ['gap_key'], None)
        gap_type = str(_first(e, ['gap_type','source_gap_type'], 'unknown'))
        role = str(_first(e, ['role','target_role'], 'unknown'))
        selected_strategy = str(_first(e, ['selected_strategy','window_strategy','phase5g_selected_strategy'], 'unknown_strategy'))
        center_chunk = _first(e, ['center_chunk_id','center_chunk','source_chunk_id','chunk_id'], None)
        target_chunk = _first(e, ['target_chunk_id','target_chunk','chunk_id'], center_chunk)
        try:
            center_chunk = int(center_chunk) if center_chunk is not None else None
        except Exception:
            center_chunk = None
        try:
            target_chunk = int(target_chunk) if target_chunk is not None else None
        except Exception:
            target_chunk = None
        radius = _first(e, ['window_radius','phase5f_window_radius','radius'], 0)
        try:
            radius = int(radius or 0)
        except Exception:
            radius = 0
        read_status = str(_first(e, ['read_status','target_read_status'], None) or _read_status(db, target_chunk))
        explicit_no = _first(e, ['no_candidate_rate','phase5g_no_candidate_rate','phase5f_no_candidate_rate'], None)
        if explicit_no is None:
            no_candidate_rate = 1.0 if read_status == 'read_no_candidate' else 0.0
        else:
            no_candidate_rate = _clamp(explicit_no)
            if read_status == 'read_no_candidate':
                no_candidate_rate = max(no_candidate_rate, 1.0)
        closure_delta = _clamp(_first(e, ['closure_delta','phase5g_closure_delta','phase5f_closure_delta'], 0.0), -1, 1)
        overlap_score = _clamp(_first(e, ['overlap_score','phase5g_overlap_score','phase5f_overlap_score'], 0.5))
        strategy_score = _clamp(_first(e, ['strategy_score','phase5g_strategy_score','phase5f_score','score'], 0.5))
        # If previous systems produced closure_delta=0, infer weak proxy from strategy_score/no-candidate/overlap.
        outcome_score = _clamp(0.45*max(closure_delta,0) + 0.25*(1-no_candidate_rate) + 0.20*(1-overlap_score) + 0.10*strategy_score)
        if closure_delta > 0.09 and no_candidate_rate < 0.35:
            outcome_label = 'useful_strategy_signal'
        elif no_candidate_rate >= 0.75:
            outcome_label = 'no_candidate_strategy_penalty'
        elif overlap_score >= 0.9 and closure_delta < 0.04:
            outcome_label = 'high_overlap_low_gain'
        elif outcome_score >= 0.5:
            outcome_label = 'promising_strategy_observe'
        else:
            outcome_label = 'weak_strategy_signal'
        recommendation = _memory_recommendation(outcome_score, max(closure_delta,0), no_candidate_rate, overlap_score)
        exp_key = str(_first(e, ['experiment_key'], f'exp:{rowid}:{selected_strategy}:{target_chunk}'))
        outcome_key = f'{exp_key}:outcome'
        details = {'source':'phase5h','read_status':read_status,'rowid':rowid,'controls':controls}
        db.execute("""
            INSERT INTO phase5g_experiment_outcomes(
                experiment_key,outcome_key,gap_id,gap_key,gap_type,role,center_chunk_id,target_chunk_id,
                selected_strategy,window_strategy,window_radius,read_status,closure_delta,no_candidate_rate,
                overlap_score,strategy_score,outcome_score,outcome_label,recommendation,
                learning_rate,error_weight,revision_pressure,exploration_pressure,inhibition_level,consolidation_gain,
                dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,evidence_count,details,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(outcome_key) DO UPDATE SET
                read_status=excluded.read_status, closure_delta=excluded.closure_delta,
                no_candidate_rate=excluded.no_candidate_rate, overlap_score=excluded.overlap_score,
                strategy_score=excluded.strategy_score, outcome_score=excluded.outcome_score,
                outcome_label=excluded.outcome_label, recommendation=excluded.recommendation,
                details=excluded.details, updated_at=excluded.updated_at
        """, (
            exp_key,outcome_key,gap_id,gap_key,gap_type,role,center_chunk,target_chunk,selected_strategy,selected_strategy,radius,read_status,
            closure_delta,no_candidate_rate,overlap_score,strategy_score,outcome_score,outcome_label,recommendation,
            controls['learning_rate'],controls['error_weight'],controls['revision_pressure'],controls['exploration_pressure'],controls['inhibition_level'],controls['consolidation_gain'],
            controls['dopamine'],controls['serotonin'],controls['glutamate'],controls['gaba'],controls['noradrenaline'],controls['acetylcholine'],1,_j(details),now,now
        ))
        outcomes_written += 1
        outcome_scores.append(outcome_score); closure_scores.append(max(closure_delta,0)); no_cand_scores.append(no_candidate_rate); overlap_scores.append(overlap_score)
        try:
            if _table_exists(db, 'phase5g_strategy_experiments'):
                db.execute("UPDATE phase5g_strategy_experiments SET phase5h_outcome_score=?, phase5h_outcome_label=?, phase5h_last_evaluated_at=?, phase5h_memory_key=?, phase5h_reason=? WHERE rowid=?", (outcome_score, outcome_label, now, f'{selected_strategy}:{gap_type}:{role}', recommendation, rowid))
        except Exception:
            pass
        db.execute("INSERT INTO phase5h_experiment_learning_events(experiment_key,outcome_key,selected_strategy,gap_type,role,target_chunk_id,outcome_score,closure_delta,no_candidate_rate,overlap_score,strategy_score,recommendation,event_type,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (exp_key,outcome_key,selected_strategy,gap_type,role,target_chunk,outcome_score,closure_delta,no_candidate_rate,overlap_score,strategy_score,recommendation,'experiment_outcome_evaluated',_j(details),now))
        events_written += 1

    # Aggregate outcomes into strategy memory.
    memory_updates = 0
    if outcomes_written:
        rows = db.execute("""
            SELECT selected_strategy,gap_type,role,COUNT(*) n,
                   AVG(outcome_score),AVG(closure_delta),AVG(no_candidate_rate),AVG(overlap_score),AVG(strategy_score),
                   AVG(learning_rate),AVG(error_weight),AVG(revision_pressure),AVG(exploration_pressure),AVG(inhibition_level),AVG(consolidation_gain)
            FROM phase5g_experiment_outcomes
            GROUP BY selected_strategy,gap_type,role
        """).fetchall()
        for (strategy,gap_type,role,n,avg_out,avg_cl,avg_no,avg_ov,avg_str,lr,ew,rp,ep,inh,cg) in rows:
            strategy = strategy or 'unknown_strategy'; gap_type = gap_type or 'unknown_gap'; role = role or 'unknown_role'
            key = f'{strategy}:{gap_type}:{role}'
            rec = _memory_recommendation(_clamp(avg_out), _clamp(avg_cl), _clamp(avg_no), _clamp(avg_ov))
            profile = {'learning_rate':lr,'error_weight':ew,'revision_pressure':rp,'exploration_pressure':ep,'inhibition_level':inh,'consolidation_gain':cg}
            for table in ('phase5h_strategy_outcome_memory','phase5g_strategy_selection_memory'):
                db.execute(f"""
                    INSERT INTO {table}(memory_key,selected_strategy,gap_type,role,observations,avg_outcome_score,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,avg_strategy_score,recommendation,neuromodulator_profile,details,first_seen,last_seen,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(memory_key) DO UPDATE SET
                        observations=excluded.observations,
                        avg_outcome_score=excluded.avg_outcome_score,
                        avg_closure_delta=excluded.avg_closure_delta,
                        avg_no_candidate_rate=excluded.avg_no_candidate_rate,
                        avg_overlap_score=excluded.avg_overlap_score,
                        avg_strategy_score=excluded.avg_strategy_score,
                        recommendation=excluded.recommendation,
                        neuromodulator_profile=excluded.neuromodulator_profile,
                        details=excluded.details,
                        last_seen=excluded.last_seen,
                        updated_at=excluded.updated_at
                """, (key,strategy,gap_type,role,int(n or 0),_clamp(avg_out),_clamp(avg_cl),_clamp(avg_no),_clamp(avg_ov),_clamp(avg_str),rec,_j(profile),_j({'phase':PHASE}),now,now,now))
            memory_updates += 1
            # Backpropagate to matching gaps/chunks for future selection.
            if _table_exists(db, 'internal_learning_gaps'):
                try:
                    db.execute("UPDATE internal_learning_gaps SET phase5h_strategy_outcome_score=?, phase5h_strategy_memory_key=?, phase5h_last_outcome_at=?, phase5h_recommendation=?, phase5h_reason=? WHERE COALESCE(gap_type,'unknown_gap')=? AND COALESCE(role,'unknown_role')=?", (_clamp(avg_out), key, now, rec, PHASE, gap_type, role))
                except Exception:
                    pass
            if _table_exists(db, 'chunk_attention_scores'):
                try:
                    db.execute("UPDATE chunk_attention_scores SET phase5h_strategy_outcome_score=?, phase5h_strategy_memory_key=?, phase5h_last_outcome_at=?, phase5h_recommendation=?, phase5h_reason=? WHERE COALESCE(phase5g_selected_strategy,phase5f_window_strategy,'')=?", (_clamp(avg_out), key, now, rec, PHASE, strategy))
                except Exception:
                    pass
            # Update neuromodulator strategy profiles if available
            if _table_exists(db, 'phase5g_neuromodulator_strategy_profiles'):
                try:
                    db.execute("UPDATE phase5g_neuromodulator_strategy_profiles SET avg_outcome_score=?, avg_closure_delta=?, avg_no_candidate_rate=?, avg_overlap_score=?, phase5h_last_updated_at=?, phase5h_recommendation=? WHERE COALESCE(selected_strategy, strategy, '')=? AND COALESCE(gap_type,'unknown_gap')=? AND COALESCE(role,'unknown_role')=?", (_clamp(avg_out), _clamp(avg_cl), _clamp(avg_no), _clamp(avg_ov), now, rec, strategy, gap_type, role))
                except Exception:
                    pass
    avg_out = sum(outcome_scores)/len(outcome_scores) if outcome_scores else 0.0
    avg_cl = sum(closure_scores)/len(closure_scores) if closure_scores else 0.0
    avg_no = sum(no_cand_scores)/len(no_cand_scores) if no_cand_scores else 0.0
    avg_ov = sum(overlap_scores)/len(overlap_scores) if overlap_scores else 0.0
    recommendation = _memory_recommendation(avg_out, avg_cl, avg_no, avg_ov)
    db.execute("INSERT INTO phase5h_experiment_outcome_cycles(phase,experiments_seen,outcomes_written,memory_updates,avg_outcome_score,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,recommendation,safety_ok,no_word_blacklists,fact_promotion,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (PHASE,len(experiments),outcomes_written,memory_updates,avg_out,avg_cl,avg_no,avg_ov,recommendation,1,'true','disabled',now))
    state = {
        'phase':PHASE,'learning_mode':LEARNING_MODE,'no_word_blacklists':'true','fact_promotion':'disabled',
        'direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only',
        'last_experiments_seen':str(len(experiments)),'last_outcomes_written':str(outcomes_written),'last_memory_updates':str(memory_updates),
        'last_avg_outcome_score':str(round(avg_out,6)),'last_avg_closure_delta':str(round(avg_cl,6)),
        'last_avg_no_candidate_rate':str(round(avg_no,6)),'last_avg_overlap_score':str(round(avg_ov,6)),'last_recommendation':recommendation
    }
    for k,v in state.items():
        db.execute("INSERT INTO phase5h_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k,v,now))
    db.commit()
    return {'status':'phase5h_strategy_experiment_outcome_learning_complete','phase':PHASE,'experiments_seen':len(experiments),'outcomes_written':outcomes_written,'memory_updates':memory_updates,'avg_outcome_score':round(avg_out,6),'avg_closure_delta':round(avg_cl,6),'avg_no_candidate_rate':round(avg_no,6),'avg_overlap_score':round(avg_ov,6),'recommendation':recommendation,'facts':_count(db,'facts'),'relations':_count(db,'relations'),'questions':_count(db,'questions'),'no_word_blacklists':True,'fact_promotion':'disabled'}


def _count(db: sqlite3.Connection, table: str) -> int:
    if not _table_exists(db, table): return 0
    try: return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception: return 0


def managed_cycle(self, progress=None):
    # Call previous Phase5g runtime if available, then outcome learning.
    result = None
    try:
        from ki_system import v8_phase5g_context_strategy_selection_and_experiment_memory_release as phase5g
        if hasattr(phase5g, 'managed_cycle'):
            result = phase5g.managed_cycle(self, progress)
    except Exception as exc:
        result = {'phase5g_cycle_error': str(exc)}
    db = _get_db(self)
    outcome = evaluate_strategy_experiment_outcomes(db)
    return {'phase': PHASE, 'base_result': result, 'outcome_learning': outcome, 'facts': outcome.get('facts',0), 'relations': outcome.get('relations',0), 'questions': outcome.get('questions',0)}


def managed_run(self, cycles=1, progress=None):
    out = []
    try:
        cycles = int(cycles)
    except Exception:
        cycles = 1
    for i in range(max(1, cycles)):
        if progress:
            try: progress(i+1, cycles)
            except Exception: pass
        out.append(managed_cycle(self, progress))
    return {'phase': PHASE, 'cycles': len(out), 'results': out, 'no_word_blacklists': True, 'fact_promotion': 'disabled'}


def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AL
        AutonomousLoop = AL
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    # public and private markers for older tests
    for name in ('phase5h_strategy_experiment_outcome_learning_release','_phase5h_strategy_experiment_outcome_learning_release'):
        setattr(AutonomousLoop, name, True)
    for name in ('no_word_blacklists','_no_word_blacklists'):
        setattr(AutonomousLoop, name, True)
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop._learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = 'disabled'
    AutonomousLoop._fact_promotion = 'disabled'
    return AutonomousLoop

# Patch on import when possible.
try:
    patch_autonomous_loop()
except Exception:
    pass
