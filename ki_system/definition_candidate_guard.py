from __future__ import annotations
import json
import re
import time
from collections import Counter

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')

BAD_DEFINITION_SUBJECT_EXACT = {
    'nachfolger','neu','heute','bekannt','was','allerdings','beliebt','insbesondere','zunächst','zunaechst',
    'daher','deshalb','damit','zudem','insofern','als beispiele'
}
BAD_DEFINITION_SUBJECT_PREFIXES = (
    'europaweit größter', 'europaweit groesster', 'weltweit größter', 'weltweit groesster', 'größter', 'groesster',
    'einige der', 'einige ', 'die ursprüngliche domain', 'die urspruengliche domain', 'die ursprüngliche', 'die urspruengliche',
    'die erste ', 'der erste ', 'das erste ', 'die folgenden ', 'folgende ', 'weitere ', 'generische begriffe ',
    'ein wohnsitz ', 'eine niederlassung ', 'nur staatsbürger', 'nur staatsbuerger', 'eigenschaften ',
    'einzig die veröffentlichung', 'einzig die veroeffentlichung', 'die verwendung ', 'die teuerste ', 'die einzige ',
    'die empfohlene ', 'diese version', 'verbreitung nach offiziellen angaben', 'als eigenschaften',
    'innerhalb dieses containers', 'ein typischer gattungsbegriff', 'treibende kraft ', 'systeminformationen ',
    'ein beispiel dafür', 'ein beispiel dafuer', 'übliche zeichensatztabellen', 'uebliche zeichensatztabellen'
)
BAD_DEFINITION_OBJECT_EXACT = {
    'poker','sex','linux','casino','broome','verfügbar','verfuegbar','möglich','moeglich','ähnlich','aehnlich',
    'blau','rot','grün','gruen','gelb','schwarz','weiß','weiss', 'tor2web'
}
BAD_DEFINITION_OBJECT_PHRASES = (
    'nicht erforderlich','nicht möglich','nicht moeglich','nicht notwendig','nicht zulässig','nicht zulaessig','nicht gestattet',
    'nicht unumstritten','nicht dazu gedacht','nicht vorhanden','noch kein weg bekannt','zu beginn leer','zeit aktiv','seitdem gestattet',
    'dabei ', 'damit ', 'deshalb ', 'und dass', 'und heute', 'also nicht', 'zu nennen', 'bisher nicht bekannt',
    'offiziell notwendig','berechtigt, eine','gegenüber dem normalen','gegenueber dem normalen','dazu nicht zugelassen',
    'anfang ', 'ende ', 'mitte ', 'seit ', 'erst ab ', 'ausschließlich mit', 'ausschliesslich mit'
)
TECH_SUBJECT_HINTS = (
    'protokoll','framework','software','programm','betriebssystem','prozessor','mikroprozessor','dateiformat','format',
    'standard','algorithmus','architektur','netzwerk','datenbank','programmiersprache','sprache','bibliothek','schnittstelle',
    'system','domain','server','client','cpu','gpu','unternehmen','projekt','diagramm','gerät','geraet','tool','paket'
)
ENTITY_OBJECT_HINTS = (
    'protokoll','framework','software','programm','betriebssystem','prozessor','dateiformat','format','standard','algorithmus',
    'architektur','netzwerk','datenbank','sprache','bibliothek','schnittstelle','system','domain','server','client','unternehmen',
    'projekt','diagramm','gerät','geraet','tool','paket','anwendung','forks','fork'
)
PROPERTY_SUBJECT_HINTS = ('domain','ursprüngliche domain','urspruengliche domain','codename','name','farbe','größe','groesse','geschwindigkeit')


def norm_text(v):
    return ' '.join(str(v or '').replace('_', ' ').split()).strip()


def norm_key(v):
    return norm_text(v).lower()[:220]


def relation_key(v):
    return norm_text(v).lower().replace(' ', '_')[:80]


def tokens(v):
    return [t.lower() for t in WORD_RE.findall(norm_text(v))]


def token_count(v):
    return len(tokens(v))


def subject_bad_for_definition(subject):
    s = norm_key(subject)
    if not s:
        return True, 'empty_subject'
    if s in BAD_DEFINITION_SUBJECT_EXACT:
        return True, 'bad_definition_subject_exact'
    if any(s.startswith(p) for p in BAD_DEFINITION_SUBJECT_PREFIXES):
        return True, 'bad_definition_subject_prefix'
    if norm_text(subject)[:1].islower() and token_count(subject) > 2:
        return True, 'lowercase_subject_fragment'
    if token_count(subject) > 10:
        return True, 'definition_subject_too_long'
    if (' und ' in s or ' oder ' in s) and token_count(subject) > 5:
        return True, 'coordinated_definition_subject'
    return False, ''


def object_bad_for_definition(obj):
    o = norm_key(obj)
    if not o:
        return True, 'empty_object'
    if o in BAD_DEFINITION_OBJECT_EXACT:
        return True, 'bad_definition_object_exact'
    if any(p in o for p in BAD_DEFINITION_OBJECT_PHRASES):
        return True, 'bad_definition_object_phrase'
    if token_count(obj) < 2:
        return True, 'definition_object_too_short'
    if token_count(obj) > 14 or len(norm_text(obj)) > 135:
        return True, 'definition_object_too_long'
    if any(o.endswith(suf) for suf in (' des',' der',' die',' das',' von',' für',' fuer',' mit',' bei',' zu',' als',' und',' oder','(', '[', '{', ':')):
        return True, 'definition_object_incomplete'
    return False, ''


def should_be_property(subject, obj):
    s = norm_key(subject)
    o = norm_key(obj)
    if s.startswith(('die ursprüngliche domain','die urspruengliche domain')) and token_count(obj) <= 3:
        return True, 'has_original_domain', 'original_domain_property'
    if any(h in s for h in ('codename','der name','ihr codename')) and 1 <= token_count(obj) <= 8:
        return True, 'has_name', 'name_property'
    if any(h in s for h in ('farbe','hintergrundfarbe','color')) and token_count(obj) <= 3:
        return True, 'has_color', 'color_property'
    return False, '', ''


def definition_score(subject, obj):
    s = norm_key(subject)
    o = norm_key(obj)
    score = 0.0
    if any(h in s for h in TECH_SUBJECT_HINTS):
        score += 0.35
    if any(h in o for h in ENTITY_OBJECT_HINTS):
        score += 0.35
    tc_o = token_count(obj)
    if 2 <= tc_o <= 10:
        score += 0.18
    if norm_text(subject)[:1].isupper() and token_count(subject) <= 6:
        score += 0.12
    return min(1.0, score)


class DefinitionCandidateGuard:
    VERSION = 'phase3d6l2_definition_candidate_guard'

    def __init__(self, memory):
        self.memory = memory
        self.ensure_schema()
        self.state = self.load_state()

    def ensure_schema(self):
        with self.memory.lock:
            db = self.memory.db
            db.execute("CREATE TABLE IF NOT EXISTS definition_guard_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at INTEGER)")
            db.execute("""
                CREATE TABLE IF NOT EXISTS definition_guard_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    subject TEXT,
                    relation TEXT,
                    object TEXT,
                    old_status TEXT,
                    new_status TEXT,
                    old_candidate_type TEXT,
                    new_candidate_type TEXT,
                    reason TEXT,
                    score REAL,
                    created_at INTEGER
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_definition_guard_events_reason ON definition_guard_events(reason, created_at)")
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_relations'").fetchone():
                cols = {r['name'] for r in db.execute('PRAGMA table_info(candidate_relations)').fetchall()}
                additions = {
                    'definition_guard_reason': 'TEXT',
                    'definition_guard_score': 'REAL DEFAULT 0',
                }
                for col, ddl in additions.items():
                    if col not in cols:
                        db.execute(f'ALTER TABLE candidate_relations ADD COLUMN {col} {ddl}')
            db.commit()

    def load_state(self):
        row = self.memory.db.execute("SELECT value_json FROM definition_guard_state WHERE key='state'").fetchone()
        if row:
            try:
                state = json.loads(row['value_json'])
                if isinstance(state, dict):
                    state.setdefault('version', self.VERSION)
                    state.setdefault('total_checked', 0)
                    state.setdefault('total_guarded', 0)
                    state.setdefault('total_retyped', 0)
                    state.setdefault('min_definition_score', 0.62)
                    return state
            except Exception:
                pass
        state = {'version': self.VERSION, 'total_checked': 0, 'total_guarded': 0, 'total_retyped': 0, 'min_definition_score': 0.62, 'last_run_at': 0}
        self.save_state(state)
        return state

    def save_state(self, state=None):
        state = state or self.state
        with self.memory.lock:
            self.memory.db.execute("INSERT OR REPLACE INTO definition_guard_state(key,value_json,updated_at) VALUES(?,?,?)", ('state', json.dumps(state, ensure_ascii=False), int(time.time())))
            self.memory.db.commit()

    def classify_definition_candidate(self, subject, relation, obj, status='definition_candidate', candidate_type=''):
        prop, new_rel, prop_type = should_be_property(subject, obj)
        if prop:
            return {
                'action': 'retype',
                'new_status': 'property_candidate',
                'new_candidate_type': prop_type,
                'new_relation': new_rel,
                'reason': 'definition_guard_retype_property',
                'score': 0.80,
            }
        bad_s, reason_s = subject_bad_for_definition(subject)
        if bad_s:
            return {
                'action': 'reject',
                'new_status': 'rejected',
                'new_candidate_type': 'definition_guard_rejected',
                'new_relation': relation,
                'reason': 'definition_guard_' + reason_s,
                'score': 0.0,
            }
        bad_o, reason_o = object_bad_for_definition(obj)
        if bad_o:
            return {
                'action': 'reject',
                'new_status': 'rejected',
                'new_candidate_type': 'definition_guard_rejected',
                'new_relation': relation,
                'reason': 'definition_guard_' + reason_o,
                'score': 0.0,
            }
        score = definition_score(subject, obj)
        if score < float(self.state.get('min_definition_score', 0.62)):
            return {
                'action': 'downgrade',
                'new_status': 'needs_relation_repair',
                'new_candidate_type': 'definition_needs_review',
                'new_relation': relation,
                'reason': 'definition_guard_score_low',
                'score': score,
            }
        return {
            'action': 'keep',
            'new_status': status,
            'new_candidate_type': candidate_type or 'definition_candidate_guarded',
            'new_relation': relation,
            'reason': 'definition_guard_keep',
            'score': score,
        }

    def guard_once(self, batch_size=350):
        self.ensure_schema()
        if not self.memory.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_relations'").fetchone():
            return {'status': 'definition_candidate_guard_phase3d6l2', 'checked': 0, 'changed': 0, 'reason': 'no_candidate_relations'}
        rows = self.memory.rows(
            """
            SELECT id, subject, relation, object, status, COALESCE(candidate_type,'') AS candidate_type,
                   COALESCE(repair_reason,'') AS repair_reason
            FROM candidate_relations
            WHERE status='definition_candidate'
            ORDER BY id ASC
            LIMIT ?
            """,
            (int(batch_size),),
        )
        now = int(time.time())
        counts = Counter()
        samples = []
        for row in rows:
            counts['checked'] += 1
            decision = self.classify_definition_candidate(row['subject'], row['relation'], row['object'], row['status'], row['candidate_type'])
            action = decision['action']
            if action == 'keep':
                with self.memory.lock:
                    self.memory.db.execute(
                        "UPDATE candidate_relations SET candidate_type=?, definition_guard_reason=?, definition_guard_score=?, updated_at=? WHERE id=?",
                        (decision['new_candidate_type'], decision['reason'], float(decision['score']), now, row['id']),
                    )
                    self.memory.db.commit()
                counts['kept'] += 1
                continue
            with self.memory.lock:
                self.memory.db.execute(
                    """
                    UPDATE candidate_relations
                    SET status=?, candidate_type=?, relation=?, definition_guard_reason=?, definition_guard_score=?, updated_at=?
                    WHERE id=?
                    """,
                    (decision['new_status'], decision['new_candidate_type'], decision['new_relation'], decision['reason'], float(decision['score']), now, row['id']),
                )
                self.memory.db.execute(
                    """INSERT INTO definition_guard_events(candidate_id,subject,relation,object,old_status,new_status,old_candidate_type,new_candidate_type,reason,score,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (row['id'], row['subject'], row['relation'], row['object'], row['status'], decision['new_status'], row['candidate_type'], decision['new_candidate_type'], decision['reason'], float(decision['score']), now),
                )
                self.memory.db.commit()
            counts['changed'] += 1
            counts[action] += 1
            counts[decision['reason']] += 1
            if action == 'retype':
                self.state['total_retyped'] = int(self.state.get('total_retyped', 0)) + 1
            else:
                self.state['total_guarded'] = int(self.state.get('total_guarded', 0)) + 1
            if len(samples) < 12:
                samples.append({
                    'id': row['id'],
                    'from': [row['subject'], row['relation'], row['object'], row['status'], row['candidate_type']],
                    'to': [row['subject'], decision['new_relation'], row['object'], decision['new_status'], decision['new_candidate_type']],
                    'reason': decision['reason'],
                    'score': round(float(decision['score']), 3),
                })
        self.state['total_checked'] = int(self.state.get('total_checked', 0)) + counts['checked']
        self.state['last_run_at'] = now
        self.save_state()
        return {
            'status': 'definition_candidate_guard_phase3d6l2',
            'checked': counts['checked'],
            'changed': counts['changed'],
            'kept': counts['kept'],
            'counts': {k:v for k,v in counts.items() if k not in ('checked','changed','kept')},
            'samples': samples,
            'state': dict(self.state),
        }


def apply_patch(CorpusReader):
    if getattr(CorpusReader, '_phase3d6l2_definition_guard_patched', False):
        return
    original = CorpusReader.read_once
    def read_once_with_definition_guard(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            guard = getattr(self, '_phase3d6l2_definition_guard', None)
            if guard is None:
                guard = DefinitionCandidateGuard(self.memory)
                self._phase3d6l2_definition_guard = guard
            guard_result = guard.guard_once(batch_size=350)
            if isinstance(result, dict):
                result['definition_candidate_guard'] = guard_result
                result['status'] = 'adaptive_alignment_corpus_reader_phase3d6l2'
        except Exception as exc:
            if isinstance(result, dict):
                result['definition_candidate_guard'] = {'status': 'definition_candidate_guard_error_phase3d6l2', 'error': str(exc)}
        return result
    CorpusReader.read_once = read_once_with_definition_guard
    CorpusReader._phase3d6l2_definition_guard_patched = True
