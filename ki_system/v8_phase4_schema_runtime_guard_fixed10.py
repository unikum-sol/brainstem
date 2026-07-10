
# v8_phase4_schema_runtime_guard_fixed10.py
# Runtime schema guard for Phase4 context learning.
# Goal: canonical schema before every run/cycle; no word blacklists; no facts/relations/questions writes.
import sqlite3, time, sys

_FIXED10_MARKER = "phase4_schema_runtime_guard_fixed10"


def _conn(obj):
    """Return sqlite3 connection from Memory, AutonomousLoop, or connection."""
    if obj is None:
        raise RuntimeError("No memory/db object supplied")
    if isinstance(obj, sqlite3.Connection):
        return obj
    if hasattr(obj, 'db') and isinstance(getattr(obj, 'db'), sqlite3.Connection):
        return getattr(obj, 'db')
    # AutonomousLoop variants
    for name in ('mem', 'memory', 'm', 'store', 'memory_store'):
        if hasattr(obj, name):
            sub = getattr(obj, name)
            if isinstance(sub, sqlite3.Connection):
                return sub
            if hasattr(sub, 'db') and isinstance(getattr(sub, 'db'), sqlite3.Connection):
                return getattr(sub, 'db')
    # search shallow attributes
    for name in dir(obj):
        if name.startswith('_'):
            continue
        try:
            sub = getattr(obj, name)
        except Exception:
            continue
        if isinstance(sub, sqlite3.Connection):
            return sub
        if hasattr(sub, 'db') and isinstance(getattr(sub, 'db'), sqlite3.Connection):
            return getattr(sub, 'db')
    raise RuntimeError("Could not locate sqlite3 connection on object")


def _table_exists(cur, table):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur, table):
    if not _table_exists(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_col(cur, table, col, decl, changes):
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        changes.append(f"add_column:{table}.{col}")


def _dedupe(cur, table, key, changes):
    if not _table_exists(cur, table) or key not in _cols(cur, table):
        return
    # Derived/cache tables only. Keep lowest rowid for same key.
    try:
        dups = cur.execute(f"SELECT {key}, COUNT(*) FROM {table} GROUP BY {key} HAVING COUNT(*)>1 LIMIT 1").fetchone()
        if dups:
            cur.execute(f"DELETE FROM {table} WHERE rowid NOT IN (SELECT MIN(rowid) FROM {table} GROUP BY {key})")
            changes.append(f"dedupe:{table}.{key}")
    except Exception as exc:
        changes.append(f"dedupe_skip:{table}.{key}:{type(exc).__name__}")


def _unique(cur, table, key, changes):
    if not _table_exists(cur, table) or key not in _cols(cur, table):
        changes.append(f"unique_skip_missing:{table}.{key}")
        return
    _dedupe(cur, table, key, changes)
    idx = f"idx_{table}_{key}_phase4_fixed10_unique"
    try:
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({key})")
        changes.append(f"unique_index:{table}.{key}")
    except Exception as exc:
        changes.append(f"unique_index_error:{table}.{key}:{type(exc).__name__}:{exc}")


def ensure_phase4_schema(mem_or_db):
    con = _conn(mem_or_db)
    cur = con.cursor()
    changes = []
    now = int(time.time())

    # Core safety tables
    cur.execute("CREATE TABLE IF NOT EXISTS rollback_safe_core_state (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS learning_strategy_state (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")

    # Queue
    cur.execute("""CREATE TABLE IF NOT EXISTS reading_queue(
        chunk_id INTEGER PRIMARY KEY,
        priority REAL DEFAULT 0,
        reason TEXT,
        attention_score REAL DEFAULT 0,
        read_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        last_read INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    for col, decl in [
        ('priority','REAL DEFAULT 0'), ('reason','TEXT'), ('attention_score','REAL DEFAULT 0'),
        ('read_count','INTEGER DEFAULT 0'), ('status',"TEXT DEFAULT 'pending'"),
        ('last_read','INTEGER DEFAULT 0'), ('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'reading_queue', col, decl, changes)

    # Hypotheses
    cur.execute("""CREATE TABLE IF NOT EXISTS context_hypotheses(
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
        created_at INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0,
        signature TEXT,
        evidence_count INTEGER DEFAULT 1
    )""")
    for col, decl in [
        ('chunk_id','INTEGER'), ('role','TEXT'), ('subject','TEXT'), ('relation_hint','TEXT'), ('object','TEXT'),
        ('text_excerpt','TEXT'), ('source_title','TEXT'), ('confidence','REAL DEFAULT 0'), ('uncertainty','REAL DEFAULT 1'),
        ('status',"TEXT DEFAULT 'hypothesis'"), ('dopamine','REAL DEFAULT 0'), ('serotonin','REAL DEFAULT 0'),
        ('glutamate','REAL DEFAULT 0'), ('gaba','REAL DEFAULT 0'), ('noradrenaline','REAL DEFAULT 0'),
        ('acetylcholine','REAL DEFAULT 0'), ('created_at','INTEGER DEFAULT 0'), ('updated_at','INTEGER DEFAULT 0'),
        ('signature','TEXT'), ('evidence_count','INTEGER DEFAULT 1')]:
        _add_col(cur, 'context_hypotheses', col, decl, changes)

    # Learning events
    cur.execute("""CREATE TABLE IF NOT EXISTS context_learning_events(
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
    for col, decl in [
        ('hypothesis_id','INTEGER'), ('event_type','TEXT'), ('role','TEXT'), ('details','TEXT'),
        ('dopamine','REAL DEFAULT 0'), ('serotonin','REAL DEFAULT 0'), ('glutamate','REAL DEFAULT 0'),
        ('gaba','REAL DEFAULT 0'), ('noradrenaline','REAL DEFAULT 0'), ('acetylcholine','REAL DEFAULT 0'),
        ('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'context_learning_events', col, decl, changes)

    # Feedback/error/revision
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis_id INTEGER,
        feedback_type TEXT,
        signal REAL DEFAULT 0,
        reason TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    for col, decl in [('hypothesis_id','INTEGER'), ('feedback_type','TEXT'), ('signal','REAL DEFAULT 0'), ('reason','TEXT'), ('details','TEXT'), ('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'hypothesis_feedback', col, decl, changes)

    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_revisions(
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
    for col, decl in [('hypothesis_id','INTEGER'), ('old_role','TEXT'), ('new_role','TEXT'), ('old_confidence','REAL DEFAULT 0'), ('new_confidence','REAL DEFAULT 0'), ('reason','TEXT'), ('details','TEXT'), ('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'hypothesis_revisions', col, decl, changes)

    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_error_events(
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
    for col, decl in [('hypothesis_id','INTEGER'), ('error_type','TEXT'), ('severity','REAL DEFAULT 0'), ('reason','TEXT'), ('details','TEXT'), ('role','TEXT'), ('error_signal','REAL DEFAULT 0'), ('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'hypothesis_error_events', col, decl, changes)

    # Neuromodulated attention events - current failing table
    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulated_attention_events(
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
    for col, decl in [
        ('chunk_id','INTEGER'), ('hypothesis_id','INTEGER'), ('attention_reason','TEXT'), ('novelty','REAL DEFAULT 0'),
        ('uncertainty','REAL DEFAULT 0'), ('reward','REAL DEFAULT 0'), ('fatigue','REAL DEFAULT 0'),
        ('dopamine','REAL DEFAULT 0'), ('serotonin','REAL DEFAULT 0'), ('glutamate','REAL DEFAULT 0'),
        ('gaba','REAL DEFAULT 0'), ('noradrenaline','REAL DEFAULT 0'), ('acetylcholine','REAL DEFAULT 0'),
        ('details','TEXT'), ('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'neuromodulated_attention_events', col, decl, changes)

    # Stats/attention/strategy
    cur.execute("""CREATE TABLE IF NOT EXISTS context_role_stats(
        role TEXT PRIMARY KEY,
        seen INTEGER DEFAULT 0,
        seen_count INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        feedback_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    for col, decl in [('seen','INTEGER DEFAULT 0'), ('seen_count','INTEGER DEFAULT 0'), ('avg_confidence','REAL DEFAULT 0'), ('avg_uncertainty','REAL DEFAULT 0'), ('feedback_count','INTEGER DEFAULT 0'), ('error_count','INTEGER DEFAULT 0'), ('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'context_role_stats', col, decl, changes)
    try:
        cur.execute("UPDATE context_role_stats SET seen_count=seen WHERE COALESCE(seen_count,0)=0 AND COALESCE(seen,0)>0")
    except Exception:
        pass

    cur.execute("""CREATE TABLE IF NOT EXISTS chunk_attention_scores(
        chunk_id INTEGER PRIMARY KEY,
        attention_score REAL DEFAULT 0,
        novelty_score REAL DEFAULT 0,
        uncertainty_score REAL DEFAULT 0,
        reward_score REAL DEFAULT 0,
        fatigue_score REAL DEFAULT 0,
        last_reason TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    for col, decl in [('attention_score','REAL DEFAULT 0'), ('novelty_score','REAL DEFAULT 0'), ('uncertainty_score','REAL DEFAULT 0'), ('reward_score','REAL DEFAULT 0'), ('fatigue_score','REAL DEFAULT 0'), ('last_reason','TEXT'), ('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'chunk_attention_scores', col, decl, changes)

    cur.execute("CREATE TABLE IF NOT EXISTS attention_queue_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS reading_strategy_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")

    # Sleep/consolidation
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_clusters(
        cluster_key TEXT PRIMARY KEY,
        role TEXT,
        size INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        stability REAL DEFAULT 0,
        example TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    for col, decl in [('role','TEXT'), ('size','INTEGER DEFAULT 0'), ('avg_confidence','REAL DEFAULT 0'), ('avg_uncertainty','REAL DEFAULT 0'), ('stability','REAL DEFAULT 0'), ('example','TEXT'), ('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'hypothesis_clusters', col, decl, changes)

    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(
        hypothesis_id INTEGER PRIMARY KEY,
        stability REAL DEFAULT 0,
        confidence REAL DEFAULT 0,
        uncertainty REAL DEFAULT 0,
        feedback_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0,
        role TEXT,
        evidence_count INTEGER DEFAULT 0
    )""")
    for col, decl in [('stability','REAL DEFAULT 0'), ('confidence','REAL DEFAULT 0'), ('uncertainty','REAL DEFAULT 0'), ('feedback_count','INTEGER DEFAULT 0'), ('error_count','INTEGER DEFAULT 0'), ('updated_at','INTEGER DEFAULT 0'), ('role','TEXT'), ('evidence_count','INTEGER DEFAULT 0')]:
        _add_col(cur, 'hypothesis_stability_scores', col, decl, changes)

    cur.execute("""CREATE TABLE IF NOT EXISTS context_pattern_memory(
        pattern_key TEXT PRIMARY KEY,
        role TEXT,
        seen_count INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        stability REAL DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    for col, decl in [('role','TEXT'), ('seen_count','INTEGER DEFAULT 0'), ('avg_confidence','REAL DEFAULT 0'), ('avg_uncertainty','REAL DEFAULT 0'), ('stability','REAL DEFAULT 0'), ('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'context_pattern_memory', col, decl, changes)

    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events(
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
    for col, decl in [('event_type','TEXT'), ('details','TEXT'), ('dopamine','REAL DEFAULT 0'), ('serotonin','REAL DEFAULT 0'), ('glutamate','REAL DEFAULT 0'), ('gaba','REAL DEFAULT 0'), ('noradrenaline','REAL DEFAULT 0'), ('acetylcholine','REAL DEFAULT 0'), ('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur, 'neuromodulator_sleep_events', col, decl, changes)

    # Unique indexes for ON CONFLICT
    for table, key in [
        ('reading_queue','chunk_id'), ('context_role_stats','role'), ('chunk_attention_scores','chunk_id'),
        ('attention_queue_state','key'), ('reading_strategy_state','key'), ('hypothesis_clusters','cluster_key'),
        ('hypothesis_stability_scores','hypothesis_id'), ('context_pattern_memory','pattern_key'),
        ('learning_strategy_state','key'), ('rollback_safe_core_state','key')]:
        _unique(cur, table, key, changes)

    # Seed safe state
    state = {
        'no_word_blacklists': 'true',
        'learning_mode': 'context_hypotheses_with_neuromodulators',
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'disabled',
        'phase': 'phase4_schema_runtime_guard_fixed10',
    }
    for k, v in state.items():
        cur.execute("INSERT OR REPLACE INTO rollback_safe_core_state(key,value) VALUES(?,?)", (k, repr(v)))
    cur.execute("INSERT OR REPLACE INTO learning_strategy_state(key,value,updated_at) VALUES(?,?,?)", ('phase4_schema_runtime_guard_fixed10', 'active', now))

    con.commit()
    return changes


def _patch_marker(cls):
    for name in [
        'phase4_schema_runtime_guard_fixed10', '_phase4_schema_runtime_guard_fixed10',
        'phase4_schema_manager_canonicalization', '_phase4_schema_manager_canonicalization',
        'phase4d_hypothesis_feedback_error_learning', '_phase4d_hypothesis_feedback_error_learning',
        'phase4e_neuromodulated_attention_strategy', '_phase4e_neuromodulated_attention_strategy',
        'phase4f_sleep_consolidation_self_improvement', '_phase4f_sleep_consolidation_self_improvement',
        'phase4def_context_learning_pack', '_phase4def_context_learning_pack',
        'no_word_blacklists', '_no_word_blacklists',
    ]:
        setattr(cls, name, True)
    cls.learning_mode = 'context_hypotheses_with_neuromodulators'
    cls._rollback_learning_mode = 'context_hypotheses_with_neuromodulators'
    cls.fact_promotion = 'disabled'
    cls._fact_promotion = 'disabled'


def patch_autonomous_loop(*args, **kwargs):
    from ki_system.autonomous import AutonomousLoop
    import ki_system.v8_phase4def_context_learning_pack as phase4def
    _patch_marker(AutonomousLoop)

    def guarded_cycle(self, progress=None):
        ensure_phase4_schema(self)
        return phase4def.safe_cycle(self, progress)

    def guarded_run(self, cycles=1, progress=None):
        ensure_phase4_schema(self)
        return phase4def.safe_run(self, cycles, progress)

    guarded_cycle.__name__ = 'guarded_cycle_fixed10'
    guarded_run.__name__ = 'guarded_run_fixed10'
    AutonomousLoop.cycle = guarded_cycle
    AutonomousLoop.run = guarded_run
    return AutonomousLoop

# Try patch on import; safe when imported from autonomous autoload.
try:
    patch_autonomous_loop()
except Exception as exc:
    # Do not crash import; test tools will show failure if patch did not apply.
    print('[PHASE4_SCHEMA_RUNTIME_GUARD_FIXED10_AUTOLOAD_ERROR]', exc)
