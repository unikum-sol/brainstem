from __future__ import annotations
import json
import time
from collections import Counter

try:
    from ki_system import nlp
    from ki_system.relation_quality import evaluate_relations
    from ki_system.wiki_quality import topic_to_question, is_good_topic, normalize_topic_from_question
except Exception:
    nlp = None
    evaluate_relations = None
    topic_to_question = None
    is_good_topic = None
    normalize_topic_from_question = None

BAD_TOPICS = {
    'der text','creative commons','attribution-share alike 4','cm-flak','cm-gebirgshaubitze 40',
    'vor dem abschuss','der rückstoß','der rueckstoss','dies','und','jedoch','aber','deutsch','1/deutsch',
    'der verschluss','unten am wiegentrog','ergänzend','ergaenzend','einige davon','montiert',
    'gecs','days','reasons','reason','da 02','da 20','10+2',
    'verfügbar unter creative commons attribution-share alike 4','verfuegbar unter creative commons attribution-share alike 4',
    'modus die 24 mannschaften','in zwei gruppen zu je 12 teams eingeteilt','the encyclopedia of weapons of world'
}
BAD_TOPIC_PARTS = (
    'creative commons','encyclopedia of weapons','in zwei gruppen','modus die','zu je 12 teams',
    'vor dem abschuss','rückstoß','rueckstoss','uhrenwerke gebr','zentrale plattform',
    'begriffsklärungsseite','begriffsklaerungsseite','unterscheidung mehrerer','auf dem cover'
)

class ExtractionDiagnostics:
    def __init__(self, memory):
        self.memory = memory
        self._ensure()

    def _ensure(self):
        if getattr(self.memory, 'readonly', False):
            return
        with self.memory.lock:
            self.memory.db.execute("CREATE TABLE IF NOT EXISTS extraction_diagnostics_log(id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER, checked_chunks INTEGER DEFAULT 0, relation_chunks INTEGER DEFAULT 0, relations_seen INTEGER DEFAULT 0, known_relations INTEGER DEFAULT 0, potentially_new_relations INTEGER DEFAULT 0, seeded_questions INTEGER DEFAULT 0, sample_json TEXT)")
            self.memory.db.execute('CREATE INDEX IF NOT EXISTS idx_extraction_diagnostics_created ON extraction_diagnostics_log(created_at)')
            self.memory.db.commit()

    def _rows(self, sql, params=()):
        return self.memory.rows(sql, params)

    def _fact_exists(self, s, r, o):
        try:
            return bool(self._rows('SELECT id FROM facts WHERE lower(subject)=lower(?) AND lower(relation)=lower(?) AND lower(object)=lower(?) LIMIT 1', (s, r, o)))
        except Exception:
            return False

    def _chunk_context(self, row):
        try:
            meta = json.loads(row['metadata_json'] or '{}')
            return meta.get('article') or row['title'] or ''
        except Exception:
            try: return row['title'] or ''
            except Exception: return ''

    def _candidate_chunks(self, limit):
        sql = "SELECT chunks.id,chunks.text,chunks.metadata_json,documents.title,documents.path,COALESCE(chunk_learning_state.status,'new') AS cstatus,COALESCE(chunk_learning_state.checked_count,0) AS checked_count FROM chunks JOIN documents ON documents.id=chunks.document_id LEFT JOIN chunk_learning_state ON chunk_learning_state.chunk_id=chunks.id WHERE length(COALESCE(chunks.text,'')) >= 180 AND COALESCE(chunk_learning_state.status,'new') NOT IN ('no_relations','exhausted_known') AND COALESCE(chunk_learning_state.checked_count,0) < 5 ORDER BY COALESCE(chunk_learning_state.checked_count,0) ASC, chunks.id DESC LIMIT ?"
        try: return self._rows(sql, (int(limit),))
        except Exception: return self._rows("SELECT chunks.id,chunks.text,chunks.metadata_json,documents.title,documents.path FROM chunks JOIN documents ON documents.id=chunks.document_id WHERE length(COALESCE(chunks.text,'')) >= 180 ORDER BY chunks.id DESC LIMIT ?", (int(limit),))

    def _good_topic_candidate(self, t):
        t = (t or '').strip().lower().replace('_',' ')
        if not t or t in BAD_TOPICS: return False
        if any(part in t for part in BAD_TOPIC_PARTS): return False
        if len(t) < 4 or len(t) > 65: return False
        if len(t.split()) > 5: return False
        if t in {'und','jedoch','aber','oder','deutsch','dies'}: return False
        if t.startswith(('bei ','vor ','im ','in ','an ','auf ','mit ','für ','fuer ','von ','unten ','oben ','cover ')): return False
        if t.startswith('cm-'): return False
        return True

    def diagnose(self, chunk_limit=320, sample_limit=10):
        if nlp is None or evaluate_relations is None:
            return {'status':'diagnostics_unavailable'}
        checked = relation_chunks = raw_seen = accepted_seen = known = potential = 0
        rejected_by_reason = Counter(); sample=[]; rejected_sample=[]; repaired_sample=[]; topic_counter=Counter()
        for row in self._candidate_chunks(chunk_limit):
            checked += 1
            ctx = self._chunk_context(row)
            try: raw = nlp.extract_relations(row['text'] or '', context_subject=ctx)
            except Exception as exc:
                if len(sample) < sample_limit: sample.append({'chunk_id': row['id'], 'title': ctx, 'error': str(exc)})
                continue
            ev = evaluate_relations(raw, context_subject=ctx)
            raw_seen += ev['raw_relations']; accepted_seen += ev['accepted_relations']
            rejected_by_reason.update(ev.get('rejected_by_reason', {}))
            if len(rejected_sample) < sample_limit:
                rejected_sample.extend(ev.get('rejected_sample', [])[:sample_limit-len(rejected_sample)])
            if len(repaired_sample) < sample_limit:
                repaired_sample.extend(ev.get('repaired_sample', [])[:sample_limit-len(repaired_sample)])
            if ev['accepted_relations']:
                relation_chunks += 1
            for s,r,o,c in ev['accepted']:
                exists = self._fact_exists(s,r,o)
                if exists: known += 1
                else:
                    potential += 1
                    for cand in (s,o,ctx):
                        t = (cand or '').strip().lower().replace('_',' ')
                        if self._good_topic_candidate(t): topic_counter[t] += 1
                if len(sample) < sample_limit:
                    sample.append({'chunk_id': row['id'], 'title': ctx, 'relation': [s,r,o], 'known': exists})
        result = {'status':'ok','checked_chunks':checked,'relation_chunks':relation_chunks,'raw_relations_seen':raw_seen,'relations_seen':accepted_seen,'accepted_relations':accepted_seen,'known_relations':known,'potentially_new_relations':potential,'rejected_total':sum(rejected_by_reason.values()),'rejected_by_reason':dict(rejected_by_reason),'rejected_sample':rejected_sample,'repaired_sample':repaired_sample,'top_candidate_topics':topic_counter.most_common(12),'sample':sample}
        if not getattr(self.memory, 'readonly', False):
            with self.memory.lock:
                self.memory.db.execute('INSERT INTO extraction_diagnostics_log(created_at,checked_chunks,relation_chunks,relations_seen,known_relations,potentially_new_relations,seeded_questions,sample_json) VALUES(?,?,?,?,?,?,?,?)', (int(time.time()), checked, relation_chunks, accepted_seen, known, potential, 0, json.dumps(result, ensure_ascii=False)))
                self.memory.db.commit()
        return result

    def seed_questions(self, limit=30):
        if topic_to_question is None: return {'status':'seed_unavailable','created':0}
        diag = self.diagnose(chunk_limit=340, sample_limit=8)
        existing=set()
        try:
            for r in self._rows('SELECT question FROM questions LIMIT 500000'):
                if normalize_topic_from_question: existing.add(normalize_topic_from_question(r['question']))
        except Exception: pass
        created=0; selected=[]
        for topic,count in diag.get('top_candidate_topics', []):
            if created >= int(limit): break
            t=topic.strip().lower()
            if t in existing or not self._good_topic_candidate(t): continue
            if is_good_topic and not is_good_topic(t): continue
            try:
                self.memory.add_question(topic_to_question(t), 0.94)
                existing.add(t); created += 1; selected.append({'topic':t,'score':count})
            except Exception: continue
        if not getattr(self.memory, 'readonly', False):
            with self.memory.lock:
                self.memory.db.execute('UPDATE extraction_diagnostics_log SET seeded_questions=? WHERE id=(SELECT max(id) FROM extraction_diagnostics_log)', (created,)); self.memory.db.commit()
        return {'status':'seeded_from_extraction_diagnostics','created':created,'selected':selected,'diagnostics':diag}

def run_extraction_diagnostics(memory, chunk_limit=320):
    return ExtractionDiagnostics(memory).diagnose(chunk_limit=chunk_limit)

def seed_questions_from_extraction_diagnostics(memory, limit=30):
    return ExtractionDiagnostics(memory).seed_questions(limit=limit)
