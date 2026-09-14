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
    # BRAINSTEM_DIAGNOSTICS_ERROR_KEY_COVERAGE_FIX_V1: "phase5g_error" is a
    # real status value already produced by
    # v8_phase5g_context_strategy_selection_and_experiment_memory_release.py
    # (managed_cycle/managed_run) but was missing from this set. It was
    # previously only caught incidentally because those specific call sites
    # also happen to include a separate "error" key in the same dict (see
    # the generic key-based scan below) -- adding it here explicitly closes
    # that coincidental dependency for any future variant that might set
    # this status without also including a bare "error" key.
    "phase5g_error",
}

# BRAINSTEM_DIAGNOSTICS_ERROR_KEY_COVERAGE_FIX_V1 (continued)
#
# Root cause (confirmed by a project-wide grep across all ~68 modules):
# _walk() previously only checked a fixed pair of generic keys, "error" and
# "base_cycle_error", for a truthy value. At least two real, existing
# failure dicts elsewhere in this codebase use neither of those two keys
# nor a recognized "status" value, and were therefore completely invisible
# to this diagnostics module:
#   - v8_phase5f_context_expansion_effectiveness_and_adaptive_windowing_
#     release.py: except Exception as e: base={'phase5e_error': repr(e)}
#   - v8_phase5h_strategy_experiment_outcome_learning_release.py:
#     except Exception as exc: result = {'phase5g_cycle_error': str(exc)}
# Both dicts carry ONLY their own ad hoc "<phaseName>_error" key, with no
# "status" field and no "error"/"base_cycle_error" key at all -- so a real,
# uncaught exception in either of those upstream phases could silently
# vanish from cycle diagnostics entirely, exactly the failure mode this
# module exists to prevent.
#
# Fix: generalize the generic-key scan from a fixed 2-item tuple to a rule
# matching the key "error" exactly OR any key ending in the "_error" suffix.
# This was verified (via a project-wide grep of all dict-literal key names
# containing "error"/"exception"/"fail") to correctly include every
# existing ad hoc failure key in this codebase (error, base_cycle_error,
# phase5e_error, phase5g_cycle_error) while correctly EXCLUDING unrelated
# data fields that merely contain "error" as a substring, not a "_error"
# suffix (error_weight, errors, hypothesis_error_events,
# last_projection_errors, projection_errors) -- none of those describe a
# cycle failure and must not be misclassified as one.
def _is_error_key(key: str) -> bool:
    return key == "error" or key.endswith("_error")

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
        for key in list(node.keys()):
            if _is_error_key(key) and node.get(key):
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
