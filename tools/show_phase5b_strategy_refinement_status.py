
import sqlite3
from pathlib import Path
p = Path('ki_memory.sqlite3')
print('db:', p.resolve())
con = sqlite3.connect(str(p)); cur = con.cursor()
def ex(t):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def cnt(t):
    return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if ex(t) else 'missing'
def cols(t):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()] if ex(t) else []
for t in ['facts','relations','questions','context_hypotheses','internal_learning_gaps','internal_learning_questions','reading_queue','chunk_attention_scores','phase5b_strategy_refinement_cycles','phase5b_persistent_gap_strategy','phase5b_reread_diversity_events','phase5b_neuromodulator_adaptation_events','phase5b_internal_question_clusters','phase5b_strategy_refinement_state','phase5a_learning_release_cycles','active_learning_decisions','strategy_feedback_events','gap_resolution_outcomes']:
    print(t, cnt(t))
print('facts_rel_questions:', {t:cnt(t) for t in ['facts','relations','questions']})
if ex('phase5b_strategy_refinement_state'):
    print('phase5b_state:', cur.execute("SELECT key,value FROM phase5b_strategy_refinement_state ORDER BY key").fetchall())
if ex('phase5b_persistent_gap_strategy'):
    print('persistent_gap_strategy_top:', cur.execute("SELECT gap_type,role,ROUND(persistence_score,3),ROUND(resolution_score,3),ROUND(strategy_effectiveness_score,3),recommended_strategy,ROUND(priority_before,3),ROUND(priority_after,3) FROM phase5b_persistent_gap_strategy ORDER BY persistence_score DESC, updated_at DESC LIMIT 12").fetchall())
if ex('phase5b_internal_question_clusters'):
    print('question_clusters_top:', cur.execute("SELECT question_type,role,size,ROUND(avg_priority,3),ROUND(avg_resolution_score,3),recommended_action,status FROM phase5b_internal_question_clusters ORDER BY size DESC LIMIT 12").fetchall())
if ex('phase5b_reread_diversity_events'):
    print('diversity_recent:', cur.execute("SELECT chunk_id,ROUND(old_priority,3),ROUND(new_priority,3),ROUND(old_attention,3),ROUND(new_attention,3),diversity_reason FROM phase5b_reread_diversity_events ORDER BY id DESC LIMIT 12").fetchall())
if ex('phase5b_neuromodulator_adaptation_events'):
    print('adaptation_recent:', cur.execute("SELECT target,ROUND(old_value,3),ROUND(new_value,3),reason FROM phase5b_neuromodulator_adaptation_events ORDER BY id DESC LIMIT 12").fetchall())
if ex('reading_queue'):
    print('reading_queue_top:', cur.execute("SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),reason,status FROM reading_queue ORDER BY COALESCE(priority,0) DESC, COALESCE(attention_score,0) DESC LIMIT 12").fetchall())
