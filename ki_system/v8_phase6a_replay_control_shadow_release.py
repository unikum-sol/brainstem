# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib,json,math,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEFAULT_DB=ROOT/'ki_memory.sqlite3'
LATEST='phase6a_replay_control_shadow_latest';EVENTS='phase6a_replay_control_shadow_events';STATE='phase6a_replay_control_shadow_state'
SCHEMA_TABLES={
LATEST:['source_table','source_id','control_fingerprint','replay_priority','replay_weight','replay_decision','plasticity_level','neuromodulator_fingerprint','first_event_id','last_event_id','first_seen_at','last_seen_at','input_count','stable_refresh_count','control_change_count','details'],
EVENTS:['id','source_event_id','source_table','source_id','control_fingerprint','classification','event_created_at','captured_at','details'],
STATE:['key','value']}
def _q(n):return '"'+str(n).replace('"','""')+'"'
def _conn(obj=None):
 if isinstance(obj,sqlite3.Connection):return obj,False
 p=Path(obj) if isinstance(obj,(str,Path)) else DEFAULT_DB;c=sqlite3.connect(str(p),timeout=120);return c,True
def _norm(v):
 if isinstance(v,dict):return {str(k):_norm(v[k]) for k in sorted(v,key=lambda x:str(x))}
 if isinstance(v,list):return [_norm(x) for x in v]
 if isinstance(v,float):
  if math.isnan(v) or math.isinf(v):raise ValueError('non-finite neuromodulator number')
  return 0.0 if v==0.0 else v
 if isinstance(v,(str,int,bool)) or v is None:return v
 raise TypeError('unsupported JSON value '+type(v).__name__)
def canonical_profile(raw):
 parsed=json.loads(str(raw));normalized=_norm(parsed)
 if not isinstance(normalized,dict):raise ValueError('neuromodulator profile must be a JSON object')
 text=json.dumps(normalized,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
 return text,hashlib.sha256(text.encode('utf-8')).hexdigest()
def control_fingerprint(source_table,source_id,priority,weight,decision,plasticity,nm_text):
 payload={'source_table':str(source_table),'source_id':int(source_id),'replay_priority':priority,'replay_weight':weight,'replay_decision':decision,'plasticity_level':plasticity,'neuromodulators':json.loads(nm_text)}
 text=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
 return hashlib.sha256(text.encode('utf-8')).hexdigest()
def ensure_schema(obj=None):
 c,own=_conn(obj)
 try:
  c.execute("CREATE TABLE IF NOT EXISTS "+LATEST+"(source_table TEXT NOT NULL,source_id INTEGER NOT NULL,control_fingerprint TEXT NOT NULL,replay_priority REAL,replay_weight REAL,replay_decision TEXT,plasticity_level REAL,neuromodulator_fingerprint TEXT NOT NULL,first_event_id INTEGER NOT NULL,last_event_id INTEGER NOT NULL,first_seen_at INTEGER NOT NULL,last_seen_at INTEGER NOT NULL,input_count INTEGER NOT NULL DEFAULT 1,stable_refresh_count INTEGER NOT NULL DEFAULT 0,control_change_count INTEGER NOT NULL DEFAULT 0,details TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(source_table,source_id))")
  c.execute("CREATE TABLE IF NOT EXISTS "+EVENTS+"(id INTEGER PRIMARY KEY AUTOINCREMENT,source_event_id INTEGER NOT NULL UNIQUE,source_table TEXT NOT NULL,source_id INTEGER NOT NULL,control_fingerprint TEXT NOT NULL,classification TEXT NOT NULL,event_created_at INTEGER,captured_at INTEGER NOT NULL,details TEXT NOT NULL DEFAULT '{}')")
  c.execute("CREATE INDEX IF NOT EXISTS idx_p6rcs_events_source ON "+EVENTS+"(source_table,source_id,id)")
  c.execute("CREATE INDEX IF NOT EXISTS idx_p6rcs_events_class ON "+EVENTS+"(classification,id)")
  c.execute("CREATE TABLE IF NOT EXISTS "+STATE+"(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
  state={'mode':'future_only_shadow_capture','scope':'context_hypotheses_only','stable_identity':'source_table+source_id','retry_identity':'phase6a_event_id','neuromodulator_canonicalization':'recursive_sorted_json_sha256','backfill':'disabled','migration':'disabled','candidate_bridge':'not_called','observation_layer':'not_called','old_v2_writer':'unchanged','content_stable_classifier':'unchanged','semantic_hypothesis_version':'not_created','observation_ready':'false','productive_writes':'disabled'}
  c.executemany('INSERT INTO '+STATE+'(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',state.items())
  if own:c.commit()
  return _self_check_schema(c)
 finally:
  if own:c.close()
def _self_check_schema(c=None):
 own=False
 if c is None:c,own=_conn()
 try:
  out={}
  for t,required in SCHEMA_TABLES.items():
   live=[str(r[1]) for r in c.execute('PRAGMA table_info('+_q(t)+')')];missing=[x for x in required if x not in live];out[t]={'missing':missing,'overall':not missing}
   if missing:raise RuntimeError(t+' missing '+repr(missing))
  out['overall']=all(v['overall'] for v in out.values());return out
 finally:
  if own:c.close()
def capture_event(con,source_event_id):
 _self_check_schema(con);eid=int(source_event_id)
 if con.execute('SELECT 1 FROM '+EVENTS+' WHERE source_event_id=?',(eid,)).fetchone():return {'classification':'identical_retry','written':0,'scoped':1}
 row=con.execute('SELECT id,source_table,source_id,replay_priority,replay_weight,replay_decision,plasticity_level,neuromodulator_profile,created_at FROM phase6a_sleep_replay_events WHERE id=?',(eid,)).fetchone()
 if row is None:raise RuntimeError('phase6a event not found: '+str(eid))
 source_table,source_id=row[1],int(row[2])
 if source_table!='context_hypotheses':return {'classification':'out_of_scope_source','written':0,'scoped':0}
 nm_text,nm_hash=canonical_profile(row[7]);fp=control_fingerprint(source_table,source_id,row[3],row[4],row[5],row[6],nm_text);now=int(time.time())
 prev=con.execute('SELECT control_fingerprint FROM '+LATEST+' WHERE source_table=? AND source_id=?',(source_table,source_id)).fetchone()
 if prev is None:
  cls='initial_replay_control_state';con.execute('INSERT INTO '+LATEST+'(source_table,source_id,control_fingerprint,replay_priority,replay_weight,replay_decision,plasticity_level,neuromodulator_fingerprint,first_event_id,last_event_id,first_seen_at,last_seen_at,input_count,stable_refresh_count,control_change_count,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(source_table,source_id,fp,row[3],row[4],row[5],row[6],nm_hash,eid,eid,now,now,1,0,0,json.dumps({'shadow_only':True},sort_keys=True)))
 elif prev[0]==fp:
  cls='same_control_state_new_replay_event';con.execute('UPDATE '+LATEST+' SET last_event_id=?,last_seen_at=?,input_count=input_count+1,stable_refresh_count=stable_refresh_count+1 WHERE source_table=? AND source_id=?',(eid,now,source_table,source_id))
 else:
  cls='replay_control_state_change_candidate';con.execute('UPDATE '+LATEST+' SET control_fingerprint=?,replay_priority=?,replay_weight=?,replay_decision=?,plasticity_level=?,neuromodulator_fingerprint=?,last_event_id=?,last_seen_at=?,input_count=input_count+1,control_change_count=control_change_count+1 WHERE source_table=? AND source_id=?',(fp,row[3],row[4],row[5],row[6],nm_hash,eid,now,source_table,source_id))
 details=json.dumps({'scope':'context_hypotheses','semantic_hypothesis_version':False,'candidate_bridge_called':False,'observation_layer_called':False,'neuromodulator_profile':nm_text},sort_keys=True,separators=(',',':'))
 con.execute('INSERT INTO '+EVENTS+'(source_event_id,source_table,source_id,control_fingerprint,classification,event_created_at,captured_at,details) VALUES(?,?,?,?,?,?,?,?)',(eid,source_table,source_id,fp,cls,row[8],now,details))
 return {'classification':cls,'written':1,'scoped':1}
def capture_last_inserted_event(con):
 eid=int(con.execute('SELECT last_insert_rowid()').fetchone()[0]);return capture_event(con,eid)
