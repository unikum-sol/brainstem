from __future__ import annotations
import json, time
SCHEMA_VERSION = "v8_phase3d6d_true_safe_brain_cycle"

def ensure_corpus_schema(memory):
    if getattr(memory, "readonly", False): return
    with memory.lock:
        db=memory.db
        db.execute("""CREATE TABLE IF NOT EXISTS reading_queue(
            chunk_id INTEGER PRIMARY KEY, priority REAL DEFAULT 0, reason TEXT,
            attention_score REAL DEFAULT 0, read_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending', last_read INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_reading_queue_status_priority ON reading_queue(status, priority DESC)")
        db.execute("""CREATE TABLE IF NOT EXISTS candidate_relations(
            id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT, relation TEXT, object TEXT,
            confidence REAL DEFAULT 0, source_chunk_id INTEGER, source_document_title TEXT, context_title TEXT,
            definition_score REAL DEFAULT 0, fragment_score REAL DEFAULT 0, license_score REAL DEFAULT 0,
            alignment_score REAL DEFAULT 0, novelty_score REAL DEFAULT 0,
            confirmation_count INTEGER DEFAULT 0, rejection_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'candidate', reject_reason TEXT, created_at INTEGER, updated_at INTEGER)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_candidate_relations_sro ON candidate_relations(subject, relation, object)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_candidate_relations_status ON candidate_relations(status, confidence DESC)")
        db.execute("""CREATE TABLE IF NOT EXISTS language_patterns(
            pattern TEXT PRIMARY KEY, pattern_type TEXT, success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0, confidence REAL DEFAULT 0,
            inhibition_score REAL DEFAULT 0, attention_score REAL DEFAULT 0,
            last_examples_json TEXT, created_at INTEGER, updated_at INTEGER)""")
        db.execute("""CREATE TABLE IF NOT EXISTS negative_patterns(
            pattern TEXT PRIMARY KEY, reason TEXT, count INTEGER DEFAULT 0,
            examples_json TEXT, gaba_weight REAL DEFAULT 0, last_seen INTEGER)""")
        db.execute("""CREATE TABLE IF NOT EXISTS word_roles(
            token TEXT PRIMARY KEY, role TEXT, confidence REAL DEFAULT 0,
            count INTEGER DEFAULT 0, examples_json TEXT, updated_at INTEGER)""")
        db.execute("CREATE TABLE IF NOT EXISTS corpus_reader_state(key TEXT PRIMARY KEY, value_json TEXT, updated_at INTEGER)")
        db.execute("INSERT OR REPLACE INTO corpus_reader_state(key,value_json,updated_at) VALUES(?,?,?)", ("schema_version", json.dumps(SCHEMA_VERSION), int(time.time())))
        db.commit()

def _append_json(old_json, item, limit=8):
    try:
        arr=json.loads(old_json or "[]")
        if not isinstance(arr,list): arr=[]
    except Exception: arr=[]
    arr.append(item)
    return json.dumps(arr[-limit:], ensure_ascii=False)

def upsert_language_pattern(memory, pattern, pattern_type, success, example=""):
    ensure_corpus_schema(memory); pattern=(pattern or "").strip().lower()[:160]
    if not pattern: return
    now=int(time.time())
    with memory.lock:
        row=memory.db.execute("SELECT * FROM language_patterns WHERE pattern=?", (pattern,)).fetchone()
        if row:
            sc=int(row["success_count"] or 0)+(1 if success else 0); fc=int(row["failure_count"] or 0)+(0 if success else 1)
            total=max(1, sc+fc); conf=sc/total; inhib=fc/total; ex=_append_json(row["last_examples_json"], example)
            memory.db.execute("UPDATE language_patterns SET pattern_type=?,success_count=?,failure_count=?,confidence=?,inhibition_score=?,attention_score=?,last_examples_json=?,updated_at=? WHERE pattern=?", (pattern_type,sc,fc,conf,inhib,conf,ex,now,pattern))
        else:
            conf=1.0 if success else 0.0; inhib=0.0 if success else 1.0
            memory.db.execute("INSERT INTO language_patterns(pattern,pattern_type,success_count,failure_count,confidence,inhibition_score,attention_score,last_examples_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (pattern,pattern_type,1 if success else 0,0 if success else 1,conf,inhib,conf,json.dumps([example],ensure_ascii=False),now,now))
        memory.db.commit()

def upsert_negative_pattern(memory, pattern, reason, example=""):
    ensure_corpus_schema(memory); pattern=(pattern or "").strip().lower()[:160]
    if not pattern: return
    reason=(reason or "unknown")[:80]; now=int(time.time())
    with memory.lock:
        row=memory.db.execute("SELECT * FROM negative_patterns WHERE pattern=?", (pattern,)).fetchone()
        if row:
            cnt=int(row["count"] or 0)+1; ex=_append_json(row["examples_json"], example); gaba=min(1.0,0.15+cnt/20.0)
            memory.db.execute("UPDATE negative_patterns SET reason=?,count=?,examples_json=?,gaba_weight=?,last_seen=? WHERE pattern=?", (reason,cnt,ex,gaba,now,pattern))
        else:
            memory.db.execute("INSERT INTO negative_patterns(pattern,reason,count,examples_json,gaba_weight,last_seen) VALUES(?,?,?,?,?,?)", (pattern,reason,1,json.dumps([example],ensure_ascii=False),0.2,now))
        memory.db.commit()

def upsert_word_role(memory, token, role, confidence=0.8, example=""):
    ensure_corpus_schema(memory); token=(token or "").strip().lower()[:80]; role=(role or "").strip()[:80]
    if not token or not role: return
    now=int(time.time())
    with memory.lock:
        row=memory.db.execute("SELECT * FROM word_roles WHERE token=?", (token,)).fetchone()
        if row:
            cnt=int(row["count"] or 0)+1; old=float(row["confidence"] or 0); conf=min(1.0,(old*(cnt-1)+confidence)/cnt); ex=_append_json(row["examples_json"], example)
            memory.db.execute("UPDATE word_roles SET role=?,confidence=?,count=?,examples_json=?,updated_at=? WHERE token=?", (role,conf,cnt,ex,now,token))
        else:
            memory.db.execute("INSERT INTO word_roles(token,role,confidence,count,examples_json,updated_at) VALUES(?,?,?,?,?,?)", (token,role,float(confidence),1,json.dumps([example],ensure_ascii=False),now))
        memory.db.commit()

def insert_candidate(memory, subject, relation, obj, confidence=0, source_chunk_id=None, source_document_title="", context_title="", scores=None, status="candidate", reject_reason=None):
    ensure_corpus_schema(memory); scores=scores or {}; now=int(time.time())
    subject=(subject or "").strip(); relation=(relation or "").strip(); obj=(obj or "").strip()
    if not subject or not relation or not obj: return None
    with memory.lock:
        row=memory.db.execute("SELECT id,confirmation_count,rejection_count FROM candidate_relations WHERE lower(subject)=lower(?) AND lower(relation)=lower(?) AND lower(object)=lower(?) LIMIT 1", (subject,relation,obj)).fetchone()
        if row:
            cc=int(row["confirmation_count"] or 0)+(1 if status!="rejected" else 0); rc=int(row["rejection_count"] or 0)+(1 if status=="rejected" else 0)
            memory.db.execute("UPDATE candidate_relations SET confidence=MAX(confidence,?), confirmation_count=?, rejection_count=?, status=CASE WHEN status='promoted' THEN status ELSE ? END, reject_reason=COALESCE(?, reject_reason), updated_at=? WHERE id=?", (float(confidence),cc,rc,status,reject_reason,now,row["id"]))
            cid=row["id"]
        else:
            memory.db.execute("""INSERT INTO candidate_relations(subject,relation,object,confidence,source_chunk_id,source_document_title,context_title,definition_score,fragment_score,license_score,alignment_score,novelty_score,confirmation_count,rejection_count,status,reject_reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (subject,relation,obj,float(confidence),source_chunk_id,source_document_title,context_title,float(scores.get("definition_score",0)),float(scores.get("fragment_score",0)),float(scores.get("license_score",0)),float(scores.get("alignment_score",0)),float(scores.get("novelty_score",0)),1 if status!="rejected" else 0,1 if status=="rejected" else 0,status,reject_reason,now,now))
            cid=memory.db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        memory.db.commit(); return cid
