# -*- coding: utf-8 -*-
"""Adaptive DB Bootstrap for the KI System (creates DB + base + phase tables)."""
from __future__ import annotations
import os, sqlite3, importlib
from pathlib import Path
from typing import Any, Dict, List, Tuple
# BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): the five
# standalone shadow/observation module imports that used to be declared
# here (modern_gap_phase5f_shadow_observation[_v2]/_history,
# stable_obs_content_fp_shadow_classifier, phase6a_replay_control_shadow)
# have been removed together with the modules themselves. All five were
# confirmed, by exhaustive cross-reference across the whole codebase, to
# feed only each other and never a consumer outside their own cascade.
# See the Legacy Report shipped with this cleanup for the full
# verification trail.


# BRAINSTEM_CORE_TABLE_NAMING_SYNC_FIX_V1: this central declaration for
# facts/relations/ontology used to use a DIFFERENT column naming convention
# (subject/relation/object, subject/super/source_fact_id) than the one
# actually created and used everywhere at runtime by memory.py's own _init()
# (subject/relation/value with UNIQUE(subject,relation,value); source/
# relation/target; child/parent/relation/fact_id). Since Memory._init()
# always runs for every Memory(...) instance and is read/written by
# memory.py's add_fact/add_relation/add_ontology/export_facts_csv and by
# gui_app.py's fact browser, it is the true, always-authoritative schema.
# No other module in the codebase ever referenced the old "object"/"super"/
# "source_fact_id" names (direct fact/relation/ontology writes are disabled
# by design in this build anyway). Depending on call order, the previous
# mismatch could let db_bootstrap.py "win" and create these 3 tables with
# the wrong column names before memory.py ever got to run its own (now
# no-op) CREATE TABLE IF NOT EXISTS, breaking memory.py's own methods with
# "no such column: value" style errors. Fixed by matching memory.py exactly.
SCHEMA_TABLES: Dict[str, List[Tuple[str, str]]] = {'facts': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
           ('subject', 'TEXT'),
           ('relation', 'TEXT'),
           ('value', 'TEXT'),
           ('confidence', 'REAL DEFAULT 0'),
           ('source_chunk_id', 'INTEGER'),
           ('created_at', 'INTEGER'),
           # BRAINSTEM_SCHEMA_CENTRALIZATION_GAP_FIX_V1 (23.09.2026): this
           # column was previously ONLY ever added by memory.py's own
           # Memory._ensure_core_import_schema()/CORE_IMPORT_SCHEMA, never
           # mirrored here in the central schema authority -- violating
           # this project's own rule that every schema change must be
           # tracked in db_bootstrap.py's SCHEMA_TABLES. On a database
           # bootstrapped via ensure_database_exists() alone (no Memory()
           # instantiated first), v8_stageb_fact_promotion_release.py's own
           # schema self-check correctly detected the missing column and
           # refused to write, exactly as designed -- but this masked a
           # real central-schema gap rather than a bug in that module.
           # Mirrored here now (memory.py's own ALTER TABLE ADD COLUMN
           # remains additionally idempotent/harmless if it runs first).
           ('source_hypothesis_id', 'INTEGER')],
 'relations': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
               ('source', 'TEXT'),
               ('relation', 'TEXT'),
               ('target', 'TEXT'),
               ('confidence', 'REAL DEFAULT 0'),
               ('source_chunk_id', 'INTEGER'),
               ('created_at', 'INTEGER'),
               # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_V1 (25 September 2026):
               # additive, nullable column linking a promoted relation back
               # to the exact context_hypotheses row it was promoted from
               # (see v8_stageb_relation_promotion_release.py), mirroring
               # facts.source_hypothesis_id's existing role/rationale
               # exactly. Required so a relation can be retracted again if
               # its source hypothesis is later reversed by
               # v8_stageb_hypothesis_revision_release.py.
               ('source_hypothesis_id', 'INTEGER')],
 'questions': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
               ('question', 'TEXT'),
               ('priority', 'REAL DEFAULT 0'),
               ('status', "TEXT DEFAULT 'open'"),
               ('created_at', 'INTEGER'),
               ('updated_at', 'INTEGER'),
               # BRAINSTEM_QUESTIONS_EMERGENCE_SLICE3_V1 (25 September 2026):
               # additive, nullable column linking a promoted question back
               # to the exact internal_learning_gaps row it was promoted
               # from (see v8_stageb_question_promotion_release.py),
               # mirroring facts.source_hypothesis_id and relations.
               # source_hypothesis_id's existing role/rationale exactly.
               # Required so a question can be resolved again (status set
               # to 'resolved', never deleted) if its source gap is later
               # closed.
               ('source_gap_id', 'INTEGER')],
 'documents': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
               ('path', 'TEXT'),
               ('title', 'TEXT'),
               ('kind', 'TEXT'),
               ('metadata_json', 'TEXT'),
               ('source_score', 'REAL DEFAULT 1'),
               ('created_at', 'INTEGER')],
 'chunks': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('document_id', 'INTEGER'),
            ('chunk_index', 'INTEGER'),
            ('text', 'TEXT'),
            ('token_count', 'INTEGER'),
            ('title', 'TEXT'),
            ('metadata_json', 'TEXT'),
            ('import_key', 'TEXT'),
            ('created_at', 'INTEGER')],
 'ontology': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
              ('child', 'TEXT'),
              ('parent', 'TEXT'),
              ('relation', 'TEXT'),
              ('confidence', 'REAL DEFAULT 0'),
              ('fact_id', 'INTEGER'),
              ('created_at', 'INTEGER'),
              # BRAINSTEM_ONTOLOGY_EMERGENCE_SLICE2_V1 (25 September 2026):
              # two additive, nullable columns for
              # v8_stageb_ontology_promotion_release.py, per
              # BrainStem_Relations_Ontology_Questions_Emergence_Concept.md,
              # Abschnitt 3.2/10.2. source_cluster_key links a promoted
              # ontology row back to the stable-cluster anchor (prototype
              # node key) it was derived from, enabling retraction if the
              # cluster later dissolves (see v8_stageb_ontology_cluster_
              # observation_release.py). source_relation_ids is a JSON list
              # of the contributing relations.id values -- a single foreign
              # key (like facts.source_hypothesis_id) is not sufficient
              # here because an ontology row derives from a GROUP of
              # multiple relations (the edges connecting child to prototype
              # within the stable cluster), not from one single hypothesis.
              # fact_id remains unused by this module (Slice 2 clusters
              # over `relations`, not `facts` -- see the module's own
              # docstring for the full rationale) but is left in place,
              # unremoved, for any future direct-fact-based clustering.
              ('source_cluster_key', 'TEXT'),
              ('source_relation_ids', 'TEXT')],
 'context_hypotheses': [('id', 'INTEGER PRIMARY KEY'),
                        ('subject', 'TEXT'),
                        ('hypothesis', 'TEXT'),
                        ('confidence', 'REAL DEFAULT 0'),
                        ('phase6a_replay_priority', 'REAL DEFAULT 0'),
                        ('phase6a_replay_weight', 'REAL DEFAULT 0'),
                        ('phase6a_meta_plasticity', 'REAL DEFAULT 0'),
                        ('phase6a_sleep_replay_count', 'INTEGER DEFAULT 0'),
                        ('phase6a_last_replayed_at', 'INTEGER'),
                        ('phase6a_replay_reason', 'TEXT'),
                        ('created_at', 'INTEGER DEFAULT 0'),
                        ('chunk_id', 'INTEGER'),
                        ('role', 'TEXT'),
                        ('relation_hint', 'TEXT'),
                        ('object', 'TEXT'),
                        ('text_excerpt', 'TEXT'),
                        ('source_title', 'TEXT'),
                        ('uncertainty', 'REAL DEFAULT 1'),
                        ('status', "TEXT DEFAULT 'hypothesis'"),
                        ('dopamine', 'REAL DEFAULT 0'),
                        ('serotonin', 'REAL DEFAULT 0'),
                        ('glutamate', 'REAL DEFAULT 0'),
                        ('gaba', 'REAL DEFAULT 0'),
                        ('noradrenaline', 'REAL DEFAULT 0'),
                        ('acetylcholine', 'REAL DEFAULT 0'),
                        ('signature', 'TEXT'),
                        ('evidence_count', 'INTEGER DEFAULT 1'),
                        ('updated_at', 'INTEGER DEFAULT 0'),
                        ('phase5a_integrated_score', 'REAL DEFAULT 0'),
                        ('phase5a_last_integrated_at', 'INTEGER DEFAULT 0'),
                        ('phase5a_integrated_reason', 'TEXT'),
                        ('learning_outcome_score', 'REAL DEFAULT 0'),
                        ('last_outcome_tracked_at', 'INTEGER DEFAULT 0'),
                        ('outcome_tracking_reason', 'TEXT'),
                        ('resolution_support_score', 'REAL DEFAULT 0'),
                        ('strategy_effectiveness_score', 'REAL DEFAULT 0'),
                        ('last_strategy_feedback_at', 'INTEGER DEFAULT 0'),
                        ('strategy_feedback_reason', 'TEXT'),
                        ('progress_score', 'REAL DEFAULT 0'),
                        ('progress_reason', 'TEXT'),
                        ('last_progress_evaluated_at', 'INTEGER DEFAULT 0'),
                        ('active_learning_score', 'REAL DEFAULT 0'),
                        ('last_active_learning_at', 'INTEGER DEFAULT 0'),
                        ('active_learning_reason', 'TEXT'),
                        ('self_score', 'REAL DEFAULT 0'),
                        ('revision_pressure', 'REAL DEFAULT 0'),
                        ('revision_count', 'INTEGER DEFAULT 0'),
                        ('last_evaluated_at', 'INTEGER DEFAULT 0'),
                        ('last_revision_reason', 'TEXT'),
                        ('phase5f_context_window_score', 'REAL DEFAULT 0'),
                        ('phase5f_window_strategy', 'TEXT'),
                        ('phase5f_last_windowed_at', 'INTEGER DEFAULT 0'),
                        ('phase5g_score', 'REAL DEFAULT 0'),
                        ('phase5g_selected_strategy', 'TEXT'),
                        ('phase5g_strategy_score', 'REAL DEFAULT 0'),
                        ('phase5g_closure_delta', 'REAL DEFAULT 0'),
                        ('phase5g_no_candidate_rate', 'REAL DEFAULT 0'),
                        ('phase5g_overlap_score', 'REAL DEFAULT 0'),
                        ('phase5g_last_selected_at', 'INTEGER DEFAULT 0'),
                        ('phase5g_reason', 'TEXT'),
                        # BRAINSTEM_LEXICAL_LAYER_SCHEMA_V1: additive column
                        # for the new v8_phase0_lexical_boundary_observation_
                        # release.py module (autonomous lexical/word-boundary
                        # discovery, see docs/lexical_emergence_concept.md).
                        # context_hypotheses is a centrally-declared, shared
                        # table used by many phases, so per this project's
                        # own "alle Spalten vorab in SCHEMA_TABLES" rule, any
                        # new column on it belongs here, not only in the
                        # owning module's own schema helper. Nullable and
                        # unused by every existing hypothesis role
                        # (sentence-level hypotheses simply leave it NULL);
                        # only rows with role='uncertain_lexical_boundary'
                        # (or its graduated form 'stable_lexical_boundary')
                        # populate it, with the character offset (within the
                        # FIRST-seen chunk's normalized text) of that
                        # boundary candidate.
                        ('lexical_offset', 'INTEGER'),
                        # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_V1 (25
                        # September 2026): additive column for the new
                        # v8_phase0b_relational_binding_observation_release.py
                        # module (see BrainStem_Relations_Ontology_
                        # Questions_Emergence_Concept.md, Abschnitt 10.2).
                        # Nullable and NULL for every existing hypothesis
                        # role (sentence-level and lexical-boundary
                        # hypotheses leave it NULL); only rows with
                        # role='uncertain_relation_hypothesis' populate it,
                        # marking that the row's subject/object direction
                        # was assigned via the Positions-Heuristik (Signal
                        # 1, Abschnitt 2.4.1) rather than a more certain
                        # source. Per Abschnitt 2.4.5/6, hypotheses with
                        # this origin receive increased revision tolerance
                        # in contradiction/revision handling.
                        ('origin', 'TEXT')],
 # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_V1 (25 September 2026): pure
 # observation/counting table for
 # v8_phase0b_relational_binding_observation_release.py (Abschnitt 2.4/10.3
 # of the Emergence Concept). One row per ordered pair of stable elements
 # (subject_signature, object_signature) observed co-occurring within the
 # same sentence. pair_count/count_a/count_b are the raw frequency inputs
 # to the symmetric PMI existence gate (Abschnitt 2.4.2); first_as_a_count/
 # first_as_b_count are the raw inputs to the Positions-Heuristik direction
 # signal (Abschnitt 2.4.1). No confidence/uncertainty/neuromodulator
 # columns here deliberately -- this table is a pure frequency ledger, not
 # itself a hypothesis; the resulting uncertain_relation_hypothesis row in
 # context_hypotheses carries all of that via the existing, shared
 # machinery.
 'relational_cooccurrence_counts': [
     ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
     ('signature_a', 'TEXT'),
     ('signature_b', 'TEXT'),
     ('subject_a', 'TEXT'),
     ('subject_b', 'TEXT'),
     ('pair_count', 'INTEGER DEFAULT 0'),
     ('count_a', 'INTEGER DEFAULT 0'),
     ('count_b', 'INTEGER DEFAULT 0'),
     ('first_as_a_count', 'INTEGER DEFAULT 0'),
     ('first_as_b_count', 'INTEGER DEFAULT 0'),
     ('first_seen_at', 'INTEGER'),
     ('updated_at', 'INTEGER'),
 ],
 'internal_learning_gaps': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                            ('gap_key', 'TEXT'),
                            ('gap_type', 'TEXT'),
                            ('gap_reason', 'TEXT'),
                            ('role', 'TEXT'),
                            ('priority', 'REAL DEFAULT 0'),
                            # BRAINSTEM_GAP_SCHEMA_COMPLETENESS_FIX_V1: severity,
                            # hypothesis_id, uncertainty and pattern_key are all
                            # referenced directly (unconditionally, without an
                            # "in columns" existence guard) by real read queries
                            # in v8_phase6a (severity), v8_phase5i and
                            # v8_phase5e (hypothesis_id, uncertainty,
                            # pattern_key). None of these columns were ever
                            # declared anywhere, so a real learning cycle on a
                            # freshly bootstrapped database reliably failed
                            # with "no such column" as soon as those phases
                            # ran. Declaring them here (matching the project's
                            # own "alle Spalten vorab in SCHEMA_TABLES" rule)
                            # fixes the crash without changing any query logic;
                            # unpopulated columns simply read back as NULL,
                            # which every one of these call sites already
                            # treats as a valid fallback case via COALESCE.
                            ('severity', 'REAL DEFAULT 0'),
                            ('hypothesis_id', 'INTEGER'),
                            ('uncertainty', 'REAL DEFAULT 1'),
                            ('pattern_key', 'TEXT'),
                            ('status', "TEXT DEFAULT 'open'"),
                            ('resolution_score', 'REAL DEFAULT 0'),
                            # BRAINSTEM_GAP_SCHEMA_COMPLETENESS_FIX_V2: same
                            # class of defect as the severity/hypothesis_id/
                            # uncertainty/pattern_key fix above --
                            # resolution_attempts is referenced directly
                            # (unconditionally, via COALESCE(resolution_
                            # attempts,0), with no "in columns" existence
                            # guard) by v8_phase5b_integrated_strategy_
                            # refinement_release.py's real per-cycle
                            # persistent-gap-strategy query. This column was
                            # never declared anywhere, so on a real learning
                            # cycle -- verified reproducible on every single
                            # cycle, from cycle 1 onward, on both the
                            # unmodified original codebase and this fixed
                            # copy before this addition -- Phase 5b reliably
                            # failed with "no such column: resolution_
                            # attempts" as soon as the persistent-gap-
                            # strategy branch ran (i.e. whenever
                            # internal_learning_gaps is non-empty). Declaring
                            # it here (matching the project's own "alle
                            # Spalten vorab in SCHEMA_TABLES" rule) fixes the
                            # crash without changing any query logic; the
                            # unpopulated column simply reads back as 0 via
                            # the existing COALESCE, which the call site
                            # already treats as a valid fallback (an
                            # as-yet-unattempted gap).
                            ('resolution_attempts', 'INTEGER DEFAULT 0'),
                            # BRAINSTEM_GAP_SCHEMA_COMPLETENESS_FIX_V3: same
                            # class of defect as the two fixes above --
                            # revision_pressure is referenced directly
                            # (unconditionally, via COALESCE(revision_
                            # pressure,0) inside an ORDER BY clause, with no
                            # "in columns" existence guard) by
                            # v8_phase5e_context_expansion_and_gap_closure_
                            # release.py's real per-cycle gap-selection
                            # query. Verified via a project-wide, systematic
                            # audit of every column referenced via
                            # COALESCE(...) against internal_learning_gaps
                            # across all ~68 modules (undertaken after two
                            # similar missing-column crashes,
                            # resolution_attempts and, before that,
                            # severity/hypothesis_id/uncertainty/
                            # pattern_key, were each independently
                            # discovered one cycle at a time): every OTHER
                            # candidate column found by that audit
                            # (phase5e_expansion_attempts,
                            # phase5f_experiment_count,
                            # phase5g_experiment_count,
                            # phase5i_experiment_count,
                            # phase6a_sleep_replay_count,
                            # strategy_refinement_count) was confirmed
                            # already self-healed by its OWNER module's own
                            # ensure_schema()/addcol() call, which always
                            # runs before that module's own query in the
                            # same function -- and resolution_status was
                            # confirmed already safely guarded everywhere
                            # via an explicit "in columns" check before use.
                            # revision_pressure was the ONLY column in that
                            # audit genuinely unowned by any module's own
                            # schema extension, confirmed reproducible on
                            # every single real cycle once
                            # resolution_attempts was fixed (both on the
                            # unmodified original codebase and this fixed
                            # copy). Declaring it here (matching the
                            # project's own "alle Spalten vorab in
                            # SCHEMA_TABLES" rule) fixes the crash without
                            # changing any query logic.
                            ('revision_pressure', 'REAL DEFAULT 0'),
                            ('strategy_effectiveness_score', 'REAL DEFAULT 0'),
                            ('evidence_count', 'INTEGER DEFAULT 0'),
                            # BRAINSTEM_GAP_CLOSURE_AND_HABITUATION_V1 (25
                            # September 2026): five additive columns, all
                            # nullable/defaulted, needed to close two
                            # gaps identified in the Questions Slice 3
                            # audit -- (a) a gap whose own hypothesis_id
                            # graduates into a fact/relation is never
                            # marked resolved (status stayed 'open'
                            # forever, making Slice 3's retraction path
                            # permanently dead code in real operation),
                            # and (b) resolution_attempts, once fixed to
                            # actually increment, grows monotonically
                            # forever with no decay, so a gap whose
                            # underlying hypothesis is genuine, unresolvable
                            # noise (e.g. a Phase-0 lexical-boundary
                            # parsing artifact that keeps being
                            # reobserved but never gains new evidence)
                            # would stay at permanently maximal priority/
                            # salience instead of habituating -- contrary
                            # to the empirically well-established inverted-
                            # U relationship between resolvability and
                            # curiosity (Kang et al. 2009, Psychological
                            # Science 20(8):963-973; synthesized further in
                            # Ten/Oudeyer/Sakaki/Murayama 2025, Open Mind
                            # 9:1763-1785) and to habituation as a real,
                            # reversible neural process driven by absence
                            # of new information gain, not by elapsed
                            # attempts alone (Ueda/Sekoguchi/Yanagisawa
                            # 2021, PLoS One 16(6):e0237278; Smart/
                            # Shvartsman/Moennigmann 2026, Annual Review of
                            # Control, Robotics and Autonomous Systems).
                            # closed_at/closure_reason record a positive
                            # resolution (hypothesis graduated); habituated_
                            # at/stagnant_streak/evidence_count_at_last_gain
                            # implement the separate, reversible decay path
                            # (see v8_stageb_gap_detection_release.py's own
                            # _upsert_gap() for the full mechanism). Both
                            # paths are owned exclusively by
                            # v8_stageb_gap_detection_release.py, which
                            # remains the sole writer of internal_learning_
                            # gaps' base lifecycle row; fact/relation
                            # promotion only ever set status/closed_at/
                            # closure_reason at their own existing
                            # promotion/retraction write points, never any
                            # of the stagnation/habituation columns.
                            ('closed_at', 'INTEGER'),
                            ('closure_reason', 'TEXT'),
                            ('habituated_at', 'INTEGER'),
                            ('stagnant_streak', 'INTEGER DEFAULT 0'),
                            ('evidence_count_at_last_gain', 'INTEGER'),
                            ('updated_at', 'INTEGER DEFAULT 0'),
                            ('created_at', 'INTEGER')],
 'phase5g_experiment_outcomes': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                 ('experiment_id', 'INTEGER'),
                                 ('gap_id', 'INTEGER'),
                                 ('strategy', 'TEXT'),
                                 ('before_score', 'REAL DEFAULT 0'),
                                 ('after_score', 'REAL DEFAULT 0'),
                                 ('closure_delta', 'REAL DEFAULT 0'),
                                 ('read_status', 'TEXT'),
                                 ('no_candidate_penalty', 'REAL DEFAULT 0'),
                                 ('effectiveness_score', 'REAL DEFAULT 0'),
                                 ('outcome', 'TEXT'),
                                 ('details', 'TEXT'),
                                 ('created_at', 'INTEGER'),
                                 ('outcome_key', 'TEXT'),
                                 ('experiment_key', 'TEXT'),
                                 ('gap_key', 'TEXT'),
                                 ('gap_type', 'TEXT'),
                                 ('role', 'TEXT'),
                                 ('source_chunk_id', 'INTEGER'),
                                 ('center_chunk_id', 'INTEGER'),
                                 ('target_chunk_id', 'INTEGER'),
                                 ('selected_strategy', 'TEXT'),
                                 ('window_strategy', 'TEXT'),
                                 ('window_radius', 'INTEGER'),
                                 ('no_candidate_rate', 'REAL DEFAULT 0'),
                                 ('overlap_score', 'REAL DEFAULT 0'),
                                 ('strategy_score', 'REAL DEFAULT 0'),
                                 ('outcome_score', 'REAL DEFAULT 0'),
                                 ('outcome_label', 'TEXT'),
                                 ('recommendation', 'TEXT'),
                                 ('learning_rate', 'REAL DEFAULT 0'),
                                 ('error_weight', 'REAL DEFAULT 0'),
                                 ('revision_pressure', 'REAL DEFAULT 0'),
                                 ('exploration_pressure', 'REAL DEFAULT 0'),
                                 ('inhibition_level', 'REAL DEFAULT 0'),
                                 ('consolidation_gain', 'REAL DEFAULT 0'),
                                 ('dopamine', 'REAL DEFAULT 0'),
                                 ('serotonin', 'REAL DEFAULT 0'),
                                 ('glutamate', 'REAL DEFAULT 0'),
                                 ('gaba', 'REAL DEFAULT 0'),
                                 ('noradrenaline', 'REAL DEFAULT 0'),
                                 ('acetylcholine', 'REAL DEFAULT 0'),
                                 ('evidence_count', 'INTEGER DEFAULT 1'),
                                 ('updated_at', 'INTEGER DEFAULT 0'),
                                 ('phase5i_memory_used', 'INTEGER DEFAULT 0'),
                                 ('phase6a_replay_priority', 'REAL DEFAULT 0'),
                                 ('phase6a_replay_weight', 'REAL DEFAULT 0'),
                                 ('phase6a_meta_plasticity', 'REAL DEFAULT 0'),
                                 ('phase6a_sleep_replay_count', 'INTEGER DEFAULT 0'),
                                 ('phase6a_last_replayed_at', 'INTEGER'),
                                 ('phase6a_replay_decision', 'TEXT'),
                                 ('phase6a_replay_reason', 'TEXT')],
 'phase5h_strategy_outcome_memory': [('memory_key', 'TEXT PRIMARY KEY'),
                                     ('selected_strategy', 'TEXT'),
                                     ('gap_type', 'TEXT'),
                                     ('role', 'TEXT'),
                                     ('observations', 'INTEGER DEFAULT 0'),
                                     ('avg_outcome_score', 'REAL DEFAULT 0'),
                                     ('avg_closure_delta', 'REAL DEFAULT 0'),
                                     ('avg_no_candidate_rate', 'REAL DEFAULT 0'),
                                     ('avg_overlap_score', 'REAL DEFAULT 0'),
                                     ('avg_strategy_score', 'REAL DEFAULT 0'),
                                     ('recommendation', 'TEXT'),
                                     ('neuromodulator_profile', 'TEXT'),
                                     ('details', 'TEXT'),
                                     ('first_seen', 'INTEGER'),
                                     ('last_seen', 'INTEGER'),
                                     ('updated_at', 'INTEGER DEFAULT 0'),
                                     ('phase6a_replay_weight', 'REAL DEFAULT 0'),
                                     ('phase6a_meta_plasticity', 'REAL DEFAULT 0'),
                                     ('phase6a_last_replayed_at', 'INTEGER'),
                                     ('phase6a_replay_recommendation', 'TEXT')],
 'phase6a_sleep_replay_cycles': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                 # BRAINSTEM_PHASE6A_CYCLES_SCHEMA_SYNC_FIX_V1:
                                 # this central declaration used to be missing
                                 # replay_mode/inhibition_bias/revision_bias/
                                 # safety_ok/details even though phase6a's own
                                 # authoritative CREATE TABLE IF NOT EXISTS
                                 # (in ensure_phase6a_schema) and its INSERT
                                 # statement both already used them. Because
                                 # central bootstrap runs first and phase6a's
                                 # own "IF NOT EXISTS" is then a no-op with no
                                 # matching ALTER TABLE fallback for these
                                 # specific columns, every real cycle failed
                                 # with "table ... has no column named
                                 # replay_mode" as soon as phase6a tried to
                                 # record its first replay cycle. Synced to
                                 # match phase6a's own full column list.
                                 ('replay_mode', 'TEXT'),
                                 ('candidate_count', 'INTEGER'),
                                 ('replay_events', 'INTEGER'),
                                 ('avg_outcome_score', 'REAL'),
                                 ('avg_closure_delta', 'REAL'),
                                 ('avg_overlap_score', 'REAL'),
                                 ('persistent_gap_pressure', 'REAL'),
                                 ('plasticity_level', 'REAL'),
                                 ('exploration_bias', 'REAL'),
                                 ('consolidation_bias', 'REAL'),
                                 ('inhibition_bias', 'REAL DEFAULT 0'),
                                 ('revision_bias', 'REAL DEFAULT 0'),
                                 ('safety_ok', 'INTEGER DEFAULT 1'),
                                 ('details', 'TEXT'),
                                 ('created_at', 'INTEGER'),
        ('population_available', 'INTEGER DEFAULT 0'),
        ('outcome_observation_available', 'INTEGER DEFAULT 0'),
        ('outcome_observation_count', 'INTEGER DEFAULT 0'),
        ('evidence_state', 'TEXT'),
        ('evidence_reason', 'TEXT')
    ],
 'phase6a_meta_plasticity_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')],
 'phase6a_neuromodulated_sleep_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')],
 # BRAINSTEM_TONIC_PHASIC_INTEGRATION_V1 (23.09.2026): mirrored here per
 # project convention (every schema change is tracked in this central
 # SCHEMA_TABLES alongside its owning module's own ensure_schema()). See
 # v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release.py
 # and v8_cooperative_core_neuromodulator_sleep_authority_release.py for
 # the full architecture note and column-level documentation.
 'phase6a_neuromodulator_integration_events': [
     ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
     ('created_at', 'INTEGER'),
     ('parameter', 'TEXT'),
     ('phasic_value', 'REAL DEFAULT 0'),
     ('tonic_target', 'REAL DEFAULT 0'),
     ('tonic_weight', 'REAL DEFAULT 0'),
     ('phasic_contribution', 'REAL DEFAULT 0'),
     ('tonic_contribution', 'REAL DEFAULT 0'),
     ('final_value', 'REAL DEFAULT 0'),
     ('driver_botenstoff', 'TEXT'),
     ('driver_botenstoff_value', 'REAL DEFAULT 0'),
 ],
 'cooperative_core_target_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')],
 # BRAINSTEM_SCHEMA_CENTRALIZATION_GAP_FIX_V1 (23.09.2026): this table was
 # previously ONLY ever created by memory.py's own Memory._init()
 # executescript(), never mirrored here in the central schema authority --
 # the same central-schema gap as facts.source_hypothesis_id above (see
 # that comment). Column list matches memory.py's own CREATE TABLE exactly
 # (id/subject/relation/value_a/value_b/status/details_json/created_at),
 # so both remain fully compatible; whichever authority runs first wins,
 # the other's CREATE TABLE IF NOT EXISTS becomes a no-op.
 'contradictions': [('id', 'INTEGER PRIMARY KEY'),
                    ('subject', 'TEXT'),
                    ('relation', 'TEXT'),
                    ('value_a', 'TEXT'),
                    ('value_b', 'TEXT'),
                    ('status', 'TEXT'),
                    ('details_json', 'TEXT'),
                    ('created_at', 'INTEGER')],
 'attention_queue_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER DEFAULT 0')],
 'chunk_attention_scores': [('chunk_id', 'INTEGER PRIMARY KEY'),
                            ('attention_score', 'REAL DEFAULT 0'),
                            ('novelty_score', 'REAL DEFAULT 0'),
                            ('uncertainty_score', 'REAL DEFAULT 0'),
                            ('reward_score', 'REAL DEFAULT 0'),
                            ('fatigue_score', 'REAL DEFAULT 0'),
                            ('last_reason', 'TEXT'),
                            ('updated_at', 'INTEGER DEFAULT 0'),
                            ('phase5b_score', 'REAL DEFAULT 0'),
                            ('phase5b_reason', 'TEXT'),
                            ('phase5b_last_adjusted_at', 'INTEGER DEFAULT 0'),
                            ('diversity_score', 'REAL DEFAULT 0'),
                            ('resolution_support_score', 'REAL DEFAULT 0'),
                            ('strategy_effectiveness_score', 'REAL DEFAULT 0'),
                            ('learning_outcome_score', 'REAL DEFAULT 0'),
                            ('active_learning_score', 'REAL DEFAULT 0'),
                            ('progress_adjusted_score', 'REAL DEFAULT 0'),
                            ('strategy_reason', 'TEXT'),
                            ('phase5a_attention_score', 'REAL DEFAULT 0'),
                            ('phase5a_strategy_reason', 'TEXT'),
                            ('phase5a_last_integrated_at', 'INTEGER DEFAULT 0'),
                            ('last_outcome_tracked_at', 'INTEGER DEFAULT 0'),
                            ('outcome_tracking_reason', 'TEXT'),
                            ('last_strategy_feedback_at', 'INTEGER DEFAULT 0'),
                            ('strategy_feedback_reason', 'TEXT'),
                            ('progress_adjustment_reason', 'TEXT'),
                            ('learning_rate', 'REAL DEFAULT 0'),
                            ('error_weight', 'REAL DEFAULT 0'),
                            ('revision_pressure', 'REAL DEFAULT 0'),
                            ('consolidation_gain', 'REAL DEFAULT 0'),
                            ('exploration_pressure', 'REAL DEFAULT 0'),
                            ('inhibition_level', 'REAL DEFAULT 0'),
                            ('phase5f_score', 'REAL DEFAULT 0'),
                            ('phase5f_reason', 'TEXT'),
                            ('phase5f_last_adjusted_at', 'INTEGER DEFAULT 0'),
                            ('phase5f_window_strategy', 'TEXT'),
                            ('phase5f_window_radius', 'INTEGER DEFAULT 0'),
                            ('phase5f_effectiveness_score', 'REAL DEFAULT 0'),
                            ('phase5f_read_outcome_score', 'REAL DEFAULT 0'),
                            ('phase5f_overlap_score', 'REAL DEFAULT 0'),
                            ('phase5g_score', 'REAL DEFAULT 0'),
                            ('phase5g_selected_strategy', 'TEXT'),
                            ('phase5g_strategy_score', 'REAL DEFAULT 0'),
                            ('phase5g_closure_delta', 'REAL DEFAULT 0'),
                            ('phase5g_no_candidate_rate', 'REAL DEFAULT 0'),
                            ('phase5g_overlap_score', 'REAL DEFAULT 0'),
                            ('phase5g_last_selected_at', 'INTEGER DEFAULT 0'),
                            ('phase5g_reason', 'TEXT'),
                            ('phase5h_strategy_outcome_score', 'REAL DEFAULT 0'),
                            ('phase5h_strategy_memory_key', 'TEXT'),
                            ('phase5h_last_outcome_at', 'INTEGER DEFAULT 0'),
                            ('phase5h_recommendation', 'TEXT'),
                            ('phase5h_reason', 'TEXT'),
                            ('phase5i_score', 'REAL DEFAULT 0'),
                            ('phase5i_selected_strategy', 'TEXT'),
                            ('phase5i_strategy_score', 'REAL DEFAULT 0'),
                            ('phase5i_expected_outcome_score', 'REAL DEFAULT 0'),
                            ('phase5i_expected_closure_delta', 'REAL DEFAULT 0'),
                            ('phase5i_expected_overlap_score', 'REAL DEFAULT 0'),
                            ('phase5i_expected_no_candidate_rate', 'REAL DEFAULT 0'),
                            ('phase5i_last_adjusted_at', 'INTEGER'),
                            ('phase5i_reason', 'TEXT'),
                            ('phase6a_sleep_priority', 'REAL DEFAULT 0'),
                            ('phase6a_replay_weight', 'REAL DEFAULT 0'),
                            ('phase6a_meta_plasticity', 'REAL DEFAULT 0'),
                            ('phase6a_last_adjusted_at', 'INTEGER'),
                            ('phase6a_reason', 'TEXT'),
                            # BRAINSTEM_QUESTION_CHUNK_FEEDBACK_V1 (25
                            # September 2026): mirrors the identically-named
                            # reading_queue columns above; see that
                            # declaration's own comment for the full
                            # rationale.
                            ('question_feedback_score', 'REAL DEFAULT 0'),
                            ('question_feedback_reason', 'TEXT'),
                            ('question_feedback_question_id', 'INTEGER'),
                            ('question_feedback_last_adjusted_at', 'INTEGER DEFAULT 0')],
 'context_learning_events': [('id', 'INTEGER PRIMARY KEY'),
                             ('hypothesis_id', 'INTEGER'),
                             ('event_type', 'TEXT'),
                             ('role', 'TEXT'),
                             ('details', 'TEXT'),
                             ('dopamine', 'REAL DEFAULT 0'),
                             ('serotonin', 'REAL DEFAULT 0'),
                             ('glutamate', 'REAL DEFAULT 0'),
                             ('gaba', 'REAL DEFAULT 0'),
                             ('noradrenaline', 'REAL DEFAULT 0'),
                             ('acetylcholine', 'REAL DEFAULT 0'),
                             ('created_at', 'INTEGER DEFAULT 0')],
 'context_pattern_memory': [('pattern_key', 'TEXT PRIMARY KEY'),
                            ('role', 'TEXT'),
                            ('seen_count', 'INTEGER DEFAULT 0'),
                            ('avg_confidence', 'REAL DEFAULT 0'),
                            ('avg_uncertainty', 'REAL DEFAULT 0'),
                            ('stability', 'REAL DEFAULT 0'),
                            ('updated_at', 'INTEGER DEFAULT 0')],
 'context_role_stats': [('role', 'TEXT PRIMARY KEY'),
                        ('seen', 'INTEGER DEFAULT 0'),
                        ('seen_count', 'INTEGER DEFAULT 0'),
                        ('avg_confidence', 'REAL DEFAULT 0'),
                        ('avg_uncertainty', 'REAL DEFAULT 0'),
                        ('feedback_count', 'INTEGER DEFAULT 0'),
                        ('error_count', 'INTEGER DEFAULT 0'),
                        ('updated_at', 'INTEGER DEFAULT 0')],
 'hypothesis_clusters': [('cluster_key', 'TEXT PRIMARY KEY'),
                         ('role', 'TEXT'),
                         ('size', 'INTEGER DEFAULT 0'),
                         ('avg_confidence', 'REAL DEFAULT 0'),
                         ('avg_uncertainty', 'REAL DEFAULT 0'),
                         ('stability', 'REAL DEFAULT 0'),
                         ('example', 'TEXT'),
                         ('updated_at', 'INTEGER DEFAULT 0')],
 'hypothesis_error_events': [('id', 'INTEGER PRIMARY KEY'),
                             ('hypothesis_id', 'INTEGER'),
                             ('error_type', 'TEXT'),
                             ('severity', 'REAL DEFAULT 0'),
                             ('details', 'TEXT'),
                             ('created_at', 'INTEGER DEFAULT 0'),
                             ('reason', 'TEXT'),
                             ('role', 'TEXT'),
                             ('error_signal', 'REAL DEFAULT 0')],
 'hypothesis_feedback': [('id', 'INTEGER PRIMARY KEY'),
                         ('hypothesis_id', 'INTEGER'),
                         ('feedback_type', 'TEXT'),
                         ('signal', 'REAL DEFAULT 0'),
                         ('reason', 'TEXT'),
                         ('details', 'TEXT'),
                         ('created_at', 'INTEGER DEFAULT 0')],
 'hypothesis_revisions': [('id', 'INTEGER PRIMARY KEY'),
                          ('hypothesis_id', 'INTEGER'),
                          ('old_role', 'TEXT'),
                          ('new_role', 'TEXT'),
                          ('reason', 'TEXT'),
                          ('details', 'TEXT'),
                          ('created_at', 'INTEGER DEFAULT 0'),
                          ('old_confidence', 'REAL DEFAULT 0'),
                          ('new_confidence', 'REAL DEFAULT 0'),
                          ('old_uncertainty', 'REAL DEFAULT 1'),
                          ('new_uncertainty', 'REAL DEFAULT 1')],
 'hypothesis_stability_scores': [('hypothesis_id', 'INTEGER PRIMARY KEY'),
                                 ('stability', 'REAL DEFAULT 0'),
                                 ('confidence', 'REAL DEFAULT 0'),
                                 ('uncertainty', 'REAL DEFAULT 0'),
                                 ('feedback_count', 'INTEGER DEFAULT 0'),
                                 ('error_count', 'INTEGER DEFAULT 0'),
                                 ('updated_at', 'INTEGER DEFAULT 0'),
                                 ('role', 'TEXT'),
                                 ('evidence_count', 'INTEGER DEFAULT 0'),
                                 ('conflict_count', 'INTEGER DEFAULT 0'),
                                 ('last_reason', 'TEXT')],
 'learning_strategy_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER DEFAULT 0')],
 'neuromodulated_attention_events': [('id', 'INTEGER PRIMARY KEY'),
                                     ('chunk_id', 'INTEGER'),
                                     ('hypothesis_id', 'INTEGER'),
                                     ('event_type', 'TEXT'),
                                     ('novelty', 'REAL DEFAULT 0'),
                                     ('uncertainty', 'REAL DEFAULT 0'),
                                     ('reward', 'REAL DEFAULT 0'),
                                     ('fatigue', 'REAL DEFAULT 0'),
                                     ('dopamine', 'REAL DEFAULT 0'),
                                     ('serotonin', 'REAL DEFAULT 0'),
                                     ('glutamate', 'REAL DEFAULT 0'),
                                     ('gaba', 'REAL DEFAULT 0'),
                                     ('noradrenaline', 'REAL DEFAULT 0'),
                                     ('acetylcholine', 'REAL DEFAULT 0'),
                                     ('created_at', 'INTEGER DEFAULT 0'),
                                     ('attention_reason', 'TEXT'),
                                     ('attention_score', 'REAL DEFAULT 0'),
                                     ('summary', 'TEXT'),
                                     ('details', 'TEXT')],
 'neuromodulator_sleep_events': [('id', 'INTEGER PRIMARY KEY'),
                                 ('event_type', 'TEXT'),
                                 ('details', 'TEXT'),
                                 ('dopamine', 'REAL DEFAULT 0'),
                                 ('serotonin', 'REAL DEFAULT 0'),
                                 ('glutamate', 'REAL DEFAULT 0'),
                                 ('gaba', 'REAL DEFAULT 0'),
                                 ('noradrenaline', 'REAL DEFAULT 0'),
                                 ('acetylcholine', 'REAL DEFAULT 0'),
                                 ('created_at', 'INTEGER DEFAULT 0'),
                                 ('summary', 'TEXT')],
 'reading_queue': [('chunk_id', 'INTEGER PRIMARY KEY'),
                   ('priority', 'REAL DEFAULT 0'),
                   ('reason', 'TEXT'),
                   ('attention_score', 'REAL DEFAULT 0'),
                   ('read_count', 'INTEGER DEFAULT 0'),
                   ('status', "TEXT DEFAULT 'pending'"),
                   ('last_read', 'INTEGER DEFAULT 0'),
                   ('updated_at', 'INTEGER DEFAULT 0'),
                   ('phase5b_priority', 'REAL DEFAULT 0'),
                   ('phase5b_reason', 'TEXT'),
                   ('phase5b_last_adjusted_at', 'INTEGER DEFAULT 0'),
                   ('cooldown_until', 'INTEGER DEFAULT 0'),
                   ('phase5a_priority', 'REAL DEFAULT 0'),
                   ('phase5a_reason', 'TEXT'),
                   ('phase5a_updated_at', 'INTEGER DEFAULT 0'),
                   ('active_learning_priority', 'REAL DEFAULT 0'),
                   ('phase5f_priority', 'REAL DEFAULT 0'),
                   ('phase5f_reason', 'TEXT'),
                   ('phase5f_last_adjusted_at', 'INTEGER DEFAULT 0'),
                   ('phase5f_window_strategy', 'TEXT'),
                   ('phase5f_window_radius', 'INTEGER DEFAULT 0'),
                   ('phase5f_no_candidate_penalty', 'REAL DEFAULT 0'),
                   ('phase5g_score', 'REAL DEFAULT 0'),
                   ('phase5g_selected_strategy', 'TEXT'),
                   ('phase5g_strategy_score', 'REAL DEFAULT 0'),
                   ('phase5g_closure_delta', 'REAL DEFAULT 0'),
                   ('phase5g_no_candidate_rate', 'REAL DEFAULT 0'),
                   ('phase5g_overlap_score', 'REAL DEFAULT 0'),
                   ('phase5g_last_selected_at', 'INTEGER DEFAULT 0'),
                   ('phase5g_reason', 'TEXT'),
                   ('phase5h_strategy_outcome_score', 'REAL DEFAULT 0'),
                   ('phase5h_strategy_memory_key', 'TEXT'),
                   ('phase5h_last_outcome_at', 'INTEGER DEFAULT 0'),
                   ('phase5h_recommendation', 'TEXT'),
                   ('phase5h_reason', 'TEXT'),
                   ('phase5i_priority', 'REAL DEFAULT 0'),
                   ('phase5i_selected_strategy', 'TEXT'),
                   ('phase5i_strategy_score', 'REAL DEFAULT 0'),
                   ('phase5i_expected_outcome_score', 'REAL DEFAULT 0'),
                   ('phase5i_expected_closure_delta', 'REAL DEFAULT 0'),
                   ('phase5i_expected_overlap_score', 'REAL DEFAULT 0'),
                   ('phase5i_expected_no_candidate_rate', 'REAL DEFAULT 0'),
                   ('phase5i_last_adjusted_at', 'INTEGER'),
                   ('phase5i_reason', 'TEXT'),
                   ('phase6a_sleep_priority', 'REAL DEFAULT 0'),
                   ('phase6a_replay_weight', 'REAL DEFAULT 0'),
                   ('phase6a_meta_plasticity', 'REAL DEFAULT 0'),
                   ('phase6a_last_adjusted_at', 'INTEGER'),
                   ('phase6a_reason', 'TEXT'),
                   # BRAINSTEM_QUESTION_CHUNK_FEEDBACK_V1 (25 September
                   # 2026): additive columns for v8_stageb_question_
                   # chunk_feedback_release.py, following this table's own
                   # already-established per-phase column-triplet
                   # convention (score/reason/last_adjusted_at, e.g.
                   # phase5f_priority/phase5f_reason/phase5f_last_
                   # adjusted_at above). Closes the Questions Slice 3
                   # audit's "rein schreibender Blinddarm" finding: this is
                   # the first and only module that ever reads the
                   # questions table to influence real system behavior.
                   # question_feedback_question_id records exactly which
                   # still-open question caused the most recent boost, for
                   # traceability/debugging.
                   ('question_feedback_priority', 'REAL DEFAULT 0'),
                   ('question_feedback_reason', 'TEXT'),
                   ('question_feedback_question_id', 'INTEGER'),
                   ('question_feedback_last_adjusted_at', 'INTEGER DEFAULT 0')],
 'reading_strategy_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER DEFAULT 0')],
 'rollback_safe_core_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER DEFAULT 0')],
 'phase5g_strategy_selection_memory': [('memory_key', 'TEXT PRIMARY KEY'),
                                       ('gap_type', 'TEXT'),
                                       ('role', 'TEXT'),
                                       ('strategy', 'TEXT'),
                                       ('observations', 'INTEGER DEFAULT 0'),
                                       ('avg_closure_delta', 'REAL DEFAULT 0'),
                                       ('avg_no_candidate_rate', 'REAL DEFAULT 0'),
                                       ('avg_overlap_score', 'REAL DEFAULT 0'),
                                       ('avg_effectiveness', 'REAL DEFAULT 0'),
                                       ('avg_outcome_score', 'REAL DEFAULT 0'),
                                       ('avg_expected_gain', 'REAL DEFAULT 0'),
                                       ('dopamine', 'REAL DEFAULT 0'),
                                       ('serotonin', 'REAL DEFAULT 0'),
                                       ('glutamate', 'REAL DEFAULT 0'),
                                       ('gaba', 'REAL DEFAULT 0'),
                                       ('noradrenaline', 'REAL DEFAULT 0'),
                                       ('acetylcholine', 'REAL DEFAULT 0'),
                                       ('recommendation', 'TEXT'),
                                       ('status', "TEXT DEFAULT 'observe'"),
                                       ('details', 'TEXT'),
                                       ('first_seen', 'INTEGER'),
                                       ('last_seen', 'INTEGER'),
                                       ('updated_at', 'INTEGER'),
                                       ('selected_strategy', 'TEXT'),
                                       ('avg_strategy_score', 'REAL DEFAULT 0'),
                                       ('success_count', 'INTEGER DEFAULT 0'),
                                       ('failure_count', 'INTEGER DEFAULT 0'),
                                       ('neuromodulator_profile', 'TEXT'),
                                       ('created_at', 'INTEGER DEFAULT 0'),
                                       ('phase5i_diversification_score', 'REAL DEFAULT 0'),
                                       ('phase5i_last_used_at', 'INTEGER'),
                                       ('phase5i_recommendation', 'TEXT')],
 'phase5h_experiment_outcome_cycles': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                       ('phase', 'TEXT'),
                                       ('experiments_seen', 'INTEGER DEFAULT 0'),
                                       ('outcomes_written', 'INTEGER DEFAULT 0'),
                                       ('memory_updates', 'INTEGER DEFAULT 0'),
                                       ('avg_outcome_score', 'REAL DEFAULT 0'),
                                       ('avg_closure_delta', 'REAL DEFAULT 0'),
                                       ('avg_no_candidate_rate', 'REAL DEFAULT 0'),
                                       ('avg_overlap_score', 'REAL DEFAULT 0'),
                                       ('recommendation', 'TEXT'),
                                       ('safety_ok', 'INTEGER DEFAULT 1'),
                                       ('no_word_blacklists', "TEXT DEFAULT 'true'"),
                                       ('fact_promotion', "TEXT DEFAULT 'disabled'"),
                                       ('facts', 'INTEGER DEFAULT 0'),
                                       ('relations', 'INTEGER DEFAULT 0'),
                                       ('questions', 'INTEGER DEFAULT 0'),
                                       ('created_at', 'INTEGER DEFAULT 0')],
 'phase5g_strategy_experiments': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                  ('gap_id', 'INTEGER'),
                                  ('gap_key', 'TEXT'),
                                  ('gap_type', 'TEXT'),
                                  ('role', 'TEXT'),
                                  ('source_strategy', 'TEXT'),
                                  ('selected_strategy', 'TEXT'),
                                  ('previous_best_strategy', 'TEXT'),
                                  ('center_chunk_id', 'INTEGER'),
                                  ('target_chunk_id', 'INTEGER'),
                                  ('window_radius', 'INTEGER DEFAULT 0'),
                                  ('expected_gain', 'REAL DEFAULT 0'),
                                  ('predicted_effectiveness', 'REAL DEFAULT 0'),
                                  ('observed_closure_delta', 'REAL DEFAULT 0'),
                                  ('no_candidate_rate', 'REAL DEFAULT 0'),
                                  ('overlap_score', 'REAL DEFAULT 0'),
                                  ('exploration_pressure', 'REAL DEFAULT 0'),
                                  ('inhibition_level', 'REAL DEFAULT 0'),
                                  ('learning_rate', 'REAL DEFAULT 0'),
                                  ('error_weight', 'REAL DEFAULT 0'),
                                  ('revision_pressure', 'REAL DEFAULT 0'),
                                  ('decision', 'TEXT'),
                                  ('outcome', "TEXT DEFAULT 'pending'"),
                                  ('details', 'TEXT'),
                                  ('created_at', 'INTEGER'),
                                  ('updated_at', 'INTEGER'),
                                  ('experiment_key', 'TEXT'),
                                  ('source_chunk_id', 'INTEGER'),
                                  ('strategy', 'TEXT'),
                                  ('window_strategy', 'TEXT'),
                                  ('read_status', 'TEXT'),
                                  ('before_score', 'REAL DEFAULT 0'),
                                  ('after_score', 'REAL DEFAULT 0'),
                                  ('closure_delta', 'REAL DEFAULT 0'),
                                  ('strategy_score', 'REAL DEFAULT 0'),
                                  ('effectiveness_score', 'REAL DEFAULT 0'),
                                  ('outcome_score', 'REAL DEFAULT 0'),
                                  ('outcome_label', 'TEXT'),
                                  ('recommendation', 'TEXT'),
                                  ('phase5h_outcome_score', 'REAL DEFAULT 0'),
                                  ('phase5h_outcome_label', 'TEXT'),
                                  ('phase5h_last_evaluated_at', 'INTEGER DEFAULT 0'),
                                  ('phase5h_memory_key', 'TEXT'),
                                  ('phase5h_reason', 'TEXT')],
 'phase5h_experiment_learning_events': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                        ('experiment_key', 'TEXT'),
                                        ('outcome_key', 'TEXT'),
                                        ('selected_strategy', 'TEXT'),
                                        ('gap_type', 'TEXT'),
                                        ('role', 'TEXT'),
                                        ('target_chunk_id', 'INTEGER'),
                                        ('outcome_score', 'REAL DEFAULT 0'),
                                        ('closure_delta', 'REAL DEFAULT 0'),
                                        ('no_candidate_rate', 'REAL DEFAULT 0'),
                                        ('overlap_score', 'REAL DEFAULT 0'),
                                        ('strategy_score', 'REAL DEFAULT 0'),
                                        ('recommendation', 'TEXT'),
                                        ('event_type', 'TEXT'),
                                        ('details', 'TEXT'),
                                        ('created_at', 'INTEGER')],
 'phase5i_outcome_driven_experiments': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                        ('experiment_key', 'TEXT'),
                                        ('gap_id', 'INTEGER'),
                                        ('gap_key', 'TEXT'),
                                        ('gap_type', 'TEXT'),
                                        ('role', 'TEXT'),
                                        ('center_chunk_id', 'INTEGER'),
                                        ('target_chunk_id', 'INTEGER'),
                                        ('selected_strategy', 'TEXT'),
                                        ('previous_strategy', 'TEXT'),
                                        ('strategy_score', 'REAL DEFAULT 0'),
                                        ('expected_outcome_score', 'REAL DEFAULT 0'),
                                        ('expected_closure_delta', 'REAL DEFAULT 0'),
                                        ('expected_overlap_score', 'REAL DEFAULT 0'),
                                        ('expected_no_candidate_rate', 'REAL DEFAULT 0'),
                                        ('learning_rate', 'REAL DEFAULT 0'),
                                        ('error_weight', 'REAL DEFAULT 0'),
                                        ('revision_pressure', 'REAL DEFAULT 0'),
                                        ('exploration_pressure', 'REAL DEFAULT 0'),
                                        ('inhibition_level', 'REAL DEFAULT 0'),
                                        ('consolidation_gain', 'REAL DEFAULT 0'),
                                        ('dopamine', 'REAL DEFAULT 0'),
                                        ('serotonin', 'REAL DEFAULT 0'),
                                        ('glutamate', 'REAL DEFAULT 0'),
                                        ('gaba', 'REAL DEFAULT 0'),
                                        ('noradrenaline', 'REAL DEFAULT 0'),
                                        ('acetylcholine', 'REAL DEFAULT 0'),
                                        ('reason', 'TEXT'),
                                        ('details', 'TEXT'),
                                        ('created_at', 'INTEGER'),
                                        ('updated_at', 'INTEGER')],
 # BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): the six
 # 'modern_outcome_bridge_shadow[_cycles/_state]' and
 # 'modern_gap_candidate_shadow[_cycles/_state]' table declarations that
 # used to sit here have been removed together with every module that
 # ever wrote to them (v8_modern_gap_candidate_bridge_shadow_release,
 # v8_modern_gap_phase5f_shadow_observation[_v2]_release,
 # v8_modern_gap_phase5f_shadow_history_release,
 # v8_modern_outcome_bridge_shadow_release,
 # v8_stable_obs_content_fp_shadow_classifier_release). Removing the
 # declarations here only stops these tables from being (re-)created on a
 # fresh database; it does not touch any already-existing production
 # database. See the Legacy Report shipped with this cleanup for the
 # full verification trail and for an optional, separate, read-only-first
 # migration script to retire the tables in an existing database.
 }
BASE_SCHEMA = SCHEMA_TABLES

PHASE_REGISTRY: List[Tuple[str, str]] = [
    # BRAINSTEM_LEXICAL_LAYER_BOOTSTRAP_REGISTRATION_V1: registered here so
    # the new module's own tables/columns are ensured explicitly at
    # database-bootstrap time (visible in the bootstrap report), in
    # addition to the module's own self-healing ensure_schema() call that
    # already runs defensively on its own first real cycle regardless.
    ("v8_phase0_lexical_boundary_observation_release", "phase0_lexical"),
    ("v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release", "phase6a"),
    ("v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "phase6b"),
    ("v8_phase6c_bias_persistence_and_self_regulating_meta_release", "phase6c"),
    ("v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "phase6d"),
    ("v8_phase7a_adenosine_homeostat_release", "phase7a"),
    ("v8_phase7b_endocannabinoid_retrograde_gain_control_release", "phase7b"),
    ("v8_stageb_guarded_hypothesis_graduation_release", "stageb_graduation"),
    # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_REVIEW_FIX_V1 (25 September 2026)
    #
    # Root cause, found during the Slice 1 internal review: both new Slice 1
    # modules (v8_phase0b_relational_binding_observation_release.py and
    # v8_stageb_relation_promotion_release.py) already expose their own
    # ensure_schema(con) functions and are correctly self-healing on their
    # own first real cycle -- but, unlike every other Stage-B module (gap
    # detection, contradiction detection, hypothesis revision, fact
    # promotion, graduation, all registered above/below), neither was ever
    # added to this bootstrap-time PHASE_REGISTRY list. Confirmed
    # reproducible: a fresh ensure_database_exists() call does not create
    # phase0b_relational_state, stageb_relation_promotion_state, or
    # stageb_relation_promotion_events, so any tooling (e.g. the new
    # diagnose_relational_binding_calibration.py) or GUI feature that reads
    # or writes those tables before the module's own first real cycle has
    # run fails with "no such table" -- exactly the same class of gap this
    # project's own BRAINSTEM_LEXICAL_LAYER_BOOTSTRAP_REGISTRATION_V1
    # comment above (for Phase 0 lexical) was written to prevent. Fixed by
    # registering both here, matching that exact same convention.
    ("v8_phase0b_relational_binding_observation_release", "phase0b_relational"),
    ("v8_stageb_relation_promotion_release", "stageb_relation_promotion"),
    # BRAINSTEM_ONTOLOGY_EMERGENCE_SLICE2_V1 (25 September 2026): registered
    # here from the start (not retrofitted after the fact), applying the
    # exact lesson from the Slice 1 internal review directly above -- both
    # new Slice 2 modules are registered immediately, matching the same
    # bootstrap-registration convention already established for every other
    # Stage-B module.
    ("v8_stageb_ontology_cluster_observation_release", "stageb_ontology_cluster_observation"),
    ("v8_stageb_ontology_promotion_release", "stageb_ontology_promotion"),
    ("v8_stageb_gapflow_runtime_contract_release", "stageb_ef"),
    # BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): the
    # 'v8_non_productive_recheck_canonical_autoload_shadow_runtime_
    # integration_v1' entry that used to sit here has been removed
    # together with the module itself and its entire dependency chain.
    # See the Legacy Report shipped with this cleanup.
]

def register_phase_module(module_name, phase_name):
    for m, _ in PHASE_REGISTRY:
        if m == module_name:
            return
    PHASE_REGISTRY.append((module_name, phase_name))

def _table_exists(con, table):
    return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _columns(con, table):
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]

def _apply_base_schema(con):
    report = {"created_tables": [], "added_columns": []}
    for table, cols in SCHEMA_TABLES.items():
        if not _table_exists(con, table):
            col_defs = ", ".join(name + " " + spec for name, spec in cols)
            con.execute("CREATE TABLE " + table + " (" + col_defs + ")")
            report["created_tables"].append(table)
        else:
            existing = set(_columns(con, table))
            for name, spec in cols:
                if name in existing: continue
                spec_up = spec.upper()
                if "PRIMARY KEY" in spec_up or "AUTOINCREMENT" in spec_up: continue
                con.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + spec)
                report["added_columns"].append(table + "." + name)
    con.commit()
    return report

SCHEMA_INDEXES = [('idx_bs_attention_queue_state_key_uniq', 'attention_queue_state', ('key',), True),
 ('idx_bs_chunk_attention_scores_chunk_id_uniq', 'chunk_attention_scores', ('chunk_id',), True),
 ('idx_bs_context_hypotheses_signature', 'context_hypotheses', ('signature',), False),
 ('idx_bs_context_hypotheses_role', 'context_hypotheses', ('role',), False),
 ('idx_bs_context_pattern_memory_pattern_key_uniq', 'context_pattern_memory', ('pattern_key',), True),
 ('idx_bs_context_role_stats_role_uniq', 'context_role_stats', ('role',), True),
 ('idx_bs_hypothesis_clusters_cluster_key_uniq', 'hypothesis_clusters', ('cluster_key',), True),
 ('idx_bs_hypothesis_stability_scores_hypothesis_id_uniq', 'hypothesis_stability_scores', ('hypothesis_id',), True),
 ('idx_bs_learning_strategy_state_key_uniq', 'learning_strategy_state', ('key',), True),
 ('idx_bs_reading_queue_chunk_id_uniq', 'reading_queue', ('chunk_id',), True),
 ('idx_bs_reading_strategy_state_key_uniq', 'reading_strategy_state', ('key',), True),
 ('idx_bs_rollback_safe_core_state_key_uniq', 'rollback_safe_core_state', ('key',), True),
 # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_V1 (25 September 2026): enforces
 # exactly one row per ordered (signature_a, signature_b) pair in
 # relational_cooccurrence_counts, used by
 # v8_phase0b_relational_binding_observation_release.py's own
 # INSERT ... ON CONFLICT(signature_a, signature_b) DO UPDATE upsert.
 ('idx_bs_relational_cooccurrence_pair_uniq', 'relational_cooccurrence_counts', ('signature_a', 'signature_b'), True)]


def _self_check_schema(con):
    missing = []
    for table, columns in SCHEMA_TABLES.items():
        if not _table_exists(con, table):
            missing.append(table)
            continue
        existing = _columns(con, table)
        for name, _spec in columns:
            if name not in existing:
                missing.append(table + "." + name)
    if missing:
        raise RuntimeError("Central schema missing: " + ", ".join(missing))
    return True


def _apply_schema_indexes(con):
    for name, table, columns, unique in SCHEMA_INDEXES:
        if not _table_exists(con, table):
            continue
        existing = _columns(con, table)
        if any(column not in existing for column in columns):
            continue
        sql = "CREATE " + ("UNIQUE " if unique else "") + "INDEX IF NOT EXISTS " + name + " ON " + table + "(" + ",".join(columns) + ")"
        try:
            con.execute(sql)
        except sqlite3.IntegrityError:
            if not unique:
                raise


def ensure_schema_for(obj):
    own = False
    con = None
    if isinstance(obj, sqlite3.Connection):
        con = obj
    elif isinstance(obj, (str, os.PathLike, Path)):
        con = sqlite3.connect(str(obj)); own = True
    else:
        for attr in ("db", "conn", "con"):
            value = getattr(obj, attr, None)
            if isinstance(value, sqlite3.Connection):
                con = value; break
        if con is None:
            for attr in ("db_path", "path"):
                value = getattr(obj, attr, None)
                if value:
                    con = sqlite3.connect(str(value)); own = True; break
    if con is None:
        raise RuntimeError("Central schema could not locate sqlite connection")
    try:
        _apply_base_schema(con)
        _apply_schema_indexes(con)
        _self_check_schema(con)
        _apply_schema_indexes(con)
        _self_check_schema(con)
        con.commit()
        return True
    finally:
        if own:
            con.close()


def _bootstrap_phase_modules(con):
    # BRAINSTEM_BOOTSTRAP_NAMING_FIX_V1: some phase modules (e.g. phase6a) do
    # not expose a function literally named "ensure_schema" but instead use a
    # phase-specific name such as "ensure_phase6a_schema". The previous lookup
    # only tried the generic name and silently skipped such modules with no
    # error and no entry in "errors", which looked like a clean bootstrap even
    # though the phase's own tables/columns were never explicitly ensured
    # here (they were only created lazily the first time the phase itself ran
    # a real cycle). We now also try the phase-specific convention.
    bootstrapped, phase_reports, errors = [], {}, []
    for mod_name, phase_name in PHASE_REGISTRY:
        try:
            mod = importlib.import_module("ki_system." + mod_name)
        except ImportError:
            continue
        except Exception as exc:
            errors.append((phase_name, "import_error: " + str(exc)))
            continue
        fn = getattr(mod, "ensure_schema", None)
        if fn is None:
            fn = getattr(mod, "ensure_" + phase_name + "_schema", None)
        if fn is None:
            continue
        try:
            r = fn(con)
            phase_reports[phase_name] = r
            bootstrapped.append(phase_name)
        except Exception as exc:
            errors.append((phase_name, "ensure_schema_error: " + str(exc)))
    con.commit()
    return bootstrapped, phase_reports, errors
_PERF_INDEXES = [
    ("hypothesis_learning_updates", "hypothesis_id", "idx_hlu_hyp"),
    ("hypothesis_feedback", "hypothesis_id", "idx_hfb_hyp"),
    ("hypothesis_error_events", "hypothesis_id", "idx_hee_hyp"),
    ("hypothesis_stability_scores", "hypothesis_id", "idx_hss_hyp"),
    ("phase5f_context_window_experiments", "target_chunk_id", "idx_p5f_tgt"),
]

def ensure_perf_indexes(con):
    created = []
    for table, col, name in _PERF_INDEXES:
        try:
            if not _table_exists(con, table):
                continue
            if col not in _columns(con, table):
                continue
            exists = con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
            if exists:
                continue
            con.execute("CREATE INDEX IF NOT EXISTS " + name + " ON " + table + "(" + col + ")")
            created.append(name)
        except Exception:
            continue
    con.commit()
    return created
# BRAINSTEM_SHADOW_CASCADE_CLEANUP_V1 (24 September 2026): the
# _bootstrap_shadow_modules() function that used to sit here has been
# removed together with the five standalone shadow/observation modules
# it bootstrapped (modern_gap_phase5f_shadow_observation[_v2]/_history,
# stable_obs_content_fp_shadow_classifier, phase6a_replay_control_shadow).
# All five were confirmed, by exhaustive cross-reference across the whole
# codebase, to feed only each other and never a consumer outside their
# own cascade. See the Legacy Report shipped with this cleanup for the
# full verification trail.


def ensure_database_exists(db_path):
    p = Path(db_path)
    db_created = not p.exists()
    if db_created:
        p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p), timeout=30.0)
    try:
        try: con.execute("PRAGMA journal_mode=WAL")
        except Exception: pass
        base_report = _apply_base_schema(con)
        # BRAINSTEM_BOOTSTRAP_SELF_CHECK_V1: fail loudly if the central schema
        # authority itself is inconsistent right after it was applied.
        _self_check_schema(con)
        bootstrapped, phase_reports, errors = _bootstrap_phase_modules(con)
        perf_indexes = ensure_perf_indexes(con)
        con.commit()
        return {"db_created": db_created, "db_path": str(p.resolve()),
                "perf_indexes_created": perf_indexes,
                "base_tables_created": base_report["created_tables"],
                "base_columns_added": base_report["added_columns"],
                "phases_bootstrapped": bootstrapped,
                "phase_reports": phase_reports, "errors": errors}
    finally:
        con.close()

def print_bootstrap_report(report):
    print("=" * 60)
    print("KI Database Bootstrap Report")
    print("=" * 60)
    print("DB path:      ", report.get("db_path"))
    print("DB created:   ", report.get("db_created"))
    print("Base tables:  ", report.get("base_tables_created") or "(none new)")
    added = report.get("base_columns_added") or []
    if added:
        print("Base columns added:")
        for a in added: print("  +", a)
    print("Phases bootstrapped:", report.get("phases_bootstrapped") or "(none)")
    for phase, r in (report.get("phase_reports") or {}).items():
        if isinstance(r, dict):
            ct = r.get("created_tables") or []; ac = r.get("added_columns") or []; ci = r.get("created_indexes") or []
            print("  " + phase + ":")
            if ct: print("    new tables :", ct)
            if ac: print("    new columns:", ac)
            if ci: print("    new indexes:", ci)
    for phase, e in (report.get("errors") or []):
        print("  !", phase, "->", e)
    print("=" * 60)
