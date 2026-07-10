# V8-phase4o_schema_guard_FIXED2
from __future__ import annotations
import json, time, sqlite3
PHASE="phase4o_schema_guard_fixed2"
LEARNING_MODE="context_hypotheses_with_neuromodulators"

def _now(): return int(time.time())
def _connect(x=None):
    if isinstance(x, sqlite3.Connection): return x, False
    if x is not None:
        for a in ("conn","con","connection","db"):
            c=getattr(x,a,None)
            if isinstance(c, sqlite3.Connection): return c, False
        for a in ("db_path","path","filename"):
            p=getattr(x,a,None)
            if p: return sqlite3.connect(str(p)), True
    return sqlite3.connect("ki_memory.sqlite3"), True

def _exists(cur,t): return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _cols(cur,t): return {r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()} if _exists(cur,t) else set()
def _add(cur,t,c,s,changes):
    if _exists(cur,t) and c not in _cols(cur,t):
        cur.execute(f"ALTER TABLE {t} ADD COLUMN {c} {s}"); changes.append(f"add_column:{t}.{c}")
def _table(cur,t,ddl,changes):
    old=_exists(cur,t); cur.execute(ddl)
    if not old: changes.append(f"create_table:{t}")
def _unique(cur,t,c,changes):
    if not _exists(cur,t) or c not in _cols(cur,t): return
    dup=cur.execute(f"SELECT {c}, COUNT(*) FROM {t} WHERE {c} IS NOT NULL GROUP BY {c} HAVING COUNT(*)>1 LIMIT 1").fetchone()
    if dup: changes.append(f"skip_unique_duplicates:{t}.{c}"); return
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_{c}_phase4o_fixed2_unique ON {t}({c})")
    changes.append(f"unique_index:{t}.{c}")

def ensure_phase4o_schema(mem_or_db=None):
    con,close=_connect(mem_or_db); cur=con.cursor(); changes=[]; now=_now()
    _table(cur,'strategy_feedback_events', "\nCREATE TABLE IF NOT EXISTS strategy_feedback_events(\n id INTEGER PRIMARY KEY AUTOINCREMENT,\n event_type TEXT DEFAULT 'strategy_feedback', target_type TEXT DEFAULT 'global_strategy', target_id INTEGER DEFAULT 0, target_key TEXT,\n strategy_key TEXT DEFAULT 'global_neuromodulated_strategy', strategy_name TEXT DEFAULT 'neuromodulated_learning_control', phase TEXT DEFAULT 'phase4o_strategy_effectiveness_feedback_loop',\n outcome_score REAL DEFAULT 0, progress_score REAL DEFAULT 0, error_pressure REAL DEFAULT 0, uncertainty_pressure REAL DEFAULT 0, stability_gain REAL DEFAULT 0, exploration_need REAL DEFAULT 0,\n recommendation TEXT DEFAULT 'observe_and_adapt', learning_rate REAL DEFAULT 0, error_weight REAL DEFAULT 0, revision_pressure REAL DEFAULT 0, exploration_pressure REAL DEFAULT 0,\n inhibition_level REAL DEFAULT 0, consolidation_gain REAL DEFAULT 0, dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0,\n noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, evidence_count INTEGER DEFAULT 0, affected_hypotheses INTEGER DEFAULT 0, affected_gaps INTEGER DEFAULT 0,\n affected_chunks INTEGER DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)\n", changes)
    _table(cur,'strategy_outcome_memory', "\nCREATE TABLE IF NOT EXISTS strategy_outcome_memory(\n strategy_key TEXT PRIMARY KEY, strategy_name TEXT DEFAULT 'neuromodulated_learning_control', observations INTEGER DEFAULT 0,\n avg_outcome_score REAL DEFAULT 0, avg_progress_score REAL DEFAULT 0, avg_error_pressure REAL DEFAULT 0, avg_uncertainty_pressure REAL DEFAULT 0,\n avg_stability_gain REAL DEFAULT 0, avg_exploration_need REAL DEFAULT 0, success_count INTEGER DEFAULT 0, failure_count INTEGER DEFAULT 0,\n last_recommendation TEXT DEFAULT 'observe_and_adapt', last_outcome_score REAL DEFAULT 0, last_progress_score REAL DEFAULT 0,\n learning_rate REAL DEFAULT 0, error_weight REAL DEFAULT 0, revision_pressure REAL DEFAULT 0, exploration_pressure REAL DEFAULT 0,\n inhibition_level REAL DEFAULT 0, consolidation_gain REAL DEFAULT 0, no_word_blacklists TEXT DEFAULT 'true', fact_promotion TEXT DEFAULT 'disabled',\n created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0, details TEXT)\n", changes)
    _table(cur,'strategy_adjustment_recommendations', "\nCREATE TABLE IF NOT EXISTS strategy_adjustment_recommendations(\n id INTEGER PRIMARY KEY AUTOINCREMENT, parameter TEXT, target TEXT DEFAULT 'neuromodulated_learning_control', source_value REAL DEFAULT 0, recommended_value REAL DEFAULT 0,\n delta REAL DEFAULT 0, reason TEXT DEFAULT 'phase4o_progress_adaptive_strategy', outcome_score REAL DEFAULT 0, error_pressure REAL DEFAULT 0, uncertainty_pressure REAL DEFAULT 0,\n stability_gain REAL DEFAULT 0, exploration_need REAL DEFAULT 0, status TEXT DEFAULT 'recommended', applied INTEGER DEFAULT 0, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0, details TEXT)\n", changes)
    _table(cur,'strategy_effectiveness_feedback_state', "CREATE TABLE IF NOT EXISTS strategy_effectiveness_feedback_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)", changes)
    specs={
      'strategy_feedback_events': {'event_type':"TEXT DEFAULT 'strategy_feedback'",'target_type':"TEXT DEFAULT 'global_strategy'",'target_id':'INTEGER DEFAULT 0','target_key':'TEXT','strategy_key':"TEXT DEFAULT 'global_neuromodulated_strategy'",'strategy_name':"TEXT DEFAULT 'neuromodulated_learning_control'",'phase':"TEXT DEFAULT 'phase4o_strategy_effectiveness_feedback_loop'",'outcome_score':'REAL DEFAULT 0','progress_score':'REAL DEFAULT 0','error_pressure':'REAL DEFAULT 0','uncertainty_pressure':'REAL DEFAULT 0','stability_gain':'REAL DEFAULT 0','exploration_need':'REAL DEFAULT 0','recommendation':"TEXT DEFAULT 'observe_and_adapt'",'learning_rate':'REAL DEFAULT 0','error_weight':'REAL DEFAULT 0','revision_pressure':'REAL DEFAULT 0','exploration_pressure':'REAL DEFAULT 0','inhibition_level':'REAL DEFAULT 0','consolidation_gain':'REAL DEFAULT 0','dopamine':'REAL DEFAULT 0','serotonin':'REAL DEFAULT 0','glutamate':'REAL DEFAULT 0','gaba':'REAL DEFAULT 0','noradrenaline':'REAL DEFAULT 0','acetylcholine':'REAL DEFAULT 0','evidence_count':'INTEGER DEFAULT 0','affected_hypotheses':'INTEGER DEFAULT 0','affected_gaps':'INTEGER DEFAULT 0','affected_chunks':'INTEGER DEFAULT 0','details':'TEXT','created_at':'INTEGER DEFAULT 0','updated_at':'INTEGER DEFAULT 0'},
      'strategy_outcome_memory': {'strategy_key':'TEXT','strategy_name':"TEXT DEFAULT 'neuromodulated_learning_control'",'observations':'INTEGER DEFAULT 0','avg_outcome_score':'REAL DEFAULT 0','avg_progress_score':'REAL DEFAULT 0','avg_error_pressure':'REAL DEFAULT 0','avg_uncertainty_pressure':'REAL DEFAULT 0','avg_stability_gain':'REAL DEFAULT 0','avg_exploration_need':'REAL DEFAULT 0','success_count':'INTEGER DEFAULT 0','failure_count':'INTEGER DEFAULT 0','last_recommendation':"TEXT DEFAULT 'observe_and_adapt'",'last_outcome_score':'REAL DEFAULT 0','last_progress_score':'REAL DEFAULT 0','learning_rate':'REAL DEFAULT 0','error_weight':'REAL DEFAULT 0','revision_pressure':'REAL DEFAULT 0','exploration_pressure':'REAL DEFAULT 0','inhibition_level':'REAL DEFAULT 0','consolidation_gain':'REAL DEFAULT 0','no_word_blacklists':"TEXT DEFAULT 'true'",'fact_promotion':"TEXT DEFAULT 'disabled'",'created_at':'INTEGER DEFAULT 0','updated_at':'INTEGER DEFAULT 0','details':'TEXT'},
      'strategy_adjustment_recommendations': {'parameter':'TEXT','target':"TEXT DEFAULT 'neuromodulated_learning_control'",'source_value':'REAL DEFAULT 0','recommended_value':'REAL DEFAULT 0','delta':'REAL DEFAULT 0','reason':"TEXT DEFAULT 'phase4o_progress_adaptive_strategy'",'outcome_score':'REAL DEFAULT 0','error_pressure':'REAL DEFAULT 0','uncertainty_pressure':'REAL DEFAULT 0','stability_gain':'REAL DEFAULT 0','exploration_need':'REAL DEFAULT 0','status':"TEXT DEFAULT 'recommended'",'applied':'INTEGER DEFAULT 0','created_at':'INTEGER DEFAULT 0','updated_at':'INTEGER DEFAULT 0','details':'TEXT'},
      'strategy_effectiveness_feedback_state': {'key':'TEXT','value':'TEXT','updated_at':'INTEGER DEFAULT 0'},
      'context_hypotheses': {'strategy_effectiveness_score':'REAL DEFAULT 0','last_strategy_feedback_at':'INTEGER DEFAULT 0','strategy_feedback_reason':'TEXT','progress_score':'REAL DEFAULT 0','progress_reason':'TEXT','last_progress_evaluated_at':'INTEGER DEFAULT 0'},
      'internal_learning_gaps': {'priority':'REAL DEFAULT 0','active_learning_priority':'REAL DEFAULT 0','progress_priority':'REAL DEFAULT 0','strategy_effectiveness_score':'REAL DEFAULT 0','last_strategy_feedback_at':'INTEGER DEFAULT 0','strategy_feedback_reason':'TEXT','last_progress_evaluated_at':'INTEGER DEFAULT 0','progress_reason':'TEXT','selection_count':'INTEGER DEFAULT 0','last_selected_at':'INTEGER DEFAULT 0'},
      'chunk_attention_scores': {'strategy_effectiveness_score':'REAL DEFAULT 0','last_strategy_feedback_at':'INTEGER DEFAULT 0','strategy_feedback_reason':'TEXT','progress_adjusted_score':'REAL DEFAULT 0','progress_adjustment_reason':'TEXT','active_learning_score':'REAL DEFAULT 0','strategy_reason':'TEXT'},
      'reading_queue': {'active_learning_priority':'REAL DEFAULT 0','cooldown_until':'INTEGER DEFAULT 0','attention_score':'REAL DEFAULT 0','priority':'REAL DEFAULT 0'},
      'active_learning_loop_state': {'key':'TEXT','value':'TEXT','updated_at':'INTEGER DEFAULT 0'},
      'progress_evaluation_state': {'key':'TEXT','value':'TEXT','updated_at':'INTEGER DEFAULT 0'},
    }
    for t, cs in specs.items():
        for c,s in cs.items(): _add(cur,t,c,s,changes)
    if _exists(cur,'internal_learning_gaps') and 'priority' in _cols(cur,'internal_learning_gaps'):
        cols=_cols(cur,'internal_learning_gaps'); parts=[]
        for c in ('strategy_effectiveness_score','progress_priority','active_learning_priority','reread_priority','severity'):
            if c in cols: parts.append(f'COALESCE({c},0)')
        if parts:
            cur.execute(f"UPDATE internal_learning_gaps SET priority=MAX(COALESCE(priority,0), MIN(1.0, ({' + '.join(parts)})/{len(parts)}))")
            changes.append('backfill:internal_learning_gaps.priority')
    for t,c in [('strategy_outcome_memory','strategy_key'),('strategy_effectiveness_feedback_state','key'),('reading_queue','chunk_id'),('chunk_attention_scores','chunk_id'),('active_learning_loop_state','key'),('progress_evaluation_state','key')]: _unique(cur,t,c,changes)
    if _exists(cur,'strategy_effectiveness_feedback_state'):
        for k,v in {'phase':PHASE,'no_word_blacklists':'true','learning_mode':LEARNING_MODE,'fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only'}.items():
            cur.execute('INSERT INTO strategy_effectiveness_feedback_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(k,v,now))
    con.commit()
    if close: con.close()
    return {'status':'ok','phase':PHASE,'changes':changes,'no_word_blacklists':True,'fact_promotion':'disabled'}

def _mem(loop):
    for a in ('mem','memory','m','store','memory_store'):
        v=getattr(loop,a,None)
        if v is not None: return v
    return None

def patch_autonomous_loop(*args, **kwargs):
    try:
        from ki_system.autonomous import AutonomousLoop
    except Exception:
        return False
    try:
        from ki_system import v8_phase4o_schema_guard_fixed1 as base
    except Exception:
        try:
            from ki_system import v8_phase4o_strategy_effectiveness_feedback_loop as base
        except Exception:
            base=None
    orig_run=(getattr(base,'managed_run',None) or getattr(base,'safe_run',None)) if base else getattr(AutonomousLoop,'run')
    orig_cycle=(getattr(base,'managed_cycle',None) or getattr(base,'safe_cycle',None)) if base else getattr(AutonomousLoop,'cycle')
    def managed_cycle(self, progress=None):
        ensure_phase4o_schema(_mem(self)); return orig_cycle(self, progress)
    def managed_run(self, cycles=1, progress=None):
        ensure_phase4o_schema(_mem(self)); return orig_run(self, cycles, progress)
    AutonomousLoop.cycle=managed_cycle; AutonomousLoop.run=managed_run
    for name in ['phase4o_schema_guard_fixed2','_phase4o_schema_guard_fixed2','phase4o_strategy_effectiveness_feedback_loop','_phase4o_strategy_effectiveness_feedback_loop','no_word_blacklists','_no_word_blacklists']:
        setattr(AutonomousLoop,name,True)
    AutonomousLoop.learning_mode=LEARNING_MODE; AutonomousLoop._learning_mode=LEARNING_MODE
    AutonomousLoop.fact_promotion='disabled'; AutonomousLoop._fact_promotion='disabled'
    return True
try:
    patch_autonomous_loop()
except Exception as exc:
    print('[PHASE4O_SCHEMA_GUARD_FIXED2_AUTOLOAD_ERROR]', exc)
