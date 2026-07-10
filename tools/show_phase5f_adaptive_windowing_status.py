import sqlite3, os
con=sqlite3.connect('ki_memory.sqlite3'); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
print('db:', os.path.abspath('ki_memory.sqlite3'))
for t in ['facts','relations','questions']: print(t,cnt(t))
for t in ['phase5f_effectiveness_cycles','phase5f_adaptive_window_events','phase5f_context_window_experiments','phase5f_window_strategy_memory','phase5f_read_outcome_memory','phase5f_gap_window_state','phase5f_runtime_state','context_expansion_actions','gap_closure_attempts','context_expansion_memory','internal_learning_gaps','reading_queue','chunk_attention_scores','context_hypotheses']:
    print(t,cnt(t))
print('facts_rel_questions:', {t:cnt(t) for t in ['facts','relations','questions']})
if ex('phase5f_runtime_state'): print('phase5f_state:', cur.execute('SELECT key,value FROM phase5f_runtime_state ORDER BY key').fetchall())
if ex('phase5f_effectiveness_cycles'): print('cycles_recent:', cur.execute('SELECT gaps_considered,experiments_created,queue_updates,ROUND(avg_closure_delta,3),ROUND(avg_expected_gain,3),ROUND(avg_no_candidate_rate,3),ROUND(avg_overlap_score,3),recommended_strategy,safety_ok,created_at FROM phase5f_effectiveness_cycles ORDER BY id DESC LIMIT 8').fetchall())
if ex('phase5f_window_strategy_memory'): print('window_strategy_memory_top:', cur.execute('SELECT strategy_name,gap_type,role,observations,ROUND(avg_closure_delta,3),ROUND(read_no_candidate_rate,3),ROUND(avg_overlap_score,3),ROUND(avg_window_radius,2),ROUND(success_score,3),recommendation FROM phase5f_window_strategy_memory ORDER BY observations DESC, success_score DESC LIMIT 12').fetchall())
if ex('phase5f_adaptive_window_events'): print('adaptive_events_recent:', cur.execute('SELECT gap_type,role,center_chunk_id,old_window_radius,new_window_radius,old_strategy,new_strategy,ROUND(closure_delta,3),ROUND(read_no_candidate_rate,3),ROUND(overlap_score,3),action FROM phase5f_adaptive_window_events ORDER BY id DESC LIMIT 12').fetchall())
if ex('phase5f_context_window_experiments'): print('experiments_recent:', cur.execute('SELECT center_chunk_id,target_chunk_id,window_radius,window_strategy,read_outcome,ROUND(no_candidate_signal,3),ROUND(overlap_score,3),ROUND(experiment_score,3) FROM phase5f_context_window_experiments ORDER BY id DESC LIMIT 12').fetchall())
if ex('reading_queue') and 'phase5f_priority' in cols('reading_queue'):
    print('reading_queue_top_phase5f:', cur.execute('SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),reason,status,ROUND(phase5f_priority,3),phase5f_window_strategy,phase5f_window_radius,ROUND(phase5f_no_candidate_penalty,3) FROM reading_queue ORDER BY COALESCE(phase5f_priority,0) DESC, COALESCE(priority,0) DESC LIMIT 12').fetchall())
if ex('chunk_attention_scores') and 'phase5f_score' in cols('chunk_attention_scores'):
    print('chunk_attention_top_phase5f:', cur.execute('SELECT chunk_id,ROUND(attention_score,3),ROUND(phase5f_score,3),phase5f_window_strategy,phase5f_window_radius,ROUND(phase5f_effectiveness_score,3),ROUND(phase5f_read_outcome_score,3),ROUND(phase5f_overlap_score,3) FROM chunk_attention_scores ORDER BY COALESCE(phase5f_score,0) DESC LIMIT 12').fetchall())
print('internal_learning_gaps_phase5f_cols:', [c for c in cols('internal_learning_gaps') if c.startswith('phase5f_') or c in ('priority','resolution_score','strategy_effectiveness_score')])
print('chunk_attention_phase5f_cols:', [c for c in cols('chunk_attention_scores') if c.startswith('phase5f_')])
