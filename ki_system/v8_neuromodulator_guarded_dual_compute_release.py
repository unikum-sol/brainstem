from __future__ import annotations

import math
from typing import Any, Mapping

GUARD_VERSION = "neuromodulator_guarded_old_authoritative_dual_compute_v1"
ABS_TOLERANCE = 1e-12
REL_TOLERANCE = 1e-12


def _numeric_equal(old: Any, kernel: Any) -> bool:
    if isinstance(old, bool) or isinstance(kernel, bool):
        return old is kernel
    if isinstance(old, (int, float)) and isinstance(kernel, (int, float)):
        return math.isclose(float(old), float(kernel), rel_tol=REL_TOLERANCE, abs_tol=ABS_TOLERANCE)
    return old == kernel


def compare_scalar(kernel_name: str, field: str, old_value: Any, kernel_value: Any) -> None:
    if not _numeric_equal(old_value, kernel_value):
        raise RuntimeError(
            "NEUROMOD_KERNEL_GUARD_MISMATCH " + kernel_name + "." + field
            + " old=" + repr(old_value) + " kernel=" + repr(kernel_value)
        )


def compare_mapping(kernel_name: str, old_values: Mapping[str, Any], kernel_values: Mapping[str, Any]) -> None:
    missing = [key for key in old_values if key not in kernel_values]
    if missing:
        raise RuntimeError(
            "NEUROMOD_KERNEL_GUARD_MISMATCH " + kernel_name
            + " missing_kernel_fields=" + repr(sorted(missing))
        )
    for key, old_value in old_values.items():
        compare_scalar(kernel_name, key, old_value, kernel_values[key])


def selftest() -> dict[str, Any]:
    compare_scalar("selftest", "x", 0.3, 0.1 + 0.2)
    compare_mapping("selftest", {"a": 1.0, "b": "hold"}, {"a": 1.0, "b": "hold"})
    mismatch_detected = False
    try:
        compare_scalar("selftest", "x", 1.0, 2.0)
    except RuntimeError:
        mismatch_detected = True
    if not mismatch_detected:
        raise AssertionError("guard mismatch selftest failed")
    return {
        "status": "ok",
        "guard_version": GUARD_VERSION,
        "old_output_authoritative": True,
        "kernel_result_applied": False,
        "mismatch_is_fail_closed": True,
    }
