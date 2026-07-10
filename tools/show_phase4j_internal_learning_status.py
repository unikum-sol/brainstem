
from pathlib import Path
import sqlite3
DB = Path('ki_memory.sqlite3')
print('db:', DB.resolve())
con = sqlite3.connect(str(DB)); cur = con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def count(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
for t in ['facts','relations','questions','context_hypotheses','hypothesis_error_events','role_confusion_memory','long_term_pattern_memory','internal_learning_gaps','internal_learning_questions','gap_detection_events','learning_gap_state']:
    print(t, count(t))
if ex('internal_learning_gaps'):
    print('gap_types:', cur.execute("SELECT gap_type, COUNT(*), ROUND(AVG(severity),3) FROM internal_learning_gaps GROUP BY gap_type ORDER BY COUNT(*) DESC").fetchall())
    print('top_gaps:', cur.execute("SELECT gap_type, role, ROUND(severity,3), evidence_count, status FROM internal_learning_gaps ORDER BY severity DESC, evidence_count DESC LIMIT 12").fetchall())
if ex('internal_learning_questions'):
    print('question_types:', cur.execute("SELECT question_type, COUNT(*), ROUND(AVG(priority),3) FROM internal_learning_questions GROUP BY question_type ORDER BY COUNT(*) DESC").fetchall())
    print('top_internal_questions:', cur.execute("SELECT question_type, role, ROUND(priority,3), evidence_count, status FROM internal_learning_questions ORDER BY priority DESC, evidence_count DESC LIMIT 12").fetchall())
if ex('learning_gap_state'):
    print('learning_gap_state:', cur.execute("SELECT key,value FROM learning_gap_state ORDER BY key").fetchall())
print('facts_rel_questions:', {t: count(t) for t in ['facts','relations','questions']})
con.close()
