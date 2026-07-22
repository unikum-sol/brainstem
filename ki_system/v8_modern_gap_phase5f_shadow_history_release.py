# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_DB=ROOT/'ki_memory.sqlite3'
TABLE='modern_gap_phase5f_shadow_observation_history'
SCHEMA_TABLES={TABLE:['history_id','observation_key','shadow_key','hypothesis_id','source_updated_at','source_fingerprint','projection_fingerprint','center_chunk_id','target_chunk_ids','projected_window_strategy','projected_window_radius','projected_action','expected_gain','closure_delta','overlap_score','read_no_candidate_rate','projected_effectiveness','neuromodulators','real_outcome_observation_available','observation_ready','source_default_path','productive_gap_id','productive_write','change_kind','previous_history_id','details','created_at']}
def _q(n):return '"'+str(n).replace('"','""')+'"'
def _con(obj=None):
 p=Path(obj) if isinstance(obj,(str,Path)) else DEFAULT_DB;c=sqlite3.connect(str(p),timeout=120);c.row_factory=sqlite3.Row;return c
def _canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def _hash(v):return hashlib.sha256(_canon(v).encode('utf-8')).hexdigest()
def ensure_schema(obj=None):
 c=_con(obj)
 try:
  c.execute("CREATE TABLE IF NOT EXISTS "+TABLE+"(history_id INTEGER PRIMARY KEY AUTOINCREMENT,observation_key TEXT NOT NULL,shadow_key TEXT NOT NULL,hypothesis_id INTEGER NOT NULL,source_updated_at INTEGER NOT NULL DEFAULT 0,source_fingerprint TEXT NOT NULL,projection_fingerprint TEXT NOT NULL,center_chunk_id INTEGER,target_chunk_ids TEXT NOT NULL DEFAULT '[]',projected_window_strategy TEXT,projected_window_radius INTEGER,projected_action TEXT,expected_gain REAL,closure_delta REAL,overlap_score REAL,read_no_candidate_rate REAL,projected_effectiveness REAL,neuromodulators TEXT NOT NULL DEFAULT '{}',real_outcome_observation_available INTEGER NOT NULL DEFAULT 0,observation_ready INTEGER NOT NULL DEFAULT 0,source_default_path INTEGER NOT NULL DEFAULT 1,productive_gap_id INTEGER,productive_write INTEGER NOT NULL DEFAULT 0,change_kind TEXT NOT NULL,previous_history_id INTEGER,details TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL)")
  c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_shadow_history_fingerprints ON '+TABLE+'(observation_key,source_fingerprint,projection_fingerprint,real_outcome_observation_available,observation_ready)')
  c.execute('CREATE INDEX IF NOT EXISTS idx_shadow_history_hypothesis ON '+TABLE+'(hypothesis_id,history_id)')
  c.execute('CREATE INDEX IF NOT EXISTS idx_shadow_history_shadow_key ON '+TABLE+'(shadow_key,history_id)')
  c.commit();return _self_check_schema(c)
 finally:c.close()
def _self_check_schema(c=None):
 own=c is None
 if own:c=_con()
 try:
  live=[str(r[1]) for r in c.execute('PRAGMA table_info('+_q(TABLE)+')')];missing=[x for x in SCHEMA_TABLES[TABLE] if x not in live];result={'table':TABLE,'missing':missing,'overall':not missing}
  if missing:raise RuntimeError('history schema missing '+repr(missing))
  return result
 finally:
  if own:c.close()
def fingerprints(item):
 source={'shadow_key':item.get('shadow_key'),'hypothesis_id':item.get('hypothesis_id'),'source_updated_at':item.get('source_updated_at'),'center_chunk_id':item.get('center_chunk_id'),'candidate_state':(item.get('details') or {}).get('candidate_state'),'bridge_mode':(item.get('details') or {}).get('bridge_mode'),'neuromodulators':item.get('neuromodulators') or {}}
 projection={'target_chunk_ids':item.get('target_chunk_ids') or [],'target_count':item.get('target_count'),'strategy':item.get('projected_window_strategy'),'radius':item.get('projected_window_radius'),'action':item.get('projected_action'),'expected_gain':item.get('expected_gain'),'closure_delta':item.get('closure_delta'),'overlap_score':item.get('overlap_score'),'read_no_candidate_rate':item.get('read_no_candidate_rate'),'projected_effectiveness':item.get('projected_effectiveness')}
 return _hash(source),_hash(projection)
def record_history(con,item,now=None):
 _self_check_schema(con);now=int(now or time.time());sf,pf=fingerprints(item)
 prev=con.execute('SELECT history_id,source_fingerprint,projection_fingerprint,real_outcome_observation_available,observation_ready FROM '+TABLE+' WHERE observation_key=? ORDER BY history_id DESC LIMIT 1',(item['observation_key'],)).fetchone()
 outcome=int(item.get('real_outcome_observation_available') or 0);ready=int(item.get('observation_ready') or 0)
 if prev and prev['source_fingerprint']==sf and prev['projection_fingerprint']==pf and int(prev['real_outcome_observation_available'] or 0)==outcome and int(prev['observation_ready'] or 0)==ready:return {'inserted':False,'change_kind':'technical_retry_or_identical_state','history_id':int(prev['history_id'])}
 if not prev:kind='initial_observation'
 else:
  sc=prev['source_fingerprint']!=sf;pc=prev['projection_fingerprint']!=pf;oc=int(prev['real_outcome_observation_available'] or 0)!=outcome or int(prev['observation_ready'] or 0)!=ready
  kind='outcome_observation_change' if oc else ('source_and_projection_change' if sc and pc else ('source_state_change' if sc else 'projection_change'))
 vals=(item['observation_key'],item['shadow_key'],int(item['hypothesis_id']),int(item.get('source_updated_at') or 0),sf,pf,item.get('center_chunk_id'),_canon(item.get('target_chunk_ids') or []),item.get('projected_window_strategy'),item.get('projected_window_radius'),item.get('projected_action'),item.get('expected_gain'),item.get('closure_delta'),item.get('overlap_score'),item.get('read_no_candidate_rate'),item.get('projected_effectiveness'),_canon(item.get('neuromodulators') or {}),0,0,1,None,0,kind,(int(prev['history_id']) if prev else None),_canon({'history_version':'v1','real_outcome_source':'unavailable','observation_ready_gate':'closed'}),now)
 con.execute('INSERT OR IGNORE INTO '+TABLE+'(observation_key,shadow_key,hypothesis_id,source_updated_at,source_fingerprint,projection_fingerprint,center_chunk_id,target_chunk_ids,projected_window_strategy,projected_window_radius,projected_action,expected_gain,closure_delta,overlap_score,read_no_candidate_rate,projected_effectiveness,neuromodulators,real_outcome_observation_available,observation_ready,source_default_path,productive_gap_id,productive_write,change_kind,previous_history_id,details,created_at) VALUES('+','.join('?' for _ in vals)+')',vals)
 hid=con.execute('SELECT history_id FROM '+TABLE+' WHERE observation_key=? AND source_fingerprint=? AND projection_fingerprint=? AND real_outcome_observation_available=0 AND observation_ready=0',(item['observation_key'],sf,pf)).fetchone()[0]
 return {'inserted':True,'change_kind':kind,'history_id':int(hid),'source_fingerprint':sf,'projection_fingerprint':pf}
