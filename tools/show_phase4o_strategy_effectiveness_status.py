
import sqlite3, os
p='ki_memory.sqlite3'
print('db:', os.path.abspath(p))
con=sqlite3.connect(p); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
for t in ['facts','relations','questions','learning_progress_evaluations','adaptive_strategy_adjustments','strategy_effectiveness_memory','strategy_feedback_events','strategy_outcome_memory','strategy_adjustment_recommendations','strategy_effectiveness_feedback_state','context_hypotheses','internal_learning_gaps','chunk_attention_scores','active_learning_decisions','learning_control_cycles','neuromodulator_control_history']:
    print(t, cnt(t))
if ex('strategy_effectiveness_feedback_state'):
    print('strategy_feedback_state:', cur.execute('SELECT key,value FROM strategy_effectiveness_feedback_state ORDER BY key').fetchall())
if ex('strategy_feedback_events'):
    print('feedback_recent:', cur.execute('SELECT strategy_key,ROUND(progress_score,3),ROUND(error_pressure,3),ROUND(uncertainty_pressure,3),ROUND(stability_gain,3),ROUND(outcome_score,3),recommendation,created_at FROM strategy_feedback_events ORDER BY id DESC LIMIT 8').fetchall())
if ex('strategy_outcome_memory'):
    print('strategy_outcomes:', cur.execute('SELECT strategy_key,observations,ROUND(avg_progress_score,3),ROUND(avg_error_pressure,3),ROUND(avg_uncertainty_pressure,3),ROUND(avg_stability_gain,3),ROUND(effectiveness_score,3),last_recommendation FROM strategy_outcome_memory ORDER BY updated_at DESC LIMIT 8').fetchall())
if ex('strategy_adjustment_recommendations'):
    print('recommendations_recent:', cur.execute('SELECT control_name,ROUND(current_value,3),ROUND(recommended_value,3),reason,ROUND(strength,3),status,created_at FROM strategy_adjustment_recommendations ORDER BY id DESC LIMIT 12').fetchall())
if ex('context_hypotheses'):
    cols=[r[1] for r in cur.execute('PRAGMA table_info(context_hypotheses)').fetchall()]
    if 'strategy_effectiveness_score' in cols:
        print('hypothesis_strategy_top:', cur.execute('SELECT id,role,ROUND(strategy_effectiveness_score,3),strategy_feedback_reason FROM context_hypotheses ORDER BY strategy_effectiveness_score DESC, id DESC LIMIT 12').fetchall())
if ex('internal_learning_gaps'):
    cols=[r[1] for r in cur.execute('PRAGMA table_info(internal_learning_gaps)').fetchall()]
    if 'strategy_effectiveness_score' in cols:
        # Use rowid to avoid assuming id column
        print('gap_strategy_top:', cur.execute('SELECT gap_type,role,ROUND(strategy_effectiveness_score,3),strategy_feedback_reason,status FROM internal_learning_gaps ORDER BY strategy_effectiveness_score DESC, rowid DESC LIMIT 12').fetchall())
if ex('chunk_attention_scores'):
    cols=[r[1] for r in cur.execute('PRAGMA table_info(chunk_attention_scores)').fetchall()]
    if 'strategy_effectiveness_score' in cols:
        print('chunk_strategy_top:', cur.execute('SELECT chunk_id,ROUND(attention_score,3),ROUND(strategy_effectiveness_score,3),strategy_feedback_reason FROM chunk_attention_scores ORDER BY strategy_effectiveness_score DESC, attention_score DESC LIMIT 12').fetchall())
print('facts_rel_questions:', {t: cnt(t) for t in ['facts','relations','questions']})
