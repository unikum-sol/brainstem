import sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DB=ROOT/'ki_memory.sqlite3'
print('db:',DB)
con=sqlite3.connect(str(DB)); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t):
    try: return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
    except Exception as e: return 'ERR '+str(e)
for t in ['facts','relations','questions','context_hypotheses','hypothesis_self_evaluations','hypothesis_role_revisions','self_evaluation_cycles','revision_strategy_state','hypothesis_learning_updates','hypothesis_stability_scores','hypothesis_feedback','hypothesis_error_events','neuromodulator_learning_state']:
    print(t,cnt(t))
if ex('context_hypotheses'):
    print('hypothesis_roles:',cur.execute("SELECT role, COUNT(*) FROM context_hypotheses GROUP BY role ORDER BY COUNT(*) DESC LIMIT 20").fetchall())
    print('context_hypotheses_columns:',[r[1] for r in cur.execute('PRAGMA table_info(context_hypotheses)').fetchall()])
if ex('self_evaluation_cycles'):
    print('self_eval_recent:',cur.execute('SELECT evaluated,revised,stable,uncertain,ROUND(avg_self_score,3),ROUND(avg_revision_pressure,3),created_at FROM self_evaluation_cycles ORDER BY id DESC LIMIT 10').fetchall())
if ex('hypothesis_role_revisions'):
    print('revision_recent:',cur.execute('SELECT hypothesis_id,old_role,new_role,ROUND(revision_pressure,3),reason,applied FROM hypothesis_role_revisions ORDER BY id DESC LIMIT 10').fetchall())
if ex('revision_strategy_state'):
    print('revision_strategy_state:',cur.execute('SELECT key,value FROM revision_strategy_state ORDER BY key').fetchall())
print('facts_rel_questions:',{t:cnt(t) for t in ['facts','relations','questions']})
con.close()
