# -*- coding: utf-8 -*-
"""V8 Phase 7b1 - Wake Chain Bridge Fix.

Restores original wake+sleep chain that was severed by later phases.
Every AutonomousLoop.cycle() now runs in strict order:
  1. 6a.managed_cycle -> real wake+sleep (produces context_hypotheses)
  2. 6b/6c/6d/7a/7b run_*_cycle -> homeostasis regulators
No schema changes, no DB writes from this file.
"""
from __future__ import annotations
import os, sqlite3
from pathlib import Path
from typing import Any

PHASE = "phase7b1_wake_chain_bridge_release"
PHASE_VERSION = "phase7b1_v1"

def resolve_db(obj: Any = None):
    if obj is None:
        path = "ki_memory.sqlite3"
        if not os.path.exists(path):
            here = Path(__file__).resolve().parent.parent
            cand = here / "ki_memory.sqlite3"
            if cand.exists(): path = str(cand)
        con = sqlite3.connect(path, timeout=30.0)
        con.row_factory = sqlite3.Row
        return con
    if isinstance(obj, sqlite3.Connection):
        obj.row_factory = sqlite3.Row
        return obj
    for attr in ("db","connection","conn","memory"):
        inner = getattr(obj, attr, None)
        if inner is None: continue
        if isinstance(inner, sqlite3.Connection):
            inner.row_factory = sqlite3.Row
            return inner
        inner2 = getattr(inner, "db", None) or getattr(inner, "connection", None)
        if isinstance(inner2, sqlite3.Connection):
            inner2.row_factory = sqlite3.Row
            return inner2
    return resolve_db(None)

def _call_module_run(mod_name, run_fn_name, db):
    try:
        m = __import__("ki_system." + mod_name, fromlist=[run_fn_name])
    except ImportError:
        return {"skipped": True, "reason": "not_installed", "module": mod_name}
    except Exception as exc:
        return {"error": "import_error: " + str(exc), "module": mod_name}
    fn = getattr(m, run_fn_name, None)
    if fn is None:
        return {"skipped": True, "reason": "no_" + run_fn_name, "module": mod_name}
    try:
        return fn(db)
    except Exception as exc:
        return {"error": str(exc), "module": mod_name, "step": run_fn_name}

def _call_module_managed_cycle(mod_name, self_obj, progress):
    try:
        m = __import__("ki_system." + mod_name, fromlist=["managed_cycle"])
    except ImportError:
        return {"skipped": True, "reason": "not_installed", "module": mod_name}
    except Exception as exc:
        return {"error": "import_error: " + str(exc), "module": mod_name}
    fn = getattr(m, "managed_cycle", None)
    if fn is None:
        return {"skipped": True, "reason": "no_managed_cycle", "module": mod_name}
    if fn is managed_cycle:
        return {"skipped": True, "reason": "would_recurse", "module": mod_name}
    try:
        return fn(self_obj, progress)
    except Exception as exc:
        return {"error": str(exc), "module": mod_name, "step": "managed_cycle"}

def managed_cycle(self, progress=None):
    results = {"phase": PHASE, "chain": []}
    wake_sleep = _call_module_managed_cycle(
        "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
        self, progress)
    results["chain"].append({"step": "wake_sleep_6a", "result": wake_sleep})
    try:
        db = resolve_db(self)
    except Exception as exc:
        results["db_resolve_error"] = str(exc)
        return results
    for mod_name, run_fn_name, step_name in (
        ("v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release",
         "run_phase6b_cycle", "phase6b_effectiveness"),
        ("v8_phase6c_bias_persistence_and_self_regulating_meta_release",
         "run_phase6c_cycle", "phase6c_bias_persistence"),
        ("v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release",
         "run_phase6d_cycle", "phase6d_saturation"),
        ("v8_phase7a_adenosine_homeostat_release",
         "run_phase7a_cycle", "phase7a_adenosine"),
        ("v8_phase7b_endocannabinoid_retrograde_gain_control_release",
         "run_phase7b_cycle", "phase7b_endocannabinoids"),
    ):
        r = _call_module_run(mod_name, run_fn_name, db)
        results["chain"].append({"step": step_name, "result": r})
    return results

def managed_run(self, cycles=1, progress=None):
    results = []
    try: cycles = int(cycles or 1)
    except Exception: cycles = 1
    for _ in range(max(1, cycles)):
        results.append(managed_cycle(self, progress))
    return {"phase": PHASE, "cycles": len(results), "results": results}

def autoload(AutonomousLoop):
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.phase7b1_wake_chain_bridge_release = True
    AutonomousLoop._phase7b1_wake_chain_bridge_release = True
    AutonomousLoop.wake_chain_bridge = True
    for flag in ("phase7b_endocannabinoid_retrograde_gain_control_release",
                 "phase7a_adenosine_homeostat_release",
                 "phase6d_saturation_homeostasis_and_meta_metaplasticity_release",
                 "phase6c_bias_persistence_and_self_regulating_meta_release",
                 "phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release",
                 "phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release",
                 "no_word_blacklists","self_regulating_meta_parameters",
                 "saturation_homeostasis","meta_metaplasticity",
                 "adenosine_homeostat","endocannabinoid_retrograde_gain_control"):
        if not hasattr(AutonomousLoop, flag):
            setattr(AutonomousLoop, flag, True)
    AutonomousLoop.learning_mode = "context_hypotheses_with_neuromodulators"
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"
    AutonomousLoop.direct_relation_writes = "disabled"
    return AutonomousLoop
