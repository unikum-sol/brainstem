# -*- coding: utf-8 -*-
"""BrainStem shadow-only runtime adapter for delayed-evidence recheck V1.2.

The adapter owns budget, failure isolation and provenance gates. It delegates
eligibility evaluation unchanged to V1.2 and never propagates phase exceptions
into the host runtime.
"""
from __future__ import annotations
import hashlib, importlib.util, json, sqlite3, tempfile, time
from pathlib import Path
from typing import Any, Dict, Optional

VERSION="non_productive_recheck_shadow_runtime_registration_v1"
PHASE_NAME=VERSION
TARGET_FILE="v8_non_productive_recheck_initialization_cursor_wrap_fairness_telemetry_v1_2.py"
DEFAULT_TOTAL_BUDGET=64
DEFAULT_RECHECK_BUDGET=32
HARD_MAX_BUDGET=64
STATE="non_productive_recheck_runtime_state"
CYCLES="non_productive_recheck_runtime_cycles"
PROTECTED=("facts","relations","questions","internal_learning_gaps","chunk_attention_scores","phase5f_context_window_experiments","phase5g_strategy_experiments","phase5g_experiment_outcomes","phase5i_outcome_driven_experiments","modern_outcome_bridge_shadow")
SCHEMA_TABLES={
 STATE:["key","value","updated_at"],
 CYCLES:["id","phase","started_at","finished_at","status","total_budget","recheck_budget","source_module","source_hash","source_version","provenance_ok","protected_before","protected_after","protected_unchanged","result","error_type","error_message","error_hash","runtime_continued","productive_writes","phase5i_writes"]}

def _now():return int(time.time())
def _canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
def _q(s):return '"'+str(s).replace('"','""')+'"'
def _exists(c,t):return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _cols(c,t):return [r[1] for r in c.execute("PRAGMA table_info("+_q(t)+")")]
def _count(c,t):return int(c.execute("SELECT COUNT(*) FROM "+_q(t)).fetchone()[0]) if _exists(c,t) else None
def _protected(c):return {t:_count(c,t) for t in PROTECTED}
def _read_kv(con: sqlite3.Connection, table: str) -> Dict[str, Any]:
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())
def _hash(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def ensure_schema(c):
    c.execute("CREATE TABLE IF NOT EXISTS "+STATE+"(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS "+CYCLES+"(id INTEGER PRIMARY KEY AUTOINCREMENT,phase TEXT NOT NULL,started_at INTEGER NOT NULL,finished_at INTEGER NOT NULL,status TEXT NOT NULL,total_budget INTEGER NOT NULL,recheck_budget INTEGER NOT NULL,source_module TEXT NOT NULL,source_hash TEXT NOT NULL,source_version TEXT NOT NULL,provenance_ok INTEGER NOT NULL,protected_before TEXT NOT NULL,protected_after TEXT NOT NULL,protected_unchanged INTEGER NOT NULL,result TEXT NOT NULL,error_type TEXT,error_message TEXT,error_hash TEXT,runtime_continued INTEGER NOT NULL,productive_writes INTEGER NOT NULL DEFAULT 0,phase5i_writes INTEGER NOT NULL DEFAULT 0)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_np_runtime_cycles_status ON "+CYCLES+"(status,finished_at)")
    defaults={"phase":PHASE_NAME,"mode":"shadow_only","enabled":"true","total_budget":str(DEFAULT_TOTAL_BUDGET),"recheck_budget":str(DEFAULT_RECHECK_BUDGET),"hard_max_budget":str(HARD_MAX_BUDGET),"failure_policy":"isolate_and_continue","provenance_gate":"required","runtime_registration":"installed","productive_writes":"disabled","phase5i_writes":"disabled","causal_effect_claimed":"false","last_status":"never_run","last_error_hash":""};n=_now()
    for k,v in defaults.items():c.execute("INSERT OR IGNORE INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?)",(k,v,n))
def self_check_schema(c):
    for t,required in SCHEMA_TABLES.items():
        missing=[x for x in required if x not in _cols(c,t)]
        if missing:raise RuntimeError("Runtime schema missing for "+t+": "+", ".join(missing))
def _write_state(c,values,n):
    for k,v in values.items():c.execute("INSERT INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,str(v).lower() if isinstance(v,bool) else str(v),n))
def _load_target(path):
    spec=importlib.util.spec_from_file_location("brainstem_np_runtime_target",str(path))
    if spec is None or spec.loader is None:raise RuntimeError("Cannot load target module")
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run_registered_phase(con: sqlite3.Connection, total_budget: Optional[int]=None, recheck_budget: Optional[int]=None, **_:Any)->Dict[str,Any]:
    """Host-safe entry point. Never raises after schema availability."""
    started=_now();ensure_schema(con);self_check_schema(con);state=_read_kv(con,STATE)
    if str(state.get("enabled","true")).lower()!="true":return {"phase":PHASE_NAME,"status":"disabled","runtime_continued":True,"productive_writes":0,"phase5i_writes":0}
    total=min(max(1,int(total_budget if total_budget is not None else state.get("total_budget",DEFAULT_TOTAL_BUDGET))),HARD_MAX_BUDGET)
    recheck=min(max(0,int(recheck_budget if recheck_budget is not None else state.get("recheck_budget",DEFAULT_RECHECK_BUDGET))),total)
    target_path=Path(__file__).resolve().with_name(TARGET_FILE);before=_protected(con);source_hash="";source_version="unknown";provenance_ok=False;result={};status="error_isolated";etype=emsg=ehash=None
    try:
        if not target_path.exists():raise RuntimeError("Target module missing: "+TARGET_FILE)
        source_hash=_hash(target_path);target=_load_target(target_path);source_version=str(getattr(target,"VERSION","unknown"));provenance_ok=bool(source_hash and source_version!="unknown" and callable(getattr(target,"run_phase",None)))
        if not provenance_ok:raise RuntimeError("Target provenance gate failed")
        nested=con.in_transaction
        if nested:con.execute("SAVEPOINT np_runtime_shadow")
        try:
            result=target.run_phase(con,total,recheck)
            after_inner=_protected(con)
            if before!=after_inner:raise RuntimeError("Protected counts changed")
            if int(result.get("productive_writes",0))!=0 or int(result.get("phase5i_writes",0))!=0:raise RuntimeError("Target reported forbidden writes")
            if nested:con.execute("RELEASE SAVEPOINT np_runtime_shadow")
            status="ok"
        except Exception:
            if nested:
                con.execute("ROLLBACK TO SAVEPOINT np_runtime_shadow");con.execute("RELEASE SAVEPOINT np_runtime_shadow")
            raise
    except Exception as exc:
        etype=type(exc).__name__;emsg=str(exc)[:1000];ehash=hashlib.sha256((etype+":"+emsg).encode()).hexdigest();result={"phase":PHASE_NAME,"status":"error_isolated","runtime_continued":True,"productive_writes":0,"phase5i_writes":0}
    after=_protected(con);unchanged=before==after;finished=_now()
    con.execute("INSERT INTO "+CYCLES+"(phase,started_at,finished_at,status,total_budget,recheck_budget,source_module,source_hash,source_version,provenance_ok,protected_before,protected_after,protected_unchanged,result,error_type,error_message,error_hash,runtime_continued,productive_writes,phase5i_writes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(PHASE_NAME,started,finished,status,total,recheck,TARGET_FILE,source_hash,source_version,int(provenance_ok),_canon(before),_canon(after),int(unchanged),_canon(result),etype,emsg,ehash,1,0,0))
    _write_state(con,{"last_status":status,"last_started_at":started,"last_finished_at":finished,"last_source_hash":source_hash,"last_source_version":source_version,"last_provenance_ok":provenance_ok,"last_protected_unchanged":unchanged,"last_error_hash":ehash or "","runtime_continued":True,"productive_writes":"disabled","phase5i_writes":"disabled"},finished)
    result=dict(result);result.update({"runtime_phase":PHASE_NAME,"runtime_status":status,"runtime_continued":True,"runtime_total_budget":total,"runtime_recheck_budget":recheck,"provenance_ok":provenance_ok,"protected_unchanged":unchanged,"productive_writes":0,"phase5i_writes":0})
    return result

def registered_phase_spec():
    return {"name":PHASE_NAME,"callable":run_registered_phase,"mode":"shadow_only","budget":DEFAULT_TOTAL_BUDGET,"recheck_budget":DEFAULT_RECHECK_BUDGET,"failure_policy":"isolate_and_continue","productive_writes":False,"phase5i_writes":False}
def selftest():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);db=root/"x.sqlite3";target=root/TARGET_FILE
        target.write_text("VERSION='test_target'\ndef run_phase(con,limit,recheck_limit):\n    return {'phase':'test','productive_writes':0,'phase5i_writes':0}\n",encoding="utf-8")
        global __file__;old=__file__;__file__=str(root/Path(old).name)
        try:
            c=sqlite3.connect(db);c.execute("CREATE TABLE facts(id INTEGER)");r=run_registered_phase(c,999,999);c.commit();assert r["runtime_status"]=="ok" and r["runtime_total_budget"]==HARD_MAX_BUDGET and r["runtime_recheck_budget"]==HARD_MAX_BUDGET
            target.write_text("raise RuntimeError('boom')\n",encoding="utf-8");r2=run_registered_phase(c,64,32);c.commit();assert r2["runtime_status"]=="error_isolated" and r2["runtime_continued"];assert _count(c,"facts")==0;c.close()
        finally:__file__=old
    print("SELFTEST PASS");print(_canon({"budget_gate":True,"error_isolation":True,"provenance_gate":True,"protected_counts":True,"runtime_continued":True,"productive_writes":False,"phase5i_writes":False}));return 0
if __name__=="__main__":selftest()
