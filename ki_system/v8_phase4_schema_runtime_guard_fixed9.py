
# v8_phase4_schema_runtime_guard_fixed9.py
# Phase4 canonical runtime schema guard FIXED9
# Goal: make Phase4def robust against old DB schemas without word blacklists, facts, relations, or questions writes.

import sqlite3
import time

PHASE = "phase4_schema_runtime_guard_fixed9"


def _get_db(obj):
    """Return sqlite3 connection from Memory, AutonomousLoop, or connection-like object."""
    if isinstance(obj, sqlite3.Connection):
        return obj
    if hasattr(obj, "db") and isinstance(getattr(obj, "db"), sqlite3.Connection):
        return getattr(obj, "db")
    for name in ("mem", "memory", "m", "store", "memory_store"):
        v = getattr(obj, name, None)
        if isinstance(v, sqlite3.Connection):
            return v
        if hasattr(v, "db") and isinstance(getattr(v, "db"), sqlite3.Connection):
            return getattr(v, "db")
    # last fallback: scan attributes for something with .db
    for name in dir(obj):
        if name.startswith("__"):
            continue
        try:
            v = getattr(obj, name)
        except Exception:
            continue
        if isinstance(v, sqlite3.Connection):
            return v
        if hasattr(v, "db") and isinstance(getattr(v, "db"), sqlite3.Connection):
            return getattr(v, "db")
    raise AttributeError("No sqlite3 connection / Memory.db found on object")


def _table_exists(cur, table):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur, table):
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _ensure_table(cur, table, create_sql):
    cur.execute(create_sql)


def _add_col(cur, table, col, decl, changes):
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        changes.append(f"add_column:{table}.{col}")


def _ensure_unique_index(cur, table, col, changes):
    if not _table_exists(cur, table) or col not in _cols(cur, table):
        return
    # If duplicates exist in derived/cache tables, keep the lowest rowid and remove duplicate cache rows.
    dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} WHERE {col} IS NOT NULL GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
    if dup:
        # Only de-duplicate derived/cache tables. Never delete core hypotheses or corpus tables.
        if table in {"hypothesis_clusters", "context_pattern_memory", "chunk_attention_scores", "hypothesis_stability_scores", "context_role_stats", "reading_queue", "learning_strategy_state", "rollback_safe_core_state", "attention_queue_state", "reading_strategy_state"}:
            cur.execute(f"DELETE FROM {table} WHERE rowid NOT IN (SELECT MIN(rowid) FROM {table} GROUP BY {col})")
            changes.append(f"dedupe:{table}.{col}")
        else:
            changes.append(f"skip_unique_duplicates:{table}.{col}")
            return
    idx = f"idx_{table}_{col}_phase4_fixed9_unique"
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
    changes.append(f"unique_index:{table}.{col}")


def ensure_phase4_schema(mem_or_loop):
    db = _get_db(mem_or_loop)
    cur = db.cursor()
    changes = []
    now = int(time.time())

    # Core safety/state tables
    _ensure_table(cur, "rollback_safe_core_state", """
        CREATE TABLE IF NOT EXISTS rollback_safe_core_state(
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """)
    _ensure_table(cur, "learning_strategy_state", """
        CREATE TABLE IF NOT EXISTS learning_strategy_state(
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """)

    # Queue
    _ensure_table(cur, "reading_queue", """
        CREATE TABLE IF NOT EXISTS reading_queue(
            chunk_id INTEGER PRIMARY KEY,
            priority REAL DEFAULT 0,
            reason TEXT,
            attention_score REAL DEFAULT 0,
            read_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            last_read INTEGER DEFAULT 0,
            updated_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('priority','REAL DEFAULT 0'),('reason','TEXT'),('attention_score','REAL DEFAULT 0'),('read_count','INTEGER DEFAULT 0'),('status',"TEXT DEFAULT 'pending'"),('last_read','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'reading_queue',c,d,changes)

    # Hypotheses
    _ensure_table(cur, "context_hypotheses", """
        CREATE TABLE IF NOT EXISTS context_hypotheses(
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
        )
    """)
    for c,d in [
        ('chunk_id','INTEGER'),('role','TEXT'),('subject','TEXT'),('relation_hint','TEXT'),('object','TEXT'),('text_excerpt','TEXT'),('source_title','TEXT'),
        ('confidence','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 1'),('status',"TEXT DEFAULT 'hypothesis'"),
        ('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),
        ('signature','TEXT'),('evidence_count','INTEGER DEFAULT 1'),('created_at','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'context_hypotheses',c,d,changes)

    _ensure_table(cur, "context_learning_events", """
        CREATE TABLE IF NOT EXISTS context_learning_events(
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
        )
    """)
    for c,d in [('hypothesis_id','INTEGER'),('event_type','TEXT'),('role','TEXT'),('details','TEXT'),('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'context_learning_events',c,d,changes)

    _ensure_table(cur, "hypothesis_feedback", """
        CREATE TABLE IF NOT EXISTS hypothesis_feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis_id INTEGER,
            feedback_type TEXT,
            signal REAL DEFAULT 0,
            reason TEXT,
            details TEXT,
            created_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('hypothesis_id','INTEGER'),('feedback_type','TEXT'),('signal','REAL DEFAULT 0'),('reason','TEXT'),('details','TEXT'),('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'hypothesis_feedback',c,d,changes)

    _ensure_table(cur, "hypothesis_revisions", """
        CREATE TABLE IF NOT EXISTS hypothesis_revisions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis_id INTEGER,
            old_role TEXT,
            new_role TEXT,
            old_confidence REAL DEFAULT 0,
            new_confidence REAL DEFAULT 0,
            reason TEXT,
            details TEXT,
            created_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('hypothesis_id','INTEGER'),('old_role','TEXT'),('new_role','TEXT'),('old_confidence','REAL DEFAULT 0'),('new_confidence','REAL DEFAULT 0'),('reason','TEXT'),('details','TEXT'),('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'hypothesis_revisions',c,d,changes)

    _ensure_table(cur, "hypothesis_error_events", """
        CREATE TABLE IF NOT EXISTS hypothesis_error_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hypothesis_id INTEGER,
            error_type TEXT,
            severity REAL DEFAULT 0,
            role TEXT,
            error_signal REAL DEFAULT 0,
            reason TEXT,
            details TEXT,
            created_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('hypothesis_id','INTEGER'),('error_type','TEXT'),('severity','REAL DEFAULT 0'),('role','TEXT'),('error_signal','REAL DEFAULT 0'),('reason','TEXT'),('details','TEXT'),('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'hypothesis_error_events',c,d,changes)

    _ensure_table(cur, "neuromodulated_attention_events", """
        CREATE TABLE IF NOT EXISTS neuromodulated_attention_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER,
            hypothesis_id INTEGER,
            event_type TEXT,
            attention_score REAL DEFAULT 0,
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
        )
    """)
    for c,d in [('chunk_id','INTEGER'),('hypothesis_id','INTEGER'),('event_type','TEXT'),('attention_score','REAL DEFAULT 0'),('novelty','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 0'),('reward','REAL DEFAULT 0'),('fatigue','REAL DEFAULT 0'),('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),('details','TEXT'),('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'neuromodulated_attention_events',c,d,changes)

    _ensure_table(cur, "context_role_stats", """
        CREATE TABLE IF NOT EXISTS context_role_stats(
            role TEXT PRIMARY KEY,
            seen INTEGER DEFAULT 0,
            seen_count INTEGER DEFAULT 0,
            avg_confidence REAL DEFAULT 0,
            avg_uncertainty REAL DEFAULT 0,
            feedback_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            updated_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('seen','INTEGER DEFAULT 0'),('seen_count','INTEGER DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 0'),('feedback_count','INTEGER DEFAULT 0'),('error_count','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'context_role_stats',c,d,changes)
    if 'seen' in _cols(cur,'context_role_stats') and 'seen_count' in _cols(cur,'context_role_stats'):
        cur.execute("UPDATE context_role_stats SET seen_count=COALESCE(NULLIF(seen_count,0), COALESCE(seen,0))")

    _ensure_table(cur, "chunk_attention_scores", """
        CREATE TABLE IF NOT EXISTS chunk_attention_scores(
            chunk_id INTEGER PRIMARY KEY,
            attention_score REAL DEFAULT 0,
            novelty_score REAL DEFAULT 0,
            uncertainty_score REAL DEFAULT 0,
            reward_score REAL DEFAULT 0,
            fatigue_score REAL DEFAULT 0,
            last_reason TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('attention_score','REAL DEFAULT 0'),('novelty_score','REAL DEFAULT 0'),('uncertainty_score','REAL DEFAULT 0'),('reward_score','REAL DEFAULT 0'),('fatigue_score','REAL DEFAULT 0'),('last_reason','TEXT'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'chunk_attention_scores',c,d,changes)

    for table in ['attention_queue_state','reading_strategy_state','learning_strategy_state','rollback_safe_core_state']:
        _ensure_table(cur, table, f"""
            CREATE TABLE IF NOT EXISTS {table}(
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at INTEGER DEFAULT 0
            )
        """)
        for c,d in [('value','TEXT'),('updated_at','INTEGER DEFAULT 0')]:
            _add_col(cur,table,c,d,changes)

    _ensure_table(cur, "hypothesis_clusters", """
        CREATE TABLE IF NOT EXISTS hypothesis_clusters(
            cluster_key TEXT PRIMARY KEY,
            role TEXT,
            size INTEGER DEFAULT 0,
            avg_confidence REAL DEFAULT 0,
            avg_uncertainty REAL DEFAULT 0,
            stability REAL DEFAULT 0,
            example TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('role','TEXT'),('size','INTEGER DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 0'),('stability','REAL DEFAULT 0'),('example','TEXT'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'hypothesis_clusters',c,d,changes)

    _ensure_table(cur, "hypothesis_stability_scores", """
        CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(
            hypothesis_id INTEGER PRIMARY KEY,
            role TEXT,
            stability REAL DEFAULT 0,
            confidence REAL DEFAULT 0,
            uncertainty REAL DEFAULT 0,
            feedback_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            evidence_count INTEGER DEFAULT 0,
            updated_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('role','TEXT'),('stability','REAL DEFAULT 0'),('confidence','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 0'),('feedback_count','INTEGER DEFAULT 0'),('error_count','INTEGER DEFAULT 0'),('evidence_count','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'hypothesis_stability_scores',c,d,changes)

    _ensure_table(cur, "context_pattern_memory", """
        CREATE TABLE IF NOT EXISTS context_pattern_memory(
            pattern_key TEXT PRIMARY KEY,
            role TEXT,
            seen_count INTEGER DEFAULT 0,
            avg_confidence REAL DEFAULT 0,
            avg_uncertainty REAL DEFAULT 0,
            stability REAL DEFAULT 0,
            updated_at INTEGER DEFAULT 0
        )
    """)
    for c,d in [('role','TEXT'),('seen_count','INTEGER DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 0'),('stability','REAL DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'context_pattern_memory',c,d,changes)

    _ensure_table(cur, "neuromodulator_sleep_events", """
        CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events(
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
        )
    """)
    for c,d in [('event_type','TEXT'),('details','TEXT'),('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),('created_at','INTEGER DEFAULT 0')]:
        _add_col(cur,'neuromodulator_sleep_events',c,d,changes)

    # Unique indexes for ON CONFLICT clauses.
    for table, col in [
        ('reading_queue','chunk_id'),('context_role_stats','role'),('chunk_attention_scores','chunk_id'),
        ('attention_queue_state','key'),('reading_strategy_state','key'),('learning_strategy_state','key'),('rollback_safe_core_state','key'),
        ('hypothesis_clusters','cluster_key'),('hypothesis_stability_scores','hypothesis_id'),('context_pattern_memory','pattern_key')]:
        _ensure_unique_index(cur, table, col, changes)

    # Safety state
    for k,v in {
        'phase': PHASE,
        'no_word_blacklists': 'true',
        'learning_mode': 'context_hypotheses_with_neuromodulators',
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'disabled',
    }.items():
        cur.execute("INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, repr(v), now))

    db.commit()
    return changes


def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        return False
    # Avoid double wrapping.
    if getattr(AutonomousLoop, '_phase4_schema_runtime_guard_fixed9', False):
        return True
    orig_run = AutonomousLoop.run
    orig_cycle = AutonomousLoop.cycle

    def guarded_run(self, cycles=5, progress=None):
        ensure_phase4_schema(self)
        return orig_run(self, cycles, progress)

    def guarded_cycle(self, progress=None):
        ensure_phase4_schema(self)
        return orig_cycle(self, progress)

    AutonomousLoop.run = guarded_run
    AutonomousLoop.cycle = guarded_cycle
    # Public and private markers for compatibility with existing tools.
    for name in [
        'phase4_schema_runtime_guard_fixed9', '_phase4_schema_runtime_guard_fixed9',
        'phase4_schema_manager_canonicalization', '_phase4_schema_manager_canonicalization',
        'phase4d_hypothesis_feedback_error_learning', '_phase4d_hypothesis_feedback_error_learning',
        'phase4e_neuromodulated_attention_strategy', '_phase4e_neuromodulated_attention_strategy',
        'phase4f_sleep_consolidation_self_improvement', '_phase4f_sleep_consolidation_self_improvement',
        'phase4def_context_learning_pack', '_phase4def_context_learning_pack',
        'no_word_blacklists', '_no_word_blacklists'
    ]:
        setattr(AutonomousLoop, name, True)
    AutonomousLoop.learning_mode = 'context_hypotheses_with_neuromodulators'
    AutonomousLoop._rollback_learning_mode = 'context_hypotheses_with_neuromodulators'
    AutonomousLoop.fact_promotion = 'disabled'
    AutonomousLoop._fact_promotion = 'disabled'
    return True
