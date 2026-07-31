# -*- coding: utf-8 -*-
"""BrainStem Non-Productive Delayed Evidence Recheck, Watermark Progression & Awaiting-State Contract V1.1."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, tempfile, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERSION="non_productive_delayed_evidence_recheck_watermark_awaiting_state_v1_1"
LIMIT=512; DEFAULT_RECHECK_LIMIT=256
SOURCE="modern_gap_phase5f_shadow_observation_v2_latest"; EVENTS="context_learning_events"; READS="reading_queue"; STABILITY="hypothesis_stability_scores"
SHADOW="non_productive_real_outcome_observation_shadow"; CYCLES="non_productive_real_outcome_observation_shadow_cycles"; STATE="non_productive_real_outcome_observation_shadow_state"
PROTECTED=("facts","relations","questions","internal_learning_gaps","chunk_attention_scores","phase5f_context_window_experiments","phase5g_strategy_experiments","phase5g_experiment_outcomes","phase5i_outcome_driven_experiments","modern_outcome_bridge_shadow")
SHADOW_COLUMNS=["eligibility_key","stable_observation_key","shadow_key","hypothesis_id","baseline_source_updated_at","baseline_projection_fingerprint","delayed_event_count","delayed_reobservation_count","first_delayed_event_at","last_delayed_event_at","stability_available","stability","real_outcome_observation_available","non_productive_eligible","eligibility_state","source_provenance","missing_signals","productive_write","details","first_seen_at","last_seen_at","version_count","last_evaluated_at","recheck_count","last_event_watermark","last_read_watermark","last_stability_watermark","evidence_changed"]
CYCLE_COLUMNS=["id","phase","source_rows_seen","shadow_rows_created","shadow_rows_updated","real_outcome_available","non_productive_eligible","awaiting_delayed_reobservation","awaiting_stability","checkpoint_updated_at_before","checkpoint_hypothesis_id_before","checkpoint_updated_at_after","checkpoint_hypothesis_id_after","protected_before","protected_after","safety_ok","mode","created_at","details","recheck_rows_seen","recheck_rows_changed","recheck_rows_eligible","awaiting_target_read"]
SCHEMA_TABLES={SHADOW:SHADOW_COLUMNS,CYCLES:CYCLE_COLUMNS,STATE:["key","value","updated_at"]}

def now():return int(time.time())
def canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def q(s):return '"'+str(s).replace('"','""')+'"'
def exists(c,t):return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cols(c,t):return [r[1] for r in c.execute("PRAGMA table_info("+q(t)+")")] if exists(c,t) else []
def count(c,t):return int(c.execute("SELECT COUNT(*) FROM "+q(t)).fetchone()[0]) if exists(c,t) else None
def _read_kv(con: sqlite3.Connection, table: str) -> Dict[str, Any]:
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())
def protected(c):return {t:count(c,t) for t in PROTECTED}
def add_column(c,t,name,decl):
    if name not in cols(c,t):c.execute("ALTER TABLE "+q(t)+" ADD COLUMN "+q(name)+" "+decl)
def write_state(c,values,ts):
    for k,v in values.items():c.execute("INSERT INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,str(v).lower() if isinstance(v,bool) else str(v),ts))

def ensure_schema(c):
    if not exists(c,SHADOW):
        c.execute("CREATE TABLE "+SHADOW+"(eligibility_key TEXT PRIMARY KEY,stable_observation_key TEXT NOT NULL,shadow_key TEXT NOT NULL,hypothesis_id INTEGER NOT NULL,baseline_source_updated_at INTEGER NOT NULL DEFAULT 0,baseline_projection_fingerprint TEXT NOT NULL DEFAULT '',delayed_event_count INTEGER NOT NULL DEFAULT 0,delayed_reobservation_count INTEGER NOT NULL DEFAULT 0,first_delayed_event_at INTEGER,last_delayed_event_at INTEGER,stability_available INTEGER NOT NULL DEFAULT 0,stability REAL,real_outcome_observation_available INTEGER NOT NULL DEFAULT 0,non_productive_eligible INTEGER NOT NULL DEFAULT 0,eligibility_state TEXT NOT NULL,source_provenance TEXT NOT NULL DEFAULT '{}',missing_signals TEXT NOT NULL DEFAULT '[]',productive_write INTEGER NOT NULL DEFAULT 0,details TEXT NOT NULL DEFAULT '{}',first_seen_at INTEGER NOT NULL,last_seen_at INTEGER NOT NULL,version_count INTEGER NOT NULL DEFAULT 1)")
    if not exists(c,CYCLES):
        c.execute("CREATE TABLE "+CYCLES+"(id INTEGER PRIMARY KEY AUTOINCREMENT,phase TEXT NOT NULL,source_rows_seen INTEGER NOT NULL DEFAULT 0,shadow_rows_created INTEGER NOT NULL DEFAULT 0,shadow_rows_updated INTEGER NOT NULL DEFAULT 0,real_outcome_available INTEGER NOT NULL DEFAULT 0,non_productive_eligible INTEGER NOT NULL DEFAULT 0,awaiting_delayed_reobservation INTEGER NOT NULL DEFAULT 0,awaiting_stability INTEGER NOT NULL DEFAULT 0,checkpoint_updated_at_before INTEGER NOT NULL DEFAULT 0,checkpoint_hypothesis_id_before INTEGER NOT NULL DEFAULT 0,checkpoint_updated_at_after INTEGER NOT NULL DEFAULT 0,checkpoint_hypothesis_id_after INTEGER NOT NULL DEFAULT 0,protected_before TEXT NOT NULL DEFAULT '{}',protected_after TEXT NOT NULL DEFAULT '{}',safety_ok INTEGER NOT NULL DEFAULT 0,mode TEXT NOT NULL DEFAULT 'shadow',created_at INTEGER NOT NULL,details TEXT NOT NULL DEFAULT '{}')")
    c.execute("CREATE TABLE IF NOT EXISTS "+STATE+"(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at INTEGER NOT NULL)")
    for n,d in (("last_evaluated_at","INTEGER NOT NULL DEFAULT 0"),("recheck_count","INTEGER NOT NULL DEFAULT 0"),("last_event_watermark","INTEGER NOT NULL DEFAULT 0"),("last_read_watermark","INTEGER NOT NULL DEFAULT 0"),("last_stability_watermark","INTEGER NOT NULL DEFAULT 0"),("evidence_changed","INTEGER NOT NULL DEFAULT 0")):add_column(c,SHADOW,n,d)
    for n,d in (("recheck_rows_seen","INTEGER NOT NULL DEFAULT 0"),("recheck_rows_changed","INTEGER NOT NULL DEFAULT 0"),("recheck_rows_eligible","INTEGER NOT NULL DEFAULT 0"),("awaiting_target_read","INTEGER NOT NULL DEFAULT 0")):add_column(c,CYCLES,n,d)
    c.execute("CREATE INDEX IF NOT EXISTS idx_np_recheck_state ON "+SHADOW+"(non_productive_eligible,last_evaluated_at,recheck_count,eligibility_key)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_np_recheck_hyp ON "+SHADOW+"(hypothesis_id,baseline_source_updated_at)")
    defaults={"phase":VERSION,"mode":"shadow_recheck","contract_version":"v1.1","checkpoint_updated_at":"0","checkpoint_hypothesis_id":"0","recheck_cursor_key":"","last_recheck_rows_seen":"0","last_recheck_rows_changed":"0","productive_writes":"disabled","phase5i_writes":"disabled","productive_gap_writes":"disabled","attention_writes":"disabled","fact_writes":"disabled","relation_writes":"disabled","question_writes":"disabled","causal_effect_claimed":"false","last_safety_ok":"true"};ts=now()
    for k,v in defaults.items():c.execute("INSERT OR IGNORE INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?)",(k,v,ts))
def self_check(c):
    for t,required in SCHEMA_TABLES.items():
        missing=[x for x in required if x not in cols(c,t)]
        if missing:raise RuntimeError("Schema missing for "+t+": "+", ".join(missing))

def parse_targets(v):
    try:x=json.loads(v) if isinstance(v,str) else v
    except Exception:x=[]
    out=[]
    if isinstance(x,list):
        for a in x:
            try:out.append(int(a))
            except Exception:pass
    return sorted(set(out))
def fingerprint(parts):return hashlib.sha256(canon(list(parts)).encode()).hexdigest()
def event_evidence(c,hid,baseline):
    if not exists(c,EVENTS) or not {"hypothesis_id","event_type","created_at"}.issubset(cols(c,EVENTS)):return {"count":0,"reobserved":0,"first":None,"last":None,"watermark":0,"reason":"event_contract_missing"}
    r=c.execute("SELECT COUNT(*),SUM(CASE WHEN event_type='raw_observation_reobserved' THEN 1 ELSE 0 END),MIN(created_at),MAX(created_at) FROM "+EVENTS+" WHERE hypothesis_id=? AND created_at>?",(hid,baseline)).fetchone()
    return {"count":int(r[0] or 0),"reobserved":int(r[1] or 0),"first":r[2],"last":r[3],"watermark":int(r[3] or 0),"reason":"strictly_after_v2_baseline"}
def read_evidence(c,targets,baseline):
    if not targets or not exists(c,READS):return {"available":False,"matched":0,"positive":0,"watermark":0,"reason":"read_source_or_targets_missing"}
    cs=set(cols(c,READS));timecol=next((x for x in ("updated_at","last_read","created_at") if x in cs),None)
    if "chunk_id" not in cs or not timecol or not ({"status","read_count"}&cs):return {"available":False,"matched":0,"positive":0,"watermark":0,"reason":"read_contract_missing"}
    status="COALESCE(status,'')" if "status" in cs else "''";rc="COALESCE(read_count,0)" if "read_count" in cs else "0";ph=",".join("?" for _ in targets)
    sql="SELECT COUNT(*),SUM(CASE WHEN "+rc+">0 OR lower("+status+") IN ('read','read_no_candidate','completed','done') THEN 1 ELSE 0 END),MAX("+q(timecol)+") FROM "+READS+" WHERE chunk_id IN ("+ph+") AND COALESCE("+q(timecol)+",0)>?"
    r=c.execute(sql,tuple(targets)+(baseline,)).fetchone();pos=int(r[1] or 0)
    return {"available":pos>0,"matched":int(r[0] or 0),"positive":pos,"watermark":int(r[2] or 0),"reason":"delayed_target_read_outcome" if pos else "no_delayed_target_read_outcome"}
def stability_evidence(c,hid):
    if not exists(c,STABILITY) or not {"hypothesis_id","stability"}.issubset(cols(c,STABILITY)):return {"available":False,"value":None,"watermark":0,"reason":"stability_contract_missing"}
    cs=set(cols(c,STABILITY));wm="updated_at" if "updated_at" in cs else "rowid";r=c.execute("SELECT stability,"+wm+" FROM "+STABILITY+" WHERE hypothesis_id=? ORDER BY "+wm+" DESC LIMIT 1",(hid,)).fetchone()
    return {"available":bool(r and r[0] is not None),"value":float(r[0]) if r and r[0] is not None else None,"watermark":int(r[1] or 0) if r else 0,"reason":"latest_hypothesis_stability" if r else "stability_not_found"}
def evaluate(c,hid,baseline,targets,old=(0,0,0)):
    ev=event_evidence(c,hid,baseline);rd=read_evidence(c,targets,baseline);st=stability_evidence(c,hid);real=ev["reobserved"]>0 and rd["available"];eligible=real and st["available"]
    missing=[]
    if ev["reobserved"]<=0:missing.append("delayed_raw_reobservation")
    if not rd["available"]:missing.append("delayed_target_read_outcome")
    if not st["available"]:missing.append("hypothesis_stability")
    state="eligible_shadow" if eligible else ("awaiting_future_reobservation" if ev["reobserved"]<=0 else ("awaiting_target_read" if not rd["available"] else "awaiting_stability"))
    water=(ev["watermark"],rd["watermark"],st["watermark"]);changed=water!=tuple(int(x or 0) for x in old)
    return {"events":ev,"read":rd,"stability":st,"real":real,"eligible":eligible,"missing":missing,"state":state,"watermarks":water,"changed":changed}
def source_rows(c,cp_t,cp_id,n):
    if n<=0 or not exists(c,SOURCE):return []
    return c.execute("SELECT stable_observation_key,shadow_key,hypothesis_id,latest_source_updated_at,COALESCE(latest_projection_fingerprint,''),COALESCE(target_chunk_ids,'[]') FROM "+SOURCE+" WHERE (COALESCE(latest_source_updated_at,0)>? OR (COALESCE(latest_source_updated_at,0)=? AND hypothesis_id>?)) ORDER BY COALESCE(latest_source_updated_at,0),hypothesis_id LIMIT ?",(cp_t,cp_t,cp_id,n)).fetchall()
def recheck_rows(c,cursor,n):
    if n<=0:return []
    base="SELECT eligibility_key,stable_observation_key,shadow_key,hypothesis_id,baseline_source_updated_at,source_provenance,last_event_watermark,last_read_watermark,last_stability_watermark FROM "+SHADOW+" WHERE non_productive_eligible=0 "
    rows=c.execute(base+"AND eligibility_key>? ORDER BY eligibility_key LIMIT ?",(cursor,n)).fetchall()
    if len(rows)<n:rows+=c.execute(base+"AND eligibility_key<=? ORDER BY eligibility_key LIMIT ?",(cursor,n-len(rows))).fetchall()
    return rows

def run_phase(c,limit=LIMIT,recheck_limit=DEFAULT_RECHECK_LIMIT):
    limit=min(max(1,int(limit)),LIMIT);recheck_limit=min(max(0,int(recheck_limit)),limit);ingest_limit=limit-recheck_limit
    ensure_schema(c);self_check(c);before=protected(c);state=_read_kv(c,STATE);ts=now();cp_t=int(state.get("checkpoint_updated_at",0) or 0);cp_id=int(state.get("checkpoint_hypothesis_id",0) or 0);cursor=str(state.get("recheck_cursor_key","") or "")
    rechecks=recheck_rows(c,cursor,recheck_limit);r_changed=r_eligible=0;await_reobs=await_read=await_stability=0;real_total=eligible_total=0;last_cursor=cursor;errors=[]
    for row in rechecks:
        try:
            key,stable,shadow,hid,baseline,prov,ew,rw,sw=row;targets=parse_targets((json.loads(prov) if prov else {}).get("target_chunk_ids",[]));e=evaluate(c,int(hid),int(baseline),targets,(ew,rw,sw));last_cursor=str(key);r_changed+=int(e["changed"]);r_eligible+=int(e["eligible"]);real_total+=int(e["real"]);eligible_total+=int(e["eligible"]);await_reobs+=int("delayed_raw_reobservation" in e["missing"]);await_read+=int("delayed_target_read_outcome" in e["missing"]);await_stability+=int("hypothesis_stability" in e["missing"])
            details={"contract":VERSION,"event_reason":e["events"]["reason"],"read_outcome":e["read"],"stability_reason":e["stability"]["reason"],"productive_handoff":False,"phase5i_write":False}
            c.execute("UPDATE "+SHADOW+" SET delayed_event_count=?,delayed_reobservation_count=?,first_delayed_event_at=?,last_delayed_event_at=?,stability_available=?,stability=?,real_outcome_observation_available=?,non_productive_eligible=?,eligibility_state=?,missing_signals=?,productive_write=0,details=?,last_seen_at=?,last_evaluated_at=?,recheck_count=recheck_count+1,last_event_watermark=?,last_read_watermark=?,last_stability_watermark=?,evidence_changed=?,version_count=version_count+1 WHERE eligibility_key=?",(e["events"]["count"],e["events"]["reobserved"],e["events"]["first"],e["events"]["last"],int(e["stability"]["available"]),e["stability"]["value"],int(e["real"]),int(e["eligible"]),e["state"],canon(e["missing"]),canon(details),ts,ts,*e["watermarks"],int(e["changed"]),key))
        except Exception as exc:errors.append("recheck:"+type(exc).__name__+":"+str(exc));break
    created=updated=0;after_t,after_id=cp_t,cp_id
    for row in source_rows(c,cp_t,cp_id,ingest_limit) if not errors else []:
        try:
            stable,shadow,hid,baseline,pf,target_json=row;targets=parse_targets(target_json);e=evaluate(c,int(hid),int(baseline),targets);key=fingerprint([stable,int(hid),int(baseline),"non_productive_delayed_eligibility"]);ex=c.execute("SELECT 1 FROM "+SHADOW+" WHERE eligibility_key=?",(key,)).fetchone() is not None;prov={"baseline_table":SOURCE,"baseline_identity":stable,"delayed_event_table":EVENTS,"delayed_identity":int(hid),"read_outcome_table":READS,"stability_table":STABILITY,"time_order_required":True,"causal_effect_claimed":False,"target_chunk_ids":targets};details={"contract":VERSION,"event_reason":e["events"]["reason"],"read_outcome":e["read"],"stability_reason":e["stability"]["reason"],"productive_handoff":False,"phase5i_write":False}
            c.execute("INSERT INTO "+SHADOW+"(eligibility_key,stable_observation_key,shadow_key,hypothesis_id,baseline_source_updated_at,baseline_projection_fingerprint,delayed_event_count,delayed_reobservation_count,first_delayed_event_at,last_delayed_event_at,stability_available,stability,real_outcome_observation_available,non_productive_eligible,eligibility_state,source_provenance,missing_signals,productive_write,details,first_seen_at,last_seen_at,version_count,last_evaluated_at,recheck_count,last_event_watermark,last_read_watermark,last_stability_watermark,evidence_changed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?,?,1,?,0,?,?,?,?) ON CONFLICT(eligibility_key) DO NOTHING",(key,stable,shadow,int(hid),int(baseline),pf,e["events"]["count"],e["events"]["reobserved"],e["events"]["first"],e["events"]["last"],int(e["stability"]["available"]),e["stability"]["value"],int(e["real"]),int(e["eligible"]),e["state"],canon(prov),canon(e["missing"]),0,canon(details),ts,ts,ts,*e["watermarks"],int(e["changed"])));created+=int(not ex);updated+=int(ex);real_total+=int(e["real"]);eligible_total+=int(e["eligible"]);await_reobs+=int("delayed_raw_reobservation" in e["missing"]);await_read+=int("delayed_target_read_outcome" in e["missing"]);await_stability+=int("hypothesis_stability" in e["missing"]);after_t,after_id=int(baseline),int(hid)
        except Exception as exc:errors.append("ingest:"+type(exc).__name__+":"+str(exc));break
    after=protected(c);safety=before==after and not errors
    c.execute("INSERT INTO "+CYCLES+"(phase,source_rows_seen,shadow_rows_created,shadow_rows_updated,real_outcome_available,non_productive_eligible,awaiting_delayed_reobservation,awaiting_stability,checkpoint_updated_at_before,checkpoint_hypothesis_id_before,checkpoint_updated_at_after,checkpoint_hypothesis_id_after,protected_before,protected_after,safety_ok,mode,created_at,details,recheck_rows_seen,recheck_rows_changed,recheck_rows_eligible,awaiting_target_read) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(VERSION,created+updated,created,updated,real_total,eligible_total,await_reobs,await_stability,cp_t,cp_id,after_t,after_id,canon(before),canon(after),int(safety),"shadow_recheck",ts,canon({"errors":errors,"total_budget":limit,"ingest_budget":ingest_limit,"recheck_budget":recheck_limit}),len(rechecks),r_changed,r_eligible,await_read))
    if safety:
        write_state(c,{"checkpoint_updated_at":after_t,"checkpoint_hypothesis_id":after_id,"recheck_cursor_key":last_cursor,"last_recheck_rows_seen":len(rechecks),"last_recheck_rows_changed":r_changed,"last_recheck_rows_eligible":r_eligible,"last_source_rows_seen":created+updated,"last_safety_ok":True,"productive_writes":"disabled","phase5i_writes":"disabled","causal_effect_claimed":"false"},ts)
    else:raise RuntimeError("V1.1 safety failure: "+repr(errors))
    return {"phase":VERSION,"mode":"shadow_recheck","budget_total":limit,"ingest_rows_seen":created+updated,"recheck_rows_seen":len(rechecks),"recheck_rows_changed":r_changed,"recheck_rows_eligible":r_eligible,"real_outcome_observation_available":real_total,"non_productive_eligible":eligible_total,"awaiting_delayed_reobservation":await_reobs,"awaiting_target_read":await_read,"awaiting_stability":await_stability,"productive_writes":0,"phase5i_writes":0,"safety_ok":True}
def run_db(path,limit,recheck_limit):
    c=sqlite3.connect(str(path))
    try:c.execute("BEGIN IMMEDIATE");r=run_phase(c,limit,recheck_limit);c.commit();return r
    except Exception:c.rollback();raise
    finally:c.close()
def selftest():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/"x.sqlite3";c=sqlite3.connect(db);c.executescript("""
        CREATE TABLE modern_gap_phase5f_shadow_observation_v2_latest(stable_observation_key TEXT,shadow_key TEXT,hypothesis_id INTEGER,latest_source_updated_at INTEGER,latest_projection_fingerprint TEXT,target_chunk_ids TEXT);
        CREATE TABLE context_learning_events(hypothesis_id INTEGER,event_type TEXT,created_at INTEGER);CREATE TABLE reading_queue(chunk_id INTEGER,status TEXT,read_count INTEGER,updated_at INTEGER);CREATE TABLE hypothesis_stability_scores(hypothesis_id INTEGER,stability REAL,updated_at INTEGER);
        CREATE TABLE facts(id INTEGER);CREATE TABLE relations(id INTEGER);CREATE TABLE questions(id INTEGER);CREATE TABLE internal_learning_gaps(id INTEGER);CREATE TABLE phase5i_outcome_driven_experiments(id INTEGER);CREATE TABLE modern_outcome_bridge_shadow(id INTEGER);
        INSERT INTO modern_gap_phase5f_shadow_observation_v2_latest VALUES('o','s',1,100,'p','[10]');
        """);c.commit();r1=run_phase(c,2,0);c.commit();assert r1["ingest_rows_seen"]==1 and r1["non_productive_eligible"]==0;c.execute("INSERT INTO context_learning_events VALUES(1,'raw_observation_reobserved',110)");c.execute("INSERT INTO reading_queue VALUES(10,'read',1,111)");c.execute("INSERT INTO hypothesis_stability_scores VALUES(1,.2,112)");c.commit();r2=run_phase(c,2,2);c.commit();assert r2["recheck_rows_seen"]==1 and r2["recheck_rows_changed"]==1 and r2["recheck_rows_eligible"]==1;assert count(c,"phase5i_outcome_driven_experiments")==0;row=c.execute("SELECT non_productive_eligible,recheck_count,productive_write FROM "+SHADOW).fetchone();assert tuple(row)==(1,1,0);c.close()
    print("SELFTEST PASS");print(canon({"bounded_total_budget":True,"ingestion_checkpoint":True,"recheck_cursor":True,"watermark_progression":True,"awaiting_states":True,"productive_writes":False,"phase5i_writes":False}));return 0
def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="cmd",required=True);s.add_parser("selftest");r=s.add_parser("run");r.add_argument("--db",default="ki_memory.sqlite3");r.add_argument("--limit",type=int,default=LIMIT);r.add_argument("--recheck-limit",type=int,default=DEFAULT_RECHECK_LIMIT);a=p.parse_args();
    if a.cmd=="selftest":return selftest()
    print(canon(run_db(Path(a.db),a.limit,a.recheck_limit)));return 0
if __name__=="__main__":raise SystemExit(main())
