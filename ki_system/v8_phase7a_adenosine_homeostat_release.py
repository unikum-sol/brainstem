# -*- coding: utf-8 -*-
"""BrainStem Phase 7a - Adenosine homeostat with gated sleep discharge.

This release replaces the former one-step threshold oscillator with a persistent
wake/sleep state. Wake cycles accumulate adenosine. Sleep cycles inhibit normal
buildup, discharge adenosine over multiple cycles, and exit only after the low
threshold and minimum dwell contract are satisfied.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from pathlib import Path

try:
    from ki_system import v8_guarded_core_adapters_canonical_sleep_wake_shadow_release as __gca_shadow
except Exception:
    __gca_shadow = None

PHASE = "phase7a_adenosine_homeostat_release"
PHASE_VERSION = "phase7a_v2_gated_sleep_discharge"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"

SCHEMA_TABLES = {
    "phase7a_state": [("key", "TEXT PRIMARY KEY"), ("value", "TEXT"), ("updated_at", "INTEGER")],
    "phase7a_adenosine_state": [("key", "TEXT PRIMARY KEY"), ("value", "TEXT"), ("updated_at", "INTEGER")],
    "phase7a_adenosine_events": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"), ("created_at", "INTEGER"),
        ("cycle_index", "INTEGER"), ("event_type", "TEXT"), ("adenosine_level", "REAL"),
        ("sleep_pressure", "REAL"), ("downscale_factor", "REAL"), ("action_taken", "TEXT"),
        ("targets_affected", "TEXT"), ("reason", "TEXT"), ("driver_botenstoff", "TEXT"),
        ("driver_botenstoff_value", "REAL")],
    "phase7a_sleep_pressure_history": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"), ("created_at", "INTEGER"),
        ("cycle_index", "INTEGER"), ("adenosine_level", "REAL"),
        ("wake_activity_since", "REAL"), ("downscale_applied", "REAL"),
        ("effectiveness_before", "REAL"), ("effectiveness_after", "REAL"),
        ("recovery_delta", "REAL"), ("anchor_stability_before", "REAL"),
        ("anchor_stability_after", "REAL"), ("notes", "TEXT")],
}
SCHEMA_INDEXES = [
    ("idx_phase7a_events_cyc", "phase7a_adenosine_events", "cycle_index"),
    ("idx_phase7a_history_cyc", "phase7a_sleep_pressure_history", "cycle_index"),
]
ADENOSINE_PARAMS = {
    "adenosine_level": 0.0, "buildup_rate": 0.08, "activity_scale": 0.5,
    "decay_after_sleep": 0.85, "threshold_high": 0.65, "threshold_low": 0.15,
    "downscale_min": 0.05, "downscale_max": 0.25,
    "wake_activity_last": 0.0, "cycles_since_last_downscale": 0,
    "total_wake_cycles": 0, "total_downscales": 0,
    "last_adenosine_level": 0.0, "last_sleep_pressure": 0.0,
    "homeostat_mode": "wake", "mode_entered_cycle": 0, "sleep_dwell_cycles": 0,
    "minimum_sleep_cycles": 3, "total_sleep_cycles": 0,
    "last_transition_cycle": 0, "transition_count": 0,
    "productive_state_machine": "gated_sleep_discharge_v2",
}
BIAS_KEYS = ("last_plasticity_level", "last_exploration_bias", "last_consolidation_bias", "last_inhibition_bias", "last_revision_bias")
BIAS_MIDS = {"last_plasticity_level":0.5,"last_exploration_bias":0.5,"last_consolidation_bias":0.5,"last_inhibition_bias":0.35,"last_revision_bias":0.5}

class SchemaCheckError(RuntimeError): pass

def _now(): return int(time.time())
def _clamp(x, lo=0.0, hi=1.0):
    try: x=float(x)
    except Exception: x=0.0
    return lo if x<lo else hi if x>hi else x
def _to_float(x,d=0.0):
    try: return float(x)
    except Exception: return d
def _to_int(x,d=0):
    try: return int(float(x))
    except Exception: return d
def _table_exists(con,t): return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _columns(con,t): return [r[1] for r in con.execute("PRAGMA table_info("+t+")")] if _table_exists(con,t) else []
def resolve_db(obj=None):
    if isinstance(obj,sqlite3.Connection): obj.row_factory=sqlite3.Row; return obj
    if obj is not None:
        for a in ("db","connection","conn"):
            v=getattr(obj,a,None)
            if isinstance(v,sqlite3.Connection): v.row_factory=sqlite3.Row; return v
        for a in ("memory","mem"):
            v=getattr(obj,a,None)
            if v is not None and v is not obj:
                try: return resolve_db(v)
                except Exception: pass
    path="ki_memory.sqlite3"
    if not os.path.exists(path):
        p=Path(__file__).resolve().parent.parent/"ki_memory.sqlite3"
        if p.exists(): path=str(p)
    con=sqlite3.connect(path,timeout=30); con.row_factory=sqlite3.Row; return con

def ensure_schema(con):
    for t,defs in SCHEMA_TABLES.items():
        if not _table_exists(con,t): con.execute("CREATE TABLE "+t+" ("+", ".join(n+" "+s for n,s in defs)+")")
        else:
            live=set(_columns(con,t))
            for n,s in defs:
                if n not in live and "PRIMARY KEY" not in s.upper() and "AUTOINCREMENT" not in s.upper(): con.execute("ALTER TABLE "+t+" ADD COLUMN "+n+" "+s)
    for i,t,c in SCHEMA_INDEXES: con.execute("CREATE INDEX IF NOT EXISTS "+i+" ON "+t+"("+c+")")
    con.commit(); return _self_check_schema(con)
def _self_check_schema(con):
    missing=[]
    for t,defs in SCHEMA_TABLES.items():
        live=set(_columns(con,t)); missing += [t+"."+n for n,_ in defs if n not in live]
    if missing: raise SchemaCheckError("missing schema: "+repr(missing))
    return {"overall":True,"missing":[]}
def _kv_set(con,t,k,v):
    con.execute("INSERT INTO "+t+"(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,("true" if v else "false") if isinstance(v,bool) else str(v),_now()))
def _read_kv(con,table):
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())
def _get(con,k,d=0.0): return _read_kv(con,"phase7a_adenosine_state").get(k,d)
def _set(con,k,v): _kv_set(con,"phase7a_adenosine_state",k,v)
def initialize_adenosine_parameters(con):
    ensure_schema(con); inserted=[]
    for k,v in ADENOSINE_PARAMS.items():
        if con.execute("SELECT 1 FROM phase7a_adenosine_state WHERE key=?",(k,)).fetchone() is None: _set(con,k,v); inserted.append(k)
    mode=str(_get(con,"homeostat_mode","wake")).lower()
    if mode not in ("wake","sleep"): _set(con,"homeostat_mode","wake")
    con.commit(); return {"inserted":inserted,"total":len(ADENOSINE_PARAMS)}
def _count(con,t):
    try: return int(con.execute("SELECT COUNT(*) FROM "+t).fetchone()[0]) if _table_exists(con,t) else None
    except Exception: return None
def _measure_wake_activity(con):
    st=_read_kv(con,"phase7a_state"); vals=[]
    for table,key in (("context_hypotheses","last_ch_count"),("phase5g_experiment_outcomes","last_outcome_count"),("phase6a_sleep_replay_cycles","last_cycle_count")):
        cur=_count(con,table); last=_to_int(st.get(key),0); delta=max(0,(cur or 0)-last) if cur is not None else 0
        vals.append(delta); _kv_set(con,"phase7a_state",key,cur if cur is not None else last)
    con.commit(); dch,dout,dcyc=vals
    raw=0.5*math.log1p(dch)/math.log1p(1000)+0.3*math.log1p(dout)/math.log1p(2000)+0.2*math.log1p(dcyc)/math.log1p(50)
    return {"wake_activity":_clamp(raw),"d_ch":dch,"d_out":dout,"d_cyc":dcyc,"reason":"measured"}
def _neuromod(con):
    st=_read_kv(con,"phase6a_neuromodulated_sleep_state") if _table_exists(con,"phase6a_neuromodulated_sleep_state") else {}
    return {k:_clamp(_to_float(st.get(k),d)) for k,d in (("acetylcholine",0.5),("glutamate",0.5),("serotonin",0.5))}
def _log(con,cyc,typ,level,pressure,factor,action,targets,reason,driver,val):
    con.execute("INSERT INTO phase7a_adenosine_events(created_at,cycle_index,event_type,adenosine_level,sleep_pressure,downscale_factor,action_taken,targets_affected,reason,driver_botenstoff,driver_botenstoff_value) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(_now(),int(cyc),typ,float(level),float(pressure),float(factor),action,json.dumps(targets,sort_keys=True) if not isinstance(targets,str) else targets,reason,driver,float(val)))
def _targets(con):
    if not _table_exists(con,"phase6a_meta_plasticity_state"): return []
    st=_read_kv(con,"phase6a_meta_plasticity_state"); out=[]
    for k in BIAS_KEYS:
        if k in st:
            v=_to_float(st[k],None)
            if v is not None and (v<=0.05 or v>=0.95): out.append((k,v,"min" if v<=0.05 else "max"))
    return out
def _enter_sleep(con,level,neuromod,cyc):
    high=_to_float(_get(con,"threshold_high",0.65),0.65); dmin=_to_float(_get(con,"downscale_min",0.05),0.05); dmax=_to_float(_get(con,"downscale_max",0.25),0.25)
    glu=neuromod["glutamate"]; sero=neuromod["serotonin"]
    pull=dmin+max(0.0,level-high)*(dmax-dmin)/max(1e-6,1-high); pull=_clamp(pull*(0.7+0.6*glu)*(1-0.3*sero),0.02,0.4)
    affected=[]
    for k,v,side in _targets(con):
        nv=_clamp(v+(BIAS_MIDS[k]-v)*pull)
        for table in ("phase6a_meta_plasticity_state","phase6a_neuromodulated_sleep_state","phase6c_target_bias_state"):
            if _table_exists(con,table): _kv_set(con,table,k,round(nv,6))
        affected.append({"key":k,"pre":v,"post":nv,"side":side})
    _set(con,"homeostat_mode","sleep"); _set(con,"mode_entered_cycle",cyc); _set(con,"sleep_dwell_cycles",0); _set(con,"last_transition_cycle",cyc); _set(con,"transition_count",_to_int(_get(con,"transition_count",0))+1)
    typ="sleep_downscale" if affected else "idle_decay"
    _log(con,cyc,typ,level,level,pull if affected else 0.0,"enter_gated_sleep",[a["key"] for a in affected],"threshold_high_reached","glutamate",glu)
    if affected: _set(con,"total_downscales",_to_int(_get(con,"total_downscales",0))+1)
    return {"triggered":True,"action":"enter_sleep","pull":pull,"new_adenosine":level,"adenosine_after":level,"targets_affected":affected}
def _sleep_cycle(con,old,neuromod,cyc):
    retain=_clamp(_to_float(_get(con,"decay_after_sleep",0.85),0.85),0.01,0.999); new=_clamp(old*retain)
    dwell=_to_int(_get(con,"sleep_dwell_cycles",0))+1; minimum=max(1,_to_int(_get(con,"minimum_sleep_cycles",3),3)); low=_clamp(_to_float(_get(con,"threshold_low",0.15),0.15))
    _set(con,"adenosine_level",round(new,6)); _set(con,"sleep_dwell_cycles",dwell); _set(con,"total_sleep_cycles",_to_int(_get(con,"total_sleep_cycles",0))+1)
    exit_now=dwell>=minimum and new<=low
    if exit_now:
        _set(con,"homeostat_mode","wake"); _set(con,"last_transition_cycle",cyc); _set(con,"transition_count",_to_int(_get(con,"transition_count",0))+1); _set(con,"cycles_since_last_downscale",0)
    _log(con,cyc,"sleep_discharge",new,old,1-retain,"exit_to_wake" if exit_now else "continue_sleep",[],"low_threshold_and_dwell_satisfied" if exit_now else "gated_multicycle_discharge","acetylcholine",neuromod["acetylcholine"])
    return {"triggered":True,"action":"sleep_discharge","new_adenosine":new,"adenosine_after":new,"targets_affected":[],"sleep_dwell_cycles":dwell,"transitioned_to_wake":exit_now}
def run_phase7a_cycle(db_or_obj=None,cycle_index=None):
    con=resolve_db(db_or_obj); ensure_schema(con); initialize_adenosine_parameters(con)
    if cycle_index is None: cycle_index=_to_int(_read_kv(con,"phase7a_state").get("cycle_count"),0)+1
    neu=_neuromod(con); wake=_measure_wake_activity(con); old=_clamp(_to_float(_get(con,"adenosine_level",0.0),0.0)); mode=str(_get(con,"homeostat_mode","wake")).lower()
    if mode=="sleep":
        accum={"old":old,"new":old,"rate":0.0,"sleep_pressure":old,"inhibited_by_sleep_gate":True}; down=_sleep_cycle(con,old,neu,cycle_index)
    else:
        br=max(0.0,_to_float(_get(con,"buildup_rate",0.08),0.08)); scale=max(0.0,_to_float(_get(con,"activity_scale",0.5),0.5)); rate=br*(1+scale*wake["wake_activity"])*(1.2-0.4*neu["acetylcholine"]); new=_clamp(old+rate)
        _set(con,"adenosine_level",round(new,6)); _set(con,"wake_activity_last",round(wake["wake_activity"],6)); _set(con,"last_adenosine_level",round(old,6)); _set(con,"last_sleep_pressure",round(new,6)); _set(con,"total_wake_cycles",_to_int(_get(con,"total_wake_cycles",0))+1)
        _log(con,cycle_index,"buildup",new,new,0.0,"accumulate",[],"gated_wake_buildup","acetylcholine",neu["acetylcholine"])
        accum={"old":old,"new":new,"rate":rate,"sleep_pressure":new,"inhibited_by_sleep_gate":False}
        down=_enter_sleep(con,new,neu,cycle_index) if new>=_to_float(_get(con,"threshold_high",0.65),0.65) else {"triggered":False,"action":"wake_hold","new_adenosine":new,"adenosine_after":new,"targets_affected":[]}
    if __gca_shadow is not None:
        try: __gca_shadow.observe_sleep_wake_shadow(con,{"cycle_index":cycle_index,"accum":accum,"downscale_result":down})
        except Exception: pass
    for k,v in (("cycle_count",cycle_index),("last_cycle_at",_now()),("phase",PHASE),("phase_version",PHASE_VERSION),("learning_mode",LEARNING_MODE),("no_word_blacklists",True),("direct_fact_writes","disabled"),("direct_relation_writes","disabled"),("fact_promotion","disabled"),("adenosine_homeostat",True)):_kv_set(con,"phase7a_state",k,v)
    con.commit()
    return {"phase":PHASE,"phase_version":PHASE_VERSION,"cycle_index":cycle_index,"status":"ok","homeostat_mode":str(_get(con,"homeostat_mode","wake")),"wake_activity":wake,"adenosine_accumulation":accum,"downscale":down,"safety":{"direct_fact_writes":"disabled","direct_relation_writes":"disabled","fact_promotion":"disabled","no_word_blacklists":True}}
def managed_cycle(self,progress=None):
    base=None; dmod=None
    for name in ("v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release","v8_phase6c_bias_persistence_and_self_regulating_meta_release","v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release","v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release"):
        try:
            m=__import__("ki_system."+name,fromlist=["managed_cycle"])
            if hasattr(m,"managed_cycle") and m.managed_cycle is not managed_cycle: base=m.managed_cycle(self,progress); dmod=name; break
        except Exception: continue
    return {"phase":PHASE,"downstream_module":dmod,"downstream_result":base,"phase7a_result":run_phase7a_cycle(self)}
def managed_run(self,cycles=1,progress=None): return {"phase":PHASE,"cycles":max(1,int(cycles or 1)),"results":[managed_cycle(self,progress) for _ in range(max(1,int(cycles or 1)))]}
def autoload(AutonomousLoop):
    AutonomousLoop.cycle=managed_cycle; AutonomousLoop.run=managed_run; AutonomousLoop.phase7a_adenosine_homeostat_release=True; AutonomousLoop.adenosine_homeostat=True
    return AutonomousLoop
