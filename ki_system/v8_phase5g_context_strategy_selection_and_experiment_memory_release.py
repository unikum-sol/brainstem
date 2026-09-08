
from __future__ import annotations
import sqlite3, time, json
from collections import defaultdict
PHASE='phase5g_context_strategy_selection_and_experiment_memory_release'
LEARNING_MODE='context_hypotheses_with_neuromodulators'

def _now(): return int(time.time())
def _json(x):
    try: return json.dumps(x, ensure_ascii=False, sort_keys=True)
    except Exception: return json.dumps({'repr':repr(x)}, ensure_ascii=False)
def _db(mem=None):
    if isinstance(mem, sqlite3.Connection): return mem, False
    if mem is not None:
        for a in ('con','conn','connection','db','sqlite','_con','_conn'):
            v=getattr(mem,a,None)
            if isinstance(v, sqlite3.Connection): return v, False
        for a in ('db_path','path','filename','file','memory_path'):
            p=getattr(mem,a,None)
            if isinstance(p,str) and p: return sqlite3.connect(p), True
    return sqlite3.connect('ki_memory.sqlite3'), True
def _exists(cur,t): return cur.execute('SELECT 1 FROM sqlite_master WHERE type="table" AND name=?',(t,)).fetchone() is not None
def _cols(cur,t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if _exists(cur,t) else []
def _count(cur,t):
    if not _exists(cur,t): return 0
    try: return int(cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
    except Exception: return 0
def _add(cur,t,c,typ,changes):
    if _exists(cur,t) and c not in _cols(cur,t):
        cur.execute(f'ALTER TABLE {t} ADD COLUMN {c} {typ}')
        changes.append(f'add_column:{t}.{c}')
def _unique(cur,t,c,changes):
    if _exists(cur,t) and c in _cols(cur,t):
        cur.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_{c}_phase5g_unique ON {t}({c})')
        changes.append(f'unique_index:{t}.{c}')

def ensure_schema(mem=None):
    con,close=_db(mem); cur=con.cursor(); changes=[]; now=_now()
    cur.execute('CREATE TABLE IF NOT EXISTS phase5g_context_strategy_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS phase5g_strategy_selection_memory(memory_key TEXT PRIMARY KEY,gap_type TEXT,role TEXT,strategy TEXT,observations INTEGER DEFAULT 0,avg_closure_delta REAL DEFAULT 0,avg_no_candidate_rate REAL DEFAULT 0,avg_overlap_score REAL DEFAULT 0,avg_effectiveness REAL DEFAULT 0,avg_outcome_score REAL DEFAULT 0,avg_expected_gain REAL DEFAULT 0,dopamine REAL DEFAULT 0,serotonin REAL DEFAULT 0,glutamate REAL DEFAULT 0,gaba REAL DEFAULT 0,noradrenaline REAL DEFAULT 0,acetylcholine REAL DEFAULT 0,recommendation TEXT,status TEXT DEFAULT "observe",details TEXT,first_seen INTEGER,last_seen INTEGER,updated_at INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS phase5g_strategy_experiments(id INTEGER PRIMARY KEY AUTOINCREMENT,gap_id INTEGER,gap_key TEXT,gap_type TEXT,role TEXT,source_strategy TEXT,selected_strategy TEXT,previous_best_strategy TEXT,center_chunk_id INTEGER,target_chunk_id INTEGER,window_radius INTEGER DEFAULT 0,expected_gain REAL DEFAULT 0,predicted_effectiveness REAL DEFAULT 0,observed_closure_delta REAL DEFAULT 0,no_candidate_rate REAL DEFAULT 0,overlap_score REAL DEFAULT 0,exploration_pressure REAL DEFAULT 0,inhibition_level REAL DEFAULT 0,learning_rate REAL DEFAULT 0,error_weight REAL DEFAULT 0,revision_pressure REAL DEFAULT 0,decision TEXT,outcome TEXT DEFAULT "pending",details TEXT,created_at INTEGER,updated_at INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS phase5g_experiment_outcomes(id INTEGER PRIMARY KEY AUTOINCREMENT,experiment_id INTEGER,gap_id INTEGER,strategy TEXT,before_score REAL DEFAULT 0,after_score REAL DEFAULT 0,closure_delta REAL DEFAULT 0,read_status TEXT,no_candidate_penalty REAL DEFAULT 0,effectiveness_score REAL DEFAULT 0,outcome TEXT,details TEXT,created_at INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS phase5g_neuromodulator_strategy_profiles(profile_key TEXT PRIMARY KEY,strategy TEXT,gap_type TEXT,role TEXT,observations INTEGER DEFAULT 0,avg_learning_rate REAL DEFAULT 0,avg_error_weight REAL DEFAULT 0,avg_revision_pressure REAL DEFAULT 0,avg_exploration_pressure REAL DEFAULT 0,avg_inhibition_level REAL DEFAULT 0,avg_consolidation_gain REAL DEFAULT 0,avg_closure_delta REAL DEFAULT 0,avg_effectiveness REAL DEFAULT 0,recommendation TEXT,updated_at INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS internal_learning_gaps(id INTEGER PRIMARY KEY AUTOINCREMENT,gap_key TEXT,gap_type TEXT,role TEXT,status TEXT DEFAULT "open",priority REAL DEFAULT 0,resolution_score REAL DEFAULT 0,strategy_effectiveness_score REAL DEFAULT 0,evidence_count INTEGER DEFAULT 0,updated_at INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS reading_queue(chunk_id INTEGER PRIMARY KEY,priority REAL DEFAULT 0,reason TEXT,attention_score REAL DEFAULT 0,read_count INTEGER DEFAULT 0,status TEXT DEFAULT "pending",last_read INTEGER DEFAULT 0,updated_at INTEGER DEFAULT 0)')
    cur.execute('CREATE TABLE IF NOT EXISTS chunk_attention_scores(chunk_id INTEGER PRIMARY KEY,attention_score REAL DEFAULT 0,novelty_score REAL DEFAULT 0,uncertainty_score REAL DEFAULT 0,reward_score REAL DEFAULT 0,fatigue_score REAL DEFAULT 0,last_reason TEXT,updated_at INTEGER DEFAULT 0)')
    for t in ('internal_learning_gaps','internal_learning_questions'):
        if _exists(cur,t):
            for c,typ in [('phase5g_selected_strategy','TEXT'),('phase5g_strategy_score','REAL DEFAULT 0'),('phase5g_experiment_count','INTEGER DEFAULT 0'),('phase5g_last_experiment_at','INTEGER DEFAULT 0'),('phase5g_outcome_score','REAL DEFAULT 0'),('phase5g_closure_delta','REAL DEFAULT 0'),('phase5g_no_candidate_rate','REAL DEFAULT 0'),('phase5g_overlap_score','REAL DEFAULT 0'),('phase5g_reason','TEXT'),('priority','REAL DEFAULT 0'),('resolution_score','REAL DEFAULT 0'),('strategy_effectiveness_score','REAL DEFAULT 0'),('learning_outcome_score','REAL DEFAULT 0')]: _add(cur,t,c,typ,changes)
    for t in ('reading_queue','chunk_attention_scores','context_hypotheses'):
        if _exists(cur,t):
            for c,typ in [('phase5g_score','REAL DEFAULT 0'),('phase5g_selected_strategy','TEXT'),('phase5g_strategy_score','REAL DEFAULT 0'),('phase5g_closure_delta','REAL DEFAULT 0'),('phase5g_no_candidate_rate','REAL DEFAULT 0'),('phase5g_overlap_score','REAL DEFAULT 0'),('phase5g_last_selected_at','INTEGER DEFAULT 0'),('phase5g_reason','TEXT')]: _add(cur,t,c,typ,changes)
    for t in ('phase5f_window_strategy_memory','phase5f_context_window_experiments','phase5e_runtime_state'):
        if _exists(cur,t):
            _add(cur,t,'phase5g_used_for_strategy_selection','INTEGER DEFAULT 0',changes); _add(cur,t,'phase5g_last_used_at','INTEGER DEFAULT 0',changes)
    if _exists(cur,'internal_learning_gaps') and 'priority' in _cols(cur,'internal_learning_gaps'):
        cols=_cols(cur,'internal_learning_gaps'); fallback='0.5'
        for cand in ('severity','active_learning_priority','progress_priority','reread_priority'):
            if cand in cols: fallback=cand; break
        cur.execute(f'UPDATE internal_learning_gaps SET priority=COALESCE(priority,{fallback},0.5)')
        changes.append('backfill:internal_learning_gaps.priority')
    for t,c in [('phase5g_context_strategy_state','key'),('phase5g_strategy_selection_memory','memory_key'),('phase5g_neuromodulator_strategy_profiles','profile_key'),('internal_learning_gaps','gap_key'),('internal_learning_questions','question_key'),('reading_queue','chunk_id'),('chunk_attention_scores','chunk_id')]: _unique(cur,t,c,changes)
    for k,v in {'phase':PHASE,'learning_mode':LEARNING_MODE,'no_word_blacklists':'true','fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only'}.items(): cur.execute('INSERT OR REPLACE INTO phase5g_context_strategy_state(key,value,updated_at) VALUES(?,?,?)',(k,str(v),now))
    con.commit();
    if close: con.close()
    return {'status':'ok','phase':PHASE,'changes':changes,'no_word_blacklists':True,'fact_promotion':'disabled'}

def _state_float(cur,t,k,d):
    if not _exists(cur,t): return d
    try:
        r=cur.execute(f'SELECT value FROM {t} WHERE key=?',(k,)).fetchone()
        return float(str(r[0]).strip("'\"")) if r and r[0] is not None else d
    except Exception: return d

def _choose(gt,role,closure,no_cand,overlap,eff):
    if eff>0.58 and closure>0.08: return 'reinforce_effective_window','reinforce_effective_strategy'
    if no_cand>0.35: return 'shift_away_from_no_candidate_context','avoid_unproductive_context'
    if gt=='role_confusion': return 'contrastive_context_window','compare_role_boundary_contexts'
    if overlap>0.78:
        return ('contrastive_context_window','try_contrastive_low_overlap_context') if closure<=0.03 else ('low_overlap_context_window','reduce_overlap')
    if gt=='repeated_uncertainty': return 'wider_context_window','increase_context_depth_for_repeated_uncertainty'
    return 'low_overlap_context_window','default_low_overlap_experiment'

def _load_window_memory(cur):
    rows=[]
    if not _exists(cur,'phase5f_window_strategy_memory'): return rows
    cols=_cols(cur,'phase5f_window_strategy_memory')
    strat='strategy' if 'strategy' in cols else ('window_strategy' if 'window_strategy' in cols else None)
    if not strat: return rows
    gap='gap_type' if 'gap_type' in cols else "'unknown'"; role='role' if 'role' in cols else "'unknown'"
    closure='avg_closure_delta' if 'avg_closure_delta' in cols else ('closure_delta' if 'closure_delta' in cols else '0')
    nc='avg_no_candidate_rate' if 'avg_no_candidate_rate' in cols else ('no_candidate_rate' if 'no_candidate_rate' in cols else '0')
    ov='avg_overlap_score' if 'avg_overlap_score' in cols else ('overlap_score' if 'overlap_score' in cols else '0')
    eff='avg_effectiveness' if 'avg_effectiveness' in cols else ('effectiveness_score' if 'effectiveness_score' in cols else '0')
    obs='observations' if 'observations' in cols else '1'
    try: rows=cur.execute(f"SELECT {strat},COALESCE({gap},'unknown'),COALESCE({role},'unknown'),COALESCE({closure},0),COALESCE({nc},0),COALESCE({ov},0),COALESCE({eff},0),COALESCE({obs},1) FROM phase5f_window_strategy_memory").fetchall()
    except Exception: rows=[]
    return rows

def apply_context_strategy_selection(mem=None):
    con,close=_db(mem); cur=con.cursor(); ensure_schema(con); now=_now()
    lr=_state_float(cur,'active_learning_loop_state','last_learning_rate',0.234); ew=_state_float(cur,'active_learning_loop_state','last_error_weight',0.407); rp=_state_float(cur,'active_learning_loop_state','last_revision_pressure',0.312); ep=_state_float(cur,'active_learning_loop_state','last_exploration_pressure',0.31); ih=_state_float(cur,'active_learning_loop_state','last_inhibition_level',0.349); cg=_state_float(cur,'active_learning_loop_state','last_consolidation_gain',0.297)
    mem_updates=0
    for strategy,gt,role,closure,nc,ov,eff,obs in _load_window_memory(cur):
        key=f'{strategy}:{gt}:{role}'; rec='observe'
        if closure>0.08 and eff>0.45: rec='reinforce'
        elif nc>0.35: rec='shift_away_from_no_candidate_context'
        elif ov>0.75: rec='reduce_overlap_or_contrast'
        cur.execute('INSERT INTO phase5g_strategy_selection_memory(memory_key,gap_type,role,strategy,observations,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,avg_effectiveness,avg_outcome_score,avg_expected_gain,recommendation,status,details,first_seen,last_seen,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_key) DO UPDATE SET observations=excluded.observations,avg_closure_delta=excluded.avg_closure_delta,avg_no_candidate_rate=excluded.avg_no_candidate_rate,avg_overlap_score=excluded.avg_overlap_score,avg_effectiveness=excluded.avg_effectiveness,recommendation=excluded.recommendation,last_seen=excluded.last_seen,updated_at=excluded.updated_at',(key,gt,role,strategy,int(obs or 0),float(closure or 0),float(nc or 0),float(ov or 0),float(eff or 0),float(eff or 0),max(float(closure or 0),float(eff or 0)),rec,'observe',_json({'source':'phase5f'}),now,now,now)); mem_updates+=1
    gaps=[]
    if _exists(cur,'internal_learning_gaps'):
        cols=_cols(cur,'internal_learning_gaps'); expr=lambda c,d='0': c if c in cols else d
        try: gaps=cur.execute(f"SELECT id,COALESCE(gap_key,'gap:'||id),COALESCE(gap_type,'unknown'),COALESCE(role,'unknown'),COALESCE({expr('priority')},0),COALESCE({expr('resolution_score')},0),COALESCE({expr('strategy_effectiveness_score')},0),COALESCE({expr('phase5f_closure_delta',expr('phase5e_closure_delta','0'))},0),COALESCE({expr('phase5f_no_candidate_rate','0')},0),COALESCE({expr('phase5f_overlap_score','1')},1),COALESCE({expr('hypothesis_id','0')},0) FROM internal_learning_gaps WHERE COALESCE(status,'open') IN ('open','internal_open','persistent_gap','monitoring','') ORDER BY COALESCE(priority,0) DESC,COALESCE(resolution_score,0) ASC,id DESC LIMIT 120").fetchall()
        except Exception: gaps=[]
    selected=experiments=queue_updates=0; dist=defaultdict(int)
    for gid,gkey,gt,role,prio,res,eff,closure,nc,ov,hid in gaps:
        selected+=1; strategy,reason=_choose(gt,role,float(closure or 0),float(nc or 0),float(ov or 0),float(eff or 0)); dist[strategy]+=1
        radius={'wider_context_window':8,'low_overlap_context_window':6,'contrastive_context_window':5,'shift_away_from_no_candidate_context':7,'reinforce_effective_window':3}.get(strategy,4)
        pred=max(0.05,min(1.0,0.25+0.35*float(eff or 0)+0.25*float(closure or 0)+0.15*ep-0.10*float(nc or 0)))
        egain=max(0.05,min(1.0,pred+0.2*(1-float(res or 0))-0.08*float(ov or 0)))
        cur.execute('UPDATE internal_learning_gaps SET phase5g_selected_strategy=?,phase5g_strategy_score=?,phase5g_experiment_count=COALESCE(phase5g_experiment_count,0)+1,phase5g_last_experiment_at=?,phase5g_outcome_score=?,phase5g_closure_delta=?,phase5g_no_candidate_rate=?,phase5g_overlap_score=?,phase5g_reason=? WHERE id=?',(strategy,round(egain,6),now,round(pred,6),float(closure or 0),float(nc or 0),float(ov or 0),reason,gid))
        center=None
        if hid and _exists(cur,'context_hypotheses') and 'chunk_id' in _cols(cur,'context_hypotheses'):
            r=cur.execute('SELECT chunk_id FROM context_hypotheses WHERE id=?',(hid,)).fetchone(); center=int(r[0]) if r and r[0] is not None else None
        if center is None: center=int((gid or 1)%1000)+1
        if strategy=='contrastive_context_window': offsets=[-2*radius,-radius,radius,2*radius]
        elif strategy=='low_overlap_context_window': offsets=[-radius,radius,-radius-2,radius+2]
        elif strategy=='shift_away_from_no_candidate_context': offsets=[-radius-3,radius+3,-radius-5,radius+5]
        else: offsets=[-radius,-1,1,radius]
        for off in offsets:
            target=center+off
            if target<=0: continue
            experiments+=1
            cur.execute('INSERT INTO phase5g_strategy_experiments(gap_id,gap_key,gap_type,role,source_strategy,selected_strategy,center_chunk_id,target_chunk_id,window_radius,expected_gain,predicted_effectiveness,observed_closure_delta,no_candidate_rate,overlap_score,exploration_pressure,inhibition_level,learning_rate,error_weight,revision_pressure,decision,outcome,details,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(gid,gkey,gt,role,'phase5f_or_gap_memory',strategy,center,target,radius,round(egain,6),round(pred,6),float(closure or 0),float(nc or 0),float(ov or 0),ep,ih,lr,ew,rp,reason,'pending',_json({'compass':'no_blacklists'}),now,now))
            score=max(0.05,min(0.95,egain+0.10*ep-0.08*ih-0.15*float(nc or 0)))
            cur.execute('INSERT INTO reading_queue(chunk_id,priority,reason,attention_score,read_count,status,last_read,updated_at,phase5g_score,phase5g_selected_strategy,phase5g_strategy_score,phase5g_closure_delta,phase5g_no_candidate_rate,phase5g_overlap_score,phase5g_last_selected_at,phase5g_reason) VALUES(?,?,?,?,0,"pending",0,?,?,?,?,?,?,?, ?,?) ON CONFLICT(chunk_id) DO UPDATE SET priority=MAX(COALESCE(reading_queue.priority,0),excluded.priority),attention_score=MAX(COALESCE(reading_queue.attention_score,0),excluded.attention_score),reason=excluded.reason,updated_at=excluded.updated_at,phase5g_score=excluded.phase5g_score,phase5g_selected_strategy=excluded.phase5g_selected_strategy,phase5g_strategy_score=excluded.phase5g_strategy_score,phase5g_closure_delta=excluded.phase5g_closure_delta,phase5g_no_candidate_rate=excluded.phase5g_no_candidate_rate,phase5g_overlap_score=excluded.phase5g_overlap_score,phase5g_last_selected_at=excluded.phase5g_last_selected_at,phase5g_reason=excluded.phase5g_reason',(target,round(score,6),'phase5g_context_strategy_selection',round(score,6),now,round(score,6),strategy,round(pred,6),float(closure or 0),float(nc or 0),float(ov or 0),now,reason))
            cur.execute('INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,reward_score,fatigue_score,last_reason,updated_at,phase5g_score,phase5g_selected_strategy,phase5g_strategy_score,phase5g_closure_delta,phase5g_no_candidate_rate,phase5g_overlap_score,phase5g_last_selected_at,phase5g_reason) VALUES(?,?,?,?,?,?,?, ?,?,?,?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET attention_score=MAX(COALESCE(chunk_attention_scores.attention_score,0),excluded.attention_score),novelty_score=MAX(COALESCE(chunk_attention_scores.novelty_score,0),excluded.novelty_score),uncertainty_score=MAX(COALESCE(chunk_attention_scores.uncertainty_score,0),excluded.uncertainty_score),reward_score=MAX(COALESCE(chunk_attention_scores.reward_score,0),excluded.reward_score),fatigue_score=excluded.fatigue_score,last_reason=excluded.last_reason,updated_at=excluded.updated_at,phase5g_score=excluded.phase5g_score,phase5g_selected_strategy=excluded.phase5g_selected_strategy,phase5g_strategy_score=excluded.phase5g_strategy_score,phase5g_closure_delta=excluded.phase5g_closure_delta,phase5g_no_candidate_rate=excluded.phase5g_no_candidate_rate,phase5g_overlap_score=excluded.phase5g_overlap_score,phase5g_last_selected_at=excluded.phase5g_last_selected_at,phase5g_reason=excluded.phase5g_reason',(target,round(score,6),round(min(1.0,0.5+ep),6),round(min(1.0,0.4+float(prio or 0)/2),6),round(pred,6),round(float(nc or 0),6),'phase5g_context_strategy_selection',now,round(score,6),strategy,round(pred,6),float(closure or 0),float(nc or 0),float(ov or 0),now,reason))
            queue_updates+=1
        pkey=f'{strategy}:{gt}:{role}'
        cur.execute('INSERT INTO phase5g_neuromodulator_strategy_profiles(profile_key,strategy,gap_type,role,observations,avg_learning_rate,avg_error_weight,avg_revision_pressure,avg_exploration_pressure,avg_inhibition_level,avg_consolidation_gain,avg_closure_delta,avg_effectiveness,recommendation,updated_at) VALUES(?,?,?,?,1,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(profile_key) DO UPDATE SET observations=observations+1,avg_learning_rate=(avg_learning_rate*0.85)+excluded.avg_learning_rate*0.15,avg_error_weight=(avg_error_weight*0.85)+excluded.avg_error_weight*0.15,avg_revision_pressure=(avg_revision_pressure*0.85)+excluded.avg_revision_pressure*0.15,avg_exploration_pressure=(avg_exploration_pressure*0.85)+excluded.avg_exploration_pressure*0.15,avg_inhibition_level=(avg_inhibition_level*0.85)+excluded.avg_inhibition_level*0.15,avg_consolidation_gain=(avg_consolidation_gain*0.85)+excluded.avg_consolidation_gain*0.15,avg_closure_delta=(avg_closure_delta*0.85)+excluded.avg_closure_delta*0.15,avg_effectiveness=(avg_effectiveness*0.85)+excluded.avg_effectiveness*0.15,recommendation=excluded.recommendation,updated_at=excluded.updated_at',(pkey,strategy,gt,role,lr,ew,rp,ep,ih,cg,float(closure or 0),pred,reason,now))
    top=max(dist.items(), key=lambda x:x[1])[0] if dist else 'observe'
    state={'phase':PHASE,'learning_mode':LEARNING_MODE,'no_word_blacklists':'true','fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only','last_gaps_considered':str(selected),'last_experiments_created':str(experiments),'last_queue_updates':str(queue_updates),'last_memory_updates':str(mem_updates),'last_recommended_strategy':top,'last_strategy_distribution':_json(dict(dist))}
    for k,v in state.items(): cur.execute('INSERT OR REPLACE INTO phase5g_context_strategy_state(key,value,updated_at) VALUES(?,?,?)',(k,v,now))
    con.commit(); result={'status':'phase5g_context_strategy_selection_complete','phase':PHASE,'gaps_considered':selected,'experiments_created':experiments,'queue_updates':queue_updates,'memory_updates':mem_updates,'recommended_strategy':top,'strategy_distribution':dict(dist),'facts':_count(cur,'facts'),'relations':_count(cur,'relations'),'questions':_count(cur,'questions'),'no_word_blacklists':True,'fact_promotion':'disabled'}
    if close: con.close()
    return result

_ORIG_RUN=None; _ORIG_CYCLE=None
def managed_cycle(self, progress=None):
    base=_ORIG_CYCLE(self, progress) if _ORIG_CYCLE else None
    try: res=apply_context_strategy_selection(getattr(self,'mem',None) or getattr(self,'memory',None) or getattr(self,'m',None))
    except Exception as e: res={'status':'phase5g_error','error':repr(e),'phase':PHASE}
    if isinstance(base,dict): base['phase5g_context_strategy_selection']=res; return base
    return {'base_cycle':base,'phase5g_context_strategy_selection':res}
def managed_run(self, cycles=1, progress=None):
    base=_ORIG_RUN(self, cycles, progress) if _ORIG_RUN else None
    try: res=apply_context_strategy_selection(getattr(self,'mem',None) or getattr(self,'memory',None) or getattr(self,'m',None))
    except Exception as e: res={'status':'phase5g_error','error':repr(e),'phase':PHASE}
    return {'base_run':base,'phase5g_context_strategy_selection':res}
def patch_autonomous_loop(AutonomousLoop=None):
    global _ORIG_RUN,_ORIG_CYCLE
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AL; AutonomousLoop=AL
    if getattr(AutonomousLoop,'phase5g_context_strategy_selection_and_experiment_memory_release',False): return AutonomousLoop
    _ORIG_RUN=getattr(AutonomousLoop,'run',None); _ORIG_CYCLE=getattr(AutonomousLoop,'cycle',None)
    AutonomousLoop.run=managed_run; AutonomousLoop.cycle=managed_cycle
    for n in ('phase5g_context_strategy_selection_and_experiment_memory_release','_phase5g_context_strategy_selection_and_experiment_memory_release','phase5f_context_expansion_effectiveness_and_adaptive_windowing_release','phase5e_context_expansion_and_gap_closure_release','phase5a_integrated_self_improving_learning_release'):
        setattr(AutonomousLoop,n,True)
    AutonomousLoop.no_word_blacklists=True; AutonomousLoop._no_word_blacklists=True; AutonomousLoop.learning_mode=LEARNING_MODE; AutonomousLoop._rollback_learning_mode=LEARNING_MODE; AutonomousLoop.fact_promotion='disabled'; AutonomousLoop._fact_promotion='disabled'
    return AutonomousLoop
