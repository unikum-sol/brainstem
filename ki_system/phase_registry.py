# -*- coding: utf-8 -*-
"""BrainStem central phase/patch registry."""
import importlib

PKG = "ki_system"

LOAD_ORDER = [
    # ---------------- Welt A: Legacy patches ----------------
    {"module": "autonomous_brain_patch", "how": "apply_patch", "target": "LEARNER", "label": "PHASE3D6A", "dead_code": True},
    {"module": "autonomous_brain_patch", "how": "apply_patch", "target": "LEARNER", "label": "PHASE3D6B", "dead_code": True},
    {"module": "autonomous_brain_patch", "how": "apply_patch", "target": "LEARNER", "label": "PHASE3D6C", "dead_code": True},
    {"module": "true_safe_brain", "how": "apply_patch", "target": "LEARNER", "label": "PHASE3D6D", "dead_code": True},
    {"module": "true_safe_loop_patch", "how": "apply_patch", "target": "GLOBALS", "label": "PHASE3D6E"},
    {"module": "true_safe_loop_patch", "how": "apply_patch", "target": "GLOBALS", "label": "PHASE3D6F"},
    {"module": "true_safe_loop_patch", "how": "apply_patch", "target": "GLOBALS", "label": "PHASE3D6G"},
    {"module": "true_safe_loop_patch", "how": "apply_patch", "target": "GLOBALS", "label": "PHASE3D6H"},
    {"module": "true_safe_loop_patch", "how": "apply_patch", "target": "GLOBALS", "label": "PHASE3D6I"},
    {"module": "true_safe_loop_patch", "how": "apply_patch", "target": "GLOBALS", "label": "PHASE3D6J"},
    {"module": "true_safe_loop_patch", "how": "apply_patch", "target": "GLOBALS", "label": "PHASE3D6K1"},
    {"module": "v8_phase3d8_to_3d6g_rollback_fixed2", "how": "apply_patch", "target": "NONE", "label": "PHASE3D8_ROLLBACK_FIXED2"},
    {"module": "v8_phase3d9_cleanup_safe_core", "how": "apply_patch", "target": "NONE", "label": "PHASE3D9_FORCE_SAFE_CORE_FIXED5"},
    # ---------------- Welt B: Phase 4/5 ----------------
    {"module": "v8_phase4abc_context_learning_pack", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4ABC"},
    {"module": "v8_phase4abc_context_learning_pack", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4ABC_FIXED1"},
    {"module": "v8_phase4def_context_learning_pack", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4DEF_PACK"},
    {"module": "v8_phase4def_context_learning_pack", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4DEF_FIXED2"},
    {"module": "v8_phase4def_context_learning_pack", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4DEF_FIXED3",
     "post_flags": {"_phase4d_hypothesis_feedback_error_learning": True, "_phase4e_neuromodulated_attention_strategy": True,
                    "_phase4f_sleep_consolidation_self_improvement": True, "_phase4def_context_learning_pack": True,
                    "_phase4def_context_learning_pack_fixed3": True, "_no_word_blacklists": True,
                    "_rollback_learning_mode": "context_hypotheses_with_neuromodulators",
                    "_learning_mode": "context_hypotheses_with_neuromodulators", "_fact_promotion": "disabled"}},
    {"module": "v8_phase4def_context_learning_pack", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4DEF_FIXED4",
     "post_flags": {"phase4d_hypothesis_feedback_error_learning": True, "phase4e_neuromodulated_attention_strategy": True,
                    "phase4f_sleep_consolidation_self_improvement": True, "phase4def_context_learning_pack": True,
                    "phase4def_context_learning_pack_fixed4": True, "_phase4d_hypothesis_feedback_error_learning": True,
                    "_phase4e_neuromodulated_attention_strategy": True, "_phase4f_sleep_consolidation_self_improvement": True,
                    "_phase4def_context_learning_pack": True, "_phase4def_context_learning_pack_fixed4": True,
                    "no_word_blacklists": True, "_no_word_blacklists": True,
                    "learning_mode": "context_hypotheses_with_neuromodulators", "_learning_mode": "context_hypotheses_with_neuromodulators",
                    "_rollback_learning_mode": "context_hypotheses_with_neuromodulators",
                    "fact_promotion": "disabled", "_fact_promotion": "disabled"}},
    {"module": "v8_phase4def_context_learning_pack", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4DEF_SCHEMA_FIXED5"},
    {"module": "v8_phase4_schema_manager_canonicalization", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4_SCHEMA_MANAGER_CANON"},
    {"module": "v8_phase4_schema_manager_mem_alias_fix", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4_SCHEMA_MEM_ALIAS_FIX_FIXED1"},
    {"module": "v8_phase4_schema_runtime_guard_fixed9", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4_SCHEMA_RUNTIME_GUARD_FIXED9"},
    {"module": "v8_phase4_schema_runtime_guard_fixed10", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4_SCHEMA_RUNTIME_GUARD_FIXED10"},
    {"module": "v8_phase4g_neuromodulated_attention_queue_activation", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4G"},
    {"module": "v8_phase4h_self_evaluation_and_revision_core", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4H"},
    {"module": "v8_phase4i_runtime_schema_guard_fixed3", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4I_RUNTIME_SCHEMA_GUARD_FIXED3"},
    {"module": "v8_phase4j_internal_learning_questions_and_gap_detection", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4J"},
    {"module": "v8_phase4k_gap_driven_rereading_and_learning_strategy", "how": "patch_autonomous_loop", "target": "LOOP", "loop_then_none": True, "label": "PHASE4K",
     "post_flags": {"phase4k_gap_driven_rereading_and_learning_strategy": True, "_phase4k_gap_driven_rereading_and_learning_strategy": True,
                    "phase4j_internal_learning_questions_and_gap_detection": True, "_phase4j_internal_learning_questions_and_gap_detection": True,
                    "no_word_blacklists": True, "_no_word_blacklists": True,
                    "learning_mode": "context_hypotheses_with_neuromodulators",
                    "_rollback_learning_mode": "context_hypotheses_with_neuromodulators",
                    "fact_promotion": "disabled", "_fact_promotion": "disabled"}},
    {"module": "v8_phase4l_gap_cluster_planning_and_strategy_balance", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4L"},
    {"module": "v8_phase4m_active_learning_loop_controller", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4M"},
    {"module": "v8_phase4n_learning_progress_evaluation_and_adaptive_strategy", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4N"},
    {"module": "v8_phase4o_strategy_effectiveness_feedback_loop", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4O_STRATEGY"},
    {"module": "v8_phase4o_schema_guard_fixed1", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4O_SCHEMA_GUARD_FIXED1"},
    {"module": "v8_phase4o_schema_guard_fixed2", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE4O_SCHEMA_GUARD_FIXED2"},
    {"module": "v8_phase4p_gap_resolution_and_learning_outcome_tracking", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE4P"},
    {"module": "v8_phase5a_integrated_self_improving_learning_release", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE5A"},
    {"module": "v8_phase5b_integrated_strategy_refinement_release", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE5B"},
    {"module": "v8_phase5b_schema_guard_fixed1", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE5B_SCHEMA_GUARD_FIXED1"},
    {"module": "v8_phase5c_learning_outcome_closure_and_question_cluster_resolution", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE5C"},
    {"module": "v8_phase5d_integrated_observation_and_strategy_memory_release", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE5D"},
    {"module": "v8_phase5e_context_expansion_and_gap_closure_release", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE5E"},
    {"module": "v8_phase5f_context_expansion_effectiveness_and_adaptive_windowing_release", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE5F"},
    {"module": "v8_phase5g_context_strategy_selection_and_experiment_memory_release", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE5G"},
    {"module": "v8_phase5h_strategy_experiment_outcome_learning_release", "how": "patch_autonomous_loop", "target": "LOOP", "label": "PHASE5H"},
    {"module": "v8_phase5h_schema_guard_fixed1", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE5H_SCHEMA_GUARD_FIXED1"},
    {"module": "v8_phase5h_schema_guard_fixed2", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE5H_SCHEMA_GUARD_FIXED2"},
    {"module": "v8_phase5i_outcome_driven_context_strategy_diversification_release", "how": "patch_autonomous_loop", "target": "NONE", "label": "PHASE5I"},
    # ---------------- Welt C: Phase 6/7 + perf (autoload). 7d must be last. ----------------
    {"module": "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release", "how": "autoload", "target": "LOOP", "label": "PHASE6A"},
    {"module": "v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "how": "autoload", "target": "LOOP", "label": "PHASE6B"},
    {"module": "v8_phase6c_bias_persistence_and_self_regulating_meta_release", "how": "autoload", "target": "LOOP", "label": "PHASE6C"},
    {"module": "v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "how": "autoload", "target": "LOOP", "label": "PHASE6D"},
    {"module": "v8_phase7a_adenosine_homeostat_release", "how": "autoload", "target": "LOOP", "label": "PHASE7A"},
    {"module": "v8_phase7b_endocannabinoid_retrograde_gain_control_release", "how": "autoload", "target": "LOOP", "label": "PHASE7B"},
    {"module": "v8_phase7b1_wake_chain_bridge_release", "how": "autoload", "target": "LOOP", "label": "PHASE7B1"},
    {"module": "v8_perf0_runtime_acceleration_release", "how": "autoload", "target": "LOOP", "label": "PERF0"},
    {"module": "v8_phase7c_adaptive_boundaries_and_ei_balance_release", "how": "autoload", "target": "LOOP", "label": "PHASE7C"},
    {"module": "v8_perf3_connection_accelerator", "how": "autoload", "target": "LOOP", "label": "PERF3"},
    {"module": "v8_phase7d_slow_wave_sleep_substructure_release", "how": "autoload", "target": "LOOP", "label": "PHASE7D"},
    {"module": "v8_phase7e_histamine_wake_arousal_release", "how": "autoload", "target": "LOOP", "label": "PHASE7E"},
    {"module": "v8_phase7f_orexin_wake_endurance_release", "how": "autoload", "target": "LOOP", "label": "PHASE7F"},
    {"module": "v8_phase7g_bdnf_growth_consolidation_release", "how": "autoload", "target": "LOOP", "label": "PHASE7G"},
    {"module": "v8_phase7cort_stability_watch_release", "how": "autoload", "target": "LOOP", "label": "PHASE7CORT"},
]

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
