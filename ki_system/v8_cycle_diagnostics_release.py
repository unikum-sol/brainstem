# -*- coding: utf-8 -*-
"""BrainStem cycle diagnostics summarizer.

BRAINSTEM_CYCLE_DIAGNOSTICS_V1

Problem this fixes: every phase's managed_cycle() wraps its own work in a
try/except and turns real failures into an ordinary-looking nested dictionary
key such as {"status": "error", ...} or {"base_cycle_error": "..."}. The
*outer* cycle() call always returns successfully (no exception propagates),
so a GUI, a script, or a human skimming the top-level result can easily miss
that a core phase (for example Phase 6a replay) silently failed while
downstream phases kept reporting "status": "ok".

This module does not change any phase's own behavior or return contract. It
only adds a read-only, recursive scan over an already-produced cycle result
dictionary and classifies the overall outcome as:

  - "ok"       - no failure indicators found anywhere in the tree.
  - "degraded" - only non-core / shadow / observer paths reported problems.
  - "failed"   - at least one core phase reported a failure.

Core phase name fragments are matched against the "phase" field found at each
level of the nested result (e.g. "phase6a_neuromodulated_sleep_replay...",
"phase7c_adaptive_boundaries...", "cooperative_core_neuromodulator...",
"stageb_gapflow_runtime_contract..."). Fragments containing "shadow",
"non_productive", "workpoint_observer", or "recheck" are treated as
non-core/observational and only ever produce a "degraded" classification.
"""
from __future__ import annotations
from typing import Any, Dict, List

FAILURE_STATUS_VALUES = {
    "error",
    "schema_check_failed",
    "phase6a_sleep_replay_error",
    "phase7c_error",
    "phase7d_error",
    "phase7e_error",
    "phase7f_error",
    "phase7g_error",
    "phase7a_error",
    "phase7b_error",
    "observer_error",
}

NON_CORE_MARKERS = ("shadow", "non_productive", "workpoint_observer", "recheck", "bridge")


def _is_non_core(phase_name: str) -> bool:
    name = (phase_name or "").lower()
    return any(marker in name for marker in NON_CORE_MARKERS)


def _walk(node: Any, path: str, findings: List[Dict[str, Any]]) -> None:
    if isinstance(node, dict):
        phase_name = node.get("phase")
        status = node.get("status")
        if status in FAILURE_STATUS_VALUES:
            findings.append({
                "path": path,
                "phase": phase_name,
                "status": status,
                "error": node.get("error"),
                "core": not _is_non_core(phase_name if phase_name else path),
            })
        for key in ("error", "base_cycle_error"):
            if node.get(key):
                findings.append({
                    "path": path + "." + key,
                    "phase": phase_name,
                    "status": key,
                    "error": node.get(key),
                    "core": not _is_non_core(phase_name if phase_name else path),
                })
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                _walk(value, path + "." + str(key), findings)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk(item, path + "[%d]" % index, findings)


def summarize_cycle_result(result: Any) -> Dict[str, Any]:
    """Recursively scan a cycle() result and classify the overall outcome."""
    findings: List[Dict[str, Any]] = []
    _walk(result, "cycle", findings)
    core_failures = [f for f in findings if f["core"]]
    warnings = [f for f in findings if not f["core"]]
    if core_failures:
        cycle_status = "failed"
    elif warnings:
        cycle_status = "degraded"
    else:
        cycle_status = "ok"
    return {
        "cycle_status": cycle_status,
        "fatal_errors": core_failures,
        "warnings": warnings,
    }


def selftest() -> Dict[str, Any]:
    ok_result = {"phase": "cooperative_core_neuromodulator_sleep_authority", "status": "complete",
                 "downstream_result": {"phase": "phase7cort_stability_watch_release", "status": "ok"}}
    summary_ok = summarize_cycle_result(ok_result)
    assert summary_ok["cycle_status"] == "ok", summary_ok

    degraded_result = {"phase": "stageb_gapflow_runtime_contract_release", "status": "ok",
                        "shadow_recheck": {"phase": "non_productive_recheck_shadow_runtime_registration_v1",
                                            "status": "error", "error": "no candidates"}}
    summary_degraded = summarize_cycle_result(degraded_result)
    assert summary_degraded["cycle_status"] == "degraded", summary_degraded

    failed_result = {"phase": "phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
                      "wake_result": {"base_cycle_error": "no such column: gap_type"},
                      "sleep_replay": {"status": "phase6a_sleep_replay_error", "error": "no such column: gap_type",
                                        "phase": "phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release"}}
    summary_failed = summarize_cycle_result(failed_result)
    assert summary_failed["cycle_status"] == "failed", summary_failed
    return {"status": "ok", "ok": summary_ok, "degraded": summary_degraded, "failed": summary_failed}
