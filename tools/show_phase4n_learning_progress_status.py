
import sqlite3, os
DB='ki_memory.sqlite3'
con=sqlite3.connect(DB); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute('PRAGMA table_info('+t+')').fetchall()] if ex(t) else []
print('db:', os.path.abspath(DB))
for t in ['facts','relations','questions','context_hypotheses','internal_learning_gaps','learning_progress_evaluations','adaptive_strategy_adjustments','strategy_effectiveness_memory','progress_evaluation_state','active_learning_loop_state','active_learning_decisions','learning_control_cycles','neuromodulator_control_history','hypothesis_learning_updates','sleep_consolidation_decisions','chunk_attention_scores','reading_queue']:
    print(t, cnt(t))
if ex('progress_evaluation_state'):
    print('progress_evaluation_state:', cur.execute('SELECT key,value FROM progress_evaluation_state ORDER BY key').fetchall())
if ex('learning_progress_evaluations'):
    print('progress_recent:', cur.execute('SELECT phase,hypotheses,gaps,errors,updates_count,long_term_patterns,reread_actions,active_decisions,ROUND(progress_score,3),ROUND(error_pressure,3),ROUND(uncertainty_pressure,3),ROUND(stability_gain,3),ROUND(exploration_need,3),created_at FROM learning_progress_evaluations ORDER BY id DESC LIMIT 8').fetchall())
if ex('adaptive_strategy_adjustments'):
    print('adjustments_recent:', cur.execute('SELECT adjustment_type,target,ROUND(old_value,3),ROUND(new_value,3),reason,created_at FROM adaptive_strategy_adjustments ORDER BY id DESC LIMIT 12').fetchall())
if ex('strategy_effectiveness_memory'):
    print('strategy_effectiveness:', cur.execute('SELECT strategy_key,observations,ROUND(avg_progress_score,3),ROUND(avg_error_pressure,3),ROUND(avg_uncertainty_pressure,3),ROUND(avg_stability_gain,3),last_decision FROM strategy_effectiveness_memory ORDER BY observations DESC LIMIT 10').fetchall())
if ex('context_hypotheses') and 'progress_score' in cols('context_hypotheses'):
    print('hypothesis_progress_top:', cur.execute('SELECT id,role,ROUND(progress_score,3),progress_reason FROM context_hypotheses ORDER BY progress_score DESC LIMIT 12').fetchall())
if ex('internal_learning_gaps') and 'progress_priority' in cols('internal_learning_gaps'):
    print('gap_progress_top:', cur.execute('SELECT gap_type,role,ROUND(progress_priority,3),progress_reason,status FROM internal_learning_gaps ORDER BY progress_priority DESC LIMIT 12').fetchall())
if ex('chunk_attention_scores') and 'progress_adjusted_score' in cols('chunk_attention_scores'):
    print('chunk_progress_top:', cur.execute('SELECT chunk_id,ROUND(attention_score,3),ROUND(progress_adjusted_score,3),progress_adjustment_reason FROM chunk_attention_scores ORDER BY progress_adjusted_score DESC LIMIT 12').fetchall())
print('facts_rel_questions:', {'facts':cnt('facts'), 'relations':cnt('relations'), 'questions':cnt('questions')})
