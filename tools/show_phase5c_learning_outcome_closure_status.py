import sqlite3, pathlib
p=pathlib.Path('ki_memory.sqlite3').resolve(); print('db:', p)
con=sqlite3.connect(str(p)); cur=con.cursor()
def ex(t): return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def count(t): return cur.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] if ex(t) else 'missing'
def cols(t): return [r[1] for r in cur.execute('PRAGMA table_info('+t+')').fetchall()] if ex(t) else []
for t in ['facts','relations','questions','internal_learning_questions','phase5b_internal_question_clusters','question_cluster_resolution_events','learning_outcome_closure_events','phase5c_cluster_resolution_memory','phase5c_runtime_state','phase5c_read_outcome_events','reading_queue','chunk_attention_scores','context_hypotheses','internal_learning_gaps']:
    print(t, count(t))
print('facts_rel_questions:', {'facts':count('facts'),'relations':count('relations'),'questions':count('questions')})
print('phase5c_state:', cur.execute("SELECT key,value FROM phase5c_runtime_state ORDER BY key").fetchall() if ex('phase5c_runtime_state') else [])
print('question_cluster_columns:', cols('phase5b_internal_question_clusters'))
if ex('phase5b_internal_question_clusters'):
    c=cols('phase5b_internal_question_clusters')
    if all(x in c for x in ['question_type','role','question_count','phase5c_priority','resolution_score','closure_status']):
        print('question_clusters_resolution_top:', cur.execute("SELECT question_type,role,question_count,ROUND(COALESCE(phase5c_priority,0),3),ROUND(COALESCE(resolution_score,0),3),COALESCE(closure_status,'') FROM phase5b_internal_question_clusters ORDER BY COALESCE(phase5c_priority,0) DESC, question_count DESC LIMIT 12").fetchall())
print('cluster_resolution_recent:', cur.execute("SELECT question_type,role,question_count,ROUND(avg_priority,3),ROUND(avg_resolution_score,3),after_status,decision FROM question_cluster_resolution_events ORDER BY id DESC LIMIT 12").fetchall() if ex('question_cluster_resolution_events') else [])
print('read_outcome_recent:', cur.execute("SELECT target_type,target_id,ROUND(before_priority,3),ROUND(after_priority,3),closure_status,closure_reason FROM learning_outcome_closure_events ORDER BY id DESC LIMIT 12").fetchall() if ex('learning_outcome_closure_events') else [])
if ex('reading_queue') and 'phase5c_outcome_penalty' in cols('reading_queue'):
    print('read_no_candidate_penalties:', cur.execute("SELECT chunk_id,ROUND(priority,3),ROUND(attention_score,3),ROUND(phase5c_outcome_penalty,3),phase5c_reason,status FROM reading_queue WHERE COALESCE(phase5c_outcome_penalty,0)>0 ORDER BY phase5c_last_adjusted_at DESC LIMIT 12").fetchall())
