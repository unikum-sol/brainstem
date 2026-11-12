# -*- coding: utf-8 -*-
"""Canonical six-core dynamics and the single sleep/wake switch.

The switch is the only place that decides between wake and sleep. It works
like the hypothalamic flip-flop: homeostatic sleep pressure (adenosine,
Process S from Phase 7a) is compared against an upper threshold for sleep
onset and a lower threshold for waking. The gap between the two thresholds is
the hysteresis that makes transitions rare and complete. The arousal side
(histamine, orexin, noradrenaline, acetylcholine, cortisol) and the
GABAergic sleep side shift both thresholds together, the way the circadian
process shifts them in the two-process model: strong arousal delays sleep
onset and ends sleep earlier, strong inhibition does the opposite. Every
other module reads the resulting state from cooperative_sleep_wake_state.

Updates only neuromodulator and sleep/wake state. No facts, relations,
questions, attention, gap, experiment, graduation, or promotion writes.

Literatur: Daan, Beersma & Borbely 1984; Saper, Chou & Scammell 2001;
Saper, Scammell & Lu 2005; Skeldon, Dijk & Derks 2014
"""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path

PHASE="cooperative_core_neuromodulator_sleep_authority"
VERSION="v2_single_switch"
CORE=("dopamine","serotonin","glutamate","gaba","noradrenaline","acetylcholine")
SCHEMA_TABLES={
 "cooperative_sleep_wake_state":[("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
 "cooperative_sleep_wake_cycles":[
  ("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
  ("state","TEXT"),("previous_state","TEXT"),("transitioned","INTEGER"),("reason","TEXT"),
  ("sleep_pressure","REAL"),("upper_threshold","REAL"),("lower_threshold","REAL"),
  ("threshold_shift","REAL"),("wake_drive","REAL"),("sleep_drive","REAL"),
  ("core_before_json","TEXT"),("core_target_json","TEXT")],
 "cooperative_core_target_state":[("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
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
SWITCH_PARAMS={"upper_threshold_base":0.67,"lower_threshold_base":0.17,"threshold_shift_gain":0.1,"upper_threshold_ceiling":0.85,"lower_threshold_floor":0.05}
OBSOLETE_SWITCH_KEYS=("sleep_score","enter_threshold","exit_threshold","min_dwell_cycles","adenosine_pressure","arousal_release","inhibitory_readiness","consolidation_readiness","stress_block")
def _switch(con,pressure,wake_drive,sleep_drive):
 st=_read_kv(con,"cooperative_sleep_wake_state")
 for k,v in SWITCH_PARAMS.items():
  if k not in st:_set_kv(con,"cooperative_sleep_wake_state",k,v);st[k]=v
 con.executemany("DELETE FROM cooperative_sleep_wake_state WHERE key=?",[(k,) for k in OBSOLETE_SWITCH_KEYS])
 gain=_clamp(st["threshold_shift_gain"],0.0,0.3)
 shift=max(-gain,min(gain,gain*(wake_drive-sleep_drive)))
 upper=min(_clamp(st["upper_threshold_ceiling"]),_clamp(st["upper_threshold_base"])+shift)
 lower=max(_clamp(st["lower_threshold_floor"]),_clamp(st["lower_threshold_base"])+shift)
 previous="sleep" if str(st.get("state","wake")).lower()=="sleep" else "wake"
 cycle=_to_int(st.get("cycle_count"),0)+1;entered=_to_int(st.get("state_entered_cycle"),cycle)
 if st.get("switch_version")!=VERSION:entered=cycle;_set_kv(con,"cooperative_sleep_wake_state","switch_version",VERSION)
 state=previous;reason="hold"
 if previous=="wake" and pressure>=upper:state="sleep";reason="sleep_pressure_reached_upper_threshold"
 elif previous=="sleep" and pressure<=lower:state="wake";reason="sleep_pressure_dissipated_to_lower_threshold"
 transitioned=state!=previous
 values={"state":state,"previous_state":previous,"cycle_count":cycle,"transition_reason":reason,
  "sleep_pressure":round(pressure,6),"upper_threshold":round(upper,6),"lower_threshold":round(lower,6),
  "threshold_shift":round(shift,6),"wake_drive":round(wake_drive,6),"sleep_drive":round(sleep_drive,6),
  "pressure_position":round(_clamp((pressure-lower)/max(1e-6,upper-lower)),6)}
 if transitioned:
  episode=cycle-entered
  values["last_"+previous+"_episode_cycles"]=episode
  values["total_transitions"]=_to_int(st.get("total_transitions"),0)+1
  entered=cycle
 values["state_entered_cycle"]=entered;values["dwell_cycles"]=cycle-entered
 for k,v in values.items():_set_kv(con,"cooperative_sleep_wake_state",k,v)
 return values,transitioned
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
 cort_state=_read_kv(con,"cortisol_state")
 ei_state=_read_kv(con,"phase7c_state")
 before={k:_value(core,k,{"dopamine":.5,"serotonin":.6,"glutamate":.4,"gaba":.4,"noradrenaline":.3,"acetylcholine":.5}[k]) for k in CORE}
 pressure=_value(ade_state,"adenosine_level",0.0);hist=_value(his_state,"histamine_level",core.get("histamine",.5));orexin=_value(orx_state,"orexin_level",core.get("orexin",.5));cort=_value(cort_state,"cortisol_level",core.get("cortisol",.2))
 exploration=_value(meta,"last_exploration_bias",.5);consolidation=_value(meta,"last_consolidation_bias",.5);inhibition=_value(meta,"last_inhibition_bias",.4);revision=_value(meta,"last_revision_bias",.5);persistent=_value(meta,"last_persistent_gap_pressure",.5);outcome=_value(meta,"last_avg_outcome_score",.0)
 ei_glu=_value(ei_state,"glutamate_state",before["glutamate"]);ei_gaba=_value(ei_state,"gaba_state",before["gaba"])
 wake_drive=_clamp(.28*hist+.25*orexin+.20*before["noradrenaline"]+.12*before["acetylcholine"]+.15*cort)
 sleep_drive=_clamp(.55*ei_gaba+.25*inhibition+.20*(1.0-ei_glu))
 target={
  "dopamine":_clamp(.20+.34*outcome+.18*exploration+.16*(1.0-persistent)+.12*(1.0-cort)),
  "serotonin":_clamp(.22+.38*consolidation+.20*(1.0-cort)+.12*outcome+.08*sleep_drive),
  "noradrenaline":_clamp(.12+.30*persistent+.25*hist+.18*orexin+.15*cort),
  "acetylcholine":_clamp(.18+.33*revision+.22*hist+.17*orexin+.10*exploration),
 }
 for k,v in target.items():_set_kv(con,"cooperative_core_target_state",k,round(v,6))
 sw,transitioned=_switch(con,pressure,wake_drive,sleep_drive)
 con.execute("INSERT INTO cooperative_sleep_wake_cycles(created_at,cycle_index,state,previous_state,transitioned,reason,sleep_pressure,upper_threshold,lower_threshold,threshold_shift,wake_drive,sleep_drive,core_before_json,core_target_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(_now(),sw["cycle_count"],sw["state"],sw["previous_state"],1 if transitioned else 0,sw["transition_reason"],pressure,sw["upper_threshold"],sw["lower_threshold"],sw["threshold_shift"],wake_drive,sleep_drive,json.dumps(before,sort_keys=True),json.dumps(target,sort_keys=True)))
 con.commit()
 return {"phase":PHASE,"status":"complete","cycle_index":sw["cycle_count"],"core_before":before,"tonic_target":target,"sleep_state":sw["state"],"sleep_pressure":sw["sleep_pressure"],"upper_threshold":sw["upper_threshold"],"lower_threshold":sw["lower_threshold"],"transitioned":transitioned,"transition_reason":sw["transition_reason"],"productive_writes":{"facts":0,"relations":0,"questions":0}}
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
