from __future__ import annotations
import json
import re
import time
from collections import Counter

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
TEMPORAL_RE = re.compile(r'^(seit\s+)?(anfang|mitte|ende|januar|februar|märz|maerz|april|mai|juni|juli|august|september|oktober|november|dezember)\s+\d{4}\b|^\d{4}$|^\d{1,2}\.\s*\w+\s+\d{4}\b', re.I)

BAD_SUBJECT_EXACT = {
    'neu','heute','seitdem','mittlerweile','ursprünglich','urspruenglich','oft','zudem','damit','daher','deshalb','zuvor','bekannt','was',
    'nachfolger','ausschlaggebend','allerdings','insbesondere','zunächst','zunaechst','häufig','haeufig','daher','als beispiele'
}
BAD_SUBJECT_PREFIXES = (
    'seit ', 'anfang ', 'mitte ', 'ende ', 'bis dahin', 'zu beginn', 'die erste ', 'der erste ', 'das erste ',
    'die einzige ', 'der einzige ', 'das einzige ', 'ein wohnsitz ', 'eine niederlassung ', 'ein lokaler wohnsitz',
    'zeichen aus ', 'eigenschaften ', 'die endung lehnt ', 'die verwendung ', 'die seite ', 'der text ', 'das modell ',
    'funktionstabelle ', 'second-level-domains folgende', 'folgende ', 'weitere ', 'einer der ', 'eine der ', 'eines der ',
    'die teuerste ', 'die empfohlene ', 'die folgenden ', 'die dazu ', 'als eigenschaften', 'innerhalb dieses containers'
)
BAD_OBJECT_EXACT = {'der','die','das','ein','eine','einer','eines','poker','sex','linux','mit','zeit aktiv','broome'}
BAD_OBJECT_CONTAINS = (
    'nicht erforderlich','nicht möglich','nicht moeglich','nicht notwendig','nicht zulässig','nicht zulaessig',
    'nicht mehr erforderlich','nicht unumstritten','nicht öffentlich bekannt','nicht oeffentlich bekannt','nicht dazu gedacht',
    'nicht vorhanden, wenn','noch kein weg bekannt','zu beginn leer','zeit aktiv','seitdem gestattet','dabei ', 'damit ',
    'deshalb ', 'und dass', 'und heute', 'also nicht', 'zu nennen', 'ähnlich', 'aehnlich', 'denkbar einfach',
    'erst ab ', 'ausschließlich mit', 'ausschliesslich mit', 'zeit nicht', 'bisher nicht bekannt', 'jedoch wegen'
)
BAD_OBJECT_PREFIXES = (
    'abkömmling des', 'abkoemmling des', 'teil der ', 'bestandteil des ', 'e ', 's ', 'se ', 'ser ', 'und ', 'oder ',
    'also ', 'dabei ', 'damit ', 'deshalb ', 'seit ', 'bei ', 'zur ', 'zu ', 'von ', 'für ', 'fuer ', 'mit ', 'dyMO'.lower()
)
BAD_OBJECT_SUFFIXES = (' des',' der',' die',' das',' von',' für',' fuer',' mit',' bei',' zu',' als',' und',' oder','(', '[', '{', ':')


def norm_text(value):
    return ' '.join(str(value or '').replace('_', ' ').split()).strip()


def norm_key(value):
    return norm_text(value).lower()[:180]


def token_count(value):
    return len(WORD_RE.findall(norm_text(value)))


def relation_key(value):
    return norm_text(value).lower().replace(' ', '_')[:80]


def has_unbalanced_brackets(text):
    text = norm_text(text)
    return (text.count('(') != text.count(')')) or (text.count('[') != text.count(']')) or (text.count('{') != text.count('}'))


class CandidateSleepPruner:
    """Sleep-time candidate maintenance.

    Phase 3d6k never deletes data and never promotes to facts.
    It only marks suspicious candidate_relations as rejected and reinforces learned patterns.
    """
    VERSION = 'phase3d6k_candidate_sleep_pruning_FIXED'

    def __init__(self, memory):
        self.memory = memory
        self.ensure_schema()
        self.state = self.load_state()

    def ensure_schema(self):
        with self.memory.lock:
            db = self.memory.db
            db.execute("""CREATE TABLE IF NOT EXISTS candidate_pruning_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at INTEGER)""")
            db.execute("""CREATE TABLE IF NOT EXISTS candidate_pruning_events(id INTEGER PRIMARY KEY AUTOINCREMENT,candidate_id INTEGER,subject TEXT,relation TEXT,object TEXT,old_status TEXT,new_status TEXT,reason TEXT,score REAL,created_at INTEGER)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_candidate_pruning_events_reason ON candidate_pruning_events(reason, created_at)")
            db.execute("""CREATE TABLE IF NOT EXISTS learned_quality_blocks(kind TEXT,value TEXT,reason TEXT,count INTEGER DEFAULT 0,weight REAL DEFAULT 0,last_seen INTEGER,PRIMARY KEY(kind,value))""")
            db.execute("""CREATE TABLE IF NOT EXISTS adaptive_quality_stats(kind TEXT,value TEXT,accepted_count INTEGER DEFAULT 0,rejected_count INTEGER DEFAULT 0,last_reason TEXT,updated_at INTEGER,PRIMARY KEY(kind,value))""")
            db.execute("""CREATE TABLE IF NOT EXISTS negative_patterns(pattern TEXT PRIMARY KEY,reason TEXT,count INTEGER DEFAULT 0,examples_json TEXT,gaba_weight REAL DEFAULT 0,last_seen INTEGER)""")
            db.execute("""CREATE TABLE IF NOT EXISTS language_patterns(pattern TEXT PRIMARY KEY,pattern_type TEXT,success_count INTEGER DEFAULT 0,failure_count INTEGER DEFAULT 0,confidence REAL DEFAULT 0,inhibition_score REAL DEFAULT 0,attention_score REAL DEFAULT 0,last_examples_json TEXT,created_at INTEGER,updated_at INTEGER)""")
            db.commit()

    def load_state(self):
        row = self.memory.db.execute("SELECT value_json FROM candidate_pruning_state WHERE key='state'").fetchone()
        if row:
            try:
                state = json.loads(row['value_json'])
                if isinstance(state, dict):
                    state.setdefault('version', self.VERSION)
                    state.setdefault('total_pruned', 0)
                    state.setdefault('last_candidate_id', 0)
                    state.setdefault('prune_threshold', 0.62)
                    state.setdefault('sleep_interval_candidates', 100)
                    return state
            except Exception:
                pass
        state = {'version': self.VERSION, 'total_pruned': 0, 'last_candidate_id': 0, 'prune_threshold': 0.62, 'sleep_interval_candidates': 100, 'last_run_at': 0}
        self.save_state(state)
        return state

    def save_state(self, state=None):
        state = state or self.state
        with self.memory.lock:
            self.memory.db.execute("INSERT OR REPLACE INTO candidate_pruning_state(key,value_json,updated_at) VALUES(?,?,?)", ('state', json.dumps(state, ensure_ascii=False), int(time.time())))
            self.memory.db.commit()

    def _pattern(self, subject, relation, obj, reason):
        return f"{reason}:{norm_text(subject)[:40]}->{norm_text(obj)[:40]}".lower()[:180]

    def _append_json(self, old_json, item, limit=8):
        try:
            arr = json.loads(old_json or '[]')
            if not isinstance(arr, list):
                arr = []
        except Exception:
            arr = []
        arr.append(item)
        return json.dumps(arr[-limit:], ensure_ascii=False)

    def _reinforce_negative(self, subject, relation, obj, reason, candidate_id=None):
        now = int(time.time())
        subject_key = norm_key(subject)
        object_key = norm_key(obj)[:120]
        pattern = self._pattern(subject, relation, obj, reason)
        example = {'id': candidate_id, 's': norm_text(subject)[:80], 'r': norm_text(relation), 'o': norm_text(obj)[:100]}
        with self.memory.lock:
            # learned blocks for subject/object
            for kind, value in [('subject', subject_key), ('object', object_key)]:
                if not value:
                    continue
                row = self.memory.db.execute("SELECT count, weight FROM learned_quality_blocks WHERE kind=? AND value=?", (kind, value)).fetchone()
                if row:
                    count = int(row['count'] or 0) + 1
                    weight = min(1.0, max(float(row['weight'] or 0.0), 0.50) + 0.06)
                    self.memory.db.execute("UPDATE learned_quality_blocks SET reason=?, count=?, weight=?, last_seen=? WHERE kind=? AND value=?", (reason, count, weight, now, kind, value))
                else:
                    self.memory.db.execute("INSERT INTO learned_quality_blocks(kind,value,reason,count,weight,last_seen) VALUES(?,?,?,?,?,?)", (kind, value, reason, 1, 0.52, now))
                stat = self.memory.db.execute("SELECT * FROM adaptive_quality_stats WHERE kind=? AND value=?", (kind, value)).fetchone()
                if stat:
                    self.memory.db.execute("UPDATE adaptive_quality_stats SET rejected_count=rejected_count+1,last_reason=?,updated_at=? WHERE kind=? AND value=?", (reason, now, kind, value))
                else:
                    self.memory.db.execute("INSERT INTO adaptive_quality_stats(kind,value,accepted_count,rejected_count,last_reason,updated_at) VALUES(?,?,?,?,?,?)", (kind, value, 0, 1, reason, now))
            # negative pattern
            row = self.memory.db.execute("SELECT count, examples_json FROM negative_patterns WHERE pattern=?", (pattern,)).fetchone()
            if row:
                count = int(row['count'] or 0) + 1
                examples = self._append_json(row['examples_json'], example)
                gaba = min(1.0, 0.20 + count / 18.0)
                self.memory.db.execute("UPDATE negative_patterns SET reason=?,count=?,examples_json=?,gaba_weight=?,last_seen=? WHERE pattern=?", (reason, count, examples, gaba, now, pattern))
            else:
                self.memory.db.execute("INSERT INTO negative_patterns(pattern,reason,count,examples_json,gaba_weight,last_seen) VALUES(?,?,?,?,?,?)", (pattern, reason, 1, json.dumps([example], ensure_ascii=False), 0.25, now))
            # language pattern failure
            lrow = self.memory.db.execute("SELECT failure_count, success_count, last_examples_json FROM language_patterns WHERE pattern=?", (pattern,)).fetchone()
            if lrow:
                failure = int(lrow['failure_count'] or 0) + 1
                success = int(lrow['success_count'] or 0)
                total = max(1, failure + success)
                ex = self._append_json(lrow['last_examples_json'], example)
                self.memory.db.execute("UPDATE language_patterns SET pattern_type=?,failure_count=?,confidence=?,inhibition_score=?,attention_score=?,last_examples_json=?,updated_at=? WHERE pattern=?", ('pruned_candidate', failure, success/total, failure/total, failure/total, ex, now, pattern))
            else:
                self.memory.db.execute("INSERT INTO language_patterns(pattern,pattern_type,success_count,failure_count,confidence,inhibition_score,attention_score,last_examples_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (pattern, 'pruned_candidate', 0, 1, 0.0, 1.0, 1.0, json.dumps([example], ensure_ascii=False), now, now))
            self.memory.db.commit()

    def score_candidate(self, subject, relation, obj, confidence=0.0, scores=None):
        scores = scores or {}
        s = norm_key(subject)
        r = relation_key(relation)
        o = norm_key(obj)
        bad = 0.0
        reasons = []

        if not s or not o or not r:
            return 1.0, 'prune_empty_candidate'
        if s in BAD_SUBJECT_EXACT or any(s.startswith(p) for p in BAD_SUBJECT_PREFIXES):
            bad += 0.75; reasons.append('prune_bad_subject')
        if TEMPORAL_RE.search(s):
            bad += 0.80; reasons.append('prune_temporal_subject')
        if len(norm_text(subject)) > 85 or token_count(subject) > 11:
            bad += 0.45; reasons.append('prune_subject_too_long')
        if norm_text(subject)[:1].islower() and token_count(subject) > 2:
            bad += 0.55; reasons.append('prune_lowercase_subject_fragment')
        if ' und ' in s or ' oder ' in s:
            bad += 0.30; reasons.append('prune_coordinated_subject')

        if r in ('is_a', 'definition'):
            if o in BAD_OBJECT_EXACT:
                bad += 0.80; reasons.append('prune_bad_object_exact')
            if any(x in o for x in BAD_OBJECT_CONTAINS):
                bad += 0.75; reasons.append('prune_bad_is_a_object_phrase')
            if any(o.startswith(p) for p in BAD_OBJECT_PREFIXES):
                bad += 0.65; reasons.append('prune_bad_object_prefix')
            if any(o.endswith(suf) for suf in BAD_OBJECT_SUFFIXES):
                bad += 0.50; reasons.append('prune_object_incomplete')
            if token_count(obj) < 2 or len(norm_text(obj)) < 4:
                bad += 0.70; reasons.append('prune_object_too_short')
            if token_count(obj) > 16 or len(norm_text(obj)) > 135:
                bad += 0.40; reasons.append('prune_object_too_long')
            if has_unbalanced_brackets(obj):
                bad += 0.55; reasons.append('prune_unbalanced_brackets')

        try:
            fragment = float(scores.get('fragment_score', 0.0) or 0.0)
            license_score = float(scores.get('license_score', 0.0) or 0.0)
            alignment = float(scores.get('alignment_score', 0.0) or 0.0)
        except Exception:
            fragment = license_score = alignment = 0.0
        bad += min(0.25, fragment * 0.20)
        bad += min(0.45, license_score * 0.45)
        if alignment < 0.12 and r in ('is_a', 'definition'):
            bad += 0.18; reasons.append('prune_low_alignment')

        # learned block reinforcement: if subject/object already learned as bad, prune strongly.
        for kind, value, label in [('subject', s, 'prune_learned_bad_subject'), ('object', o[:120], 'prune_learned_bad_object')]:
            row = self.memory.db.execute("SELECT weight FROM learned_quality_blocks WHERE kind=? AND value=?", (kind, value)).fetchone()
            if row and float(row['weight'] or 0.0) >= 0.68:
                bad += 0.70; reasons.append(label)

        if not reasons and bad < 0.62:
            return bad, 'keep'
        return min(1.0, bad), reasons[0] if reasons else 'prune_score_high'

    def prune_once(self, batch_size=300, include_old_candidates=True):
        self.ensure_schema()
        threshold = float(self.state.get('prune_threshold', 0.62))
        last_id = int(self.state.get('last_candidate_id', 0))
        where = "status='candidate'"
        params = []
        if not include_old_candidates:
            where += " AND id>?"
            params.append(last_id)
        sql = f"""
            SELECT id, subject, relation, object, confidence, source_chunk_id, source_document_title, context_title,
                   definition_score, fragment_score, license_score, alignment_score, novelty_score, status
            FROM candidate_relations
            WHERE {where}
            ORDER BY id ASC
            LIMIT ?
        """
        params.append(int(batch_size))
        rows = self.memory.rows(sql, tuple(params))
        now = int(time.time())
        counts = Counter()
        samples = []
        max_id = last_id
        for row in rows:
            cid = int(row['id'])
            max_id = max(max_id, cid)
            scores = {
                'definition_score': row['definition_score'], 'fragment_score': row['fragment_score'],
                'license_score': row['license_score'], 'alignment_score': row['alignment_score'], 'novelty_score': row['novelty_score']
            }
            score, reason = self.score_candidate(row['subject'], row['relation'], row['object'], row['confidence'], scores)
            counts['checked'] += 1
            if score >= threshold and reason != 'keep':
                with self.memory.lock:
                    self.memory.db.execute("UPDATE candidate_relations SET status='rejected', reject_reason=COALESCE(reject_reason, ?), rejection_count=rejection_count+1, updated_at=? WHERE id=? AND status='candidate'", (reason, now, cid))
                    self.memory.db.execute("INSERT INTO candidate_pruning_events(candidate_id,subject,relation,object,old_status,new_status,reason,score,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (cid, row['subject'], row['relation'], row['object'], row['status'], 'rejected', reason, float(score), now))
                    self.memory.db.commit()
                self._reinforce_negative(row['subject'], row['relation'], row['object'], reason, cid)
                counts['pruned'] += 1
                counts[reason] += 1
                if len(samples) < 12:
                    samples.append({'id': cid, 'candidate': [row['subject'], row['relation'], row['object']], 'reason': reason, 'score': round(float(score), 3)})
            else:
                counts['kept'] += 1
        self.state['last_candidate_id'] = max_id
        self.state['total_pruned'] = int(self.state.get('total_pruned', 0)) + counts['pruned']
        self.state['last_run_at'] = now
        self.save_state()
        return {'status': 'candidate_sleep_pruning_phase3d6k', 'checked': counts['checked'], 'pruned': counts['pruned'], 'kept': counts['kept'], 'reasons': {k:v for k,v in counts.items() if k not in ('checked','pruned','kept')}, 'samples': samples, 'state': dict(self.state)}


def apply_patch(CorpusReader):
    if getattr(CorpusReader, '_phase3d6k_sleep_pruning_patched', False):
        return
    original = CorpusReader.read_once
    def read_once_with_pruning(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            pruner = getattr(self, '_phase3d6k_candidate_pruner', None)
            if pruner is None:
                pruner = CandidateSleepPruner(self.memory)
                self._phase3d6k_candidate_pruner = pruner
            pruning = pruner.prune_once(batch_size=350, include_old_candidates=True)
            if isinstance(result, dict):
                result['candidate_sleep_pruning'] = pruning
                result['status'] = 'adaptive_alignment_corpus_reader_phase3d6k'
        except Exception as exc:
            if isinstance(result, dict):
                result['candidate_sleep_pruning'] = {'status': 'candidate_sleep_pruning_error_phase3d6k', 'error': str(exc)}
        return result
    CorpusReader.read_once = read_once_with_pruning
    CorpusReader._phase3d6k_sleep_pruning_patched = True
