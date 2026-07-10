import sqlite3
from pathlib import Path
p=Path('ki_memory.sqlite3')
print('DB:', p.resolve())
if not p.exists():
    print('DB fehlt im aktuellen Ordner'); raise SystemExit(1)
con=sqlite3.connect(str(p)); cur=con.cursor()
def exists(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
for t in ['facts','relations','questions','context_hypotheses','context_learning_events','rollback_safe_core_state','candidate_relations']:
    if exists(t): print(t, cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
print('rollback_state:', cur.execute('SELECT key,value FROM rollback_safe_core_state ORDER BY key').fetchall() if exists('rollback_safe_core_state') else [])
print('hypothesis_roles:', cur.execute('SELECT role_guess, COUNT(*) FROM context_hypotheses GROUP BY role_guess ORDER BY COUNT(*) DESC LIMIT 20').fetchall() if exists('context_hypotheses') else [])
