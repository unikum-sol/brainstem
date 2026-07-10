from __future__ import annotations
import json
import re
import time
from collections import Counter

BAD_SUBJECT_EXACT = {
    'neu', 'ursprünglich', 'urspruenglich', 'heute', 'seitdem', 'mittlerweile', 'oft', 'damit', 'zudem',
    'bekannt', 'anfang', 'ende', 'mitte', 'zu beginn', 'die seite', 'der text', 'das modell', 'die version',
    'die datei', 'die verwendung', 'eine besonderheit', 'ein weiteres merkmal', 'zuletzt', 'außerdem', 'ausserdem',
    'nachfolger', 'ausschlaggebend', 'zu ihnen', 'häufig', 'haeufig', 'zuvor', 'trivia'
}
BAD_SUBJECT_PREFIXES = (
    'seit ', 'seitdem', 'anfang ', 'ende ', 'mitte ', 'im jahr ', 'am ', 'ab ', 'bis ', 'zu beginn',
    'die empfohlene ', 'ein wohnsitz ', 'eine niederlassung ', 'zeichen aus ', 'eigenschaften ',
    'das beliebte ', 'forschung ', 'funktionstabelle ', 'die dazu benötigte zeit', 'die dazu benoetigte zeit',
    'die endung lehnt ', 'die für ', 'die fuer ', 'die ebenfalls ', 'die bestimmten ', 'die folgenden ',
    'folgende ', 'weitere ', 'einer der ', 'eines der ', 'eine der ', 'die erste offizielle version ',
    'die ursprüngliche ', 'die urspruengliche ', 'die auf ', 'das internet-protokoll', 'aufgrund ',
    'ohne einen ', 'generische begriffe ', 'neben der ', 'desto ', 'die vergabekriterien'
)
GENERIC_SUBJECT_PREFIXES = (
    'die seite', 'der text', 'das modell', 'die version', 'die datei', 'die verwendung',
    'eine besonderheit', 'ein weiteres', 'ein zentrales', 'eine ungelöste', 'eine ungeloeste',
    'eine bedeutende weiterentwicklung', 'ein weiteres nennenswertes merkmal', 'die dateiformatkompatibilität',
    'die dateiformatkompatibilitaet', 'das beliebte', 'die erste offizielle version', 'besonderheit',
    'der titelinterpret', 'der einsatz', 'eine freie implementation', 'die ursprüngliche ausführung',
    'die urspruengliche ausfuehrung'
)
BAD_ISA_OBJECT_FRAGMENTS = (
    'nicht erforderlich', 'nicht möglich', 'nicht moeglich', 'nicht notwendig', 'nicht zulässig', 'nicht zulaessig',
    'nicht mehr erforderlich', 'auch möglich', 'auch moeglich', 'dabei ', 'damit ', 'deshalb ', 'und dass',
    'und heute', 'sie auf den', 'zur aberkennung', 'nicht unumstritten', 'jetzt frei verfügbar',
    'jetzt frei verfuegbar', 'noch kein weg bekannt', 'zeit nicht möglich', 'zeit nicht moeglich',
    'nicht öffentlich bekannt', 'nicht oeffentlich bekannt', 'allerdings nicht gestattet', 'noch nicht',
    'eingeschränkt geeignet', 'eingeschraenkt geeignet', 'nicht zugelassen', 'nicht gestattet'
)
BAD_OBJECT_EXACT = {'der', 'die', 'das', 'ein', 'eine', 'einer', 'eines', 'poker', 'sex', 'linux', 'version 4', 'nummer 1'}
BAD_OBJECT_PREFIXES = (
    'abkömmling des', 'abkoemmling des', 'teil der', 'in ttl-logik', 'dabei ', 'damit ', 'deshalb ',
    'und ', 'oder ', 'also ', 'zunächst ', 'zunaechst ', 'seit ', 'bei ', 'zur ', 'vom ', 'von ', 'für ', 'fuer ',
    'e ', 's ', 'ser ', '– verkaufen', '- verkaufen', 'dyMO'.lower(), 'bezeichnung für ein video- dateiformat für mobile endgeräte wie mobiltelefone der 3'.lower()
)
BAD_OBJECT_SUFFIXES = (
    ' des', ' der', ' die', ' das', ' von', ' für', ' fuer', ' mit', ' bei', ' zu', ' als', ' und', ' oder',
    '(', '[', '{', '„', '"', ':'
)
TEMPORAL_RE = re.compile(r'^(seit\s+)?(anfang|mitte|ende|april|august|oktober|november|dezember|januar|februar|märz|maerz|mai|juni|juli|september)\s+\d{4}\b|^\d{1,2}\.\s*\w+\s+\d{4}\b|^\d{4}$', re.I)
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
UPPER_TOKEN_RE = re.compile(r'^[A-ZÄÖÜ0-9][A-Za-zÄÖÜäöüß0-9+.#-]{1,24}$')


def norm_text(value):
    return ' '.join(str(value or '').replace('_', ' ').split()).strip()


def norm_key(value):
    return norm_text(value).lower()[:180]


def token_count(text):
    return len(re.findall(r'[A-Za-zÄÖÜäöüß0-9]+', text or ''))


def has_unbalanced_brackets(text):
    return (text.count('(') != text.count(')')) or (text.count('[') != text.count(']')) or (text.count('{') != text.count('}'))


class AdaptiveQuality:
    """Adaptive semantic candidate gate.

    Phase 3d6i extends 3d6h with a semantic gate:
    - direct facts/relations are still disabled elsewhere,
    - no promotion is performed,
    - repeated bad forms become learned_quality_blocks,
    - semantic score controls accepted candidate admission.
    """
    def __init__(self, memory):
        self.memory = memory
        self.ensure_schema()
        self.state = self.load_state()

    def ensure_schema(self):
        with self.memory.lock:
            db = self.memory.db
            db.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_quality_state(
                    key TEXT PRIMARY KEY,
                    value_json TEXT,
                    updated_at INTEGER
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_quality_stats(
                    kind TEXT,
                    value TEXT,
                    accepted_count INTEGER DEFAULT 0,
                    rejected_count INTEGER DEFAULT 0,
                    last_reason TEXT,
                    updated_at INTEGER,
                    PRIMARY KEY(kind, value)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS learned_quality_blocks(
                    kind TEXT,
                    value TEXT,
                    reason TEXT,
                    count INTEGER DEFAULT 0,
                    weight REAL DEFAULT 0,
                    last_seen INTEGER,
                    PRIMARY KEY(kind, value)
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_learned_quality_blocks_weight ON learned_quality_blocks(kind, weight DESC, count DESC)")
            db.commit()

    def load_state(self):
        row = self.memory.db.execute("SELECT value_json FROM adaptive_quality_state WHERE key='state'").fetchone()
        if row:
            try:
                state = json.loads(row['value_json'])
                if isinstance(state, dict):
                    state['version'] = 'phase3d6i'
                    state.setdefault('semantic_min_score', 0.42)
                    state.setdefault('sleep_interval_chunks', 250)
                    state.setdefault('bad_pattern_reject_weight', 0.62)
                    state.setdefault('adaptive_strictness', 0.58)
                    return state
            except Exception:
                pass
        state = {
            'version': 'phase3d6i',
            'min_candidate_confidence': 0.0,
            'semantic_min_score': 0.42,
            'bad_pattern_reject_weight': 0.62,
            'sleep_interval_chunks': 250,
            'total_seen': 0,
            'total_accepted': 0,
            'total_rejected': 0,
            'adaptive_strictness': 0.58,
            'last_sleep_at_seen': 0,
        }
        self.save_state(state)
        return state

    def save_state(self, state=None):
        state = state or self.state
        with self.memory.lock:
            self.memory.db.execute(
                "INSERT OR REPLACE INTO adaptive_quality_state(key,value_json,updated_at) VALUES(?,?,?)",
                ('state', json.dumps(state, ensure_ascii=False), int(time.time())),
            )
            self.memory.db.commit()

    def _record_stat(self, kind, value, accepted, reason=''):
        value = norm_key(value)
        if not value:
            return
        now = int(time.time())
        with self.memory.lock:
            row = self.memory.db.execute("SELECT * FROM adaptive_quality_stats WHERE kind=? AND value=?", (kind, value)).fetchone()
            if row:
                ac = int(row['accepted_count'] or 0) + (1 if accepted else 0)
                rc = int(row['rejected_count'] or 0) + (0 if accepted else 1)
                self.memory.db.execute(
                    "UPDATE adaptive_quality_stats SET accepted_count=?, rejected_count=?, last_reason=?, updated_at=? WHERE kind=? AND value=?",
                    (ac, rc, reason, now, kind, value),
                )
            else:
                self.memory.db.execute(
                    "INSERT INTO adaptive_quality_stats(kind,value,accepted_count,rejected_count,last_reason,updated_at) VALUES(?,?,?,?,?,?)",
                    (kind, value, 1 if accepted else 0, 0 if accepted else 1, reason, now),
                )
            self.memory.db.commit()

    def _record_block(self, kind, value, reason, base_weight=0.45):
        value = norm_key(value)
        if not value:
            return
        now = int(time.time())
        with self.memory.lock:
            row = self.memory.db.execute("SELECT * FROM learned_quality_blocks WHERE kind=? AND value=?", (kind, value)).fetchone()
            if row:
                count = int(row['count'] or 0) + 1
                weight = min(1.0, max(float(row['weight'] or 0.0), base_weight) + 0.08)
                self.memory.db.execute(
                    "UPDATE learned_quality_blocks SET reason=?, count=?, weight=?, last_seen=? WHERE kind=? AND value=?",
                    (reason, count, weight, now, kind, value),
                )
            else:
                self.memory.db.execute(
                    "INSERT INTO learned_quality_blocks(kind,value,reason,count,weight,last_seen) VALUES(?,?,?,?,?,?)",
                    (kind, value, reason, 1, base_weight, now),
                )
            self.memory.db.commit()

    def _learned_block_reason(self, kind, value):
        value = norm_key(value)
        if not value:
            return None
        row = self.memory.db.execute(
            "SELECT reason, weight, count FROM learned_quality_blocks WHERE kind=? AND value=?",
            (kind, value),
        ).fetchone()
        if row and float(row['weight'] or 0.0) >= float(self.state.get('bad_pattern_reject_weight', 0.62)):
            return row['reason'] or 'learned_quality_block'
        return None

    def semantic_score(self, subject, relation, obj, scores=None):
        scores = scores or {}
        subject_text = norm_text(subject)
        object_text = norm_text(obj)
        relation_text = norm_key(relation)
        s = subject_text.lower()
        o = object_text.lower()
        score = 0.55
        notes = []

        # subject shape
        st = token_count(subject_text)
        ot = token_count(object_text)
        if 1 <= st <= 6:
            score += 0.12
        elif st > 10:
            score -= 0.30; notes.append('subject_too_long')
        if subject_text and subject_text[0].islower() and not UPPER_TOKEN_RE.match(subject_text):
            score -= 0.12; notes.append('lowercase_subject_fragment')
        if ' und ' in s or ' oder ' in s:
            score -= 0.20; notes.append('coordinated_subject')
        if any(s.startswith(prefix) for prefix in BAD_SUBJECT_PREFIXES + GENERIC_SUBJECT_PREFIXES):
            score -= 0.35; notes.append('bad_subject_shape')

        # object shape
        if 1 <= ot <= 9:
            score += 0.08
        elif ot > 14:
            score -= 0.28; notes.append('object_too_long')
        if has_unbalanced_brackets(object_text):
            score -= 0.25; notes.append('unbalanced_brackets')
        if o in BAD_OBJECT_EXACT or any(o.startswith(prefix) for prefix in BAD_OBJECT_PREFIXES):
            score -= 0.35; notes.append('bad_object_shape')
        if any(o.endswith(suffix) for suffix in BAD_OBJECT_SUFFIXES):
            score -= 0.22; notes.append('object_bad_suffix')
        if any(fragment in o for fragment in BAD_ISA_OBJECT_FRAGMENTS):
            score -= 0.40; notes.append('bad_is_a_object_phrase')

        # relation-specific plausibility
        if relation_text in ('is_a', 'definition'):
            if ot < 2:
                score -= 0.35; notes.append('object_too_short')
            if o.startswith(('nicht ', 'auch ', 'dabei ', 'damit ', 'und ', 'oder ', 'also ', 'deshalb ', 'seit ')):
                score -= 0.35; notes.append('object_clause_start')
            if subject_text.lower().startswith(('die ', 'der ', 'das ', 'ein ', 'eine ')) and st > 6:
                score -= 0.18; notes.append('long_article_subject')

        score += min(0.15, float(scores.get('alignment_score', 0.0) or 0.0) * 0.08)
        score -= min(0.25, float(scores.get('fragment_score', 0.0) or 0.0) * 0.20)
        score -= min(0.35, float(scores.get('license_score', 0.0) or 0.0) * 0.35)
        return max(0.0, min(1.0, score)), notes

    def classify_candidate(self, subject, relation, obj, confidence=0.0, scores=None):
        scores = scores or {}
        subject_text = norm_text(subject)
        object_text = norm_text(obj)
        relation_text = norm_key(relation)
        s = subject_text.lower()
        o = object_text.lower()

        if not subject_text or not object_text or not relation_text:
            return False, 'empty_candidate'

        learned_subject = self._learned_block_reason('subject', s)
        if learned_subject:
            return False, 'learned_bad_subject'
        learned_object = self._learned_block_reason('object', o[:120])
        if learned_object:
            return False, 'learned_bad_object'

        if s in BAD_SUBJECT_EXACT or any(s.startswith(prefix) for prefix in BAD_SUBJECT_PREFIXES):
            return False, 'temporal_or_adverbial_subject'
        if TEMPORAL_RE.search(s) or (YEAR_RE.search(s) and len(s.split()) <= 5):
            return False, 'temporal_subject'
        if any(s.startswith(prefix) for prefix in GENERIC_SUBJECT_PREFIXES):
            return False, 'generic_subject'
        if len(subject_text) > 70 or subject_text.count(' und ') >= 1 or subject_text.count(',') >= 2:
            return False, 'subject_sentence_fragment'
        if subject_text and subject_text[0].islower() and token_count(subject_text) > 3:
            return False, 'lowercase_subject_fragment'

        if relation_text in ('is_a', 'definition'):
            if o in BAD_OBJECT_EXACT:
                return False, 'bad_is_a_object'
            if any(fragment in o for fragment in BAD_ISA_OBJECT_FRAGMENTS):
                return False, 'bad_is_a_object'
            if any(o.startswith(prefix) for prefix in BAD_OBJECT_PREFIXES):
                return False, 'bad_is_a_object'
            if any(o.endswith(suffix) for suffix in BAD_OBJECT_SUFFIXES):
                return False, 'object_incomplete_fragment'
            if len(object_text) < 4 or token_count(object_text) < 2:
                return False, 'too_short_object'
            if len(object_text) > 120 or token_count(object_text) > 14:
                return False, 'object_sentence_like_or_too_long'
            if has_unbalanced_brackets(object_text):
                return False, 'object_incomplete_fragment'

        if float(scores.get('license_score', 0.0) or 0.0) >= 0.8:
            return False, 'license_or_footer'
        if float(scores.get('fragment_score', 0.0) or 0.0) >= 0.85:
            return False, 'high_fragment_score'

        score, notes = self.semantic_score(subject_text, relation_text, object_text, scores)
        threshold = float(self.state.get('semantic_min_score', 0.42))
        strictness = float(self.state.get('adaptive_strictness', 0.58))
        threshold = min(0.72, max(0.38, threshold + (strictness - 0.55) * 0.25))
        if score < threshold:
            reason = 'semantic_score_low'
            if notes:
                reason = 'semantic_' + notes[0]
            return False, reason

        return True, 'accepted'

    def observe(self, subject, relation, obj, accepted, reason):
        self.state['total_seen'] = int(self.state.get('total_seen', 0)) + 1
        if accepted:
            self.state['total_accepted'] = int(self.state.get('total_accepted', 0)) + 1
        else:
            self.state['total_rejected'] = int(self.state.get('total_rejected', 0)) + 1
        self._record_stat('subject', subject, accepted, reason)
        self._record_stat('object', obj, accepted, reason)
        self._record_stat('relation', relation, accepted, reason)
        if not accepted:
            if 'subject' in reason or reason in ('temporal_or_adverbial_subject', 'temporal_subject', 'generic_subject', 'lowercase_subject_fragment'):
                self._record_block('subject', subject, reason, 0.48)
            if 'object' in reason or 'is_a_object' in reason:
                self._record_block('object', obj[:120], reason, 0.48)
        self.save_state()

    def sleep_consolidate(self, min_rejections=3):
        total_seen = int(self.state.get('total_seen', 0))
        last_sleep = int(self.state.get('last_sleep_at_seen', 0))
        interval = int(self.state.get('sleep_interval_chunks', 250))
        if total_seen - last_sleep < interval:
            return {'status': 'skip', 'reason': 'interval_not_reached', 'total_seen': total_seen}
        learned = 0
        now = int(time.time())
        rows = self.memory.rows(
            """
            SELECT kind, value, accepted_count, rejected_count, last_reason
            FROM adaptive_quality_stats
            WHERE rejected_count >= ? AND rejected_count > accepted_count * 2
            ORDER BY rejected_count DESC
            LIMIT 300
            """,
            (int(min_rejections),),
        )
        for row in rows:
            kind = row['kind']
            if kind not in ('subject', 'object'):
                continue
            value = row['value']
            reason = row['last_reason'] or 'learned_high_failure_rate'
            count = int(row['rejected_count'] or 0)
            weight = min(1.0, 0.48 + count / 18.0)
            with self.memory.lock:
                self.memory.db.execute(
                    """INSERT OR REPLACE INTO learned_quality_blocks(kind,value,reason,count,weight,last_seen)
                       VALUES(?,?,?,?,?,?)""",
                    (kind, value, reason, count, weight, now),
                )
                self.memory.db.commit()
            learned += 1
        total_rej = max(0, int(self.state.get('total_rejected', 0)))
        total_acc = max(0, int(self.state.get('total_accepted', 0)))
        ratio = total_rej / max(1, total_acc + total_rej)
        strictness = float(self.state.get('adaptive_strictness', 0.58))
        if ratio > 0.70:
            strictness = min(0.92, strictness + 0.025)
        elif ratio < 0.40:
            strictness = max(0.38, strictness - 0.02)
        self.state['adaptive_strictness'] = strictness
        self.state['semantic_min_score'] = min(0.68, max(0.42, 0.42 + (strictness - 0.55) * 0.30))
        self.state['bad_pattern_reject_weight'] = max(0.45, min(0.75, 0.9 - strictness * 0.35))
        self.state['last_sleep_at_seen'] = total_seen
        self.save_state()
        return {'status': 'consolidated', 'learned_blocks': learned, 'reject_ratio': round(ratio, 3), 'adaptive_strictness': round(strictness, 3), 'semantic_min_score': round(float(self.state['semantic_min_score']), 3)}

    def summary(self):
        row = self.memory.db.execute("SELECT COUNT(*) AS c FROM learned_quality_blocks").fetchone()
        return {'state': dict(self.state), 'learned_quality_blocks': int(row['c'] if row else 0)}
