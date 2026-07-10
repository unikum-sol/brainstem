
"""V8-phase4m Active Learning Loop Controller

Purpose:
- Coordinate Phase4g/h/i/j/k signals into one active learning control loop.
- No word blacklists, no facts/relations/questions writes, no fact promotion.
- Digital neuromodulators steer the whole learning process: learning rate,
  error weighting, revision pressure, uncertainty/confidence adaptation,
  exploration, inhibition, stabilization, consolidation and reading strategy.
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

PHASE = "phase4m_active_learning_loop_controller"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _now():
    return int(time.time())


def _get_db_from_memory(mem_or_loop):
    """Return sqlite3 connection from Memory-like object or AutonomousLoop.

    The project evolved over many patches, therefore this helper is intentionally
    tolerant. It never creates facts/relations/questions.
    """
    obj = mem_or_loop
    # If an AutonomousLoop is passed, try common memory attributes first.
    for attr in ("mem", "memory", "m", "store", "memory_store"):
        if hasattr(obj, attr):
            candidate = getattr(obj, attr)
            if candidate is not None:
                obj = candidate
                break
    if isinstance(obj, sqlite3.Connection):
        return obj
    for attr in ("con", "conn", "connection", "db"):
        if hasattr(obj, attr):
            con = getattr(obj, attr)
            if isinstance(con, sqlite3.Connection):
                return con
    # Try method forms.
    for meth in ("get_connection", "connect", "connection"):
        fn = getattr(obj, meth, None)
        if callable(fn):
            con = fn()
            if isinstance(con, sqlite3.Connection):
                return con
    # Fallback to default database path in project root/current working dir.
    return sqlite3.connect("ki_memory.sqlite3")


def _table_exists(db, table):
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(db, table):
    if not _table_exists(db, table): return []
    return [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]


def _ensure_table(db, ddl):
    db.execute(ddl)


def _ensure_col(db, table, col, spec, changes):
    if table not in _known_tables(db):
        return
    cols = _columns(db, table)
    if col not in cols:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {spec}")
        changes.append(f"add_column:{table}.{col}")


def _known_tables(db):
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _ensure_unique_index(db, table, col, changes):
    if not _table_exists(db, table) or col not in _columns(db, table):
        return
    # Avoid index creation if duplicates exist. Duplicates should not block runtime.
    dup = db.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
    if dup:
        changes.append(f"skip_unique_duplicates:{table}.{col}")
        return
    name = f"idx_{table}_{col}_phase4m_unique"
    db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table}({col})")
    changes.append(f"unique_index:{table}.{col}")


def ensure_phase4m_schema(mem_or_db):
    db = _get_db_from_memory(mem_or_db)
    changes = []

    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS active_learning_loop_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS active_learning_decisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_type TEXT,
        source_signal TEXT,
        affected_count INTEGER DEFAULT 0,
        learning_rate REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        exploration_pressure REAL DEFAULT 0,
        inhibition_level REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS learning_control_cycles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase TEXT,
        hypotheses INTEGER DEFAULT 0,
        gaps INTEGER DEFAULT 0,
        reread_actions INTEGER DEFAULT 0,
        chunk_scores INTEGER DEFAULT 0,
        learning_rate REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        exploration_pressure REAL DEFAULT 0,
        inhibition_level REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0,
        no_word_blacklists INTEGER DEFAULT 1,
        fact_promotion TEXT DEFAULT 'disabled',
        created_at INTEGER DEFAULT 0
    )""")
    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS neuromodulator_control_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        learning_rate REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        exploration_pressure REAL DEFAULT 0,
        inhibition_level REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0
    )""")

    # Ensure state tables that the controller may update.
    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS reading_strategy_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS attention_queue_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS learning_strategy_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    _ensure_table(db, """
    CREATE TABLE IF NOT EXISTS rollback_safe_core_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")

    # Additional tolerant columns for existing tables.
    for table, cols in {
        'context_hypotheses': {
            'active_learning_score': 'REAL DEFAULT 0',
            'last_active_learning_at': 'INTEGER DEFAULT 0',
            'active_learning_reason': 'TEXT'
        },
        'internal_learning_gaps': {
            'active_learning_priority': 'REAL DEFAULT 0',
            'last_selected_at': 'INTEGER DEFAULT 0',
            'selection_count': 'INTEGER DEFAULT 0'
        },
        'reading_queue': {
            'active_learning_priority': 'REAL DEFAULT 0',
            'cooldown_until': 'INTEGER DEFAULT 0'
        },
        'chunk_attention_scores': {
            'active_learning_score': 'REAL DEFAULT 0',
            'strategy_reason': 'TEXT'
        }
    }.items():
        if _table_exists(db, table):
            for col, spec in cols.items():
                _ensure_col(db, table, col, spec, changes)

    for table, col in [
        ('active_learning_loop_state','key'),
        ('reading_strategy_state','key'),
        ('attention_queue_state','key'),
        ('learning_strategy_state','key'),
        ('rollback_safe_core_state','key'),
        ('reading_queue','chunk_id'),
        ('chunk_attention_scores','chunk_id')
    ]:
        _ensure_unique_index(db, table, col, changes)

    # Safety state.
    now = _now()
    for key, val in {
        'phase': PHASE,
        'no_word_blacklists': 'true',
        'learning_mode': LEARNING_MODE,
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'internal_learning_questions_only'
    }.items():
        db.execute("INSERT INTO active_learning_loop_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, val, now))
        db.execute("INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, repr(val), now))
    db.commit()
    return {'status':'ok','phase':PHASE,'changes':changes}


def _safe_count(db, table):
    if not _table_exists(db, table): return 0
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _latest_learning_controls(db):
    # Use the most recent Phase4g state when available.
    row = None
    if _table_exists(db, 'neuromodulator_learning_state'):
        cols = _columns(db, 'neuromodulator_learning_state')
        needed = ['learning_rate','error_weight','revision_pressure','consolidation_gain','exploration_pressure','inhibition_level']
        if all(c in cols for c in needed):
            row = db.execute("SELECT learning_rate,error_weight,revision_pressure,consolidation_gain,exploration_pressure,inhibition_level FROM neuromodulator_learning_state ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        lr, ew, rp, cg, ep, il = [float(x or 0) for x in row]
    else:
        lr, ew, rp, cg, ep, il = 0.20, 0.35, 0.30, 0.25, 0.30, 0.30
    # Neuromodulators are control signals, not decorative values.
    dopamine = max(0.0, min(1.0, 0.45 + lr * 0.5 + cg * 0.2))
    serotonin = max(0.0, min(1.0, 0.35 + cg * 0.4))
    glutamate = max(0.0, min(1.0, 0.35 + ep * 0.5))
    gaba = max(0.0, min(1.0, 0.25 + il * 0.6))
    noradrenaline = max(0.0, min(1.0, 0.30 + ew * 0.45 + rp * 0.25))
    acetylcholine = max(0.0, min(1.0, 0.35 + rp * 0.25 + lr * 0.2))
    return {
        'learning_rate': lr, 'error_weight': ew, 'revision_pressure': rp,
        'consolidation_gain': cg, 'exploration_pressure': ep, 'inhibition_level': il,
        'dopamine': dopamine, 'serotonin': serotonin, 'glutamate': glutamate,
        'gaba': gaba, 'noradrenaline': noradrenaline, 'acetylcholine': acetylcholine
    }


def active_learning_controller(mem_or_db, limit_hypotheses=300, limit_gaps=80):
    db = _get_db_from_memory(mem_or_db)
    ensure_phase4m_schema(db)
    now = _now()
    ctrl = _latest_learning_controls(db)

    hypotheses = _safe_count(db, 'context_hypotheses')
    gaps = _safe_count(db, 'internal_learning_gaps')
    reread_actions = _safe_count(db, 'gap_driven_rereading_actions')
    chunk_scores = _safe_count(db, 'chunk_attention_scores')

    updated_h = 0
    selected_gaps = 0
    updated_chunks = 0

    # 1) Update hypothesis active-learning score from confidence/uncertainty/self_score/revision_pressure.
    if _table_exists(db, 'context_hypotheses'):
        cols = _columns(db, 'context_hypotheses')
        if all(c in cols for c in ['id','confidence','uncertainty','role','active_learning_score','last_active_learning_at','active_learning_reason']):
            rows = db.execute("SELECT id, role, COALESCE(confidence,0), COALESCE(uncertainty,0), COALESCE(revision_pressure,0), COALESCE(self_score,0) FROM context_hypotheses ORDER BY updated_at DESC, id DESC LIMIT ?", (limit_hypotheses,)).fetchall()
            for hid, role, conf, unc, revp, self_score in rows:
                # Error and uncertainty increase learning priority; GABA prevents runaway.
                priority = (unc * ctrl['error_weight']) + (revp * ctrl['revision_pressure']) + (ctrl['exploration_pressure'] * 0.2) - (ctrl['inhibition_level'] * 0.12)
                # Stabilized confidence reduces urgency a little, not to block learning.
                priority += max(0.0, 0.55 - conf) * 0.12
                priority = max(0.0, min(1.0, priority))
                db.execute("UPDATE context_hypotheses SET active_learning_score=?, last_active_learning_at=?, active_learning_reason=? WHERE id=?", (round(priority,4), now, PHASE, hid))
                updated_h += 1

    # 2) Select learning gaps and mark them as active learning drivers.
    if _table_exists(db, 'internal_learning_gaps'):
        cols = _columns(db, 'internal_learning_gaps')
        if 'active_learning_priority' in cols and 'selection_count' in cols and 'last_selected_at' in cols:
            base_cols = _columns(db, 'internal_learning_gaps')
            order_col = 'priority' if 'priority' in base_cols else ('severity' if 'severity' in base_cols else None)
            if order_col:
                rows = db.execute(f"SELECT id, gap_type, role, COALESCE({order_col},0) FROM internal_learning_gaps WHERE COALESCE(status,'open') LIKE 'open%' OR status IS NULL ORDER BY {order_col} DESC, id DESC LIMIT ?", (limit_gaps,)).fetchall()
            else:
                rows = db.execute("SELECT id, gap_type, role, 0.5 FROM internal_learning_gaps ORDER BY id DESC LIMIT ?", (limit_gaps,)).fetchall()
            for gid, gtype, role, sev in rows:
                pr = max(0.0, min(1.0, float(sev or 0) * 0.55 + ctrl['error_weight'] * 0.25 + ctrl['exploration_pressure'] * 0.20 - ctrl['inhibition_level'] * 0.10))
                db.execute("UPDATE internal_learning_gaps SET active_learning_priority=?, last_selected_at=?, selection_count=COALESCE(selection_count,0)+1 WHERE id=?", (round(pr,4), now, gid))
                selected_gaps += 1

    # 3) Ensure queue state reflects active learning balance without blacklists.
    if _table_exists(db, 'chunk_attention_scores') and _table_exists(db, 'reading_queue'):
        qcols = _columns(db, 'reading_queue')
        ccols = _columns(db, 'chunk_attention_scores')
        if all(c in qcols for c in ['chunk_id','priority','attention_score','reason']) and all(c in ccols for c in ['chunk_id','attention_score','active_learning_score','strategy_reason']):
            rows = db.execute("SELECT chunk_id, COALESCE(attention_score,0), COALESCE(uncertainty_score,0), COALESCE(reward_score,0), COALESCE(fatigue_score,0) FROM chunk_attention_scores ORDER BY attention_score DESC LIMIT 500").fetchall()
            for cid, attention, uncertainty, reward, fatigue in rows:
                score = attention * 0.45 + uncertainty * ctrl['error_weight'] * 0.25 + reward * ctrl['learning_rate'] * 0.2 + ctrl['exploration_pressure'] * 0.12 - fatigue * ctrl['inhibition_level'] * 0.15
                score = max(0.0, min(1.0, score))
                db.execute("UPDATE chunk_attention_scores SET active_learning_score=?, strategy_reason=? WHERE chunk_id=?", (round(score,4), PHASE, cid))
                db.execute("UPDATE reading_queue SET priority=MAX(COALESCE(priority,0), ?), attention_score=MAX(COALESCE(attention_score,0), ?), reason=? WHERE chunk_id=?", (round(score,4), round(score,4), PHASE, cid))
                updated_chunks += 1

    # 4) Record high-level decisions, not user-facing questions.
    details = {
        'hypotheses': hypotheses,
        'gaps': gaps,
        'reread_actions': reread_actions,
        'chunk_scores': chunk_scores,
        'updated_hypotheses': updated_h,
        'selected_gaps': selected_gaps,
        'updated_chunks': updated_chunks,
        'no_word_blacklists': True,
        'fact_promotion': 'disabled'
    }
    db.execute("""
        INSERT INTO learning_control_cycles(
            phase,hypotheses,gaps,reread_actions,chunk_scores,learning_rate,error_weight,
            revision_pressure,exploration_pressure,inhibition_level,consolidation_gain,
            no_word_blacklists,fact_promotion,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (PHASE, hypotheses, gaps, reread_actions, chunk_scores, ctrl['learning_rate'], ctrl['error_weight'], ctrl['revision_pressure'], ctrl['exploration_pressure'], ctrl['inhibition_level'], ctrl['consolidation_gain'], 1, 'disabled', now))
    db.execute("""
        INSERT INTO neuromodulator_control_history(
            dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,
            learning_rate,error_weight,revision_pressure,exploration_pressure,inhibition_level,consolidation_gain,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ctrl['dopamine'], ctrl['serotonin'], ctrl['glutamate'], ctrl['gaba'], ctrl['noradrenaline'], ctrl['acetylcholine'], ctrl['learning_rate'], ctrl['error_weight'], ctrl['revision_pressure'], ctrl['exploration_pressure'], ctrl['inhibition_level'], ctrl['consolidation_gain'], now))
    for dtype, source, count in [
        ('hypothesis_learning_control','context_hypotheses', updated_h),
        ('gap_learning_control','internal_learning_gaps', selected_gaps),
        ('chunk_strategy_control','chunk_attention_scores', updated_chunks)
    ]:
        db.execute("INSERT INTO active_learning_decisions(decision_type,source_signal,affected_count,learning_rate,error_weight,revision_pressure,exploration_pressure,inhibition_level,consolidation_gain,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (dtype, source, count, ctrl['learning_rate'], ctrl['error_weight'], ctrl['revision_pressure'], ctrl['exploration_pressure'], ctrl['inhibition_level'], ctrl['consolidation_gain'], _json(details), now))

    # 5) State mirrors for status tools and future strategy.
    state = {
        'phase': PHASE,
        'learning_mode': LEARNING_MODE,
        'no_word_blacklists': 'true',
        'fact_promotion': 'disabled',
        'question_generation': 'internal_learning_questions_only',
        'last_updated_hypotheses': str(updated_h),
        'last_selected_gaps': str(selected_gaps),
        'last_updated_chunks': str(updated_chunks),
        'last_learning_rate': str(ctrl['learning_rate']),
        'last_error_weight': str(ctrl['error_weight']),
        'last_revision_pressure': str(ctrl['revision_pressure']),
        'last_exploration_pressure': str(ctrl['exploration_pressure']),
        'last_inhibition_level': str(ctrl['inhibition_level']),
        'last_consolidation_gain': str(ctrl['consolidation_gain']),
    }
    for table in ('active_learning_loop_state','reading_strategy_state','attention_queue_state','learning_strategy_state'):
        if _table_exists(db, table):
            for key, val in state.items():
                db.execute(f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, val, now))
    db.commit()
    return {'status':'phase4m_active_learning_control_complete', 'phase':PHASE, **details, **{k:ctrl[k] for k in ['learning_rate','error_weight','revision_pressure','exploration_pressure','inhibition_level','consolidation_gain']}}


# Runtime wrapping
_BASE_RUN = None
_BASE_CYCLE = None


def _load_base():
    """Prefer Phase4l as base, fall back through previous runtime layers."""
    for modname in [
        'ki_system.v8_phase4l_gap_cluster_planning_and_strategy_balance',
        'ki_system.v8_phase4k_gap_driven_rereading_and_learning_strategy',
        'ki_system.v8_phase4j_internal_learning_questions_and_gap_detection',
        'ki_system.v8_phase4i_runtime_schema_guard_fixed3',
        'ki_system.v8_phase4h_self_evaluation_and_revision_core',
    ]:
        try:
            mod = __import__(modname, fromlist=['x'])
            run = getattr(mod, 'managed_run', None) or getattr(mod, 'safe_run', None)
            cyc = getattr(mod, 'managed_cycle', None) or getattr(mod, 'safe_cycle', None)
            if callable(run) and callable(cyc):
                return run, cyc, modname
        except Exception:
            continue
    return None, None, None


def managed_cycle(self, progress=None):
    ensure_phase4m_schema(self)
    base_run, base_cycle, base_name = _load_base()
    base_result = None
    if callable(base_cycle):
        base_result = base_cycle(self, progress)
    control = active_learning_controller(self)
    return {
        'status': PHASE,
        'message': 'Active learning loop controller: neuromodulators coordinate hypothesis learning, gaps, rereading, consolidation and strategy. No word blacklists. No facts/relations/questions.',
        'base_runtime': base_name,
        'base_result': base_result,
        'active_learning_control': control,
        'no_word_blacklists': True,
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'internal_learning_questions_only'
    }


def managed_run(self, cycles=1, progress=None):
    results = []
    for _ in range(cycles or 1):
        results.append(managed_cycle(self, progress))
        # Honor stop flags if present.
        if getattr(self, 'stop_requested', False) or getattr(self, '_stop_requested', False):
            break
    return results


def patch_autonomous_loop(*args, **kwargs):
    try:
        from ki_system.autonomous import AutonomousLoop
        AutonomousLoop.cycle = managed_cycle
        AutonomousLoop.run = managed_run
        AutonomousLoop.phase4m_active_learning_loop_controller = True
        AutonomousLoop._phase4m_active_learning_loop_controller = True
        AutonomousLoop.phase4l_gap_cluster_planning_and_strategy_balance = True
        AutonomousLoop.phase4k_gap_driven_rereading_and_learning_strategy = True
        AutonomousLoop.phase4j_internal_learning_questions_and_gap_detection = True
        AutonomousLoop.phase4i_long_term_memory_and_pattern_stability = True
        AutonomousLoop.phase4h_self_evaluation_and_revision_core = True
        AutonomousLoop.phase4g_neuromodulated_learning_control = True
        AutonomousLoop.no_word_blacklists = True
        AutonomousLoop._no_word_blacklists = True
        AutonomousLoop.learning_mode = LEARNING_MODE
        AutonomousLoop._rollback_learning_mode = LEARNING_MODE
        AutonomousLoop.fact_promotion = 'disabled'
        AutonomousLoop._fact_promotion = 'disabled'
        return True
    except Exception as exc:
        print('[PHASE4M_ACTIVE_LEARNING_AUTOLOAD_ERROR]', exc)
        return False


patch_autonomous_loop()
