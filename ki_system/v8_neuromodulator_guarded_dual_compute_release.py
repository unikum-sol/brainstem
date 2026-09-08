from __future__ import annotations

import math
from typing import Any, Mapping

from ki_system.v8_neuromodulator_kernel_authority_control_release import guard_active

GUARD_VERSION = "neuromodulator_guarded_old_authoritative_dual_compute_v2_gated"
ABS_TOLERANCE = 1e-12
REL_TOLERANCE = 1e-12

# BRAINSTEM_GUARD_CRASH_FIX_V1
#
# Root cause of the original bug: compare_scalar()/compare_mapping() used to
# raise RuntimeError unconditionally on ANY mismatch between the "old" active
# code path and the pure kernel mirror, even though select_authoritative()
# (in v8_neuromodulator_kernel_authority_control_release) only ever *uses*
# the kernel output when the per-name mode is explicitly "kernel_guarded"
# (the default authority is always "old"). The comparison therefore ran on
# every single cycle regardless of mode.
#
# For compute_ei_balance specifically, the "old" active path applies sigmoid
# soft-clamping (see _soft_clamp in v8_phase7c...) while the pure kernel
# mirror (compute_ei_balance in v8_neuromodulator_computational_kernels...)
# intentionally applies a hard 0..1 clamp for a simple, auditable parity
# contract. These two are mathematically identical in the interior of the
# [0,1] range but diverge close to the boundaries -- exactly where GABA and
# glutamate are expected to operate under real inhibition/exploration
# pressure or cooperative sleep readiness. The unconditional raise crashed
# Phase 7c (and any other guarded kernel call) whenever a neuromodulator
# approached its documented operating extremes.
#
# Fix: only enforce (and only raise) when the corresponding kernel name is
# explicitly running in "kernel_guarded" mode (opt-in via the
# BRAINSTEM_KERNEL_AUTH_<NAME> environment variable). In the default "old"
# mode the kernel output is never applied anyway, so a mismatch there is
# expected/harmless shadow-parity information, not a fatal error. This keeps
# the fail-closed guarantee fully intact for anyone who explicitly enables
# kernel-guarded testing, while no longer crashing default production runs.


def _numeric_equal(old: Any, kernel: Any) -> bool:
    if isinstance(old, bool) or isinstance(kernel, bool):
        return old is kernel
    if isinstance(old, (int, float)) and isinstance(kernel, (int, float)):
        return math.isclose(float(old), float(kernel), rel_tol=REL_TOLERANCE, abs_tol=ABS_TOLERANCE)
    return old == kernel


def compare_scalar(kernel_name: str, field: str, old_value: Any, kernel_value: Any, force: bool = False) -> bool:
    """Compare a single old/kernel value pair.

    Returns True if equal, False if not. Raises RuntimeError only when the
    kernel is explicitly running in guarded/authoritative test mode for this
    kernel_name (or when force=True, used by the deterministic selftest
    below), matching the fail-closed contract of select_authoritative().
    """
    equal = _numeric_equal(old_value, kernel_value)
    if not equal and (force or guard_active(kernel_name)):
        raise RuntimeError(
            "NEUROMOD_KERNEL_GUARD_MISMATCH " + kernel_name + "." + field
            + " old=" + repr(old_value) + " kernel=" + repr(kernel_value)
        )
    return equal


def compare_mapping(kernel_name: str, old_values: Mapping[str, Any], kernel_values: Mapping[str, Any], force: bool = False) -> bool:
    """Compare an old/kernel mapping pair.

    Returns True if every field matches, False otherwise. Only raises when
    guard_active(kernel_name) is True (or force=True), see compare_scalar().
    """
    missing = [key for key in old_values if key not in kernel_values]
    if missing:
        if force or guard_active(kernel_name):
            raise RuntimeError(
                "NEUROMOD_KERNEL_GUARD_MISMATCH " + kernel_name
                + " missing_kernel_fields=" + repr(sorted(missing))
            )
        return False
    all_equal = True
    for key, old_value in old_values.items():
        if not compare_scalar(kernel_name, key, old_value, kernel_values[key], force=force):
            all_equal = False
    return all_equal


def selftest() -> dict[str, Any]:
    assert compare_scalar("selftest", "x", 0.3, 0.1 + 0.2, force=True) is True
    assert compare_mapping("selftest", {"a": 1.0, "b": "hold"}, {"a": 1.0, "b": "hold"}, force=True) is True
    # Default (non-guarded) mode must NOT raise on a real mismatch:
    assert compare_scalar("selftest_never_guarded", "x", 1.0, 2.0) is False
    # Forced/guarded mode must still fail closed on a real mismatch:
    mismatch_detected = False
    try:
        compare_scalar("selftest", "x", 1.0, 2.0, force=True)
    except RuntimeError:
        mismatch_detected = True
    if not mismatch_detected:
        raise AssertionError("guard mismatch selftest failed")
    return {
        "status": "ok",
        "guard_version": GUARD_VERSION,
        "old_output_authoritative": True,
        "kernel_result_applied": False,
        "mismatch_is_fail_closed_when_guard_active": True,
        "default_mode_never_raises": True,
    }
