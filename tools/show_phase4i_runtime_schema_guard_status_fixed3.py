
import sqlite3, os
DB='ki_memory.sqlite3'
con=sqlite3.connect(DB); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def count(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
print('db:', os.path.abspath(DB))
for t in ['facts','relations','questions','context_hypotheses','context_pattern_memory','long_term_pattern_memory','pattern_stability_history','role_confusion_memory','neuromodulator_pattern_profiles','long_term_consolidation_state','hypothesis_learning_updates','sleep_consolidation_decisions','neuromodulator_learning_state']:
    print(t, count(t))
for t in ['pattern_stability_history','long_term_pattern_memory','role_confusion_memory','neuromodulator_pattern_profiles','long_term_consolidation_state']:
    print(t+'_columns:', cols(t))
if ex('long_term_consolidation_state'):
    print('long_term_state:', cur.execute('SELECT key,value FROM long_term_consolidation_state ORDER BY key').fetchall())
if ex('long_term_pattern_memory'):
    print('long_term_top:', cur.execute('SELECT pattern_key, dominant_role, observations, ROUND(avg_confidence,3), ROUND(avg_uncertainty,3), ROUND(stability,3), last_decision FROM long_term_pattern_memory ORDER BY observations DESC, stability DESC LIMIT 10').fetchall())
print('facts_rel_questions:', {'facts': count('facts'), 'relations': count('relations'), 'questions': count('questions')})
