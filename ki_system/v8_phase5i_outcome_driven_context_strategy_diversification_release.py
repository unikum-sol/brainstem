
import sqlite3, time, json
from collections import Counter
PHASE='phase5i_outcome_driven_context_strategy_diversification_release'
def n(): return int(time.time())
def j(o):
    try: return json.dumps(o,ensure_ascii=False,sort_keys=True)
    except Exception: return '{}'
def c01(x):
    try: x=float(x)
    except Exception: x=0.0
    return max(0.0,min(1.0,x))
def db_of(o=None):
    if o is not None:
        for a in ('mem','memory','m','store','memory_store','db'):
            if hasattr(o,a): o=getattr(o,a); break
        if hasattr(o,'execute') and hasattr(o,'commit'): return o,False
        for a in ('conn','con','db','connection'):
            x=getattr(o,a,None)
            if x is not None and hasattr(x,'execute'): return x,False
        for a in ('db_path','path','filename'):
            x=getattr(o,a,None)
            if x: return sqlite3.connect(str(x)),True
    return sqlite3.connect('ki_memory.sqlite3'),True
def ex(db,t): return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cols(db,t): return [r[1] for r in db.execute('PRAGMA table_info(%s)'%t).fetchall()] if ex(db,t) else []
def add(db,t,col,decl,changes):
    if ex(db,t) and col not in cols(db,t):
        db.execute('ALTER TABLE %s ADD COLUMN %s %s'%(t,col,decl)); changes.append('add_column:%s.%s'%(t,col))
def uidx(db,t,col,changes):
    if ex(db,t) and col in cols(db,t):
        try:
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_%s_%s_phase5i_unique ON %s(%s)'%(t,col,t,col)); changes.append('unique_index:%s.%s'%(t,col))
        except sqlite3.IntegrityError: changes.append('skip_unique_duplicates:%s.%s'%(t,col))
def count(db,t): return db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(db,t) else 0

def ensure_schema(obj=None):
    db,close=db_of(obj); changes=[]
    try:
        db.execute("CREATE TABLE IF NOT EXISTS phase5i_diversification_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER)")
        db.execute("CREATE TABLE IF NOT EXISTS phase5i_strategy_diversification_cycles(id INTEGER PRIMARY KEY AUTOINCREMENT,phase TEXT,experiments_seen INTEGER DEFAULT 0,outcome_memory_rows INTEGER DEFAULT 0,gaps_considered INTEGER DEFAULT 0,experiments_created INTEGER DEFAULT 0,queue_updates INTEGER DEFAULT 0,avg_outcome_score REAL DEFAULT 0,avg_closure_delta REAL DEFAULT 0,avg_overlap_score REAL DEFAULT 0,avg_no_candidate_rate REAL DEFAULT 0,selected_main_strategy TEXT,safety_ok INTEGER DEFAULT 1,created_at INTEGER)")
        db.execute("CREATE TABLE IF NOT EXISTS phase5i_outcome_driven_experiments(id INTEGER PRIMARY KEY AUTOINCREMENT,experiment_key TEXT,gap_id INTEGER,gap_key TEXT,gap_type TEXT,role TEXT,center_chunk_id INTEGER,target_chunk_id INTEGER,selected_strategy TEXT,previous_strategy TEXT,strategy_score REAL DEFAULT 0,expected_outcome_score REAL DEFAULT 0,expected_closure_delta REAL DEFAULT 0,expected_overlap_score REAL DEFAULT 0,expected_no_candidate_rate REAL DEFAULT 0,learning_rate REAL DEFAULT 0,error_weight REAL DEFAULT 0,revision_pressure REAL DEFAULT 0,exploration_pressure REAL DEFAULT 0,inhibition_level REAL DEFAULT 0,consolidation_gain REAL DEFAULT 0,dopamine REAL DEFAULT 0,serotonin REAL DEFAULT 0,glutamate REAL DEFAULT 0,gaba REAL DEFAULT 0,noradrenaline REAL DEFAULT 0,acetylcholine REAL DEFAULT 0,reason TEXT,details TEXT,created_at INTEGER,updated_at INTEGER)")
        db.execute("CREATE TABLE IF NOT EXISTS phase5i_strategy_diversification_memory(memory_key TEXT PRIMARY KEY,gap_type TEXT,role TEXT,strategy TEXT,observations INTEGER DEFAULT 0,avg_outcome_score REAL DEFAULT 0,avg_closure_delta REAL DEFAULT 0,avg_overlap_score REAL DEFAULT 0,avg_no_candidate_rate REAL DEFAULT 0,success_score REAL DEFAULT 0,failure_pressure REAL DEFAULT 0,recommendation TEXT,neuromodulator_profile TEXT,updated_at INTEGER)")
        db.execute("CREATE TABLE IF NOT EXISTS phase5i_neuromodulated_selection_events(id INTEGER PRIMARY KEY AUTOINCREMENT,gap_id INTEGER,gap_type TEXT,role TEXT,selected_strategy TEXT,selection_reason TEXT,learning_rate REAL DEFAULT 0,error_weight REAL DEFAULT 0,revision_pressure REAL DEFAULT 0,exploration_pressure REAL DEFAULT 0,inhibition_level REAL DEFAULT 0,consolidation_gain REAL DEFAULT 0,outcome_memory_score REAL DEFAULT 0,created_at INTEGER)")
        db.execute("CREATE TABLE IF NOT EXISTS reading_queue(chunk_id INTEGER PRIMARY KEY,priority REAL DEFAULT 0,reason TEXT,attention_score REAL DEFAULT 0,read_count INTEGER DEFAULT 0,status TEXT DEFAULT 'pending',last_read INTEGER,updated_at INTEGER)")
        db.execute("CREATE TABLE IF NOT EXISTS chunk_attention_scores(chunk_id INTEGER PRIMARY KEY,attention_score REAL DEFAULT 0,novelty_score REAL DEFAULT 0,uncertainty_score REAL DEFAULT 0,reward_score REAL DEFAULT 0,fatigue_score REAL DEFAULT 0,last_reason TEXT,updated_at INTEGER)")
        spec={
          'internal_learning_gaps': {'phase5i_selected_strategy':'TEXT','phase5i_strategy_score':'REAL DEFAULT 0','phase5i_expected_outcome_score':'REAL DEFAULT 0','phase5i_expected_closure_delta':'REAL DEFAULT 0','phase5i_expected_overlap_score':'REAL DEFAULT 0','phase5i_expected_no_candidate_rate':'REAL DEFAULT 0','phase5i_experiment_count':'INTEGER DEFAULT 0','phase5i_last_selected_at':'INTEGER','phase5i_reason':'TEXT','phase5i_memory_key':'TEXT','phase5i_diversification_pressure':'REAL DEFAULT 0','phase5i_outcome_memory_score':'REAL DEFAULT 0','priority':'REAL DEFAULT 0','resolution_score':'REAL DEFAULT 0','strategy_effectiveness_score':'REAL DEFAULT 0','learning_outcome_score':'REAL DEFAULT 0'},
          'reading_queue': {'phase5i_priority':'REAL DEFAULT 0','phase5i_selected_strategy':'TEXT','phase5i_strategy_score':'REAL DEFAULT 0','phase5i_expected_outcome_score':'REAL DEFAULT 0','phase5i_expected_closure_delta':'REAL DEFAULT 0','phase5i_expected_overlap_score':'REAL DEFAULT 0','phase5i_expected_no_candidate_rate':'REAL DEFAULT 0','phase5i_last_adjusted_at':'INTEGER','phase5i_reason':'TEXT','active_learning_priority':'REAL DEFAULT 0','cooldown_until':'INTEGER DEFAULT 0'},
          'chunk_attention_scores': {'phase5i_score':'REAL DEFAULT 0','phase5i_selected_strategy':'TEXT','phase5i_strategy_score':'REAL DEFAULT 0','phase5i_expected_outcome_score':'REAL DEFAULT 0','phase5i_expected_closure_delta':'REAL DEFAULT 0','phase5i_expected_overlap_score':'REAL DEFAULT 0','phase5i_expected_no_candidate_rate':'REAL DEFAULT 0','phase5i_last_adjusted_at':'INTEGER','phase5i_reason':'TEXT'},
          'phase5g_experiment_outcomes': {'outcome_key':'TEXT','experiment_key':'TEXT','gap_id':'INTEGER','gap_key':'TEXT','gap_type':'TEXT','role':'TEXT','center_chunk_id':'INTEGER','source_chunk_id':'INTEGER','target_chunk_id':'INTEGER','selected_strategy':'TEXT','window_strategy':'TEXT','strategy':'TEXT','window_radius':'INTEGER DEFAULT 0','read_status':'TEXT','closure_delta':'REAL DEFAULT 0','no_candidate_rate':'REAL DEFAULT 0','no_candidate_penalty':'REAL DEFAULT 0','overlap_score':'REAL DEFAULT 0','strategy_score':'REAL DEFAULT 0','effectiveness_score':'REAL DEFAULT 0','outcome_score':'REAL DEFAULT 0','outcome_label':'TEXT','recommendation':'TEXT','learning_rate':'REAL DEFAULT 0','error_weight':'REAL DEFAULT 0','revision_pressure':'REAL DEFAULT 0','exploration_pressure':'REAL DEFAULT 0','inhibition_level':'REAL DEFAULT 0','consolidation_gain':'REAL DEFAULT 0','dopamine':'REAL DEFAULT 0','serotonin':'REAL DEFAULT 0','glutamate':'REAL DEFAULT 0','gaba':'REAL DEFAULT 0','noradrenaline':'REAL DEFAULT 0','acetylcholine':'REAL DEFAULT 0','evidence_count':'INTEGER DEFAULT 0','details':'TEXT','created_at':'INTEGER','updated_at':'INTEGER','phase5i_memory_used':'INTEGER DEFAULT 0'},
          'phase5g_strategy_selection_memory': {'memory_key':'TEXT','gap_type':'TEXT','role':'TEXT','strategy':'TEXT','observations':'INTEGER DEFAULT 0','avg_outcome_score':'REAL DEFAULT 0','avg_closure_delta':'REAL DEFAULT 0','avg_no_candidate_rate':'REAL DEFAULT 0','avg_overlap_score':'REAL DEFAULT 0','avg_strategy_score':'REAL DEFAULT 0','recommendation':'TEXT','neuromodulator_profile':'TEXT','updated_at':'INTEGER','phase5i_diversification_score':'REAL DEFAULT 0','phase5i_last_used_at':'INTEGER','phase5i_recommendation':'TEXT'}
        }
        for t,mp in spec.items():
            for col,decl in mp.items(): add(db,t,col,decl,changes)
        for t,col in [('phase5i_diversification_state','key'),('phase5i_strategy_diversification_memory','memory_key'),('phase5g_experiment_outcomes','outcome_key'),('phase5g_strategy_selection_memory','memory_key'),('internal_learning_gaps','gap_key'),('reading_queue','chunk_id'),('chunk_attention_scores','chunk_id')]: uidx(db,t,col,changes)
        ts=n()
        for k,v in {'phase':PHASE,'no_word_blacklists':'true','learning_mode':'context_hypotheses_with_neuromodulators','fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only'}.items(): db.execute('INSERT OR REPLACE INTO phase5i_diversification_state VALUES(?,?,?)',(k,v,ts))
        db.commit(); return {'status':'ok','phase':PHASE,'changes':changes,'no_word_blacklists':True,'fact_promotion':'disabled'}
    finally:
        if close: db.close()

def maxchunk(db):
    if ex(db,'chunks') and 'id' in cols(db,'chunks'):
        r=db.execute('SELECT MAX(id) FROM chunks').fetchone();
        if r and r[0]: return int(r[0])
    r=db.execute('SELECT MAX(chunk_id) FROM reading_queue').fetchone(); return int((r and r[0]) or 100000)
def ctrls(db): return {'learning_rate':0.234,'error_weight':0.407,'revision_pressure':0.312,'exploration_pressure':0.31,'inhibition_level':0.349,'consolidation_gain':0.297}
def build_memory(db):
    vals=ctrls(db); updates=0; total=0; ao=ac=av=an=0.0
    if ex(db,'phase5g_experiment_outcomes') and {'gap_type','role'}.issubset(set(cols(db,'phase5g_experiment_outcomes'))):
        rows=db.execute("SELECT COALESCE(gap_type,'unknown'),COALESCE(role,'unknown'),COALESCE(selected_strategy,window_strategy,strategy,'unknown_strategy'),COUNT(*),AVG(COALESCE(outcome_score,effectiveness_score,0)),AVG(COALESCE(closure_delta,0)),AVG(COALESCE(overlap_score,0)),AVG(COALESCE(no_candidate_rate,no_candidate_penalty,0)) FROM phase5g_experiment_outcomes GROUP BY 1,2,3").fetchall()
        total=sum(int(r[3] or 0) for r in rows)
        if total:
            ao=sum((r[4] or 0)*r[3] for r in rows)/total; ac=sum((r[5] or 0)*r[3] for r in rows)/total; av=sum((r[6] or 0)*r[3] for r in rows)/total; an=sum((r[7] or 0)*r[3] for r in rows)/total
        for gt,role,strat,obs,out,clo,ov,noc in rows:
            out=float(out or 0); clo=float(clo or 0); ov=float(ov or 0); noc=float(noc or 0); obs=int(obs or 0); succ=c01(.45*out+.35*clo+.15*(1-ov)+.05*(1-noc)); fail=c01(.5*ov+.35*noc+.15*(1-clo)); rec='reinforce_strategy' if succ>.55 else ('shift_farther_and_reduce_overlap' if ov>.75 else 'observe_and_compare'); key=f'{gt}:{role}:{strat}'
            db.execute("INSERT INTO phase5i_strategy_diversification_memory VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_key) DO UPDATE SET observations=excluded.observations,avg_outcome_score=excluded.avg_outcome_score,avg_closure_delta=excluded.avg_closure_delta,avg_overlap_score=excluded.avg_overlap_score,avg_no_candidate_rate=excluded.avg_no_candidate_rate,success_score=excluded.success_score,failure_pressure=excluded.failure_pressure,recommendation=excluded.recommendation,neuromodulator_profile=excluded.neuromodulator_profile,updated_at=excluded.updated_at",(key,gt,role,strat,obs,out,clo,ov,noc,succ,fail,rec,j(vals),n()))
            if ex(db,'phase5g_strategy_selection_memory'):
                db.execute("INSERT INTO phase5g_strategy_selection_memory(memory_key,gap_type,role,strategy,observations,avg_outcome_score,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,avg_strategy_score,recommendation,neuromodulator_profile,updated_at,phase5i_diversification_score,phase5i_last_used_at,phase5i_recommendation) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_key) DO UPDATE SET observations=excluded.observations,avg_outcome_score=excluded.avg_outcome_score,avg_closure_delta=excluded.avg_closure_delta,avg_no_candidate_rate=excluded.avg_no_candidate_rate,avg_overlap_score=excluded.avg_overlap_score,avg_strategy_score=excluded.avg_strategy_score,recommendation=excluded.recommendation,neuromodulator_profile=excluded.neuromodulator_profile,updated_at=excluded.updated_at,phase5i_diversification_score=excluded.phase5i_diversification_score,phase5i_last_used_at=excluded.phase5i_last_used_at,phase5i_recommendation=excluded.phase5i_recommendation",(key,gt,role,strat,obs,out,clo,noc,ov,succ,rec,j(vals),n(),succ,n(),rec))
            updates+=1
    return updates,(total,ao,ac,av,an)
def choose(db,gt,role,res):
    r=db.execute('SELECT strategy,avg_closure_delta,avg_overlap_score,avg_no_candidate_rate,success_score FROM phase5i_strategy_diversification_memory WHERE gap_type=? AND role=? ORDER BY success_score DESC,observations DESC LIMIT 1',(gt,role)).fetchone()
    if r:
        s,cl,ov,nc,su=r; cl=float(cl or 0); ov=float(ov or 0); nc=float(nc or 0)
        if ov>.85 and cl<=.02: return 'far_low_overlap_context_window'
        if nc>.35: return 'avoid_no_candidate_neighbors'
        if float(res or 0)<.08 and s in ('contrastive_context_window','low_overlap_context_window'): return 'far_low_overlap_context_window'
        return s
    return 'far_low_overlap_context_window'
def center(db,g):
    gid,gkey,gt,role,hid=g[:5]
    if hid and ex(db,'context_hypotheses') and 'id' in cols(db,'context_hypotheses') and 'chunk_id' in cols(db,'context_hypotheses'):
        r=db.execute('SELECT chunk_id FROM context_hypotheses WHERE id=?',(hid,)).fetchone()
        if r and r[0]: return int(r[0])
    return max(1,int(gid or 1)%max(2,maxchunk(db)))
def offs(s,seed):
    mp={'far_low_overlap_context_window':[25,-25,50,-50],'avoid_no_candidate_neighbors':[20,-20,35,-35],'cross_role_contrastive_context_window':[15,-15,45,-45],'section_shift_context_window':[30,60,-30,-60]}; b=mp.get(s,[18,-18,36,-36]); z=int(seed)%7; return [x+(z if x>0 else -z) for x in b]
def apply_diversification(obj=None,limit_gaps=120):
    db,close=db_of(obj)
    try:
        ensure_schema(db); vals=ctrls(db); mem,stats=build_memory(db); total,ao,ac,av,an=stats; ts=n(); gaps=[]
        if ex(db,'internal_learning_gaps'):
            gaps=db.execute("SELECT id,COALESCE(gap_key,''),COALESCE(gap_type,'unknown'),COALESCE(role,'unknown'),hypothesis_id,COALESCE(priority,0),COALESCE(resolution_score,0),COALESCE(strategy_effectiveness_score,0) FROM internal_learning_gaps WHERE COALESCE(status,'open') NOT IN ('closed','resolved') ORDER BY COALESCE(priority,0) DESC, COALESCE(resolution_score,0) ASC, id DESC LIMIT ?",(limit_gaps,)).fetchall()
        created=q=0; mc=maxchunk(db); dist=Counter()
        for g in gaps:
            gid,gkey,gt,role,hid,prio,res,eff=g; cen=center(db,g); strat=choose(db,gt,role,res); dist[strat]+=1
            m=db.execute('SELECT AVG(avg_closure_delta),AVG(avg_overlap_score),AVG(avg_no_candidate_rate),AVG(success_score) FROM phase5i_strategy_diversification_memory WHERE gap_type=? AND role=?',(gt,role)).fetchone(); mcl=float((m and m[0]) or 0); mov=float((m and m[1]) or 0); mno=float((m and m[2]) or 0); msu=float((m and m[3]) or 0)
            score=c01(.28+.35*(1-mov)+.25*msu+.12*vals['exploration_pressure']); out=c01(.35*msu+.25*(1-mov)+.2*(1-mno)+.2*vals['exploration_pressure']); clo=c01(max(mcl,.03 if strat.startswith('far') else .01)+.05*(1-mov)); att=c01(.45+.25*out+.2*float(prio or 0)+.1*vals['revision_pressure'])
            for off in offs(strat,gid):
                tgt=cen+off
                if tgt<=0 or tgt>mc: continue
                db.execute('INSERT INTO phase5i_outcome_driven_experiments(experiment_key,gap_id,gap_key,gap_type,role,center_chunk_id,target_chunk_id,selected_strategy,strategy_score,expected_outcome_score,expected_closure_delta,expected_overlap_score,expected_no_candidate_rate,learning_rate,error_weight,revision_pressure,exploration_pressure,inhibition_level,consolidation_gain,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,reason,details,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'phase5i:{gid}:{strat}:{cen}:{tgt}:{ts}',gid,gkey,gt,role,cen,tgt,strat,score,out,clo,mov,mno,vals['learning_rate'],vals['error_weight'],vals['revision_pressure'],vals['exploration_pressure'],vals['inhibition_level'],vals['consolidation_gain'],.5,.4,vals['exploration_pressure'],vals['inhibition_level'],vals['revision_pressure'],.5,'phase5i_outcome_driven_strategy_diversification',j({'offset':off}),ts,ts))
                db.execute("INSERT INTO reading_queue(chunk_id,priority,reason,attention_score,read_count,status,updated_at,phase5i_priority,phase5i_selected_strategy,phase5i_strategy_score,phase5i_expected_outcome_score,phase5i_expected_closure_delta,phase5i_expected_overlap_score,phase5i_expected_no_candidate_rate,phase5i_last_adjusted_at,phase5i_reason) VALUES(?,?,?,?,0,'pending',?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET priority=MAX(COALESCE(reading_queue.priority,0),excluded.priority),attention_score=MAX(COALESCE(reading_queue.attention_score,0),excluded.attention_score),reason=excluded.reason,updated_at=excluded.updated_at,phase5i_priority=excluded.phase5i_priority,phase5i_selected_strategy=excluded.phase5i_selected_strategy,phase5i_strategy_score=excluded.phase5i_strategy_score,phase5i_expected_outcome_score=excluded.phase5i_expected_outcome_score,phase5i_expected_closure_delta=excluded.phase5i_expected_closure_delta,phase5i_expected_overlap_score=excluded.phase5i_expected_overlap_score,phase5i_expected_no_candidate_rate=excluded.phase5i_expected_no_candidate_rate,phase5i_last_adjusted_at=excluded.phase5i_last_adjusted_at,phase5i_reason=excluded.phase5i_reason",(tgt,att,'phase5i_outcome_driven_strategy_diversification',att,ts,att,strat,score,out,clo,mov,mno,ts,'phase5i_outcome_driven_strategy_diversification'))
                db.execute("INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,reward_score,fatigue_score,last_reason,updated_at,phase5i_score,phase5i_selected_strategy,phase5i_strategy_score,phase5i_expected_outcome_score,phase5i_expected_closure_delta,phase5i_expected_overlap_score,phase5i_expected_no_candidate_rate,phase5i_last_adjusted_at,phase5i_reason) VALUES(?,?,?,?,?,?,?, ?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET attention_score=MAX(COALESCE(chunk_attention_scores.attention_score,0),excluded.attention_score),phase5i_score=excluded.phase5i_score,phase5i_selected_strategy=excluded.phase5i_selected_strategy,phase5i_strategy_score=excluded.phase5i_strategy_score,phase5i_expected_outcome_score=excluded.phase5i_expected_outcome_score,phase5i_expected_closure_delta=excluded.phase5i_expected_closure_delta,phase5i_expected_overlap_score=excluded.phase5i_expected_overlap_score,phase5i_expected_no_candidate_rate=excluded.phase5i_expected_no_candidate_rate,phase5i_last_adjusted_at=excluded.phase5i_last_adjusted_at,phase5i_reason=excluded.phase5i_reason,last_reason=excluded.last_reason,updated_at=excluded.updated_at",(tgt,att,.72,.55,out,mno,'phase5i_outcome_driven_strategy_diversification',ts,att,strat,score,out,clo,mov,mno,ts,'phase5i_outcome_driven_strategy_diversification'))
                created+=1; q+=1
            db.execute('UPDATE internal_learning_gaps SET phase5i_selected_strategy=?,phase5i_strategy_score=?,phase5i_expected_outcome_score=?,phase5i_expected_closure_delta=?,phase5i_expected_overlap_score=?,phase5i_expected_no_candidate_rate=?,phase5i_last_selected_at=?,phase5i_reason=?,phase5i_memory_key=?,phase5i_diversification_pressure=?,phase5i_outcome_memory_score=?,phase5i_experiment_count=COALESCE(phase5i_experiment_count,0)+1 WHERE id=?',(strat,score,out,clo,mov,mno,ts,'phase5i_outcome_driven_strategy_diversification',f'{gt}:{role}:{strat}',c01(1-msu),msu,gid))
        safety=count(db,'facts')==0 and count(db,'relations')==0 and count(db,'questions')==0; main=dist.most_common(1)[0][0] if dist else 'none'
        db.execute('INSERT INTO phase5i_strategy_diversification_cycles(phase,experiments_seen,outcome_memory_rows,gaps_considered,experiments_created,queue_updates,avg_outcome_score,avg_closure_delta,avg_overlap_score,avg_no_candidate_rate,selected_main_strategy,safety_ok,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(PHASE,total,mem,len(gaps),created,q,ao,ac,av,an,main,1 if safety else 0,ts))
        state={'phase':PHASE,'no_word_blacklists':'true','learning_mode':'context_hypotheses_with_neuromodulators','fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'internal_learning_questions_only','last_experiments_seen':str(total),'last_memory_updates':str(mem),'last_gaps_considered':str(len(gaps)),'last_experiments_created':str(created),'last_queue_updates':str(q),'last_avg_outcome_score':str(round(ao,6)),'last_avg_closure_delta':str(round(ac,6)),'last_avg_overlap_score':str(round(av,6)),'last_avg_no_candidate_rate':str(round(an,6)),'last_selected_main_strategy':main,'last_strategy_distribution':j(dist),'last_safety_ok':str(bool(safety)).lower()}
        for k,v in state.items(): db.execute('INSERT OR REPLACE INTO phase5i_diversification_state VALUES(?,?,?)',(k,v,ts))
        db.commit(); return {'status':'phase5i_outcome_driven_strategy_diversification_complete','phase':PHASE,'experiments_seen':total,'memory_updates':mem,'gaps_considered':len(gaps),'experiments_created':created,'queue_updates':q,'avg_outcome_score':round(ao,6),'avg_closure_delta':round(ac,6),'avg_overlap_score':round(av,6),'avg_no_candidate_rate':round(an,6),'selected_main_strategy':main,'strategy_distribution':dict(dist),'facts':count(db,'facts'),'relations':count(db,'relations'),'questions':count(db,'questions'),'no_word_blacklists':True,'fact_promotion':'disabled'}
    finally:
        if close: db.close()
def managed_cycle(self,progress=None):
    base=None
    try:
        from ki_system import v8_phase5h_strategy_experiment_outcome_learning_release as b
        base=b.managed_cycle(self,progress)
    except Exception as e: base={'base_warning':repr(e)}
    return {'phase':PHASE,'base':base,'phase5i':apply_diversification(self)}
def managed_run(self,cycles=1,progress=None):
    out=[]
    try: cycles=int(cycles)
    except Exception: cycles=1
    for _ in range(max(1,cycles)): out.append(managed_cycle(self,progress))
    return {'phase':PHASE,'cycles':out}
def patch_autonomous_loop(*args,**kwargs):
    try: from ki_system.autonomous import AutonomousLoop
    except Exception:
        if not args: return False
        AutonomousLoop=args[0]
    AutonomousLoop.cycle=managed_cycle; AutonomousLoop.run=managed_run
    for x in ['phase5i_outcome_driven_context_strategy_diversification_release','phase5h_strategy_experiment_outcome_learning_release','phase5g_context_strategy_selection_and_experiment_memory_release','no_word_blacklists']:
        setattr(AutonomousLoop,x,True); setattr(AutonomousLoop,'_'+x,True)
    AutonomousLoop.learning_mode='context_hypotheses_with_neuromodulators'; AutonomousLoop.fact_promotion='disabled'
    return True
try: patch_autonomous_loop()
except Exception as e: print('[PHASE5I_AUTOLOAD_ERROR]',e)
