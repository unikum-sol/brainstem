from __future__ import annotations
import json
import re
import time
from collections import Counter

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
YEAR_RE = re.compile(r'\b(18|19|20)\d{2}\b')

SAFE_CURRENT_STATUSES = {'candidate', 'needs_relation_repair'}
TECH_NOMINAL_HINTS = {
    'protokoll','schnittstelle','framework','software','programm','betriebssystem','prozessor','mikroprozessor',
    'dateiformat','format','standard','algorithmus','architektur','netzwerk','datenbank','programmiersprache','sprache',
    'bibliothek','system','domain','server','client','unternehmen','projekt','diagramm','gerät','geraet','tool','paket',
    'modell','serie','familie','anwendung','spezifikation','verfahren','methode','bus','route-over-protokoll',
    'funk-rechnernetz','eingabegerät','eingabegeraet','implementierung','markenname','dateiformat','grafikkarten',
    'mikroarchitektur','programmierschnittstelle','komprimierung','tablet-computer','bürocomputer','buero computer','bürocomputer'
}
PROPERTY_SUBJECT_HINTS = {
    'codename':'has_codename', 'name':'has_name', 'version':'has_version', 'dateiendung':'has_file_extension',
    'farbe':'has_color', 'hintergrundfarbe':'has_color', 'domain':'has_domain', 'ursprüngliche domain':'has_original_domain',
    'urspruengliche domain':'has_original_domain', 'sockel':'uses_socket', 'zielgruppe':'has_target_group',
    'auflage':'has_quantity', 'marktstart':'has_launch_date', 'einführung':'has_launch_date', 'einfuehrung':'has_launch_date'
}
RELATION_SUBJECT_HINTS = {
    'sitz':'located_in', 'zentrale':'located_in', 'hauptsitz':'located_in', 'standort':'located_in',
    'nachfolger':'successor_of', 'vorgänger':'predecessor_of', 'vorgaenger':'predecessor_of',
    'bestandteil':'part_of', 'teil':'part_of'
}
BAD_SUBJECT_PREFIXES = (
    'wie ', 'was ', 'warum ', 'entwicklung ', 'technik ', 'technische einzelheiten ', 'leistung ', 'vergleich ',
    'beispiel es ', 'anwendungsbeispiel ', 'foundation der zweck ', 'ioT-geräte auch'.lower(),
    'geschichte ', 'serie ', 'logo ', 'de ', 'com ', 'die letzten ', 'die letzte ', 'andernfalls', 'dafür', 'dafuer',
    'gleichzeitig', 'mittlerweile', 'derzeit', 'aktuell', 'allerdings', 'neu', 'daher', 'damit'
)
BAD_OBJECT_PREFIXES = (
    'ab ', 'am ', 'bis ', 'seit ', 'erst ', 'nun ', 'dabei ', 'damit ', 'daher ', 'jedoch ', 'aber ',
    'e ', 's ', 'se ', 'ser ', 'nicht ', 'vor allem ', 'speziell ', 'laut ', 'wie ', 'um eine ',
)
BAD_OBJECT_CONTAINS = (
    ' nicht ', 'nicht ', ' nicht', 'möglich', 'moeglich', 'kompatibel', 'verbreitet', 'vorgesehen', 'ausgelegt',
    'standardisiert', 'bekannt', 'besorgt', 'handle sich', 'in arbeit', 'zugänglich', 'zugaenglich',
    'abwärtskompatibel', 'abwaertskompatibel', 'erweitert', 'geschützt', 'geschuetzt', 'jumpern', 'billig-'
)
GENERIC_SUBJECT_EXACT = {'kritiker', 'andernfalls', 'dafür', 'dafuer', 'gleichzeitig', 'mittlerweile', 'derzeit', 'aktuell'}


def norm_text(value):
    return ' '.join(str(value or '').replace('_', ' ').split()).strip()


def norm_key(value):
    return norm_text(value).lower()[:320]


def relation_key(value):
    return norm_text(value).lower().replace(' ', '_')[:80]


def tokens(value):
    return [t.lower() for t in WORD_RE.findall(norm_text(value))]


def token_count(value):
    return len(tokens(value))


def has_nominal_hint(value):
    v = norm_key(value)
    return any(h in v for h in TECH_NOMINAL_HINTS)


def bad_subject(subject):
    s = norm_key(subject)
    if not s:
        return 'refine_empty_subject'
    if s in GENERIC_SUBJECT_EXACT:
        return 'refine_generic_subject'
    if norm_text(subject)[:1].islower() and token_count(subject) > 1:
        return 'refine_lowercase_subject_fragment'
    if any(s.startswith(p) for p in BAD_SUBJECT_PREFIXES):
        return 'refine_heading_or_frame_subject'
    if token_count(subject) > 10:
        return 'refine_subject_too_long'
    if (' und ' in s or ' oder ' in s) and token_count(subject) > 5:
        return 'refine_coordinated_subject'
    return ''


def bad_object_for_is_a(obj):
    o = norm_key(obj)
    if not o:
        return 'refine_empty_object'
    if o in {'der','die','das','ein','eine','einer','eines','mit','bei','zu','von','für','fuer','als','und','oder'}:
        return 'refine_bad_object_exact'
    if any(o.startswith(p) for p in BAD_OBJECT_PREFIXES):
        return 'refine_predicate_object_prefix'
    if any(x in o for x in BAD_OBJECT_CONTAINS):
        return 'refine_predicate_object_phrase'
    if any(o.endswith(suf) for suf in (' des',' der',' die',' das',' von',' für',' fuer',' mit',' bei',' zu',' als',' und',' oder','(', '[', '{', ':')):
        return 'refine_object_incomplete'
    if token_count(obj) < 2 and not has_nominal_hint(obj):
        return 'refine_object_too_short'
    return ''


def property_relation_for(subject, obj):
    s = norm_key(subject)
    o = norm_key(obj)
    if (s.startswith(('der codename lautet ', 'codename lautet ')) or 'codename' in s):
        # Only type as codename when the object looks like a compact name/code,
        # not like a predicative clause (e.g. 'speziell für Server ... ausgelegt').
        if token_count(obj) <= 8 and not any(x in o for x in ('speziell ', 'ausgelegt', 'vorgesehen', 'nicht ', 'möglich', 'moeglich', 'für server', 'fuer server')):
            return 'has_codename', 'codename_property'
    if s.startswith(('der name ', 'ihr name ', 'der name lautet ')):
        return 'has_name', 'name_property'
    if 'ursprüngliche domain' in s or 'urspruengliche domain' in s:
        return 'has_original_domain', 'original_domain_property'
    if 'dateiendung' in s and 1 <= token_count(obj) <= 5:
        return 'has_file_extension', 'file_extension_property'
    if 'sockel' in s and 1 <= token_count(obj) <= 8:
        return 'uses_socket', 'socket_property'
    if 'zielgruppe' in s and 1 <= token_count(obj) <= 10:
        return 'has_target_group', 'target_group_property'
    if ('einführung' in s or 'einfuehrung' in s or 'marktstart' in s) and (YEAR_RE.search(o) or token_count(obj) <= 4):
        return 'has_launch_date', 'launch_date_property'
    if 'farbe' in s and token_count(obj) <= 3:
        return 'has_color', 'color_property'
    return '', ''


def relation_for(subject, obj):
    s = norm_key(subject)
    o = norm_key(obj)
    if any(h in s for h in ('sitz','zentrale','hauptsitz','standort')) and 1 <= token_count(obj) <= 7:
        return 'located_in', 'location_relation'
    if 'nachfolger' in s and token_count(obj) <= 8:
        return 'successor_of', 'successor_relation'
    if 'vorgänger' in s or 'vorgaenger' in s:
        if token_count(obj) <= 8:
            return 'predecessor_of', 'predecessor_relation'
    if o.startswith(('teil des ', 'teil der ', 'teil von ', 'bestandteil des ', 'bestandteil der ')):
        return 'part_of', 'part_of_relation'
    return '', ''


def classify_type(subject, relation, obj, status='candidate'):
    r = relation_key(relation)
    if status not in SAFE_CURRENT_STATUSES:
        return None
    subj_bad = bad_subject(subject)
    if subj_bad:
        return {'new_status':'needs_relation_repair','new_relation':relation,'candidate_type':'unsafe_subject_needs_review','reason':subj_bad,'confidence':0.35}

    # Predicate/fragment objects must not be converted into properties just because
    # the subject contains a property word such as 'Codename'.
    # Safe short property values (original domain, socket, extension, color, launch dates)
    # are still allowed by property_relation_for below.
    if r in ('is_a','definition'):
        early_obj_bad = bad_object_for_is_a(obj)
        if early_obj_bad in ('refine_predicate_object_prefix', 'refine_predicate_object_phrase', 'refine_object_incomplete'):
            return {'new_status':'needs_relation_repair','new_relation':relation,'candidate_type':'predicate_or_fragment_needs_review','reason':early_obj_bad,'confidence':0.42}

    rel, ctype = property_relation_for(subject, obj)
    if rel:
        return {'new_status':'property_candidate','new_relation':rel,'candidate_type':ctype,'reason':'refine_property_candidate','confidence':0.78}
    rel, ctype = relation_for(subject, obj)
    if rel:
        return {'new_status':'relation_candidate','new_relation':rel,'candidate_type':ctype,'reason':'refine_relation_candidate','confidence':0.74}

    if r in ('is_a','definition'):
        obj_bad = bad_object_for_is_a(obj)
        if obj_bad:
            return {'new_status':'needs_relation_repair','new_relation':relation,'candidate_type':'predicate_or_fragment_needs_review','reason':obj_bad,'confidence':0.42}
        if has_nominal_hint(obj) and 2 <= token_count(obj) <= 14:
            return {'new_status':'definition_candidate','new_relation':'is_a','candidate_type':'guarded_definition_candidate','reason':'refine_definition_candidate', 'confidence':0.66}
        return {'new_status':'needs_relation_repair','new_relation':relation,'candidate_type':'ambiguous_candidate_needs_review','reason':'refine_ambiguous_is_a', 'confidence':0.45}
    return {'new_status':'relation_candidate','new_relation':relation,'candidate_type':'typed_relation_candidate','reason':'refine_non_is_a_relation_candidate','confidence':0.60}


class CandidateTypeRefiner:
    VERSION = 'phase3d8_candidate_type_refinement_pack'

    def __init__(self, memory):
        self.memory = memory
        self.ensure_schema()
        self.state = self.load_state()

    def ensure_schema(self):
        with self.memory.lock:
            db = self.memory.db
            db.execute("CREATE TABLE IF NOT EXISTS candidate_type_refinement_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at INTEGER)")
            db.execute("""
                CREATE TABLE IF NOT EXISTS candidate_type_refinement_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id INTEGER,
                    subject TEXT,
                    old_relation TEXT,
                    object TEXT,
                    new_relation TEXT,
                    old_status TEXT,
                    new_status TEXT,
                    candidate_type TEXT,
                    reason TEXT,
                    confidence REAL,
                    created_at INTEGER
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_candidate_type_refinement_events_reason ON candidate_type_refinement_events(reason, created_at)")
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_relations'").fetchone():
                cols = {r['name'] for r in db.execute('PRAGMA table_info(candidate_relations)').fetchall()}
                additions = {
                    'type_refinement_reason':'TEXT',
                    'type_refinement_confidence':'REAL DEFAULT 0',
                    'type_refined_at':'INTEGER DEFAULT 0',
                    'candidate_type':'TEXT',
                    'repaired_relation':'TEXT',
                    'original_relation':'TEXT',
                    'original_object':'TEXT',
                }
                for col, ddl in additions.items():
                    if col not in cols:
                        db.execute(f'ALTER TABLE candidate_relations ADD COLUMN {col} {ddl}')
            db.commit()

    def load_state(self):
        row = self.memory.db.execute("SELECT value_json FROM candidate_type_refinement_state WHERE key='state'").fetchone()
        if row:
            try:
                state = json.loads(row['value_json'])
                if isinstance(state, dict):
                    state.setdefault('version', self.VERSION)
                    state.setdefault('total_checked', 0)
                    state.setdefault('total_refined', 0)
                    state.setdefault('batch_size', 500)
                    return state
            except Exception:
                pass
        state = {'version': self.VERSION, 'total_checked': 0, 'total_refined': 0, 'batch_size': 500, 'last_run_at': 0}
        self.save_state(state)
        return state

    def save_state(self, state=None):
        state = state or self.state
        with self.memory.lock:
            self.memory.db.execute("INSERT OR REPLACE INTO candidate_type_refinement_state(key,value_json,updated_at) VALUES(?,?,?)", ('state', json.dumps(state, ensure_ascii=False), int(time.time())))
            self.memory.db.commit()

    def refine_once(self, batch_size=500):
        self.ensure_schema()
        if not self.memory.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_relations'").fetchone():
            return {'status':'candidate_type_refinement_phase3d8','checked':0,'refined':0,'reason':'no_candidate_relations'}
        rows = self.memory.rows(
            """
            SELECT id, subject, relation, object, status, COALESCE(candidate_type,'') AS candidate_type,
                   COALESCE(type_refinement_reason,'') AS type_refinement_reason
            FROM candidate_relations
            WHERE status IN ('candidate','needs_relation_repair')
              AND (candidate_type IS NULL OR candidate_type='' OR type_refinement_reason IS NULL OR type_refinement_reason='')
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
            decision = classify_type(row['subject'], row['relation'], row['object'], row['status'])
            if not decision:
                counts['unchanged'] += 1
                continue
            with self.memory.lock:
                self.memory.db.execute(
                    """
                    UPDATE candidate_relations
                    SET original_relation=COALESCE(original_relation, relation),
                        original_object=COALESCE(original_object, object),
                        relation=?, repaired_relation=?, status=?, candidate_type=?,
                        type_refinement_reason=?, type_refinement_confidence=?, type_refined_at=?, updated_at=?
                    WHERE id=?
                    """,
                    (decision['new_relation'], decision['new_relation'], decision['new_status'], decision['candidate_type'], decision['reason'], float(decision['confidence']), now, now, row['id']),
                )
                self.memory.db.execute(
                    """INSERT INTO candidate_type_refinement_events(candidate_id,subject,old_relation,object,new_relation,old_status,new_status,candidate_type,reason,confidence,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (row['id'], row['subject'], row['relation'], row['object'], decision['new_relation'], row['status'], decision['new_status'], decision['candidate_type'], decision['reason'], float(decision['confidence']), now),
                )
                self.memory.db.commit()
            counts['refined'] += 1
            counts[decision['new_status']] += 1
            counts[decision['reason']] += 1
            if len(samples) < 16:
                samples.append({'id': row['id'], 'from': [row['subject'], row['relation'], row['object'], row['status']], 'to': [row['subject'], decision['new_relation'], row['object'], decision['new_status']], 'candidate_type': decision['candidate_type'], 'reason': decision['reason'], 'confidence': round(float(decision['confidence']), 3)})
        self.state['total_checked'] = int(self.state.get('total_checked', 0)) + counts['checked']
        self.state['total_refined'] = int(self.state.get('total_refined', 0)) + counts['refined']
        self.state['last_run_at'] = now
        self.save_state()
        # Re-run definition guard if available, because this phase may create definition_candidate.
        guard_result = None
        try:
            from ki_system.definition_candidate_guard import DefinitionCandidateGuard
            guard_result = DefinitionCandidateGuard(self.memory).guard_once(batch_size=500)
        except Exception as exc:
            guard_result = {'status':'definition_guard_skip_or_error_phase3d8', 'error': str(exc)}
        return {'status':'candidate_type_refinement_phase3d8','checked':counts['checked'],'refined':counts['refined'],'unchanged':counts['unchanged'],'counts':{k:v for k,v in counts.items() if k not in ('checked','refined','unchanged')},'samples':samples,'definition_guard_after_refinement':guard_result,'state':dict(self.state)}


def install_reader(CorpusReader):
    if getattr(CorpusReader, '_phase3d8_candidate_type_refinement_patched', False):
        return {'status':'already_installed_phase3d8'}
    original = CorpusReader.read_once
    def read_once_with_candidate_type_refinement(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            refiner = getattr(self, '_phase3d8_candidate_type_refiner', None)
            if refiner is None:
                refiner = CandidateTypeRefiner(self.memory)
                self._phase3d8_candidate_type_refiner = refiner
            refined = refiner.refine_once(batch_size=500)
            if isinstance(result, dict):
                result['status'] = 'adaptive_alignment_corpus_reader_phase3d8'
                result['candidate_type_refinement'] = refined
                result['fact_promotion'] = 'disabled'
                result['direct_fact_writes'] = 'disabled'
                result['direct_relation_writes'] = 'disabled'
        except Exception as exc:
            if isinstance(result, dict):
                result['candidate_type_refinement'] = {'status':'candidate_type_refinement_error_phase3d8', 'error': str(exc)}
        return result
    CorpusReader.read_once = read_once_with_candidate_type_refinement
    CorpusReader._phase3d8_candidate_type_refinement_patched = True
    return {'status':'installed_phase3d8'}
