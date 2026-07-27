# -*- coding: utf-8 -*-
"""Stage-B guarded hypothesis graduation with productive fact closure.

Graduates at most one uncertain hypothesis per cycle to stable_hypothesis.
No facts, relations, or questions are written. Eligibility requires three
separate Phase-7d consolidation survival cycles, warm-up completion, active
status, and the canonical Phase-6b critic gate.
"""
from __future__ import annotations
import json, os, sqlite3, time
from pathlib import Path

PHASE = "stageb_guarded_hypothesis_graduation_release"
VERSION = "stageb_cd_v1"
STATE = "stageb_graduation_state"
EVENTS = "stageb_graduation_events"
PROTECTED = ("facts", "relations", "questions")
SCHEMA_TABLES = {
    STATE: [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    EVENTS: [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
             ("hypothesis_id","INTEGER"),("old_role","TEXT"),("new_role","TEXT"),("survival_cycles","INTEGER"),
             ("critic_allowed","INTEGER"),("critic_penalty","REAL"),("critic_reason","TEXT"),
             ("decision","TEXT"),("details","TEXT"),("facts_before","INTEGER"),("facts_after","INTEGER"),
             ("relations_before","INTEGER"),("relations_after","INTEGER"),("questions_before","INTEGER"),
             ("questions_after","INTEGER")],
}
DEFAULTS = {"enabled":"true","warmup_cycles":"50","cycle_count":"0","minimum_7d_survivals":"3",
            "promotion_budget":"1","total_graduated":"0","fact_promotion":"disabled",
            "direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_writes":"disabled",
            "mode":"consolidation_gated_stable_hypothesis_only"}

def _now(): return int(time.time())
def _table_exists(con,t): return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _columns(con,t): return [r[1] for r in con.execute("PRAGMA table_info("+t+")")] if _table_exists(con,t) else []
def _read_kv(con,table):
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())
def _set(con,k,v):
    con.execute("INSERT INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,str(v).lower() if isinstance(v,bool) else str(v),_now()))
def _int(v,d=0):
    try: return int(float(v))
    except Exception: return d
def _float(v,d=0.0):
    try: return float(v)
    except Exception: return d
def _count(con,t): return int(con.execute("SELECT COUNT(*) FROM "+t).fetchone()[0]) if _table_exists(con,t) else 0
def _protected(con): return {t:_count(con,t) for t in PROTECTED}
def resolve_db(obj=None):
    if isinstance(obj,sqlite3.Connection): obj.row_factory=sqlite3.Row; return obj
    if obj is not None:
        for a in ("db","conn","con","connection"):
            v=getattr(obj,a,None)
            if isinstance(v,sqlite3.Connection): v.row_factory=sqlite3.Row; return v
        for a in ("mem","memory"):
            v=getattr(obj,a,None)
            if v is not None and v is not obj:
                try: return resolve_db(v)
                except Exception: pass
    path="ki_memory.sqlite3"
    p=Path(__file__).resolve().parent.parent/path
    if not os.path.exists(path) and p.exists(): path=str(p)
    con=sqlite3.connect(path,timeout=30); con.row_factory=sqlite3.Row; return con

def ensure_schema(con):
    for table,defs in SCHEMA_TABLES.items():
        if not _table_exists(con,table): con.execute("CREATE TABLE "+table+" ("+", ".join(n+" "+d for n,d in defs)+")")
        else:
            live=set(_columns(con,table))
            for n,d in defs:
                if n not in live and "PRIMARY KEY" not in d.upper() and "AUTOINCREMENT" not in d.upper(): con.execute("ALTER TABLE "+table+" ADD COLUMN "+n+" "+d)
    con.execute("CREATE INDEX IF NOT EXISTS idx_stageb_grad_cycle ON "+EVENTS+"(cycle_index)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_stageb_grad_hyp ON "+EVENTS+"(hypothesis_id)")
    for k,v in DEFAULTS.items(): con.execute("INSERT OR IGNORE INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?)",(k,v,_now()))
    con.commit(); return _self_check_schema(con)
def _self_check_schema(con):
    missing=[]
    for t,defs in SCHEMA_TABLES.items():
        live=set(_columns(con,t)); missing += [t+"."+n for n,_ in defs if n not in live]
    if missing: raise RuntimeError("stageb graduation schema missing: "+repr(missing))
    return {"overall":True,"missing":[]}
def _bias_state(con):
    st=_read_kv(con,"phase6a_meta_plasticity_state") if _table_exists(con,"phase6a_meta_plasticity_state") else {}
    return {"plasticity_level":_float(st.get("last_plasticity_level"),.5),"exploration_bias":_float(st.get("last_exploration_bias"),.5),
            "consolidation_bias":_float(st.get("last_consolidation_bias"),.5),"inhibition_bias":_float(st.get("last_inhibition_bias"),.3),
            "revision_bias":_float(st.get("last_revision_bias"),.5)}
def _critic(con,anchor_consistency):
    try:
        from ki_system import v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release as p6b
        return p6b._critic_gate(con,_bias_state(con),anchor_consistency)
    except Exception as exc:
        return False,1.0,"critic_gate_unavailable:"+type(exc).__name__
def _candidates(con,minimum,limit=64):
    if not _table_exists(con,"context_hypotheses") or not _table_exists(con,"phase7d_consolidation_survivors"): return []
    cols=set(_columns(con,"context_hypotheses")); role_expr="COALESCE(h.role,'')" if "role" in cols else "''"; status_expr="COALESCE(h.status,'active')" if "status" in cols else "'active'"
    q=("SELECT h.id,"+role_expr+","+status_expr+",COUNT(DISTINCT s.cycle_index) AS survived,AVG(COALESCE(s.final_consistency,0)) AS consistency "
       "FROM context_hypotheses h JOIN phase7d_consolidation_survivors s ON s.source_table='context_hypotheses' AND s.source_id=h.id "
       "WHERE "+role_expr+"='uncertain_hypothesis' AND "+status_expr+"='active' AND COALESCE(s.reinforced,0)=1 "
       "GROUP BY h.id HAVING COUNT(DISTINCT s.cycle_index)>=? ORDER BY survived DESC,consistency DESC,h.id ASC LIMIT ?")
    return [dict(r) for r in con.execute(q,(minimum,limit)).fetchall()]
def _log(con,cycle,hid,old,new,surv,allowed,penalty,reason,decision,details,b,a):
    con.execute("INSERT INTO "+EVENTS+"(created_at,cycle_index,hypothesis_id,old_role,new_role,survival_cycles,critic_allowed,critic_penalty,critic_reason,decision,details,facts_before,facts_after,relations_before,relations_after,questions_before,questions_after) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(_now(),cycle,hid,old,new,surv,1 if allowed else 0,penalty,reason,decision,json.dumps(details,sort_keys=True),b["facts"],a["facts"],b["relations"],a["relations"],b["questions"],a["questions"]))
def run_graduation_cycle(obj=None,cycle_index=None):
    con=resolve_db(obj); ensure_schema(con); st=_read_kv(con,STATE); cycle=_int(cycle_index,_int(st.get("cycle_count"),0)+1); _set(con,"cycle_count",cycle)
    before=_protected(con); warmup=_int(st.get("warmup_cycles"),50); minimum=max(3,_int(st.get("minimum_7d_survivals"),3)); budget=min(1,max(0,_int(st.get("promotion_budget"),1)))
    if str(st.get("enabled","true")).lower()!="true" or cycle<=warmup or budget==0:
        con.commit(); return {"phase":PHASE,"graduated":0,"reason":"disabled_warmup_or_zero_budget","cycle_index":cycle,"protected_unchanged":True}
    graduated=0; decisions=[]
    con.execute("SAVEPOINT stageb_graduation")
    try:
        for cand in _candidates(con,minimum):
            if graduated>=budget: break
            allowed,penalty,reason=_critic(con,_float(cand.get("consistency"),0.0)); decision="blocked_by_critic"
            if allowed:
                cur=con.execute("UPDATE context_hypotheses SET role='stable_hypothesis',updated_at=? WHERE id=? AND role='uncertain_hypothesis' AND COALESCE(status,'active')='active'",(_now(),cand["id"]))
                if cur.rowcount==1: graduated+=1; decision="graduated_to_stable_hypothesis"
            after_now=_protected(con)
            if after_now!=before: raise RuntimeError("protected_productive_counts_changed")
            _log(con,cycle,cand["id"],"uncertain_hypothesis","stable_hypothesis" if decision.startswith("graduated") else "uncertain_hypothesis",cand["survived"],allowed,penalty,reason,decision,{"budget":budget,"minimum_7d_survivals":minimum,"anchor_consistency":cand.get("consistency")},before,after_now)
            decisions.append({"hypothesis_id":cand["id"],"decision":decision,"survival_cycles":cand["survived"],"critic_reason":reason})
        after=_protected(con)
        if after!=before: raise RuntimeError("protected_productive_counts_changed")
        _set(con,"total_graduated",_int(st.get("total_graduated"),0)+graduated); _set(con,"last_graduated",graduated); _set(con,"last_decisions",json.dumps(decisions,sort_keys=True)); _set(con,"fact_promotion","disabled")
        con.execute("RELEASE SAVEPOINT stageb_graduation"); con.commit()
        return {"phase":PHASE,"version":VERSION,"cycle_index":cycle,"graduated":graduated,"budget":budget,"decisions":decisions,"protected_unchanged":True,"fact_promotion":"disabled"}
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_graduation"); con.execute("RELEASE SAVEPOINT stageb_graduation"); con.commit(); raise

def managed_cycle(self,progress=None):
    downstream=None
    try:
        from ki_system import v8_phase7cort_stability_watch_release as m
        downstream=m.managed_cycle(self,progress)
    except Exception as exc: downstream={"status":"downstream_error","error":str(exc)}
    try: result=run_graduation_cycle(self)
    except Exception as exc: result={"phase":PHASE,"status":"error","error":type(exc).__name__+":"+str(exc),"graduated":0}
    return {"phase":PHASE,"downstream_result":downstream,"stageb_graduation_result":result}
def managed_run(self,cycles=1,progress=None): return {"phase":PHASE,"results":[managed_cycle(self,progress) for _ in range(max(1,int(cycles or 1)))]}
def autoload(AutonomousLoop):
    AutonomousLoop.cycle=managed_cycle; AutonomousLoop.run=managed_run; AutonomousLoop.stageb_guarded_hypothesis_graduation=True
    AutonomousLoop.fact_promotion="disabled"; AutonomousLoop.direct_fact_writes="disabled"; AutonomousLoop.direct_relation_writes="disabled"
    return AutonomousLoop
