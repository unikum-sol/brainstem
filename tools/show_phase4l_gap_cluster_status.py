import sqlite3,os
p='ki_memory.sqlite3'; print('db:',os.path.abspath(p)); con=sqlite3.connect(p); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def cnt(t): return cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] if ex(t) else 'missing'
for t in ['facts','relations','questions','internal_learning_gaps','internal_learning_questions','gap_clusters','gap_cluster_members','gap_driven_rereading_actions','rereading_candidate_links','reread_cooldowns','exploration_exploitation_events','reading_queue','chunk_attention_scores','strategy_balance_state','context_hypotheses','long_term_pattern_memory']:
 print(t,cnt(t))
if ex('gap_clusters'): print('cluster_top:',cur.execute("SELECT gap_type,role,member_count,ROUND(avg_severity,3),ROUND(avg_uncertainty,3),ROUND(avg_stability,3),strategy,status FROM gap_clusters ORDER BY avg_severity DESC, member_count DESC LIMIT 12").fetchall())
if ex('reread_cooldowns'): print('cooldowns_top:',cur.execute("SELECT chunk_id,ROUND(pressure,3),reason,cooldown_until FROM reread_cooldowns ORDER BY pressure DESC LIMIT 12").fetchall())
if ex('exploration_exploitation_events'): print('balance_recent:',cur.execute("SELECT event_type,ROUND(exploration_pressure,3),ROUND(exploitation_pressure,3),affected_clusters,affected_chunks,created_at FROM exploration_exploitation_events ORDER BY id DESC LIMIT 10").fetchall())
if ex('strategy_balance_state'): print('strategy_balance_state:',cur.execute("SELECT key,value FROM strategy_balance_state ORDER BY key").fetchall())
if ex('reading_queue'): print('reading_queue_top:',cur.execute("SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),reason,status FROM reading_queue ORDER BY priority DESC, attention_score DESC LIMIT 12").fetchall())
print('facts_rel_questions:',{t:cnt(t) for t in ['facts','relations','questions']})
