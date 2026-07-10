
# V8 phase3d8 -> phase3d6g rollback SAFE CORE FIXED2
from __future__ import annotations
import re, time, json, sqlite3
PATCH_MARKER = "PHASE3D8_TO_3D6G_ROLLBACK_SAFE_CORE_FIXED2"

def _now(): return int(time.time())

def _get_db_from_loop(loop):
    mem = getattr(loop,"mem",None) or getattr(loop,"memory",None) or getattr(loop,"db",None)
    if mem is None: return None, None
    db = getattr(mem,"db",None) or getattr(mem,"conn",None) or getattr(mem,"con",None)
    if isinstance(db, sqlite3.Connection): return mem, db
    path = getattr(mem,"path",None)
    if path:
        try: return mem, sqlite3.connect(str(path), check_same_thread=False)
        except Exception: return mem, None
    return mem, None

def _table_exists(cur, name):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None

def _columns(cur, table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]

def ensure_schema(db):
    cur=db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS context_hypotheses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chunk_id INTEGER,
        title TEXT,
        text_sample TEXT,
        hypothesis_text TEXT,
        role_guess TEXT,
        confidence REAL DEFAULT 0.0,
        uncertainty REAL DEFAULT 1.0,
        evidence_count INTEGER DEFAULT 1,
        error_count INTEGER DEFAULT 0,
        learning_status TEXT DEFAULT 'open_hypothesis',
        neuromodulator_snapshot TEXT,
        source TEXT DEFAULT 'rollback_safe_core_3d6g_fixed2',
        created_at INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0,
        UNIQUE(chunk_id,hypothesis_text)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS context_learning_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT,
        chunk_id INTEGER,
        role_guess TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rollback_safe_core_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    db.commit()

def _state_get(cur,key,default=None):
    row=cur.execute("SELECT value FROM rollback_safe_core_state WHERE key=?",(key,)).fetchone()
    return row[0] if row else default

def _state_set(cur,key,value):
    cur.execute("INSERT OR REPLACE INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?)",(key,str(value),_now()))

def _neuromodulator_snapshot(db):
    cur=db.cursor(); snap={"dopamine":0.5,"serotonin":0.6,"glutamate":0.4,"gaba":0.4,"noradrenaline":0.3,"acetylcholine":0.5}
    try:
        if _table_exists(cur,"neuromodulator_state"):
            cols=_columns(cur,"neuromodulator_state"); row=cur.execute("SELECT * FROM neuromodulator_state LIMIT 1").fetchone()
            if row:
                d=dict(zip(cols,row))
                for k in list(snap):
                    if k in d and d[k] is not None:
                        try: snap[k]=float(d[k])
                        except Exception: pass
    except Exception: pass
    return snap

def _guess_role(text):
    t=(text or "").strip()
    if not t: return "empty_fragment",0.0,1.0
    if len(t)>600: return "long_context_fragment",0.20,0.80
    if re.search(r"\b(ist|sind|war|waren|wird|werden|bezeichnet|nennt|besteht|gehört|enthält|verwendet)\b",t,re.I):
        if re.search(r"\b(ein|eine|eines|einem|einen)\b",t,re.I): return "definition_hypothesis",0.35,0.65
        return "statement_hypothesis",0.30,0.70
    if re.search(r"\d{4}|Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember",t):
        return "temporal_hypothesis",0.25,0.75
    if len(t.split())<=4: return "short_context_fragment",0.15,0.85
    return "raw_hypothesis",0.25,0.75

def _split_sentences(text,max_items=3):
    if not text: return []
    text=re.sub(r"\s+"," ",str(text)).strip()
    if not text: return []
    parts=re.split(r"(?<=[.!?])\s+",text)
    out=[]
    for p in parts:
        p=p.strip()
        if 25<=len(p)<=500: out.append(p)
        if len(out)>=max_items: break
    if not out and len(text)>=25: out=[text[:500]]
    return out

def _select_chunks(db,limit=48):
    cur=db.cursor()
    if not _table_exists(cur,"chunks"): return []
    cols=_columns(cur,"chunks")
    id_col="id" if "id" in cols else ("chunk_id" if "chunk_id" in cols else cols[0])
    title_col="title" if "title" in cols else None
    text_col=None
    for c in ("text","content","chunk","body"):
        if c in cols: text_col=c; break
    if text_col is None:
        text_cols=[c for c in cols if c.lower() not in (id_col.lower(),"doc_id","document_id")]
        text_col=text_cols[-1] if text_cols else id_col
    last=_state_get(cur,"last_chunk_id","0")
    try: last_i=int(last)
    except Exception: last_i=0
    select_title=title_col if title_col else "''"
    rows=cur.execute(f"SELECT {id_col}, {select_title}, {text_col} FROM chunks WHERE {id_col}>? ORDER BY {id_col} LIMIT ?",(last_i,limit)).fetchall()
    if not rows:
        rows=cur.execute(f"SELECT {id_col}, {select_title}, {text_col} FROM chunks ORDER BY {id_col} LIMIT ?",(limit,)).fetchall()
    return rows

def safe_cycle(self, progress=None, limit=48):
    mem,db=_get_db_from_loop(self)
    if db is None: return [{"status":"rollback_safe_core_error","message":"Keine SQLite-Verbindung gefunden."}]
    ensure_schema(db); cur=db.cursor(); chunks=_select_chunks(db,limit); snap=_neuromodulator_snapshot(db)
    inserted=updated=seen=0; role_counts={}; samples=[]; last_chunk_id=None; total=max(1,len(chunks))
    for i,row in enumerate(chunks,1):
        chunk_id,title,text=row[0],row[1],row[2]; last_chunk_id=chunk_id
        if callable(progress):
            try: progress(i,total,"3d6g rollback context learning")
            except TypeError:
                try: progress(i,total)
                except Exception: pass
        for sent in _split_sentences(text,3):
            role,conf,unc=_guess_role(sent); role_counts[role]=role_counts.get(role,0)+1; seen+=1
            try:
                cur.execute("""
                INSERT INTO context_hypotheses(chunk_id,title,text_sample,hypothesis_text,role_guess,confidence,uncertainty,neuromodulator_snapshot,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(chunk_id,hypothesis_text) DO UPDATE SET evidence_count=evidence_count+1, confidence=excluded.confidence, uncertainty=excluded.uncertainty, role_guess=excluded.role_guess, neuromodulator_snapshot=excluded.neuromodulator_snapshot, updated_at=excluded.updated_at
                """,(chunk_id,title or "",str(text)[:300],sent,role,conf,unc,json.dumps(snap,ensure_ascii=False),_now(),_now()))
                inserted += 1
                if len(samples)<8: samples.append({"chunk_id":chunk_id,"title":title,"role_guess":role,"hypothesis":sent[:180]})
            except Exception as exc:
                cur.execute("INSERT INTO context_learning_events(event_type,chunk_id,role_guess,details,created_at) VALUES(?,?,?,?,?)",("hypothesis_store_error",chunk_id,role,str(exc),_now()))
    if last_chunk_id is not None: _state_set(cur,"last_chunk_id",last_chunk_id)
    _state_set(cur,"last_run_at",_now()); _state_set(cur,"mode","3d6g_rollback_no_word_blacklists")
    db.commit()
    counts={}
    for t in ("facts","relations","questions","context_hypotheses"):
        try: counts[t]=cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if _table_exists(cur,t) else None
        except Exception: counts[t]="error"
    return [{"status":"true_safe_corpus_reader_phase3d6g_rollback_fixed2","message":"Safe-Core aktiv: Kontext-Hypothesen statt Wort-Blacklists, keine facts/relations/questions.","word_blacklists":"disabled_not_loaded","learning_mode":"context_hypotheses_with_neuromodulators","chunks_read":len(chunks),"hypotheses_seen":seen,"hypotheses_inserted_or_updated":inserted+updated,"role_counts":role_counts,"neuromodulators":snap,"samples":samples,"safety_counts":counts,"direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_generation":"disabled","fact_promotion":"disabled"}]

def _stop_requested(self):
    for name in ("stop_requested","auto_stop","cancel","cancelled","should_stop"):
        v=getattr(self,name,False)
        if isinstance(v,bool) and v: return True
    return False

def safe_run(self,cycles=5,progress=None):
    try: cycles=int(cycles or 1)
    except Exception: cycles=1
    cycles=max(1,min(cycles,5)); out=[]
    for i in range(1,cycles+1):
        if _stop_requested(self):
            out.append([{"status":"stopped","message":"Stop-Anforderung erkannt."}]); break
        if callable(progress):
            try: progress(i,cycles,"3d6g rollback safe core")
            except TypeError:
                try: progress(i,cycles)
                except Exception: pass
        out.append(safe_cycle(self,progress=progress))
    return out

def apply_patch():
    try: from . import autonomous
    except Exception: return False
    cls=getattr(autonomous,"AutonomousLoop",None)
    if cls is None: return False
    cls.cycle=safe_cycle; cls.run=safe_run
    cls._phase3d8_to_3d6g_rollback_fixed2=True
    cls._phase3d8_to_3d6g_no_word_blacklists=True
    return True
try: apply_patch()
except Exception: pass
