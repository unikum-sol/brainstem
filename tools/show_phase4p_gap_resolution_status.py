from pathlib import Path
import sqlite3, sys, os
ROOT = Path(__file__).resolve().parents[1]
db_path = ROOT / 'ki_memory.sqlite3'
print('db:', db_path)
con = sqlite3.connect(str(db_path)); cur = con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def count(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute('PRAGMA table_info('+t+')').fetchall()] if ex(t) else []
for t in ['facts','relations','questions','internal_learning_gaps','gap_resolution_outcomes','learning_outcome_tracking_events','strategy_gap_resolution_memory','gap_resolution_state','strategy_feedback_events','context_hypotheses','chunk_attention_scores']:
    print(t, count(t))
print('facts_rel_questions:', {k:count(k) for k in ['facts','relations','questions']})
print('internal_learning_gaps_columns:', cols('internal_learning_gaps'))
print('gap_resolution_outcomes_columns:', cols('gap_resolution_outcomes'))
if ex('gap_resolution_state'):
    print('gap_resolution_state:', cur.execute('SELECT key,value FROM gap_resolution_state ORDER BY key').fetchall())
if ex('internal_learning_gaps'):
    c=cols('internal_learning_gaps')
    if all(x in c for x in ['gap_type','role','priority','strategy_effectiveness_score','resolution_score','resolution_status']):
        print('gap_priority_top_fixed:', cur.execute("SELECT gap_type,role,ROUND(priority,3),ROUND(strategy_effectiveness_score,3),ROUND(resolution_score,3),resolution_status FROM internal_learning_gaps ORDER BY priority DESC, id DESC LIMIT 12").fetchall())
if ex('gap_resolution_outcomes'):
    print('resolution_recent:', cur.execute("SELECT gap_type,role,ROUND(before_priority,3),ROUND(after_priority,3),ROUND(after_effectiveness,3),ROUND(resolution_score,3),outcome FROM gap_resolution_outcomes ORDER BY id DESC LIMIT 12").fetchall())
if ex('strategy_gap_resolution_memory'):
    print('strategy_gap_resolution_memory:', cur.execute("SELECT strategy_key,observations,ROUND(avg_resolution_score,3),ROUND(avg_outcome_score,3),resolved_count,persistent_count,last_recommendation FROM strategy_gap_resolution_memory ORDER BY updated_at DESC LIMIT 10").fetchall())
con.close()
