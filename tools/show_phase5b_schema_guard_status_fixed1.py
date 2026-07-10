import sqlite3
from pathlib import Path
DB = Path('ki_memory.sqlite3')
print('db:', DB.resolve())
con = sqlite3.connect(str(DB)); cur = con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def count(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute('PRAGMA table_info('+t+')').fetchall()] if ex(t) else []
for t in ['facts','relations','questions','internal_learning_gaps','internal_learning_questions','phase5b_strategy_refinement_cycles','phase5b_persistent_gap_strategy','phase5b_internal_question_clusters','phase5b_reread_diversity_events','phase5b_neuromodulator_adaptation_events','phase5b_strategy_refinement_state','reading_queue','chunk_attention_scores']:
    print(t, count(t))
print('internal_learning_questions_columns:', cols('internal_learning_questions'))
print('internal_learning_gaps_columns:', cols('internal_learning_gaps'))
if ex('phase5b_strategy_refinement_state'):
    print('phase5b_state:', cur.execute('SELECT key,value FROM phase5b_strategy_refinement_state ORDER BY key').fetchall())
if ex('phase5b_internal_question_clusters'):
    print('question_clusters_top:', cur.execute("SELECT question_type,role,size,ROUND(avg_priority,3),ROUND(avg_resolution_score,3),recommended_action,status FROM phase5b_internal_question_clusters ORDER BY size DESC LIMIT 12").fetchall())
if ex('phase5b_persistent_gap_strategy'):
    print('persistent_gap_strategy_top:', cur.execute("SELECT gap_type,role,ROUND(persistence_score,3),ROUND(resolution_score,3),ROUND(strategy_effectiveness_score,3),recommended_strategy,ROUND(priority_before,3),ROUND(priority_after,3) FROM phase5b_persistent_gap_strategy ORDER BY persistence_score DESC LIMIT 12").fetchall())
if ex('phase5b_reread_diversity_events'):
    print('diversity_recent:', cur.execute("SELECT chunk_id,ROUND(old_priority,3),ROUND(new_priority,3),diversity_reason FROM phase5b_reread_diversity_events ORDER BY id DESC LIMIT 12").fetchall())
print('facts_rel_questions:', {t: count(t) for t in ['facts','relations','questions']})
