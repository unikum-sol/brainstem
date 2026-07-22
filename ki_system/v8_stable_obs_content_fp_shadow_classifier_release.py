# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib,json,sqlite3,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DEFAULT_DB=ROOT/'ki_memory.sqlite3'
LATEST='modern_gap_phase5f_shadow_content_fp_classifier_latest'; EVENTS='modern_gap_phase5f_shadow_content_fp_classifier_events'; STATE='modern_gap_phase5f_shadow_content_fp_classifier_state'
SCHEMA_TABLES={
LATEST:['stable_observation_key','shadow_key','hypothesis_id','old_source_fingerprint','content_source_fingerprint','projection_fingerprint','latest_source_updated_at','first_seen_at','last_seen_at','input_count','old_version_candidate_count','content_version_candidate_count','timestamp_refresh_count','identical_retry_count','details'],
EVENTS:['id','stable_observation_key','hypothesis_id','source_updated_at','old_source_fingerprint','content_source_fingerprint','projection_fingerprint','old_contract_classification','content_contract_classification','classifiers_agree','created_at','details'],
STATE:['key','value']}
def _q(n):return '"'+str(n).replace('"','""')+'"'
def _con(obj=None):
    if isinstance(obj,sqlite3.Connection):return obj,False
    p=Path(obj) if isinstance(obj,(str,Path)) else DEFAULT_DB;c=sqlite3.connect(str(p),timeout=120);c.row_factory=sqlite3.Row;return c,True
def _canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str)
def _hash(v):return hashlib.sha256(_canon(v).encode('utf-8')).hexdigest()
def stable_key(shadow_key,hypothesis_id):return 'stable-shadow-observation:'+hashlib.sha256((str(shadow_key)+'|'+str(int(hypothesis_id))).encode('utf-8')).hexdigest()
def fingerprints(item):
    old={'shadow_key':item.get('shadow_key'),'hypothesis_id':int(item.get('hypothesis_id') or 0),'source_updated_at':int(item.get('source_updated_at') or 0),'center_chunk_id':item.get('center_chunk_id'),'neuromodulators':item.get('neuromodulators') or {}}
    content={'shadow_key':item.get('shadow_key'),'hypothesis_id':int(item.get('hypothesis_id') or 0),'center_chunk_id':item.get('center_chunk_id'),'neuromodulators':item.get('neuromodulators') or {}}
    projection={'target_chunk_ids':item.get('target_chunk_ids') or [],'target_count':int(item.get('target_count') or 0),'strategy':item.get('projected_window_strategy'),'radius':item.get('projected_window_radius'),'action':item.get('projected_action'),'expected_gain':item.get('expected_gain'),'closure_delta':item.get('closure_delta'),'overlap_score':item.get('overlap_score'),'read_no_candidate_rate':item.get('read_no_candidate_rate'),'projected_effectiveness':item.get('projected_effectiveness')}
    return _hash(old),_hash(content),_hash(projection)
def ensure_schema(obj=None):
    c,own=_con(obj)
    try:
        c.execute("CREATE TABLE IF NOT EXISTS "+LATEST+"(stable_observation_key TEXT PRIMARY KEY,shadow_key TEXT NOT NULL,hypothesis_id INTEGER NOT NULL,old_source_fingerprint TEXT NOT NULL,content_source_fingerprint TEXT NOT NULL,projection_fingerprint TEXT NOT NULL,latest_source_updated_at INTEGER NOT NULL,first_seen_at INTEGER NOT NULL,last_seen_at INTEGER NOT NULL,input_count INTEGER NOT NULL DEFAULT 1,old_version_candidate_count INTEGER NOT NULL DEFAULT 1,content_version_candidate_count INTEGER NOT NULL DEFAULT 1,timestamp_refresh_count INTEGER NOT NULL DEFAULT 0,identical_retry_count INTEGER NOT NULL DEFAULT 0,details TEXT NOT NULL DEFAULT '{}',UNIQUE(shadow_key,hypothesis_id))")
        c.execute("CREATE TABLE IF NOT EXISTS "+EVENTS+"(id INTEGER PRIMARY KEY AUTOINCREMENT,stable_observation_key TEXT NOT NULL,hypothesis_id INTEGER NOT NULL,source_updated_at INTEGER NOT NULL,old_source_fingerprint TEXT NOT NULL,content_source_fingerprint TEXT NOT NULL,projection_fingerprint TEXT NOT NULL,old_contract_classification TEXT NOT NULL,content_contract_classification TEXT NOT NULL,classifiers_agree INTEGER NOT NULL,created_at INTEGER NOT NULL,details TEXT NOT NULL DEFAULT '{}')")
        c.execute("CREATE INDEX IF NOT EXISTS idx_content_fp_events_stable ON "+EVENTS+"(stable_observation_key,id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_content_fp_events_class ON "+EVENTS+"(content_contract_classification,id)")
        c.execute("CREATE TABLE IF NOT EXISTS "+STATE+"(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        state={'mode':'shadow_classifier','old_v2_writer':'unchanged','backfill':'disabled','migration':'disabled','reader_switch':'disabled','source_updated_at_provenance':'retained','content_fingerprint_excludes_source_updated_at':'true','database_size_optimization':'not_requested','gui_freeze_database_size_causality':'not_assumed','observation_ready':'false','productive_writes':'disabled'}
        c.executemany('INSERT INTO '+STATE+'(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',state.items())
        if own:c.commit()
        return _self_check_schema(c)
    finally:
        if own:c.close()
def _self_check_schema(c=None):
    own=False
    if c is None:c,own=_con()
    try:
        out={}
        for t,required in SCHEMA_TABLES.items():
            live=[str(r[1]) for r in c.execute('PRAGMA table_info('+_q(t)+')')];missing=[x for x in required if x not in live];out[t]={'missing':missing,'overall':not missing}
            if missing:raise RuntimeError(t+' missing '+repr(missing))
        out['overall']=all(x['overall'] for x in out.values());return out
    finally:
        if own:c.close()
def record_shadow_classification(con,item,now=None):
    _self_check_schema(con);now=int(now or time.time());sk=stable_key(item['shadow_key'],item['hypothesis_id']);ofp,cfp,pfp=fingerprints(item);ts=int(item.get('source_updated_at') or 0)
    prev=con.execute('SELECT * FROM '+LATEST+' WHERE stable_observation_key=?',(sk,)).fetchone()
    if prev is None:
        old_class=content_class='initial_observation';agree=1;old_add=content_add=1;refresh=identical=0
        con.execute('INSERT INTO '+LATEST+'(stable_observation_key,shadow_key,hypothesis_id,old_source_fingerprint,content_source_fingerprint,projection_fingerprint,latest_source_updated_at,first_seen_at,last_seen_at,input_count,old_version_candidate_count,content_version_candidate_count,timestamp_refresh_count,identical_retry_count,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(sk,item['shadow_key'],int(item['hypothesis_id']),ofp,cfp,pfp,ts,now,now,1,1,1,0,0,_canon({'contract':'content_stable_fp_shadow_classifier_v1'})))
    else:
        old_sc=prev['old_source_fingerprint']!=ofp;content_sc=prev['content_source_fingerprint']!=cfp;pc=prev['projection_fingerprint']!=pfp
        old_class='source_and_projection_change' if old_sc and pc else ('source_state_change' if old_sc else ('projection_change' if pc else 'technical_retry_or_identical_state'))
        if content_sc and pc:content_class='source_and_projection_change'
        elif content_sc:content_class='source_state_change'
        elif pc:content_class='projection_change'
        elif ts!=int(prev['latest_source_updated_at']):content_class='same_content_new_timestamp'
        else:content_class='technical_retry_or_identical_state'
        agree=1 if old_class==content_class else 0;old_add=1 if old_class in ('source_state_change','projection_change','source_and_projection_change') else 0;content_add=1 if content_class in ('source_state_change','projection_change','source_and_projection_change') else 0;refresh=1 if content_class=='same_content_new_timestamp' else 0;identical=1 if content_class=='technical_retry_or_identical_state' else 0
        con.execute('UPDATE '+LATEST+' SET old_source_fingerprint=?,content_source_fingerprint=?,projection_fingerprint=?,latest_source_updated_at=?,last_seen_at=?,input_count=input_count+1,old_version_candidate_count=old_version_candidate_count+?,content_version_candidate_count=content_version_candidate_count+?,timestamp_refresh_count=timestamp_refresh_count+?,identical_retry_count=identical_retry_count+? WHERE stable_observation_key=?',(ofp,cfp,pfp,ts,now,old_add,content_add,refresh,identical,sk))
    con.execute('INSERT INTO '+EVENTS+'(stable_observation_key,hypothesis_id,source_updated_at,old_source_fingerprint,content_source_fingerprint,projection_fingerprint,old_contract_classification,content_contract_classification,classifiers_agree,created_at,details) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(sk,int(item['hypothesis_id']),ts,ofp,cfp,pfp,old_class,content_class,agree,now,_canon({'contract':'content_stable_fp_shadow_classifier_v1','old_v2_writer_unchanged':True,'timestamp_provenance_retained':True,'observation_ready':False,'productive_writes':False})))
    return {'old_contract_classification':old_class,'content_contract_classification':content_class,'classifiers_agree':agree,'old_version_candidate':old_add,'content_version_candidate':content_add,'timestamp_refresh':refresh,'identical_retry':identical}
