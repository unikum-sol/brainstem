from __future__ import annotations
import sqlite3, json, time, threading, csv
from pathlib import Path
class Memory:
    def __init__(self,path='ki_memory.sqlite3',readonly=False):
        self.path=Path(path); self.readonly=readonly; self.lock=threading.RLock()
        if readonly:
            self.db=sqlite3.connect(f'file:{self.path.resolve().as_posix()}?mode=ro',uri=True,check_same_thread=False)
        else:
            self.path.parent.mkdir(parents=True,exist_ok=True); self.db=sqlite3.connect(str(self.path),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        if not readonly: self._init()
    def _json(self,o): return json.dumps(o,ensure_ascii=False,default=str)
    def _init(self):
        sql="""PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;
        CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,path TEXT,title TEXT,kind TEXT,metadata_json TEXT,source_score REAL DEFAULT 1,created_at INTEGER);
        CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,document_id INTEGER,chunk_index INTEGER,text TEXT,token_count INTEGER,metadata_json TEXT,import_key TEXT UNIQUE);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text,title,path,content='');
        CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY,subject TEXT,relation TEXT,value TEXT,confidence REAL,source_chunk_id INTEGER,created_at INTEGER,UNIQUE(subject,relation,value));
        CREATE TABLE IF NOT EXISTS relations(id INTEGER PRIMARY KEY,source TEXT,relation TEXT,target TEXT,confidence REAL,source_chunk_id INTEGER,created_at INTEGER,UNIQUE(source,relation,target));
        CREATE TABLE IF NOT EXISTS ontology(id INTEGER PRIMARY KEY,child TEXT,parent TEXT,relation TEXT,confidence REAL,fact_id INTEGER,created_at INTEGER,UNIQUE(child,parent,relation));
        CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY,question TEXT UNIQUE,priority REAL DEFAULT .5,status TEXT DEFAULT 'open',created_at INTEGER,updated_at INTEGER);
        CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY,role TEXT,text TEXT,topic TEXT,created_at INTEGER);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,event TEXT,data_json TEXT,created_at INTEGER);
        CREATE TABLE IF NOT EXISTS contradictions(id INTEGER PRIMARY KEY,subject TEXT,relation TEXT,value_a TEXT,value_b TEXT,status TEXT,details_json TEXT,created_at INTEGER);
        CREATE TABLE IF NOT EXISTS clusters(id INTEGER PRIMARY KEY,name TEXT,terms_json TEXT,score REAL,created_at INTEGER);
        CREATE TABLE IF NOT EXISTS import_state(path TEXT PRIMARY KEY,last_article INTEGER,last_chunk INTEGER,status TEXT,updated_at INTEGER);
        CREATE TABLE IF NOT EXISTS topic_context(id INTEGER PRIMARY KEY CHECK(id=1),topic TEXT,user_text TEXT,last_sources_json TEXT,updated_at INTEGER);"""
        with self.lock: self.db.executescript(sql); self.db.commit()
    def rows(self,sql,params=()):
        with self.lock: return list(self.db.execute(sql,params))
    def add_document(self,path,title,kind,metadata=None,score=1.0):
        if self.readonly: raise PermissionError('readonly')
        with self.lock:
            cur=self.db.execute('INSERT INTO documents(path,title,kind,metadata_json,source_score,created_at) VALUES(?,?,?,?,?,?)',(str(path),title,kind,self._json(metadata or {}),score,int(time.time()))); self.db.commit(); return cur.lastrowid
    def add_chunk(self,doc_id,idx,text,metadata=None,import_key=None):
        if self.readonly: raise PermissionError('readonly')
        with self.lock:
            cur=self.db.execute('INSERT OR IGNORE INTO chunks(document_id,chunk_index,text,token_count,metadata_json,import_key) VALUES(?,?,?,?,?,?)',(doc_id,idx,text,len(text.split()),self._json(metadata or {}),import_key))
            if cur.rowcount:
                cid=cur.lastrowid; d=self.db.execute('SELECT title,path FROM documents WHERE id=?',(doc_id,)).fetchone(); self.db.execute('INSERT INTO chunks_fts(rowid,text,title,path) VALUES(?,?,?,?)',(cid,text,d['title'],d['path']))
            self.db.commit(); return cur.lastrowid if cur.rowcount else None
    def iter_chunks(self): return self.rows('SELECT chunks.*,documents.title,documents.path,documents.kind,documents.source_score FROM chunks JOIN documents ON documents.id=chunks.document_id')
    def fts_search(self,q,limit=20): return self.rows('SELECT rowid,text,title,path,bm25(chunks_fts) AS score FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?',(q,limit))
    def add_fact(self,s,r,v,c=.7,chunk_id=None):
        if self.readonly: raise PermissionError('readonly')
        with self.lock:
            cur=self.db.execute('INSERT OR IGNORE INTO facts(subject,relation,value,confidence,source_chunk_id,created_at) VALUES(?,?,?,?,?,?)',(s,r,v,c,chunk_id,int(time.time()))); self.db.commit(); return cur.lastrowid if cur.rowcount else None
    def add_relation(self,s,r,t,c=.7,chunk_id=None):
        if self.readonly: raise PermissionError('readonly')
        with self.lock:
            cur=self.db.execute('INSERT OR IGNORE INTO relations(source,relation,target,confidence,source_chunk_id,created_at) VALUES(?,?,?,?,?,?)',(s,r,t,c,chunk_id,int(time.time()))); self.db.commit(); return cur.lastrowid if cur.rowcount else None
    def add_ontology(self,child,parent,rel='is_a',conf=.7,fact_id=None):
        if self.readonly: raise PermissionError('readonly')
        with self.lock:
            cur=self.db.execute('INSERT OR IGNORE INTO ontology(child,parent,relation,confidence,fact_id,created_at) VALUES(?,?,?,?,?,?)',(child,parent,rel,conf,fact_id,int(time.time()))); self.db.commit(); return cur.lastrowid if cur.rowcount else None
    def add_question(self,q,priority=.5):
        if self.readonly: return
        with self.lock: self.db.execute('INSERT OR IGNORE INTO questions(question,priority,status,created_at,updated_at) VALUES(?,?,?,?,?)',(q,priority,'open',int(time.time()),int(time.time()))); self.db.commit()
    def open_questions(self,limit=1): return self.rows("SELECT * FROM questions WHERE status='open' ORDER BY priority DESC,id ASC LIMIT ?",(limit,))
    def update_question(self,qid,status):
        if self.readonly: return
        with self.lock: self.db.execute('UPDATE questions SET status=?,updated_at=? WHERE id=?',(status,int(time.time()),qid)); self.db.commit()
    def add_conversation(self,role,text,topic=None):
        if self.readonly: return
        with self.lock: self.db.execute('INSERT INTO conversations(role,text,topic,created_at) VALUES(?,?,?,?)',(role,text,topic,int(time.time()))); self.db.commit()
    def set_topic_context(self,topic,user_text,sources):
        if self.readonly: return
        with self.lock: self.db.execute('INSERT OR REPLACE INTO topic_context(id,topic,user_text,last_sources_json,updated_at) VALUES(1,?,?,?,?)',(topic,user_text,self._json(sources),int(time.time()))); self.db.commit()
    def last_topic_context(self):
        r=self.rows('SELECT * FROM topic_context WHERE id=1'); return r[0] if r else None
    def get_setting(self,k,default=None):
        r=self.rows('SELECT value FROM settings WHERE key=?',(k,)); return json.loads(r[0]['value']) if r else default
    def set_setting(self,k,v):
        if self.readonly: return
        with self.lock: self.db.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',(k,self._json(v))); self.db.commit()
    def get_import_state(self,path):
        r=self.rows('SELECT * FROM import_state WHERE path=?',(str(path),)); return r[0] if r else None
    def set_import_state(self,path,last_article,last_chunk,status):
        if self.readonly: return
        with self.lock: self.db.execute('INSERT OR REPLACE INTO import_state(path,last_article,last_chunk,status,updated_at) VALUES(?,?,?,?,?)',(str(path),last_article,last_chunk,status,int(time.time()))); self.db.commit()
    def stats(self):
        # PHASE_STATS_SAFE_NO_CRASH
        out = {}
        for t in ['documents','chunks','facts','relations','ontology','questions']:
            try:
                out[t] = self.rows(f'SELECT COUNT(*) AS c FROM {t}')[0]['c']
            except Exception:
                out[t] = 0
        return out
    def log(self,event,data):
        if self.readonly: return
        with self.lock: self.db.execute('INSERT INTO logs(event,data_json,created_at) VALUES(?,?,?)',(event,self._json(data),int(time.time()))); self.db.commit()
    def export_json(self,path): Path(path).write_text(json.dumps({'stats':self.stats()},ensure_ascii=False,indent=2),encoding='utf-8')
    def export_facts_csv(self,path):
        with open(path,'w',newline='',encoding='utf-8') as f:
            w=csv.writer(f); w.writerow(['subject','relation','value','confidence'])
            for r in self.rows('SELECT subject,relation,value,confidence FROM facts'): w.writerow([r['subject'],r['relation'],r['value'],r['confidence']])


# BRAINSTEM_PURE_WRITE_GUARD
# Technische Uebergangssperre: keine Klassifikation, keine Candidate-Umleitung.
def _brainstem_blocked_write(self, *args, **kwargs):
    return False

for _brainstem_name in (
    "add_fact", "add_relation", "add_relations", "store_relation",
    "insert_relation", "add_ontology"
):
    if hasattr(Memory, _brainstem_name):
        setattr(Memory, _brainstem_name, _brainstem_blocked_write)
