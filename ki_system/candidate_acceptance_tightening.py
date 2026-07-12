from __future__ import annotations
import re

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

# Subjects that often looked entity-like due to capitalization but are actually discourse/adverbial frames.
BAD_SUBJECT_EXACT = set()
BAD_SUBJECT_PREFIXES = ()

BAD_ISA_OBJECT_EXACT = set()
BAD_ISA_OBJECT_PREFIXES = ()
BAD_ISA_OBJECT_CONTAINS = ()

SAFE_SHORT_OBJECT_HINTS = {
    'protokoll', 'framework', 'software', 'programm', 'betriebssystem', 'prozessor', 'mikroprozessor',
    'dateiformat', 'format', 'standard', 'algorithmus', 'architektur', 'netzwerk', 'datenbank',
    'sprache', 'bibliothek', 'schnittstelle', 'system', 'domain', 'server', 'client', 'unternehmen',
    'projekt', 'diagramm', 'gerät', 'geraet', 'tool', 'paket', 'fork', 'forks'
}

PROPERTY_SUBJECT_HINTS = (
    'farbe', 'hintergrundfarbe', 'color', 'ursprüngliche domain', 'urspruengliche domain', 'codename', 'der name', 'ihr codename'
)


def norm_text(value):
    return ' '.join(str(value or '').replace('_', ' ').split()).strip()


def norm_key(value):
    return norm_text(value).lower()[:220]


def relation_key(value):
    return norm_text(value).lower().replace(' ', '_')[:80]


def tokens(value):
    return [t.lower() for t in WORD_RE.findall(norm_text(value))]


def token_count(value):
    return len(tokens(value))


def has_safe_short_object_hint(obj):
    o = norm_key(obj)
    return any(h in o for h in SAFE_SHORT_OBJECT_HINTS)


def has_property_subject_hint(subject):
    s = norm_key(subject)
    return any(h in s for h in PROPERTY_SUBJECT_HINTS)


def subject_tightening_reason(subject):
    s = norm_key(subject)
    if not s:
        return 'acceptance_empty_subject'
    if s in BAD_SUBJECT_EXACT:
        return 'acceptance_adverbial_or_discourse_subject'
    if any(s.startswith(prefix) for prefix in BAD_SUBJECT_PREFIXES):
        return 'acceptance_frame_or_generic_subject'
    if norm_text(subject)[:1].islower() and token_count(subject) > 1:
        return 'acceptance_lowercase_subject_fragment'
    if token_count(subject) > 9:
        return 'acceptance_subject_too_long'
    if (' und ' in s or ' oder ' in s) and token_count(subject) > 4:
        return 'acceptance_coordinated_subject'
    # Mixed heading artifacts are recurring bad subjects.
    if ' die folgenden ' in s or ' folgende ' in s or ' logo ' in s or ' probleme ' in s:
        return 'acceptance_heading_artifact_subject'
    return ''


def object_tightening_reason(subject, relation, obj):
    r = relation_key(relation)
    o = norm_key(obj)
    if not o:
        return 'acceptance_empty_object'
    if r not in ('is_a', 'definition'):
        return ''
    if has_property_subject_hint(subject):
        # Let relation_repair/definition_guard type these rather than blocking too early.
        return ''
    if o in BAD_ISA_OBJECT_EXACT:
        return 'acceptance_bad_is_a_object_exact'
    if any(o.startswith(prefix) for prefix in BAD_ISA_OBJECT_PREFIXES):
        return 'acceptance_bad_is_a_object_prefix'
    if any(fragment in o for fragment in BAD_ISA_OBJECT_CONTAINS):
        return 'acceptance_bad_is_a_object_phrase'
    if any(o.endswith(suf) for suf in (' des', ' der', ' die', ' das', ' von', ' für', ' fuer', ' mit', ' bei', ' zu', ' als', ' und', ' oder', '(', '[', '{', ':')):
        return 'acceptance_object_incomplete_fragment'
    tc = token_count(obj)
    if tc < 2 and not has_safe_short_object_hint(obj):
        return 'acceptance_object_too_short'
    if tc <= 2 and YEAR_RE.search(o):
        return 'acceptance_object_is_date_or_number_fragment'
    if tc > 15 or len(norm_text(obj)) > 145:
        return 'acceptance_object_too_long'
    # Clause-like object without a nominal head.
    if tc <= 5 and not has_safe_short_object_hint(obj) and any(w in o for w in ('variabel', 'geeignet', 'erforderlich', 'nötig', 'noetig', 'schneller', 'selten', 'hoch')):
        return 'acceptance_non_nominal_object'
    return ''


def tightening_reason(subject, relation, obj):
    sr = subject_tightening_reason(subject)
    if sr:
        return sr
    return object_tightening_reason(subject, relation, obj)


def apply_patch(AdaptiveQuality):
    if getattr(AdaptiveQuality, '_phase3d6m_acceptance_tightening_patched', False):
        return
    original = AdaptiveQuality.classify_candidate

    def classify_candidate_tightened(self, subject, relation, obj, confidence=0.0, scores=None):
        pre_reason = tightening_reason(subject, relation, obj)
        if pre_reason:
            return False, pre_reason
        allowed, reason = original(self, subject, relation, obj, confidence, scores)
        if not allowed:
            return allowed, reason
        post_reason = tightening_reason(subject, relation, obj)
        if post_reason:
            return False, post_reason
        return True, reason

    AdaptiveQuality.classify_candidate = classify_candidate_tightened
    AdaptiveQuality._phase3d6m_acceptance_tightening_patched = True
