
import sqlite3
from pathlib import Path
p='ki_memory.sqlite3'
con=sqlite3.connect(p); cur=con.cursor()
print('db:', Path(p).resolve())
def ex(t): return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
def idx(t): return [(r[1],r[2]) for r in cur.execute(f'PRAGMA index_list({t})').fetchall()] if ex(t) else []
for t in ['facts','relations','questions','reading_queue','context_hypotheses','context_learning_events','hypothesis_feedback','hypothesis_revisions','hypothesis_error_events','neuromodulated_attention_events','context_role_stats','chunk_attention_scores','attention_queue_state','reading_strategy_state','hypothesis_clusters','hypothesis_stability_scores','context_pattern_memory','neuromodulator_sleep_events','learning_strategy_state','rollback_safe_core_state']:
    print(t,cnt(t))
if ex('rollback_safe_core_state'):
    print('rollback_state:', cur.execute('SELECT key,value FROM rollback_safe_core_state ORDER BY key').fetchall())
for t in ['neuromodulator_sleep_events','hypothesis_stability_scores','neuromodulated_attention_events','hypothesis_error_events','hypothesis_feedback','context_pattern_memory','hypothesis_clusters','chunk_attention_scores','context_role_stats','reading_queue']:
    print(t+'_columns:', cols(t))
    print(t+'_indexes:', idx(t))
if ex('context_hypotheses') and 'role' in cols('context_hypotheses'):
    print('hypothesis_roles:', cur.execute('SELECT role,COUNT(*) FROM context_hypotheses GROUP BY role ORDER BY COUNT(*) DESC').fetchall())
if ex('reading_queue'):
    print('reading_queue_status:', cur.execute('SELECT status,COUNT(*) FROM reading_queue GROUP BY status').fetchall())
