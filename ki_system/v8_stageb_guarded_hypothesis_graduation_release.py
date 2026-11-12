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
ELIGIBLE_ROLES = {
    "uncertain_hypothesis": "stable_hypothesis",
    "uncertain_lexical_boundary": "stable_lexical_boundary",
    "uncertain_relation_hypothesis": "stable_relation_hypothesis",
}
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
            "mode":"consolidation_gated_stable_hypothesis_only",
            "selection_pressure_ach_novelty_gain":"0.6",
            "selection_pressure_gaba_temperature_gain":"0.5",
            "selection_pressure_temperature_base":"1.0"}

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
def _candidates(con,minimum,limit=64,role_filter=None,exclude_ids=None):
    if not _table_exists(con,"context_hypotheses") or not _table_exists(con,"phase7d_consolidation_survivors"): return []
    cols=set(_columns(con,"context_hypotheses")); role_expr="COALESCE(h.role,'')" if "role" in cols else "''"; status_expr="COALESCE(h.status,'active')" if "status" in cols else "'active'"
    roles_to_use = [role_filter] if role_filter else list(ELIGIBLE_ROLES)
    role_list = ",".join("'" + r.replace("'", "''") + "'" for r in roles_to_use)
    exclude_clause = ""
    params = [minimum]
    if exclude_ids:
        exclude_clause = " AND h.id NOT IN (" + ",".join("?" for _ in exclude_ids) + ")"
        params = [minimum] + list(exclude_ids)
    # Literatur: Nader et al. 2000; Sevenster et al. 2013
    reconsolidation_clause = ""
    if _table_exists(con, "hypothesis_revisions"):
        reconsolidation_clause = (" AND s.created_at > COALESCE((SELECT MAX(r.created_at) FROM hypothesis_revisions r "
                                  "WHERE r.hypothesis_id=h.id),0)")
    q=("SELECT h.id,"+role_expr+" AS matched_role,"+status_expr+" AS matched_status,COUNT(DISTINCT s.cycle_index) AS survived,AVG(COALESCE(s.final_consistency,0)) AS consistency "
       "FROM context_hypotheses h JOIN phase7d_consolidation_survivors s ON s.source_table='context_hypotheses' AND s.source_id=h.id "
       "WHERE "+role_expr+" IN ("+role_list+") AND "+status_expr+"='active' AND COALESCE(s.reinforced,0)=1"+exclude_clause+reconsolidation_clause+" "
       "GROUP BY h.id HAVING COUNT(DISTINCT s.cycle_index)>=? ORDER BY survived DESC,consistency DESC,h.id ASC LIMIT ?")
    params.append(limit)
    return [dict(r) for r in con.execute(q,tuple(params)).fetchall()]

# Literatur: Carandini & Heeger 2011
_SIGMA_DEFAULT = 1.0

# Literatur: Douchamps et al. 2013; Gomez-Ocadiz et al. 2022; Katzner et al. 2011
def _neuromodulators(con):
    """Identical access pattern to every other module in this chain that
    reads the shared six-core neuromodulator snapshot (e.g. v8_stageb_
    question_promotion_release.py's / v8_stageb_gap_detection_release.py's
    own _neuromodulators()) -- no new messenger responsibility introduced."""
    defaults = {
        "dopamine": 0.5, "serotonin": 0.6, "glutamate": 0.4,
        "gaba": 0.4, "noradrenaline": 0.3, "acetylcholine": 0.5,
    }
    if not _table_exists(con, "phase6a_neuromodulated_sleep_state"):
        return defaults
    values = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    for key in tuple(defaults):
        try:
            defaults[key] = float(values.get(key, defaults[key]))
        except (TypeError, ValueError):
            pass
    return defaults


def _historical_role_graduations(con):
    """Per-role count of how many times that role has EVER actually
    graduated in this project's real history, read directly from this
    module's own, already-existing EVENTS log -- reused as-is, no new
    table. new_role stores the TARGET role name (e.g. 'stable_hypothesis')
    on a real graduation event, so this maps each target name back to its
    ELIGIBLE_ROLES source key."""
    counts = {role: 0 for role in ELIGIBLE_ROLES}
    if not _table_exists(con, EVENTS):
        return counts
    target_to_role = {target: role for role, target in ELIGIBLE_ROLES.items()}
    rows = con.execute(
        "SELECT new_role, COUNT(*) FROM " + EVENTS + " WHERE decision LIKE 'graduated_to_%' GROUP BY new_role"
    ).fetchall()
    for new_role, count in rows:
        role = target_to_role.get(new_role)
        if role is not None:
            counts[role] = int(count or 0)
    return counts


def _effective_pressure(con, raw_pressure, state):
    """Applies the acetylcholine novelty bias (see block comment above) to
    each role's raw eligibility-count pressure. Returns (effective_pressure
    dict, diagnostic dict for the event log)."""
    neuromod = _neuromodulators(con)
    acetylcholine = neuromod["acetylcholine"]
    ach_gain = _float(state.get("selection_pressure_ach_novelty_gain"), 0.6)
    historical = _historical_role_graduations(con)
    total_historical = sum(historical.values())
    effective = {}
    novelty_by_role = {}
    for role, pressure in raw_pressure.items():
        if total_historical > 0:
            novelty = 1.0 - (historical.get(role, 0) / total_historical)
        else:
            # No graduation has ever happened for ANY role yet -- neutral,
            # unbiased midpoint rather than an undefined/maximal novelty
            # value with no real history behind it.
            novelty = 0.5
        novelty_by_role[role] = novelty
        effective[role] = pressure * max(0.0, 1.0 + ach_gain * (acetylcholine - 0.5) * novelty)
    diagnostics = {
        "acetylcholine": acetylcholine,
        "gaba": neuromod["gaba"],
        "historical_graduations": historical,
        "novelty_by_role": novelty_by_role,
    }
    return effective, diagnostics


def _role_pressure(con, minimum):
    """Per-role count of candidates that already satisfy this module's own
    graduation-eligibility SQL (see _candidates() above), used as the
    'Bedarfsdruck' input to divisive normalization. A dedicated COUNT query
    per role (not a re-slice of a LIMITed candidate list) so pressure is
    accurate even if a role's true backlog exceeds _candidates()'s own
    per-call limit."""
    pressure = {}
    for role in ELIGIBLE_ROLES:
        rows = _candidates(con, minimum, limit=100000, role_filter=role)
        pressure[role] = len(rows)
    return pressure


def _select_role_by_divisive_normalization(pressure, rnd, sigma=_SIGMA_DEFAULT, temperature=1.0):
    """Returns (selected_role_or_None, shares_dict): one role, chosen via
    Efraimidis-Spirakis weighted sampling where the weight of each role is
    its divisive-normalized share:
    share(role) = pressure(role)**temperature / (sum(pressure**temperature) + sigma).
    Roles with zero pressure are excluded outright (nothing to graduate
    there this cycle regardless of share). selected_role is None if every
    role has zero pressure (shares_dict is then empty too), so the caller
    can always safely unpack a 2-tuple regardless of outcome.
    """
    eligible = {role: count for role, count in pressure.items() if count > 0}
    if not eligible:
        return None, {}
    temperature = max(1e-3, temperature)
    powered = {role: count ** temperature for role, count in eligible.items()}
    total = sum(powered.values())
    shares = {role: value / (total + sigma) for role, value in powered.items()}
    keyed = [(rnd.random() ** (1.0 / max(1e-6, share)), role) for role, share in shares.items()]
    keyed.sort(key=lambda x: x[0], reverse=True)
    return keyed[0][1], shares
def _log(con,cycle,hid,old,new,surv,allowed,penalty,reason,decision,details,b,a):
    con.execute("INSERT INTO "+EVENTS+"(created_at,cycle_index,hypothesis_id,old_role,new_role,survival_cycles,critic_allowed,critic_penalty,critic_reason,decision,details,facts_before,facts_after,relations_before,relations_after,questions_before,questions_after) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(_now(),cycle,hid,old,new,surv,1 if allowed else 0,penalty,reason,decision,json.dumps(details,sort_keys=True),b["facts"],a["facts"],b["relations"],a["relations"],b["questions"],a["questions"]))
def run_graduation_cycle(obj=None,cycle_index=None):
    con=resolve_db(obj); ensure_schema(con); st=_read_kv(con,STATE); cycle=_int(cycle_index,_int(st.get("cycle_count"),0)+1); _set(con,"cycle_count",cycle)
    before=_protected(con); warmup=_int(st.get("warmup_cycles"),50); minimum=max(3,_int(st.get("minimum_7d_survivals"),3)); budget=min(1,max(0,_int(st.get("promotion_budget"),1)))
    if str(st.get("enabled","true")).lower()!="true" or cycle<=warmup or budget==0:
        con.commit(); return {"phase":PHASE,"graduated":0,"reason":"disabled_warmup_or_zero_budget","cycle_index":cycle,"protected_unchanged":True}
    graduated=0; decisions=[]
    import random as _random_module
    _rnd = _random_module.Random("stageb_graduation_role_select:%d" % cycle)
    _pressure = _role_pressure(con, minimum)
    _effective_pressure_snapshot, _neuromod_diagnostics = _effective_pressure(con, _pressure, st)
    _temperature_base = _float(st.get("selection_pressure_temperature_base"), 1.0)
    _gaba_gain = _float(st.get("selection_pressure_gaba_temperature_gain"), 0.5)
    _temperature = _temperature_base + _gaba_gain * (_neuromod_diagnostics["gaba"] - 0.5)
    handled_ids = set()
    con.execute("SAVEPOINT stageb_graduation")
    try:
        while graduated < budget:
            selected_role, shares = _select_role_by_divisive_normalization(
                _effective_pressure_snapshot, _rnd, temperature=_temperature
            )
            if selected_role is None:
                break
            role_candidates = _candidates(con, minimum, limit=1, role_filter=selected_role, exclude_ids=handled_ids)
            if not role_candidates:
                _effective_pressure_snapshot[selected_role] = 0
                continue
            cand = role_candidates[0]
            handled_ids.add(cand["id"])
            allowed,penalty,reason=_critic(con,_float(cand.get("consistency"),0.0)); decision="blocked_by_critic"
            old_role=cand.get("matched_role") or "uncertain_hypothesis"
            new_role=ELIGIBLE_ROLES.get(old_role,"stable_hypothesis")
            if allowed:
                cur=con.execute("UPDATE context_hypotheses SET role=?,updated_at=? WHERE id=? AND role=? AND COALESCE(status,'active')='active'",(new_role,_now(),cand["id"],old_role))
                if cur.rowcount==1: graduated+=1; decision="graduated_to_"+new_role
            after_now=_protected(con)
            if after_now!=before: raise RuntimeError("protected_productive_counts_changed")
            _log(con,cycle,cand["id"],old_role,new_role if decision.startswith("graduated") else old_role,cand["survived"],allowed,penalty,reason,decision,{"budget":budget,"minimum_7d_survivals":minimum,"anchor_consistency":cand.get("consistency"),"divisive_normalization_pressure":_pressure,"divisive_normalization_effective_pressure":_effective_pressure_snapshot,"divisive_normalization_shares":shares,"divisive_normalization_temperature":_temperature,"neuromodulator_diagnostics":_neuromod_diagnostics,"selected_role":selected_role},before,after_now)
            decisions.append({"hypothesis_id":cand["id"],"decision":decision,"survival_cycles":cand["survived"],"critic_reason":reason,"role":old_role})
            # Whether graduated or blocked_by_critic, this specific
            # hypothesis id is already excluded from future draws this
            # cycle via handled_ids above -- the next while-loop iteration
            # re-rolls across all roles' current pressure, so one role
            # being repeatedly blocked by the critic gate cannot prevent
            # other roles' candidates from being tried this same cycle.
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
        from ki_system import v8_cooperative_core_neuromodulator_sleep_authority_release as m
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
