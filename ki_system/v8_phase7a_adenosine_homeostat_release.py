# -*- coding: utf-8 -*-
"""BrainStem Phase 7a - Adenosine as homeostatic sleep pressure (Process S).

Adenosine rises during wake as a saturating exponential driven by encoding
load and decays exponentially during sleep. The rise is faster while the
system is immature, so the sleep share falls from about two thirds to the
adult share as consolidated knowledge grows. Phase 7a does not decide when the
system sleeps: it reads the single sleep/wake state of the switch in the
cooperative core and only integrates the pressure. At the first sleep cycle it
pulls saturated meta-plasticity biases back toward their mid values
(synaptic renormalization at sleep onset).

Literatur: Borbely 1982; Daan, Beersma & Borbely 1984; Porkka-Heiskanen et al.
1997; Tononi & Cirelli 2006
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from pathlib import Path


PHASE = "phase7a_adenosine_homeostat_release"
PHASE_VERSION = "phase7a_v4_developmental_process_s"
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
    "adenosine_level": 0.0,
    # Process S time constants in cycles. The ratio of wake rise to sleep
    # decay follows the two-process fits (tau_w 18.2 h, tau_s 4.2 h), scaled
    # so that a wake episode at typical load lasts about 60 cycles, well
    # inside the synaptic tag window of Phase 7d.
    # Literatur: Daan, Beersma & Borbely 1984; Skeldon, Dijk & Derks 2014
    "wake_rise_rate": 0.0154, "sleep_decay_rate": 0.0666,
    # Rise scales with encoding load: new traces relative to the system's own
    # running novelty level (synaptic potentiation during wake drives sleep
    # need), and with glutamatergic activity (activity-dependent release).
    # Literatur: Porkka-Heiskanen et al. 1997; Tononi & Cirelli 2006;
    # Huber et al. 2004; Brambilla et al. 2005
    "novelty_reference_hypotheses": 0.0, "novelty_reference_outcomes": 0.0,
    "novelty_reference_alpha": 0.01, "outcome_load_share": 0.2,
    "glutamate_rise_gain": 0.4,
    # Developmental sleep share: an immature system builds up sleep pressure
    # faster, so it sleeps about two thirds of the time at the start (like a
    # newborn) and moves toward the adult share as consolidated knowledge
    # grows. Only the rise changes with maturation; the decay stays the same.
    # maturity = knowledge / (knowledge + maturity_half_knowledge), knowledge =
    # net number of hypotheses in a stable role (revisions count back down).
    # Literatur: Roffwarg, Muzio & Dement 1966; Jenni, Achermann & Carskadon
    # 2005; Tarokh, Carskadon & Achermann 2012; Feinberg & Campbell 2010
    "developmental_rise_gain": 4.0, "maturity_half_knowledge": 1000.0,
    "developmental_maturity": 0.0, "developmental_rise_factor": 1.0, "consolidated_knowledge": 0,
    # Slow-wave dissipation is deeper with stronger GABAergic inhibition.
    # Literatur: Walsh et al. 2008
    "gaba_decay_gain": 0.4,
    "downscale_min": 0.05, "downscale_max": 0.25,
    "last_seen_state": "wake", "last_encoding_load": 0.0, "last_rate": 0.0,
    "last_new_hypotheses": 0, "last_new_outcomes": 0,
    "total_wake_cycles": 0, "total_sleep_cycles": 0, "total_downscales": 0,
    "last_adenosine_level": 0.0,
}
OBSOLETE_STATE_KEYS = (
    "buildup_rate", "activity_scale", "decay_after_sleep", "threshold_high", "threshold_low",
    "homeostat_mode", "mode_entered_cycle", "sleep_dwell_cycles", "minimum_sleep_cycles",
    "last_transition_cycle", "transition_count", "productive_state_machine", "wake_activity_last",
    "cycles_since_last_downscale", "last_sleep_pressure", "canonical_event_typed_observer_mode",
    "canonical_event_typed_observer_authority",
)
OBSOLETE_COUNTER_KEYS = ("last_ch_count", "last_outcome_count", "last_cycle_count")
SWITCH_TABLE = "cooperative_sleep_wake_state"
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
    con.executemany("DELETE FROM phase7a_adenosine_state WHERE key=?",[(k,) for k in OBSOLETE_STATE_KEYS])
    con.executemany("DELETE FROM phase7a_state WHERE key=?",[(k,) for k in OBSOLETE_COUNTER_KEYS])
    con.commit(); return {"inserted":inserted,"total":len(ADENOSINE_PARAMS)}
def sleep_state(con):
    st=_read_kv(con,SWITCH_TABLE) if _table_exists(con,SWITCH_TABLE) else {}
    return "sleep" if str(st.get("state","wake")).strip().lower()=="sleep" else "wake"
def _max_id(con,t):
    try: return int(con.execute("SELECT COALESCE(MAX(id),0) FROM "+t).fetchone()[0]) if _table_exists(con,t) else None
    except Exception: return None
def _novelty(con,n,ref_key,alpha,update):
    ref=max(0.0,_to_float(_get(con,ref_key,0.0),0.0))
    if ref<=0.0: ref=float(n)
    load=n/(n+ref) if n>0 else 0.0
    if update and n>0: _set(con,ref_key,round((1-alpha)*ref+alpha*n,6))
    elif update and ref>0: _set(con,ref_key,round((1-alpha)*ref,6))
    return load
def _measure_encoding_load(con,update):
    st=_read_kv(con,"phase7a_state"); deltas={}
    for table,key in (("context_hypotheses","last_ch_max_id"),("phase5g_experiment_outcomes","last_outcome_max_id")):
        cur=_max_id(con,table)
        if cur is None: deltas[table]=0; continue
        last=st.get(key); deltas[table]=max(0,cur-_to_int(last,cur)) if last is not None else 0
        _kv_set(con,"phase7a_state",key,cur)
    alpha=_clamp(_to_float(_get(con,"novelty_reference_alpha",0.01),0.01),0.0001,1.0)
    share=_clamp(_to_float(_get(con,"outcome_load_share",0.2),0.2))
    l_h=_novelty(con,deltas["context_hypotheses"],"novelty_reference_hypotheses",alpha,update)
    l_o=_novelty(con,deltas["phase5g_experiment_outcomes"],"novelty_reference_outcomes",alpha,update)
    return {"encoding_load":_clamp((1-share)*l_h+share*l_o),"new_hypotheses":deltas["context_hypotheses"],"new_outcomes":deltas["phase5g_experiment_outcomes"],"hypothesis_load":l_h,"outcome_load":l_o}
def _maturity(con):
    knowledge=0
    if _table_exists(con,"context_hypotheses"):
        try: knowledge=int(con.execute("SELECT COUNT(*) FROM context_hypotheses WHERE role>='stable_' AND role<'stable`'").fetchone()[0])
        except Exception: knowledge=0
    half=max(1.0,_to_float(_get(con,"maturity_half_knowledge",1000.0),1000.0))
    maturity=knowledge/(knowledge+half)
    gain=max(0.0,_to_float(_get(con,"developmental_rise_gain",4.0),4.0))
    return {"consolidated_knowledge":knowledge,"maturity":maturity,"rise_factor":1.0+gain*(1.0-maturity)}
def _neuromod(con):
    st=_read_kv(con,"phase6a_neuromodulated_sleep_state") if _table_exists(con,"phase6a_neuromodulated_sleep_state") else {}
    return {k:_clamp(_to_float(st.get(k),d)) for k,d in (("acetylcholine",0.5),("glutamate",0.5),("serotonin",0.5),("gaba",0.5))}
def _gain(g,level): return (1.0-0.5*g)+g*level
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
def _sleep_onset(con,level,neuromod,cyc):
    sw=_read_kv(con,SWITCH_TABLE) if _table_exists(con,SWITCH_TABLE) else {}
    high=_clamp(_to_float(sw.get("upper_threshold"),0.67),0.01,0.99)
    dmin=_to_float(_get(con,"downscale_min",0.05),0.05); dmax=_to_float(_get(con,"downscale_max",0.25),0.25)
    glu=neuromod["glutamate"]; sero=neuromod["serotonin"]
    pull=dmin+max(0.0,level-high)*(dmax-dmin)/max(1e-6,1-high); pull=_clamp(pull*(0.7+0.6*glu)*(1-0.3*sero),0.02,0.4)
    affected=[]
    for k,v,side in _targets(con):
        nv=_clamp(v+(BIAS_MIDS[k]-v)*pull)
        for table in ("phase6a_meta_plasticity_state","phase6a_neuromodulated_sleep_state","phase6c_target_bias_state"):
            if _table_exists(con,table): _kv_set(con,table,k,round(nv,6))
        affected.append({"key":k,"pre":v,"post":nv,"side":side})
    if affected: _set(con,"total_downscales",_to_int(_get(con,"total_downscales",0))+1)
    _log(con,cyc,"sleep_onset_downscale" if affected else "sleep_onset",level,level,pull if affected else 0.0,"renormalize_saturated_biases" if affected else "none",[a["key"] for a in affected],"sleep_onset","glutamate",glu)
    return {"pull":pull if affected else 0.0,"targets_affected":affected}
def run_phase7a_cycle(db_or_obj=None,cycle_index=None):
    con=resolve_db(db_or_obj); ensure_schema(con); initialize_adenosine_parameters(con)
    if cycle_index is None: cycle_index=_to_int(_read_kv(con,"phase7a_state").get("cycle_count"),0)+1
    neu=_neuromod(con); state=sleep_state(con); previous=str(_get(con,"last_seen_state","wake")).lower()
    old=_clamp(_to_float(_get(con,"adenosine_level",0.0),0.0))
    load=_measure_encoding_load(con,update=(state=="wake"))
    onset=None; dev=_maturity(con)
    if state=="sleep":
        if previous!="sleep": onset=_sleep_onset(con,old,neu,cycle_index)
        rate=max(0.0,_to_float(_get(con,"sleep_decay_rate",0.0666),0.0666))*_gain(_to_float(_get(con,"gaba_decay_gain",0.4),0.4),neu["gaba"])
        new=_clamp(old*math.exp(-rate)); _set(con,"total_sleep_cycles",_to_int(_get(con,"total_sleep_cycles",0))+1)
        _log(con,cycle_index,"sleep_dissipation",new,old,1-math.exp(-rate),"dissipate",[],"process_s_exponential_decay","gaba",neu["gaba"])
    else:
        rate=max(0.0,_to_float(_get(con,"wake_rise_rate",0.0154),0.0154))*dev["rise_factor"]*(0.5+load["encoding_load"])*_gain(_to_float(_get(con,"glutamate_rise_gain",0.4),0.4),neu["glutamate"])
        new=_clamp(1.0-(1.0-old)*math.exp(-rate)); _set(con,"total_wake_cycles",_to_int(_get(con,"total_wake_cycles",0))+1)
        _log(con,cycle_index,"wake_buildup",new,new,0.0,"accumulate",[],"process_s_saturating_rise","glutamate",neu["glutamate"])
    for k,v in (("adenosine_level",round(new,6)),("last_adenosine_level",round(old,6)),("last_rate",round(rate,6)),("last_encoding_load",round(load["encoding_load"],6)),("last_new_hypotheses",load["new_hypotheses"]),("last_new_outcomes",load["new_outcomes"]),("last_seen_state",state),("developmental_maturity",round(dev["maturity"],6)),("developmental_rise_factor",round(dev["rise_factor"],6)),("consolidated_knowledge",dev["consolidated_knowledge"])): _set(con,k,v)
    for k,v in (("cycle_count",cycle_index),("last_cycle_at",_now()),("phase",PHASE),("phase_version",PHASE_VERSION),("learning_mode",LEARNING_MODE),("no_word_blacklists",True),("direct_fact_writes","disabled"),("direct_relation_writes","disabled"),("fact_promotion","disabled"),("adenosine_homeostat",True)):_kv_set(con,"phase7a_state",k,v)
    con.commit()
    return {"phase":PHASE,"phase_version":PHASE_VERSION,"cycle_index":cycle_index,"status":"ok","sleep_state":state,"adenosine_before":old,"adenosine_after":new,"rate":rate,"encoding_load":load,"development":dev,"sleep_onset":onset,"safety":{"direct_fact_writes":"disabled","direct_relation_writes":"disabled","fact_promotion":"disabled","no_word_blacklists":True}}
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
