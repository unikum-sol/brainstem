
# PHASE3D9_FORCE_CLEANUP_SAFE_CORE_FIXED5
from __future__ import annotations
import time, json, re
PHASE = "phase3d9_force_cleanup_safe_core_fixed5"

def _get_db_from_self(self):
    for name in ("mem", "memory", "db", "m"):
        obj = getattr(self, name, None)
        if obj is None: continue
        if hasattr(obj, "db"): return obj.db
        if hasattr(obj, "execute") and hasattr(obj, "commit"): return obj
    return None

def _ensure_schema(db):
    cur = db.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS context_hypotheses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, subject TEXT, relation TEXT, object TEXT,
        hypothesis_role TEXT, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1, context TEXT, source TEXT,
        neuromodulator_state TEXT, status TEXT DEFAULT 'hypothesis', created_at INTEGER, updated_at INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS context_learning_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, message TEXT, payload TEXT, created_at INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS rollback_safe_core_state (
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)""")
    now = int(time.time())
    state = {"phase":PHASE,"no_word_blacklists":True,"learning_mode":"context_hypotheses_with_neuromodulators",
             "fact_promotion":"disabled","direct_fact_writes":"disabled","direct_relation_writes":"disabled"}
    for k,v in state.items():
        cur.execute("INSERT OR REPLACE INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?)", (k,json.dumps(v,ensure_ascii=False),now))
    db.commit()

def _neuromodulator_snapshot(self):
    st = {}
    for source_name in ("neuromodulators", "neuromodulator_manager", "modulators"):
        obj = getattr(self, source_name, None)
        if obj is None: continue
        for attr in ("state", "values"):
            val = getattr(obj, attr, None)
            if isinstance(val, dict): st.update(val)
            elif val is not None:
                for k in ("dopamine","serotonin","glutamate","gaba","noradrenaline","acetylcholine"):
                    if hasattr(val,k): st[k]=getattr(val,k)
    return st

def _role_guess(subject, relation, obj):
    s=(subject or '').strip(); r=(relation or '').strip(); o=(obj or '').strip(); lo=o.lower()
    if not s or not o: return 'context_fragment',0.15,0.85
    if len(s)>90 or len(o)>180: return 'context_fragment',0.25,0.75
    if r in ('located_in','part_of','has_name','has_codename','has_original_domain','uses_socket'):
        return 'relation_hypothesis',0.55,0.45
    if r in ('definition','is_a'):
        if any(tok in lo for tok in ('protokoll','programm','software','schnittstelle','framework','dateiformat','mikroprozessor','prozessor','betriebssystem','standard','system','architektur')):
            return 'definition_hypothesis',0.55,0.45
        if any(tok in lo for tok in ('verfügbar','fertig','aktiv','notwendig','möglich','kompatibel','geeignet','kostenlos')):
            return 'state_hypothesis',0.45,0.55
        if any(tok in lo for tok in ('erforderlich','voraussetzung','benötigt','nötig')):
            return 'requirement_hypothesis',0.45,0.55
        return 'raw_hypothesis',0.35,0.65
    return 'raw_hypothesis',0.3,0.7

def _extract_lightweight_hypotheses(self, limit=48):
    db=_get_db_from_self(self)
    if db is None: return {"status":"no_db","created_hypotheses":0,"message":"No DB handle available"}
    _ensure_schema(db); cur=db.cursor(); now=int(time.time())
    tables={r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    created=0; scanned=0; samples=[]
    if 'chunks' in tables:
        rows=[]
        if 'reading_queue' in tables:
            try:
                rows=cur.execute("""SELECT c.id, COALESCE(c.title,''), COALESCE(c.text,'')
                    FROM reading_queue rq JOIN chunks c ON c.id=rq.chunk_id
                    WHERE COALESCE(rq.status,'pending') IN ('pending','read_candidate','read_no_candidate')
                    ORDER BY COALESCE(rq.priority,0) DESC, rq.chunk_id ASC LIMIT ?""", (limit,)).fetchall()
            except Exception: rows=[]
        if not rows:
            cols=[x[1] for x in cur.execute('PRAGMA table_info(chunks)').fetchall()]
            idcol='id' if 'id' in cols else ('chunk_id' if 'chunk_id' in cols else None)
            textcol='text' if 'text' in cols else ('content' if 'content' in cols else None)
            titlecol='title' if 'title' in cols else None
            if idcol and textcol:
                q = "SELECT {idc}, {ttl}, COALESCE({txt},'') FROM chunks ORDER BY {idc} ASC LIMIT ?".format(
                    idc=idcol, ttl=("COALESCE("+titlecol+",'')" if titlecol else "''"), txt=textcol)
                rows=cur.execute(q,(limit,)).fetchall()
        for chunk_id,title,text in rows:
            scanned+=1; text=(text or '').strip()
            if not text: continue
            for sent in re.split(r'(?<=[.!?])\s+', text)[:3]:
                m=re.search(r'^(.{2,80}?)\s+(ist|sind|bezeichnet|war|wird als)\s+(.{2,160})', sent.strip(), re.I)
                if not m: continue
                subj=m.group(1).strip(' -:;,.\n\t'); verb=m.group(2).lower(); obj=m.group(3).strip(' -:;,.\n\t')
                rel='definition' if verb in ('bezeichnet','wird als') else 'is_a'
                role,conf,unc=_role_guess(subj,rel,obj); nm=_neuromodulator_snapshot(self)
                cur.execute("""INSERT INTO context_hypotheses(chunk_id,subject,relation,object,hypothesis_role,confidence,uncertainty,context,source,neuromodulator_state,status,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (chunk_id,subj,rel,obj,role,conf,unc,title or '',PHASE,json.dumps(nm,ensure_ascii=False),'hypothesis',now,now))
                created+=1
                if len(samples)<8: samples.append({'hypothesis':[subj,rel,obj],'role':role,'confidence':conf,'uncertainty':unc})
                break
    cur.execute("INSERT INTO context_learning_events(event_type,message,payload,created_at) VALUES(?,?,?,?)", ("safe_core_cycle","Context hypothesis learning cycle completed without facts/relations/questions.",json.dumps({'scanned':scanned,'created':created,'phase':PHASE},ensure_ascii=False),now))
    db.commit()
    return {'status':'context_hypothesis_cycle','scanned_chunks':scanned,'created_hypotheses':created,'samples':samples}

def safe_cycle(self,*args,**kwargs):
    result=_extract_lightweight_hypotheses(self, limit=int(kwargs.get('limit',48) or 48))
    return [{'status':'true_safe_autonomous_loop_phase3d9_cleanup_safe_core_fixed5','message':'SAFE CORE: Kontext-Hypothesenlernen mit digitalen Botenstoffen. Keine Wort-Blacklists. Keine facts/relations/questions.','word_blacklists':'disabled','learning_mode':'context_hypotheses_with_neuromodulators','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'disabled','diagnostic_reseed':'disabled','legacy_question_cycle':'disabled','fact_promotion':'disabled','context_learning':result}]

def _stop_requested(self):
    for attr in ('auto_stop','cancel','stop_requested'):
        val=getattr(self,attr,False)
        if isinstance(val,bool) and val: return True
    return False

def safe_run(self,cycles=1,progress=None,*args,**kwargs):
    out=[]
    try: cycles=int(cycles or 1)
    except Exception: cycles=1
    cycles=max(1,min(cycles,5))
    for i in range(1,cycles+1):
        if _stop_requested(self): out.append([{'status':'stopped','message':'Stop-Anforderung erkannt.'}]); break
        if progress:
            try: progress(i,cycles,'context hypothesis learning')
            except TypeError:
                try: progress(i,cycles)
                except Exception: pass
            except Exception: pass
        out.append(safe_cycle(self))
    return out

def apply_patch():
    from ki_system.autonomous import AutonomousLoop
    AutonomousLoop.cycle=safe_cycle; AutonomousLoop.run=safe_run
    AutonomousLoop._phase3d8_to_3d6g_rollback_fixed2=True
    AutonomousLoop._phase3d8_to_3d6g_rollback_fixed3=True
    AutonomousLoop._phase3d9_cleanup_safe_core=True
    AutonomousLoop._phase3d9_force_cleanup_safe_core_fixed4=True
    AutonomousLoop._phase3d9_force_cleanup_safe_core_fixed5=True
    AutonomousLoop._no_word_blacklists=True
    AutonomousLoop._rollback_learning_mode='context_hypotheses_with_neuromodulators'
    AutonomousLoop._learning_mode='context_hypotheses_with_neuromodulators'
    AutonomousLoop._fact_promotion='disabled'
    return AutonomousLoop
try:
    apply_patch()
except Exception:
    pass
