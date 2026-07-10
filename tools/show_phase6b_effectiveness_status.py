import sqlite3, json

def ex(cur, table):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def count(cur, table):
    if not ex(cur, table):
        return 'missing'
    return cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]

def cols(cur, table):
    if not ex(cur, table):
        return []
    return [r[1] for r in cur.execute(f'PRAGMA table_info({table})').fetchall()]

con = sqlite3.connect('ki_memory.sqlite3')
cur = con.cursor()
print('db: ki_memory.sqlite3')

phase6b_tables = [
    'phase6b_state',
    'phase6b_anchor_pool',
    'phase6b_critic_snapshot',
    'phase6b_effectiveness_events',
    'phase6b_plasticity_adjustments',
    'phase6b_distilled_knowledge',
    'phase6b_l2m_metrics',
]
phase6a_tables = [
    'phase6a_sleep_replay_cycles',
    'phase6a_sleep_replay_events',
    'phase6a_replay_candidates',
    'phase6a_replay_memory',
    'phase6a_meta_plasticity_state',
    'phase6a_neuromodulated_sleep_state',
    'phase6a_plasticity_adjustments',
]
other = ['facts','relations','questions',
         'internal_learning_gaps','context_hypotheses',
         'phase5g_experiment_outcomes','phase5h_strategy_outcome_memory',
         'reading_queue','chunk_attention_scores']

print('--- counts phase6b ---')
for t in phase6b_tables:
    print(t, count(cur, t))
print('--- counts phase6a ---')
for t in phase6a_tables:
    print(t, count(cur, t))
print('--- counts other ---')
for t in other:
    print(t, count(cur, t))

if ex(cur, 'phase6b_state'):
    print('phase6b_state:', cur.execute('SELECT key,value FROM phase6b_state ORDER BY key').fetchall())

if ex(cur, 'phase6b_anchor_pool'):
    print('anchor_pool_top:', cur.execute(
        'SELECT id, source_table, source_id, ROUND(stability_score,3), replay_count, '
        ' ROUND(outcome_score_avg,3), promoted_from, active '
        'FROM phase6b_anchor_pool WHERE active=1 '
        'ORDER BY stability_score DESC LIMIT 10').fetchall())

if ex(cur, 'phase6b_effectiveness_events'):
    print('effectiveness_recent:', cur.execute(
        'SELECT cycle_index, ROUND(delta_outcome,4), ROUND(delta_closure,4), '
        ' ROUND(delta_overlap,4), ROUND(effectiveness_score,4), plateau_flag, '
        ' ROUND(anchor_consistency,3), ROUND(dopamine,3), ROUND(gaba,3) '
        'FROM phase6b_effectiveness_events ORDER BY id DESC LIMIT 8').fetchall())

if ex(cur, 'phase6b_plasticity_adjustments'):
    print('plasticity_adjustments_recent:', cur.execute(
        'SELECT cycle_index, adjustment_type, '
        ' ROUND(pre_plasticity_level,3), ROUND(post_plasticity_level,3), '
        ' ROUND(pre_exploration_bias,3), ROUND(post_exploration_bias,3), '
        ' ROUND(pre_inhibition_bias,3), ROUND(post_inhibition_bias,3), '
        ' critic_gate_result '
        'FROM phase6b_plasticity_adjustments ORDER BY id DESC LIMIT 8').fetchall())

if ex(cur, 'phase6b_l2m_metrics'):
    print('l2m_metrics_recent:', cur.execute(
        'SELECT cycle_index, ROUND(performance_maintenance,3), '
        ' ROUND(forward_transfer,4), ROUND(backward_transfer,4), '
        ' ROUND(sample_efficiency,4), ROUND(performance_recovery,3), '
        ' ROUND(anchor_stability,3), alert_flag, alert_reason '
        'FROM phase6b_l2m_metrics ORDER BY id DESC LIMIT 8').fetchall())

if ex(cur, 'phase6b_critic_snapshot'):
    print('critic_snapshot_recent:', cur.execute(
        'SELECT snapshot_id, active, ROUND(plasticity_level,3), '
        ' ROUND(exploration_bias,3), ROUND(consolidation_bias,3), '
        ' anchor_count, reason '
        'FROM phase6b_critic_snapshot ORDER BY snapshot_id DESC LIMIT 5').fetchall())

# safety verification
print('safety_facts_rel_questions:', {t: count(cur, t) for t in ['facts','relations','questions']})

con.close()
