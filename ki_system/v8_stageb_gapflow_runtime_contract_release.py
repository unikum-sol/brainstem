# -*- coding: utf-8 -*-
"""Stage-B E+F: shadow gap-flow orchestration and backend-authoritative runtime contract."""
from __future__ import annotations
import json, os, sqlite3, time
from pathlib import Path
PHASE="stageb_gapflow_runtime_contract_release"; VERSION="stageb_ef_v1"
STATE="stageb_runtime_contract_state"; CYCLES="stageb_runtime_contract_cycles"
PROTECTED=("internal_learning_gaps","chunk_attention_scores","phase5f_context_window_experiments","phase5g_strategy_experiments","phase5i_outcome_driven_experiments","facts","relations","questions")
SCHEMA_TABLES={
 STATE:[("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
 CYCLES:[("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("backend_cycle","INTEGER"),("outcome_source_rows","INTEGER"),("gap_source_rows","INTEGER"),("phase5f_source_rows","INTEGER"),("phase5f_observations","INTEGER"),("candidate_flow_state","TEXT"),("protected_before","TEXT"),("protected_after","TEXT"),("safety_ok","INTEGER"),("errors","TEXT")]
}
def _now(): return int(time.time())
def _exists(c,t): return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _cols(c,t): return [r[1] for r in c.execute("PRAGMA table_info("+t+")")] if _exists(c,t) else []
def _read_kv(con,table):
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())
def _set(c,k,v): c.execute("INSERT INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,str(v).lower() if isinstance(v,bool) else str(v),_now()))
def _i(v,d=0):
    try:return int(float(v))
    except Exception:return d
def _count(c,t): return int(c.execute("SELECT COUNT(*) FROM "+t).fetchone()[0]) if _exists(c,t) else 0
def _protected(c): return {t:_count(c,t) for t in PROTECTED}
def resolve_db(obj=None):
    if isinstance(obj,sqlite3.Connection): obj.row_factory=sqlite3.Row; return obj
    if obj is not None:
        for a in ("db","conn","con","connection"):
            v=getattr(obj,a,None)
            if isinstance(v,sqlite3.Connection):v.row_factory=sqlite3.Row;return v
        for a in ("mem","memory"):
            v=getattr(obj,a,None)
            if v is not None and v is not obj:
                try:return resolve_db(v)
                except Exception:pass
    path="ki_memory.sqlite3"; p=Path(__file__).resolve().parent.parent/path
    if not os.path.exists(path) and p.exists():path=str(p)
    c=sqlite3.connect(path,timeout=60);c.row_factory=sqlite3.Row;return c
def ensure_schema(c):
    for t,defs in SCHEMA_TABLES.items():
        if not _exists(c,t): c.execute("CREATE TABLE "+t+" ("+", ".join(n+" "+d for n,d in defs)+")")
        else:
            live=set(_cols(c,t))
            for n,d in defs:
                if n not in live and "PRIMARY KEY" not in d.upper() and "AUTOINCREMENT" not in d.upper():c.execute("ALTER TABLE "+t+" ADD COLUMN "+n+" "+d)
    c.execute("CREATE INDEX IF NOT EXISTS idx_stageb_runtime_backend_cycle ON "+CYCLES+"(backend_cycle)")
    for k,v in {"backend_cycle":"0","backend_status":"idle","gui_render_stride":"5","diagnostic_stride":"25","candidate_flow_state":"unmeasured","last_safety_ok":"true","productive_writes":"disabled"}.items():c.execute("INSERT OR IGNORE INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?)",(k,v,_now()))
    c.commit();return _self_check_schema(c)
def _self_check_schema(c):
    miss=[]
    for t,defs in SCHEMA_TABLES.items():
        live=set(_cols(c,t));miss += [t+"."+n for n,_ in defs if n not in live]
    if miss:raise RuntimeError("stageb runtime schema missing: "+repr(miss))
    return {"overall":True,"missing":[]}
def _source_rows(r):
    if not isinstance(r,dict):return 0
    for k in ("source_rows_seen","rows_seen","source_rows"):
        if k in r:return _i(r.get(k),0)
    return 0
def observe_cycle(obj=None,backend_cycle=None):
    c=resolve_db(obj);ensure_schema(c);st=_read_kv(c,STATE);cycle=_i(backend_cycle,_i(st.get("backend_cycle"),0)+1);before=_protected(c);errors=[]
    results={}
    modules=(("outcome","v8_modern_outcome_bridge_shadow_release",1200),("gap","v8_modern_gap_candidate_bridge_shadow_release",512),("phase5f","v8_modern_gap_phase5f_shadow_observation_release",512))
    for label,name,limit in modules:
        try:
            m=__import__("ki_system."+name,fromlist=["observe_shadow"]);results[label]=m.observe_shadow(c,limit=limit)
        except Exception as exc:errors.append(label+":"+type(exc).__name__+":"+str(exc));results[label]={"status":"error"}
    after=_protected(c);safe=before==after and not errors
    outcome_rows=_source_rows(results["outcome"]);gap_rows=_source_rows(results["gap"]);p5_rows=_source_rows(results["phase5f"])
    p5_obs=_i(results["phase5f"].get("observations_created"),0)+_i(results["phase5f"].get("observations_updated"),0)
    if errors:flow="error"
    elif outcome_rows==0 and gap_rows==0 and p5_rows==0:flow="measured_zero_no_new_sources"
    elif gap_rows>0 or p5_rows>0:flow="real_candidates_observed_shadow_only"
    else:flow="upstream_outcomes_without_gap_candidates"
    if not safe: c.rollback(); raise RuntimeError("stageb E protected-count or pipeline failure: "+repr(errors)+" before="+repr(before)+" after="+repr(after))
    c.execute("INSERT INTO "+CYCLES+"(created_at,backend_cycle,outcome_source_rows,gap_source_rows,phase5f_source_rows,phase5f_observations,candidate_flow_state,protected_before,protected_after,safety_ok,errors) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(_now(),cycle,outcome_rows,gap_rows,p5_rows,p5_obs,flow,json.dumps(before,sort_keys=True),json.dumps(after,sort_keys=True),1,json.dumps(errors)))
    for k,v in {"backend_cycle":cycle,"backend_status":"running","last_backend_at":_now(),"candidate_flow_state":flow,"last_outcome_source_rows":outcome_rows,"last_gap_source_rows":gap_rows,"last_phase5f_source_rows":p5_rows,"last_phase5f_observations":p5_obs,"last_safety_ok":True,"productive_writes":"disabled"}.items():_set(c,k,v)
    c.commit();return {"phase":PHASE,"version":VERSION,"backend_cycle":cycle,"candidate_flow_state":flow,"results":results,"protected_unchanged":True,"productive_writes":0}
def mark_backend_stopped(obj=None):
    c=resolve_db(obj);ensure_schema(c);_set(c,"backend_status","stopped");_set(c,"last_backend_at",_now());c.commit();return True
def managed_cycle(self,progress=None):
    downstream=None
    try:
        from ki_system import v8_stageb_guarded_hypothesis_graduation_release as m;downstream=m.managed_cycle(self,progress)
    except Exception as exc:downstream={"status":"downstream_error","error":str(exc)}
    # BRAINSTEM CALLBACK PROPAGATION FIX V1
    try:result=observe_cycle(self, progress)
    except Exception as exc:result={"phase":PHASE,"status":"error","error":type(exc).__name__+":"+str(exc),"productive_writes":0}
    return {"phase":PHASE,"downstream_result":downstream,"stageb_runtime_contract_result":result}
def managed_run(self,cycles=1,progress=None):return {"phase":PHASE,"results":[managed_cycle(self,progress) for _ in range(max(1,int(cycles or 1)))]}
def autoload(AutonomousLoop):
    AutonomousLoop.cycle=managed_cycle;AutonomousLoop.run=managed_run;AutonomousLoop.stageb_gapflow_runtime_contract=True
    AutonomousLoop.fact_promotion="disabled";AutonomousLoop.direct_fact_writes="disabled";AutonomousLoop.direct_relation_writes="disabled";return AutonomousLoop
