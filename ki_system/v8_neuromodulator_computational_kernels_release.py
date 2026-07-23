# -*- coding: utf-8 -*-
"""Pure, deterministic neuromodulator computational kernels.

This module performs no SQLite access, no file I/O, no logging, no runtime
registration, and no state mutation. Runtime cutover is intentionally not part
of V1. V1 establishes an importable shadow/parity contract first.
"""
from __future__ import annotations
from typing import Any, Dict, Mapping

KERNEL_VERSION = "neuromodulator_computational_kernels_v1"
ALL12 = (
    "dopamine", "serotonin", "glutamate", "gaba", "noradrenaline",
    "acetylcholine", "endocannabinoids", "histamine", "orexin", "bdnf",
    "cortisol", "adenosine",
)

def clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        x = float(value)
    except Exception:
        x = 0.0
    return lo if x < lo else hi if x > hi else x


def compute_ei_balance(glutamate_drive: float, gaba_drive: float,
                       gamma: float = 0.15, alpha: float = 0.12) -> Dict[str, float]:
    glu_pre = clamp(glutamate_drive)
    gaba_pre = clamp(gaba_drive)
    glu_post = clamp(glu_pre - float(gamma) * gaba_pre)
    gaba_post = clamp(gaba_pre + float(alpha) * glu_pre)
    return {
        "glu_pre": glu_pre, "gaba_pre": gaba_pre,
        "gamma": float(gamma), "alpha": float(alpha),
        "glu_post": glu_post, "gaba_post": gaba_post,
    }


def compute_phase6b_plasticity_adjustment(
    pre: Mapping[str, float], neuromod: Mapping[str, float],
    effectiveness_score: float, plateau_flag: bool,
    cfg: Mapping[str, float], evidence_allows_state_change: bool = False,
) -> Dict[str, Any]:
    """Pure mirror of the currently evidenced Phase-6b adjustment formulas.

    It returns a recommendation only. V1 never applies it.
    """
    da = clamp(neuromod.get("dopamine", 0.5))
    se = clamp(neuromod.get("serotonin", 0.5))
    na = clamp(neuromod.get("noradrenaline", 0.5))
    ach = clamp(neuromod.get("acetylcholine", 0.5))
    glu = clamp(neuromod.get("glutamate", 0.5))
    gaba = clamp(neuromod.get("gaba", 0.3))
    score = clamp(effectiveness_score)
    out = {
        "plasticity_level": clamp(pre.get("plasticity_level", 0.5)),
        "exploration_bias": clamp(pre.get("exploration_bias", 0.5)),
        "consolidation_bias": clamp(pre.get("consolidation_bias", 0.5)),
        "inhibition_bias": clamp(pre.get("inhibition_bias", 0.5)),
        "revision_bias": clamp(pre.get("revision_bias", 0.5)),
    }
    adjustment = "hold"
    reasons = []
    scale = 1.0
    if plateau_flag:
        adjustment = "plateau_break"
        scale = clamp(float(cfg.get("plateau_break_scale", 0.85)) - 0.10 * gaba, 0.55, 0.98)
        out["plasticity_level"] = clamp(out["plasticity_level"] * scale)
        out["exploration_bias"] = clamp(out["exploration_bias"] + float(cfg.get("exploration_delta", 0.15)) * (1.0 - gaba) + 0.05 * na)
        out["inhibition_bias"] = clamp(out["inhibition_bias"] + float(cfg.get("inhibition_delta", 0.10)) * gaba + 0.05 * (1.0 - da))
        out["revision_bias"] = clamp(out["revision_bias"] + float(cfg.get("revision_delta", 0.10)) * se + 0.05 * ach)
        out["consolidation_bias"] = clamp(out["consolidation_bias"] - 0.05 * (1.0 - score))
        reasons.append("plateau_break_canonical")
    elif score > 0.0:
        adjustment = "stabilize_gains"
        out["consolidation_bias"] = clamp(out["consolidation_bias"] + float(cfg.get("consolidation_delta", 0.05)) * da + 0.05 * glu)
        out["revision_bias"] = clamp(out["revision_bias"] - 0.03 * se)
        out["plasticity_level"] = clamp(out["plasticity_level"] + 0.02 * da)
        reasons.append("stabilize_positive_effectiveness")
    return {
        "adjustment_type": adjustment,
        "scale_factor": scale,
        "recommended": out,
        "reasons": reasons,
        "state_change_allowed": bool(evidence_allows_state_change),
        "applied": False,
    }


def compute_2ag_release(current_2ag: float, max_delta: float,
                        dopamine: float, gaba: float,
                        release_gain: float = 5.0) -> Dict[str, float]:
    release = clamp(float(max_delta) * float(release_gain) * (0.5 + clamp(dopamine)) * (1.0 - 0.4 * clamp(gaba)), 0.0, 0.6)
    return {"released": release, "new_2ag": clamp(float(current_2ag) + release)}


def compute_2ag_decay(current_2ag: float, decay_rate: float = 0.6) -> float:
    return clamp(float(current_2ag) * float(decay_rate))


def compute_anandamide_level(current: float, extreme_score: float,
                              alpha: float = 0.10, maximum: float = 0.85) -> Dict[str, float]:
    target = clamp(float(extreme_score) * 2.0 * float(maximum), 0.0, float(maximum))
    level = clamp((1.0 - float(alpha)) * float(current) + float(alpha) * target)
    return {"target": target, "anandamide": level}


def compute_anandamide_ltd_value(value: float, midpoint: float,
                                  anandamide_level: float, serotonin: float,
                                  baseline: float = 0.1,
                                  pull_strength: float = 0.10,
                                  extreme_threshold: float = 0.35) -> Dict[str, Any]:
    if float(anandamide_level) <= float(baseline):
        return {"eligible": False, "reason": "anandamide_below_baseline", "value": clamp(value), "effective_pull": 0.0}
    if abs(float(value) - float(midpoint)) < float(extreme_threshold):
        return {"eligible": False, "reason": "bias_not_extreme", "value": clamp(value), "effective_pull": 0.0}
    effective_pull = clamp(float(pull_strength) * (float(anandamide_level) - float(baseline)) * 4.0, 0.0, 0.3)
    new_value = clamp(float(value) + (float(midpoint) - float(value)) * effective_pull * (1.0 - 0.3 * clamp(serotonin)))
    return {"eligible": True, "reason": "tonic_extreme_bias", "value": new_value, "effective_pull": effective_pull}


def compute_bdnf_state(consolidation_consistency: float, marginal_progress: float,
                       activity_level: float, previous_level: float,
                       progress_gain: float = 2.0,
                       consolidation_weight: float = 0.45,
                       progress_weight: float = 0.35,
                       activity_weight: float = 0.20,
                       ewma_alpha: float = 0.30,
                       growth_gate: float = 0.60,
                       low_gate: float = 0.35) -> Dict[str, Any]:
    progress_norm = clamp(0.5 + float(marginal_progress) * float(progress_gain))
    wc, wp, wa = float(consolidation_weight), float(progress_weight), float(activity_weight)
    total = wc + wp + wa
    if total <= 0.0:
        wc, wp, wa, total = 0.45, 0.35, 0.20, 1.0
    target = clamp((wc / total) * clamp(consolidation_consistency) + (wp / total) * progress_norm + (wa / total) * clamp(activity_level))
    level = clamp((1.0 - float(ewma_alpha)) * clamp(previous_level) + float(ewma_alpha) * target)
    if level >= float(growth_gate) and progress_norm >= 0.58:
        regime = "growth"
    elif clamp(activity_level) <= 0.30 and progress_norm <= 0.52:
        regime = "low_plasticity"
    else:
        regime = "maintenance"
    return {"progress_norm": progress_norm, "bdnf_target": target, "bdnf_level": level, "regime": regime}


def validate_all12_snapshot(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    missing = [name for name in ALL12 if name not in snapshot]
    values = {name: clamp(snapshot.get(name, 0.0)) for name in ALL12 if name in snapshot}
    return {"complete": not missing, "missing": missing, "values": values}


def selftest() -> Dict[str, Any]:
    ei = compute_ei_balance(0.575, 0.32, 0.15, 0.12)
    assert abs(ei["glu_post"] - 0.527) < 1e-12
    assert abs(ei["gaba_post"] - 0.389) < 1e-12
    ag = compute_2ag_release(0.1, 0.2, 0.25, 0.389)
    assert ag["new_2ag"] >= 0.1
    b = compute_bdnf_state(0.7, 0.02, 0.44, 0.65)
    assert 0.0 <= b["bdnf_level"] <= 1.0
    p = compute_phase6b_plasticity_adjustment(
        {"plasticity_level": 0.78, "exploration_bias": 0.5, "consolidation_bias": 0.1, "inhibition_bias": 0.2, "revision_bias": 0.8},
        {"dopamine": 0.25, "serotonin": 0.2885, "noradrenaline": 0.7, "acetylcholine": 0.7625, "glutamate": 0.527, "gaba": 0.389},
        0.0, True, {}, False,
    )
    assert p["applied"] is False and p["state_change_allowed"] is False
    return {"status": "ok", "kernel_version": KERNEL_VERSION, "ei": ei, "phase6b_applied": p["applied"]}
