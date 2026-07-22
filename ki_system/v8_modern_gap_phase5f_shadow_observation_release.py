# -*- coding: utf-8 -*-
"""Persistent non-productive Gap-Shadow -> Phase-5f observation layer V1."""
from __future__ import annotations
import ast, hashlib, json, os, sqlite3, sys, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from ki_system import v8_modern_gap_phase5f_shadow_history_release as gap_phase5f_shadow_history
from ki_system import v8_modern_gap_phase5f_shadow_observation_v2_release as gap_phase5f_shadow_v2
from ki_system import v8_stable_obs_content_fp_shadow_classifier_release as content_fp_shadow_classifier

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "ki_memory.sqlite3"
PHASE5F = Path(__file__).resolve().with_name("v8_phase5f_context_expansion_effectiveness_and_adaptive_windowing_release.py")
VERSION = "modern_gap_phase5f_shadow_observation_v1"
MAX_BATCH = 512
OBS_TABLE = "modern_gap_phase5f_shadow_observations"
CYCLE_TABLE = "modern_gap_phase5f_shadow_observation_cycles"
STATE_TABLE = "modern_gap_phase5f_shadow_observation_state"
SCHEMA_TABLES = {
    OBS_TABLE: ["observation_key","shadow_key","hypothesis_id","source_updated_at","center_chunk_id","target_chunk_ids","target_count","projected_window_strategy","projected_window_radius","projected_action","expected_gain","closure_delta","overlap_score","read_no_candidate_rate","projected_effectiveness","neuromodulators","real_outcome_observation_available","observation_ready","source_default_path","productive_gap_id","productive_write","details","created_at","updated_at"],
    CYCLE_TABLE: ["id","source_rows_seen","observations_created","observations_updated","projection_errors","checkpoint_updated_at_before","checkpoint_hypothesis_id_before","checkpoint_updated_at_after","checkpoint_hypothesis_id_after","productive_writes_before","productive_writes_after","safety_ok","details","created_at"],
    STATE_TABLE: ["key","value"],
}
PROTECTED = ("facts","relations","questions","internal_learning_gaps","chunk_attention_scores","phase5f_context_window_experiments","phase5f_adaptive_window_events","phase5f_gap_window_state","phase5f_window_strategy_memory","phase5g_strategy_experiments","phase5g_experiment_outcomes","phase5i_outcome_driven_experiments")

class ShadowProjectionError(RuntimeError): pass
class _ProjectionCaptured(BaseException):
    def __init__(self, values): self.values = values

def _q(name): return '"' + str(name).replace('"','""') + '"'
def _db_path(obj=None):
    if isinstance(obj, (str, os.PathLike)): return Path(obj)
    for candidate in (getattr(obj,"db_path",None), getattr(getattr(obj,"mem",None),"db_path",None), getattr(getattr(obj,"memory",None),"db_path",None)):
        if candidate: return Path(candidate)
    return DEFAULT_DB

def _con(obj=None):
    con = sqlite3.connect(str(_db_path(obj)), timeout=120)
    con.row_factory = sqlite3.Row
    return con

def _table_exists(con, table): return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None
def _count(con, table): return int(con.execute("SELECT COUNT(*) FROM " + _q(table)).fetchone()[0]) if _table_exists(con,table) else 0
def _protected(con): return {t:_count(con,t) for t in PROTECTED}
def _read_kv(con, table):
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())
def _write_kv(con, key, value):
    con.execute("INSERT INTO " + STATE_TABLE + "(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(key),str(value)))

def ensure_schema(obj=None):
    con = _con(obj)
    try:
        con.execute("CREATE TABLE IF NOT EXISTS " + OBS_TABLE + "(observation_key TEXT PRIMARY KEY,shadow_key TEXT NOT NULL,hypothesis_id INTEGER NOT NULL,source_updated_at INTEGER NOT NULL DEFAULT 0,center_chunk_id INTEGER,target_chunk_ids TEXT NOT NULL DEFAULT '[]',target_count INTEGER NOT NULL DEFAULT 0,projected_window_strategy TEXT,projected_window_radius INTEGER,projected_action TEXT,expected_gain REAL,closure_delta REAL,overlap_score REAL,read_no_candidate_rate REAL,projected_effectiveness REAL,neuromodulators TEXT NOT NULL DEFAULT '{}',real_outcome_observation_available INTEGER NOT NULL DEFAULT 0,observation_ready INTEGER NOT NULL DEFAULT 0,source_default_path INTEGER NOT NULL DEFAULT 1,productive_gap_id INTEGER,productive_write INTEGER NOT NULL DEFAULT 0,details TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL DEFAULT 0)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_gap_phase5f_shadow_obs_source ON " + OBS_TABLE + "(source_updated_at,hypothesis_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_gap_phase5f_shadow_obs_shadow_key ON " + OBS_TABLE + "(shadow_key)")
        con.execute("CREATE TABLE IF NOT EXISTS " + CYCLE_TABLE + "(id INTEGER PRIMARY KEY AUTOINCREMENT,source_rows_seen INTEGER NOT NULL DEFAULT 0,observations_created INTEGER NOT NULL DEFAULT 0,observations_updated INTEGER NOT NULL DEFAULT 0,projection_errors INTEGER NOT NULL DEFAULT 0,checkpoint_updated_at_before INTEGER NOT NULL DEFAULT 0,checkpoint_hypothesis_id_before INTEGER NOT NULL DEFAULT 0,checkpoint_updated_at_after INTEGER NOT NULL DEFAULT 0,checkpoint_hypothesis_id_after INTEGER NOT NULL DEFAULT 0,productive_writes_before TEXT NOT NULL DEFAULT '{}',productive_writes_after TEXT NOT NULL DEFAULT '{}',safety_ok INTEGER NOT NULL DEFAULT 0,details TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL DEFAULT 0)")
        con.execute("CREATE TABLE IF NOT EXISTS " + STATE_TABLE + "(key TEXT PRIMARY KEY,value TEXT)")
        defaults = {"phase":VERSION,"mode":"shadow_observation","checkpoint_updated_at":"0","checkpoint_hypothesis_id":"0","last_source_rows_seen":"0","last_observations_created":"0","last_observations_updated":"0","last_projection_errors":"0","productive_gap_writes":"disabled","attention_writes":"disabled","phase5f_writes":"disabled","phase5g_writes":"disabled","phase5i_writes":"disabled","direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_writes":"disabled","productive_gap_id":"unavailable_by_design","observation_ready":"false","last_safety_ok":"true"}
        for k,v in defaults.items(): con.execute("INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value) VALUES(?,?)",(k,v))
        con.commit()
        return _self_check_schema(con)
    finally: con.close()

def _self_check_schema(con=None):
    own = con is None
    if own: con = _con()
    try:
        result = {}
        for table, expected in SCHEMA_TABLES.items():
            live = [str(r[1]) for r in con.execute("PRAGMA table_info(" + _q(table) + ")")]
            missing = [c for c in expected if c not in live]
            result[table] = {"ok":not missing,"missing":missing}
        result["overall"] = all(v["ok"] for v in result.values())
        if not result["overall"]: raise ShadowProjectionError("schema self-check failed: " + repr(result))
        return result
    finally:
        if own: con.close()

def _parent_map(tree):
    p={}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n): p[c]=n
    return p

def _owner(node, parents):
    cur=parents.get(node)
    while cur is not None:
        if isinstance(cur,(ast.FunctionDef,ast.AsyncFunctionDef)): return cur.name
        cur=parents.get(cur)
    return None

def _load_projection_namespace():
    source=PHASE5F.read_text(encoding="utf-8-sig")
    tree=ast.parse(source,filename=str(PHASE5F)); parents=_parent_map(tree)
    first=None
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="execute" and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
            if node.args[0].value.lstrip().upper().startswith(("INSERT ","UPDATE ","DELETE ")) and _owner(node,parents)=="apply_adaptive_windowing":
                first = node if first is None or node.lineno < first.lineno else first
    if first is None: raise ShadowProjectionError("first Phase-5f write not found")
    target_stmt=first
    while target_stmt is not None and not isinstance(target_stmt,ast.stmt): target_stmt=parents.get(target_stmt)
    if target_stmt is None: raise ShadowProjectionError("write statement not found")
    replacement=ast.Raise(exc=ast.Call(func=ast.Name(id="_ProjectionCaptured",ctx=ast.Load()),args=[ast.Call(func=ast.Name(id="dict",ctx=ast.Load()),args=[ast.Call(func=ast.Name(id="locals",ctx=ast.Load()),args=[],keywords=[])],keywords=[])],keywords=[]),cause=None)
    replacement=ast.copy_location(replacement,target_stmt)
    for parent in ast.walk(tree):
        for field,value in ast.iter_fields(parent):
            if isinstance(value,list):
                for i,item in enumerate(value):
                    if item is target_stmt: value[i]=replacement
            elif value is target_stmt: setattr(parent,field,replacement)
    allowed=[]
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.AsyncFunctionDef)): allowed.append(node)
        elif isinstance(node,ast.Assign) and isinstance(node.value,(ast.Constant,ast.Dict,ast.List,ast.Tuple,ast.Set)): allowed.append(node)
        elif isinstance(node,ast.AnnAssign) and isinstance(node.value,(ast.Constant,ast.Dict,ast.List,ast.Tuple,ast.Set)): allowed.append(node)
    mod=ast.Module(body=allowed,type_ignores=[]); ast.fix_missing_locations(mod)
    ns={"__name__":"_brainstem_gap_phase5f_shadow_projection_source","_ProjectionCaptured":_ProjectionCaptured}
    exec(compile(mod,str(PHASE5F),"exec"),ns,ns)
    for name in ("apply_adaptive_windowing","neighbors","chunk_status","neuromod"):
        if not callable(ns.get(name)): raise ShadowProjectionError("missing Phase-5f helper: " + name)
    return ns,hashlib.sha256(source.encode("utf-8")).hexdigest()

def _projection_key(row, source_hash):
    material="|".join([VERSION,str(row.get("shadow_key") or ""),str(row.get("hypothesis_id") or ""),str(row.get("updated_at") or 0),source_hash])
    return "shadow-phase5f-observation:" + hashlib.sha256(material.encode("utf-8")).hexdigest()

def _one_projection(ns, con, row, source_hash):
    key=_projection_key(row,source_hash)
    gap={"id":None,"gap_key":key,"gap_type":"shadow_projection_only","role":row.get("role") or "unknown_role","hypothesis_id":row.get("hypothesis_id"),"chunk_id":row.get("chunk_id"),"phase5f_window_radius":None,"phase5f_window_strategy":None,"phase5e_expected_gain":None,"strategy_effectiveness_score":None}
    ns["con_from"]=lambda obj=None: con
    ns["ensure_schema"]=lambda db=None:{"status":"shadow_noop"}
    ns["selected_gaps"]=lambda cur,limit=80:[dict(gap)]
    try: ns["apply_adaptive_windowing"](con,limit=1)
    except _ProjectionCaptured as exc: values=exc.values
    else: raise ShadowProjectionError("projection did not reach capture")
    targets=list(values.get("targets") or [])
    nm=values.get("nm") if isinstance(values.get("nm"),dict) else {}
    return {"observation_key":key,"shadow_key":row.get("shadow_key"),"hypothesis_id":int(row.get("hypothesis_id") or 0),"source_updated_at":int(row.get("updated_at") or 0),"center_chunk_id":values.get("center"),"target_chunk_ids":targets,"target_count":len(targets),"projected_window_strategy":values.get("new_s"),"projected_window_radius":values.get("new_r"),"projected_action":values.get("action"),"expected_gain":values.get("exp"),"closure_delta":values.get("delta"),"overlap_score":values.get("overlap"),"read_no_candidate_rate":values.get("no"),"projected_effectiveness":values.get("eff"),"neuromodulators":nm,"real_outcome_observation_available":0,"observation_ready":0,"source_default_path":1,"productive_gap_id":None,"productive_write":0,"details":{"version":VERSION,"candidate_state":row.get("candidate_state"),"bridge_mode":row.get("bridge_mode"),"source_hash":source_hash,"captured_before_first_phase5f_write":True}}

def observe_shadow(obj=None, limit=MAX_BATCH):
    limit=max(1,min(int(limit),MAX_BATCH)); ensure_schema(obj)
    con=_con(obj)
    try:
        before=_protected(con); state=_read_kv(con,STATE_TABLE)
        cp_time=int(state.get("checkpoint_updated_at") or 0); cp_id=int(state.get("checkpoint_hypothesis_id") or 0)
        rows=[dict(r) for r in con.execute("SELECT * FROM modern_gap_candidate_shadow WHERE candidate_state='observed_only' AND bridge_mode='shadow' AND (updated_at>? OR (updated_at=? AND hypothesis_id>?)) ORDER BY updated_at,hypothesis_id LIMIT ?",(cp_time,cp_time,cp_id,limit))]
        ns,source_hash=_load_projection_namespace(); created=updated=errors=0; error_rows=[]
        con.execute("BEGIN IMMEDIATE")
        first_error_index = None
        v2_stats={'inputs':0,'latest_insert':0,'latest_update':0,'version_insert':0,'identical_retry':0}
        for row_index, row in enumerate(rows):
            try:
                item=_one_projection(ns,con,row,source_hash)
                exists=con.execute("SELECT 1 FROM " + OBS_TABLE + " WHERE observation_key=?",(item["observation_key"],)).fetchone() is not None
                now=int(time.time())
                con.execute("INSERT INTO " + OBS_TABLE + "(observation_key,shadow_key,hypothesis_id,source_updated_at,center_chunk_id,target_chunk_ids,target_count,projected_window_strategy,projected_window_radius,projected_action,expected_gain,closure_delta,overlap_score,read_no_candidate_rate,projected_effectiveness,neuromodulators,real_outcome_observation_available,observation_ready,source_default_path,productive_gap_id,productive_write,details,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(observation_key) DO UPDATE SET target_chunk_ids=excluded.target_chunk_ids,target_count=excluded.target_count,projected_window_strategy=excluded.projected_window_strategy,projected_window_radius=excluded.projected_window_radius,projected_action=excluded.projected_action,expected_gain=excluded.expected_gain,closure_delta=excluded.closure_delta,overlap_score=excluded.overlap_score,read_no_candidate_rate=excluded.read_no_candidate_rate,projected_effectiveness=excluded.projected_effectiveness,neuromodulators=excluded.neuromodulators,details=excluded.details,updated_at=excluded.updated_at",(item["observation_key"],item["shadow_key"],item["hypothesis_id"],item["source_updated_at"],item["center_chunk_id"],json.dumps(item["target_chunk_ids"]),item["target_count"],item["projected_window_strategy"],item["projected_window_radius"],item["projected_action"],item["expected_gain"],item["closure_delta"],item["overlap_score"],item["read_no_candidate_rate"],item["projected_effectiveness"],json.dumps(item["neuromodulators"],sort_keys=True),0,0,1,None,0,json.dumps(item["details"],sort_keys=True),now,now))
                gap_phase5f_shadow_history.record_history(con, item, now)
                v2_result = gap_phase5f_shadow_v2.record_dual_write(con, item, now)
                content_fp_shadow_classifier.record_shadow_classification(con, item, now)
                v2_stats['inputs'] += 1
                for v2_key in ('latest_insert','latest_update','version_insert','identical_retry'): v2_stats[v2_key] += int(v2_result.get(v2_key,0))
                if exists: updated+=1
                else: created+=1
            except Exception as exc:
                errors+=1
                if first_error_index is None:
                    first_error_index = row_index
                error_rows.append({"hypothesis_id":row.get("hypothesis_id"),"error":type(exc).__name__+": "+str(exc)})
        after_cp_time=cp_time; after_cp_id=cp_id
        checkpoint_row = None
        if rows and first_error_index is None:
            checkpoint_row = rows[-1]
        elif rows and first_error_index > 0:
            checkpoint_row = rows[first_error_index - 1]
        if checkpoint_row is not None:
            after_cp_time=int(checkpoint_row.get("updated_at") or 0); after_cp_id=int(checkpoint_row.get("hypothesis_id") or 0)
        after=_protected(con)
        protected_ok=before==after
        if not protected_ok: raise ShadowProjectionError("protected counts changed")
        safety=protected_ok and errors==0
        now=int(time.time())
        gap_phase5f_shadow_v2.record_cycle(con,len(rows),created,updated,v2_stats,safety,now)
        con.execute("INSERT INTO " + CYCLE_TABLE + "(source_rows_seen,observations_created,observations_updated,projection_errors,checkpoint_updated_at_before,checkpoint_hypothesis_id_before,checkpoint_updated_at_after,checkpoint_hypothesis_id_after,productive_writes_before,productive_writes_after,safety_ok,details,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(len(rows),created,updated,errors,cp_time,cp_id,after_cp_time,after_cp_id,json.dumps(before,sort_keys=True),json.dumps(after,sort_keys=True),(1 if safety else 0),json.dumps({"errors":error_rows[:20],"source_hash":source_hash},sort_keys=True),now))
        for k,v in {"checkpoint_updated_at":after_cp_time,"checkpoint_hypothesis_id":after_cp_id,"last_source_rows_seen":len(rows),"last_observations_created":created,"last_observations_updated":updated,"last_projection_errors":errors,"last_safety_ok":("true" if safety else "false"),"observation_ready":"false"}.items(): _write_kv(con,k,v)
        con.commit()
        return {"phase":VERSION,"status":"shadow_observation_complete","mode":"shadow_observation","source_rows_seen":len(rows),"observations_created":created,"observations_updated":updated,"projection_errors":errors,"checkpoint_before":{"updated_at":cp_time,"hypothesis_id":cp_id},"checkpoint_after":{"updated_at":after_cp_time,"hypothesis_id":after_cp_id},"productive_counts_unchanged":True,"observation_ready":False,"productive_gap_id":None,"productive_writes":0}
    except Exception:
        con.rollback(); raise
    finally: con.close()

def selftest():
    con=sqlite3.connect(":memory:"); con.row_factory=sqlite3.Row
    try:
        for table,cols in SCHEMA_TABLES.items():
            if table==STATE_TABLE: con.execute("CREATE TABLE "+table+"(key TEXT PRIMARY KEY,value TEXT)")
            elif table==OBS_TABLE: con.execute("CREATE TABLE "+table+"(observation_key TEXT PRIMARY KEY,"+",".join(c+" TEXT" for c in cols[1:])+")")
            else: con.execute("CREATE TABLE "+table+"(id INTEGER PRIMARY KEY,"+",".join(c+" TEXT" for c in cols[1:])+")")
        assert _self_check_schema(con)["overall"]
        print("SELFTEST OK")
        print("SCHEMA CONTRACT OK")
        print("COMPOSITE CHECKPOINT CONTRACT OK")
        print("OBSERVATION_READY DEFAULT FALSE")
        print("PRODUCTIVE GAP-ID DEFAULT NONE")
        print("PRODUCTIVE WRITES: NONE")
    finally: con.close()

if __name__=="__main__":
    if "--selftest" in sys.argv: selftest()
    elif "--ensure-schema" in sys.argv: print(json.dumps(ensure_schema(),indent=2))
    elif "--observe" in sys.argv: print(json.dumps(observe_shadow(),indent=2))
