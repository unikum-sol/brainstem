
# V8-phase5c_learning_outcome_closure_and_question_cluster_resolution
# Integrated, no blacklist, no fact/relation/question writes.
import os, sqlite3, time, json

PHASE = "phase5c_learning_outcome_closure_and_question_cluster_resolution"

def _now(): return int(time.time())
def _json(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True)
def _connect(): return sqlite3.connect('ki_memory.sqlite3')

def _conn_from_memory(mem):
    if mem is None: return _connect(), True
    for name in ('conn','con','db','connection'):
        c=getattr(mem,name,None)
        if c is not None and hasattr(c,'execute'): return c, False
    for name in ('db_path','path','database_path'):
        p=getattr(mem,name,None)
        if p: return sqlite3.connect(str(p)), True
    return _connect(), True

def _memory_from_loop(loop):
    for name in ('mem','memory','m','store','memory_store'):
        v=getattr(loop,name,None)
        if v is not None: return v
    return None

def _table_exists(cur, table):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _cols(cur, table):
    if not _table_exists(cur, table): return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]

def _add_col(cur, table, col, spec, changes):
    if not _table_exists(cur, table): return
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {spec}")
        changes.append(f"add_column:{table}.{col}")

def _safe_unique(cur, table, col, changes):
    if not _table_exists(cur, table) or col not in _cols(cur, table): return
    dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} WHERE {col} IS NOT NULL GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
    if dup:
        changes.append(f"skip_unique_duplicates:{table}.{col}")
        return
    idx=f"idx_{table}_{col}_phase5c_unique"
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
    changes.append(f"unique_index:{table}.{col}")

def ensure_schema(mem=None):
    db, own = _conn_from_memory(mem); cur = db.cursor(); changes=[]
    cur.execute("""CREATE TABLE IF NOT EXISTS question_cluster_resolution_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, cluster_key TEXT, question_type TEXT, role TEXT,
        question_count INTEGER DEFAULT 0, open_count INTEGER DEFAULT 0, improved_count INTEGER DEFAULT 0,
        persistent_count INTEGER DEFAULT 0, avg_priority REAL DEFAULT 0, avg_resolution_score REAL DEFAULT 0,
        avg_strategy_effectiveness REAL DEFAULT 0, avg_learning_outcome REAL DEFAULT 0,
        before_status TEXT, after_status TEXT, decision TEXT, details TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS learning_outcome_closure_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, target_type TEXT, target_key TEXT, target_id INTEGER,
        before_priority REAL DEFAULT 0, after_priority REAL DEFAULT 0, resolution_score REAL DEFAULT 0,
        strategy_effectiveness_score REAL DEFAULT 0, learning_outcome_score REAL DEFAULT 0,
        closure_status TEXT, closure_reason TEXT, neuromodulator_reason TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5c_cluster_resolution_memory(
        memory_key TEXT PRIMARY KEY, question_type TEXT, role TEXT, observations INTEGER DEFAULT 0,
        avg_resolution_score REAL DEFAULT 0, avg_strategy_effectiveness REAL DEFAULT 0, avg_learning_outcome REAL DEFAULT 0,
        persistent_count INTEGER DEFAULT 0, improved_count INTEGER DEFAULT 0, recommended_strategy TEXT,
        status TEXT DEFAULT 'observe', updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5c_runtime_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS phase5c_read_outcome_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, previous_priority REAL DEFAULT 0, new_priority REAL DEFAULT 0,
        previous_attention REAL DEFAULT 0, new_attention REAL DEFAULT 0, status TEXT, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0)""")
    if _table_exists(cur, 'phase5b_internal_question_clusters'):
        for col, spec in [('resolution_score','REAL DEFAULT 0'),('learning_outcome_score','REAL DEFAULT 0'),('strategy_effectiveness_score','REAL DEFAULT 0'),('closure_status',"TEXT DEFAULT 'open'"),('closure_reason','TEXT'),('last_closure_evaluated_at','INTEGER DEFAULT 0'),('closure_attempts','INTEGER DEFAULT 0'),('persistent_count','INTEGER DEFAULT 0'),('improved_count','INTEGER DEFAULT 0'),('open_count','INTEGER DEFAULT 0'),('phase5c_recommended_strategy','TEXT'),('phase5c_priority','REAL DEFAULT 0')]: _add_col(cur,'phase5b_internal_question_clusters',col,spec,changes)
    if _table_exists(cur, 'internal_learning_questions'):
        for col, spec in [('resolution_score','REAL DEFAULT 0'),('learning_outcome_score','REAL DEFAULT 0'),('strategy_effectiveness_score','REAL DEFAULT 0'),('closure_status',"TEXT DEFAULT 'internal_open'"),('closure_reason','TEXT'),('last_closure_evaluated_at','INTEGER DEFAULT 0'),('closure_attempts','INTEGER DEFAULT 0'),('phase5c_cluster_key','TEXT'),('phase5c_resolution_priority','REAL DEFAULT 0'),('phase5c_recommended_strategy','TEXT')]: _add_col(cur,'internal_learning_questions',col,spec,changes)
    if _table_exists(cur, 'internal_learning_gaps'):
        for col, spec in [('resolution_score','REAL DEFAULT 0'),('learning_outcome_score','REAL DEFAULT 0'),('strategy_effectiveness_score','REAL DEFAULT 0'),('priority','REAL DEFAULT 0'),('closure_status',"TEXT DEFAULT 'open'"),('closure_reason','TEXT'),('last_closure_evaluated_at','INTEGER DEFAULT 0'),('closure_attempts','INTEGER DEFAULT 0'),('phase5c_gap_outcome_score','REAL DEFAULT 0'),('phase5c_recommended_strategy','TEXT')]: _add_col(cur,'internal_learning_gaps',col,spec,changes)
    if _table_exists(cur, 'reading_queue'):
        for col, spec in [('phase5c_outcome_penalty','REAL DEFAULT 0'),('phase5c_reason','TEXT'),('phase5c_last_adjusted_at','INTEGER DEFAULT 0'),('phase5c_read_outcome_score','REAL DEFAULT 0')]: _add_col(cur,'reading_queue',col,spec,changes)
    if _table_exists(cur, 'chunk_attention_scores'):
        for col, spec in [('phase5c_outcome_score','REAL DEFAULT 0'),('phase5c_reason','TEXT'),('phase5c_last_adjusted_at','INTEGER DEFAULT 0'),('read_no_candidate_penalty','REAL DEFAULT 0')]: _add_col(cur,'chunk_attention_scores',col,spec,changes)
    for t,c in [('phase5c_runtime_state','key'),('phase5c_cluster_resolution_memory','memory_key'),('reading_queue','chunk_id'),('chunk_attention_scores','chunk_id')]: _safe_unique(cur,t,c,changes)
    now=_now()
    for k,v in [('phase',PHASE),('no_word_blacklists','true'),('fact_promotion','disabled'),('direct_fact_writes','disabled'),('direct_relation_writes','disabled'),('question_generation','internal_learning_questions_only'),('learning_mode','context_hypotheses_with_neuromodulators')]:
        cur.execute("INSERT INTO phase5c_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",(k,v,now))
    db.commit();
    if own: db.close()
    return {'status':'ok','phase':PHASE,'changes':changes,'no_word_blacklists':True,'fact_promotion':'disabled'}

def _state_set(cur,key,value,now):
    cur.execute("INSERT INTO phase5c_runtime_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",(key,str(value),now))

def _cluster_rows(cur, limit=240):
    if _table_exists(cur,'phase5b_internal_question_clusters'):
        c=_cols(cur,'phase5b_internal_question_clusters')
        def field(name, fallback): return name if name in c else fallback
        ck=field('cluster_key',"COALESCE(question_type,'unknown')||':'||COALESCE(role,'unknown')")
        qt=field('question_type',"'unknown'"); role=field('role',"'unknown'")
        cnt=field('question_count', field('count','1')); pri=field('avg_priority', field('priority','0'))
        res=field('resolution_score','0'); eff=field('strategy_effectiveness_score','0'); out=field('learning_outcome_score','0'); st=field('status',"'open'")
        q=f"SELECT {ck},{qt},{role},{cnt},{pri},{res},{eff},{out},{st} FROM phase5b_internal_question_clusters ORDER BY COALESCE({pri},0) DESC LIMIT ?"
        return cur.execute(q,(limit,)).fetchall()
    if _table_exists(cur,'internal_learning_questions'):
        c=_cols(cur,'internal_learning_questions')
        qt='question_type' if 'question_type' in c else "'unknown'"; role='role' if 'role' in c else "'unknown'"
        pri='priority' if 'priority' in c else '0'; res='resolution_score' if 'resolution_score' in c else '0'; eff='strategy_effectiveness_score' if 'strategy_effectiveness_score' in c else '0'; out='learning_outcome_score' if 'learning_outcome_score' in c else '0'
        q=f"SELECT COALESCE({qt},'unknown')||':'||COALESCE({role},'unknown'), COALESCE({qt},'unknown'), COALESCE({role},'unknown'), COUNT(*), AVG(COALESCE({pri},0)), AVG(COALESCE({res},0)), AVG(COALESCE({eff},0)), AVG(COALESCE({out},0)), 'open' FROM internal_learning_questions GROUP BY COALESCE({qt},'unknown'), COALESCE({role},'unknown') ORDER BY COUNT(*) DESC LIMIT ?"
        return cur.execute(q,(limit,)).fetchall()
    return []

def apply_learning_outcome_closure(mem=None):
    ensure_schema(mem); db, own=_conn_from_memory(mem); cur=db.cursor(); now=_now()
    clusters=_cluster_rows(cur,240); evaluated=improved=persistent=monitoring=event_rows=0; total_resolution=total_priority=0.0
    for row in clusters:
        cluster_key,qtype,role,count,priority,resolution,eff,outcome,status=row
        count=int(count or 0); priority=float(priority or 0); resolution=float(resolution or 0); eff=float(eff or 0); outcome=float(outcome or 0)
        closure_score=max(0.0,min(1.0,0.38*resolution+0.32*eff+0.20*outcome+0.10*(1.0-min(priority,1.0))))
        if closure_score>=0.68 and count>=3: decision='monitoring'; monitoring+=1
        elif closure_score>=0.35: decision='improving'; improved+=1
        else: decision='persistent_gap'; persistent+=1
        rec='broaden_context_and_compare_patterns' if decision=='persistent_gap' else ('continue_observe_and_consolidate' if decision=='improving' else 'monitor_for_regression')
        total_resolution+=closure_score; total_priority+=priority; evaluated+=1
        cur.execute("INSERT INTO question_cluster_resolution_events(cluster_key,question_type,role,question_count,open_count,improved_count,persistent_count,avg_priority,avg_resolution_score,avg_strategy_effectiveness,avg_learning_outcome,before_status,after_status,decision,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(cluster_key,qtype,role,count,1 if decision!='monitoring' else 0,1 if decision=='improving' else 0,1 if decision=='persistent_gap' else 0,priority,closure_score,eff,outcome,str(status),decision,rec,_json({'source':'phase5c_cluster_resolution','raw_resolution':resolution,'raw_effectiveness':eff,'raw_outcome':outcome}),now)); event_rows+=1
        if _table_exists(cur,'phase5b_internal_question_clusters') and 'cluster_key' in _cols(cur,'phase5b_internal_question_clusters'):
            cur.execute("UPDATE phase5b_internal_question_clusters SET resolution_score=?, learning_outcome_score=?, strategy_effectiveness_score=?, closure_status=?, closure_reason=?, last_closure_evaluated_at=?, closure_attempts=COALESCE(closure_attempts,0)+1, phase5c_recommended_strategy=?, phase5c_priority=? WHERE cluster_key=?",(closure_score,outcome,eff,decision,rec,now,rec,max(priority*(0.92 if decision!='persistent_gap' else 1.0),closure_score),cluster_key))
        if _table_exists(cur,'internal_learning_questions') and 'cluster_key' in _cols(cur,'internal_learning_questions'):
            cur.execute("UPDATE internal_learning_questions SET resolution_score=?, learning_outcome_score=?, strategy_effectiveness_score=?, closure_status=?, closure_reason=?, last_closure_evaluated_at=?, closure_attempts=COALESCE(closure_attempts,0)+1, phase5c_cluster_key=?, phase5c_recommended_strategy=?, phase5c_resolution_priority=? WHERE cluster_key=?",(closure_score,outcome,eff,decision,rec,now,cluster_key,rec,max(priority,closure_score),cluster_key))
        cur.execute("INSERT OR REPLACE INTO phase5c_cluster_resolution_memory(memory_key,question_type,role,observations,avg_resolution_score,avg_strategy_effectiveness,avg_learning_outcome,persistent_count,improved_count,recommended_strategy,status,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(str(cluster_key),qtype,role,count,closure_score,eff,outcome,1 if decision=='persistent_gap' else 0,1 if decision=='improving' else 0,rec,decision,now))
    adjusted=0
    if _table_exists(cur,'reading_queue'):
        rqcols=_cols(cur,'reading_queue')
        if all(x in rqcols for x in ('priority','attention_score','status','chunk_id')):
            for cid,pri,att,st in cur.execute("SELECT chunk_id,COALESCE(priority,0),COALESCE(attention_score,0),status FROM reading_queue WHERE status='read_no_candidate' AND COALESCE(priority,0)>=0.65 ORDER BY priority DESC LIMIT 120").fetchall():
                newp=max(0.05,float(pri)*0.82); newa=max(0.05,float(att)*0.84)
                cur.execute("UPDATE reading_queue SET priority=?,attention_score=?,phase5c_outcome_penalty=?,phase5c_reason=?,phase5c_last_adjusted_at=?,phase5c_read_outcome_score=? WHERE chunk_id=?",(newp,newa,1.0,'phase5c_high_priority_read_no_candidate_penalty',now,0.0,cid))
                if _table_exists(cur,'chunk_attention_scores') and 'chunk_id' in _cols(cur,'chunk_attention_scores'):
                    cur.execute("UPDATE chunk_attention_scores SET attention_score=?,phase5c_outcome_score=?,phase5c_reason=?,phase5c_last_adjusted_at=?,read_no_candidate_penalty=? WHERE chunk_id=?",(newa,0.0,'phase5c_high_priority_read_no_candidate_penalty',now,1.0,cid))
                cur.execute("INSERT INTO learning_outcome_closure_events(target_type,target_key,target_id,before_priority,after_priority,resolution_score,strategy_effectiveness_score,learning_outcome_score,closure_status,closure_reason,neuromodulator_reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",('chunk',str(cid),cid,float(pri),newp,0.0,0.0,0.0,'penalized_read_no_candidate','high_priority_without_candidate','gaba_inhibition_and_exploration_rebalance',now)); adjusted+=1
    avg_res=round(total_resolution/evaluated,6) if evaluated else 0.0; avg_pri=round(total_priority/evaluated,6) if evaluated else 0.0
    for k,v in [('phase',PHASE),('no_word_blacklists','true'),('fact_promotion','disabled'),('question_generation','internal_learning_questions_only'),('last_evaluated_clusters',evaluated),('last_improved_clusters',improved),('last_persistent_clusters',persistent),('last_monitoring_clusters',monitoring),('last_avg_cluster_resolution_score',avg_res),('last_avg_cluster_priority',avg_pri),('last_read_no_candidate_penalties',adjusted)]: _state_set(cur,k,v,now)
    db.commit();
    if own: db.close()
    return {'status':'phase5c_learning_outcome_closure_complete','phase':PHASE,'evaluated_clusters':evaluated,'improved_clusters':improved,'persistent_clusters':persistent,'monitoring_clusters':monitoring,'avg_cluster_resolution_score':avg_res,'avg_cluster_priority':avg_pri,'read_no_candidate_penalties':adjusted,'events':event_rows,'no_word_blacklists':True,'fact_promotion':'disabled'}

_PREV_RUN=None; _PREV_CYCLE=None

def managed_cycle(self, progress=None):
    res=None
    if _PREV_CYCLE and _PREV_CYCLE is not managed_cycle: res=_PREV_CYCLE(self, progress)
    outcome=apply_learning_outcome_closure(_memory_from_loop(self))
    if isinstance(res,dict): res['phase5c_learning_outcome_closure']=outcome; return res
    return {'status':'phase5c_managed_cycle','base_result':res,'phase5c_learning_outcome_closure':outcome,'facts_relations_questions':'disabled'}

def managed_run(self, cycles=1, progress=None):
    out=None
    if _PREV_RUN and _PREV_RUN is not managed_run: out=_PREV_RUN(self, cycles, progress)
    outcome=apply_learning_outcome_closure(_memory_from_loop(self))
    return {'status':'phase5c_managed_run','base_result':out,'phase5c_learning_outcome_closure':outcome,'fact_promotion':'disabled','no_word_blacklists':True}

def patch_autonomous_loop(cls=None):
    global _PREV_RUN,_PREV_CYCLE
    if cls is None:
        from ki_system.autonomous import AutonomousLoop as cls
    if getattr(cls,'phase5c_learning_outcome_closure_and_question_cluster_resolution',False): return cls
    _PREV_RUN=getattr(cls,'run',None); _PREV_CYCLE=getattr(cls,'cycle',None)
    cls.run=managed_run; cls.cycle=managed_cycle
    cls.phase5c_learning_outcome_closure_and_question_cluster_resolution=True
    cls._phase5c_learning_outcome_closure_and_question_cluster_resolution=True
    cls.no_word_blacklists=True; cls._no_word_blacklists=True
    cls.learning_mode='context_hypotheses_with_neuromodulators'; cls._learning_mode='context_hypotheses_with_neuromodulators'
    cls.fact_promotion='disabled'; cls._fact_promotion='disabled'
    return cls
