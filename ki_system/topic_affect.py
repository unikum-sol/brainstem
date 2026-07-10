from __future__ import annotations
import time
import re

BAD_WORDS = set('dieser diese dieses diesen diesem deren dessen welche welcher welches welchen welchem jener jene jenes möglicherweise moeglicherweise beobachtet verschiedene verschiedener verschiedenes weiteren weitere weiterer weiteres einer eines einem einen werden wurden wurde haben hatte sowie auch oder aber nicht mehrere google-books best-of webarchive archive-org isbn issn doi pmid jstor commons wikidata wikipedia us-amerikanischen englischsprachigen deutschsprachigen chinesischen französischen franzoesischen sowjetischen russischen astronomischen belgischen historischen amerikanischen japanischen europäischen europaeischen politischen staatlichen sogenannten verschiedenen'.split())
BAD_PATTERNS = [
    re.compile(r'^(?:[a-zäöüß]{1,3})$'),
    re.compile(r'.*(?:books|archive|webarchive|isbn|doi|jstor).*'),
    re.compile(r'^(?:us|uk|eu|de)-[a-zäöüß]+en$'),
]

def normalize_topic(topic: str) -> str:
    return ' '.join((topic or '').strip().lower().replace('_', ' ').split())

def static_bad_topic(topic: str) -> bool:
    t = normalize_topic(topic).strip(' ?!.:,;()[]{}"\'')
    if not t or t in BAD_WORDS or len(t) < 4 or len(t) > 80:
        return True
    if any(p.match(t) for p in BAD_PATTERNS):
        return True
    if t.endswith(('isch', 'ische', 'ischen', 'ischer', 'isches')) and len(t.split()) == 1:
        return True
    return False

class TopicAffect:
    def __init__(self, memory):
        self.memory = memory
        self._ensure()

    def _ensure(self):
        if getattr(self.memory, 'readonly', False):
            return
        with self.memory.lock:
            self.memory.db.execute("CREATE TABLE IF NOT EXISTS topic_affect(topic TEXT PRIMARY KEY, attempts INTEGER DEFAULT 0, productive_count INTEGER DEFAULT 0, new_facts INTEGER DEFAULT 0, already_known INTEGER DEFAULT 0, no_extractable INTEGER DEFAULT 0, no_sources INTEGER DEFAULT 0, errors INTEGER DEFAULT 0, relations_seen INTEGER DEFAULT 0, dopamine_score REAL DEFAULT 0, gaba_score REAL DEFAULT 0, score REAL DEFAULT 0, status TEXT DEFAULT 'new', last_status TEXT, updated_at INTEGER)")
            self.memory.db.execute('CREATE INDEX IF NOT EXISTS idx_topic_affect_score ON topic_affect(score)')
            self.memory.db.execute('CREATE INDEX IF NOT EXISTS idx_topic_affect_status ON topic_affect(status)')
            now_3c2 = int(time.time())
            self.memory.db.execute("UPDATE topic_affect SET score=-0.22, status='exhausted', updated_at=? WHERE status='known_only' AND new_facts=0 AND score>-0.18", (now_3c2,))
            bad_topics = tuple(BAD_WORDS)
            if bad_topics:
                placeholders = ','.join('?' for _ in bad_topics)
                self.memory.db.execute("UPDATE topic_affect SET score=-0.61, status='noise', updated_at=? WHERE topic IN (" + placeholders + ") AND score>-0.61", (now_3c2, *bad_topics))
            self.memory.db.commit()

    def row(self, topic):
        rows = self.memory.rows('SELECT * FROM topic_affect WHERE topic=?', (normalize_topic(topic),))
        return rows[0] if rows else None

    def score_for(self, topic) -> float:
        t = normalize_topic(topic)
        base = -0.90 if static_bad_topic(t) else 0.0
        r = self.row(t)
        return base + (float(r['score'] or 0.0) if r else 0.0)

    def is_blocked(self, topic) -> bool:
        t = normalize_topic(topic)
        if static_bad_topic(t):
            return True
        r = self.row(t)
        if not r:
            return False
        attempts = int(r['attempts'] or 0)
        score = float(r['score'] or 0.0)
        status = r['status'] or ''
        return bool(status in ('noise', 'exhausted', 'blocked') or (status == 'known_only' and attempts >= 2 and score <= -0.18))

    def update(self, topic, status, new_facts=0, no_extractable=0, no_sources=0, errors=0, relations_seen=0, already_known=0):
        if getattr(self.memory, 'readonly', False):
            return None
        t = normalize_topic(topic)
        if not t:
            return None
        nf = int(new_facts or 0)
        no_ext = int(no_extractable or 0)
        no_src = int(no_sources or 0)
        err = int(errors or 0)
        known = int(already_known or (1 if status == 'already_known' else 0))
        rel = int(relations_seen or 0)
        productive = 1 if nf > 0 else 0
        delta = nf * 0.34 + productive * 0.12 + min(rel, 8) * 0.004 - no_ext * 0.16 - no_src * 0.14 - err * 0.30 - known * 0.13
        if status in ('known_only', 'already_known') and nf == 0:
            delta -= 0.08
        if static_bad_topic(t):
            delta -= 0.50
        now = int(time.time())
        with self.memory.lock:
            self.memory.db.execute('INSERT OR IGNORE INTO topic_affect(topic,updated_at) VALUES(?,?)', (t, now))
            row = self.memory.db.execute('SELECT * FROM topic_affect WHERE topic=?', (t,)).fetchone()
            old = float(row['score'] or 0.0)
            attempts_old = int(row['attempts'] or 0)
            score = max(-1.0, min(1.0, old * 0.82 + delta))
            attempts_new = attempts_old + 1
            if nf > 0:
                status_new = 'productive'
            elif static_bad_topic(t):
                status_new = 'noise'
            elif no_ext > 0 and attempts_new >= 1:
                status_new = 'exhausted'
            elif (known > 0 and attempts_new >= 2) or (score <= -0.35 and attempts_new >= 2):
                status_new = 'exhausted'
            elif known > 0:
                status_new = 'known_only'
            else:
                status_new = status
            self.memory.db.execute('UPDATE topic_affect SET attempts=attempts+1, productive_count=productive_count+?, new_facts=new_facts+?, already_known=already_known+?, no_extractable=no_extractable+?, no_sources=no_sources+?, errors=errors+?, relations_seen=relations_seen+?, dopamine_score=?, gaba_score=?, score=?, status=?, last_status=?, updated_at=? WHERE topic=?', (productive, nf, known, no_ext, no_src, err, rel, max(0.0, score), max(0.0, -score), score, status_new, status, now, t))
            self.memory.db.commit()
        return score

    def summary(self, limit=8):
        good = self.memory.rows('SELECT topic,score,new_facts,attempts,status FROM topic_affect WHERE new_facts>0 ORDER BY score DESC,new_facts DESC LIMIT ?', (int(limit),))
        if not good:
            good = self.memory.rows('SELECT topic,score,new_facts,attempts,status FROM topic_affect ORDER BY score DESC,new_facts DESC LIMIT ?', (int(limit),))
        bad = self.memory.rows('SELECT topic,score,no_extractable,attempts,status FROM topic_affect ORDER BY score ASC,no_extractable DESC LIMIT ?', (int(limit),))
        return {'top_productive': [dict(r) for r in good], 'top_blocked': [dict(r) for r in bad]}

# PHASE3C4_ANTI_FALLBACK_LOOP: no_extractable topics exhausted faster

# PHASE3D1_TOPIC_NOISE_FIX: adjective pseudo-topics
try:
    BAD_WORDS.update(['größer', 'groesser', 'größere', 'groessere', 'kleine', 'kleiner', 'kleines', 'bekannt', 'bekannte', 'bekannter', 'bekanntes', 'andere', 'weiter', 'weitere', 'mehrere'])
except Exception:
    pass

# PHASE3D2_FOOTER_TOPIC_NOISE
try:
    BAD_WORDS.update(['der text', 'creative commons', 'verfügbar unter creative commons attribution-share alike 4', 'verfuegbar unter creative commons attribution-share alike 4'])
except Exception:
    pass

# PHASE3D3_STRICT_TOPIC_NOISE
try:
    BAD_WORDS.update(['und', 'jedoch', 'aber', 'oder', 'sowie', 'dabei', 'dadurch', 'damit', 'the encyclopedia of weapons of world', 'german artillery of world', 'modus die 24 mannschaften', 'in zwei gruppen zu je 12 teams eingeteilt', 'deutsch', '1/deutsch'])
except Exception:
    pass

# PHASE3D4_PREPOSITION_FRAGMENT_TOPIC_NOISE
try:
    BAD_WORDS.update(['bei', 'vor', 'im', 'in', 'an', 'auf', 'mit', 'für', 'fuer', 'von', 'nach', 'cm-flak', 'cm-gebirgshaubitze 40', 'vor dem abschuss', 'der rückstoß', 'der rueckstoss', 'dies'])
except Exception:
    pass

# PHASE3D5_IS_A_DEFINITION_TOPIC_NOISE
try:
    BAD_WORDS.update(['der verschluss', 'unten am wiegentrog', 'ergänzend', 'ergaenzend', 'einige davon', 'montiert', 'begriffsklärungsseite', 'begriffsklaerungsseite'])
except Exception:
    pass

# PHASE3D6_SUBJECT_ALIGNMENT_TOPIC_NOISE
try:
    BAD_WORDS.update(['gecs', 'days', 'reasons', 'reason', 'da 02', 'da 20', '10+2', 'cover auf dem cover des albums', 'cover des albums', 'auf dem cover des albums'])
except Exception:
    pass

# PHASE3D7_QUESTION_GUARD_TOPIC_AFFECT
try:
    BAD_WORDS.update(['größer', 'groesser', 'kleine', 'bekannt', 'bekannte', 'jedoch', 'aber', 'und', 'oder', 'gecs', 'days', 'reasons', 'reason', 'da 02', 'da 20', '10+2', 'cm-flak', 'cover', 'der text', 'creative commons'])
except Exception:
    pass
