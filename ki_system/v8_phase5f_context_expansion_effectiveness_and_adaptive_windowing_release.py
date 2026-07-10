# -*- coding: utf-8 -*-
"""Phase5f: context expansion effectiveness and adaptive windowing.
No word blacklists, no fact/relation/question writes.
"""
from __future__ import annotations
import sqlite3, time, json
from collections import Counter

PHASE = "phase5f_context_expansion_effectiveness_and_adaptive_windowing_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"
FACT_PROMOTION = "disabled"


def now(): return int(time.time())
def js(o):
    try: return json.dumps(o, ensure_ascii=False, sort_keys=True)
    except Exception: return json.dumps({"repr": repr(o)}, ensure_ascii=False)
def clamp(x, lo=0.0, hi=1.0):
    try: x=float(x)
    except Exception: x=0.0
    return max(lo, min(hi, x))

def con_from(obj=None):
    if isinstance(obj, sqlite3.Connection): return obj
    for a in ("mem","memory","m","store","memory_store","con","conn","connection","db","_con","_conn"):
        v = getattr(obj, a, None)
        if isinstance(v, sqlite3.Connection): return v
        if v is not None and v is not obj:
            try: return con_from(v)
            except Exception: pass
    return sqlite3.connect("ki_memory.sqlite3")

def table(cur,t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cols(cur,t): return [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()] if table(cur,t) else []
def count(cur,t): return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if table(cur,t) else 0

def addcol(cur,t,c,typ,changes):
    if table(cur,t) and c not in cols(cur,t):
        cur.execute(f"ALTER TABLE {t} ADD COLUMN {c} {typ}"); changes.append(f"add_column:{t}.{c}")

def uidx(cur,t,c,changes):
    if table(cur,t) and c in cols(cur,t):
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_{c}_phase5f_unique ON {t}({c})"); changes.append(f"unique_index:{t}.{c}")

def ensure_schema(db=None):
    con=con_from(db); cur=con.cursor(); changes=[]
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5f_window_strategy_memory(
        memory_key TEXT PRIMARY KEY, strategy_name TEXT, gap_type TEXT, role TEXT,
        observations INTEGER DEFAULT 0, avg_closure_delta REAL DEFAULT 0,
        avg_expected_gain REAL DEFAULT 0, read_no_candidate_rate REAL DEFAULT 0,
        avg_overlap_score REAL DEFAULT 0, avg_window_radius REAL DEFAULT 0,
        success_score REAL DEFAULT 0, recommendation TEXT, neuromodulator_profile TEXT,
        updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5f_adaptive_window_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, gap_id INTEGER, gap_key TEXT, gap_type TEXT,
        role TEXT, center_chunk_id INTEGER, old_window_radius INTEGER DEFAULT 0,
        new_window_radius INTEGER DEFAULT 0, old_strategy TEXT, new_strategy TEXT,
        closure_delta REAL DEFAULT 0, expected_gain REAL DEFAULT 0,
        read_no_candidate_rate REAL DEFAULT 0, overlap_score REAL DEFAULT 0,
        action TEXT, details TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5f_context_window_experiments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_key TEXT, gap_id INTEGER, gap_key TEXT,
        center_chunk_id INTEGER, target_chunk_id INTEGER, window_radius INTEGER DEFAULT 0,
        window_strategy TEXT, expected_gain REAL DEFAULT 0, closure_delta REAL DEFAULT 0,
        read_outcome TEXT, no_candidate_signal REAL DEFAULT 0, overlap_score REAL DEFAULT 0,
        experiment_score REAL DEFAULT 0, status TEXT DEFAULT 'active', details TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5f_effectiveness_cycles(
        id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT, gaps_considered INTEGER DEFAULT 0,
        experiments_created INTEGER DEFAULT 0, queue_updates INTEGER DEFAULT 0,
        avg_closure_delta REAL DEFAULT 0, avg_expected_gain REAL DEFAULT 0,
        avg_no_candidate_rate REAL DEFAULT 0, avg_overlap_score REAL DEFAULT 0,
        recommended_strategy TEXT, safety_ok INTEGER DEFAULT 1, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5f_runtime_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5f_read_outcome_memory(
        memory_key TEXT PRIMARY KEY, chunk_id INTEGER, observations INTEGER DEFAULT 0,
        read_candidate_count INTEGER DEFAULT 0, read_no_candidate_count INTEGER DEFAULT 0,
        read_no_candidate_rate REAL DEFAULT 0, avg_priority REAL DEFAULT 0,
        avg_attention_score REAL DEFAULT 0, recommendation TEXT, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5f_gap_window_state(
        gap_id INTEGER PRIMARY KEY, gap_key TEXT, current_window_radius INTEGER DEFAULT 3,
        current_window_strategy TEXT DEFAULT 'near_context_window', last_closure_delta REAL DEFAULT 0,
        last_no_candidate_rate REAL DEFAULT 0, last_overlap_score REAL DEFAULT 0,
        update_count INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reading_queue(
        chunk_id INTEGER PRIMARY KEY, priority REAL DEFAULT 0, reason TEXT, attention_score REAL DEFAULT 0,
        read_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', last_read INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chunk_attention_scores(
        chunk_id INTEGER PRIMARY KEY, attention_score REAL DEFAULT 0, novelty_score REAL DEFAULT 0,
        uncertainty_score REAL DEFAULT 0, reward_score REAL DEFAULT 0, fatigue_score REAL DEFAULT 0,
        last_reason TEXT, updated_at INTEGER DEFAULT 0)""")
    for t in ("internal_learning_gaps",):
        for c,typ in [("phase5f_window_radius","INTEGER DEFAULT 3"),("phase5f_window_strategy","TEXT"),("phase5f_window_effectiveness","REAL DEFAULT 0"),("phase5f_closure_delta","REAL DEFAULT 0"),("phase5f_no_candidate_rate","REAL DEFAULT 0"),("phase5f_overlap_score","REAL DEFAULT 0"),("phase5f_last_windowed_at","INTEGER DEFAULT 0"),("phase5f_window_reason","TEXT"),("phase5f_strategy_recommendation","TEXT"),("phase5f_experiment_count","INTEGER DEFAULT 0"),("priority","REAL DEFAULT 0"),("resolution_score","REAL DEFAULT 0"),("strategy_effectiveness_score","REAL DEFAULT 0"),("phase5e_closure_delta","REAL DEFAULT 0"),("phase5e_expected_gain","REAL DEFAULT 0")]: addcol(cur,t,c,typ,changes)
    for t in ("internal_learning_questions",):
        for c,typ in [("phase5f_window_strategy","TEXT"),("phase5f_window_radius","INTEGER DEFAULT 3"),("phase5f_resolution_score","REAL DEFAULT 0"),("phase5f_last_evaluated_at","INTEGER DEFAULT 0"),("phase5f_reason","TEXT"),("priority","REAL DEFAULT 0"),("resolution_score","REAL DEFAULT 0"),("cluster_key","TEXT")]: addcol(cur,t,c,typ,changes)
    for t in ("reading_queue",):
        for c,typ in [("phase5f_priority","REAL DEFAULT 0"),("phase5f_reason","TEXT"),("phase5f_last_adjusted_at","INTEGER DEFAULT 0"),("phase5f_window_strategy","TEXT"),("phase5f_window_radius","INTEGER DEFAULT 0"),("phase5f_no_candidate_penalty","REAL DEFAULT 0"),("active_learning_priority","REAL DEFAULT 0"),("cooldown_until","INTEGER DEFAULT 0")]: addcol(cur,t,c,typ,changes)
    for t in ("chunk_attention_scores",):
        for c,typ in [("phase5f_score","REAL DEFAULT 0"),("phase5f_reason","TEXT"),("phase5f_last_adjusted_at","INTEGER DEFAULT 0"),("phase5f_window_strategy","TEXT"),("phase5f_window_radius","INTEGER DEFAULT 0"),("phase5f_effectiveness_score","REAL DEFAULT 0"),("phase5f_read_outcome_score","REAL DEFAULT 0"),("phase5f_overlap_score","REAL DEFAULT 0"),("strategy_reason","TEXT"),("progress_adjusted_score","REAL DEFAULT 0")]: addcol(cur,t,c,typ,changes)
    for t in ("context_hypotheses",):
        for c,typ in [("phase5f_context_window_score","REAL DEFAULT 0"),("phase5f_window_strategy","TEXT"),("phase5f_last_windowed_at","INTEGER DEFAULT 0")]: addcol(cur,t,c,typ,changes)
    for t in ("context_expansion_plans", "context_expansion_actions", "gap_closure_attempts"):
        if table(cur,t):
            for c,typ in [("phase5f_effectiveness_score","REAL DEFAULT 0"),("phase5f_window_radius","INTEGER DEFAULT 3"),("phase5f_window_strategy","TEXT"),("phase5f_read_no_candidate_rate","REAL DEFAULT 0"),("phase5f_overlap_score","REAL DEFAULT 0"),("phase5f_next_action","TEXT"),("phase5f_last_evaluated_at","INTEGER DEFAULT 0"),("phase5f_reason","TEXT")]: addcol(cur,t,c,typ,changes)
    for t,c in [("phase5f_window_strategy_memory","memory_key"),("phase5f_read_outcome_memory","memory_key"),("phase5f_gap_window_state","gap_id"),("phase5f_runtime_state","key"),("reading_queue","chunk_id"),("chunk_attention_scores","chunk_id"),("internal_learning_gaps","gap_key"),("internal_learning_questions","question_key"),("context_expansion_plans","plan_key")]: uidx(cur,t,c,changes)
    n=now()
    for k,v in {"phase":PHASE,"no_word_blacklists":"true","learning_mode":LEARNING_MODE,"fact_promotion":FACT_PROMOTION,"direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_generation":"internal_learning_questions_only"}.items():
        cur.execute("INSERT INTO phase5f_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,v,n))
    con.commit(); return {"status":"ok","phase":PHASE,"changes":changes,"no_word_blacklists":True,"fact_promotion":FACT_PROMOTION}

def avg_from_table(cur,t,col,where="1=1"):
    if table(cur,t) and col in cols(cur,t):
        return float(cur.execute(f"SELECT AVG(COALESCE({col},0)) FROM {t} WHERE {where}").fetchone()[0] or 0)
    return 0.0

def neuromod(cur):
    vals={"learning_rate":0.234,"error_weight":0.407,"revision_pressure":0.312,"exploration_pressure":0.31,"inhibition_level":0.349,"consolidation_gain":0.297}
    for t in ("active_learning_loop_state","progress_evaluation_state","phase5a_integrated_runtime_state"):
        if table(cur,t) and {'key','value'}.issubset(set(cols(cur,t))):
            for k,v in cur.execute(f"SELECT key,value FROM {t}"):
                kk=str(k).replace('last_','')
                if kk in vals:
                    try: vals[kk]=float(str(v).strip().strip('\"').strip("'"))
                    except Exception: pass
    return vals

def selected_gaps(cur,limit=80):
    if not table(cur,"internal_learning_gaps"): return []
    c=cols(cur,"internal_learning_gaps")
    fields=[x for x in ['id','gap_key','gap_type','role','hypothesis_id','priority','resolution_score','strategy_effectiveness_score','phase5e_closure_delta','phase5e_expected_gain','phase5f_window_radius','phase5f_window_strategy'] if x in c]
    order=[]
    if 'phase5f_window_effectiveness' in c: order.append('COALESCE(phase5f_window_effectiveness,0) ASC')
    for x in ['priority','phase5e_expected_gain','strategy_effectiveness_score','uncertainty','severity']:
        if x in c: order.append(f'COALESCE({x},0) DESC')
    rows=cur.execute(f"SELECT {','.join(fields)} FROM internal_learning_gaps WHERE COALESCE(status,'open') NOT IN ('resolved','closed') ORDER BY {','.join(order) if order else 'id DESC'} LIMIT ?",(limit,)).fetchall()
    names=[d[0] for d in cur.description]
    return [dict(zip(names,r)) for r in rows]

def center_chunk(cur,g):
    hid=g.get('hypothesis_id')
    if hid and table(cur,'context_hypotheses') and 'chunk_id' in cols(cur,'context_hypotheses'):
        r=cur.execute('SELECT chunk_id FROM context_hypotheses WHERE id=?',(hid,)).fetchone()
        if r and r[0]: return int(r[0])
    if table(cur,'reading_queue'):
        r=cur.execute('SELECT chunk_id FROM reading_queue ORDER BY COALESCE(priority,0) DESC LIMIT 1').fetchone()
        if r: return int(r[0])
    return None

def closure_stats(cur,gap_key):
    d=e=0.0
    if table(cur,'gap_closure_attempts') and 'gap_key' in cols(cur,'gap_closure_attempts'):
        c=cols(cur,'gap_closure_attempts')
        dcol='closure_delta' if 'closure_delta' in c else None
        ecol='expected_gain' if 'expected_gain' in c else None
        sel=(f'AVG(COALESCE({dcol},0))' if dcol else '0')+','+(f'AVG(COALESCE({ecol},0))' if ecol else '0')
        r=cur.execute(f'SELECT {sel} FROM gap_closure_attempts WHERE gap_key=?',(gap_key,)).fetchone(); d=float(r[0] or 0); e=float(r[1] or 0)
    return d,e

def chunk_status(cur,ids):
    if not ids or not table(cur,'reading_queue'): return {}
    q=','.join('?' for _ in ids)
    return {int(r[0]):r[1] for r in cur.execute(f'SELECT chunk_id,status FROM reading_queue WHERE chunk_id IN ({q})',tuple(ids)).fetchall()}

def neighbors(cur,center,radius,strategy,maxn=6):
    if not center: return []
    offsets=[]
    if strategy in ('low_overlap_context_window','contrastive_context_window'):
        for d in range(radius,0,-2): offsets += [-d,d]
        for d in range(1,radius+1,2): offsets += [-d,d]
    else:
        for d in range(1,radius+1): offsets += [-d,d]
    cand=[]; seen=set()
    for off in offsets:
        cid=center+off
        if cid<=0 or cid in seen: continue
        seen.add(cid); cand.append(cid)
    if not cand: return []
    if not table(cur,'chunks'): return cand[:maxn]
    q=','.join('?' for _ in cand)
    existing=set(r[0] for r in cur.execute(f'SELECT id FROM chunks WHERE id IN ({q})',tuple(cand)).fetchall())
    out=[cid for cid in cand if cid in existing]
    return out[:maxn]

def apply_adaptive_windowing(db=None, limit=80):
    con=con_from(db); ensure_schema(con); cur=con.cursor(); n=now(); nm=neuromod(cur)
    gaps=selected_gaps(cur,limit); experiments=updates=0; ds=[]; es=[]; no_rates=[]; overlaps=[]; strategies=Counter()
    for g in gaps:
        gid=g.get('id'); gkey=g.get('gap_key') or f'gap:{gid}'; gt=g.get('gap_type') or 'unknown_gap'; role=g.get('role') or 'unknown_role'
        center=center_chunk(cur,g); delta,exp=closure_stats(cur,gkey); exp=float(g.get('phase5e_expected_gain') or exp or 0.5)
        old_r=int(g.get('phase5f_window_radius') or 3); old_s=g.get('phase5f_window_strategy') or 'near_context_window'
        pre=neighbors(cur,center,old_r,old_s); st=chunk_status(cur,pre); no=sum(1 for v in st.values() if v=='read_no_candidate')/max(1,len(pre))
        prev=0
        if table(cur,'phase5f_context_window_experiments') and pre:
            q=','.join('?' for _ in pre); prev=cur.execute(f'SELECT COUNT(*) FROM phase5f_context_window_experiments WHERE target_chunk_id IN ({q})',tuple(pre)).fetchone()[0]
        overlap=clamp(prev/max(1,len(pre)*5))
        if no>0.38: new_s='shift_away_from_no_candidate_context'; new_r=max(2,old_r-1); action='reduce_no_candidate_window'
        elif overlap>0.55: new_s='low_overlap_context_window'; new_r=min(9,old_r+2); action='reduce_overlap'
        elif delta<0.08: new_s='wider_context_window'; new_r=min(9,old_r+2); action='increase_window'
        elif delta<0.16: new_s='contrastive_context_window'; new_r=min(7,old_r+1); action='try_contrastive_window'
        else: new_s='reinforce_effective_window'; new_r=old_r; action='reinforce'
        if nm['inhibition_level']>0.42: new_r=min(new_r,old_r+1)
        if nm['exploration_pressure']>0.34: new_r=min(10,new_r+1)
        targets=neighbors(cur,center,new_r,new_s); st=chunk_status(cur,targets); no=sum(1 for v in st.values() if v=='read_no_candidate')/max(1,len(targets))
        if table(cur,'phase5f_context_window_experiments') and targets:
            q=','.join('?' for _ in targets); prev=cur.execute(f'SELECT COUNT(*) FROM phase5f_context_window_experiments WHERE target_chunk_id IN ({q})',tuple(targets)).fetchone()[0]
        overlap=clamp(prev/max(1,len(targets)*5)) if targets else overlap
        eff=clamp(0.45*delta+0.25*(1-no)+0.2*(1-overlap)+0.1*float(g.get('strategy_effectiveness_score') or 0))
        ds.append(delta); es.append(exp); no_rates.append(no); overlaps.append(overlap); strategies[new_s]+=1
        cur.execute('INSERT INTO phase5f_adaptive_window_events(gap_id,gap_key,gap_type,role,center_chunk_id,old_window_radius,new_window_radius,old_strategy,new_strategy,closure_delta,expected_gain,read_no_candidate_rate,overlap_score,action,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(gid,gkey,gt,role,center,old_r,new_r,old_s,new_s,delta,exp,no,overlap,action,js({'targets':targets,'neuromodulators':nm}),n))
        cur.execute('INSERT INTO phase5f_gap_window_state(gap_id,gap_key,current_window_radius,current_window_strategy,last_closure_delta,last_no_candidate_rate,last_overlap_score,update_count,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(gap_id) DO UPDATE SET current_window_radius=excluded.current_window_radius,current_window_strategy=excluded.current_window_strategy,last_closure_delta=excluded.last_closure_delta,last_no_candidate_rate=excluded.last_no_candidate_rate,last_overlap_score=excluded.last_overlap_score,update_count=phase5f_gap_window_state.update_count+1,updated_at=excluded.updated_at',(gid,gkey,new_r,new_s,delta,no,overlap,1,n))
        if table(cur,'internal_learning_gaps'):
            cur.execute('UPDATE internal_learning_gaps SET phase5f_window_radius=?, phase5f_window_strategy=?, phase5f_window_effectiveness=?, phase5f_closure_delta=?, phase5f_no_candidate_rate=?, phase5f_overlap_score=?, phase5f_last_windowed_at=?, phase5f_window_reason=?, phase5f_strategy_recommendation=?, phase5f_experiment_count=COALESCE(phase5f_experiment_count,0)+1 WHERE id=?',(new_r,new_s,eff,delta,no,overlap,n,action,new_s,gid))
        for t in targets:
            status=st.get(t,'pending'); nosig=1.0 if status=='read_no_candidate' else 0.0; score=clamp(0.5*exp+0.2*(1-nosig)+0.2*(1-overlap)+0.1*nm['exploration_pressure'])
            experiments+=1
            cur.execute('INSERT INTO phase5f_context_window_experiments(experiment_key,gap_id,gap_key,center_chunk_id,target_chunk_id,window_radius,window_strategy,expected_gain,closure_delta,read_outcome,no_candidate_signal,overlap_score,experiment_score,status,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'phase5f:{gid}:{t}:{new_s}',gid,gkey,center,t,new_r,new_s,exp,delta,status,nosig,overlap,score,'active',js({'action':action}),n))
            pri=clamp(score*(0.72 if nosig else 1.0))
            cur.execute("""
                INSERT INTO reading_queue(chunk_id,priority,reason,attention_score,read_count,status,last_read,updated_at,phase5f_priority,phase5f_reason,phase5f_last_adjusted_at,phase5f_window_strategy,phase5f_window_radius,phase5f_no_candidate_penalty)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    priority=CASE WHEN COALESCE(reading_queue.status,'pending')='read_no_candidate' THEN MIN(COALESCE(reading_queue.priority,0.5),excluded.priority) ELSE MAX(COALESCE(reading_queue.priority,0.5),excluded.priority) END,
                    reason=excluded.reason,
                    attention_score=CASE WHEN COALESCE(reading_queue.status,'pending')='read_no_candidate' THEN MIN(COALESCE(reading_queue.attention_score,0.5),excluded.attention_score) ELSE MAX(COALESCE(reading_queue.attention_score,0.5),excluded.attention_score) END,
                    updated_at=excluded.updated_at,
                    phase5f_priority=excluded.phase5f_priority,
                    phase5f_reason=excluded.phase5f_reason,
                    phase5f_last_adjusted_at=excluded.phase5f_last_adjusted_at,
                    phase5f_window_strategy=excluded.phase5f_window_strategy,
                    phase5f_window_radius=excluded.phase5f_window_radius,
                    phase5f_no_candidate_penalty=excluded.phase5f_no_candidate_penalty
            """, (t,pri,'phase5f_adaptive_windowing',score,0,'pending',0,n,pri,PHASE,n,new_s,new_r,nosig))
            cur.execute("""
                INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,reward_score,fatigue_score,last_reason,updated_at,phase5f_score,phase5f_reason,phase5f_last_adjusted_at,phase5f_window_strategy,phase5f_window_radius,phase5f_effectiveness_score,phase5f_read_outcome_score,phase5f_overlap_score)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    attention_score=MAX(COALESCE(chunk_attention_scores.attention_score,0),excluded.attention_score),
                    novelty_score=MAX(COALESCE(chunk_attention_scores.novelty_score,0),excluded.novelty_score),
                    reward_score=MAX(COALESCE(chunk_attention_scores.reward_score,0),excluded.reward_score),
                    last_reason=excluded.last_reason,
                    updated_at=excluded.updated_at,
                    phase5f_score=excluded.phase5f_score,
                    phase5f_reason=excluded.phase5f_reason,
                    phase5f_last_adjusted_at=excluded.phase5f_last_adjusted_at,
                    phase5f_window_strategy=excluded.phase5f_window_strategy,
                    phase5f_window_radius=excluded.phase5f_window_radius,
                    phase5f_effectiveness_score=excluded.phase5f_effectiveness_score,
                    phase5f_read_outcome_score=excluded.phase5f_read_outcome_score,
                    phase5f_overlap_score=excluded.phase5f_overlap_score
            """, (t,score,clamp(1-overlap),0.5,clamp(delta+0.25),clamp(nosig*0.4),PHASE,n,score,PHASE,n,new_s,new_r,eff,clamp(1-nosig),overlap))
            updates+=1
        mem=f'{gt}:{role}:{new_s}'
        cur.execute('INSERT INTO phase5f_window_strategy_memory(memory_key,strategy_name,gap_type,role,observations,avg_closure_delta,avg_expected_gain,read_no_candidate_rate,avg_overlap_score,avg_window_radius,success_score,recommendation,neuromodulator_profile,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(memory_key) DO UPDATE SET observations=phase5f_window_strategy_memory.observations+1, avg_closure_delta=(phase5f_window_strategy_memory.avg_closure_delta*phase5f_window_strategy_memory.observations+excluded.avg_closure_delta)/MAX(1,phase5f_window_strategy_memory.observations+1), avg_expected_gain=(phase5f_window_strategy_memory.avg_expected_gain*phase5f_window_strategy_memory.observations+excluded.avg_expected_gain)/MAX(1,phase5f_window_strategy_memory.observations+1), read_no_candidate_rate=(phase5f_window_strategy_memory.read_no_candidate_rate*phase5f_window_strategy_memory.observations+excluded.read_no_candidate_rate)/MAX(1,phase5f_window_strategy_memory.observations+1), avg_overlap_score=(phase5f_window_strategy_memory.avg_overlap_score*phase5f_window_strategy_memory.observations+excluded.avg_overlap_score)/MAX(1,phase5f_window_strategy_memory.observations+1), avg_window_radius=(phase5f_window_strategy_memory.avg_window_radius*phase5f_window_strategy_memory.observations+excluded.avg_window_radius)/MAX(1,phase5f_window_strategy_memory.observations+1), success_score=(phase5f_window_strategy_memory.success_score*phase5f_window_strategy_memory.observations+excluded.success_score)/MAX(1,phase5f_window_strategy_memory.observations+1), recommendation=excluded.recommendation, neuromodulator_profile=excluded.neuromodulator_profile, updated_at=excluded.updated_at',(mem,new_s,gt,role,1,delta,exp,no,overlap,new_r,eff,'reinforce_window' if eff>0.55 else 'shift_or_observe',js(nm),n))
    avg=lambda xs: sum(xs)/len(xs) if xs else 0.0
    rec=strategies.most_common(1)[0][0] if strategies else 'observe'
    safety=(count(cur,'facts')==0 and count(cur,'relations')==0 and count(cur,'questions')==0)
    cur.execute('INSERT INTO phase5f_effectiveness_cycles(phase,gaps_considered,experiments_created,queue_updates,avg_closure_delta,avg_expected_gain,avg_no_candidate_rate,avg_overlap_score,recommended_strategy,safety_ok,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(PHASE,len(gaps),experiments,updates,avg(ds),avg(es),avg(no_rates),avg(overlaps),rec,1 if safety else 0,n))
    state={'phase':PHASE,'last_gaps_considered':len(gaps),'last_experiments_created':experiments,'last_queue_updates':updates,'last_avg_closure_delta':round(avg(ds),6),'last_avg_expected_gain':round(avg(es),6),'last_avg_no_candidate_rate':round(avg(no_rates),6),'last_avg_overlap_score':round(avg(overlaps),6),'last_recommended_strategy':rec,'last_safety_ok':str(bool(safety)).lower(),'no_word_blacklists':'true','fact_promotion':FACT_PROMOTION,'learning_mode':LEARNING_MODE,'question_generation':'internal_learning_questions_only','direct_fact_writes':'disabled','direct_relation_writes':'disabled'}
    for k,v in state.items(): cur.execute('INSERT INTO phase5f_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(k,str(v),n))
    con.commit()
    return {'status':'phase5f_adaptive_windowing_complete','phase':PHASE,'gaps_considered':len(gaps),'experiments_created':experiments,'queue_updates':updates,'avg_closure_delta':round(avg(ds),6),'avg_expected_gain':round(avg(es),6),'avg_no_candidate_rate':round(avg(no_rates),6),'avg_overlap_score':round(avg(overlaps),6),'recommended_strategy':rec,'no_word_blacklists':True,'fact_promotion':FACT_PROMOTION,'facts':count(cur,'facts'),'relations':count(cur,'relations'),'questions':count(cur,'questions')}

def managed_cycle(self, progress=None):
    base=None
    try:
        from ki_system import v8_phase5e_context_expansion_and_gap_closure_release as p5e
        if hasattr(p5e,'managed_cycle'): base=p5e.managed_cycle(self, progress)
    except Exception as e: base={'phase5e_error':repr(e)}
    res=apply_adaptive_windowing(self)
    if progress:
        try: progress(1,1)
        except Exception: pass
    return {'phase':PHASE,'base':base,'phase5f':res}

def managed_run(self, cycles=1, progress=None):
    try: cycles=int(cycles or 1)
    except Exception: cycles=1
    cycles=max(1,min(cycles,50)); out=[]
    for _ in range(cycles): out.append(managed_cycle(self,progress))
    return {'phase':PHASE,'cycles':cycles,'results':out}

def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AutonomousLoop
    AutonomousLoop.cycle=managed_cycle; AutonomousLoop.run=managed_run
    for n in ['phase5f_context_expansion_effectiveness_and_adaptive_windowing_release','_phase5f_context_expansion_effectiveness_and_adaptive_windowing_release','no_word_blacklists','_no_word_blacklists']:
        setattr(AutonomousLoop,n,True)
    AutonomousLoop.learning_mode=LEARNING_MODE; AutonomousLoop._learning_mode=LEARNING_MODE
    AutonomousLoop.fact_promotion=FACT_PROMOTION; AutonomousLoop._fact_promotion=FACT_PROMOTION
    return AutonomousLoop
try:
    from ki_system.autonomous import AutonomousLoop as _AL
    patch_autonomous_loop(_AL)
except Exception:
    pass
