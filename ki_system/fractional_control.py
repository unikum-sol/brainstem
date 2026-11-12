"""Deterministic bounded error diffusion for discrete engineering controls.

This is numerical implementation, not a claim of a biological mechanism.
No random decisions, data deletion, or unbounded token banking.
"""
import math


def finite(value, default):
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    return result if math.isfinite(result) else float(default)


def fractional_integer(target, remainder=0.0, minimum=0):
    """Track a fractional target with cumulative error below one unit.

    Integral targets reset the remainder, preserving exact neutral behavior.
    Only a fractional remainder survives; unused whole allocations never bank.
    """
    target = max(float(minimum), finite(target, minimum))
    remainder = min(1.0 - 1e-12, max(0.0, finite(remainder, 0.0)))
    lower = math.floor(target)
    fraction = target - lower
    if fraction < 1e-12:
        return max(minimum, lower), 0.0
    total = fraction + remainder
    extra = 1 if total >= 1.0 - 1e-12 else 0
    next_remainder = max(0.0, min(1.0 - 1e-12, total - extra))
    return max(minimum, lower + extra), next_remainder
