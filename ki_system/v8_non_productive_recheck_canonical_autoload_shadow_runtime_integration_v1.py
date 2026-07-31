from __future__ import annotations
import inspect,json,sqlite3,time
from pathlib import Path
PHASE="non_productive_recheck_shadow_runtime_v1"
PATCH_MARKER="brainstem_per_cycle_runtime_provenance_fix_v1"
TOTAL_BUDGET=64
RECHECK_BUDGET=64

def _table_exists(con,table):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None

def _columns(con,table):
    if not _table_exists(con,table): return set()
    return {r[1] for r in con.execute("PRAGMA table_info("+'"'+table.replace('"','""')+'"'+")").fetchall()}

def _ensure_schema(con):
    con.execute("CREATE TABLE IF NOT EXISTS non_productive_recheck_runtime_invocations(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at INTEGER NOT NULL,autonomous_cycle INTEGER,connection_source TEXT NOT NULL,connection_found INTEGER NOT NULL,registered_phase_entered INTEGER NOT NULL,registered_phase_completed INTEGER NOT NULL,status TEXT NOT NULL,gate_reason TEXT NOT NULL DEFAULT '',exception_type TEXT NOT NULL DEFAULT '',exception_text TEXT NOT NULL DEFAULT '',runtime_cycle_rows_before INTEGER,runtime_cycle_rows_after INTEGER,neuromod_updated_at_before INTEGER,neuromod_updated_at_after INTEGER,neuromod_event_rows_before INTEGER,neuromod_event_rows_after INTEGER,result_json TEXT NOT NULL DEFAULT '{}',productive_writes INTEGER NOT NULL DEFAULT 0,phase5i_writes INTEGER NOT NULL DEFAULT 0)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_np_recheck_runtime_invocations_cycle ON non_productive_recheck_runtime_invocations(autonomous_cycle,id)")
    con.execute("CREATE TABLE IF NOT EXISTS non_productive_recheck_runtime_bridge_state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    con.commit()

def _self_check_schema(con):
    required={"id","created_at","autonomous_cycle","connection_source","connection_found","registered_phase_entered","registered_phase_completed","status","gate_reason","exception_type","exception_text","runtime_cycle_rows_before","runtime_cycle_rows_after","neuromod_updated_at_before","neuromod_updated_at_after","neuromod_event_rows_before","neuromod_event_rows_after","result_json","productive_writes","phase5i_writes"}
    missing=sorted(required-_columns(con,"non_productive_recheck_runtime_invocations"))
    if missing: raise RuntimeError("schema missing: "+",".join(missing))

def _connection_from(value,seen=None,depth=0,path="context"):
    if isinstance(value,sqlite3.Connection): return value,path
    if value is None or depth>8: return None,path
    if seen is None: seen=set()
    if id(value) in seen: return None,path
    seen.add(id(value))
    names=("con","conn","connection","db","memory","mem","m","store","database","_con","_conn","_connection","_db")
    if isinstance(value,(tuple,list)):
        for i,item in enumerate(value):
            found,where=_connection_from(item,seen,depth+1,path+"["+str(i)+"]")
            if found is not None:return found,where
    if isinstance(value,dict):
        for name in names:
            if name in value:
                found,where=_connection_from(value[name],seen,depth+1,path+"["+name+"]")
                if found is not None:return found,where
    for name in names:
        try:item=getattr(value,name)
        except Exception:continue
        found,where=_connection_from(item,seen,depth+1,path+"."+name)
        if found is not None:return found,where
    return None,path

def _fallback_connection():
    path=Path("ki_memory.sqlite3").resolve()
    if not path.is_file():return None,"fallback_missing:"+str(path)
    con=sqlite3.connect(str(path),timeout=30);con.row_factory=sqlite3.Row
    return con,"fallback_owned:"+str(path)

def _scalar(con,sql):
    try:
        row=con.execute(sql).fetchone();return None if row is None else row[0]
    except sqlite3.Error:return None

def _snapshot(con):
    cycles=_scalar(con,"SELECT COUNT(*) FROM non_productive_recheck_runtime_cycles") if _table_exists(con,"non_productive_recheck_runtime_cycles") else None
    updated=_scalar(con,"SELECT MAX(updated_at) FROM neuromodulator_state") if _table_exists(con,"neuromodulator_state") and "updated_at" in _columns(con,"neuromodulator_state") else None
    events=_scalar(con,"SELECT COUNT(*) FROM neuromodulator_events") if _table_exists(con,"neuromodulator_events") else None
    return cycles,updated,events

def _cycle_index(loop):
    for name in ("cycle_index","cycle_count","current_cycle","cycles","_cycle_index"):
        try:
            value=getattr(loop,name)
            if not callable(value):return int(value)
        except Exception:pass
    return None

def _invoke_registered(con):
    from ki_system.v8_non_productive_recheck_shadow_runtime_registration_v1 import run_registered_phase
    params=inspect.signature(run_registered_phase).parameters;kwargs={}
    if "total_budget" in params:kwargs["total_budget"]=TOTAL_BUDGET
    if "recheck_budget" in params:kwargs["recheck_budget"]=RECHECK_BUDGET
    return run_registered_phase(con,**kwargs)

def _record(con,v):
    cols=("created_at","autonomous_cycle","connection_source","connection_found","registered_phase_entered","registered_phase_completed","status","gate_reason","exception_type","exception_text","runtime_cycle_rows_before","runtime_cycle_rows_after","neuromod_updated_at_before","neuromod_updated_at_after","neuromod_event_rows_before","neuromod_event_rows_after","result_json","productive_writes","phase5i_writes")
    con.execute("INSERT INTO non_productive_recheck_runtime_invocations("+",".join(cols)+") VALUES("+",".join("?" for _ in cols)+")",tuple(v.get(k) for k in cols))
    for key,val in (("last_invocation_at",v["created_at"]),("last_status",v["status"]),("last_connection_source",v["connection_source"])):
        con.execute("INSERT INTO non_productive_recheck_runtime_bridge_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(val)))
    con.commit()

def _run_shadow(loop,args,kwargs):
    con,source=_connection_from((loop,args,kwargs));owned=False
    if con is None:con,source=_fallback_connection();owned=con is not None
    if con is None:
        print("[NP_RECHECK_PER_CYCLE] connection_missing "+source,flush=True)
        return {"phase":PHASE,"status":"connection_missing","runtime_continued":True,"productive_writes":0,"phase5i_writes":0}
    v={"created_at":int(time.time()),"autonomous_cycle":_cycle_index(loop),"connection_source":source,"connection_found":1,"registered_phase_entered":0,"registered_phase_completed":0,"status":"started","gate_reason":"","exception_type":"","exception_text":"","result_json":"{}","productive_writes":0,"phase5i_writes":0}
    try:
        _ensure_schema(con);_self_check_schema(con)
        v["runtime_cycle_rows_before"],v["neuromod_updated_at_before"],v["neuromod_event_rows_before"]=_snapshot(con)
        v["registered_phase_entered"]=1;result=_invoke_registered(con);v["registered_phase_completed"]=1
        if isinstance(result,dict):
            v["status"]=str(result.get("status","completed"));v["gate_reason"]=str(result.get("reason",result.get("gate_reason","")))
            v["productive_writes"]=int(result.get("productive_writes",0) or 0);v["phase5i_writes"]=int(result.get("phase5i_writes",0) or 0)
        else:v["status"]="completed"
        if v["productive_writes"] or v["phase5i_writes"]:raise RuntimeError("shadow safety counter nonzero")
        v["result_json"]=json.dumps(result,ensure_ascii=False,sort_keys=True,default=str)
    except Exception as exc:
        v["status"]="error";v["exception_type"]=type(exc).__name__;v["exception_text"]=str(exc)[:2000];v["result_json"]=json.dumps({"error":type(exc).__name__,"message":str(exc)},ensure_ascii=False)
        print("[NP_RECHECK_PER_CYCLE_ERROR] "+type(exc).__name__+": "+str(exc),flush=True)
    finally:
        v["runtime_cycle_rows_after"],v["neuromod_updated_at_after"],v["neuromod_event_rows_after"]=_snapshot(con);_record(con,v)
        # NP_RECHECK_PER_CYCLE_QUIET_SUCCESS_V1: successful cycles are persisted but not printed.
        if owned:con.close()
    return {"phase":PHASE,"status":v["status"],"gate_reason":v["gate_reason"],"runtime_continued":True,"productive_writes":0,"phase5i_writes":0}

def autoload(AutonomousLoop=None):
    if AutonomousLoop is None:from ki_system.autonomous import AutonomousLoop
    marker="_"+PATCH_MARKER
    if getattr(AutonomousLoop,marker,False):return AutonomousLoop
    current=getattr(AutonomousLoop,"cycle",None)
    if not callable(current):raise RuntimeError("AutonomousLoop.cycle not callable")
    def managed_cycle(self,*args,**kwargs):
        downstream=current(self,*args,**kwargs);shadow=_run_shadow(self,args,kwargs)
        if isinstance(downstream,dict):downstream[PHASE]=shadow;return downstream
        return {"downstream":downstream,PHASE:shadow}
    managed_cycle.__wrapped__=current;AutonomousLoop.cycle=managed_cycle;setattr(AutonomousLoop,marker,True);return AutonomousLoop

autoload()
