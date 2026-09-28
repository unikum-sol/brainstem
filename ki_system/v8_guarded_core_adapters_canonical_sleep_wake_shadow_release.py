from __future__ import annotations

import time
from collections import deque
from typing import Any

# BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): this module used
# to also contain observe_sleep_wake_shadow()/observe_event_typed_checkpoint()
# (plus their private _to_float/_to_int/_read_kv/_set/_et_* helpers), a
# second, DB-writing shadow cascade that tracked a hypothetical "canonical
# sleep/wake state" and a "wake-exit candidate matrix" for Phase 7a, once per
# real cycle. Exhaustive cross-reference across the whole codebase confirmed
# every one of its "canonical_*_shadow" state keys was written but never read
# anywhere else, and its own state explicitly recorded
# "canonical_downstream_authority": "disabled" on every real cycle it ran --
# the same "observe a not-yet-activated future decision" pattern as the five
# other shadow cascades removed in the same cleanup (see the Legacy Report
# shipped with this cleanup for the full verification trail, including the
# single call site in v8_phase7a_adenosine_homeostat_release.py that has
# been removed accordingly).
#
# The functions below (observe_adapter/_projection/_plain/adapter_snapshot/
# selftest) are UNRELATED and have NOT been touched: they are a lightweight,
# in-memory-only (bounded deque, no database writes), identity-preserving
# kernel round-trip validator, still actively called from Phase 7b, 7c, 6b
# and 7g to canonicalize kernel outputs for live diagnostics. They return the
# exact original object unchanged and carry no dependency on, or shared
# purpose with, the removed sleep/wake shadow code.

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
