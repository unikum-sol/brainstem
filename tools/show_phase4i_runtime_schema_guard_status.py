import sqlite3, os
p='ki_memory.sqlite3'
con=sqlite3.connect(p); cur=con.cursor()
print('db:', os.path.abspath(p))
for t in ['facts','relations','questions','long_term_pattern_memory','pattern_stability_history','role_confusion_memory','neuromodulator_pattern_profiles','long_term_consolidation_state']:
    ex=cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone()
    print(t, cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex else 'missing')
for t in ['pattern_stability_history','long_term_pattern_memory','role_confusion_memory','neuromodulator_pattern_profiles','long_term_consolidation_state']:
    ex=cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone()
    if ex: print(t+'_columns:', [r[1] for r in cur.execute('PRAGMA table_info('+t+')').fetchall()])
