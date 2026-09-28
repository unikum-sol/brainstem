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
 # BRAINSTEM_LEXICAL_LAYER_LOAD_ORDER_V1: registered directly after
 # context_observation_learning_release so it chains onto (and its own
 # phase-specific work runs immediately after) the existing sentence-level
 # observation entry point, matching the exact chaining convention already
 # used by every phase from PHASE5A onward (module-level _PREV_CYCLE
 # capture + call-then-extend, see v8_phase0_lexical_boundary_observation_
 # release.py's own autoload()). Uses 'autoload' (the naming convention
 # already used by every phase6a+ module) since this module's own function
 # is named autoload(), not patch_autonomous_loop().
 {'module': 'v8_phase0_lexical_boundary_observation_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'PHASE0_LEXICAL'},
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
 # BRAINSTEM_EXPERIMENT_GAP_DETECTION_LOAD_ORDER_V1: registered directly
 # before PHASE5E (the first already-existing module that reads from
 # internal_learning_gaps) so gaps this module creates are visible to
 # downstream consumers within the same real cycle they were created in.
 {'module': 'v8_stageb_gap_detection_release',
  'how': 'autoload',
  'target': 'LOOP',
  'label': 'STAGEB_GAP_DETECTION'},
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
 {'module': 'v8_phase7cort_stability_watch_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE7CORT'},
 {'module': 'v8_cooperative_core_neuromodulator_sleep_authority_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'COOPERATIVE_CORE_SLEEP_AUTHORITY'},
 {'module': 'v8_stageb_guarded_hypothesis_graduation_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_GRADUATION'},
 # BRAINSTEM_EXPERIMENT_LOAD_ORDER_TIMING_FIX_V1 (22 September 2026): a
 # real end-to-end test run surfaced a real, if non-critical, timing
 # issue with the ORIGINAL ordering here (fact promotion registered
 # BEFORE contradiction detection/revision). Because each module's own
 # _PREV_CYCLE chaining convention runs the PREVIOUSLY-registered module
 # FIRST, then does its own work, the original order meant fact promotion
 # for a given real cycle always ran BEFORE that same cycle's own
 # contradiction detection and hypothesis revision -- so a fact could only
 # ever be retracted one full real cycle after the revision that should
 # have triggered it (confirmed directly: a genuinely stronger,
 # contradicting hypothesis correctly reversed the weaker hypothesis's
 # role in the SAME cycle it was detected, but the corresponding fact was
 # only retracted on the NEXT cycle's fact-promotion pass). Not a
 # correctness bug (nothing was ever lost or left permanently wrong --
 # see facts_before/promoted/retracted counters here at
 # every_cycle in dedicated diagnostics), but the reordering below (gap
 # detection -> contradiction detection -> hypothesis revision -> fact
 # promotion, i.e. fact promotion now LAST among the four new modules)
 # ensures retraction happens within the SAME real cycle as the revision
 # that causes it, matching this project's own "erst messen, dann
 # aendern, dann sofort konsistent halten" spirit as closely as possible
 # within a single-pass-per-cycle chain.
 {'module': 'v8_stageb_contradiction_detection_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_CONTRADICTION_DETECTION'},
 {'module': 'v8_stageb_hypothesis_revision_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_HYPOTHESIS_REVISION'},
 # BRAINSTEM_EXPERIMENT_FACT_PROMOTION_LOAD_ORDER_V1: registered LAST
 # among the four new Stage-B modules (see timing fix note above) so both
 # a fresh graduation AND a same-cycle revision are already visible to it.
 {'module': 'v8_stageb_fact_promotion_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_FACT_PROMOTION'},
 # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_V1 (25 September 2026): registered
 # directly after STAGEB_FACT_PROMOTION and before the chain-top
 # STAGEB_EF, per BrainStem_Relations_Ontology_Questions_Emergence_
 # Concept.md, Abschnitt 10.4. PHASE0B_RELATIONAL_BINDING (observation)
 # must run before STAGEB_RELATION_PROMOTION so a relation graduated in
 # the SAME cycle it was (re)observed is already visible to promotion --
 # matching the same same-cycle-visibility principle already used for the
 # gap-detection/contradiction/revision/fact-promotion ordering above.
 {'module': 'v8_phase0b_relational_binding_observation_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'PHASE0B_RELATIONAL_BINDING'},
 {'module': 'v8_stageb_relation_promotion_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_RELATION_PROMOTION'},
 # BRAINSTEM_ONTOLOGY_EMERGENCE_SLICE2_V1 (25 September 2026): registered
 # directly after STAGEB_RELATION_PROMOTION and before the chain-top
 # STAGEB_EF, per BrainStem_Relations_Ontology_Questions_Emergence_
 # Concept.md, Abschnitt 10.4's already-planned Relations -> Ontologie ->
 # Fragen chain position. Cluster observation must run before ontology
 # promotion so a cluster reconfirmed stable in THIS cycle is already
 # visible to promotion within the same cycle -- the same same-cycle-
 # visibility principle already used throughout this chain.
 {'module': 'v8_stageb_ontology_cluster_observation_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_ONTOLOGY_CLUSTER_OBSERVATION'},
 {'module': 'v8_stageb_ontology_promotion_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_ONTOLOGY_PROMOTION'},
 # BRAINSTEM_QUESTIONS_EMERGENCE_SLICE3_V1 (25 September 2026): registered
 # directly after STAGEB_ONTOLOGY_PROMOTION and before the chain-top
 # STAGEB_EF, completing the Relations -> Ontologie -> Fragen chain per
 # BrainStem_Relations_Ontology_Questions_Emergence_Concept.md, Abschnitt
 # 10.4/10.7. Unlike the two entries above, this module needs no paired
 # observation-phase entry: it reads only the already-populated, already-
 # productive internal_learning_gaps table (STAGEB_GAP_DETECTION, which
 # already runs much earlier in this same chain, directly after PHASE5D)
 # -- no new context_hypotheses role, no ELIGIBLE_ROLES/REVERT_ROLES/
 # contradiction-detection role-list entry needed.
 {'module': 'v8_stageb_question_promotion_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_QUESTION_PROMOTION'},
 # BRAINSTEM_QUESTION_CHUNK_FEEDBACK_V1 (25 September 2026): registered
 # directly after STAGEB_QUESTION_PROMOTION so a question promoted or
 # retracted in THIS cycle (including retraction driven by this same
 # cycle's gap habituation/closure) is already reflected before this
 # module reads the `questions` table -- the same same-cycle-visibility
 # principle already used throughout this chain. Closes the Questions
 # Slice 3 audit's "rein schreibender Blinddarm" finding: this is the
 # first and only module that reads `questions` to influence real
 # reading_queue/chunk_attention_scores behavior. Deliberately built
 # AFTER, not before, v8_stageb_gap_detection_release.py's own
 # habituation mechanism -- see that module's own docstring for why
 # wiring chunker feedback in first would have risked the
 # "noisy-TV problem" on unfiltered Phase-0 lexical noise.
 {'module': 'v8_stageb_question_chunk_feedback_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_QUESTION_CHUNK_FEEDBACK'},
 # BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): the
 # 'non_productive_recheck_canonical_autoload_shadow_runtime_integration_v1'
 # entry that used to sit here has been removed together with its entire
 # dependency chain (registration_v1 -> initialization_cursor_wrap_
 # fairness_telemetry_v1_2 -> delayed_evidence_recheck_watermark_
 # awaiting_state_contract_v1_1 -> real_outcome_delayed_eligibility_
 # shadow). That chain existed solely to observe a hypothetical future
 # outcome-eligibility/fact-promotion decision before that decision was
 # made. Since Stage-B fact promotion, gap detection, contradiction
 # detection and hypothesis revision are now productive (see the four
 # STAGEB_* entries above), the chain's own purpose was already fulfilled
 # and its output was confirmed to have no consumer anywhere in the
 # codebase (see the Legacy Report shipped with this cleanup for the full
 # verification trail). See the same Legacy Report for the removal of
 # four further, independently-confirmed-unused shadow cascades.
 {'module': 'v8_stageb_gapflow_runtime_contract_release', 'how': 'autoload', 'target': 'LOOP', 'label': 'STAGEB_EF'}]

EXPECTED_TOP_MODULE = "v8_stageb_gapflow_runtime_contract_release"


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
    # BRAINSTEM_REGISTRY_FATAL_TRACKING_V1: previously a failed *required*
    # (non dead_code) module load was recorded in report["errors"] but the
    # loop always continued silently and load_all() never surfaced this as a
    # clearly fatal condition anywhere the caller could easily check. The
    # per-entry catch-and-continue behavior itself is intentionally kept (a
    # single missing/broken optional module should not prevent every other
    # phase from loading), but we now also compute an explicit report["fatal"]
    # flag and feed load errors into the final self-check so the overall "ok"
    # verdict correctly reflects a partially broken chain instead of only
    # checking the topmost module name and a couple of class flags.
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
    report["fatal"] = bool(report["errors"])
    if report["fatal"] and verbose:
        print("[PHASE_REGISTRY_FATAL] one or more required phase modules failed to load:")
        for failed_label, exc_repr in report["errors"]:
            print("   -", failed_label, ":", exc_repr)
    report["self_check"] = _self_check(AutonomousLoop, verbose, errors=report["errors"])
    return report


def _self_check(AutonomousLoop, verbose=True, errors=None):
    chk = {}
    cyc = getattr(AutonomousLoop, "cycle", None)
    top_mod = getattr(cyc, "__module__", "") if cyc is not None else ""
    chk["cycle_module"] = top_mod
    chk["cycle_on_phase7d"] = top_mod.endswith(EXPECTED_TOP_MODULE)
    chk["no_word_blacklists"] = getattr(AutonomousLoop, "no_word_blacklists", None)
    chk["fact_promotion"] = getattr(AutonomousLoop, "fact_promotion", None)
    chk["direct_fact_writes"] = getattr(AutonomousLoop, "direct_fact_writes", None)
    chk["slow_wave_sleep"] = getattr(AutonomousLoop, "slow_wave_sleep", None)
    chk["load_errors"] = list(errors or [])
    # BRAINSTEM_COMPASS_FACT_PROMOTION_FLAG_FIX_V1 (24 September 2026): this
    # self-check used to require fact_promotion == "disabled" to be
    # considered healthy. That was correct for the original, closed-by-
    # default build, but is now the OPPOSITE of the current, user-declared
    # experiment state (see v8_stageb_fact_promotion_release.py, the sole,
    # guarded writer of the facts table, whose own autoload() now
    # correctly asserts "enabled"). Left unchanged, this self-check would
    # print a spurious [PHASE_REGISTRY_SELF_CHECK_WARNING] on every single
    # real startup from now on, despite nothing actually being wrong.
    # Fixed to expect the current, correct value instead.
    ok = chk["cycle_on_phase7d"] and chk["fact_promotion"] == "enabled" and not chk["load_errors"]
    chk["ok"] = bool(ok)
    if verbose and not ok:
        print("[PHASE_REGISTRY_SELF_CHECK_WARNING]", chk)
    return chk
