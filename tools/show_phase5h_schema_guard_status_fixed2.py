import sys, pathlib, sqlite3
ROOT=pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system.v8_phase5h_schema_guard_fixed2 import ensure_phase5h_schema
ensure_phase5h_schema('ki_memory.sqlite3')
con=sqlite3.connect('ki_memory.sqlite3'); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def count(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
print('db:', pathlib.Path('ki_memory.sqlite3').resolve())
for t in ['facts','relations','questions','phase5g_strategy_experiments','phase5g_experiment_outcomes','phase5g_strategy_selection_memory','phase5h_strategy_outcome_memory','phase5h_experiment_outcome_cycles','phase5h_runtime_state']:
    print(t, count(t))
print('facts_rel_questions:', {t:count(t) for t in ['facts','relations','questions']})
print('phase5g_experiment_outcomes_columns:', cols('phase5g_experiment_outcomes'))
if ex('phase5g_strategy_selection_memory'):
    print('strategy_memory_top:', cur.execute("SELECT memory_key, observations, ROUND(avg_outcome_score,3), ROUND(avg_closure_delta,3), ROUND(avg_no_candidate_rate,3), ROUND(avg_overlap_score,3), recommendation FROM phase5g_strategy_selection_memory ORDER BY observations DESC LIMIT 12").fetchall())
if ex('phase5g_experiment_outcomes'):
    print('outcomes_recent:', cur.execute("SELECT selected_strategy,gap_type,role,ROUND(outcome_score,3),ROUND(closure_delta,3),ROUND(no_candidate_rate,3),ROUND(overlap_score,3),outcome_label,recommendation FROM phase5g_experiment_outcomes ORDER BY rowid DESC LIMIT 12").fetchall())
if ex('phase5h_experiment_outcome_cycles'):
    print('cycles_recent:', cur.execute("SELECT experiments_seen,outcomes_written,memory_updates,ROUND(avg_outcome_score,3),ROUND(avg_closure_delta,3),ROUND(avg_no_candidate_rate,3),ROUND(avg_overlap_score,3),facts,relations,questions,created_at FROM phase5h_experiment_outcome_cycles ORDER BY id DESC LIMIT 5").fetchall())
if ex('phase5h_runtime_state'):
    print('runtime_state:', cur.execute("SELECT key,value FROM phase5h_runtime_state ORDER BY key").fetchall())
