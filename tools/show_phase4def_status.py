
import sqlite3
from pathlib import Path
DB = Path('ki_memory.sqlite3').resolve()
con = sqlite3.connect(str(DB))
cur = con.cursor()
print('db:', DB)

def ex(t):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None

def cols(t):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()] if ex(t) else []

def count(t):
    return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if ex(t) else 'missing'

for t in ['facts','relations','questions','reading_queue','context_hypotheses','context_learning_events','hypothesis_feedback','hypothesis_revisions','hypothesis_error_events','neuromodulated_attention_events','context_role_stats','chunk_attention_scores','attention_queue_state','reading_strategy_state','hypothesis_clusters','hypothesis_stability_scores','context_pattern_memory','neuromodulator_sleep_events','learning_strategy_state','rollback_safe_core_state']:
    print(t, count(t))

if ex('rollback_safe_core_state'):
    print('rollback_state:', cur.execute('SELECT key,value FROM rollback_safe_core_state ORDER BY key').fetchall())
if ex('context_hypotheses') and 'role' in cols('context_hypotheses'):
    print('hypothesis_roles:', cur.execute('SELECT role, COUNT(*) FROM context_hypotheses GROUP BY role ORDER BY COUNT(*) DESC').fetchall())
if ex('reading_queue') and 'status' in cols('reading_queue'):
    print('reading_queue_status:', cur.execute('SELECT status, COUNT(*) FROM reading_queue GROUP BY status').fetchall())
for t in ['hypothesis_feedback','context_pattern_memory','hypothesis_clusters','chunk_attention_scores','hypothesis_stability_scores','context_role_stats']:
    print(t + '_columns:', cols(t))
if ex('context_role_stats') and 'role' in cols('context_role_stats'):
    select_cols=[]
    c=cols('context_role_stats')
    for col in ['role','seen','seen_count','avg_confidence','avg_uncertainty','feedback_count','error_count']:
        if col in c: select_cols.append(col)
    if select_cols:
        print('role_stats:', cur.execute('SELECT '+','.join(select_cols)+' FROM context_role_stats ORDER BY '+('seen_count' if 'seen_count' in c else 'seen')+' DESC LIMIT 20').fetchall())
if ex('chunk_attention_scores'):
    print('chunk_attention_top:', cur.execute('SELECT * FROM chunk_attention_scores ORDER BY attention_score DESC LIMIT 10').fetchall())
