
import sqlite3, os
con=sqlite3.connect('ki_memory.sqlite3')
cur=con.cursor()
print('db:', os.path.abspath('ki_memory.sqlite3'))
for t in ['facts','relations','questions','context_hypotheses','context_pattern_memory','long_term_pattern_memory','pattern_stability_history','role_confusion_memory','neuromodulator_pattern_profiles','long_term_consolidation_state','hypothesis_learning_updates','sleep_consolidation_decisions','neuromodulator_learning_state']:
    ex=cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone()
    print(t, cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex else 'missing')
print('long_term_state:', cur.execute("SELECT key,value FROM long_term_consolidation_state ORDER BY key").fetchall() if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='long_term_consolidation_state'").fetchone() else [])
print('long_term_top:', cur.execute("SELECT pattern_key,dominant_role,observations,ROUND(avg_confidence,3),ROUND(avg_uncertainty,3),ROUND(stability,3),last_decision FROM long_term_pattern_memory ORDER BY observations DESC, stability DESC LIMIT 10").fetchall() if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='long_term_pattern_memory'").fetchone() else [])
print('neuro_profiles:', cur.execute("SELECT role,observations,ROUND(avg_dopamine,3),ROUND(avg_gaba,3),ROUND(avg_confidence,3),ROUND(avg_uncertainty,3),ROUND(avg_learning_rate,3),ROUND(avg_error_weight,3) FROM neuromodulator_pattern_profiles ORDER BY observations DESC LIMIT 10").fetchall() if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='neuromodulator_pattern_profiles'").fetchone() else [])
print('facts_rel_questions:', {t:cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['facts','relations','questions']})
