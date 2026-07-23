from __future__ import annotations

import hashlib
import importlib
import importlib.util
import math
from pathlib import Path
from typing import Any

VERSION = "modern_projection_contract_consolidation_v1"
LEGACY_MODULE = "ki_system.v8_phase5f_context_expansion_effectiveness_and_adaptive_windowing_release"


def clamp(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return max(0.0, min(1.0, number))


def contract_source_hash() -> str:
    spec = importlib.util.find_spec(LEGACY_MODULE)
    if spec is None or not spec.origin:
        raise RuntimeError("legacy Phase-5f source module not found")
    return hashlib.sha256(Path(spec.origin).read_bytes()).hexdigest()


def _legacy_helpers():
    module = importlib.import_module(LEGACY_MODULE)
    required = (
        "center_chunk",
        "closure_stats",
        "neighbors",
        "chunk_status",
        "neuromod",
        "table",
        "clamp",
    )
    missing = [name for name in required if not callable(getattr(module, name, None))]
    if missing:
        raise RuntimeError("missing legacy read helpers: " + ",".join(missing))
    return module


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return number if math.isfinite(number) else float(default)


def _strategy(no_rate: float, overlap: float, delta: float, old_radius: int) -> tuple[str, int, str, str]:
    if no_rate > 0.38:
        return "shift_away_from_no_candidate_context", max(2, old_radius - 1), "reduce_no_candidate_window", "no_candidate_pressure"
    if overlap > 0.55:
        return "low_overlap_context_window", min(9, old_radius + 2), "reduce_overlap", "overlap_pressure"
    if delta < 0.08:
        return "wider_context_window", min(9, old_radius + 2), "increase_window", "low_closure_delta"
    if delta < 0.16:
        return "contrastive_context_window", min(7, old_radius + 1), "try_contrastive_window", "medium_closure_delta"
    return "reinforce_effective_window", old_radius, "reinforce", "effective_window"


def _count_overlap(cur: Any, helpers: Any, targets: list[int]) -> float:
    if not targets or not helpers.table(cur, "phase5f_context_window_experiments"):
        return 0.0
    placeholders = ",".join("?" for _ in targets)
    previous = cur.execute(
        "SELECT COUNT(*) FROM phase5f_context_window_experiments WHERE target_chunk_id IN (" + placeholders + ")",
        tuple(targets),
    ).fetchone()[0]
    return helpers.clamp(previous / max(1, len(targets) * 5))


def _evaluate_with_helpers(con: Any, row: dict[str, Any], source_hash: str, helpers: Any) -> dict[str, Any]:
    key_material = "|".join(
        [
            VERSION,
            str(row.get("shadow_key") or ""),
            str(row.get("hypothesis_id") or ""),
            str(row.get("updated_at") or 0),
            str(source_hash),
        ]
    )
    key = "shadow-phase5f-observation:" + hashlib.sha256(key_material.encode("utf-8")).hexdigest()
    gap = {
        "id": None,
        "gap_key": key,
        "gap_type": "shadow_projection_only",
        "role": row.get("role") or "unknown_role",
        "hypothesis_id": row.get("hypothesis_id"),
        "chunk_id": row.get("chunk_id"),
        "phase5f_window_radius": None,
        "phase5f_window_strategy": None,
        "phase5e_expected_gain": None,
        "strategy_effectiveness_score": None,
    }
    cur = con.cursor()
    nm = helpers.neuromod(cur)
    if not isinstance(nm, dict):
        nm = {}
    center = helpers.center_chunk(cur, gap)
    delta, expected_gain = helpers.closure_stats(cur, key)
    delta = _safe_float(delta, 0.0)
    expected_gain = _safe_float(gap.get("phase5e_expected_gain") or expected_gain or 0.5, 0.5)
    old_radius = _safe_int(gap.get("phase5f_window_radius") or 3, 3)
    old_strategy = gap.get("phase5f_window_strategy") or "near_context_window"

    preliminary = list(helpers.neighbors(cur, center, old_radius, old_strategy) or [])
    status = helpers.chunk_status(cur, preliminary) or {}
    no_rate = sum(1 for value in status.values() if value == "read_no_candidate") / max(1, len(preliminary))
    overlap = _count_overlap(cur, helpers, preliminary)

    new_strategy, new_radius, action, branch = _strategy(no_rate, overlap, delta, old_radius)
    inhibition = _safe_float(nm.get("inhibition_level"), 0.0)
    exploration = _safe_float(nm.get("exploration_pressure"), 0.0)
    if inhibition > 0.42:
        new_radius = min(new_radius, old_radius + 1)
    if exploration > 0.34:
        new_radius = min(10, new_radius + 1)

    targets = list(helpers.neighbors(cur, center, new_radius, new_strategy) or [])
    status = helpers.chunk_status(cur, targets) or {}
    no_rate = sum(1 for value in status.values() if value == "read_no_candidate") / max(1, len(targets))
    overlap = _count_overlap(cur, helpers, targets) if targets else overlap
    effectiveness = helpers.clamp(
        0.45 * delta
        + 0.25 * (1 - no_rate)
        + 0.2 * (1 - overlap)
        + 0.1 * _safe_float(gap.get("strategy_effectiveness_score") or 0, 0.0)
    )

    return {
        "observation_key": key,
        "shadow_key": row.get("shadow_key"),
        "hypothesis_id": _safe_int(row.get("hypothesis_id") or 0),
        "source_updated_at": _safe_int(row.get("updated_at") or 0),
        "center_chunk_id": center,
        "target_chunk_ids": targets,
        "target_count": len(targets),
        "projected_window_strategy": new_strategy,
        "projected_window_radius": new_radius,
        "projected_action": action,
        "expected_gain": expected_gain,
        "closure_delta": delta,
        "overlap_score": overlap,
        "read_no_candidate_rate": no_rate,
        "projected_effectiveness": effectiveness,
        "neuromodulators": nm,
        "real_outcome_observation_available": 0,
        "observation_ready": 0,
        "source_default_path": 1,
        "productive_gap_id": None,
        "productive_write": 0,
        "details": {
            "version": VERSION,
            "candidate_state": row.get("candidate_state"),
            "bridge_mode": row.get("bridge_mode"),
            "source_hash": source_hash,
            "projection_branch": branch,
            "contract": "read_only_parity_preserving_extraction",
            "productive_writes": 0,
        },
    }


def evaluate_projection(con: Any, row: dict[str, Any], source_hash: str | None = None) -> dict[str, Any]:
    if source_hash is None:
        source_hash = contract_source_hash()
    return _evaluate_with_helpers(con, row, source_hash, _legacy_helpers())


def selftest() -> dict[str, Any]:
    cases = {
        "no_candidate": _strategy(0.5, 0.0, 0.0, 3),
        "overlap": _strategy(0.0, 0.7, 0.0, 3),
        "low_delta": _strategy(0.0, 0.0, 0.0, 3),
        "medium_delta": _strategy(0.0, 0.0, 0.1, 3),
        "effective": _strategy(0.0, 0.0, 0.2, 3),
    }
    expected = {
        "no_candidate": "shift_away_from_no_candidate_context",
        "overlap": "low_overlap_context_window",
        "low_delta": "wider_context_window",
        "medium_delta": "contrastive_context_window",
        "effective": "reinforce_effective_window",
    }
    for name, outcome in cases.items():
        if outcome[0] != expected[name]:
            raise RuntimeError("strategy selftest failed: " + name)
    if abs(clamp(0.45) - 0.45) > 1e-12 or clamp(float("inf")) != 0.0:
        raise RuntimeError("clamp selftest failed")
    return {"status": "ok", "cases": {name: value[0] for name, value in cases.items()}}
