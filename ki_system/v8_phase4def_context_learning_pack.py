
from __future__ import annotations
import time, re, json, hashlib
from collections import Counter, defaultdict

PHASE='phase4def_neuromodulated_context_learning_pack'
LEARNING_MODE='context_hypotheses_with_neuromodulators'

_SENT_RE=re.compile(r'(?<=[.!?])\s+|\n+')
_WS_RE=re.compile(r'\s+')
_YEAR_RE=re.compile(r'\b(1[0-9]{3}|20[0-9]{2}|21[0-9]{2})\b')


def _now(): return int(time.time())
def _norm(s,n=700): return _WS_RE.sub(' ',(s or '').replace('\x00',' ')).strip()[:n]
def _json(x): return json.dumps(x, ensure_ascii=False, sort_keys=True)

def _db(loop):
    mem=getattr(loop,'mem',None) or getattr(loop,'memory',None) or getattr(loop,'db',None)
    con=getattr(mem,'db',None) or getattr(mem,'conn',None) or mem
    if not hasattr(con,'execute'): raise RuntimeError('sqlite connection not found')
    return con

def _exists(db,t): return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _cols(db,t): return [r[1] for r in db.execute(f'PRAGMA table_info({t})').fetchall()] if _exists(db,t) else []
def _col(db,t,c,decl):
    if c not in _cols(db,t): db.execute(f'ALTER TABLE {t} ADD COLUMN {c} {decl}')

def ensure_schema(db):
    c=db.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS reading_queue(chunk_id INTEGER PRIMARY KEY, priority REAL DEFAULT 0, reason TEXT, attention_score REAL DEFAULT 0, read_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', last_read INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS context_hypotheses(id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, role TEXT, subject TEXT, relation_hint TEXT, object TEXT, text_excerpt TEXT, source_title TEXT, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1, status TEXT DEFAULT 'active', dopamine REAL DEFAULT 0.5, serotonin REAL DEFAULT 0.6, glutamate REAL DEFAULT 0.4, gaba REAL DEFAULT 0.4, noradrenaline REAL DEFAULT 0.3, acetylcholine REAL DEFAULT 0.5, signature TEXT, evidence_count INTEGER DEFAULT 1, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    for name,decl in [('chunk_id','INTEGER'),('role','TEXT'),('subject','TEXT'),('relation_hint','TEXT'),('object','TEXT'),('text_excerpt','TEXT'),('source_title','TEXT'),('confidence','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 1'),('status',"TEXT DEFAULT 'active'"),('dopamine','REAL DEFAULT 0.5'),('serotonin','REAL DEFAULT 0.6'),('glutamate','REAL DEFAULT 0.4'),('gaba','REAL DEFAULT 0.4'),('noradrenaline','REAL DEFAULT 0.3'),('acetylcholine','REAL DEFAULT 0.5'),('signature','TEXT'),('evidence_count','INTEGER DEFAULT 1'),('created_at','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]: _col(db,'context_hypotheses',name,decl)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ch_role ON context_hypotheses(role)"); c.execute("CREATE INDEX IF NOT EXISTS idx_ch_sig ON context_hypotheses(signature)")
    c.execute("CREATE TABLE IF NOT EXISTS context_learning_events(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, event_type TEXT, role TEXT, details TEXT, dopamine REAL DEFAULT 0.5, serotonin REAL DEFAULT 0.6, glutamate REAL DEFAULT 0.4, gaba REAL DEFAULT 0.4, noradrenaline REAL DEFAULT 0.3, acetylcholine REAL DEFAULT 0.5, created_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS hypothesis_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, feedback_type TEXT, signal REAL DEFAULT 0, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS hypothesis_revisions(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, old_role TEXT, new_role TEXT, old_confidence REAL, new_confidence REAL, reason TEXT, created_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS hypothesis_error_events(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, error_type TEXT, severity REAL DEFAULT 0, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS neuromodulated_attention_events(id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, hypothesis_id INTEGER, attention_reason TEXT, novelty REAL DEFAULT 0, uncertainty REAL DEFAULT 0, reward REAL DEFAULT 0, fatigue REAL DEFAULT 0, dopamine REAL DEFAULT 0.5, serotonin REAL DEFAULT 0.6, glutamate REAL DEFAULT 0.4, gaba REAL DEFAULT 0.4, noradrenaline REAL DEFAULT 0.3, acetylcholine REAL DEFAULT 0.5, created_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS context_role_stats(role TEXT PRIMARY KEY, seen_count INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, feedback_count INTEGER DEFAULT 0, error_count INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS chunk_attention_scores(chunk_id INTEGER PRIMARY KEY, novelty REAL DEFAULT 0, uncertainty REAL DEFAULT 0, reward REAL DEFAULT 0, fatigue REAL DEFAULT 0, attention_score REAL DEFAULT 0, last_reason TEXT, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS attention_queue_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS reading_strategy_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS hypothesis_clusters(id INTEGER PRIMARY KEY AUTOINCREMENT, cluster_key TEXT UNIQUE, role TEXT, size INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, example TEXT, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(hypothesis_id INTEGER PRIMARY KEY, stability REAL DEFAULT 0, evidence_count INTEGER DEFAULT 1, conflict_count INTEGER DEFAULT 0, last_reason TEXT, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS context_pattern_memory(pattern_key TEXT PRIMARY KEY, role TEXT, seen_count INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events(id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, summary TEXT, dopamine REAL DEFAULT 0.5, serotonin REAL DEFAULT 0.6, glutamate REAL DEFAULT 0.4, gaba REAL DEFAULT 0.4, noradrenaline REAL DEFAULT 0.3, acetylcholine REAL DEFAULT 0.5, created_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS learning_strategy_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS rollback_safe_core_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    for k,v in [('phase',PHASE),('no_word_blacklists','true'),('learning_mode',LEARNING_MODE),('fact_promotion','disabled'),('direct_fact_writes','disabled'),('direct_relation_writes','disabled'),('question_generation','disabled')]:
        c.execute('INSERT OR REPLACE INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?)',(k,repr(v),_now()))
    db.commit()

def _chunk_cols(db):
    cols=_cols(db,'chunks'); return ('id' if 'id' in cols else ('chunk_id' if 'chunk_id' in cols else None), 'text' if 'text' in cols else ('content' if 'content' in cols else None), 'title' if 'title' in cols else None)

def seed_queue(db,target=2000):
    if not _exists(db,'chunks'): return {'seeded':0,'reason':'chunks_missing'}
    pending=db.execute("SELECT COUNT(*) FROM reading_queue WHERE status='pending'").fetchone()[0]
    if pending>=target: return {'seeded':0,'reason':'enough_pending','pending':pending}
    cid,txt,title=_chunk_cols(db)
    if not cid: return {'seeded':0,'reason':'chunk_id_missing'}
    rows=db.execute(f"SELECT c.{cid} FROM chunks c LEFT JOIN reading_queue rq ON rq.chunk_id=c.{cid} WHERE rq.chunk_id IS NULL ORDER BY c.{cid} ASC LIMIT ?",(target-pending,)).fetchall()
    now=_now()
    for (x,) in rows: db.execute("INSERT OR IGNORE INTO reading_queue(chunk_id,priority,reason,attention_score,status,updated_at) VALUES(?,?,?,?,?,?)",(x,0.5,'phase4def_seed',0.5,'pending',now))
    db.commit(); return {'seeded':len(rows),'pending_before':pending}

def _nm(db): return {'dopamine':0.5,'serotonin':0.6,'glutamate':0.4,'gaba':0.4,'noradrenaline':0.3,'acetylcholine':0.5}

def _sentences(text,limit=4): return [p.strip() for p in _SENT_RE.split(_norm(text,3000)) if len(p.strip())>20][:limit]

def classify(s,title=''):
    s=_norm(s); low=s.lower(); words=s.split(); subj=' '.join(words[:min(6,len(words))]); obj=' '.join(words[min(6,len(words)):])[:350]; rel='context'
    for m in [' ist ',' sind ',' war ',' waren ',' wird ',' werden ',' bedeutet ',' bezeichnet ',' enthält ',' umfasst ',' besteht ',' dient ',' ermöglicht ',' erfordert ',' benötigt ']:
        i=low.find(m)
        if i>0: subj=s[:i].strip(' :;,-'); obj=s[i+len(m):].strip(' :;,-')[:350]; rel=m.strip(); break
    role='raw_hypothesis'; conf=0.35; unc=0.65
    if _YEAR_RE.search(s) or re.search(r'\b(seit|bis|jahr)\b',low): role,conf,unc='temporal_hypothesis',0.48,0.52
    if rel in ('ist','sind','war','waren','bedeutet','bezeichnet') and len(obj.split())>=3: role,conf,unc='definition_hypothesis',0.55,0.45
    if rel in ('ermöglicht','erfordert','benötigt','dient'): role,conf,unc='requirement_hypothesis',0.50,0.50
    if re.search(r'\bbeispiel\b|\betwa\b',low): role,conf,unc='example_hypothesis',0.50,0.50
    if re.search(r'\b(verfügbar|kompatibel|geeignet|möglich|notwendig|erforderlich|frei|aktiv|inaktiv|fertig)\b',obj.lower()): role,conf,unc='state_hypothesis',0.48,0.52
    if rel in ('enthält','umfasst','besteht'): role,conf,unc='relation_hypothesis',0.52,0.48
    if len(words)>45 or len(subj.split())>14: role,conf,unc='context_fragment',0.30,0.70
    if conf<0.40: role='uncertain_hypothesis'
    return {'role':role,'subject':subj[:180],'relation_hint':rel,'object':obj,'text_excerpt':s,'confidence':conf,'uncertainty':unc}

def _sig(h):
    b='|'.join([h['role'],h['subject'].lower()[:80],h['relation_hint'],h['object'].lower()[:120],h['text_excerpt'].lower()[:160]])
    return hashlib.sha1(b.encode('utf-8','ignore')).hexdigest()

def insert_h(db,cid,s,title,nm):
    h=classify(s,title); sig=_sig(h); now=_now()
    ex=db.execute('SELECT id,evidence_count,confidence,uncertainty FROM context_hypotheses WHERE signature=? LIMIT 1',(sig,)).fetchone()
    if ex:
        hid,ev,cf,un=ex; db.execute('UPDATE context_hypotheses SET evidence_count=?, confidence=?, uncertainty=?, updated_at=? WHERE id=?',((ev or 1)+1,min(.95,(cf or h['confidence'])+.02),max(.05,(un or h['uncertainty'])-.02),now,hid)); evtype='hypothesis_reobserved'
    else:
        cur=db.execute("INSERT INTO context_hypotheses(chunk_id,role,subject,relation_hint,object,text_excerpt,source_title,confidence,uncertainty,status,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,signature,evidence_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,h['role'],h['subject'],h['relation_hint'],h['object'],h['text_excerpt'],title,h['confidence'],h['uncertainty'],'active',nm['dopamine'],nm['serotonin'],nm['glutamate'],nm['gaba'],nm['noradrenaline'],nm['acetylcholine'],sig,1,now,now)); hid=cur.lastrowid; evtype='hypothesis_created'
    db.execute("INSERT INTO context_learning_events(hypothesis_id,event_type,role,details,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(hid,evtype,h['role'],_json({'chunk_id':cid,'signature':sig}),nm['dopamine'],nm['serotonin'],nm['glutamate'],nm['gaba'],nm['noradrenaline'],nm['acetylcholine'],now))
    signal=h['confidence']-h['uncertainty']; db.execute("INSERT INTO hypothesis_feedback(hypothesis_id,feedback_type,signal,reason,details,created_at) VALUES(?,?,?,?,?,?)",(hid,'initial_self_assessment',round(signal,3),'neuromodulated_uncertainty_estimate',_json({'role':h['role']}),now))
    if h['uncertainty']-h['confidence']>.25: db.execute("INSERT INTO hypothesis_error_events(hypothesis_id,error_type,severity,reason,details,created_at) VALUES(?,?,?,?,?,?)",(hid,'high_uncertainty',round(h['uncertainty']-h['confidence'],3),'uncertainty_exceeds_confidence',_json({'role':h['role']}),now))
    nov=0.25 if ex else 1.0; rew=max(0,h['confidence']-.45); fat=max(0,h['uncertainty']-.65)
    db.execute("INSERT INTO neuromodulated_attention_events(chunk_id,hypothesis_id,attention_reason,novelty,uncertainty,reward,fatigue,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,hid,'hypothesis_attention_signal',nov,h['uncertainty'],rew,fat,nm['dopamine'],nm['serotonin'],nm['glutamate'],nm['gaba'],nm['noradrenaline'],nm['acetylcholine'],now))
    return hid,h

def _chunks(db,limit=32):
    if not _exists(db,'chunks'): return []
    cid,txt,title=_chunk_cols(db)
    ids=[r[0] for r in db.execute("SELECT chunk_id FROM reading_queue WHERE status='pending' ORDER BY attention_score DESC, priority DESC, chunk_id ASC LIMIT ?",(limit,)).fetchall()]
    if not ids or not cid or not txt: return []
    qs=','.join('?' for _ in ids); title_expr=title if title else "''"
    return [{'id':a,'title':b or '', 'text':c or ''} for a,b,c in db.execute(f'SELECT {cid},{title_expr},{txt} FROM chunks WHERE {cid} IN ({qs})',ids).fetchall()]

def update_stats(db):
    now=_now()
    for role,cnt,avgc,avgu in db.execute('SELECT role,COUNT(*),AVG(confidence),AVG(uncertainty) FROM context_hypotheses GROUP BY role').fetchall():
        fc=db.execute('SELECT COUNT(*) FROM hypothesis_feedback hf JOIN context_hypotheses h ON hf.hypothesis_id=h.id WHERE h.role=?',(role,)).fetchone()[0]
        ec=db.execute('SELECT COUNT(*) FROM hypothesis_error_events ee JOIN context_hypotheses h ON ee.hypothesis_id=h.id WHERE h.role=?',(role,)).fetchone()[0]
        db.execute("INSERT INTO context_role_stats(role,seen_count,avg_confidence,avg_uncertainty,feedback_count,error_count,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(role) DO UPDATE SET seen_count=excluded.seen_count, avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty, feedback_count=excluded.feedback_count, error_count=excluded.error_count, updated_at=excluded.updated_at",(role,cnt,avgc or 0,avgu or 0,fc,ec,now))

def sleep(db,nm):
    now=_now(); rows=db.execute('SELECT id,role,subject,confidence,uncertainty,evidence_count,text_excerpt FROM context_hypotheses ORDER BY id DESC LIMIT 800').fetchall(); groups=defaultdict(list)
    for r in rows: groups[(r[1] or '')+':'+(r[2] or '').lower()[:40]].append(r)
    n=0
    for key,items in groups.items():
        role=items[0][1]; size=len(items); avgc=sum((x[3] or 0) for x in items)/size; avgu=sum((x[4] or 1) for x in items)/size; ev=sum((x[5] or 1) for x in items); stab=max(0,min(1,avgc*.6+min(1,ev/10)*.25+(1-avgu)*.15)); ex=(items[0][6] or '')[:250]
        db.execute("INSERT INTO hypothesis_clusters(cluster_key,role,size,avg_confidence,avg_uncertainty,stability,example,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(cluster_key) DO UPDATE SET size=excluded.size, avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty, stability=excluded.stability, example=excluded.example, updated_at=excluded.updated_at",(key,role,size,avgc,avgu,stab,ex,now))
        db.execute("INSERT INTO context_pattern_memory(pattern_key,role,seen_count,avg_confidence,avg_uncertainty,stability,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(pattern_key) DO UPDATE SET seen_count=excluded.seen_count, avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty, stability=excluded.stability, updated_at=excluded.updated_at",(key,role,ev,avgc,avgu,stab,now))
        for hid,*rest in items[:30]: db.execute("INSERT INTO hypothesis_stability_scores(hypothesis_id,stability,evidence_count,conflict_count,last_reason,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(hypothesis_id) DO UPDATE SET stability=excluded.stability,evidence_count=excluded.evidence_count,last_reason=excluded.last_reason,updated_at=excluded.updated_at",(hid,stab,ev,0,'sleep_cluster_consolidation',now))
        n+=1
    avg_unc=db.execute('SELECT AVG(uncertainty) FROM context_hypotheses').fetchone()[0] or 0; avg_conf=db.execute('SELECT AVG(confidence) FROM context_hypotheses').fetchone()[0] or 0
    strategy={'avg_uncertainty':round(avg_unc,3),'avg_confidence':round(avg_conf,3),'recommendation':'read_more_precisely' if avg_unc>.62 else 'normal_exploration','no_word_blacklists':True,'phase':PHASE}
    db.execute('INSERT OR REPLACE INTO learning_strategy_state(key,value,updated_at) VALUES(?,?,?)',('strategy',_json(strategy),now))
    db.execute("INSERT INTO neuromodulator_sleep_events(event_type,summary,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,created_at) VALUES(?,?,?,?,?,?,?,?,?)",('sleep_consolidation',_json({'clusters':n,'avg_uncertainty':round(avg_unc,3),'avg_confidence':round(avg_conf,3)}),nm['dopamine'],nm['serotonin'],nm['glutamate'],nm['gaba'],nm['noradrenaline'],nm['acetylcholine'],now))
    return {'clusters':n,'avg_uncertainty':round(avg_unc,3),'avg_confidence':round(avg_conf,3),'strategy':strategy}

def _stop(self):
    for a in ('stop_requested','cancel','auto_stop'):
        v=getattr(self,a,False)
        if isinstance(v,bool) and v: return True
    return False

def safe_cycle(self,progress=None):
    db=_db(self); ensure_schema(db); seed=seed_queue(db,2000); nm=_nm(db); chunks=_chunks(db,32); roles=Counter(); hyp=0; now=_now(); total=max(1,len(chunks))
    for i,ch in enumerate(chunks,1):
        if _stop(self): break
        chyp=0
        for sent in _sentences(ch['text'],4):
            hid,h=insert_h(db,ch['id'],sent,ch['title'],nm); roles[h['role']]+=1; hyp+=1; chyp+=1
        db.execute("UPDATE reading_queue SET status=?, read_count=COALESCE(read_count,0)+1, last_read=?, updated_at=? WHERE chunk_id=?",('read_candidate' if chyp else 'read_no_candidate',now,now,ch['id']))
        if progress:
            try: progress(i,total,'phase4def context learning')
            except Exception: pass
    update_stats(db); sl=sleep(db,nm); db.commit()
    return [{'status':'phase4def_context_learning_cycle','message':'Phase4d/e/f active: feedback, neuromodulated attention, sleep consolidation. No word blacklists. No facts/relations/questions.','direct_fact_writes':'disabled','direct_relation_writes':'disabled','fact_promotion':'disabled','question_generation':'disabled','no_word_blacklists':True,'learning_mode':LEARNING_MODE,'reading_queue_seed':seed,'totals':{'chunks_read':len(chunks),'hypotheses_created_or_updated':hyp},'hypothesis_roles':dict(roles),'sleep_consolidation':sl}]

def safe_run(self,cycles=5,progress=None):
    for a in ('stop_requested','cancel','auto_stop'):
        if hasattr(self,a) and isinstance(getattr(self,a),bool):
            try: setattr(self,a,False)
            except Exception: pass
    out=[]
    for _ in range(max(1,int(cycles or 1))):
        if _stop(self): out.append([{'status':'stopped','message':'Stop-Anforderung erkannt.'}]); break
        out.append(safe_cycle(self,progress))
    return out

def patch_autonomous_loop(*args,**kwargs):
    try:
        from ki_system.autonomous import AutonomousLoop
    except Exception: return False
    AutonomousLoop.cycle=safe_cycle; AutonomousLoop.run=safe_run
    AutonomousLoop._phase4d_hypothesis_feedback_error_learning=True
    AutonomousLoop._phase4e_neuromodulated_attention_strategy=True
    AutonomousLoop._phase4f_sleep_consolidation_self_improvement=True
    AutonomousLoop._phase4def_context_learning_pack=True
    AutonomousLoop._no_word_blacklists=True
    AutonomousLoop._rollback_learning_mode=LEARNING_MODE
    AutonomousLoop._fact_promotion='disabled'
    return True
try: patch_autonomous_loop()
except Exception: pass

# >>> PHASE4DEF_FIXED2_MARKER_PATCH >>>
# Purpose: final marker/autoload fix. No word blacklists. No fact/relation/question writes.
def patch_autonomous_loop(*args, **kwargs):
    """Patch AutonomousLoop to Phase4def safe core and set diagnostic markers."""
    try:
        AL = args[0] if args else kwargs.get('AutonomousLoop', None)
        if AL is None:
            try:
                from ki_system.autonomous import AutonomousLoop as AL
            except Exception:
                AL = None
        if AL is None:
            return False
        try:
            AL.cycle = safe_cycle
            AL.run = safe_run
        except Exception:
            pass
        setattr(AL, '_phase4a_context_hypothesis_learning_core', True)
        setattr(AL, '_phase4b_neuromodulated_error_learning', True)
        setattr(AL, '_phase4c_sleep_consolidation_self_improvement', True)
        setattr(AL, '_phase4d_hypothesis_feedback_error_learning', True)
        setattr(AL, '_phase4e_neuromodulated_attention_strategy', True)
        setattr(AL, '_phase4f_sleep_consolidation_self_improvement', True)
        setattr(AL, '_phase4def_context_learning_pack', True)
        setattr(AL, '_phase4def_context_learning_pack_fixed2', True)
        setattr(AL, '_no_word_blacklists', True)
        setattr(AL, '_rollback_learning_mode', 'context_hypotheses_with_neuromodulators')
        setattr(AL, '_learning_mode', 'context_hypotheses_with_neuromodulators')
        setattr(AL, '_fact_promotion', 'disabled')
        setattr(AL, '_direct_fact_writes', 'disabled')
        setattr(AL, '_direct_relation_writes', 'disabled')
        setattr(AL, '_question_generation', 'disabled')
        return True
    except Exception as exc:
        print('[PHASE4DEF_FIXED2_MARKER_PATCH_ERROR]', exc)
        return False

try:
    patch_autonomous_loop()
except Exception as _phase4def_fixed2_autopatch_exc:
    print('[PHASE4DEF_FIXED2_AUTOPATCH_ERROR]', _phase4def_fixed2_autopatch_exc)
# <<< PHASE4DEF_FIXED2_MARKER_PATCH <<<

# >>> PHASE4DEF_FIXED3_FINAL_MARKERS_IN_MODULE >>>
def patch_autonomous_loop(*args, **kwargs):
    """Final Phase4def marker patch. No word blacklists. No facts/relations/questions."""
    try:
        AL = args[0] if args else kwargs.get('AutonomousLoop', None)
        if AL is None:
            try:
                from ki_system.autonomous import AutonomousLoop as AL
            except Exception:
                AL = None
        if AL is None:
            return False
        AL.cycle = safe_cycle
        AL.run = safe_run
        markers = {
            '_phase4a_context_hypothesis_learning_core': True,
            '_phase4b_neuromodulated_error_learning': True,
            '_phase4c_sleep_consolidation_self_improvement': True,
            '_phase4d_hypothesis_feedback_error_learning': True,
            '_phase4e_neuromodulated_attention_strategy': True,
            '_phase4f_sleep_consolidation_self_improvement': True,
            '_phase4def_context_learning_pack': True,
            '_phase4def_context_learning_pack_fixed1': True,
            '_phase4def_context_learning_pack_fixed2': True,
            '_phase4def_context_learning_pack_fixed3': True,
            '_no_word_blacklists': True,
            '_rollback_learning_mode': 'context_hypotheses_with_neuromodulators',
            '_learning_mode': 'context_hypotheses_with_neuromodulators',
            '_fact_promotion': 'disabled',
            '_direct_fact_writes': 'disabled',
            '_direct_relation_writes': 'disabled',
            '_question_generation': 'disabled',
        }
        for k, v in markers.items():
            setattr(AL, k, v)
        return True
    except Exception as exc:
        print('[PHASE4DEF_FIXED3_FINAL_MARKERS_IN_MODULE_ERROR]', exc)
        return False
try:
    patch_autonomous_loop()
except Exception as _phase4def_fixed3_module_autopatch_exc:
    print('[PHASE4DEF_FIXED3_MODULE_AUTOPATCH_ERROR]', _phase4def_fixed3_module_autopatch_exc)
# <<< PHASE4DEF_FIXED3_FINAL_MARKERS_IN_MODULE <<<

# >>> PHASE4DEF_FIXED4_COMPAT_MARKERS_IN_MODULE >>>
def _phase4def_set_all_markers(AL):
    marker_values = {
        'phase4d_hypothesis_feedback_error_learning': True,
        'phase4e_neuromodulated_attention_strategy': True,
        'phase4f_sleep_consolidation_self_improvement': True,
        'phase4def_context_learning_pack': True,
        'phase4def_context_learning_pack_fixed4': True,
        '_phase4d_hypothesis_feedback_error_learning': True,
        '_phase4e_neuromodulated_attention_strategy': True,
        '_phase4f_sleep_consolidation_self_improvement': True,
        '_phase4def_context_learning_pack': True,
        '_phase4def_context_learning_pack_fixed1': True,
        '_phase4def_context_learning_pack_fixed2': True,
        '_phase4def_context_learning_pack_fixed3': True,
        '_phase4def_context_learning_pack_fixed4': True,
        'no_word_blacklists': True,
        '_no_word_blacklists': True,
        'learning_mode': 'context_hypotheses_with_neuromodulators',
        '_learning_mode': 'context_hypotheses_with_neuromodulators',
        '_rollback_learning_mode': 'context_hypotheses_with_neuromodulators',
        'fact_promotion': 'disabled',
        '_fact_promotion': 'disabled',
        '_direct_fact_writes': 'disabled',
        '_direct_relation_writes': 'disabled',
        '_question_generation': 'disabled',
    }
    for key, value in marker_values.items():
        setattr(AL, key, value)
    return AL

def patch_autonomous_loop(*args, **kwargs):
    """Final compatible Phase4def marker patch. Sets both old and new marker names."""
    try:
        AL = args[0] if args else kwargs.get('AutonomousLoop', None)
        if AL is None:
            try:
                from ki_system.autonomous import AutonomousLoop as AL
            except Exception:
                AL = None
        if AL is None:
            return False
        AL.cycle = safe_cycle
        AL.run = safe_run
        _phase4def_set_all_markers(AL)
        return True
    except Exception as exc:
        print('[PHASE4DEF_FIXED4_COMPAT_MARKERS_ERROR]', exc)
        return False
try:
    patch_autonomous_loop()
except Exception as _phase4def_fixed4_module_autopatch_exc:
    print('[PHASE4DEF_FIXED4_MODULE_AUTOPATCH_ERROR]', _phase4def_fixed4_module_autopatch_exc)
# <<< PHASE4DEF_FIXED4_COMPAT_MARKERS_IN_MODULE <<<

# >>> PHASE4DEF_SCHEMA_RUNTIME_FIXED5 >>>
# Runtime schema guard: fixes older Phase3d9/Phase4abc tables before every cycle.
def _phase4def_fixed5_get_connection(loop_self):
    mem = getattr(loop_self, 'mem', None)
    if mem is None:
        return None
    if hasattr(mem, 'db'):
        return mem.db
    if hasattr(mem, 'execute'):
        return mem
    return None

def _phase4def_fixed5_migrate_runtime_schema(con):
    try:
        cur = con.cursor()
    except Exception:
        return []
    changed = []
    def exists(table):
        return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None
    def colset(table):
        if not exists(table): return set()
        return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    def add(table, name, typ):
        if name not in colset(table):
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
            changed.append(f"{table}.{name}")
    cur.execute("CREATE TABLE IF NOT EXISTS context_learning_events(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    for name, typ in [('hypothesis_id','INTEGER'),('event_type','TEXT'),('role','TEXT'),('details','TEXT'),('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),('created_at','INTEGER DEFAULT 0')]:
        add('context_learning_events', name, typ)
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, feedback_type TEXT, feedback_score REAL DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_error_events(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, error_type TEXT, role TEXT, severity REAL DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_revisions(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, old_role TEXT, new_role TEXT, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS chunk_attention_scores(chunk_id INTEGER PRIMARY KEY, attention_score REAL DEFAULT 0, novelty REAL DEFAULT 0, uncertainty REAL DEFAULT 0, reward REAL DEFAULT 0, fatigue REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS attention_queue_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS reading_strategy_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_clusters(id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, signature TEXT, size INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(hypothesis_id INTEGER PRIMARY KEY, stability_score REAL DEFAULT 0, evidence_count INTEGER DEFAULT 0, contradiction_count INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events(id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, details TEXT, dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS rollback_safe_core_state(key TEXT PRIMARY KEY, value TEXT)")
    for k,v in {'phase':"'phase4def_schema_runtime_fixed5'", 'no_word_blacklists':"'true'", 'learning_mode':"'context_hypotheses_with_neuromodulators'", 'fact_promotion':"'disabled'", 'direct_fact_writes':"'disabled'", 'direct_relation_writes':"'disabled'", 'question_generation':"'disabled'"}.items():
        cur.execute("INSERT OR REPLACE INTO rollback_safe_core_state(key,value) VALUES(?,?)", (k,v))
    try: con.commit()
    except Exception: pass
    return changed

_phase4def_fixed5_original_safe_cycle = safe_cycle
_phase4def_fixed5_original_safe_run = safe_run

def safe_cycle(self, progress=None):
    con = _phase4def_fixed5_get_connection(self)
    if con is not None:
        _phase4def_fixed5_migrate_runtime_schema(con)
    return _phase4def_fixed5_original_safe_cycle(self, progress)

def safe_run(self, cycles=1, progress=None):
    con = _phase4def_fixed5_get_connection(self)
    if con is not None:
        _phase4def_fixed5_migrate_runtime_schema(con)
    return _phase4def_fixed5_original_safe_run(self, cycles, progress)

def patch_autonomous_loop(*args, **kwargs):
    try:
        AL = args[0] if args else kwargs.get('AutonomousLoop', None)
        if AL is None:
            try:
                from ki_system.autonomous import AutonomousLoop as AL
            except Exception:
                AL = None
        if AL is None: return False
        AL.cycle = safe_cycle
        AL.run = safe_run
        for k,v in {'phase4d_hypothesis_feedback_error_learning':True,'phase4e_neuromodulated_attention_strategy':True,'phase4f_sleep_consolidation_self_improvement':True,'phase4def_context_learning_pack':True,'phase4def_schema_runtime_fixed5':True,'_phase4d_hypothesis_feedback_error_learning':True,'_phase4e_neuromodulated_attention_strategy':True,'_phase4f_sleep_consolidation_self_improvement':True,'_phase4def_context_learning_pack':True,'_phase4def_schema_runtime_fixed5':True,'_no_word_blacklists':True,'no_word_blacklists':True,'_learning_mode':'context_hypotheses_with_neuromodulators','learning_mode':'context_hypotheses_with_neuromodulators','_rollback_learning_mode':'context_hypotheses_with_neuromodulators','_fact_promotion':'disabled','fact_promotion':'disabled'}.items():
            setattr(AL,k,v)
        return True
    except Exception as exc:
        print('[PHASE4DEF_SCHEMA_RUNTIME_FIXED5_PATCH_ERROR]', exc)
        return False
try:
    patch_autonomous_loop()
except Exception as _phase4def_schema_fixed5_autopatch_exc:
    print('[PHASE4DEF_SCHEMA_RUNTIME_FIXED5_AUTOPATCH_ERROR]', _phase4def_schema_fixed5_autopatch_exc)
# <<< PHASE4DEF_SCHEMA_RUNTIME_FIXED5 <<<



# >>> PHASE4DEF_SCHEMA_CANONICALIZER_FIXED8_AUTOLOAD >>>
try:
    from ki_system import v8_phase4def_schema_canonicalizer_fixed8 as _phase4def_fixed8_schema
    _phase4def_fixed8_schema.patch_module()
except Exception as _phase4def_fixed8_exc:
    print('[PHASE4DEF_SCHEMA_CANONICALIZER_FIXED8_AUTOLOAD_ERROR]', _phase4def_fixed8_exc)
# <<< PHASE4DEF_SCHEMA_CANONICALIZER_FIXED8_AUTOLOAD <<<
