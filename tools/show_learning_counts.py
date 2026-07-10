import sqlite3
con = sqlite3.connect('ki_memory.sqlite3')
cur = con.cursor()
tables = [
    'facts','relations','candidate_relations','language_patterns','negative_patterns','word_roles','reading_queue','questions',
    'adaptive_quality_stats','learned_quality_blocks','adaptive_quality_state','alignment_role_state','token_role_stats','subject_role_stats',
    'candidate_pruning_state','candidate_pruning_events','relation_repair_state','relation_repair_events',
    'definition_guard_state','definition_guard_events','candidate_type_refinement_state','candidate_type_refinement_events'
]
for t in tables:
    if cur.execute('SELECT name FROM sqlite_master WHERE type=? AND name=?', ('table', t)).fetchone():
        print(t, cur.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0])
