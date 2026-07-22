# -*- coding: utf-8 -*-
"""Adaptive DB Bootstrap for the KI System (creates DB + base + phase tables)."""
from __future__ import annotations
import os, sqlite3, importlib
from pathlib import Path
from typing import Any, Dict, List, Tuple
from ki_system import v8_modern_gap_phase5f_shadow_observation_release as _gap_phase5f_shadow_observation
from ki_system import v8_modern_gap_phase5f_shadow_history_release as _gap_phase5f_shadow_history
from ki_system import v8_modern_gap_phase5f_shadow_observation_v2_release as _gap_phase5f_shadow_v2
from ki_system import v8_stable_obs_content_fp_shadow_classifier_release as _content_fp_shadow_classifier
from ki_system import v8_phase6a_replay_control_shadow_release as _phase6a_replay_control_shadow

SCHEMA_TABLES: Dict[str, List[Tuple[str, str]]] = {'facts': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
           ('subject', 'TEXT'),
           ('relation', 'TEXT'),
           ('object', 'TEXT'),
           ('confidence', 'REAL DEFAULT 0'),
           ('source_chunk_id', 'INTEGER'),
           ('created_at', 'INTEGER'),
           ('updated_at', 'INTEGER')],
 'relations': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
               ('subject', 'TEXT'),
               ('relation', 'TEXT'),
               ('object', 'TEXT'),
               ('confidence', 'REAL DEFAULT 0'),
               ('source_chunk_id', 'INTEGER'),
               ('created_at', 'INTEGER')],
 'questions': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
               ('question', 'TEXT'),
               ('priority', 'REAL DEFAULT 0'),
               ('status', "TEXT DEFAULT 'open'"),
               ('created_at', 'INTEGER'),
               ('updated_at', 'INTEGER')],
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
              ('subject', 'TEXT'),
              ('super', 'TEXT'),
              ('relation', 'TEXT'),
              ('confidence', 'REAL DEFAULT 0'),
              ('source_fact_id', 'INTEGER')],
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
                        ('phase5g_reason', 'TEXT')],
 'internal_learning_gaps': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                            ('gap_key', 'TEXT'),
                            ('gap_reason', 'TEXT'),
                            ('priority', 'REAL DEFAULT 0'),
                            ('status', "TEXT DEFAULT 'open'"),
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
                                 ('candidate_count', 'INTEGER'),
                                 ('replay_events', 'INTEGER'),
                                 ('avg_outcome_score', 'REAL'),
                                 ('avg_closure_delta', 'REAL'),
                                 ('avg_overlap_score', 'REAL'),
                                 ('persistent_gap_pressure', 'REAL'),
                                 ('plasticity_level', 'REAL'),
                                 ('exploration_bias', 'REAL'),
                                 ('consolidation_bias', 'REAL'),
                                 ('created_at', 'INTEGER'),
        ('population_available', 'INTEGER DEFAULT 0'),
        ('outcome_observation_available', 'INTEGER DEFAULT 0'),
        ('outcome_observation_count', 'INTEGER DEFAULT 0'),
        ('evidence_state', 'TEXT'),
        ('evidence_reason', 'TEXT')
    ],
 'phase6a_meta_plasticity_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')],
 'phase6a_neuromodulated_sleep_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')],
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
                            ('phase6a_reason', 'TEXT')],
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
                   ('phase6a_reason', 'TEXT')],
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
 'modern_outcome_bridge_shadow': [('shadow_key', 'TEXT PRIMARY KEY'),
                                  ('source_table', 'TEXT'),
                                  ('source_id', 'INTEGER'),
                                  ('experiment_key', 'TEXT'),
                                  ('gap_id', 'INTEGER'),
                                  ('gap_key', 'TEXT'),
                                  ('gap_type', 'TEXT'),
                                  ('role', 'TEXT'),
                                  ('center_chunk_id', 'INTEGER'),
                                  ('target_chunk_id', 'INTEGER'),
                                  ('selected_strategy', 'TEXT'),
                                  ('strategy_score', 'REAL DEFAULT 0'),
                                  ('expected_outcome_score', 'REAL DEFAULT 0'),
                                  ('expected_closure_delta', 'REAL DEFAULT 0'),
                                  ('expected_overlap_score', 'REAL DEFAULT 0'),
                                  ('expected_no_candidate_rate', 'REAL DEFAULT 0'),
                                  ('observed_read_status', 'TEXT'),
                                  ('observed_read_count', 'INTEGER DEFAULT 0'),
                                  ('observed_attention_score', 'REAL DEFAULT 0'),
                                  ('observation_ready', 'INTEGER DEFAULT 0'),
                                  ('mapped_closure_delta', 'REAL DEFAULT 0'),
                                  ('mapped_overlap_score', 'REAL DEFAULT 0'),
                                  ('mapped_no_candidate_rate', 'REAL DEFAULT 0'),
                                  ('mapped_outcome_score', 'REAL DEFAULT 0'),
                                  ('mapped_outcome_label', 'TEXT'),
                                  ('mapped_recommendation', 'TEXT'),
                                  ('projection_status', 'TEXT'),
                                  ('missing_signals', 'TEXT'),
                                  ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                  ('details', 'TEXT'),
                                  ('source_created_at', 'INTEGER'),
                                  ('created_at', 'INTEGER'),
                                  ('updated_at', 'INTEGER')],
 'modern_outcome_bridge_shadow_cycles': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                         ('phase', 'TEXT'),
                                         ('source_rows_seen', 'INTEGER DEFAULT 0'),
                                         ('shadow_rows_created', 'INTEGER DEFAULT 0'),
                                         ('shadow_rows_updated', 'INTEGER DEFAULT 0'),
                                         ('observation_ready', 'INTEGER DEFAULT 0'),
                                         ('awaiting_observation', 'INTEGER DEFAULT 0'),
                                         ('productive_outcomes_before', 'INTEGER DEFAULT 0'),
                                         ('productive_outcomes_after', 'INTEGER DEFAULT 0'),
                                         ('productive_memory_before', 'INTEGER DEFAULT 0'),
                                         ('productive_memory_after', 'INTEGER DEFAULT 0'),
                                         ('facts_before', 'INTEGER DEFAULT 0'),
                                         ('facts_after', 'INTEGER DEFAULT 0'),
                                         ('relations_before', 'INTEGER DEFAULT 0'),
                                         ('relations_after', 'INTEGER DEFAULT 0'),
                                         ('questions_before', 'INTEGER DEFAULT 0'),
                                         ('questions_after', 'INTEGER DEFAULT 0'),
                                         ('safety_ok', 'INTEGER DEFAULT 1'),
                                         ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                         ('created_at', 'INTEGER')],
 'modern_outcome_bridge_shadow_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')],
 'modern_gap_candidate_shadow': [('shadow_key', 'TEXT PRIMARY KEY'),
                                 ('hypothesis_id', 'INTEGER'),
                                 ('signature', 'TEXT'),
                                 ('chunk_id', 'INTEGER'),
                                 ('role', 'TEXT'),
                                 ('status', 'TEXT'),
                                 ('hypothesis_confidence', 'REAL DEFAULT 0'),
                                 ('hypothesis_uncertainty', 'REAL DEFAULT 0'),
                                 ('evidence_count', 'INTEGER DEFAULT 0'),
                                 ('raw_observation_count', 'INTEGER DEFAULT 0'),
                                 ('raw_created_count', 'INTEGER DEFAULT 0'),
                                 ('raw_reobserved_count', 'INTEGER DEFAULT 0'),
                                 ('stability', 'REAL'),
                                 ('stability_confidence', 'REAL'),
                                 ('stability_uncertainty', 'REAL'),
                                 ('feedback_count', 'INTEGER DEFAULT 0'),
                                 ('error_count', 'INTEGER DEFAULT 0'),
                                 ('conflict_count', 'INTEGER DEFAULT 0'),
                                 ('dopamine', 'REAL DEFAULT 0'),
                                 ('serotonin', 'REAL DEFAULT 0'),
                                 ('glutamate', 'REAL DEFAULT 0'),
                                 ('gaba', 'REAL DEFAULT 0'),
                                 ('noradrenaline', 'REAL DEFAULT 0'),
                                 ('acetylcholine', 'REAL DEFAULT 0'),
                                 ('phase6a_replay_weight', 'REAL DEFAULT 0'),
                                 ('phase6a_meta_plasticity', 'REAL DEFAULT 0'),
                                 ('phase6a_sleep_replay_count', 'INTEGER DEFAULT 0'),
                                 ('last_replayed_at', 'INTEGER'),
                                 ('first_observed_at', 'INTEGER'),
                                 ('last_observed_at', 'INTEGER'),
                                 ('signal_presence', 'TEXT'),
                                 ('missing_signals', 'TEXT'),
                                 ('candidate_state', "TEXT DEFAULT 'observed_only'"),
                                 ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                 ('details', 'TEXT'),
                                 ('created_at', 'INTEGER'),
                                 ('updated_at', 'INTEGER')],
 'modern_gap_candidate_shadow_cycles': [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                                        ('phase', 'TEXT'),
                                        ('source_rows_seen', 'INTEGER DEFAULT 0'),
                                        ('shadow_rows_created', 'INTEGER DEFAULT 0'),
                                        ('shadow_rows_updated', 'INTEGER DEFAULT 0'),
                                        ('rows_with_reobservation', 'INTEGER DEFAULT 0'),
                                        ('rows_with_stability', 'INTEGER DEFAULT 0'),
                                        ('rows_with_feedback', 'INTEGER DEFAULT 0'),
                                        ('rows_with_errors', 'INTEGER DEFAULT 0'),
                                        ('rows_with_replay', 'INTEGER DEFAULT 0'),
                                        ('productive_gaps_before', 'INTEGER DEFAULT 0'),
                                        ('productive_gaps_after', 'INTEGER DEFAULT 0'),
                                        ('attention_before', 'INTEGER DEFAULT 0'),
                                        ('attention_after', 'INTEGER DEFAULT 0'),
                                        ('phase5f_experiments_before', 'INTEGER DEFAULT 0'),
                                        ('phase5f_experiments_after', 'INTEGER DEFAULT 0'),
                                        ('phase5g_experiments_before', 'INTEGER DEFAULT 0'),
                                        ('phase5g_experiments_after', 'INTEGER DEFAULT 0'),
                                        ('phase5i_experiments_before', 'INTEGER DEFAULT 0'),
                                        ('phase5i_experiments_after', 'INTEGER DEFAULT 0'),
                                        ('facts_before', 'INTEGER DEFAULT 0'),
                                        ('facts_after', 'INTEGER DEFAULT 0'),
                                        ('relations_before', 'INTEGER DEFAULT 0'),
                                        ('relations_after', 'INTEGER DEFAULT 0'),
                                        ('questions_before', 'INTEGER DEFAULT 0'),
                                        ('questions_after', 'INTEGER DEFAULT 0'),
                                        ('safety_ok', 'INTEGER DEFAULT 1'),
                                        ('bridge_mode', "TEXT DEFAULT 'shadow'"),
                                        ('created_at', 'INTEGER')],
 'modern_gap_candidate_shadow_state': [('key', 'TEXT PRIMARY KEY'), ('value', 'TEXT'), ('updated_at', 'INTEGER')]}
BASE_SCHEMA = SCHEMA_TABLES

PHASE_REGISTRY: List[Tuple[str, str]] = [
    ("v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release", "phase6a"),
    ("v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "phase6b"),
    ("v8_phase6c_bias_persistence_and_self_regulating_meta_release", "phase6c"),
    ("v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "phase6d"),
    ("v8_phase7a_adenosine_homeostat_release", "phase7a"),
    ("v8_phase7b_endocannabinoid_retrograde_gain_control_release", "phase7b"),
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
 ('idx_bs_rollback_safe_core_state_key_uniq', 'rollback_safe_core_state', ('key',), True)]


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
        if fn is None: continue
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
        bootstrapped, phase_reports, errors = _bootstrap_phase_modules(con)
        perf_indexes = ensure_perf_indexes(con)
        con.commit()
        _gap_phase5f_shadow_observation.ensure_schema()
        _gap_phase5f_shadow_history.ensure_schema()
        _content_fp_shadow_classifier.ensure_schema()
        _phase6a_replay_control_shadow.ensure_schema()
        return {"db_created": db_created, "db_path": str(p.resolve()),
                "perf_indexes_created": perf_indexes,
                "base_tables_created": base_report["created_tables"],
                "base_columns_added": base_report["added_columns"],
                "phases_bootstrapped": bootstrapped,
                "phase_reports": phase_reports, "errors": errors}
    finally:
        con.close()
    _gap_phase5f_shadow_v2.ensure_schema()

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
