from pathlib import Path
import sqlite3, sys
ROOT = Path(__file__).resolve().parents[1]
db_path = ROOT / 'ki_memory.sqlite3'
print('db:', db_path)
con = sqlite3.connect(str(db_path)); cur = con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def count(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
def q(sql):
    try: return cur.execute(sql).fetchall()
    except Exception as e: return [('ERROR', str(e))]
for t in ['facts','relations','questions','phase5a_learning_release_cycles','phase5a_component_health','phase5a_integrated_runtime_state','phase5a_integrated_learning_summary','context_hypotheses','internal_learning_gaps','strategy_feedback_events','gap_resolution_outcomes','active_learning_decisions','learning_progress_evaluations','long_term_pattern_memory','hypothesis_learning_updates','sleep_consolidation_decisions','reading_queue','chunk_attention_scores']:
    print(t, count(t))
print('facts_rel_questions:', {k: count(k) for k in ['facts','relations','questions']})
print('phase5a_runtime_state:', q("SELECT key,value FROM phase5a_integrated_runtime_state ORDER BY key"))
print('component_health:', q("SELECT component_key,component_name,active,table_count,last_status FROM phase5a_component_health ORDER BY component_key"))
print('release_cycles_recent:', q("SELECT phase,hypotheses,gaps,progress_evaluations,strategy_feedback_events,gap_resolution_outcomes,ROUND(integrated_health_score,3),safety_ok,created_at FROM phase5a_learning_release_cycles ORDER BY id DESC LIMIT 10"))
print('integrated_summary:', q("SELECT summary_key,value FROM phase5a_integrated_learning_summary ORDER BY summary_key"))
con.close()
