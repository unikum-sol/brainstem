
import sqlite3
from pathlib import Path
p=Path('ki_memory.sqlite3')
print('db:', p.resolve())
con=sqlite3.connect(str(p)); cur=con.cursor()
def exists(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if exists(t) else []
def count(t):
    if not exists(t): print(t,'missing'); return None
    c=cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]; print(t,c); return c
for t in ['facts','relations','questions','reading_queue','context_hypotheses','context_learning_events','hypothesis_feedback','hypothesis_revisions','hypothesis_error_events','neuromodulated_attention_events','context_role_stats','hypothesis_clusters','hypothesis_stability_scores','context_pattern_memory','neuromodulator_sleep_events','learning_strategy_state','rollback_safe_core_state']:
    count(t)
if exists('rollback_safe_core_state'):
    print('rollback_state:', cur.execute('SELECT key,value FROM rollback_safe_core_state ORDER BY key').fetchall())
if exists('context_hypotheses'):
    c=cols('context_hypotheses'); print('context_hypotheses_columns:', c)
    role_col='role' if 'role' in c else ('hypothesis_role' if 'hypothesis_role' in c else None)
    if role_col:
        print('hypothesis_roles:', cur.execute(f'SELECT {role_col}, COUNT(*) FROM context_hypotheses GROUP BY {role_col} ORDER BY COUNT(*) DESC').fetchall())
    else: print('hypothesis_roles: unavailable - no role/hypothesis_role column')
if exists('reading_queue'):
    print('reading_queue_status:', cur.execute('SELECT status, COUNT(*) FROM reading_queue GROUP BY status').fetchall())
