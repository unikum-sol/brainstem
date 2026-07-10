import sqlite3
from pathlib import Path
p=Path('ki_memory.sqlite3').resolve(); print('db:',p)
con=sqlite3.connect(str(p)); cur=con.cursor()
def ex(t): return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
for t in ['facts','relations','questions']: print(t,cnt(t))
for t in ['phase5g_strategy_selection_memory','phase5g_strategy_experiments','phase5g_experiment_outcomes','phase5g_neuromodulator_strategy_profiles','phase5g_context_strategy_state','phase5f_window_strategy_memory','phase5f_context_window_experiments','internal_learning_gaps','reading_queue','chunk_attention_scores','context_hypotheses']:
    print(t,cnt(t))
print('facts_rel_questions:', {t:cnt(t) for t in ['facts','relations','questions']})
if ex('phase5g_context_strategy_state'):
    print('phase5g_state:', cur.execute('SELECT key,value FROM phase5g_context_strategy_state ORDER BY key').fetchall())
if ex('phase5g_strategy_selection_memory'):
    print('strategy_memory_top:', cur.execute("SELECT strategy,gap_type,role,observations,ROUND(avg_closure_delta,3),ROUND(avg_no_candidate_rate,3),ROUND(avg_overlap_score,3),ROUND(avg_effectiveness,3),recommendation FROM phase5g_strategy_selection_memory ORDER BY observations DESC, avg_effectiveness DESC LIMIT 12").fetchall())
if ex('phase5g_strategy_experiments'):
    print('experiments_recent:', cur.execute("SELECT gap_type,role,center_chunk_id,target_chunk_id,selected_strategy,window_radius,ROUND(expected_gain,3),ROUND(predicted_effectiveness,3),ROUND(no_candidate_rate,3),ROUND(overlap_score,3),decision FROM phase5g_strategy_experiments ORDER BY id DESC LIMIT 12").fetchall())
if ex('phase5g_neuromodulator_strategy_profiles'):
    print('neuro_strategy_profiles:', cur.execute("SELECT strategy,gap_type,role,observations,ROUND(avg_learning_rate,3),ROUND(avg_error_weight,3),ROUND(avg_revision_pressure,3),ROUND(avg_exploration_pressure,3),ROUND(avg_inhibition_level,3),ROUND(avg_closure_delta,3),ROUND(avg_effectiveness,3),recommendation FROM phase5g_neuromodulator_strategy_profiles ORDER BY observations DESC LIMIT 12").fetchall())
if ex('reading_queue') and 'phase5g_selected_strategy' in cols('reading_queue'):
    print('reading_queue_top_phase5g:', cur.execute("SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),reason,status,ROUND(phase5g_score,3),phase5g_selected_strategy,ROUND(phase5g_strategy_score,3),ROUND(phase5g_no_candidate_rate,3) FROM reading_queue ORDER BY phase5g_score DESC, priority DESC LIMIT 12").fetchall())
if ex('chunk_attention_scores') and 'phase5g_selected_strategy' in cols('chunk_attention_scores'):
    print('chunk_attention_top_phase5g:', cur.execute("SELECT chunk_id,ROUND(attention_score,3),ROUND(phase5g_score,3),phase5g_selected_strategy,ROUND(phase5g_strategy_score,3),ROUND(phase5g_closure_delta,3),ROUND(phase5g_no_candidate_rate,3),ROUND(phase5g_overlap_score,3) FROM chunk_attention_scores ORDER BY phase5g_score DESC, attention_score DESC LIMIT 12").fetchall())
for t in ['internal_learning_gaps','chunk_attention_scores']:
    print(t+'_phase5g_cols:', [c for c in cols(t) if c.startswith('phase5g')])
con.close()
