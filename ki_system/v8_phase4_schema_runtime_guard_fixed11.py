
# v8_phase4_schema_runtime_guard_fixed11.py
# Canonical runtime schema guard for Phase4 context learning.
# Goal: prevent old partial schemas from crashing Phase4def runtime.
# No word blacklists, no facts/relations/questions writes.
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

PHASE = "phase4_schema_runtime_guard_fixed11"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _conn_from_mem(mem):
    """Return sqlite3.Connection from Memory-like object, connection, or db path."""
    if isinstance(mem, sqlite3.Connection):
        return mem
    for attr in ("db", "conn", "connection"):
        obj = getattr(mem, attr, None)
        if isinstance(obj, sqlite3.Connection):
            return obj
    path = getattr(mem, "path", None) or getattr(mem, "db_path", None) or "ki_memory.sqlite3"
    return sqlite3.connect(str(path))


def _mem_from_loop(loop):
    for name in ("mem", "memory", "m", "store", "memory_store"):
        obj = getattr(loop, name, None)
        if obj is not None:
            return obj
    # fallback: first attribute with sqlite connection
    for obj in getattr(loop, "__dict__", {}).values():
        if isinstance(obj, sqlite3.Connection) or isinstance(getattr(obj, "db", None), sqlite3.Connection):
            return obj
    return "ki_memory.sqlite3"


def _table_exists(cur, table):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur, table):
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _add_col(cur, table, col, typ):
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        return True
    return False


def _ensure_unique_index(cur, table, col):
    if not _table_exists(cur, table) or col not in _cols(cur, table):
        return False
    # Deduplicate derived/cache tables if needed. Keep earliest rowid.
    dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
    if dup:
        # These tables are derived runtime state. Removing duplicate cache rows is safer than runtime crash.
        cur.execute(f"DELETE FROM {table} WHERE rowid NOT IN (SELECT MIN(rowid) FROM {table} GROUP BY {col})")
    idx = f"idx_{table}_{col}_phase4_fixed11_unique"
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
    return True


def ensure_phase4_schema(mem=None):
    con = _conn_from_mem(mem)
    close = not isinstance(mem, sqlite3.Connection) and not isinstance(getattr(mem, "db", None), sqlite3.Connection)
    cur = con.cursor()
    changes=[]
    now=int(time.time())

    # Base/safety tables
    cur.execute("CREATE TABLE IF NOT EXISTS rollback_safe_core_state (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS learning_strategy_state (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")

    # Reading queue
    cur.execute("""CREATE TABLE IF NOT EXISTS reading_queue (
        chunk_id INTEGER PRIMARY KEY,
        priority REAL DEFAULT 0,
        reason TEXT,
        attention_score REAL DEFAULT 0,
        read_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        last_read INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")

    # Main hypothesis tables
    cur.execute("""CREATE TABLE IF NOT EXISTS context_hypotheses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chunk_id INTEGER,
        role TEXT,
        subject TEXT,
        relation_hint TEXT,
        object TEXT,
        text_excerpt TEXT,
        source_title TEXT,
        confidence REAL DEFAULT 0,
        uncertainty REAL DEFAULT 1,
        status TEXT DEFAULT 'hypothesis',
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        signature TEXT,
        evidence_count INTEGER DEFAULT 1,
        created_at INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    for col,typ in {
        'chunk_id':'INTEGER','role':'TEXT','subject':'TEXT','relation_hint':'TEXT','object':'TEXT','text_excerpt':'TEXT','source_title':'TEXT',
        'confidence':'REAL DEFAULT 0','uncertainty':'REAL DEFAULT 1','status':"TEXT DEFAULT 'hypothesis'",
        'dopamine':'REAL DEFAULT 0','serotonin':'REAL DEFAULT 0','glutamate':'REAL DEFAULT 0','gaba':'REAL DEFAULT 0','noradrenaline':'REAL DEFAULT 0','acetylcholine':'REAL DEFAULT 0',
        'signature':'TEXT','evidence_count':'INTEGER DEFAULT 1','created_at':'INTEGER DEFAULT 0','updated_at':'INTEGER DEFAULT 0'
    }.items():
        if _add_col(cur,'context_hypotheses',col,typ): changes.append(f'add_column:context_hypotheses.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS context_learning_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis_id INTEGER,
        event_type TEXT,
        role TEXT,
        details TEXT,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0
    )""")
    for col,typ in {
        'hypothesis_id':'INTEGER','event_type':'TEXT','role':'TEXT','details':'TEXT','dopamine':'REAL DEFAULT 0','serotonin':'REAL DEFAULT 0','glutamate':'REAL DEFAULT 0','gaba':'REAL DEFAULT 0','noradrenaline':'REAL DEFAULT 0','acetylcholine':'REAL DEFAULT 0','created_at':'INTEGER DEFAULT 0'
    }.items():
        if _add_col(cur,'context_learning_events',col,typ): changes.append(f'add_column:context_learning_events.{col}')

    # Feedback and error learning
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis_id INTEGER,
        feedback_type TEXT,
        signal REAL DEFAULT 0,
        reason TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'hypothesis_id':'INTEGER','feedback_type':'TEXT','signal':'REAL DEFAULT 0','reason':'TEXT','details':'TEXT','created_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'hypothesis_feedback',col,typ): changes.append(f'add_column:hypothesis_feedback.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_error_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis_id INTEGER,
        error_type TEXT,
        severity REAL DEFAULT 0,
        reason TEXT,
        details TEXT,
        role TEXT,
        error_signal REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'hypothesis_id':'INTEGER','error_type':'TEXT','severity':'REAL DEFAULT 0','reason':'TEXT','details':'TEXT','role':'TEXT','error_signal':'REAL DEFAULT 0','created_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'hypothesis_error_events',col,typ): changes.append(f'add_column:hypothesis_error_events.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis_id INTEGER,
        old_role TEXT,
        new_role TEXT,
        old_confidence REAL DEFAULT 0,
        new_confidence REAL DEFAULT 0,
        reason TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'hypothesis_id':'INTEGER','old_role':'TEXT','new_role':'TEXT','old_confidence':'REAL DEFAULT 0','new_confidence':'REAL DEFAULT 0','reason':'TEXT','details':'TEXT','created_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'hypothesis_revisions',col,typ): changes.append(f'add_column:hypothesis_revisions.{col}')

    # Attention
    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulated_attention_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chunk_id INTEGER,
        hypothesis_id INTEGER,
        attention_reason TEXT,
        novelty REAL DEFAULT 0,
        uncertainty REAL DEFAULT 0,
        reward REAL DEFAULT 0,
        fatigue REAL DEFAULT 0,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'chunk_id':'INTEGER','hypothesis_id':'INTEGER','attention_reason':'TEXT','novelty':'REAL DEFAULT 0','uncertainty':'REAL DEFAULT 0','reward':'REAL DEFAULT 0','fatigue':'REAL DEFAULT 0','dopamine':'REAL DEFAULT 0','serotonin':'REAL DEFAULT 0','glutamate':'REAL DEFAULT 0','gaba':'REAL DEFAULT 0','noradrenaline':'REAL DEFAULT 0','acetylcholine':'REAL DEFAULT 0','details':'TEXT','created_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'neuromodulated_attention_events',col,typ): changes.append(f'add_column:neuromodulated_attention_events.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS chunk_attention_scores (
        chunk_id INTEGER,
        attention_score REAL DEFAULT 0,
        novelty_score REAL DEFAULT 0,
        uncertainty_score REAL DEFAULT 0,
        reward_score REAL DEFAULT 0,
        fatigue_score REAL DEFAULT 0,
        last_reason TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'chunk_id':'INTEGER','attention_score':'REAL DEFAULT 0','novelty_score':'REAL DEFAULT 0','uncertainty_score':'REAL DEFAULT 0','reward_score':'REAL DEFAULT 0','fatigue_score':'REAL DEFAULT 0','last_reason':'TEXT','updated_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'chunk_attention_scores',col,typ): changes.append(f'add_column:chunk_attention_scores.{col}')

    cur.execute("CREATE TABLE IF NOT EXISTS attention_queue_state (key TEXT, value TEXT, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS reading_strategy_state (key TEXT, value TEXT, updated_at INTEGER DEFAULT 0)")

    # Stats and sleep consolidation
    cur.execute("""CREATE TABLE IF NOT EXISTS context_role_stats (
        role TEXT,
        seen INTEGER DEFAULT 0,
        seen_count INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        feedback_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'role':'TEXT','seen':'INTEGER DEFAULT 0','seen_count':'INTEGER DEFAULT 0','avg_confidence':'REAL DEFAULT 0','avg_uncertainty':'REAL DEFAULT 0','feedback_count':'INTEGER DEFAULT 0','error_count':'INTEGER DEFAULT 0','updated_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'context_role_stats',col,typ): changes.append(f'add_column:context_role_stats.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_clusters (
        cluster_key TEXT,
        role TEXT,
        size INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        stability REAL DEFAULT 0,
        example TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'cluster_key':'TEXT','role':'TEXT','size':'INTEGER DEFAULT 0','avg_confidence':'REAL DEFAULT 0','avg_uncertainty':'REAL DEFAULT 0','stability':'REAL DEFAULT 0','example':'TEXT','updated_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'hypothesis_clusters',col,typ): changes.append(f'add_column:hypothesis_clusters.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_stability_scores (
        hypothesis_id INTEGER,
        stability REAL DEFAULT 0,
        confidence REAL DEFAULT 0,
        uncertainty REAL DEFAULT 0,
        evidence_count INTEGER DEFAULT 0,
        feedback_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        conflict_count INTEGER DEFAULT 0,
        last_reason TEXT,
        role TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'hypothesis_id':'INTEGER','stability':'REAL DEFAULT 0','confidence':'REAL DEFAULT 0','uncertainty':'REAL DEFAULT 0','evidence_count':'INTEGER DEFAULT 0','feedback_count':'INTEGER DEFAULT 0','error_count':'INTEGER DEFAULT 0','conflict_count':'INTEGER DEFAULT 0','last_reason':'TEXT','role':'TEXT','updated_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'hypothesis_stability_scores',col,typ): changes.append(f'add_column:hypothesis_stability_scores.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS context_pattern_memory (
        pattern_key TEXT,
        role TEXT,
        seen_count INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        stability REAL DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'pattern_key':'TEXT','role':'TEXT','seen_count':'INTEGER DEFAULT 0','avg_confidence':'REAL DEFAULT 0','avg_uncertainty':'REAL DEFAULT 0','stability':'REAL DEFAULT 0','updated_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'context_pattern_memory',col,typ): changes.append(f'add_column:context_pattern_memory.{col}')

    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        details TEXT,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0
    )""")
    for col,typ in {'event_type':'TEXT','details':'TEXT','dopamine':'REAL DEFAULT 0','serotonin':'REAL DEFAULT 0','glutamate':'REAL DEFAULT 0','gaba':'REAL DEFAULT 0','noradrenaline':'REAL DEFAULT 0','acetylcholine':'REAL DEFAULT 0','created_at':'INTEGER DEFAULT 0'}.items():
        if _add_col(cur,'neuromodulator_sleep_events',col,typ): changes.append(f'add_column:neuromodulator_sleep_events.{col}')

    # Backfill counters where Phase4abc used seen only.
    if _table_exists(cur,'context_role_stats'):
        cur.execute("UPDATE context_role_stats SET seen_count=COALESCE(NULLIF(seen_count,0), COALESCE(seen,0))")

    # UNIQUE indexes for all ON CONFLICT statements.
    for table,col in [
        ('reading_queue','chunk_id'),('context_role_stats','role'),('chunk_attention_scores','chunk_id'),
        ('attention_queue_state','key'),('reading_strategy_state','key'),('hypothesis_clusters','cluster_key'),
        ('hypothesis_stability_scores','hypothesis_id'),('context_pattern_memory','pattern_key'),
        ('learning_strategy_state','key'),('rollback_safe_core_state','key')]:
        if _ensure_unique_index(cur, table, col):
            changes.append(f'unique_index:{table}.{col}')

    # State values
    state = {
        'phase': PHASE,
        'no_word_blacklists': 'true',
        'learning_mode': LEARNING_MODE,
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'disabled',
    }
    for k,v in state.items():
        cur.execute("INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, repr(v), now))

    con.commit()
    if close:
        con.close()
    return {'status': PHASE, 'changes': changes}


def patch_autonomous_loop(*args, **kwargs):
    from ki_system.autonomous import AutonomousLoop
    import ki_system.v8_phase4def_context_learning_pack as phase4def

    # Use existing functional Phase4def safe_run/cycle, only guard schema before delegating.
    orig_run = getattr(phase4def, 'safe_run')
    orig_cycle = getattr(phase4def, 'safe_cycle')

    def guarded_cycle(self, progress=None):
        ensure_phase4_schema(_mem_from_loop(self))
        return orig_cycle(self, progress)

    def guarded_run(self, cycles=5, progress=None):
        ensure_phase4_schema(_mem_from_loop(self))
        return orig_run(self, cycles, progress)

    AutonomousLoop.cycle = guarded_cycle
    AutonomousLoop.run = guarded_run

    # Diagnostic markers: with and without underscores for older tests.
    markers = {
        'phase4_schema_runtime_guard_fixed11': True,
        'phase4_schema_manager_canonicalization': True,
        'phase4d_hypothesis_feedback_error_learning': True,
        'phase4e_neuromodulated_attention_strategy': True,
        'phase4f_sleep_consolidation_self_improvement': True,
        'phase4def_context_learning_pack': True,
        'no_word_blacklists': True,
        'learning_mode': LEARNING_MODE,
        'rollback_learning_mode': LEARNING_MODE,
        'fact_promotion': 'disabled',
    }
    for k,v in markers.items():
        setattr(AutonomousLoop, k, v)
        setattr(AutonomousLoop, '_' + k, v)
    return True

# Apply on import when possible.
try:
    patch_autonomous_loop()
except Exception as exc:
    print('[PHASE4_SCHEMA_RUNTIME_GUARD_FIXED11_AUTOLOAD_ERROR]', exc)
