import sqlite3, os
p='ki_memory.sqlite3'; con=sqlite3.connect(p); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
print('db:', os.path.abspath(p))
for t in ['facts','relations','questions','context_hypotheses','context_pattern_memory','long_term_pattern_memory','pattern_stability_history','role_confusion_memory','neuromodulator_pattern_profiles','long_term_consolidation_state','hypothesis_learning_updates','sleep_consolidation_decisions','neuromodulator_learning_state']:
    print(t, cnt(t))
if ex('long_term_consolidation_state'): print('long_term_state:', cur.execute('SELECT key,value FROM long_term_consolidation_state ORDER BY key').fetchall())
if ex('long_term_pattern_memory'): print('long_term_top:', cur.execute('SELECT pattern_key,dominant_role,observations,ROUND(avg_confidence,3),ROUND(avg_uncertainty,3),ROUND(stability,3),last_decision FROM long_term_pattern_memory ORDER BY observations DESC, stability DESC LIMIT 10').fetchall())
if ex('neuromodulator_pattern_profiles'): print('neuro_profiles:', cur.execute('SELECT role,observations,ROUND(avg_learning_rate,3),ROUND(avg_error_weight,3),ROUND(avg_revision_pressure,3),ROUND(avg_consolidation_gain,3),ROUND(avg_confidence,3),ROUND(avg_uncertainty,3) FROM neuromodulator_pattern_profiles ORDER BY observations DESC LIMIT 10').fetchall())
print('facts_rel_questions:', {t:cnt(t) for t in ['facts','relations','questions']})
