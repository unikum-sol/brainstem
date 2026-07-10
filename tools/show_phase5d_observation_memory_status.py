import sqlite3, os
from pathlib import Path
DB = Path(__file__).resolve().parents[1] / 'ki_memory.sqlite3'
print('db:', DB)
con=sqlite3.connect(str(DB)); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t):
    if not ex(t): return 'missing'
    return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
for t in ['facts','relations','questions','context_hypotheses','internal_learning_gaps','internal_learning_questions','strategy_feedback_events','gap_resolution_outcomes','phase5d_observation_memory','phase5d_strategy_memory_events','phase5d_observation_cycles','phase5d_strategy_recommendations','phase5d_runtime_state','reading_queue','chunk_attention_scores']:
    print(t, cnt(t))
print('facts_rel_questions:', {t: cnt(t) for t in ['facts','relations','questions']})
if ex('phase5d_runtime_state'):
    print('phase5d_state:', cur.execute('SELECT key,value FROM phase5d_runtime_state ORDER BY key').fetchall())
if ex('phase5d_observation_memory'):
    print('observation_memory_top:', cur.execute('SELECT memory_key, observation_type, observations, ROUND(avg_outcome_score,3), ROUND(avg_resolution_score,3), ROUND(persistent_gap_pressure,3), ROUND(read_no_candidate_pressure,3), recommendation FROM phase5d_observation_memory ORDER BY observations DESC, updated_at DESC LIMIT 12').fetchall())
if ex('phase5d_observation_cycles'):
    print('cycles_recent:', cur.execute('SELECT phase,hypotheses,gaps,feedback_events,resolution_events,ROUND(outcome_score,3),ROUND(avg_resolution_score,3),persistent_gap_count,read_no_candidate_penalties,safety_ok,created_at FROM phase5d_observation_cycles ORDER BY id DESC LIMIT 8').fetchall())
if ex('phase5d_strategy_recommendations'):
    print('recommendations_recent:', cur.execute('SELECT recommendation_type,target,ROUND(strength,3),reason,status,created_at FROM phase5d_strategy_recommendations ORDER BY id DESC LIMIT 12').fetchall())
if ex('internal_learning_gaps'):
    cols=[r[1] for r in cur.execute('PRAGMA table_info(internal_learning_gaps)').fetchall()]
    print('internal_learning_gaps_has_phase5d:', [c for c in cols if c.startswith('phase5d')])
if ex('chunk_attention_scores'):
    cols=[r[1] for r in cur.execute('PRAGMA table_info(chunk_attention_scores)').fetchall()]
    print('chunk_attention_scores_has_phase5d:', [c for c in cols if c.startswith('phase5d')])
