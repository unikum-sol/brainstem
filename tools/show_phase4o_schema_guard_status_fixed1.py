import sqlite3, os
DB='ki_memory.sqlite3'
con=sqlite3.connect(DB); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def count(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
print('db:', os.path.abspath(DB))
for t in ['facts','relations','questions','internal_learning_gaps','strategy_feedback_events','strategy_outcome_memory','strategy_adjustment_recommendations','strategy_effectiveness_feedback_state','context_hypotheses','chunk_attention_scores']:
    print(t, count(t))
print('internal_learning_gaps_columns:', cols('internal_learning_gaps'))
if ex('internal_learning_gaps'):
    print('gap_priority_top:', cur.execute("SELECT gap_type, role, ROUND(COALESCE(priority,0),3), ROUND(COALESCE(strategy_effectiveness_score,0),3), status FROM internal_learning_gaps ORDER BY COALESCE(priority,0) DESC, rowid DESC LIMIT 12").fetchall())
if ex('strategy_effectiveness_feedback_state'):
    print('strategy_effectiveness_feedback_state:', cur.execute("SELECT key,value FROM strategy_effectiveness_feedback_state ORDER BY key").fetchall())
if ex('strategy_feedback_events'):
    print('strategy_feedback_recent:', cur.execute("SELECT target_type, COUNT(*), ROUND(AVG(outcome_score),3), ROUND(AVG(error_pressure),3) FROM strategy_feedback_events GROUP BY target_type ORDER BY COUNT(*) DESC LIMIT 10").fetchall())
print('facts_rel_questions:', {t: count(t) for t in ['facts','relations','questions']})
