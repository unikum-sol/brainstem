
from __future__ import annotations
import sqlite3, time, os, json
from collections import Counter, defaultdict
PHASE='phase4l_gap_cluster_planning_and_strategy_balance'
_PREV_RUN=None
_PREV_CYCLE=None

def now(): return int(time.time())
def j(x): return json.dumps(x, ensure_ascii=False, sort_keys=True)
def db_path(mem=None):
    if mem:
        for a in ('db_path','database_path','path'):
            v=getattr(mem,a,None)
            if v: return str(v)
        c=getattr(mem,'conn',None)
        if c:
            try:
                r=c.execute('PRAGMA database_list').fetchone()
                if r and r[2]: return r[2]
            except Exception: pass
    return 'ki_memory.sqlite3'
def mem_of(loop):
    for a in ('mem','memory','m','store'):
        if hasattr(loop,a): return getattr(loop,a)
    return None
def con(mem=None):
    c=sqlite3.connect(db_path(mem)); c.row_factory=sqlite3.Row; return c
def exists(db,t): return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cols(db,t): return {r[1] for r in db.execute(f'PRAGMA table_info({t})').fetchall()} if exists(db,t) else set()
def addcol(db,t,c,typ):
    if c not in cols(db,t): db.execute(f'ALTER TABLE {t} ADD COLUMN {c} {typ}'); return True
    return False
def uidx(db,t,c):
    if exists(db,t) and c in cols(db,t):
        try: db.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_{c}_phase4l_unique ON {t}({c})'); return True
        except Exception: return False
    return False

def ensure_schema(db):
    ch=[]
    db.execute("CREATE TABLE IF NOT EXISTS gap_clusters(cluster_key TEXT PRIMARY KEY,gap_type TEXT,role TEXT,member_count INTEGER DEFAULT 0,avg_priority REAL DEFAULT 0,avg_severity REAL DEFAULT 0,avg_uncertainty REAL DEFAULT 0,avg_stability REAL DEFAULT 0,exploration_pressure REAL DEFAULT 0,exploitation_pressure REAL DEFAULT 0,strategy TEXT DEFAULT 'observe',status TEXT DEFAULT 'open',cooldown_until INTEGER DEFAULT 0,details TEXT,created_at INTEGER DEFAULT 0,updated_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS gap_cluster_members(id INTEGER PRIMARY KEY AUTOINCREMENT,cluster_key TEXT,gap_id INTEGER,question_id INTEGER,weight REAL DEFAULT 0,role TEXT,gap_type TEXT,created_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS reread_cooldowns(chunk_id INTEGER PRIMARY KEY,cooldown_until INTEGER DEFAULT 0,reason TEXT,pressure REAL DEFAULT 0,source_cluster TEXT,updated_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS strategy_balance_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS exploration_exploitation_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT,exploration_pressure REAL DEFAULT 0,exploitation_pressure REAL DEFAULT 0,inhibition_level REAL DEFAULT 0,affected_clusters INTEGER DEFAULT 0,affected_chunks INTEGER DEFAULT 0,details TEXT,created_at INTEGER DEFAULT 0)")
    for t,c in [('gap_clusters','cluster_key'),('reread_cooldowns','chunk_id'),('strategy_balance_state','key'),('reading_queue','chunk_id'),('chunk_attention_scores','chunk_id'),('attention_queue_state','key'),('reading_strategy_state','key')]:
        if uidx(db,t,c): ch.append('unique_index:%s.%s'%(t,c))
    return ch

def state(db,k,v):
    if exists(db,'strategy_balance_state'):
        db.execute('INSERT INTO strategy_balance_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(k,str(v),now()))

def f(row,*names,default=None):
    ks=row.keys()
    for n in names:
        if n in ks and row[n] is not None: return row[n]
    return default

def neuro(db):
    d={'learning_rate':0.234,'error_weight':0.407,'revision_pressure':0.312,'exploration_pressure':0.31,'inhibition_level':0.349}
    if exists(db,'neuromodulator_learning_state'):
        cs=cols(db,'neuromodulator_learning_state')
        try:
            r=db.execute('SELECT * FROM neuromodulator_learning_state ORDER BY id DESC LIMIT 1').fetchone()
            if r:
                for k in d:
                    if k in cs and r[k] is not None: d[k]=float(r[k])
        except Exception: pass
    return d

def cluster_gaps(db, limit=300):
    ensure_schema(db); nstate=neuro(db); groups=defaultdict(list)
    if not exists(db,'internal_learning_gaps'): return {'clusters':0,'members':0,'neuro':nstate}
    cs=cols(db,'internal_learning_gaps'); order='id DESC' if 'id' in cs else 'rowid DESC'
    where="WHERE status IS NULL OR status IN ('open','internal_open','active')" if 'status' in cs else ''
    for r in db.execute(f'SELECT rowid as rid,* FROM internal_learning_gaps {where} ORDER BY {order} LIMIT ?', (limit,)):
        gt=str(f(r,'gap_type','type','question_type',default='unknown_gap'))
        role=str(f(r,'role','dominant_role','from_role',default='unknown_role'))
        sev=float(f(r,'severity','priority','score','confidence',default=0.5) or 0.5)
        unc=float(f(r,'uncertainty','avg_uncertainty','error_weight',default=0.5) or 0.5)
        stab=float(f(r,'stability','avg_stability',default=max(0,1-unc)) or 0)
        groups[gt+'|'+role].append((f(r,'id','rid'),gt,role,sev,unc,stab))
    total=0; ts=now()
    for ck,items in groups.items():
        m=len(items); gt=items[0][1]; role=items[0][2]
        asev=sum(x[3] for x in items)/m; aunc=sum(x[4] for x in items)/m; astab=sum(x[5] for x in items)/m
        explore=min(1, nstate['exploration_pressure']+0.03*max(0,m-3)+0.1*(1-astab)); exploit=min(1,0.3+0.35*asev+0.25*aunc+0.1*nstate['error_weight'])
        strategy='targeted_reread' if exploit>explore+0.08 else ('diversify_context' if explore>exploit+0.08 else 'balanced_reread')
        db.execute('INSERT INTO gap_clusters(cluster_key,gap_type,role,member_count,avg_priority,avg_severity,avg_uncertainty,avg_stability,exploration_pressure,exploitation_pressure,strategy,status,details,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(cluster_key) DO UPDATE SET member_count=excluded.member_count,avg_priority=excluded.avg_priority,avg_severity=excluded.avg_severity,avg_uncertainty=excluded.avg_uncertainty,avg_stability=excluded.avg_stability,exploration_pressure=excluded.exploration_pressure,exploitation_pressure=excluded.exploitation_pressure,strategy=excluded.strategy,status=excluded.status,details=excluded.details,updated_at=excluded.updated_at',(ck,gt,role,m,asev,asev,aunc,astab,explore,exploit,strategy,'open',j({'neuro':nstate}),ts,ts))
        for it in items[:40]: db.execute('INSERT INTO gap_cluster_members(cluster_key,gap_id,weight,role,gap_type,created_at) VALUES(?,?,?,?,?,?)',(ck,it[0],it[3],role,gt,ts))
        total+=m
    return {'clusters':len(groups),'members':total,'neuro':nstate}

def chunk_counts(db):
    cnt=Counter()
    for t in ('gap_driven_rereading_actions','rereading_candidate_links'):
        if exists(db,t):
            cs=cols(db,t); cc='chunk_id' if 'chunk_id' in cs else ('candidate_chunk_id' if 'candidate_chunk_id' in cs else None)
            if cc:
                try:
                    for r in db.execute(f'SELECT {cc} cid,COUNT(*) n FROM {t} WHERE {cc} IS NOT NULL GROUP BY {cc} ORDER BY n DESC LIMIT 500'):
                        cnt[int(r['cid'])]+=int(r['n'])
                except Exception: pass
    return cnt

def apply_strategy_balance(db):
    ensure_schema(db); build=cluster_gaps(db); ts=now(); ns=build.get('neuro',neuro(db)); cd=0; div=0
    for cid,n in chunk_counts(db).most_common(200):
        if n>=4:
            pressure=min(1,0.2+n/20); db.execute('INSERT INTO reread_cooldowns(chunk_id,cooldown_until,reason,pressure,source_cluster,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET cooldown_until=excluded.cooldown_until,reason=excluded.reason,pressure=excluded.pressure,updated_at=excluded.updated_at',(cid,ts+int(300+600*pressure),'phase4l_repeated_reread_cooldown',pressure,'repeated_chunk_selection',ts)); cd+=1
            if exists(db,'reading_queue'):
                try: db.execute("UPDATE reading_queue SET priority=MIN(priority,0.62),attention_score=MIN(attention_score,0.66),reason='phase4l_cooldown_balance',updated_at=? WHERE chunk_id=? AND status='pending'",(ts,cid))
                except Exception: pass
    if exists(db,'reading_queue'):
        try:
            score=round(0.5+0.12*ns.get('exploration_pressure',0.31),3)
            for r in db.execute("SELECT chunk_id FROM reading_queue WHERE status='pending' ORDER BY priority ASC, chunk_id ASC LIMIT 80"):
                db.execute("UPDATE reading_queue SET priority=MAX(priority,?),attention_score=MAX(attention_score,?),reason='phase4l_strategy_balance_exploration',updated_at=? WHERE chunk_id=?",(score,score,ts,int(r['chunk_id']))); div+=1
        except Exception: pass
    db.execute('INSERT INTO exploration_exploitation_events(event_type,exploration_pressure,exploitation_pressure,inhibition_level,affected_clusters,affected_chunks,details,created_at) VALUES(?,?,?,?,?,?,?,?)',('phase4l_strategy_balance',ns.get('exploration_pressure',0.31),ns.get('error_weight',0.407),ns.get('inhibition_level',0.349),build['clusters'],cd+div,j({'cooldowns':cd,'diversified':div}),ts))
    for k,v in {'phase':PHASE,'no_word_blacklists':'true','fact_promotion':'disabled','question_generation':'internal_learning_questions_only','last_clusters':build['clusters'],'last_cluster_members':build['members'],'last_cooldowns':cd,'last_diversified_chunks':div}.items(): state(db,k,v)
    return {'status':'phase4l_strategy_balance_complete','clusters':build['clusters'],'members':build['members'],'cooldowns':cd,'diversified_chunks':div,'no_word_blacklists':True,'fact_promotion':'disabled'}

def managed_cycle(self,progress=None):
    mem=mem_of(self); res=_PREV_CYCLE(self,progress) if _PREV_CYCLE else {'status':'phase4l_no_previous_cycle'}
    try:
        db=con(mem); summary=apply_strategy_balance(db); db.commit(); db.close()
    except Exception as e: summary={'status':'phase4l_error','error':repr(e)}
    if isinstance(res,dict): res['phase4l_gap_cluster_planning_and_strategy_balance']=summary; return res
    return {'status':'phase4l_wrapped_cycle','previous':res,'phase4l_gap_cluster_planning_and_strategy_balance':summary}

def managed_run(self,cycles=1,progress=None):
    mem=mem_of(self); res=_PREV_RUN(self,cycles,progress) if _PREV_RUN else [managed_cycle(self,progress) for _ in range(cycles or 1)]
    try:
        db=con(mem); summary=apply_strategy_balance(db); db.commit(); db.close()
    except Exception as e: summary={'status':'phase4l_error','error':repr(e)}
    if isinstance(res,list): res.append({'status':'phase4l_post_run_strategy_balance','phase4l_gap_cluster_planning_and_strategy_balance':summary}); return res
    if isinstance(res,dict): res['phase4l_post_run_strategy_balance']=summary; return res
    return {'status':'phase4l_wrapped_run','previous':res,'phase4l_post_run_strategy_balance':summary}

def patch_autonomous_loop(AutonomousLoop):
    global _PREV_RUN,_PREV_CYCLE
    if getattr(AutonomousLoop,'_phase4l_gap_cluster_planning_and_strategy_balance',False): return AutonomousLoop
    _PREV_RUN=getattr(AutonomousLoop,'run',None); _PREV_CYCLE=getattr(AutonomousLoop,'cycle',None)
    AutonomousLoop.run=managed_run; AutonomousLoop.cycle=managed_cycle
    for name in ('phase4l_gap_cluster_planning_and_strategy_balance','phase4k_gap_driven_rereading_and_learning_strategy','phase4j_internal_learning_questions_and_gap_detection','phase4i_long_term_memory_and_pattern_stability','phase4h_self_evaluation_and_revision_core','phase4g_neuromodulated_learning_control'):
        setattr(AutonomousLoop,name,True); setattr(AutonomousLoop,'_'+name,True)
    AutonomousLoop.no_word_blacklists=True; AutonomousLoop._no_word_blacklists=True
    AutonomousLoop.learning_mode='context_hypotheses_with_neuromodulators'; AutonomousLoop._rollback_learning_mode='context_hypotheses_with_neuromodulators'; AutonomousLoop.fact_promotion='disabled'; AutonomousLoop._fact_promotion='disabled'
    return AutonomousLoop
