import sqlite3, pathlib
p=pathlib.Path('ki_memory.sqlite3')
print('db:',p.resolve())
con=sqlite3.connect(str(p)); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute(f'PRAGMA table_info({t})').fetchall()] if ex(t) else []
for t in ['facts','relations','questions','context_expansion_plans','context_expansion_actions','gap_closure_attempts','context_expansion_memory','phase5e_gap_closure_cycles','phase5e_runtime_state','internal_learning_gaps','internal_learning_questions','reading_queue','chunk_attention_scores','context_hypotheses']:
    print(t,cnt(t))
print('facts_rel_questions:',{t:cnt(t) for t in ['facts','relations','questions']})
print('phase5e_state:',cur.execute('SELECT key,value FROM phase5e_runtime_state ORDER BY key').fetchall() if ex('phase5e_runtime_state') else [])
print('plans_top:',cur.execute("SELECT role,expansion_strategy,COUNT(*),ROUND(AVG(expected_gain),3),status FROM context_expansion_plans GROUP BY role,expansion_strategy,status ORDER BY COUNT(*) DESC LIMIT 12").fetchall() if ex('context_expansion_plans') else [])
print('actions_recent:',cur.execute("SELECT gap_key,chunk_id,neighbor_chunk_id,ROUND(before_priority,3),ROUND(after_priority,3),ROUND(expected_gain,3),reason FROM context_expansion_actions ORDER BY id DESC LIMIT 12").fetchall() if ex('context_expansion_actions') else [])
print('closure_recent:',cur.execute("SELECT gap_key,ROUND(before_resolution_score,3),ROUND(after_resolution_score,3),ROUND(closure_delta,3),outcome,strategy FROM gap_closure_attempts ORDER BY id DESC LIMIT 12").fetchall() if ex('gap_closure_attempts') else [])
print('memory_top:',cur.execute("SELECT memory_key,attempts,ROUND(avg_expected_gain,3),ROUND(avg_closure_delta,3),recommended_strategy,status FROM context_expansion_memory ORDER BY attempts DESC LIMIT 10").fetchall() if ex('context_expansion_memory') else [])
print('reading_queue_top:',cur.execute("SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),reason,status,ROUND(COALESCE(phase5e_priority,0),3) FROM reading_queue ORDER BY COALESCE(phase5e_priority,0) DESC, priority DESC LIMIT 12").fetchall() if ex('reading_queue') else [])
print('internal_learning_gaps_phase5e_cols:',[c for c in cols('internal_learning_gaps') if c.startswith('phase5e') or c in ('resolution_score','priority','strategy_effectiveness_score')])
print('chunk_attention_phase5e_cols:',[c for c in cols('chunk_attention_scores') if c.startswith('phase5e') or c in ('context_expansion_score','gap_closure_boost')])
