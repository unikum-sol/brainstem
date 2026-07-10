
from __future__ import annotations
import sqlite3, time, json, traceback
PHASE="phase5h_schema_guard_fixed2"
REQUIRED={
"phase5g_strategy_experiments": {"experiment_key":"TEXT","gap_id":"INTEGER","gap_key":"TEXT","gap_type":"TEXT","role":"TEXT","source_chunk_id":"INTEGER","center_chunk_id":"INTEGER","target_chunk_id":"INTEGER","selected_strategy":"TEXT","strategy":"TEXT","window_strategy":"TEXT","window_radius":"INTEGER","read_status":"TEXT","before_score":"REAL DEFAULT 0","after_score":"REAL DEFAULT 0","closure_delta":"REAL DEFAULT 0","no_candidate_rate":"REAL DEFAULT 0","overlap_score":"REAL DEFAULT 0","strategy_score":"REAL DEFAULT 0","effectiveness_score":"REAL DEFAULT 0","outcome_score":"REAL DEFAULT 0","outcome":"TEXT","outcome_label":"TEXT","recommendation":"TEXT","phase5h_outcome_score":"REAL DEFAULT 0","phase5h_outcome_label":"TEXT","phase5h_last_evaluated_at":"INTEGER DEFAULT 0","phase5h_memory_key":"TEXT","phase5h_reason":"TEXT","details":"TEXT","created_at":"INTEGER DEFAULT 0","updated_at":"INTEGER DEFAULT 0"},
"phase5g_experiment_outcomes": {"outcome_key":"TEXT","experiment_key":"TEXT","experiment_id":"INTEGER","gap_id":"INTEGER","gap_key":"TEXT","gap_type":"TEXT","role":"TEXT","source_chunk_id":"INTEGER","center_chunk_id":"INTEGER","target_chunk_id":"INTEGER","selected_strategy":"TEXT","strategy":"TEXT","window_strategy":"TEXT","window_radius":"INTEGER","read_status":"TEXT","before_score":"REAL DEFAULT 0","after_score":"REAL DEFAULT 0","closure_delta":"REAL DEFAULT 0","no_candidate_rate":"REAL DEFAULT 0","no_candidate_penalty":"REAL DEFAULT 0","overlap_score":"REAL DEFAULT 0","strategy_score":"REAL DEFAULT 0","effectiveness_score":"REAL DEFAULT 0","outcome_score":"REAL DEFAULT 0","outcome":"TEXT","outcome_label":"TEXT","recommendation":"TEXT","learning_rate":"REAL DEFAULT 0","error_weight":"REAL DEFAULT 0","revision_pressure":"REAL DEFAULT 0","exploration_pressure":"REAL DEFAULT 0","inhibition_level":"REAL DEFAULT 0","consolidation_gain":"REAL DEFAULT 0","dopamine":"REAL DEFAULT 0","serotonin":"REAL DEFAULT 0","glutamate":"REAL DEFAULT 0","gaba":"REAL DEFAULT 0","noradrenaline":"REAL DEFAULT 0","acetylcholine":"REAL DEFAULT 0","evidence_count":"INTEGER DEFAULT 1","details":"TEXT","created_at":"INTEGER DEFAULT 0","updated_at":"INTEGER DEFAULT 0"},
"phase5g_strategy_selection_memory": {"memory_key":"TEXT","gap_type":"TEXT","role":"TEXT","selected_strategy":"TEXT","strategy":"TEXT","observations":"INTEGER DEFAULT 0","avg_closure_delta":"REAL DEFAULT 0","avg_no_candidate_rate":"REAL DEFAULT 0","avg_overlap_score":"REAL DEFAULT 0","avg_strategy_score":"REAL DEFAULT 0","avg_outcome_score":"REAL DEFAULT 0","success_count":"INTEGER DEFAULT 0","failure_count":"INTEGER DEFAULT 0","recommendation":"TEXT","neuromodulator_profile":"TEXT","details":"TEXT","created_at":"INTEGER DEFAULT 0","updated_at":"INTEGER DEFAULT 0"},
"phase5h_strategy_outcome_memory": {"memory_key":"TEXT","gap_type":"TEXT","role":"TEXT","selected_strategy":"TEXT","strategy":"TEXT","observations":"INTEGER DEFAULT 0","avg_outcome_score":"REAL DEFAULT 0","avg_closure_delta":"REAL DEFAULT 0","avg_no_candidate_rate":"REAL DEFAULT 0","avg_overlap_score":"REAL DEFAULT 0","avg_strategy_score":"REAL DEFAULT 0","success_count":"INTEGER DEFAULT 0","failure_count":"INTEGER DEFAULT 0","recommendation":"TEXT","created_at":"INTEGER DEFAULT 0","updated_at":"INTEGER DEFAULT 0"},
"phase5h_experiment_outcome_cycles": {"phase":"TEXT","experiments_seen":"INTEGER DEFAULT 0","outcomes_written":"INTEGER DEFAULT 0","memory_updates":"INTEGER DEFAULT 0","avg_outcome_score":"REAL DEFAULT 0","avg_closure_delta":"REAL DEFAULT 0","avg_no_candidate_rate":"REAL DEFAULT 0","avg_overlap_score":"REAL DEFAULT 0","facts":"INTEGER DEFAULT 0","relations":"INTEGER DEFAULT 0","questions":"INTEGER DEFAULT 0","created_at":"INTEGER DEFAULT 0"},
"phase5h_runtime_state": {"key":"TEXT","value":"TEXT","updated_at":"INTEGER DEFAULT 0"},
"internal_learning_gaps": {"phase5h_strategy_outcome_score":"REAL DEFAULT 0","phase5h_strategy_memory_key":"TEXT","phase5h_last_outcome_at":"INTEGER DEFAULT 0","phase5h_recommendation":"TEXT","phase5h_reason":"TEXT"},
"reading_queue": {"phase5h_strategy_outcome_score":"REAL DEFAULT 0","phase5h_strategy_memory_key":"TEXT","phase5h_last_outcome_at":"INTEGER DEFAULT 0","phase5h_recommendation":"TEXT","phase5h_reason":"TEXT"},
"chunk_attention_scores": {"phase5h_strategy_outcome_score":"REAL DEFAULT 0","phase5h_strategy_memory_key":"TEXT","phase5h_last_outcome_at":"INTEGER DEFAULT 0","phase5h_recommendation":"TEXT","phase5h_reason":"TEXT"}}
CREATE={"phase5g_strategy_experiments":"CREATE TABLE IF NOT EXISTS phase5g_strategy_experiments (id INTEGER PRIMARY KEY AUTOINCREMENT)","phase5g_experiment_outcomes":"CREATE TABLE IF NOT EXISTS phase5g_experiment_outcomes (id INTEGER PRIMARY KEY AUTOINCREMENT)","phase5g_strategy_selection_memory":"CREATE TABLE IF NOT EXISTS phase5g_strategy_selection_memory (memory_key TEXT PRIMARY KEY)","phase5h_strategy_outcome_memory":"CREATE TABLE IF NOT EXISTS phase5h_strategy_outcome_memory (memory_key TEXT PRIMARY KEY)","phase5h_experiment_outcome_cycles":"CREATE TABLE IF NOT EXISTS phase5h_experiment_outcome_cycles (id INTEGER PRIMARY KEY AUTOINCREMENT)","phase5h_runtime_state":"CREATE TABLE IF NOT EXISTS phase5h_runtime_state (key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)"}
def conn(o=None):
    if isinstance(o,sqlite3.Connection): return o,False
    if isinstance(o,str): return sqlite3.connect(o),True
    if o is not None:
        for a in ("conn","con","db","connection"):
            c=getattr(o,a,None)
            if isinstance(c,sqlite3.Connection): return c,False
        p=getattr(o,"path",None) or getattr(o,"db_path",None)
        if p: return sqlite3.connect(str(p)),True
    return sqlite3.connect("ki_memory.sqlite3"),True
def exists(cur,t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cols(cur,t): return {r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()} if exists(cur,t) else set()
def add(cur,t,c,d,ch):
    if exists(cur,t) and c not in cols(cur,t): cur.execute(f"ALTER TABLE {t} ADD COLUMN {c} {d}"); ch.append(f"add_column:{t}.{c}")
def ensure_phase5h_schema(o=None):
    db,cl=conn(o); cur=db.cursor(); ch=[]
    for t,s in CREATE.items():
        if not exists(cur,t): cur.execute(s); ch.append(f"create_table:{t}")
    for t,mp in REQUIRED.items():
        if exists(cur,t):
            for c,d in mp.items(): add(cur,t,c,d,ch)
    if exists(cur,"phase5g_strategy_experiments") and "experiment_key" in cols(cur,"phase5g_strategy_experiments"):
        cur.execute("UPDATE phase5g_strategy_experiments SET experiment_key='exp:'||rowid WHERE experiment_key IS NULL OR experiment_key='' ")
        if cur.rowcount: ch.append("backfill:phase5g_strategy_experiments.experiment_key")
    if exists(cur,"phase5g_experiment_outcomes") and "outcome_key" in cols(cur,"phase5g_experiment_outcomes"):
        cur.execute("UPDATE phase5g_experiment_outcomes SET outcome_key='out:'||COALESCE(experiment_key,id,rowid) WHERE outcome_key IS NULL OR outcome_key='' ")
        if cur.rowcount: ch.append("backfill:phase5g_experiment_outcomes.outcome_key")
    for t,c in [("phase5g_experiment_outcomes","outcome_key"),("phase5g_strategy_selection_memory","memory_key"),("phase5h_strategy_outcome_memory","memory_key"),("phase5h_runtime_state","key"),("internal_learning_gaps","gap_key"),("reading_queue","chunk_id"),("chunk_attention_scores","chunk_id")]:
        if exists(cur,t) and c in cols(cur,t):
            try: cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_{c}_phase5h_fixed2_unique ON {t}({c})"); ch.append(f"unique_index:{t}.{c}")
            except sqlite3.IntegrityError: ch.append(f"skip_unique_duplicates:{t}.{c}")
    n=int(time.time())
    for k,v in {"phase":PHASE,"no_word_blacklists":"true","fact_promotion":"disabled","direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_generation":"internal_learning_questions_only","learning_mode":"context_hypotheses_with_neuromodulators"}.items(): cur.execute("INSERT INTO phase5h_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,v,n))
    db.commit();
    if cl: db.close()
    return {"status":"ok","phase":PHASE,"changes":ch,"no_word_blacklists":True,"fact_promotion":"disabled"}
def count(cur,t): return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if exists(cur,t) else 0
def evaluate_strategy_experiment_outcomes(o=None,limit=1200):
    db,cl=conn(o); ensure_phase5h_schema(db); cur=db.cursor(); n=int(time.time())
    rows=cur.execute("""SELECT rowid,COALESCE(experiment_key,'exp:'||rowid),COALESCE(gap_id,0),COALESCE(gap_key,''),COALESCE(gap_type,'unknown'),COALESCE(role,'unknown'),COALESCE(source_chunk_id,center_chunk_id,0),COALESCE(center_chunk_id,source_chunk_id,0),COALESCE(target_chunk_id,0),COALESCE(selected_strategy,window_strategy,strategy,'unknown_strategy'),COALESCE(window_strategy,selected_strategy,strategy,'unknown_strategy'),COALESCE(window_radius,0),COALESCE(read_status,''),COALESCE(before_score,0),COALESCE(after_score,0),COALESCE(closure_delta,phase5h_outcome_score,outcome_score,0),COALESCE(no_candidate_rate,CASE WHEN read_status='read_no_candidate' THEN 1.0 ELSE 0.0 END),COALESCE(overlap_score,0.5),COALESCE(strategy_score,effectiveness_score,0) FROM phase5g_strategy_experiments ORDER BY rowid DESC LIMIT ?""",(limit,)).fetchall() if exists(cur,"phase5g_strategy_experiments") else []
    sums={}; outcomes=0
    for rowid,exp_key,gid,gkey,gt,role,src,center,target,sel,win,radius,read,before,after,closure,no,ov,ss in rows:
        closure=float(closure or 0); no=float(no or 0); ov=float(ov if ov is not None else 0.5); ss=float(ss or 0)
        score=max(0,min(1,0.45*closure+0.25*ss+0.20*(1-no)+0.10*(1-min(1,ov))))
        if score>=0.55: label,rec="effective_strategy","reinforce_strategy"
        elif no>0.6: label,rec="weak_no_candidate","dampen_or_shift_strategy"
        elif ov>0.85: label,rec="weak_high_overlap","seek_lower_overlap_or_contrastive_context"
        else: label,rec="observe_strategy","observe_and_compare_strategy"
        outkey=f"out:{exp_key}"; details=json.dumps({"source":PHASE,"safe":"no_facts_relations_questions"},ensure_ascii=False)
        cur.execute("""INSERT INTO phase5g_experiment_outcomes(outcome_key,experiment_key,experiment_id,gap_id,gap_key,gap_type,role,source_chunk_id,center_chunk_id,target_chunk_id,selected_strategy,strategy,window_strategy,window_radius,read_status,before_score,after_score,closure_delta,no_candidate_rate,no_candidate_penalty,overlap_score,strategy_score,effectiveness_score,outcome_score,outcome,outcome_label,recommendation,details,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(outcome_key) DO UPDATE SET outcome_score=excluded.outcome_score,outcome_label=excluded.outcome_label,recommendation=excluded.recommendation,closure_delta=excluded.closure_delta,no_candidate_rate=excluded.no_candidate_rate,overlap_score=excluded.overlap_score,strategy_score=excluded.strategy_score,effectiveness_score=excluded.effectiveness_score,updated_at=excluded.updated_at""",(outkey,exp_key,int(rowid),int(gid or 0),gkey,gt,role,int(src or 0),int(center or 0),int(target or 0),sel,sel,win,int(radius or 0),read,float(before or 0),float(after or 0),closure,no,no,ov,ss,ss,score,label,label,rec,details,n,n))
        cur.execute("UPDATE phase5g_strategy_experiments SET phase5h_outcome_score=?,phase5h_outcome_label=?,phase5h_last_evaluated_at=?,phase5h_memory_key=?,phase5h_reason=? WHERE rowid=?",(score,label,n,f"{gt}:{role}:{sel}",rec,rowid))
        outcomes+=1; key=(gt,role,sel); s=sums.setdefault(key,[0,0,0,0,0,0,0]); s[0]+=1; s[1]+=score; s[2]+=closure; s[3]+=no; s[4]+=ov; s[5]+=ss; s[6]+=1 if score>=0.55 else 0
    memupdates=0
    for (gt,role,sel),s in sums.items():
        c=s[0]; ao=s[1]/c; ac=s[2]/c; an=s[3]/c; av=s[4]/c; ast=s[5]/c; succ=int(s[6]); fail=c-succ
        rec="prefer_strategy_for_gap_role" if ao>=0.55 else ("avoid_no_candidate_strategy" if an>0.5 else ("reduce_overlap_before_reuse" if av>0.85 else "compare_with_alternative_strategy"))
        key=f"{gt}:{role}:{sel}"; prof=json.dumps({"learning_rate":0.234,"error_weight":0.407,"revision_pressure":0.312,"exploration_pressure":0.31,"inhibition_level":0.349},ensure_ascii=False)
        cur.execute("""INSERT INTO phase5g_strategy_selection_memory(memory_key,gap_type,role,selected_strategy,strategy,observations,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,avg_strategy_score,avg_outcome_score,success_count,failure_count,recommendation,neuromodulator_profile,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_key) DO UPDATE SET observations=excluded.observations,avg_closure_delta=excluded.avg_closure_delta,avg_no_candidate_rate=excluded.avg_no_candidate_rate,avg_overlap_score=excluded.avg_overlap_score,avg_strategy_score=excluded.avg_strategy_score,avg_outcome_score=excluded.avg_outcome_score,success_count=excluded.success_count,failure_count=excluded.failure_count,recommendation=excluded.recommendation,neuromodulator_profile=excluded.neuromodulator_profile,updated_at=excluded.updated_at""",(key,gt,role,sel,sel,c,ac,an,av,ast,ao,succ,fail,rec,prof,n,n))
        cur.execute("""INSERT INTO phase5h_strategy_outcome_memory(memory_key,gap_type,role,selected_strategy,strategy,observations,avg_outcome_score,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,avg_strategy_score,success_count,failure_count,recommendation,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_key) DO UPDATE SET observations=excluded.observations,avg_outcome_score=excluded.avg_outcome_score,avg_closure_delta=excluded.avg_closure_delta,avg_no_candidate_rate=excluded.avg_no_candidate_rate,avg_overlap_score=excluded.avg_overlap_score,avg_strategy_score=excluded.avg_strategy_score,success_count=excluded.success_count,failure_count=excluded.failure_count,recommendation=excluded.recommendation,updated_at=excluded.updated_at""",(key,gt,role,sel,sel,c,ao,ac,an,av,ast,succ,fail,rec,n,n))
        memupdates+=1
    total=max(1,sum(v[0] for v in sums.values())); avg=lambda i: sum(v[i] for v in sums.values())/total if sums else 0.0
    facts=count(cur,"facts"); relations=count(cur,"relations"); questions=count(cur,"questions")
    cur.execute("INSERT INTO phase5h_experiment_outcome_cycles(phase,experiments_seen,outcomes_written,memory_updates,avg_outcome_score,avg_closure_delta,avg_no_candidate_rate,avg_overlap_score,facts,relations,questions,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(PHASE,len(rows),outcomes,memupdates,avg(1),avg(2),avg(3),avg(4),facts,relations,questions,n))
    for k,v in {"phase":PHASE,"last_outcomes_written":str(outcomes),"last_memory_updates":str(memupdates),"last_avg_outcome_score":str(round(avg(1),6)),"last_avg_closure_delta":str(round(avg(2),6)),"last_avg_no_candidate_rate":str(round(avg(3),6)),"last_avg_overlap_score":str(round(avg(4),6)),"no_word_blacklists":"true","fact_promotion":"disabled","direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_generation":"internal_learning_questions_only","learning_mode":"context_hypotheses_with_neuromodulators"}.items(): cur.execute("INSERT INTO phase5h_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,v,n))
    db.commit();
    if cl: db.close()
    return {"status":"phase5h_strategy_outcome_learning_complete","phase":PHASE,"experiments_seen":len(rows),"outcomes_written":outcomes,"memory_updates":memupdates,"avg_outcome_score":round(avg(1),6),"avg_closure_delta":round(avg(2),6),"avg_no_candidate_rate":round(avg(3),6),"avg_overlap_score":round(avg(4),6),"facts":facts,"relations":relations,"questions":questions,"no_word_blacklists":True,"fact_promotion":"disabled"}
def managed_cycle(self,progress=None):
    base=None
    try:
        from ki_system import v8_phase5g_context_strategy_selection_and_experiment_memory_release as p5g
        if hasattr(p5g,"managed_cycle"): base=p5g.managed_cycle(self,progress)
    except Exception as e: base={"phase5g_call_error":str(e)}
    try: summ=evaluate_strategy_experiment_outcomes(getattr(self,"mem",None) or getattr(self,"memory",None) or self)
    except Exception as e: summ={"status":"phase5h_fixed2_error","error":str(e),"trace":traceback.format_exc()}
    return {"phase":PHASE,"base":base,"phase5h_fixed2_outcome_learning":summ}
def managed_run(self,cycles=1,progress=None):
    try: cycles=int(cycles or 1)
    except Exception: cycles=1
    out=[]
    for i in range(max(1,cycles)):
        if progress:
            try: progress(i+1,cycles)
            except Exception: pass
        out.append(managed_cycle(self,progress))
    return {"phase":PHASE,"cycles":len(out),"results":out}
def patch_autonomous_loop(*args,**kwargs):
    try:
        from ki_system.autonomous import AutonomousLoop
        AutonomousLoop.run=managed_run; AutonomousLoop.cycle=managed_cycle
        for k,v in {"phase5h_schema_guard_fixed2":True,"phase5h_strategy_experiment_outcome_learning_release":True,"no_word_blacklists":True,"learning_mode":"context_hypotheses_with_neuromodulators","fact_promotion":"disabled"}.items(): setattr(AutonomousLoop,k,v); setattr(AutonomousLoop,"_"+k,v)
        return True
    except Exception: return False
try: patch_autonomous_loop()
except Exception: pass
