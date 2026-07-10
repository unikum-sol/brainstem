
import sqlite3
from pathlib import Path
p = Path('ki_memory.sqlite3').resolve()
print('db:', p)
con = sqlite3.connect(str(p)); cur = con.cursor()
def exists(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def count(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if exists(t) else 'missing'
for t in ['facts','relations','questions','context_hypotheses','internal_learning_gaps','internal_learning_questions','gap_driven_rereading_actions','rereading_candidate_links','chunk_attention_scores','reading_queue','active_learning_loop_state','active_learning_decisions','learning_control_cycles','neuromodulator_control_history','hypothesis_learning_updates','sleep_consolidation_decisions','long_term_pattern_memory']:
    print(t, count(t))
if exists('active_learning_loop_state'):
    print('active_learning_loop_state:', cur.execute('SELECT key,value FROM active_learning_loop_state ORDER BY key').fetchall())
if exists('learning_control_cycles'):
    print('learning_control_recent:', cur.execute('SELECT phase,hypotheses,gaps,reread_actions,chunk_scores,ROUND(learning_rate,3),ROUND(error_weight,3),ROUND(revision_pressure,3),ROUND(exploration_pressure,3),ROUND(inhibition_level,3),created_at FROM learning_control_cycles ORDER BY id DESC LIMIT 5').fetchall())
if exists('active_learning_decisions'):
    print('active_decisions_recent:', cur.execute('SELECT decision_type,source_signal,affected_count,ROUND(learning_rate,3),ROUND(error_weight,3),ROUND(revision_pressure,3),created_at FROM active_learning_decisions ORDER BY id DESC LIMIT 12').fetchall())
if exists('context_hypotheses') and 'active_learning_score' in [r[1] for r in cur.execute('PRAGMA table_info(context_hypotheses)').fetchall()]:
    print('hypothesis_active_top:', cur.execute('SELECT id,role,ROUND(active_learning_score,3),active_learning_reason FROM context_hypotheses ORDER BY active_learning_score DESC LIMIT 12').fetchall())
if exists('chunk_attention_scores') and 'active_learning_score' in [r[1] for r in cur.execute('PRAGMA table_info(chunk_attention_scores)').fetchall()]:
    print('chunk_active_top:', cur.execute('SELECT chunk_id,ROUND(attention_score,3),ROUND(active_learning_score,3),strategy_reason FROM chunk_attention_scores ORDER BY active_learning_score DESC LIMIT 12').fetchall())
print('facts_rel_questions:', {t: count(t) for t in ['facts','relations','questions']})
con.close()
