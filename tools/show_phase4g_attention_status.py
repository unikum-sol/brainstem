
import sqlite3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
db = ROOT / 'ki_memory.sqlite3'
con = sqlite3.connect(str(db))
cur = con.cursor()
print('db:', db)

def ex(t):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None

def cnt(t):
    if not ex(t): return 'missing'
    return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]

for t in ['facts','relations','questions','reading_queue','context_hypotheses','context_learning_events','hypothesis_feedback','hypothesis_error_events','neuromodulated_attention_events','neuromodulator_learning_state','hypothesis_learning_updates','sleep_consolidation_decisions','chunk_attention_scores','attention_queue_state','reading_strategy_state','hypothesis_clusters','hypothesis_stability_scores','context_pattern_memory','neuromodulator_sleep_events','learning_strategy_state','rollback_safe_core_state']:
    print(t, cnt(t))
if ex('chunk_attention_scores'):
    print('chunk_attention_top:', cur.execute('SELECT chunk_id, ROUND(attention_score,3), ROUND(learning_rate,3), ROUND(error_weight,3), ROUND(revision_pressure,3), last_reason FROM chunk_attention_scores ORDER BY attention_score DESC LIMIT 10').fetchall())
if ex('reading_strategy_state'):
    print('reading_strategy_state:', cur.execute('SELECT key,value FROM reading_strategy_state ORDER BY key LIMIT 30').fetchall())
if ex('attention_queue_state'):
    print('attention_queue_state:', cur.execute('SELECT key,value FROM attention_queue_state ORDER BY key LIMIT 30').fetchall())
if ex('neuromodulator_learning_state'):
    print('learning_state_recent:', cur.execute('SELECT id, ROUND(learning_rate,3), ROUND(error_weight,3), ROUND(revision_pressure,3), ROUND(consolidation_gain,3), ROUND(exploration_pressure,3), ROUND(inhibition_level,3) FROM neuromodulator_learning_state ORDER BY id DESC LIMIT 5').fetchall())
if ex('hypothesis_learning_updates'):
    print('hypothesis_learning_updates_recent:', cur.execute('SELECT hypothesis_id, ROUND(old_confidence,3), ROUND(new_confidence,3), ROUND(old_uncertainty,3), ROUND(new_uncertainty,3), update_reason FROM hypothesis_learning_updates ORDER BY id DESC LIMIT 10').fetchall())
print('facts_rel_questions:', {t: cnt(t) for t in ['facts','relations','questions']})
con.close()
