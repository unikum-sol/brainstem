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
# BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): _source_rows()
# used to read the removed shadow modules' own "source_rows_seen"-style
# result keys; it is now unused (observe_cycle() below no longer calls
# any of those modules) and has been removed rather than left as dead
# code, per this project's own Legacy Cleanup convention.
# BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): this function
# used to import and call v8_modern_outcome_bridge_shadow_release,
# v8_modern_gap_candidate_bridge_shadow_release and
# v8_modern_gap_phase5f_shadow_observation_release unconditionally on
# every single cycle -- as a SECOND, fully independent invocation of the
# very same three modules already being called (also unconditionally,
# also every cycle) from v8_phase5a_integrated_self_improving_learning_
# release.py and v8_phase5h_strategy_experiment_outcome_learning_
# release.py. All three modules, and their two supporting dependency
# chains, have been removed: exhaustive cross-reference across the whole
# codebase confirmed their output was never read by anything else, and
# their original purpose -- observing what a productive gap/outcome
# decision would look like before one was made -- is already superseded
# by the now-productive Stage-B gap detection, contradiction detection,
# hypothesis revision and fact promotion chain. See the Legacy Report
# shipped with this cleanup for the full verification trail. This
# module's own runtime-contract bookkeeping (STATE/CYCLES tables,
# managed_cycle()/autoload() chaining as the chain-top module) is
# unchanged; only the now-removed cascades' observation calls and their
# result classification are gone, replaced by an explicit
# "shadow_cascades_removed" flow state.
def observe_cycle(obj=None,backend_cycle=None):
    c=resolve_db(obj);ensure_schema(c);st=_read_kv(c,STATE);cycle=_i(backend_cycle,_i(st.get("backend_cycle"),0)+1);before=_protected(c);errors=[]
    results={"outcome":{"status":"removed_shadow_cascade"},"gap":{"status":"removed_shadow_cascade"},"phase5f":{"status":"removed_shadow_cascade"}}
    after=_protected(c);safe=before==after and not errors
    outcome_rows=0;gap_rows=0;p5_rows=0
    p5_obs=0
    flow="shadow_cascades_removed"
    if not safe: c.rollback(); raise RuntimeError("stageb E protected-count or pipeline failure: "+repr(errors)+" before="+repr(before)+" after="+repr(after))
    c.execute("INSERT INTO "+CYCLES+"(created_at,backend_cycle,outcome_source_rows,gap_source_rows,phase5f_source_rows,phase5f_observations,candidate_flow_state,protected_before,protected_after,safety_ok,errors) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(_now(),cycle,outcome_rows,gap_rows,p5_rows,p5_obs,flow,json.dumps(before,sort_keys=True),json.dumps(after,sort_keys=True),1,json.dumps(errors)))
    for k,v in {"backend_cycle":cycle,"backend_status":"running","last_backend_at":_now(),"candidate_flow_state":flow,"last_outcome_source_rows":outcome_rows,"last_gap_source_rows":gap_rows,"last_phase5f_source_rows":p5_rows,"last_phase5f_observations":p5_obs,"last_safety_ok":True,"productive_writes":"disabled"}.items():_set(c,k,v)
    c.commit();return {"phase":PHASE,"version":VERSION,"backend_cycle":cycle,"candidate_flow_state":flow,"results":results,"protected_unchanged":True,"productive_writes":0}
def mark_backend_stopped(obj=None):
    c=resolve_db(obj);ensure_schema(c);_set(c,"backend_status","stopped");_set(c,"last_backend_at",_now());c.commit();return True
# BRAINSTEM_EXPERIMENT_CHAIN_BYPASS_FIX_V1 (22 September 2026)
#
# Root cause (found via a real end-to-end test of the four new Stage-B
# modules added as part of the user-requested "lift the write locks"
# experiment): this function previously hardcoded a DIRECT import of
# v8_stageb_guarded_hypothesis_graduation_release and called its
# managed_cycle() explicitly, bypassing this project's own established
# _PREV_CYCLE chaining convention (used by every other phase module, see
# e.g. v8_phase5a_integrated_self_improving_learning_release.py's
# _PREV_CYCLE / v8_stageb_fact_promotion_release.py's own autoload()).
# Because this module is loaded LAST in phase_registry.py's LOAD_ORDER,
# this hardcoded import silently skipped ANY module registered between
# STAGEB_GRADUATION and this one -- confirmed via a real 100-cycle test
# run: STAGEB_FACT_PROMOTION/STAGEB_CONTRADICTION_DETECTION/
# STAGEB_HYPOTHESIS_REVISION were all successfully loaded (visible in
# get_load_report()) and compiled without error, yet their own state
# tables were never even created, proving their managed_cycle() was never
# actually invoked by a real cycle. Fixed by capturing whatever
# AutonomousLoop.cycle already was at THIS module's own autoload() time
# (below) -- exactly the same pattern already used throughout this
# codebase -- instead of a fixed, specific downstream module name. This
# is a pure bugfix restoring the chaining behavior this project's own
# convention already establishes elsewhere; it does not change what this
# module itself does (observe_cycle() below is completely unchanged).
def managed_cycle(self,progress=None):
    downstream=None
    try:
        downstream=_PREV_CYCLE(self,progress) if _PREV_CYCLE is not None else {"status":"stageb_gapflow_no_previous_cycle"}
    except Exception as exc:downstream={"status":"downstream_error","error":str(exc)}
    # BRAINSTEM CALLBACK PROPAGATION FIX V1
    try:result=observe_cycle(self, progress)
    except Exception as exc:result={"phase":PHASE,"status":"error","error":type(exc).__name__+":"+str(exc),"productive_writes":0}
    return {"phase":PHASE,"downstream_result":downstream,"stageb_runtime_contract_result":result}
def managed_run(self,cycles=1,progress=None):return {"phase":PHASE,"results":[managed_cycle(self,progress) for _ in range(max(1,int(cycles or 1)))]}
_PREV_CYCLE=None
_PREV_RUN=None
# BRAINSTEM_COMPASS_FACT_PROMOTION_FLAG_FIX_V1 (24 September 2026): this
# autoload() runs LAST in phase_registry.py's LOAD_ORDER, so whatever it
# stamps onto AutonomousLoop.fact_promotion here is the final, observable
# value for the entire real cycle chain -- overwriting the correct
# "enabled" assertion made moments earlier by
# v8_stageb_fact_promotion_release.py's own autoload(), which is the
# actual, sole, guarded writer of the facts table. This module (a pure
# runtime-integrity/chaining contract, unrelated to fact promotion
# itself) previously hardcoded "disabled" unconditionally, causing the
# compass to falsely report fact promotion as disabled even while it was
# actively and correctly promoting facts every cycle (confirmed against
# a real production database with 36+ already-promoted facts). Fixed by
# no longer touching fact_promotion here at all, so the correct value
# asserted by its owning module survives. direct_fact_writes and
# direct_relation_writes are left unchanged ("disabled") -- that remains
# correct, since no module performs an ungated, non-consolidated direct
# write to facts or relations; only the guarded Stage-B fact-promotion
# path is active.
def autoload(AutonomousLoop):
    global _PREV_CYCLE,_PREV_RUN
    _PREV_CYCLE=getattr(AutonomousLoop,"cycle",None);_PREV_RUN=getattr(AutonomousLoop,"run",None)
    AutonomousLoop.cycle=managed_cycle;AutonomousLoop.run=managed_run;AutonomousLoop.stageb_gapflow_runtime_contract=True
    AutonomousLoop.direct_fact_writes="disabled";AutonomousLoop.direct_relation_writes="disabled";return AutonomousLoop
