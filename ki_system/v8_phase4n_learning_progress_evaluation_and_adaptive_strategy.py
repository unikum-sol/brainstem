
# V8-phase4n_learning_progress_evaluation_and_adaptive_strategy
# Ziel: Lernfortschritt bewerten und adaptive Strategie ableiten.
# Keine Wort-Blacklists, keine facts/relations/questions, keine Fact-Promotion.
from __future__ import annotations

import json, time, sqlite3, math
from collections import defaultdict

PHASE = "phase4n_learning_progress_evaluation_and_adaptive_strategy"


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _get_mem(loop):
    for name in ("mem", "memory", "m", "store", "memory_store"):
        obj = getattr(loop, name, None)
        if obj is not None:
            return obj
    # Fallback: find object with some db-like surface
    for obj in getattr(loop, "__dict__", {}).values():
        if hasattr(obj, "execute") or hasattr(obj, "conn") or hasattr(obj, "con") or hasattr(obj, "db_path"):
            return obj
    return None


def _db_from_mem(mem):
    if mem is None:
        return sqlite3.connect("ki_memory.sqlite3"), True
    if hasattr(mem, "execute") and hasattr(mem, "commit"):
        return mem, False
    for name in ("conn", "con", "connection", "db"):
        con = getattr(mem, name, None)
        if con is not None and hasattr(con, "execute"):
            return con, False
    for name in ("db_path", "path", "database_path", "filename"):
        p = getattr(mem, name, None)
        if p:
            return sqlite3.connect(str(p)), True
    return sqlite3.connect("ki_memory.sqlite3"), True


def _table_exists(db, table):
    try:
        return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None
    except Exception:
        return False


def _cols(db, table):
    if not _table_exists(db, table):
        return []
    return [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]


def _add_col(db, table, col, typ):
    cols = _cols(db, table)
    if col not in cols:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        return True
    return False


def _count(db, table):
    if not _table_exists(db, table):
        return 0
    try:
        return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] or 0)
    except Exception:
        return 0


def _state_get(db, table, key, default=None):
    if not _table_exists(db, table):
        return default
    try:
        row = db.execute(f"SELECT value FROM {table} WHERE key=?", (key,)).fetchone()
        return row[0] if row else default
    except Exception:
        return default


def _state_set(db, table, key, value, now=None):
    now = now or int(time.time())
    db.execute(f"CREATE TABLE IF NOT EXISTS {table}(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    db.execute(f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, str(value), now))


def ensure_phase4n_schema(mem_or_db=None):
    db, owned = _db_from_mem(mem_or_db)
    changes=[]
    try:
        db.execute("CREATE TABLE IF NOT EXISTS learning_progress_evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT, cycle_index INTEGER DEFAULT 0, hypotheses INTEGER DEFAULT 0, gaps INTEGER DEFAULT 0, errors INTEGER DEFAULT 0, updates_count INTEGER DEFAULT 0, long_term_patterns INTEGER DEFAULT 0, reread_actions INTEGER DEFAULT 0, active_decisions INTEGER DEFAULT 0, progress_score REAL DEFAULT 0, error_pressure REAL DEFAULT 0, uncertainty_pressure REAL DEFAULT 0, stability_gain REAL DEFAULT 0, exploration_need REAL DEFAULT 0, summary TEXT, created_at INTEGER DEFAULT 0)")
        db.execute("CREATE TABLE IF NOT EXISTS adaptive_strategy_adjustments(id INTEGER PRIMARY KEY AUTOINCREMENT, adjustment_type TEXT, target TEXT, old_value REAL DEFAULT 0, new_value REAL DEFAULT 0, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0)")
        db.execute("CREATE TABLE IF NOT EXISTS strategy_effectiveness_memory(strategy_key TEXT PRIMARY KEY, observations INTEGER DEFAULT 0, avg_progress_score REAL DEFAULT 0, avg_error_pressure REAL DEFAULT 0, avg_uncertainty_pressure REAL DEFAULT 0, avg_stability_gain REAL DEFAULT 0, last_decision TEXT, updated_at INTEGER DEFAULT 0)")
        db.execute("CREATE TABLE IF NOT EXISTS progress_evaluation_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
        for t in ("reading_strategy_state","attention_queue_state","learning_strategy_state","active_learning_loop_state","rollback_safe_core_state"):
            db.execute(f"CREATE TABLE IF NOT EXISTS {t}(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
        # Extend useful existing tables safely.
        if _table_exists(db, "context_hypotheses"):
            for col, typ in (('progress_score','REAL DEFAULT 0'),('last_progress_evaluated_at','INTEGER DEFAULT 0'),('progress_reason','TEXT')):
                if _add_col(db,"context_hypotheses",col,typ): changes.append(f"add_column:context_hypotheses.{col}")
        if _table_exists(db, "internal_learning_gaps"):
            for col, typ in (('progress_priority','REAL DEFAULT 0'),('last_progress_evaluated_at','INTEGER DEFAULT 0'),('progress_reason','TEXT')):
                if _add_col(db,"internal_learning_gaps",col,typ): changes.append(f"add_column:internal_learning_gaps.{col}")
        if _table_exists(db, "chunk_attention_scores"):
            for col, typ in (('progress_adjusted_score','REAL DEFAULT 0'),('progress_adjustment_reason','TEXT')):
                if _add_col(db,"chunk_attention_scores",col,typ): changes.append(f"add_column:chunk_attention_scores.{col}")
        # Some safety states
        now=int(time.time())
        for k,v in {
            'phase':PHASE,
            'no_word_blacklists':'true',
            'learning_mode':'context_hypotheses_with_neuromodulators',
            'fact_promotion':'disabled',
            'direct_fact_writes':'disabled',
            'direct_relation_writes':'disabled',
            'question_generation':'internal_learning_questions_only'
        }.items():
            _state_set(db,'progress_evaluation_state',k,v,now)
            _state_set(db,'rollback_safe_core_state',k,v,now)
        db.commit()
        return {'status':'ok','phase':PHASE,'changes':changes}
    finally:
        if owned:
            db.close()


def _float_state(db, table, key, default=0.0):
    val = _state_get(db, table, key, None)
    if val is None:
        return default
    try:
        return float(str(val).strip('"\''))
    except Exception:
        return default


def evaluate_learning_progress(mem_or_db=None, limit_hypotheses=300, limit_gaps=120, limit_chunks=500):
    db, owned = _db_from_mem(mem_or_db)
    now=int(time.time())
    try:
        ensure_phase4n_schema(db)
        metrics = {
            'hypotheses': _count(db,'context_hypotheses'),
            'gaps': _count(db,'internal_learning_gaps'),
            'errors': _count(db,'hypothesis_error_events'),
            'updates_count': _count(db,'hypothesis_learning_updates'),
            'long_term_patterns': _count(db,'long_term_pattern_memory'),
            'reread_actions': _count(db,'gap_driven_rereading_actions'),
            'active_decisions': _count(db,'active_learning_decisions'),
        }
        # Previous counters for deltas
        prev = {k: int(float(_state_get(db,'progress_evaluation_state','prev_'+k,0) or 0)) for k in metrics}
        delta = {k: metrics[k]-prev.get(k,0) for k in metrics}
        hyp = max(metrics['hypotheses'],1)
        progress_score = max(0.0, min(1.0, (delta['updates_count']*0.0008 + delta['long_term_patterns']*0.003 + delta['active_decisions']*0.02 + delta['reread_actions']*0.0005)))
        error_pressure = max(0.0, min(1.0, metrics['errors']/hyp))
        uncertainty_pressure = max(0.0, min(1.0, metrics['gaps']/hyp))
        stability_gain = max(0.0, min(1.0, delta['long_term_patterns']/max(delta['hypotheses'],1))) if delta['hypotheses'] else 0.0
        exploration_need = max(0.0, min(1.0, (uncertainty_pressure*0.55 + error_pressure*0.35 + (1.0-stability_gain)*0.10)))
        # Use neuromodulator controlled values as base if present.
        lr = _float_state(db,'active_learning_loop_state','last_learning_rate',0.234)
        ew = _float_state(db,'active_learning_loop_state','last_error_weight',0.407)
        rp = _float_state(db,'active_learning_loop_state','last_revision_pressure',0.312)
        ep = _float_state(db,'active_learning_loop_state','last_exploration_pressure',0.31)
        inhibition = _float_state(db,'active_learning_loop_state','last_inhibition_level',0.349)
        cg = _float_state(db,'active_learning_loop_state','last_consolidation_gain',0.297)
        # Adaptive suggestions (bounded, conservative)
        suggested = {
            'learning_rate': max(0.05,min(0.45, lr + 0.03*progress_score - 0.02*error_pressure)),
            'error_weight': max(0.10,min(0.80, ew + 0.04*error_pressure)),
            'revision_pressure': max(0.05,min(0.70, rp + 0.04*uncertainty_pressure + 0.02*error_pressure)),
            'exploration_pressure': max(0.05,min(0.75, ep + 0.05*exploration_need)),
            'inhibition_level': max(0.05,min(0.80, inhibition + 0.03*error_pressure + 0.02*uncertainty_pressure)),
            'consolidation_gain': max(0.05,min(0.70, cg + 0.04*stability_gain - 0.015*error_pressure)),
        }
        summary = {'metrics':metrics,'delta':delta,'suggested':{k:round(v,4) for k,v in suggested.items()}}
        cycle_index = _count(db,'learning_progress_evaluations') + 1
        db.execute("INSERT INTO learning_progress_evaluations(phase,cycle_index,hypotheses,gaps,errors,updates_count,long_term_patterns,reread_actions,active_decisions,progress_score,error_pressure,uncertainty_pressure,stability_gain,exploration_need,summary,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(PHASE,cycle_index,metrics['hypotheses'],metrics['gaps'],metrics['errors'],metrics['updates_count'],metrics['long_term_patterns'],metrics['reread_actions'],metrics['active_decisions'],round(progress_score,6),round(error_pressure,6),round(uncertainty_pressure,6),round(stability_gain,6),round(exploration_need,6),_json(summary),now))
        # Store adjustments and strategy memory
        base = {'learning_rate':lr,'error_weight':ew,'revision_pressure':rp,'exploration_pressure':ep,'inhibition_level':inhibition,'consolidation_gain':cg}
        for key,newv in suggested.items():
            oldv = base[key]
            reason = 'phase4n_progress_adaptive_strategy'
            db.execute("INSERT INTO adaptive_strategy_adjustments(adjustment_type,target,old_value,new_value,reason,details,created_at) VALUES(?,?,?,?,?,?,?)",(key,'neuromodulated_learning_control',round(oldv,6),round(newv,6),reason,_json({'progress_score':progress_score,'error_pressure':error_pressure,'uncertainty_pressure':uncertainty_pressure,'stability_gain':stability_gain,'exploration_need':exploration_need}),now))
            _state_set(db,'reading_strategy_state','phase4n_'+key,round(newv,6),now)
            _state_set(db,'attention_queue_state','phase4n_'+key,round(newv,6),now)
            _state_set(db,'learning_strategy_state','phase4n_'+key,round(newv,6),now)
            _state_set(db,'active_learning_loop_state','phase4n_'+key,round(newv,6),now)
        skey='global_neuromodulated_strategy'
        old = db.execute("SELECT observations,avg_progress_score,avg_error_pressure,avg_uncertainty_pressure,avg_stability_gain FROM strategy_effectiveness_memory WHERE strategy_key=?",(skey,)).fetchone()
        if old:
            obs,aps,aep,aup,asg=old; obs=int(obs)+1
            vals=((aps*(obs-1)+progress_score)/obs,(aep*(obs-1)+error_pressure)/obs,(aup*(obs-1)+uncertainty_pressure)/obs,(asg*(obs-1)+stability_gain)/obs)
            db.execute("UPDATE strategy_effectiveness_memory SET observations=?, avg_progress_score=?, avg_error_pressure=?, avg_uncertainty_pressure=?, avg_stability_gain=?, last_decision=?, updated_at=? WHERE strategy_key=?",(obs,*[round(x,6) for x in vals],'observe_and_adapt',now,skey))
        else:
            db.execute("INSERT INTO strategy_effectiveness_memory(strategy_key,observations,avg_progress_score,avg_error_pressure,avg_uncertainty_pressure,avg_stability_gain,last_decision,updated_at) VALUES(?,?,?,?,?,?,?,?)",(skey,1,round(progress_score,6),round(error_pressure,6),round(uncertainty_pressure,6),round(stability_gain,6),'observe_and_adapt',now))
        # Mark top hypotheses/gaps/chunks with progress scores.
        if _table_exists(db,'context_hypotheses') and 'progress_score' in _cols(db,'context_hypotheses'):
            db.execute("UPDATE context_hypotheses SET progress_score=COALESCE(active_learning_score,0)*0.55 + uncertainty*0.25 + COALESCE(revision_pressure,0)*0.20, last_progress_evaluated_at=?, progress_reason=? WHERE id IN (SELECT id FROM context_hypotheses ORDER BY COALESCE(active_learning_score,0) DESC, uncertainty DESC LIMIT ?)",(now,PHASE,limit_hypotheses))
        if _table_exists(db,'internal_learning_gaps') and 'progress_priority' in _cols(db,'internal_learning_gaps'):
            db.execute("UPDATE internal_learning_gaps SET progress_priority=COALESCE(active_learning_priority,0)*0.60 + severity*0.30 + COALESCE(selection_count,0)*0.01, last_progress_evaluated_at=?, progress_reason=? WHERE id IN (SELECT id FROM internal_learning_gaps ORDER BY COALESCE(active_learning_priority,0) DESC, severity DESC LIMIT ?)",(now,PHASE,limit_gaps))
        if _table_exists(db,'chunk_attention_scores') and 'progress_adjusted_score' in _cols(db,'chunk_attention_scores'):
            db.execute("UPDATE chunk_attention_scores SET progress_adjusted_score=attention_score*0.65 + novelty_score*0.15 + uncertainty_score*0.20, progress_adjustment_reason=? WHERE chunk_id IN (SELECT chunk_id FROM chunk_attention_scores ORDER BY COALESCE(active_learning_score,attention_score) DESC LIMIT ?)",(PHASE,limit_chunks))
        for k,v in metrics.items():
            _state_set(db,'progress_evaluation_state','prev_'+k,v,now)
        for k,v in {
            'phase':PHASE,
            'last_progress_score':round(progress_score,6),
            'last_error_pressure':round(error_pressure,6),
            'last_uncertainty_pressure':round(uncertainty_pressure,6),
            'last_stability_gain':round(stability_gain,6),
            'last_exploration_need':round(exploration_need,6),
            'last_evaluated_hypotheses':limit_hypotheses,
            'last_evaluated_gaps':limit_gaps,
            'last_evaluated_chunks':limit_chunks,
            'no_word_blacklists':'true',
            'fact_promotion':'disabled',
            'question_generation':'internal_learning_questions_only'
        }.items():
            _state_set(db,'progress_evaluation_state',k,v,now)
        db.commit()
        return {'status':'phase4n_learning_progress_evaluation_complete','phase':PHASE,'metrics':metrics,'delta':delta,'progress_score':round(progress_score,6),'error_pressure':round(error_pressure,6),'uncertainty_pressure':round(uncertainty_pressure,6),'stability_gain':round(stability_gain,6),'exploration_need':round(exploration_need,6),'no_word_blacklists':True,'fact_promotion':'disabled'}
    finally:
        if owned:
            db.close()


def _call_base_run(loop, cycles=1, progress=None):
    try:
        from ki_system import v8_phase4m_active_learning_loop_controller as base
        return base.managed_run(loop, cycles, progress)
    except Exception:
        # fallback to original if patch stored it
        orig = getattr(loop.__class__, '_phase4n_original_run', None)
        if callable(orig):
            return orig(loop, cycles, progress)
        return []


def _call_base_cycle(loop, progress=None):
    try:
        from ki_system import v8_phase4m_active_learning_loop_controller as base
        return base.managed_cycle(loop, progress)
    except Exception:
        orig = getattr(loop.__class__, '_phase4n_original_cycle', None)
        if callable(orig):
            return orig(loop, progress)
        return {'status':'base_cycle_unavailable'}


def managed_cycle(self, progress=None):
    mem = _get_mem(self)
    result = _call_base_cycle(self, progress)
    eval_result = evaluate_learning_progress(mem)
    if isinstance(result, dict):
        result['phase4n_learning_progress_evaluation'] = eval_result
        return result
    return {'status':'phase4n_managed_cycle','base_result':result,'phase4n_learning_progress_evaluation':eval_result}


def managed_run(self, cycles=1, progress=None):
    mem = _get_mem(self)
    result = _call_base_run(self, cycles, progress)
    eval_result = evaluate_learning_progress(mem)
    if isinstance(result, list):
        return result + [{'status':'phase4n_active_learning_progress_evaluation','phase4n_learning_progress_evaluation':eval_result}]
    if isinstance(result, dict):
        result['phase4n_learning_progress_evaluation'] = eval_result
        return result
    return [{'status':'phase4n_managed_run','base_result':str(result),'phase4n_learning_progress_evaluation':eval_result}]


def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AL
        AutonomousLoop = AL
    if not getattr(AutonomousLoop,'_phase4n_original_run',None):
        AutonomousLoop._phase4n_original_run = getattr(AutonomousLoop,'run',None)
    if not getattr(AutonomousLoop,'_phase4n_original_cycle',None):
        AutonomousLoop._phase4n_original_cycle = getattr(AutonomousLoop,'cycle',None)
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    # marker variants
    for name in ('phase4n_learning_progress_evaluation_and_adaptive_strategy','_phase4n_learning_progress_evaluation_and_adaptive_strategy'):
        setattr(AutonomousLoop,name,True)
    for name in ('phase4m_active_learning_loop_controller','_phase4m_active_learning_loop_controller','phase4g_neuromodulated_learning_control','_phase4g_neuromodulated_learning_control'):
        setattr(AutonomousLoop,name,True)
    AutonomousLoop.no_word_blacklists=True
    AutonomousLoop._no_word_blacklists=True
    AutonomousLoop.learning_mode='context_hypotheses_with_neuromodulators'
    AutonomousLoop._rollback_learning_mode='context_hypotheses_with_neuromodulators'
    AutonomousLoop.fact_promotion='disabled'
    AutonomousLoop._fact_promotion='disabled'
    return AutonomousLoop

try:
    from ki_system.autonomous import AutonomousLoop
    patch_autonomous_loop(AutonomousLoop)
except Exception:
    pass
