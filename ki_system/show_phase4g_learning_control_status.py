from pathlib import Path
import sys, sqlite3
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
p = ROOT / 'ki_memory.sqlite3'
con = sqlite3.connect(str(p)); cur = con.cursor()
print('db:', p)
def exists(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def count(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if exists(t) else 'missing'
def kv(t):
    if not exists(t): return []
    cols=[r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()]
    if 'key' in cols and 'value' in cols:
        return cur.execute(f'SELECT key,value FROM {t} ORDER BY key').fetchall()
    return []
for t in ['facts','relations','questions','reading_queue','context_hypotheses','context_learning_events','hypothesis_feedback','hypothesis_error_events','neuromodulated_attention_events','neuromodulator_learning_state','hypothesis_learning_updates','sleep_consolidation_decisions','chunk_attention_scores','attention_queue_state','reading_strategy_state','hypothesis_clusters','hypothesis_stability_scores','context_pattern_memory','neuromodulator_sleep_events','learning_strategy_state','rollback_safe_core_state','neuromodulated_learning_control_state']:
    print(t, count(t))
print('learning_control_state:', kv('neuromodulated_learning_control_state'))
print('reading_strategy_state:', kv('reading_strategy_state'))
print('attention_queue_state:', kv('attention_queue_state'))
if exists('context_hypotheses'):
    cols=[r[1] for r in cur.execute('PRAGMA table_info(context_hypotheses)').fetchall()]
    if 'role' in cols:
        print('hypothesis_roles:', cur.execute('SELECT role, COUNT(*) FROM context_hypotheses GROUP BY role ORDER BY COUNT(*) DESC').fetchall())
if exists('chunk_attention_scores'):
    print('chunk_attention_top:', cur.execute('SELECT chunk_id, ROUND(attention_score,3), ROUND(novelty_score,3), ROUND(uncertainty_score,3), ROUND(reward_score,3), last_reason FROM chunk_attention_scores ORDER BY attention_score DESC LIMIT 10').fetchall())
print('facts_rel_questions:', {'facts': count('facts'), 'relations': count('relations'), 'questions': count('questions')})
con.close()
