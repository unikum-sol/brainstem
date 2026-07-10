"""V8 Phase4 Schema Manager Memory Alias Fix FIXED1."""
from __future__ import annotations

PHASE = "phase4_schema_manager_mem_alias_fix_fixed1"


def _get_loop_memory(loop):
    for name in ("mem", "memory", "m", "store", "memory_store"):
        obj = getattr(loop, name, None)
        if obj is not None:
            return obj
    for name, obj in getattr(loop, "__dict__", {}).items():
        if obj is None:
            continue
        if hasattr(obj, "db") or hasattr(obj, "execute"):
            return obj
    raise AttributeError(
        "AutonomousLoop memory object not found. "
        f"Available attributes: {sorted(getattr(loop, '__dict__', {}).keys())}"
    )


def _ensure_schema_for_loop(loop):
    from ki_system.v8_phase4_schema_manager_canonicalization import ensure_phase4_schema
    mem = _get_loop_memory(loop)
    ensure_phase4_schema(mem)
    return mem


def managed_cycle(self, progress=None):
    _ensure_schema_for_loop(self)
    import ki_system.v8_phase4def_context_learning_pack as phase4def
    return phase4def.safe_cycle(self, progress)


def managed_run(self, cycles=1, progress=None):
    _ensure_schema_for_loop(self)
    import ki_system.v8_phase4def_context_learning_pack as phase4def
    return phase4def.safe_run(self, cycles, progress)


def patch_autonomous_loop(*args, **kwargs):
    from ki_system.autonomous import AutonomousLoop
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    marker_values = {
        "phase4_schema_manager_canonicalization": True,
        "phase4_schema_manager_mem_alias_fix_fixed1": True,
        "phase4d_hypothesis_feedback_error_learning": True,
        "phase4e_neuromodulated_attention_strategy": True,
        "phase4f_sleep_consolidation_self_improvement": True,
        "phase4def_context_learning_pack": True,
        "no_word_blacklists": True,
        "learning_mode": "context_hypotheses_with_neuromodulators",
        "rollback_learning_mode": "context_hypotheses_with_neuromodulators",
        "fact_promotion": "disabled",
    }
    for key, val in marker_values.items():
        setattr(AutonomousLoop, key, val)
        setattr(AutonomousLoop, "_" + key, val)
    return AutonomousLoop

try:
    patch_autonomous_loop()
except Exception as exc:
    print("[PHASE4_SCHEMA_MANAGER_MEM_ALIAS_FIX_FIXED1_AUTOLOAD_ERROR]", exc)
