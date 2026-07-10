from __future__ import annotations
import sqlite3, time, json
PHASE='phase5e_context_expansion_and_gap_closure_release'
LEARNING_MODE='context_hypotheses_with_neuromodulators'

def _now(): return int(time.time())
def _json(o):
    try: return json.dumps(o, ensure_ascii=False, sort_keys=True)
    except Exception: return json.dumps({'repr':repr(o)}, ensure_ascii=False)

def _db(mem=None):
    if mem is None: return sqlite3.connect('ki_memory.sqlite3')
    for a in ('conn','con','db','connection','sqlite_conn'):
        x=getattr(mem,a,None)
        if x is not None and hasattr(x,'execute'): return x
    if hasattr(mem,'execute'): return mem
    return sqlite3.connect('ki_memory.sqlite3')

def _exists(db,t): return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _cols(db,t): return {r[1] for r in db.execute(f'PRAGMA table_info({t})').fetchall()} if _exists(db,t) else set()
def _cnt(db,t): return db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if _exists(db,t) else 0

def _addcol(db,t,c,spec):
    if _exists(db,t) and c not in _cols(db,t):
        db.execute(f'ALTER TABLE {t} ADD COLUMN {c} {spec}')
        return f'add_column:{t}.{c}'

def _uix(db,t,c):
    if _exists(db,t) and c in _cols(db,t):
        name=f'idx_{t}_{c}_phase5e_unique'
        try:
            db.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {t}({c})')
            return f'unique_index:{t}.{c}'
        except sqlite3.IntegrityError:
            return f'skip_unique_duplicates:{t}.{c}'

def ensure_phase5e_schema(mem=None):
    db=_db(mem); changes=[]
    ddls=[
    ("context_expansion_plans", """CREATE TABLE IF NOT EXISTS context_expansion_plans(plan_key TEXT PRIMARY KEY,gap_id INTEGER,gap_key TEXT,cluster_key TEXT,role TEXT,source_type TEXT,context_window INTEGER DEFAULT 3,expansion_strategy TEXT,priority REAL DEFAULT 0,expected_gain REAL DEFAULT 0,neuromodulator_reason TEXT,status TEXT DEFAULT 'open',evidence_count INTEGER DEFAULT 0,attempts INTEGER DEFAULT 0,last_action_at INTEGER DEFAULT 0,created_at INTEGER DEFAULT 0,updated_at INTEGER DEFAULT 0,details TEXT)"""),
    ("context_expansion_actions", """CREATE TABLE IF NOT EXISTS context_expansion_actions(id INTEGER PRIMARY KEY AUTOINCREMENT,plan_key TEXT,gap_id INTEGER,gap_key TEXT,chunk_id INTEGER,neighbor_chunk_id INTEGER,direction TEXT,action_type TEXT,before_priority REAL DEFAULT 0,after_priority REAL DEFAULT 0,attention_score REAL DEFAULT 0,expected_gain REAL DEFAULT 0,outcome_score REAL DEFAULT 0,reason TEXT,details TEXT,created_at INTEGER DEFAULT 0)"""),
    ("gap_closure_attempts", """CREATE TABLE IF NOT EXISTS gap_closure_attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,gap_id INTEGER,gap_key TEXT,plan_key TEXT,before_resolution_score REAL DEFAULT 0,after_resolution_score REAL DEFAULT 0,before_priority REAL DEFAULT 0,after_priority REAL DEFAULT 0,closure_delta REAL DEFAULT 0,outcome TEXT,evidence_count INTEGER DEFAULT 0,strategy TEXT,neuromodulator_profile TEXT,details TEXT,created_at INTEGER DEFAULT 0)"""),
    ("context_expansion_memory", """CREATE TABLE IF NOT EXISTS context_expansion_memory(memory_key TEXT PRIMARY KEY,source_type TEXT,role TEXT,attempts INTEGER DEFAULT 0,avg_expected_gain REAL DEFAULT 0,avg_outcome_score REAL DEFAULT 0,avg_closure_delta REAL DEFAULT 0,persistent_pressure REAL DEFAULT 0,recommended_strategy TEXT,status TEXT DEFAULT 'observe',first_seen INTEGER DEFAULT 0,last_seen INTEGER DEFAULT 0,updated_at INTEGER DEFAULT 0,details TEXT)"""),
    ("phase5e_runtime_state", """CREATE TABLE IF NOT EXISTS phase5e_runtime_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)"""),
    ("phase5e_gap_closure_cycles", """CREATE TABLE IF NOT EXISTS phase5e_gap_closure_cycles(id INTEGER PRIMARY KEY AUTOINCREMENT,phase TEXT,gaps_considered INTEGER DEFAULT 0,plans_created INTEGER DEFAULT 0,actions_created INTEGER DEFAULT 0,closure_attempts INTEGER DEFAULT 0,avg_expected_gain REAL DEFAULT 0,avg_closure_delta REAL DEFAULT 0,facts INTEGER DEFAULT 0,relations INTEGER DEFAULT 0,questions INTEGER DEFAULT 0,safety_ok INTEGER DEFAULT 1,created_at INTEGER DEFAULT 0,details TEXT)""")]
    for t,ddl in ddls:
        before=_exists(db,t); db.execute(ddl)
        if not before: changes.append('create_table:'+t)
    future={
    'internal_learning_gaps': {'phase5e_context_expansion_score':'REAL DEFAULT 0','phase5e_expected_gain':'REAL DEFAULT 0','phase5e_closure_delta':'REAL DEFAULT 0','phase5e_closure_status':'TEXT','phase5e_context_window':'INTEGER DEFAULT 0','phase5e_plan_key':'TEXT','phase5e_last_expanded_at':'INTEGER DEFAULT 0','phase5e_expansion_attempts':'INTEGER DEFAULT 0','phase5e_recommended_strategy':'TEXT','phase5e_reason':'TEXT','resolution_score':'REAL DEFAULT 0','priority':'REAL DEFAULT 0','strategy_effectiveness_score':'REAL DEFAULT 0'},
    'internal_learning_questions': {'phase5e_context_expansion_score':'REAL DEFAULT 0','phase5e_expected_gain':'REAL DEFAULT 0','phase5e_closure_delta':'REAL DEFAULT 0','phase5e_closure_status':'TEXT','phase5e_plan_key':'TEXT','phase5e_last_expanded_at':'INTEGER DEFAULT 0','phase5e_recommended_strategy':'TEXT','resolution_score':'REAL DEFAULT 0','priority':'REAL DEFAULT 0'},
    'phase5b_internal_question_clusters': {'phase5e_context_expansion_score':'REAL DEFAULT 0','phase5e_expected_gain':'REAL DEFAULT 0','phase5e_closure_delta':'REAL DEFAULT 0','phase5e_closure_status':'TEXT','phase5e_plan_key':'TEXT','phase5e_last_expanded_at':'INTEGER DEFAULT 0','phase5e_recommended_strategy':'TEXT','resolution_score':'REAL DEFAULT 0'},
    'reading_queue': {'phase5e_priority':'REAL DEFAULT 0','phase5e_reason':'TEXT','phase5e_last_adjusted_at':'INTEGER DEFAULT 0','context_expansion_plan_key':'TEXT','gap_closure_boost':'REAL DEFAULT 0'},
    'chunk_attention_scores': {'phase5e_score':'REAL DEFAULT 0','phase5e_reason':'TEXT','phase5e_last_adjusted_at':'INTEGER DEFAULT 0','context_expansion_score':'REAL DEFAULT 0','gap_closure_boost':'REAL DEFAULT 0'},
    'context_hypotheses': {'phase5e_context_support_score':'REAL DEFAULT 0','phase5e_gap_closure_signal':'REAL DEFAULT 0','phase5e_last_context_expanded_at':'INTEGER DEFAULT 0','phase5e_reason':'TEXT'}}
    for t,cols in future.items():
        for c,s in cols.items():
            r=_addcol(db,t,c,s)
            if r: changes.append(r)
    for t,c in [('context_expansion_plans','plan_key'),('context_expansion_memory','memory_key'),('phase5e_runtime_state','key'),('internal_learning_gaps','gap_key'),('internal_learning_questions','question_key'),('reading_queue','chunk_id'),('chunk_attention_scores','chunk_id')]:
        r=_uix(db,t,c)
        if r: changes.append(r)
    now=_now()
    for k,v in {'phase':PHASE,'no_word_blacklists':'true','learning_mode':LEARNING_MODE,'fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only'}.items():
        db.execute('INSERT INTO phase5e_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(k,v,now))
    try: db.commit()
    except Exception: pass
    return {'status':'ok','phase':PHASE,'changes':changes,'no_word_blacklists':True,'fact_promotion':'disabled'}

def _neighbors(db, chunk_id, window=3):
    if not _exists(db,'chunks'): return []
    rows=db.execute('SELECT id FROM chunks WHERE id BETWEEN ? AND ? ORDER BY id',(max(1,int(chunk_id)-window),int(chunk_id)+window)).fetchall()
    return [r[0] for r in rows if r[0]!=chunk_id][:window*2]

def apply_context_expansion_and_gap_closure(mem=None, limit_gaps=80, neighbor_window=3):
    db=_db(mem); ensure_phase5e_schema(db); now=_now()
    facts,relations,questions=_cnt(db,'facts'),_cnt(db,'relations'),_cnt(db,'questions')
    if not _exists(db,'internal_learning_gaps'):
        return {'status':'skip','reason':'missing_internal_learning_gaps','phase':PHASE}
    rows=db.execute("""SELECT id,gap_key,gap_type,role,COALESCE(priority,0),COALESCE(resolution_score,0),COALESCE(strategy_effectiveness_score,0),COALESCE(uncertainty,0),COALESCE(pattern_key,''),COALESCE(hypothesis_id,0) FROM internal_learning_gaps WHERE COALESCE(status,'open') NOT IN ('closed','resolved') ORDER BY COALESCE(phase5e_expected_gain,0) DESC, COALESCE(priority,0) DESC, COALESCE(revision_pressure,0) DESC, id DESC LIMIT ?""",(limit_gaps,)).fetchall()
    plans=actions=attempts=0; total_gain=total_delta=0.0
    chunk_count=max(1,_cnt(db,'chunks'))
    for gid,gkey,gtype,role,priority,resolution,effectiveness,uncertainty,pattern_key,hid in rows:
        expected=max(0.05,min(1.0,(1-resolution)*0.45+priority*0.25+uncertainty*0.2+(1-effectiveness)*0.1))
        strategy='broaden_context_window' if expected>0.55 else 'observe_and_compare_context'
        plan_key=f'{gkey}:phase5e:{strategy}'
        db.execute("""INSERT INTO context_expansion_plans(plan_key,gap_id,gap_key,cluster_key,role,source_type,context_window,expansion_strategy,priority,expected_gain,neuromodulator_reason,status,evidence_count,attempts,last_action_at,created_at,updated_at,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(plan_key) DO UPDATE SET priority=excluded.priority,expected_gain=excluded.expected_gain,attempts=context_expansion_plans.attempts+1,last_action_at=excluded.last_action_at,updated_at=excluded.updated_at,status='open'""",(plan_key,gid,gkey,pattern_key,role,'internal_learning_gap',neighbor_window,strategy,priority,expected,'persistent_gap_pressure_and_context_need','open',1,1,now,now,now,_json({'gap_type':gtype,'resolution':resolution,'effectiveness':effectiveness,'uncertainty':uncertainty})))
        plans+=1; total_gain+=expected
        anchor=None
        if hid and _exists(db,'context_hypotheses') and 'chunk_id' in _cols(db,'context_hypotheses'):
            rr=db.execute('SELECT chunk_id FROM context_hypotheses WHERE id=?',(hid,)).fetchone(); anchor=rr[0] if rr else None
        if anchor is None: anchor=max(1,gid % chunk_count)
        neigh=_neighbors(db,anchor,neighbor_window) or [r[0] for r in db.execute('SELECT id FROM chunks WHERE id>? ORDER BY id LIMIT ?',(anchor,neighbor_window*2)).fetchall()] if _exists(db,'chunks') else []
        for nid in neigh[:6]:
            rr=db.execute('SELECT COALESCE(priority,0) FROM reading_queue WHERE chunk_id=?',(nid,)).fetchone() if _exists(db,'reading_queue') else None
            before=rr[0] if rr else 0.0
            after=max(before,min(0.92,0.45+expected*0.42)); attention=min(0.95,max(after,0.5+expected*0.4))
            db.execute("""INSERT INTO reading_queue(chunk_id,priority,reason,attention_score,read_count,status,last_read,updated_at,phase5e_priority,phase5e_reason,phase5e_last_adjusted_at,context_expansion_plan_key,gap_closure_boost) VALUES(?,?,?,?,0,'pending',0,?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET priority=MAX(reading_queue.priority,excluded.priority),attention_score=MAX(reading_queue.attention_score,excluded.attention_score),reason=excluded.reason,updated_at=excluded.updated_at,phase5e_priority=excluded.phase5e_priority,phase5e_reason=excluded.phase5e_reason,phase5e_last_adjusted_at=excluded.phase5e_last_adjusted_at,context_expansion_plan_key=excluded.context_expansion_plan_key,gap_closure_boost=excluded.gap_closure_boost""",(nid,after,'phase5e_context_expansion_gap_closure',attention,now,after,'phase5e_context_expansion_gap_closure',now,plan_key,expected))
            db.execute("""INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,reward_score,fatigue_score,last_reason,updated_at,phase5e_score,phase5e_reason,phase5e_last_adjusted_at,context_expansion_score,gap_closure_boost) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET attention_score=MAX(chunk_attention_scores.attention_score,excluded.attention_score),novelty_score=MAX(chunk_attention_scores.novelty_score,excluded.novelty_score),uncertainty_score=MAX(chunk_attention_scores.uncertainty_score,excluded.uncertainty_score),last_reason=excluded.last_reason,updated_at=excluded.updated_at,phase5e_score=excluded.phase5e_score,phase5e_reason=excluded.phase5e_reason,phase5e_last_adjusted_at=excluded.phase5e_last_adjusted_at,context_expansion_score=excluded.context_expansion_score,gap_closure_boost=excluded.gap_closure_boost""",(nid,attention,min(1.0,0.45+expected),min(1.0,0.25+uncertainty),min(0.8,effectiveness+0.1),0.05,'phase5e_context_expansion_gap_closure',now,attention,'phase5e_context_expansion_gap_closure',now,expected,expected))
            db.execute('INSERT INTO context_expansion_actions(plan_key,gap_id,gap_key,chunk_id,neighbor_chunk_id,direction,action_type,before_priority,after_priority,attention_score,expected_gain,outcome_score,reason,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(plan_key,gid,gkey,anchor,nid,'neighbor','prioritize_context_neighbor',before,after,attention,expected,0.0,'expand_context_around_gap',_json({'role':role,'gap_type':gtype}),now))
            actions+=1
        delta=max(0.0,min(1.0,expected*0.12+effectiveness*0.05-(1-resolution)*0.03)); after_res=min(1.0,resolution+delta); out='monitoring_gap' if after_res>0.45 else 'persistent_gap'
        db.execute('INSERT INTO gap_closure_attempts(gap_id,gap_key,plan_key,before_resolution_score,after_resolution_score,before_priority,after_priority,closure_delta,outcome,evidence_count,strategy,neuromodulator_profile,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(gid,gkey,plan_key,resolution,after_res,priority,max(0.1,priority*(1-delta*0.25)),delta,out,1,strategy,_json({'learning_mode':LEARNING_MODE}),_json({'expected_gain':expected,'effectiveness':effectiveness}),now))
        db.execute("""UPDATE internal_learning_gaps SET phase5e_context_expansion_score=?,phase5e_expected_gain=?,phase5e_closure_delta=?,phase5e_closure_status=?,phase5e_context_window=?,phase5e_plan_key=?,phase5e_last_expanded_at=?,phase5e_expansion_attempts=COALESCE(phase5e_expansion_attempts,0)+1,phase5e_recommended_strategy=?,phase5e_reason=? WHERE id=?""",(expected,expected,delta,out,neighbor_window,plan_key,now,strategy,'phase5e_context_expansion_and_gap_closure',gid))
        attempts+=1; total_delta+=delta
    avg_gain=total_gain/max(1,plans); avg_delta=total_delta/max(1,attempts)
    db.execute("""INSERT INTO context_expansion_memory(memory_key,source_type,role,attempts,avg_expected_gain,avg_outcome_score,avg_closure_delta,persistent_pressure,recommended_strategy,status,first_seen,last_seen,updated_at,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_key) DO UPDATE SET attempts=context_expansion_memory.attempts+excluded.attempts,avg_expected_gain=excluded.avg_expected_gain,avg_closure_delta=excluded.avg_closure_delta,persistent_pressure=excluded.persistent_pressure,recommended_strategy=excluded.recommended_strategy,last_seen=excluded.last_seen,updated_at=excluded.updated_at,details=excluded.details""",('global_context_expansion_gap_closure','global','all',attempts,avg_gain,0.0,avg_delta,1.0-avg_delta,'broaden_context_window','observe',now,now,now,_json({'plans':plans,'actions':actions})))
    for k,v in {'phase':PHASE,'no_word_blacklists':'true','learning_mode':LEARNING_MODE,'fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only','last_plans_created':str(plans),'last_actions_created':str(actions),'last_closure_attempts':str(attempts),'last_avg_expected_gain':str(round(avg_gain,6)),'last_avg_closure_delta':str(round(avg_delta,6))}.items():
        db.execute('INSERT INTO phase5e_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(k,v,now))
    db.execute('INSERT INTO phase5e_gap_closure_cycles(phase,gaps_considered,plans_created,actions_created,closure_attempts,avg_expected_gain,avg_closure_delta,facts,relations,questions,safety_ok,created_at,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(PHASE,len(rows),plans,actions,attempts,avg_gain,avg_delta,facts,relations,questions,1 if facts==relations==questions==0 else 0,now,_json({'no_word_blacklists':True})))
    try: db.commit()
    except Exception: pass
    return {'status':'phase5e_context_expansion_gap_closure_complete','phase':PHASE,'gaps_considered':len(rows),'plans_created':plans,'actions_created':actions,'closure_attempts':attempts,'avg_expected_gain':round(avg_gain,6),'avg_closure_delta':round(avg_delta,6),'facts':facts,'relations':relations,'questions':questions,'no_word_blacklists':True,'fact_promotion':'disabled'}

_orig_run=None; _orig_cycle=None

def managed_cycle(self, progress=None):
    base=None
    if _orig_cycle:
        try: base=_orig_cycle(self, progress)
        except TypeError: base=_orig_cycle(self)
    mem=getattr(self,'mem',None) or getattr(self,'memory',None) or getattr(self,'m',None) or self
    return {'phase':PHASE,'base':base,'phase5e_context_expansion':apply_context_expansion_and_gap_closure(mem),'direct_fact_writes':'disabled','direct_relation_writes':'disabled','fact_promotion':'disabled','question_generation':'internal_learning_questions_only','no_word_blacklists':True}

def managed_run(self, cycles=1, progress=None):
    return [managed_cycle(self, progress) for _ in range(int(cycles or 1))]

def patch_autonomous_loop(*args, **kwargs):
    global _orig_run,_orig_cycle
    try: from ki_system.autonomous import AutonomousLoop
    except Exception: return False
    if getattr(AutonomousLoop,'_phase5e_context_expansion_and_gap_closure_release',False): return True
    _orig_run=getattr(AutonomousLoop,'run',None); _orig_cycle=getattr(AutonomousLoop,'cycle',None)
    AutonomousLoop.run=managed_run; AutonomousLoop.cycle=managed_cycle
    vals={'phase5e_context_expansion_and_gap_closure_release':True,'_phase5e_context_expansion_and_gap_closure_release':True,'phase5d_integrated_observation_and_strategy_memory_release':True,'phase5b_integrated_strategy_refinement_release':True,'phase5a_integrated_self_improving_learning_release':True,'no_word_blacklists':True,'_no_word_blacklists':True,'learning_mode':LEARNING_MODE,'_learning_mode':LEARNING_MODE,'fact_promotion':'disabled','_fact_promotion':'disabled'}
    for k,v in vals.items(): setattr(AutonomousLoop,k,v)
    return True
try: patch_autonomous_loop()
except Exception as exc: print('[PHASE5E_AUTOLOAD_ERROR]', exc)
