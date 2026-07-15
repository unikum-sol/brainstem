# -*- coding: utf-8 -*-
"""BrainStem central phase/patch registry."""
import importlib

PKG = "ki_system"

LOAD_ORDER = [{'module': 'v8_context_observation_learning_release',
  'how': 'patch_autonomous_loop',
  'target': 'LOOP',
  'label': 'CONTEXT_OBSERVATION_LEARNING',
  'post_flags': {'context_observation_learning_release': True,
                 'no_word_blacklists': True,
                 'learning_mode': 'context_hypotheses_with_neuromodulators',
                 'fact_promotion': 'disabled',
                 'direct_fact_writes': 'disabled',
                 'direct_relation_writes': 'disabled'}},
 {'module': 'v8_phase5a_integrated_self_improving_learning_release',
  'how': 'patch_autonomous_loop',
  'target': 'LOOP',
  'label': 'PHASE5A'},
 {'module': 'v8_phase5b_integrated_strategy_refinement_release',
  'how': 'patch_autonomous_loop',
  'target': 'NONE',
  'label': 'PHASE5B'},
 {'module': 'v8_phase5c_learning_outcome_closure_and_question_cluster_resolution',
  'how': 'patch_autonomous_loop',
  'target': 'LOOP',
  'label': 'PHASE5C'},
 {'module': 'v8_phase5d_integrated_observation_and_strategy_memory_release',
  'how': 'patch_autonomous_loop',
  'target': 'LOOP',
  'label': 'PHASE5D'},
 {'module': 'v8_phase5e_context_expansion_and_gap_closure_release',
  'how': 'patch_autonomous_loop',
  'target': 'NONE',
  'label': 'PHASE5E'},
 {'module': 'v8_phase5f_context_expansion_effectiveness_and_adaptive_windowing_release',
  'how': 'patch_autonomous_loop',
  'target': 'LOOP',
  'label': 'PHASE5F'},
 {'module': 'v8_phase5g_context_strategy_selection_and_experiment_memory_release',
  'how': 'patch_autonomous_loop',
  'target': 'LOOP',
  'label': 'PHASE5G'},
 {'module': 'v8_phase5h_strategy_experiment_outcome_learning_release',
  'how': 'patch_autonomous_loop',
  'target': 'LOOP',
  'label': 'PHASE5H'},
 {'module': 'v8_phase5i_outcome_driven_context_strategy_diversification_release',
  'how': 'patch_autonomous_loop',
  'target': 'NONE',
  'label': 'PHASE5I'},
 {'module': 'v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'PHASE6A'},
 {'module': 'v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'PHASE6B'},
 {'module': 'v8_phase6c_bias_persistence_and_self_regulating_meta_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'PHASE6C'},
 {'module': 'v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'PHASE6D'},
 {'module': 'v8_phase7a_adenosine_homeostat_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7A'},
 {'module': 'v8_phase7b_endocannabinoid_retrograde_gain_control_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'PHASE7B'},
 {'module': 'v8_phase7b1_wake_chain_bridge_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7B1'},
 {'module': 'v8_perf0_runtime_acceleration_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PERF0'},
 {'module': 'v8_phase7c_adaptive_boundaries_and_ei_balance_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'PHASE7C'},
 {'module': 'v8_perf3_connection_accelerator', 'how': 'autoload', 'target': 'LOOP', 'label': 'PERF3'},
 {'module': 'v8_phase7d_slow_wave_sleep_substructure_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7D'},
 {'module': 'v8_phase7e_histamine_wake_arousal_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7E'},
 {'module': 'v8_phase7f_orexin_wake_endurance_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7F'},
 {'module': 'v8_phase7g_bdnf_growth_consolidation_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7G'},
 {'module': 'v8_phase7cort_stability_watch_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7CORT'}]

EXPECTED_TOP_MODULE = "v8_phase7cort_stability_watch_release"


def _resolve_arg(target, autonomous_globals, AutonomousLoop):
    if target == "LOOP":
        return AutonomousLoop
    if target == "GLOBALS":
        return autonomous_globals
    if target == "LEARNER":
        return autonomous_globals["AutonomousLearner"]
    return None


def _call_entry(mod, entry, arg, target):
    how = entry["how"]
    fn = getattr(mod, how)
    if entry.get("loop_then_none"):
        try:
            return fn(arg)
        except TypeError:
            return fn()
    if target == "NONE":
        return fn()
    return fn(arg)


def load_all(autonomous_globals, AutonomousLoop, verbose=True):
    report = {"loaded": [], "dead_code": [], "errors": [], "self_check": {}}
    for entry in LOAD_ORDER:
        label = entry["label"]
        try:
            mod = importlib.import_module(PKG + "." + entry["module"])
            arg = _resolve_arg(entry["target"], autonomous_globals, AutonomousLoop)
            _call_entry(mod, entry, arg, entry["target"])
            for k, v in (entry.get("post_flags") or {}).items():
                setattr(AutonomousLoop, k, v)
            if entry.get("dead_code"):
                report["dead_code"].append(label)
            else:
                report["loaded"].append(label)
        except Exception as exc:
            if entry.get("dead_code"):
                report["dead_code"].append(label + " (noop_confirmed)")
            else:
                report["errors"].append((label, repr(exc)))
                if verbose:
                    print("[" + label + "_AUTOLOAD_ERROR]", exc)
    report["self_check"] = _self_check(AutonomousLoop, verbose)
    return report


def _self_check(AutonomousLoop, verbose=True):
    chk = {}
    cyc = getattr(AutonomousLoop, "cycle", None)
    top_mod = getattr(cyc, "__module__", "") if cyc is not None else ""
    chk["cycle_module"] = top_mod
    chk["cycle_on_phase7d"] = top_mod.endswith(EXPECTED_TOP_MODULE)
    chk["no_word_blacklists"] = getattr(AutonomousLoop, "no_word_blacklists", None)
    chk["fact_promotion"] = getattr(AutonomousLoop, "fact_promotion", None)
    chk["direct_fact_writes"] = getattr(AutonomousLoop, "direct_fact_writes", None)
    chk["slow_wave_sleep"] = getattr(AutonomousLoop, "slow_wave_sleep", None)
    ok = chk["cycle_on_phase7d"] and chk["fact_promotion"] == "disabled"
    chk["ok"] = bool(ok)
    if verbose and not ok:
        print("[PHASE_REGISTRY_SELF_CHECK_WARNING]", chk)
    return chk
