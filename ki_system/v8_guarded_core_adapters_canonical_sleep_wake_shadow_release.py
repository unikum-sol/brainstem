from __future__ import annotations

import json
import time
from collections import deque
from typing import Any

MODE = "shadow_only"
VERSION = "guarded_core_adapters_canonical_sleep_wake_shadow_v1"
_MAX_OBSERVATIONS = 512
_ADAPTER_OBSERVATIONS = deque(maxlen=_MAX_OBSERVATIONS)
_CONTRACTS = {
    "compute_2ag_decay": ("reference_full_return", (), None),
    "compute_anandamide_level": ("scalar_field", ("anandamide",), None),
    "compute_anandamide_ltd_value": ("per_iteration_scalar_field", ("value",), None),
    "compute_bdnf_state": ("core_mapping_fields", ("bdnf_level", "bdnf_target", "regime"), None),
    "compute_ei_balance": ("core_mapping_fields", ("glu_post", "gaba_post"), None),
    "compute_phase6b_plasticity_adjustment": ("nested_recommendation_fields", ("plasticity_level", "exploration_bias", "consolidation_bias", "inhibition_bias", "revision_bias"), "recommended"),
}

def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return repr(value)

def _projection(name: str, kernel_result: Any) -> dict[str, Any]:
    adapter, fields, nested = _CONTRACTS[name]
    if adapter == "reference_full_return":
        return {"adapter": adapter, "valid": True, "projection": _plain(kernel_result), "missing": []}
    source = kernel_result
    if nested is not None:
        source = kernel_result.get(nested) if isinstance(kernel_result, dict) else None
    valid_mapping = isinstance(source, dict)
    missing = [field for field in fields if not valid_mapping or field not in source]
    projection = {field: _plain(source.get(field)) for field in fields if valid_mapping and field in source}
    return {"adapter": adapter, "valid": valid_mapping and not missing, "projection": projection, "missing": missing}

def observe_adapter(name: str, kernel_result: Any) -> Any:
    """Observe and canonicalize for diagnostics; return the exact original object."""
    try:
        item = _projection(name, kernel_result)
        item.update({"kernel": name, "observed_at": time.time(), "mode": MODE, "applied": False})
        _ADAPTER_OBSERVATIONS.append(item)
    except Exception as exc:
        _ADAPTER_OBSERVATIONS.append({"kernel": name, "valid": False, "error": type(exc).__name__, "mode": MODE, "applied": False})
    return kernel_result

def adapter_snapshot() -> dict[str, Any]:
    rows = list(_ADAPTER_OBSERVATIONS)
    return {"version": VERSION, "mode": MODE, "bounded": True, "max_observations": _MAX_OBSERVATIONS, "count": len(rows), "observations": rows}

def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

def _read_kv(con, table: str) -> dict[str, Any]:
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())

def _set(con, key: str, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    con.execute("INSERT INTO phase7a_adenosine_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (key, payload, int(time.time())))

def observe_sleep_wake_shadow(con, scope: dict[str, Any]) -> dict[str, Any]:
    """One shadow evaluation per completed Phase-7a cycle. No downstream authority."""
    cycle = _to_int(scope.get("cycle_index"), -1)
    accum = scope.get("accum") if isinstance(scope.get("accum"), dict) else {}
    down = scope.get("downscale_result") if isinstance(scope.get("downscale_result"), dict) else {}
    state = _read_kv(con, "phase7a_adenosine_state")
    high = _to_float(state.get("threshold_high"), 0.65)
    low = _to_float(state.get("threshold_low"), 0.15)
    post_accum = _to_float(accum.get("new"), _to_float(state.get("adenosine_level")))
    post_down = _to_float(down.get("adenosine_after", down.get("new_adenosine", state.get("adenosine_level"))), _to_float(state.get("adenosine_level")))
    previous = str(state.get("canonical_sleep_wake_state_shadow", "")).strip().lower()
    initialized = previous in ("wake", "sleep")
    if not initialized:
        previous = "sleep" if post_accum >= high else "wake"
        reason = "initialize_from_existing_level_and_thresholds"
        entered = cycle
        transitions = 0
    else:
        reason = "hold"
        entered = _to_int(state.get("canonical_state_entered_cycle_shadow"), cycle)
        transitions = _to_int(state.get("canonical_transition_count_shadow"), 0)
    candidate = previous
    if previous == "wake" and post_accum >= high:
        candidate = "sleep"; reason = "post_accumulation_at_or_above_existing_high"
    elif previous == "sleep" and post_down <= low:
        candidate = "wake"; reason = "post_downscale_at_or_below_existing_low"
    last_cycle = _to_int(state.get("canonical_last_evaluated_cycle_shadow"), -2)
    suppressed = _to_int(state.get("canonical_suppressed_same_cycle_candidates_shadow"), 0)
    changed = candidate != previous
    if cycle == last_cycle and changed:
        candidate = previous; changed = False; suppressed += 1; reason = "suppressed_one_transition_per_cycle"
    if changed:
        transitions += 1; entered = cycle
        _set(con, "canonical_last_transition_cycle_shadow", cycle)
    _set(con, "canonical_sleep_wake_state_shadow", candidate)
    _set(con, "canonical_state_entered_cycle_shadow", entered)
    _set(con, "canonical_last_evaluated_cycle_shadow", cycle)
    _set(con, "canonical_transition_reason_shadow", reason)
    _set(con, "canonical_transition_count_shadow", transitions)
    _set(con, "canonical_suppressed_same_cycle_candidates_shadow", suppressed)
    _set(con, "canonical_dwell_cycles_shadow", max(0, cycle - entered + 1))
    _set(con, "canonical_post_accumulation_adenosine_shadow", post_accum)
    _set(con, "canonical_post_downscale_adenosine_shadow", post_down)
    _set(con, "canonical_multiple_phase7a_events_cycle_shadow", 1 if down else 0)
    _set(con, "canonical_shadow_mode", MODE)
    _set(con, "canonical_downstream_authority", "disabled")
    observe_event_typed_checkpoint(con, cycle)  # EVENT_TYPED_COUNTER_PROVENANCE_WAKE_EXIT_MATRIX_SHADOW_V1
    return {"cycle_index": cycle, "state": candidate, "transitioned": changed, "reason": reason, "applied": False, "downstream_authority": False}

def selftest() -> dict[str, Any]:
    samples = {
        "compute_2ag_decay": 0.4,
        "compute_anandamide_level": {"anandamide": 0.2, "target": 0.3},
        "compute_anandamide_ltd_value": {"value": 0.2, "effective_pull": 0.1},
        "compute_bdnf_state": {"bdnf_level": 0.4, "bdnf_target": 0.5, "regime": "hold"},
        "compute_ei_balance": {"glu_post": 0.5, "gaba_post": 0.4},
        "compute_phase6b_plasticity_adjustment": {"recommended": {"plasticity_level": 0.5, "exploration_bias": 0.5, "consolidation_bias": 0.5, "inhibition_bias": 0.5, "revision_bias": 0.5}},
    }
    identity_ok = all(observe_adapter(k, v) is v for k, v in samples.items())
    valid = all(_projection(k, v)["valid"] for k, v in samples.items())
    return {"status": "ok" if identity_ok and valid else "failed", "identity_preserved": identity_ok, "six_contracts_valid": valid, "mode": MODE}

# EVENT_TYPED_COUNTER_PROVENANCE_WAKE_EXIT_MATRIX_SHADOW_V1
_ET_MAX=512
_ET_MATRIX_LIMIT=64

def _et_int(v,d=0):
    try: return int(float(v))
    except (TypeError,ValueError): return d

def _et_float(v,d=None):
    try: return float(v)
    except (TypeError,ValueError): return d

def _et_nonempty(v):
    s=str(v or "").strip()
    if s in ("","[]","None","null"): return False
    try: return bool(json.loads(s))
    except Exception: return True

def _et_kind(t,factor,targets):
    f=_et_float(factor,0.0); has_targets=_et_nonempty(targets)
    if t=="buildup": return "buildup"
    if t=="idle_decay" and f==0.0 and not has_targets: return "idle_decay"
    if t=="sleep_downscale" and f>0.0 and has_targets: return "true_target_downscale"
    return "unclassified"

def _et_exists(con,t):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None

def _et_cols(con,t):
    return [str(r[1]) for r in con.execute("PRAGMA table_info("+t+")").fetchall()] if _et_exists(con,t) else []

def _et_context(con,t,cycle,wanted):
    cols=set(_et_cols(con,t))
    if "cycle_index" not in cols: return None
    selected=[x for x in wanted if x in cols]
    if not selected: return None
    row=con.execute("SELECT "+",".join(selected)+" FROM "+t+" WHERE cycle_index=? ORDER BY rowid DESC LIMIT 1",(int(cycle),)).fetchone()
    return dict(zip(selected,row)) if row is not None else None

def observe_event_typed_checkpoint(con,current_cycle):
    if not _et_exists(con,"phase7a_adenosine_events"): return {"status":"event_table_missing","applied":False}
    required={"id","cycle_index","event_type","adenosine_level","downscale_factor","targets_affected"}
    cols=set(_et_cols(con,"phase7a_adenosine_events"))
    if not required.issubset(cols): return {"status":"event_columns_missing","missing":sorted(required-cols),"applied":False}
    st=_read_kv(con,"phase7a_adenosine_state")
    checkpoint=_et_int(st.get("canonical_event_observer_checkpoint_event_id_shadow"),-1)
    if checkpoint<0:
        latest=_et_int(con.execute("SELECT COALESCE(MAX(id),0) FROM phase7a_adenosine_events").fetchone()[0],0)
        start=latest+1
        for k,v in (("canonical_counter_provenance_start_event_id_shadow",start),("canonical_counter_provenance_start_cycle_shadow",int(current_cycle)),("canonical_event_observer_checkpoint_event_id_shadow",latest),("canonical_idle_decay_count_shadow",0),("canonical_true_target_downscale_count_shadow",0),("canonical_cycles_since_last_true_target_downscale_shadow","unknown_no_true_target_downscale_since_provenance"),("canonical_wake_exit_candidate_matrix_shadow",[]),("canonical_event_typed_observer_mode","shadow_only"),("canonical_event_typed_observer_authority","disabled")):
            _set(con,k,v)
        return {"status":"initialized_future_only","start_event_id":start,"applied":False}
    rows=con.execute("SELECT id,cycle_index,event_type,adenosine_level,downscale_factor,targets_affected,reason FROM phase7a_adenosine_events WHERE id>? AND cycle_index<? ORDER BY id LIMIT ?",(checkpoint,int(current_cycle),_ET_MAX)).fetchall()
    idle=_et_int(st.get("canonical_idle_decay_count_shadow"),0); true_count=_et_int(st.get("canonical_true_target_downscale_count_shadow"),0); last_true=_et_int(st.get("canonical_last_true_target_downscale_cycle_shadow"),-1)
    try:
        matrix=json.loads(st.get("canonical_wake_exit_candidate_matrix_shadow","[]"))
        if not isinstance(matrix,list): matrix=[]
    except Exception: matrix=[]
    low=_et_float(st.get("threshold_low"),0.15); unknown=0
    for eid,cyc,etype,level,factor,targets,reason in rows:
        kind=_et_kind(str(etype),factor,targets); val=_et_float(level,None); _set(con,"canonical_last_phase7a_event_type_shadow",kind)
        if kind=="buildup": _set(con,"canonical_post_accumulation_adenosine_shadow",val)
        elif kind=="idle_decay": idle+=1; _set(con,"canonical_post_idle_decay_adenosine_shadow",val)
        elif kind=="true_target_downscale": true_count+=1; last_true=int(cyc); _set(con,"canonical_post_target_downscale_adenosine_shadow",val); _set(con,"canonical_last_true_target_downscale_cycle_shadow",last_true)
        else: unknown+=1
        p7d=_et_context(con,"phase7d_slow_wave_cycles",cyc,("cycle_index","adenosine_level","reason","candidates_reactivated","candidates_survived"))
        p7e=_et_context(con,"phase7e_histamine_cycles",cyc,("cycle_index","histamine_level","adenosine_level","wake_activity","wake_drive","sleep_pressure","reciprocal_gate","regime"))
        low_hit=val is not None and val<=low; candidate=kind in ("idle_decay","true_target_downscale") and low_hit
        matrix.append({"event_id":int(eid),"cycle_index":int(cyc),"event_type":str(etype),"classified_type":kind,"adenosine_level":val,"threshold_low_reached":bool(low_hit),"phase7d":p7d,"phase7e":p7e,"hypothetical_wake_exit_candidate":bool(candidate),"candidate_reason":"event_typed_numeric_candidate_observation_only" if candidate else "not_authorized","canonical_state_change_applied":False})
        checkpoint=int(eid)
    matrix=matrix[-_ET_MATRIX_LIMIT:]
    for k,v in (("canonical_idle_decay_count_shadow",idle),("canonical_true_target_downscale_count_shadow",true_count),("canonical_event_observer_checkpoint_event_id_shadow",checkpoint),("canonical_event_observer_last_cycle_shadow",int(current_cycle)),("canonical_event_observer_last_batch_size_shadow",len(rows)),("canonical_event_observer_unclassified_count_shadow",_et_int(st.get("canonical_event_observer_unclassified_count_shadow"),0)+unknown),("canonical_wake_exit_candidate_matrix_shadow",matrix),("canonical_wake_exit_candidate_count_shadow",sum(1 for x in matrix if x.get("hypothetical_wake_exit_candidate"))),("canonical_state_change_applied_by_event_observer_shadow",False),("canonical_event_typed_observer_mode","shadow_only"),("canonical_event_typed_observer_authority","disabled")):
        _set(con,k,v)
    if last_true>=0: _set(con,"canonical_cycles_since_last_true_target_downscale_shadow",max(0,int(current_cycle)-last_true))
    return {"status":"observed","processed":len(rows),"checkpoint":checkpoint,"unclassified":unknown,"applied":False}

def event_typed_observer_selftest():
    ok=_et_kind("buildup",0,"[]")=="buildup" and _et_kind("idle_decay",0,"[]")=="idle_decay" and _et_kind("sleep_downscale",0.2,"[1]")=="true_target_downscale"
    return {"status":"ok" if ok else "failed","mode":"shadow_only","productive_counter_write":False,"wake_exit_authority":False,"matrix_limit":_ET_MATRIX_LIMIT,"max_events_per_cycle":_ET_MAX}
