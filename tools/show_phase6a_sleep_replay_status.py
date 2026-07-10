
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
for t in ['facts','relations','questions','phase6a_sleep_replay_cycles','phase6a_sleep_replay_events','phase6a_replay_candidates','phase6a_replay_memory','phase6a_meta_plasticity_state','phase6a_neuromodulated_sleep_state','phase6a_plasticity_adjustments','internal_learning_gaps','context_hypotheses','phase5g_experiment_outcomes','phase5h_strategy_outcome_memory','reading_queue','chunk_attention_scores']:
    print(t, count(cur,t))
print('facts_rel_questions:', {t: count(cur,t) for t in ['facts','relations','questions']})
if ex(cur,'phase6a_meta_plasticity_state'):
    print('meta_plasticity_state:', cur.execute('SELECT key,value FROM phase6a_meta_plasticity_state ORDER BY key').fetchall())
if ex(cur,'phase6a_neuromodulated_sleep_state'):
    print('neuromodulated_sleep_state:', cur.execute('SELECT key,value FROM phase6a_neuromodulated_sleep_state ORDER BY key').fetchall())
if ex(cur,'phase6a_sleep_replay_cycles'):
    print('sleep_cycles_recent:', cur.execute('SELECT candidate_count,replay_events,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_overlap_score,3),ROUND(persistent_gap_pressure,3),ROUND(plasticity_level,3),ROUND(exploration_bias,3),ROUND(consolidation_bias,3),created_at FROM phase6a_sleep_replay_cycles ORDER BY id DESC LIMIT 8').fetchall())
if ex(cur,'phase6a_replay_memory'):
    print('replay_memory_top:', cur.execute('SELECT memory_key,memory_type,observations,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_overlap_score,3),ROUND(avg_plasticity_level,3),recommendation FROM phase6a_replay_memory ORDER BY observations DESC LIMIT 12').fetchall())
if ex(cur,'phase6a_sleep_replay_events'):
    print('replay_events_recent:', cur.execute('SELECT source_table,candidate_type,role,ROUND(replay_priority,3),ROUND(replay_weight,3),ROUND(outcome_score,3),ROUND(closure_delta,3),ROUND(overlap_score,3),replay_decision FROM phase6a_sleep_replay_events ORDER BY id DESC LIMIT 12').fetchall())
print('internal_learning_gaps_phase6a_cols:', [c for c in cols(cur,'internal_learning_gaps') if c.startswith('phase6a_')])
print('context_hypotheses_phase6a_cols:', [c for c in cols(cur,'context_hypotheses') if c.startswith('phase6a_')])
print('phase5g_experiment_outcomes_phase6a_cols:', [c for c in cols(cur,'phase5g_experiment_outcomes') if c.startswith('phase6a_')])
con.close()
