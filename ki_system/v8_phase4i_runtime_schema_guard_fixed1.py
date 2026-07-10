# V8-phase4i_runtime_schema_guard_fixed1
import sqlite3, time
PHASE = "phase4i_runtime_schema_guard_fixed1"

def _conn(obj):
    if isinstance(obj, sqlite3.Connection): return obj
    if obj is None: return None
    for name in ("db","conn","connection"):
        c=getattr(obj,name,None)
        if isinstance(c, sqlite3.Connection): return c
    for name in ("mem","memory","m","store","memory_store"):
        c=_conn(getattr(obj,name,None))
        if c is not None: return c
    for v in getattr(obj,"__dict__",{}).values():
        c=_conn(v)
        if c is not None: return c
    return None

def _table_exists(cur, table):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None

def _cols(cur, table):
    if not _table_exists(cur, table): return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}

def _add_col(cur, table, col, typ, changes):
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        changes.append(f"add_column:{table}.{col}")

def _idx(cur, table, col, changes):
    if _table_exists(cur, table) and col in _cols(cur, table):
        dups=cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 3").fetchall()
        if dups:
            changes.append(f"skip_unique_duplicates:{table}.{col}")
            return
        name=f"idx_{table}_{col}_phase4i_runtime_guard_fixed1_unique"
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")

def ensure_phase4i_runtime_schema(db_or_mem):
    db=_conn(db_or_mem)
    if db is None: raise RuntimeError('Phase4i runtime schema guard could not locate sqlite connection')
    cur=db.cursor(); changes=[]; now=int(time.time())
    cur.execute("""CREATE TABLE IF NOT EXISTS pattern_stability_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, pattern_key TEXT, role TEXT, observations INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, volatility REAL DEFAULT 0,
        decision TEXT, revision_pressure REAL DEFAULT 0, error_weight REAL DEFAULT 0,
        confidence_trend REAL DEFAULT 0, uncertainty_trend REAL DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    for col,typ in [("pattern_key","TEXT"),("role","TEXT"),("observations","INTEGER DEFAULT 0"),("avg_confidence","REAL DEFAULT 0"),("avg_uncertainty","REAL DEFAULT 0"),("stability","REAL DEFAULT 0"),("volatility","REAL DEFAULT 0"),("decision","TEXT"),("revision_pressure","REAL DEFAULT 0"),("error_weight","REAL DEFAULT 0"),("confidence_trend","REAL DEFAULT 0"),("uncertainty_trend","REAL DEFAULT 0"),("details","TEXT"),("created_at","INTEGER DEFAULT 0"),("updated_at","INTEGER DEFAULT 0")]:
        _add_col(cur,'pattern_stability_history',col,typ,changes)
    cur.execute("""CREATE TABLE IF NOT EXISTS long_term_pattern_memory(
        pattern_key TEXT PRIMARY KEY, dominant_role TEXT, observations INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, volatility REAL DEFAULT 0, last_decision TEXT,
        neuromodulator_profile TEXT, revision_pressure REAL DEFAULT 0, error_weight REAL DEFAULT 0,
        confidence_trend REAL DEFAULT 0, uncertainty_trend REAL DEFAULT 0, first_seen INTEGER DEFAULT 0, last_seen INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    for col,typ in [("pattern_key","TEXT"),("dominant_role","TEXT"),("observations","INTEGER DEFAULT 0"),("avg_confidence","REAL DEFAULT 0"),("avg_uncertainty","REAL DEFAULT 0"),("stability","REAL DEFAULT 0"),("volatility","REAL DEFAULT 0"),("last_decision","TEXT"),("neuromodulator_profile","TEXT"),("revision_pressure","REAL DEFAULT 0"),("error_weight","REAL DEFAULT 0"),("confidence_trend","REAL DEFAULT 0"),("uncertainty_trend","REAL DEFAULT 0"),("first_seen","INTEGER DEFAULT 0"),("last_seen","INTEGER DEFAULT 0"),("updated_at","INTEGER DEFAULT 0")]:
        _add_col(cur,'long_term_pattern_memory',col,typ,changes)
    cur.execute("""CREATE TABLE IF NOT EXISTS role_confusion_memory(
        confusion_key TEXT PRIMARY KEY, from_role TEXT, to_role TEXT, count INTEGER DEFAULT 0,
        avg_revision_pressure REAL DEFAULT 0, avg_self_score REAL DEFAULT 0, avg_error_weight REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0, last_reason TEXT, status TEXT DEFAULT 'observe', updated_at INTEGER DEFAULT 0)""")
    for col,typ in [("confusion_key","TEXT"),("from_role","TEXT"),("to_role","TEXT"),("count","INTEGER DEFAULT 0"),("avg_revision_pressure","REAL DEFAULT 0"),("avg_self_score","REAL DEFAULT 0"),("avg_error_weight","REAL DEFAULT 0"),("avg_uncertainty","REAL DEFAULT 0"),("last_reason","TEXT"),("status","TEXT DEFAULT 'observe'"),("updated_at","INTEGER DEFAULT 0")]:
        _add_col(cur,'role_confusion_memory',col,typ,changes)
    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulator_pattern_profiles(
        profile_key TEXT PRIMARY KEY, role TEXT, observations INTEGER DEFAULT 0, avg_dopamine REAL DEFAULT 0,
        avg_serotonin REAL DEFAULT 0, avg_glutamate REAL DEFAULT 0, avg_gaba REAL DEFAULT 0, avg_noradrenaline REAL DEFAULT 0,
        avg_acetylcholine REAL DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0,
        avg_learning_rate REAL DEFAULT 0, avg_error_weight REAL DEFAULT 0, avg_revision_pressure REAL DEFAULT 0,
        avg_consolidation_gain REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    for col,typ in [("profile_key","TEXT"),("role","TEXT"),("observations","INTEGER DEFAULT 0"),("avg_dopamine","REAL DEFAULT 0"),("avg_serotonin","REAL DEFAULT 0"),("avg_glutamate","REAL DEFAULT 0"),("avg_gaba","REAL DEFAULT 0"),("avg_noradrenaline","REAL DEFAULT 0"),("avg_acetylcholine","REAL DEFAULT 0"),("avg_confidence","REAL DEFAULT 0"),("avg_uncertainty","REAL DEFAULT 0"),("avg_learning_rate","REAL DEFAULT 0"),("avg_error_weight","REAL DEFAULT 0"),("avg_revision_pressure","REAL DEFAULT 0"),("avg_consolidation_gain","REAL DEFAULT 0"),("updated_at","INTEGER DEFAULT 0")]:
        _add_col(cur,'neuromodulator_pattern_profiles',col,typ,changes)
    cur.execute("""CREATE TABLE IF NOT EXISTS long_term_consolidation_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    for col,typ in [("key","TEXT"),("value","TEXT"),("updated_at","INTEGER DEFAULT 0")]: _add_col(cur,'long_term_consolidation_state',col,typ,changes)
    for table,col in [('long_term_pattern_memory','pattern_key'),('role_confusion_memory','confusion_key'),('neuromodulator_pattern_profiles','profile_key'),('long_term_consolidation_state','key')]: _idx(cur,table,col,changes)
    try:
        cur.execute("INSERT OR REPLACE INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?)",('phase',"'phase4i_runtime_schema_guard_fixed1'",now))
        cur.execute("INSERT OR REPLACE INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?)",('no_word_blacklists',"'true'",now))
        cur.execute("INSERT OR REPLACE INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?)",('fact_promotion',"'disabled'",now))
    except Exception: pass
    db.commit(); return changes

def patch_phase4i_module():
    from ki_system import v8_phase4i_long_term_memory_and_pattern_stability as phase4i
    if not hasattr(phase4i,'_runtime_schema_guard_fixed1_original_consolidate'):
        phase4i._runtime_schema_guard_fixed1_original_consolidate = phase4i.consolidate_long_term_memory
        def _guarded_consolidate(db_or_mem,*args,**kwargs):
            ensure_phase4i_runtime_schema(db_or_mem)
            return phase4i._runtime_schema_guard_fixed1_original_consolidate(db_or_mem,*args,**kwargs)
        phase4i.consolidate_long_term_memory = _guarded_consolidate
    return phase4i

def managed_cycle(self, progress=None):
    db=_conn(self)
    if db is not None: ensure_phase4i_runtime_schema(db)
    phase4i=patch_phase4i_module()
    try:
        from ki_system import v8_phase4i_runtime_autoload_and_periodic_consolidation_fix as rt
        return rt.managed_cycle(self, progress)
    except Exception:
        return phase4i.managed_cycle(self, progress)

def managed_run(self, cycles=1, progress=None):
    db=_conn(self)
    if db is not None: ensure_phase4i_runtime_schema(db)
    phase4i=patch_phase4i_module()
    try:
        from ki_system import v8_phase4i_runtime_autoload_and_periodic_consolidation_fix as rt
        return rt.managed_run(self, cycles, progress)
    except Exception:
        return phase4i.managed_run(self, cycles, progress)

def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AL
    else: AL=AutonomousLoop
    patch_phase4i_module()
    AL.run=managed_run; AL.cycle=managed_cycle
    for marker in ['phase4i_runtime_schema_guard_fixed1','phase4i_long_term_memory_and_pattern_stability']:
        setattr(AL, marker, True); setattr(AL, '_'+marker, True)
    AL.no_word_blacklists=True; AL._no_word_blacklists=True
    AL.learning_mode='context_hypotheses_with_neuromodulators'; AL._rollback_learning_mode='context_hypotheses_with_neuromodulators'
    AL.fact_promotion='disabled'; AL._fact_promotion='disabled'
    return AL
