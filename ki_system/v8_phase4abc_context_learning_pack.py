
import time, re
PHASE = "phase4abc_context_learning_pack_fixed1"

def _conn_from_loop(loop):
    mem = getattr(loop, 'mem', None) or getattr(loop, 'memory', None)
    if mem is None:
        raise RuntimeError('AutonomousLoop has no mem/memory attribute')
    db = getattr(mem, 'db', None) or getattr(mem, 'con', None) or getattr(mem, 'conn', None)
    if db is None:
        raise RuntimeError('Memory object has no db/con/conn attribute')
    return db

def _table_exists(cur, name):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

def _cols(cur, table):
    if not _table_exists(cur, table):
        return {}
    return {r[1]: r for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}

def _add_col(cur, table, name, typ):
    if name not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")

def ensure_schema(db):
    cur = db.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS rollback_safe_core_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reading_queue(
        chunk_id INTEGER PRIMARY KEY, priority REAL DEFAULT 0, reason TEXT,
        attention_score REAL DEFAULT 0, read_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending', last_read INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    if not _table_exists(cur, 'context_hypotheses'):
        cur.execute("""CREATE TABLE context_hypotheses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, role TEXT,
            subject TEXT, relation_hint TEXT, object TEXT, text_excerpt TEXT,
            source_title TEXT, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1,
            status TEXT DEFAULT 'hypothesis', dopamine REAL DEFAULT 0.5,
            serotonin REAL DEFAULT 0.6, glutamate REAL DEFAULT 0.4, gaba REAL DEFAULT 0.4,
            noradrenaline REAL DEFAULT 0.3, acetylcholine REAL DEFAULT 0.5,
            created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    else:
        for name, typ in [
            ('role','TEXT'), ('subject','TEXT'), ('relation_hint','TEXT'), ('object','TEXT'),
            ('text_excerpt','TEXT'), ('source_title','TEXT'), ('confidence','REAL DEFAULT 0'),
            ('uncertainty','REAL DEFAULT 1'), ('status',"TEXT DEFAULT 'hypothesis'"),
            ('dopamine','REAL DEFAULT 0.5'), ('serotonin','REAL DEFAULT 0.6'),
            ('glutamate','REAL DEFAULT 0.4'), ('gaba','REAL DEFAULT 0.4'),
            ('noradrenaline','REAL DEFAULT 0.3'), ('acetylcholine','REAL DEFAULT 0.5'),
            ('created_at','INTEGER DEFAULT 0'), ('updated_at','INTEGER DEFAULT 0')]:
            _add_col(cur, 'context_hypotheses', name, typ)
    cur.execute("""CREATE TABLE IF NOT EXISTS context_learning_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, event_type TEXT,
        role TEXT, message TEXT, surprise REAL DEFAULT 0, uncertainty REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, feedback_type TEXT,
        value REAL DEFAULT 0, note TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_revisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, old_role TEXT,
        new_role TEXT, reason TEXT, confidence_delta REAL DEFAULT 0, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_error_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, error_signal TEXT,
        uncertainty REAL DEFAULT 0, conflict_score REAL DEFAULT 0, note TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulated_attention_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, role TEXT,
        dopamine REAL DEFAULT 0.5, serotonin REAL DEFAULT 0.6, glutamate REAL DEFAULT 0.4,
        gaba REAL DEFAULT 0.4, noradrenaline REAL DEFAULT 0.3, acetylcholine REAL DEFAULT 0.5,
        attention_score REAL DEFAULT 0, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS context_role_stats(
        role TEXT PRIMARY KEY, seen INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_clusters(
        id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, cluster_key TEXT,
        size INTEGER DEFAULT 0, stability REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, stability REAL DEFAULT 0,
        evidence_count INTEGER DEFAULT 0, uncertainty REAL DEFAULT 1, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS context_pattern_memory(
        pattern_key TEXT PRIMARY KEY, role TEXT, seen INTEGER DEFAULT 0,
        stability REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT, message TEXT,
        dopamine REAL DEFAULT 0.5, serotonin REAL DEFAULT 0.6, glutamate REAL DEFAULT 0.4,
        gaba REAL DEFAULT 0.4, noradrenaline REAL DEFAULT 0.3, acetylcholine REAL DEFAULT 0.5,
        created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS learning_strategy_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    now=int(time.time())
    for k,v in {
        'phase':'phase4abc_context_learning_pack_fixed1',
        'direct_fact_writes':'disabled','direct_relation_writes':'disabled',
        'fact_promotion':'disabled','question_generation':'disabled',
        'no_word_blacklists':'true','learning_mode':'context_hypotheses_with_neuromodulators'}.items():
        cur.execute('INSERT OR REPLACE INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?)',(k,repr(v),now))
    db.commit()

def _chunk_columns(cur):
    if not _table_exists(cur, 'chunks'):
        return None
    cols=_cols(cur,'chunks')
    id_col='id' if 'id' in cols else ('chunk_id' if 'chunk_id' in cols else None)
    text_col=next((c for c in ['text','content','chunk_text','body'] if c in cols), None)
    title_col=next((c for c in ['title','source_title','document_title','path'] if c in cols), None)
    return id_col,title_col,text_col

def seed_reading_queue(db, target=2000):
    cur=db.cursor(); cc=_chunk_columns(cur)
    if not cc or not cc[0]: return 0
    id_col,title_col,text_col=cc
    pending=cur.execute("SELECT COUNT(*) FROM reading_queue WHERE status='pending'").fetchone()[0]
    if pending >= 200: return 0
    before=cur.execute('SELECT COUNT(*) FROM reading_queue').fetchone()[0]
    now=int(time.time())
    sql=f"""INSERT OR IGNORE INTO reading_queue(chunk_id,priority,reason,attention_score,status,updated_at)
             SELECT {id_col},0.5,'phase4abc_seed',0.5,'pending',? FROM chunks
             WHERE {id_col} NOT IN (SELECT chunk_id FROM reading_queue)
             ORDER BY {id_col} LIMIT ?"""
    cur.execute(sql,(now,max(0,target-pending))); db.commit()
    after=cur.execute('SELECT COUNT(*) FROM reading_queue').fetchone()[0]
    return after-before

def neuromodulators(loop):
    d=dict(dopamine=0.5,serotonin=0.6,glutamate=0.4,gaba=0.4,noradrenaline=0.3,acetylcholine=0.5)
    mgr=getattr(loop,'neuromodulators',None) or getattr(loop,'neuromodulator_manager',None)
    st=getattr(mgr,'state',None)
    if st:
        for k in d:
            try: d[k]=float(getattr(st,k,d[k]))
            except Exception: pass
    return d

def split_sentences(text):
    text=re.sub(r'\s+',' ',str(text or '')).strip()
    if not text: return []
    return [p.strip()[:700] for p in re.split(r'(?<=[.!?])\s+',text) if len(p.strip())>20][:8]

def classify_sentence(sentence):
    s=sentence.strip(); low=s.lower()
    role='raw_hypothesis'; rel=''; subj=s[:80]; obj=s[80:260]; confidence=0.30; uncertainty=0.70
    m=re.search(r'(.{2,120}?)\s+(ist|sind|war|waren|wird|werden)\s+(.{2,220})',s,re.I)
    if m:
        subj=m.group(1).strip(' ,;:')[-120:]; obj=m.group(3).strip(' ,;:')[:220]
        if any(x in low for x in ['beispiel','zum beispiel','etwa']): role,rel,confidence,uncertainty='example_hypothesis','example_of',0.45,0.55
        elif any(x in low for x in ['seit','bis','ab','im jahr','zwischen']): role,rel,confidence,uncertainty='temporal_hypothesis','temporal_context',0.42,0.58
        elif any(x in low for x in ['teil von','bestandteil','sitz','liegt','gehört zu']): role,rel,confidence,uncertainty='relation_hypothesis','related_to',0.46,0.54
        elif any(x in low for x in ['verfügbar','möglich','notwendig','erforderlich','aktiv','kompatibel','fertig']): role,rel,confidence,uncertainty='state_hypothesis','has_state',0.43,0.57
        elif any(x in obj.lower() for x in ['ein ','eine ','protokoll','programm','framework','schnittstelle','format','system','sprache','modell']): role,rel,confidence,uncertainty='definition_hypothesis','is_a?',0.48,0.52
        else: role,rel,confidence,uncertainty='property_hypothesis','has_property?',0.38,0.62
    else:
        role = 'context_fragment' if len(s)>180 else 'uncertain_hypothesis'
        confidence = 0.25 if role=='context_fragment' else 0.22
        uncertainty = 1-confidence
    return role,subj,rel,obj,confidence,uncertainty

def insert_hypothesis(db, chunk_id, sentence, title, nm):
    cur=db.cursor(); now=int(time.time())
    role,subj,rel,obj,conf,unc=classify_sentence(sentence)
    cur.execute("""INSERT INTO context_hypotheses(chunk_id,role,subject,relation_hint,object,text_excerpt,source_title,confidence,uncertainty,status,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(chunk_id,role,subj,rel,obj,sentence[:700],title,conf,unc,'hypothesis',nm['dopamine'],nm['serotonin'],nm['glutamate'],nm['gaba'],nm['noradrenaline'],nm['acetylcholine'],now,now))
    hid=cur.lastrowid
    cur.execute("""INSERT INTO context_learning_events(hypothesis_id,event_type,role,message,surprise,uncertainty,created_at) VALUES(?,?,?,?,?,?,?)""",(hid,'hypothesis_created',role,'context hypothesis created without word blacklist',unc,unc,now))
    cur.execute("""INSERT INTO neuromodulated_attention_events(chunk_id,role,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,attention_score,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",(chunk_id,role,nm['dopamine'],nm['serotonin'],nm['glutamate'],nm['gaba'],nm['noradrenaline'],nm['acetylcholine'],1.0-unc,now))
    row=cur.execute('SELECT seen,avg_confidence,avg_uncertainty FROM context_role_stats WHERE role=?',(role,)).fetchone()
    if row:
        seen,ac,au=row; ns=seen+1
        cur.execute('UPDATE context_role_stats SET seen=?,avg_confidence=?,avg_uncertainty=?,updated_at=? WHERE role=?',(ns,(ac*seen+conf)/ns,(au*seen+unc)/ns,now,role))
    else:
        cur.execute('INSERT INTO context_role_stats(role,seen,avg_confidence,avg_uncertainty,updated_at) VALUES(?,?,?,?,?)',(role,1,conf,unc,now))
    return hid,role

def fetch_chunks(db, limit=32):
    cur=db.cursor(); cc=_chunk_columns(cur)
    if not cc or not cc[0] or not cc[2]: return []
    id_col,title_col,text_col=cc; title_expr=title_col if title_col else "''"
    ids=[r[0] for r in cur.execute("SELECT chunk_id FROM reading_queue WHERE status='pending' ORDER BY priority DESC, chunk_id LIMIT ?",(limit,)).fetchall()]
    rows=[]
    if ids:
        ph=','.join('?'*len(ids)); rows=cur.execute(f"SELECT {id_col},{title_expr},{text_col} FROM chunks WHERE {id_col} IN ({ph})",ids).fetchall()
    if not rows:
        rows=cur.execute(f"SELECT {id_col},{title_expr},{text_col} FROM chunks ORDER BY {id_col} LIMIT ?",(limit,)).fetchall()
    return [{'id':r[0],'title':r[1] if len(r)>1 else '', 'text':r[2] if len(r)>2 else ''} for r in rows]

def sleep_consolidation(db):
    cur=db.cursor(); now=int(time.time())
    roles=cur.execute('SELECT role,COUNT(*),AVG(confidence),AVG(uncertainty) FROM context_hypotheses GROUP BY role').fetchall()
    total=sum(r[1] for r in roles) if roles else 0
    for role,cnt,avgc,avgu in roles:
        key=f'{role}:{int((avgc or 0)*10)}:{int((avgu or 0)*10)}'; stability=max(0,min(1,(avgc or 0)*(1-(avgu or 0))+min(cnt,50)/200))
        cur.execute("""INSERT INTO context_pattern_memory(pattern_key,role,seen,stability,updated_at) VALUES(?,?,?,?,?)
            ON CONFLICT(pattern_key) DO UPDATE SET seen=seen+excluded.seen, stability=(stability+excluded.stability)/2, updated_at=excluded.updated_at""",(key,role,cnt,stability,now))
    cur.execute("""INSERT INTO neuromodulator_sleep_events(status,message,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",('consolidated',f'consolidated {total} context hypotheses into role pattern memory',0.5,0.62,0.4,0.42,0.3,0.52,now))
    cur.execute('INSERT OR REPLACE INTO learning_strategy_state(key,value,updated_at) VALUES(?,?,?)',('last_sleep_total_hypotheses',str(total),now))
    db.commit(); return {'status':'consolidated','hypotheses_seen':total,'roles':[(r[0],r[1]) for r in roles]}

def safe_cycle(self, progress=None):
    db=_conn_from_loop(self); ensure_schema(db); seeded=seed_reading_queue(db,2000); nm=neuromodulators(self); chunks=fetch_chunks(db,32)
    cur=db.cursor(); now=int(time.time()); hypotheses=0; role_counts={}; rc=0; rn=0
    for idx,ch in enumerate(chunks,1):
        chunk_h=0
        for sent in split_sentences(ch.get('text') or '')[:4]:
            hid,role=insert_hypothesis(db,ch['id'],sent,ch.get('title') or '',nm); hypotheses+=1; chunk_h+=1; role_counts[role]=role_counts.get(role,0)+1
        status='read_candidate' if chunk_h else 'read_no_candidate'; rc += 1 if chunk_h else 0; rn += 0 if chunk_h else 1
        cur.execute('UPDATE reading_queue SET status=?,read_count=read_count+1,last_read=?,updated_at=? WHERE chunk_id=?',(status,now,now,ch['id']))
        if progress:
            try: progress(idx,max(1,len(chunks)),'phase4abc context learning')
            except Exception: pass
    db.commit(); sleep=sleep_consolidation(db)
    def count(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if _table_exists(cur,t) else 'missing'
    return [{'status':'phase4abc_context_learning_pack_fixed1','message':'Context hypotheses + neuromodulated error learning + sleep consolidation. No word blacklists. No facts/relations/questions promotion.','no_word_blacklists':True,'learning_mode':'context_hypotheses_with_neuromodulators','fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','seeded_reading_queue':seeded,'chunks_read':len(chunks),'hypotheses_created':hypotheses,'learning_events_created':hypotheses,'role_counts':role_counts,'read_candidate_chunks':rc,'read_no_candidate_chunks':rn,'sleep_consolidation':sleep,'safety_counts':{'facts':count('facts'),'relations':count('relations'),'questions':count('questions')}}]

def _stop_requested(loop):
    for name in ['auto_stop','stop_requested','cancel','cancel_requested']:
        v=getattr(loop,name,False)
        if isinstance(v,bool) and v: return True
    return False

def safe_run(self, cycles=5, progress=None):
    results=[]
    for i in range(int(cycles or 1)):
        if _stop_requested(self): results.append([{'status':'stopped','message':'Stop-Anforderung erkannt.'}]); break
        results.append(safe_cycle(self,progress=progress))
    return results

def patch_autonomous_loop(*args, **kwargs):
    from ki_system.autonomous import AutonomousLoop
    AutonomousLoop.cycle=safe_cycle; AutonomousLoop.run=safe_run
    AutonomousLoop._phase4a_context_hypothesis_learning_core=True
    AutonomousLoop._phase4b_neuromodulated_error_learning=True
    AutonomousLoop._phase4c_sleep_consolidation_self_improvement=True
    AutonomousLoop._phase4abc_context_learning_pack=True
    AutonomousLoop._phase4abc_context_learning_pack_fixed1=True
    AutonomousLoop._no_word_blacklists=True
    AutonomousLoop._rollback_learning_mode='context_hypotheses_with_neuromodulators'
    AutonomousLoop._fact_promotion='disabled'
    return AutonomousLoop
try:
    patch_autonomous_loop()
except Exception:
    pass
