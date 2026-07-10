from __future__ import annotations
from collections import Counter
import re

LICENSE_TERMS = (
    'creative commons', 'attribution-share alike', 'attribution share alike', 'cc-by-sa',
    'wikipedia', 'wikimedia', 'der text ist', 'der text', 'verfügbar unter', 'verfuegbar unter',
    'lizenz', 'license'
)

BAD_SUBJECTS = {
    'der text','die text','das text','text','dabei','dadurch','darin','damit','dessen','deren',
    'dieser','diese','dieses','diesen','diesem','dies','auch','hierbei','somit','außerdem','ausserdem',
    'und','jedoch','aber','oder','sowie','wobei','während','waehrend','zudem','ferner','hierdurch',
    'ergänzend','ergaenzend','montiert','einige davon','der verschluss','unten am wiegentrog',
    'im kopf der granate','cover auf dem cover des albums','cover des albums','auf dem cover des albums',
    'technische beschreibung der minenwerfer','german artillery of world',
    'the encyclopedia of weapons of world','the encyclopedia of weapons of world war','german artillery of world war',
    'cm-flak','cm-gebirgshaubitze 40','cm-gebirgshaubitze','cm-flak 40','gecs','days','reasons'
}

BAD_OBJECTS = {
    'one','two','three','four','five','i','ii','iii','iv','v','vi','vii','viii','ix','x',
    'da 02','da 20','da 2','da 02.','da 20.',
    'sehr gering','damit sehr hoch','nur sehr schwer zu lokalisieren',
    'verfügbar unter creative commons attribution-share alike 4',
    'verfuegbar unter creative commons attribution-share alike 4',
    'heute noch vorhanden, bzw','von den uhrenwerken gebr'
}

BAD_SUBJECT_PREFIXES = (
    'der text', 'die liste', 'diese liste', 'technische beschreibung', 'museale rezeption',
    'an den enden ', 'auch die ', 'dadurch ', 'dabei ', 'hierbei ', 'somit ', 'zudem ',
    'the encyclopedia of ', 'german artillery of ', 'world war ', 'modus die ', 'in zwei gruppen ',
    'bei ', 'vor ', 'im ', 'in ', 'an ', 'auf ', 'aus ', 'mit ', 'für ', 'fuer ', 'von ', 'nach ', 'während ', 'waehrend ',
    'unten ', 'oben ', 'ergänzend', 'ergaenzend', 'montiert', 'einige davon', 'der verschluss',
    'cover auf dem cover', 'cover des albums', 'auf dem cover'
)

BAD_OBJECT_PREFIXES = (
    'für ', 'fuer ', 'von ', 'an ', 'bei ', 'im ', 'in ', 'mit ', 'ohne ', 'nach ',
    'es ', 'heute ', 'jeweils ', 'fast ', 'nur ', 'sehr ', 'als ', 'aus ', 'auf '
)

BAD_TOPIC_OR_PHRASE_PARTS = (
    'creative commons', 'attribution-share alike', 'verfügbar unter', 'verfuegbar unter',
    'encyclopedia of weapons', 'german artillery of world', 'museale rezeption',
    'modus die ', 'in zwei gruppen ', 'zu je 12 teams', 'heute noch vorhanden',
    'horizontal gelagerte munition platziert', 'uhrenwerke gebr', 'zentrale plattform für die mannschaft',
    'zentrale plattform fuer die mannschaft', 'begriffsklärungsseite', 'begriffsklaerungsseite',
    'cover auf dem cover', 'auf dem cover des albums'
)

TITLE_FRAGMENT_WORDS = {'gecs','days','reasons','reason'}
TYPE_HINTS = {
    'asteroid','fluss','stadt','gemeinde','observatorium','schauspieler','schriftsteller','komponist',
    'politiker','physiker','mathematiker','astronom','biologe','chemiker','maler','autor','roman',
    'film','album','lied','band','universität','universitaet','schule','verein','unternehmen','organisation',
    'berg','insel','see','staat','land','provinz','region','familie','gruppe','gattung','art','klasse',
    'minenwerfer','haubitze','kanone','feldkanone','gebirgsgeschütz','gebirgsgeschuetz','geschütz','geschuetz',
    'panzerzugdivision','rauschen','system','gerät','geraet','waffe','bauwerk','person','ort','objekt',
    'lied','bezeichnung','album','single','begriff','verfahren','prinzip','modell','software','sprache'
}
BAD_ISA_OBJECT_WORDS = {
    'ausgeführt','ausgefuehrt','befestigt','stammende','einsatz','montiert','entwickelt','worden',
    'einzustellen','abklappbar','bildeten','gebildet','platziert','angebracht','gebunden','vorhanden',
    'eingeteilt','befindet','besitzt','hatte','hat','war','ist','wurde','wurden','öffnender','oeffnender',
    'höhenrichten','hoehenrichten','rückstoß','rueckstoss','abgebildet'
}

GOOD_SUBJECT_HINT_RE = re.compile(r'(\d|[A-ZÄÖÜ][a-zäöüß]+[- ][A-ZÄÖÜa-zäöüß0-9]|[A-ZÄÖÜ]{2,}|cm-|/)', re.U)
ROMAN_RE = re.compile(r'^(?:[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten)$', re.I)
PRONOUN_RE = re.compile(r'^(dabei|dadurch|darin|damit|dies|dieser|diese|dieses|diesen|diesem|auch|hierbei|somit|und|jedoch|aber|oder|sowie|zudem|ferner)\b', re.I)
PREPOSITION_SUBJECT_RE = re.compile(r'^(bei|vor|im|in|an|auf|aus|mit|für|fuer|von|nach|während|waehrend|unten|oben)\b', re.I)
DA_OBJECT_RE = re.compile(r'^da\s*\d{1,3}\.?$', re.I)


def _norm(x: str) -> str:
    return ' '.join((x or '').strip().lower().replace('_', ' ').split())


def _display_title(context_subject: str) -> str:
    return ' '.join((context_subject or '').strip().replace('_', ' ').split())


def _word_count(x: str) -> int:
    return len(_norm(x).split())


def _contains_bad_part(x: str) -> bool:
    t = _norm(x)
    return any(part in t for part in BAD_TOPIC_OR_PHRASE_PARTS)


def _object_has_type_hint(obj: str) -> bool:
    words = set(_norm(obj).replace('-', ' ').split())
    return bool(words & TYPE_HINTS)


def _looks_like_truncated_technical_subject(subject: str) -> bool:
    s = _norm(subject)
    if s.startswith('cm-') or s in {'cm flak','cm-flak','cm gebirgshaubitze','cm-gebirgshaubitze'}:
        return True
    if re.match(r'^cm[- ]', s):
        return True
    return False


def _is_title_fragment(subject: str, context_subject: str | None) -> bool:
    s = _norm(subject)
    ctx = _norm(context_subject or '')
    if not ctx or not s:
        return False
    if s == ctx:
        return False
    if s in TITLE_FRAGMENT_WORDS and s in ctx.split():
        return True
    if len(s.split()) == 1 and len(s) >= 4 and s in ctx and any(ch.isdigit() for ch in ctx):
        return True
    return False


def _should_align_subject(subject: str, relation: str, obj: str, context_subject: str | None) -> bool:
    s = _norm(subject)
    r = _norm(relation)
    o = _norm(obj)
    ctx = _norm(context_subject or '')
    if r != 'is_a' or not ctx or not s:
        return False
    if s == ctx:
        return False
    if _is_title_fragment(subject, context_subject) and _object_has_type_hint(obj):
        return True
    if len(s.split()) == 1 and s in ctx.split() and any(ch.isdigit() for ch in ctx) and _object_has_type_hint(obj):
        return True
    return False


def normalize_relation(subject, relation, obj, confidence=1.0, context_subject=None):
    if _should_align_subject(subject, relation, obj, context_subject):
        return (_display_title(context_subject), relation, obj, confidence)
    return (subject, relation, obj, confidence)


def _too_sentence_like_object(text: str) -> bool:
    raw = text or ''
    t = _norm(raw)
    words = t.split()
    if len(t) > 95:
        return True
    if ',' in raw and len(words) > 5:
        return True
    if DA_OBJECT_RE.match(t):
        return True
    if any(v in words for v in BAD_ISA_OBJECT_WORDS) and len(words) > 3:
        return True
    if t.endswith((' bzw', ' bzw.', ' und', ' oder', ' von', ' für', 'fuer')):
        return True
    if any(t.startswith(p) for p in BAD_OBJECT_PREFIXES) and len(words) > 2:
        return True
    if ' zu ' in t and any(v in words for v in ('einzustellen','entwickelt','platziert','eingeteilt')):
        return True
    return False


def _is_meta_disambiguation_object(obj: str) -> bool:
    o = _norm(obj)
    return ('begriffsklärungsseite' in o or 'begriffsklaerungsseite' in o or
            'unterscheidung mehrerer' in o or 'demselben wort bezeichnet' in o or
            o.startswith('e begriff') or o.startswith('eine begriff'))


def _is_bad_is_a_definition(subject: str, obj: str, context_subject: str | None = None) -> str | None:
    s = _norm(subject)
    o = _norm(obj)
    words = o.split()
    if _is_meta_disambiguation_object(obj):
        return 'wiki_meta_disambiguation_object'
    if DA_OBJECT_RE.match(o):
        return 'is_a_short_code_object'
    if s.startswith(('cover ', 'cover des ', 'auf dem cover')) or 'auf dem cover' in s:
        return 'cover_or_layout_fragment_subject'
    if any(o.startswith(p) for p in ('als ', 'aus ', 'auf ', 'von ', 'an ', 'im ', 'in ')) and len(words) > 2:
        return 'is_a_object_prepositional_or_adverbial'
    if any(w in words for w in BAD_ISA_OBJECT_WORDS):
        return 'is_a_object_participle_or_verb_fragment'
    if s in BAD_SUBJECTS and not _should_align_subject(subject, 'is_a', obj, context_subject):
        return 'is_a_bad_or_vague_subject'
    if _is_title_fragment(subject, context_subject) and not _should_align_subject(subject, 'is_a', obj, context_subject):
        return 'title_fragment_subject'
    if s.startswith(('der ', 'die ', 'das ', 'einige ', 'unten ', 'oben ', 'ergänzend', 'ergaenzend', 'montiert')) and _word_count(subject) <= 4:
        return 'is_a_vague_article_or_adverb_subject'
    if s.startswith(('der ', 'die ', 'das ')) and not GOOD_SUBJECT_HINT_RE.search(subject or ''):
        return 'is_a_generic_article_subject'
    if _word_count(subject) <= 2 and s in {'verschluss','der verschluss','montiert','ergänzend','ergaenzend'}:
        return 'is_a_vague_subject'
    return None


def reject_reason(subject, relation, obj, context_subject=None):
    # Normalize first, so title fragments like Gecs/Days can become full article subjects when safe.
    subject, relation, obj, _c = normalize_relation(subject, relation, obj, 1.0, context_subject=context_subject)
    s = _norm(subject)
    r = _norm(relation)
    o = _norm(obj)
    joined = ' '.join([s, r, o])
    if not s or not o:
        return 'empty_subject_or_object'
    if any(term in joined for term in LICENSE_TERMS):
        return 'license_or_footer'
    if _contains_bad_part(s) or _contains_bad_part(o):
        return 'source_or_sentence_fragment'
    if s in BAD_SUBJECTS or o in BAD_OBJECTS:
        return 'known_bad_phrase'
    if ROMAN_RE.match(o):
        return 'roman_or_number_word_object'
    if PREPOSITION_SUBJECT_RE.match(s):
        return 'preposition_subject_fragment'
    if PRONOUN_RE.match(s) or any(s.startswith(p) for p in BAD_SUBJECT_PREFIXES):
        return 'pronoun_or_filler_subject'
    if _looks_like_truncated_technical_subject(subject or ''):
        return 'truncated_technical_subject'
    if _is_title_fragment(subject, context_subject):
        return 'title_fragment_subject'
    if len(s) < 3 or len(o) < 2:
        return 'too_short'
    if _word_count(s) > 7 and not GOOD_SUBJECT_HINT_RE.search(subject or ''):
        return 'subject_sentence_like_or_too_long'
    if len(s) > 90:
        return 'subject_too_long'
    if _too_sentence_like_object(obj or ''):
        return 'object_sentence_like_or_too_long'
    if r == 'is_a':
        bad_def = _is_bad_is_a_definition(subject or '', obj or '', context_subject=context_subject)
        if bad_def:
            return bad_def
        owc = _word_count(o)
        if owc > 8:
            return 'low_quality_is_a_object_too_long'
        if owc > 4 and not _object_has_type_hint(o):
            return 'low_quality_is_a_object_no_type_hint'
        if any(w in o.split() for w in ('sehr','nur','unter','ohne','fast')) and owc > 2:
            return 'low_quality_is_a_object'
    return None


def is_good_relation(subject, relation, obj, context_subject=None) -> bool:
    return reject_reason(subject, relation, obj, context_subject=context_subject) is None


def filter_relations(relations, context_subject=None):
    out = []
    for rel in relations or []:
        try:
            s, r, o, c = rel
        except Exception:
            continue
        ns, nr, no, nc = normalize_relation(s, r, o, c, context_subject=context_subject)
        if is_good_relation(ns, nr, no, context_subject=context_subject):
            out.append((ns, nr, no, nc))
    return out


def evaluate_relations(relations, context_subject=None):
    accepted = []
    rejected = Counter()
    rejected_sample = []
    repaired_sample = []
    for rel in relations or []:
        try:
            s, r, o, c = rel
        except Exception:
            rejected['malformed'] += 1
            continue
        ns, nr, no, nc = normalize_relation(s, r, o, c, context_subject=context_subject)
        if (ns, nr, no) != (s, r, o) and len(repaired_sample) < 8:
            repaired_sample.append({'from': [s, r, o], 'to': [ns, nr, no], 'context': context_subject})
        reason = reject_reason(ns, nr, no, context_subject=context_subject)
        if reason:
            rejected[reason] += 1
            if len(rejected_sample) < 16:
                rejected_sample.append({'relation': [ns, nr, no], 'reason': reason})
        else:
            accepted.append((ns, nr, no, nc))
    return {
        'raw_relations': len(relations or []),
        'accepted_relations': len(accepted),
        'rejected_total': sum(rejected.values()),
        'rejected_by_reason': dict(rejected),
        'rejected_sample': rejected_sample,
        'repaired_sample': repaired_sample,
        'accepted': accepted,
    }
