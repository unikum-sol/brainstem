import sqlite3
from pathlib import Path
p = Path('ki_memory.sqlite3').resolve()
print('db:', p)
con = sqlite3.connect(str(p)); cur = con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def cnt(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
for t in ['facts','relations','questions','internal_learning_gaps','internal_learning_questions','gap_detection_events','gap_driven_rereading_actions','rereading_candidate_links','reading_queue','chunk_attention_scores','gap_reread_strategy_state','attention_queue_state','reading_strategy_state','context_hypotheses','hypothesis_error_events','long_term_pattern_memory']:
    print(t, cnt(t))
if ex('gap_driven_rereading_actions'):
    print('recent_actions:', cur.execute("SELECT gap_type,role,chunk_id,ROUND(priority_boost,3),ROUND(attention_score,3),action_type FROM gap_driven_rereading_actions ORDER BY id DESC LIMIT 12").fetchall())
if ex('reading_queue'):
    print('reading_queue_top:', cur.execute("SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),reason,status FROM reading_queue ORDER BY priority DESC, attention_score DESC LIMIT 12").fetchall())
if ex('chunk_attention_scores'):
    print('chunk_attention_top:', cur.execute("SELECT chunk_id,ROUND(attention_score,3),ROUND(uncertainty_score,3),ROUND(reward_score,3),last_reason FROM chunk_attention_scores ORDER BY attention_score DESC LIMIT 12").fetchall())
if ex('gap_reread_strategy_state'):
    print('gap_reread_strategy_state:', cur.execute("SELECT key,value FROM gap_reread_strategy_state ORDER BY key").fetchall())
print('facts_rel_questions:', {t: cnt(t) for t in ['facts','relations','questions']})
