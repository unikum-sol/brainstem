import sys, sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
DB=ROOT/'ki_memory.sqlite3'
print('db:', DB)
if not DB.exists():
    print('ki_memory.sqlite3 missing'); raise SystemExit(0)
con=sqlite3.connect(str(DB)); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
for t in ['facts','relations','questions','context_hypotheses','context_learning_events','rollback_safe_core_state','reading_queue']:
    print(t, cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing')
if ex('rollback_safe_core_state'):
    print('rollback_state:', cur.execute('SELECT key,value FROM rollback_safe_core_state ORDER BY key').fetchall())
if ex('context_hypotheses'):
    print('hypothesis_roles:', cur.execute('SELECT hypothesis_role, COUNT(*) FROM context_hypotheses GROUP BY hypothesis_role ORDER BY COUNT(*) DESC LIMIT 20').fetchall())
