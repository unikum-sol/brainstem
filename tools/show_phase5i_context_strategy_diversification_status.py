import sqlite3
from pathlib import Path
p=Path('ki_memory.sqlite3'); print('db:',p.resolve())
con=sqlite3.connect(str(p)); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
for t in ['facts','relations','questions','phase5i_strategy_diversification_cycles','phase5i_outcome_driven_experiments','phase5i_strategy_diversification_memory','phase5i_neuromodulated_selection_events','phase5i_diversification_state','phase5g_strategy_experiments','phase5g_experiment_outcomes','phase5g_strategy_selection_memory','phase5h_strategy_outcome_memory','internal_learning_gaps','reading_queue','chunk_attention_scores','context_hypotheses']:
 print(t,cnt(t))
print('facts_rel_questions:',{t:cnt(t) for t in ['facts','relations','questions']})
if ex('phase5i_diversification_state'): print('phase5i_state:',cur.execute('SELECT key,value FROM phase5i_diversification_state ORDER BY key').fetchall())
if ex('phase5i_strategy_diversification_memory'): print('phase5i_memory_top:',cur.execute("SELECT strategy,gap_type,role,observations,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_overlap_score,3),ROUND(avg_no_candidate_rate,3),ROUND(success_score,3),recommendation FROM phase5i_strategy_diversification_memory ORDER BY observations DESC, success_score DESC LIMIT 12").fetchall())
if ex('phase5i_strategy_diversification_cycles'): print('cycles_recent:',cur.execute("SELECT gaps_considered,experiments_created,queue_updates,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_overlap_score,3),ROUND(avg_no_candidate_rate,3),selected_main_strategy,safety_ok,created_at FROM phase5i_strategy_diversification_cycles ORDER BY id DESC LIMIT 8").fetchall())
if ex('phase5i_outcome_driven_experiments'): print('experiments_recent:',cur.execute("SELECT gap_type,role,center_chunk_id,target_chunk_id,selected_strategy,ROUND(strategy_score,3),ROUND(expected_outcome_score,3),ROUND(expected_closure_delta,3),ROUND(expected_overlap_score,3),reason FROM phase5i_outcome_driven_experiments ORDER BY id DESC LIMIT 12").fetchall())
if ex('reading_queue') and 'phase5i_priority' in cols('reading_queue'): print('reading_queue_top_phase5i:',cur.execute("SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),reason,status,ROUND(phase5i_priority,3),phase5i_selected_strategy,ROUND(phase5i_expected_outcome_score,3),ROUND(phase5i_expected_overlap_score,3) FROM reading_queue ORDER BY COALESCE(phase5i_priority,0) DESC, COALESCE(priority,0) DESC LIMIT 12").fetchall())
if ex('chunk_attention_scores') and 'phase5i_score' in cols('chunk_attention_scores'): print('chunk_attention_top_phase5i:',cur.execute("SELECT chunk_id,ROUND(attention_score,3),ROUND(phase5i_score,3),phase5i_selected_strategy,ROUND(phase5i_expected_outcome_score,3),ROUND(phase5i_expected_closure_delta,3),ROUND(phase5i_expected_overlap_score,3),ROUND(phase5i_expected_no_candidate_rate,3) FROM chunk_attention_scores ORDER BY COALESCE(phase5i_score,0) DESC, COALESCE(attention_score,0) DESC LIMIT 12").fetchall())
for t in ['phase5g_experiment_outcomes','internal_learning_gaps','chunk_attention_scores']: print(t+'_phase5i_cols:',[c for c in cols(t) if c.startswith('phase5i') or c in ('center_chunk_id','experiment_key','outcome_key')])
con.close()
