from __future__ import annotations
import time

class ChunkAffect:
    def __init__(self, memory):
        self.memory = memory
        self._ensure()

    def _ensure(self):
        if getattr(self.memory, 'readonly', False):
            return
        with self.memory.lock:
            self.memory.db.execute("CREATE TABLE IF NOT EXISTS chunk_learning_state(chunk_id INTEGER PRIMARY KEY, checked_count INTEGER DEFAULT 0, relations_seen INTEGER DEFAULT 0, new_facts INTEGER DEFAULT 0, known_only INTEGER DEFAULT 0, no_relations INTEGER DEFAULT 0, score REAL DEFAULT 0, status TEXT DEFAULT 'new', last_checked_at INTEGER)")
            self.memory.db.execute('CREATE INDEX IF NOT EXISTS idx_chunk_learning_state_status ON chunk_learning_state(status)')
            self.memory.db.execute('CREATE INDEX IF NOT EXISTS idx_chunk_learning_state_score ON chunk_learning_state(score)')
            self.memory.db.execute('CREATE INDEX IF NOT EXISTS idx_chunk_learning_state_checked ON chunk_learning_state(checked_count)')
            self.memory.db.execute("UPDATE chunk_learning_state SET status='exhausted_known', score=CASE WHEN score>-0.30 THEN -0.30 ELSE score END WHERE status='known_only' AND checked_count>=3 AND new_facts=0")
            self.memory.db.commit()

    def update(self, chunk_id, relations_seen=0, new_facts=0):
        if getattr(self.memory, 'readonly', False):
            return
        rel = int(relations_seen or 0)
        nf = int(new_facts or 0)
        now = int(time.time())
        with self.memory.lock:
            self.memory.db.execute('INSERT OR IGNORE INTO chunk_learning_state(chunk_id,last_checked_at) VALUES(?,?)', (chunk_id, now))
            row = self.memory.db.execute('SELECT checked_count,score FROM chunk_learning_state WHERE chunk_id=?', (chunk_id,)).fetchone()
            old = float(row['score'] or 0.0)
            checked_new = int(row['checked_count'] or 0) + 1
            if nf > 0:
                status, delta = 'productive', 0.38 + min(nf, 5) * 0.08
            elif rel > 0:
                status, delta = ('exhausted_known' if checked_new >= 3 else 'known_only'), -0.14
            else:
                status, delta = 'no_relations', -0.18
            score = max(-1.0, min(1.0, old * 0.78 + delta))
            self.memory.db.execute('UPDATE chunk_learning_state SET checked_count=checked_count+1, relations_seen=relations_seen+?, new_facts=new_facts+?, known_only=known_only+?, no_relations=no_relations+?, score=?, status=?, last_checked_at=? WHERE chunk_id=?', (rel, nf, 1 if rel > 0 and nf == 0 else 0, 1 if rel == 0 else 0, score, status, now, chunk_id))
            self.memory.db.commit()

    def candidate_chunks(self, limit=140):
        sql = "SELECT chunks.id,chunks.text,chunks.metadata_json,documents.title,documents.path,COALESCE(chunk_learning_state.score,0) AS cscore,COALESCE(chunk_learning_state.checked_count,0) AS checked_count FROM chunks JOIN documents ON documents.id=chunks.document_id LEFT JOIN chunk_learning_state ON chunk_learning_state.chunk_id=chunks.id WHERE COALESCE(chunk_learning_state.status,'new') NOT IN ('no_relations','exhausted_known') AND NOT (COALESCE(chunk_learning_state.status,'new')='known_only' AND COALESCE(chunk_learning_state.checked_count,0)>=2) AND COALESCE(chunk_learning_state.checked_count,0)<3 ORDER BY COALESCE(chunk_learning_state.checked_count,0) ASC,COALESCE(chunk_learning_state.score,0) DESC,chunks.id DESC LIMIT ?"
        return self.memory.rows(sql, (int(limit),))

    def summary(self, limit=8):
        productive = self.memory.rows('SELECT chunk_id,score,new_facts,relations_seen,status FROM chunk_learning_state WHERE new_facts>0 ORDER BY score DESC,new_facts DESC LIMIT ?', (int(limit),))
        if not productive:
            productive = self.memory.rows('SELECT chunk_id,score,new_facts,relations_seen,status FROM chunk_learning_state ORDER BY score DESC,new_facts DESC LIMIT ?', (int(limit),))
        blocked = self.memory.rows('SELECT chunk_id,score,checked_count,status FROM chunk_learning_state ORDER BY score ASC,checked_count DESC LIMIT ?', (int(limit),))
        return {'top_productive_chunks': [dict(r) for r in productive], 'top_blocked_chunks': [dict(r) for r in blocked]}
