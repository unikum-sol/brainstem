
import sys, sqlite3, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DB = ROOT / 'ki_memory.sqlite3'
con = sqlite3.connect(DB)
cur = con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def count(t):
    if not ex(t): return 'missing'
    return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
def cols(t):
    if not ex(t): return []
    return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()]
print('db:', DB)
for t in ['facts','relations','questions','phase5g_strategy_experiments','phase5g_experiment_outcomes','phase5g_strategy_selection_memory','phase5h_strategy_outcome_memory','phase5h_experiment_outcome_cycles','phase5h_experiment_learning_events','phase5h_runtime_state','phase5g_neuromodulator_strategy_profiles','reading_queue','chunk_attention_scores','internal_learning_gaps','context_hypotheses']:
    print(t, count(t))
print('facts_rel_questions:', {'facts':count('facts'), 'relations':count('relations'), 'questions':count('questions')})
if ex('phase5h_runtime_state'):
    print('phase5h_state:', cur.execute('SELECT key,value FROM phase5h_runtime_state ORDER BY key').fetchall())
if ex('phase5g_experiment_outcomes'):
    print('outcomes_recent:', cur.execute("SELECT selected_strategy,gap_type,role,COUNT(*),ROUND(AVG(outcome_score),3),ROUND(AVG(closure_delta),3),ROUND(AVG(no_candidate_rate),3),ROUND(AVG(overlap_score),3), outcome_label FROM phase5g_experiment_outcomes GROUP BY selected_strategy,gap_type,role,outcome_label ORDER BY COUNT(*) DESC LIMIT 12").fetchall())
if ex('phase5g_strategy_selection_memory'):
    print('phase5g_strategy_memory_top:', cur.execute("SELECT selected_strategy,gap_type,role,observations,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_no_candidate_rate,3),ROUND(avg_overlap_score,3),recommendation FROM phase5g_strategy_selection_memory ORDER BY observations DESC LIMIT 12").fetchall())
if ex('phase5h_strategy_outcome_memory'):
    print('phase5h_memory_top:', cur.execute("SELECT selected_strategy,gap_type,role,observations,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_no_candidate_rate,3),ROUND(avg_overlap_score,3),recommendation FROM phase5h_strategy_outcome_memory ORDER BY observations DESC LIMIT 12").fetchall())
if ex('phase5h_experiment_outcome_cycles'):
    print('cycles_recent:', cur.execute("SELECT experiments_seen,outcomes_written,memory_updates,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_no_candidate_rate,3),ROUND(avg_overlap_score,3),recommendation,created_at FROM phase5h_experiment_outcome_cycles ORDER BY id DESC LIMIT 8").fetchall())
print('phase5g_experiment_outcomes_columns:', cols('phase5g_experiment_outcomes'))
print('phase5g_strategy_selection_memory_columns:', cols('phase5g_strategy_selection_memory'))
print('phase5h_strategy_outcome_memory_columns:', cols('phase5h_strategy_outcome_memory'))
