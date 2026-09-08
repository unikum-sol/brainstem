# -*- coding: utf-8 -*-
"""Canonical six-core dynamics and cooperative sleep/wake authority.

Updates only neuromodulator and sleep/wake state. No facts, relations,
questions, attention, gap, experiment, graduation, or promotion writes.
"""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path

PHASE="cooperative_core_neuromodulator_sleep_authority"
VERSION="v1"
CORE=("dopamine","serotonin","glutamate","gaba","noradrenaline","acetylcholine")
SCHEMA_TABLES={
 "cooperative_sleep_wake_state":[("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
 "cooperative_sleep_wake_cycles":[
  ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
  ("state","TEXT"),("previous_state","TEXT"),("transitioned","INTEGER"),("reason","TEXT"),
  ("sleep_score","REAL"),("adenosine_pressure","REAL"),("arousal_release","REAL"),
  ("inhibitory_readiness","REAL"),("consolidation_readiness","REAL"),("stress_block","REAL"),
  ("core_before_json","TEXT"),("core_target_json","TEXT"),("core_after_json","TEXT")],
}

def _now():return int(time.time())
def _clamp(v,lo=0.0,hi=1.0):
 try:v=float(v)
 except Exception:v=0.0
 return max(lo,min(hi,v))
def _to_int(v,d=0):
 try:return int(float(v))
 except Exception:return d
def _table_exists(con,t):return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _columns(con,t):return [r[1] for r in con.execute("PRAGMA table_info("+t+")").fetchall()]
def _read_kv(con,table):
 if not _table_exists(con,table):return {}
 return dict(con.execute("SELECT key,value FROM "+table).fetchall())
def _set_kv(con,table,key,value):
 con.execute("INSERT INTO "+table+"(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(key,str(value),_now()))
def resolve_db(obj=None):
 if isinstance(obj,sqlite3.Connection):return obj
 for candidate in (obj,getattr(obj,"memory",None),getattr(obj,"mem",None)):
  if candidate is None:continue
  for attr in ("db","con","conn","connection"):
   con=getattr(candidate,attr,None)
   if isinstance(con,sqlite3.Connection):return con
 return sqlite3.connect(str(Path("ki_memory.sqlite3")),timeout=30)
def ensure_schema(con):
 for table,cols in SCHEMA_TABLES.items():
  if not _table_exists(con,table):con.execute("CREATE TABLE "+table+" ("+",".join(n+" "+s for n,s in cols)+")")
  else:
   present=set(_columns(con,table))
   for name,spec in cols:
    if name not in present and "PRIMARY KEY" not in spec.upper() and "AUTOINCREMENT" not in spec.upper():con.execute("ALTER TABLE "+table+" ADD COLUMN "+name+" "+spec)
 con.execute("CREATE INDEX IF NOT EXISTS idx_coop_sleep_cycles_cycle ON cooperative_sleep_wake_cycles(cycle_index)")
 con.commit()
def _self_check_schema(con):
 missing=[]
 for table,cols in SCHEMA_TABLES.items():
  present=set(_columns(con,table))
  missing.extend(table+"."+name for name,_ in cols if name not in present)
 return missing
def _value(state,key,default):return _clamp(state.get(key,default))
def run_cycle(db_or_obj=None):
 con=resolve_db(db_or_obj);ensure_schema(con);missing=_self_check_schema(con)
 if missing:return {"phase":PHASE,"status":"schema_check_failed","missing_columns":missing}
 if not _table_exists(con,"phase6a_neuromodulated_sleep_state"):
  return {"phase":PHASE,"status":"core_state_missing"}
 core=_read_kv(con,"phase6a_neuromodulated_sleep_state")
 meta=_read_kv(con,"phase6a_meta_plasticity_state")
 ade_state=_read_kv(con,"phase7a_adenosine_state")
 his_state=_read_kv(con,"phase7e_histamine_state")
 orx_state=_read_kv(con,"phase7f_orexin_state")
 bdnf_state=_read_kv(con,"phase7g_bdnf_state")
 cort_state=_read_kv(con,"cortisol_state")
 ei_state=_read_kv(con,"phase7c_state")
 before={k:_value(core,k,{"dopamine":.5,"serotonin":.6,"glutamate":.4,"gaba":.4,"noradrenaline":.3,"acetylcholine":.5}[k]) for k in CORE}
 pressure=_value(ade_state,"adenosine_level",0.0);hist=_value(his_state,"histamine_level",core.get("histamine",.5));orexin=_value(orx_state,"orexin_level",core.get("orexin",.5));cort=_value(cort_state,"cortisol_level",core.get("cortisol",.2));bdnf=_value(bdnf_state,"bdnf_level",core.get("bdnf",.5))
 exploration=_value(meta,"last_exploration_bias",.5);consolidation=_value(meta,"last_consolidation_bias",.5);inhibition=_value(meta,"last_inhibition_bias",.4);revision=_value(meta,"last_revision_bias",.5);persistent=_value(meta,"last_persistent_gap_pressure",.5);outcome=_value(meta,"last_avg_outcome_score",.0)
 ei_glu=_value(ei_state,"glutamate_state",before["glutamate"]);ei_gaba=_value(ei_state,"gaba_state",before["gaba"])
 arousal=_clamp(.28*hist+.25*orexin+.20*before["noradrenaline"]+.12*before["acetylcholine"]+.15*cort)
 inhibitory=_clamp(.55*ei_gaba+.25*inhibition+.20*(1.0-ei_glu))
 consolid=_clamp(.45*consolidation+.30*bdnf+.25*before["serotonin"])
 arousal_release=1.0-arousal;stress_block=cort
 sleep_score=_clamp(.35*pressure+.25*arousal_release+.20*inhibitory+.12*consolid+.08*(1.0-stress_block))
 target={
  "dopamine":_clamp(.20+.34*outcome+.18*exploration+.16*(1.0-persistent)+.12*(1.0-cort)),
  "serotonin":_clamp(.22+.38*consolidation+.20*(1.0-cort)+.12*outcome+.08*inhibitory),
  "glutamate":_clamp(.18+.40*exploration+.18*orexin+.16*persistent-.18*sleep_score),
  "gaba":_clamp(.16+.39*inhibition+.23*sleep_score+.14*cort+.08*(1.0-exploration)),
  "noradrenaline":_clamp(.12+.30*persistent+.25*hist+.18*orexin+.15*cort),
  "acetylcholine":_clamp(.18+.33*revision+.22*hist+.17*orexin+.10*exploration),
 }
 alpha=.18
 after={k:round(_clamp(before[k]+alpha*(target[k]-before[k]),.05,.95),6) for k in CORE}
 for k,v in after.items():_set_kv(con,"phase6a_neuromodulated_sleep_state",k,v)
 coop=_read_kv(con,"cooperative_sleep_wake_state");previous=str(coop.get("state","wake"));cycle=_to_int(coop.get("cycle_count"),0)+1;entered=_to_int(coop.get("state_entered_cycle"),cycle)
 enter=_clamp(coop.get("enter_threshold",.62));exitv=_clamp(coop.get("exit_threshold",.42));min_dwell=max(1,_to_int(coop.get("min_dwell_cycles"),3));dwell=max(0,cycle-entered)
 state=previous;reason="hold"
 if previous!="sleep" and sleep_score>=enter and dwell>=min_dwell:state="sleep";reason="cooperative_sleep_entry"
 elif previous=="sleep" and sleep_score<=exitv and dwell>=min_dwell:state="wake";reason="cooperative_wake_entry"
 transitioned=state!=previous
 if transitioned:entered=cycle
 for k,v in {"state":state,"previous_state":previous,"cycle_count":cycle,"state_entered_cycle":entered,"dwell_cycles":max(0,cycle-entered),"transition_reason":reason,"sleep_score":round(sleep_score,6),"adenosine_pressure":round(pressure,6),"arousal_release":round(arousal_release,6),"inhibitory_readiness":round(inhibitory,6),"consolidation_readiness":round(consolid,6),"stress_block":round(stress_block,6),"enter_threshold":enter,"exit_threshold":exitv,"min_dwell_cycles":min_dwell}.items():_set_kv(con,"cooperative_sleep_wake_state",k,v)
 con.execute("INSERT INTO cooperative_sleep_wake_cycles(created_at,cycle_index,state,previous_state,transitioned,reason,sleep_score,adenosine_pressure,arousal_release,inhibitory_readiness,consolidation_readiness,stress_block,core_before_json,core_target_json,core_after_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(_now(),cycle,state,previous,1 if transitioned else 0,reason,sleep_score,pressure,arousal_release,inhibitory,consolid,stress_block,json.dumps(before,sort_keys=True),json.dumps(target,sort_keys=True),json.dumps(after,sort_keys=True)))
 con.commit()
 return {"phase":PHASE,"status":"complete","cycle_index":cycle,"core_before":before,"core_target":target,"core_after":after,"sleep_state":state,"sleep_score":round(sleep_score,6),"transitioned":transitioned,"transition_reason":reason,"productive_writes":{"facts":0,"relations":0,"questions":0}}
def managed_cycle(self,progress=None):
 from ki_system import v8_phase7cort_stability_watch_release as downstream
 result=downstream.managed_cycle(self,progress)
 try:authority=run_cycle(self)
 except Exception as exc:authority={"phase":PHASE,"status":"error","error":type(exc).__name__+":"+str(exc)}
 return {"phase":PHASE,"downstream_result":result,"authority_result":authority}
def managed_run(self,cycles=1,progress=None):
 return {"phase":PHASE,"results":[managed_cycle(self,progress) for _ in range(max(1,int(cycles or 1)))]}
def autoload(AutonomousLoop):
 AutonomousLoop.cycle=managed_cycle;AutonomousLoop.run=managed_run;AutonomousLoop.cooperative_core_neuromodulator_sleep_authority=True
 AutonomousLoop.fact_promotion="disabled";AutonomousLoop.direct_fact_writes="disabled";AutonomousLoop.direct_relation_writes="disabled";AutonomousLoop.no_word_blacklists=True
 return AutonomousLoop
