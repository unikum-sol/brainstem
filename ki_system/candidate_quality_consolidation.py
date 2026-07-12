from __future__ import annotations
import json
import re
import time

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
YEAR_RE = re.compile(r'\b(18|19|20)\d{2}\b')

SAFE_RELATIONS = {'located_in', 'has_color', 'has_name', 'has_original_domain', 'has_property_value'}

PATCH_ORDER = [
    'phase3d6m_candidate_acceptance_tightening',
    'phase3d6n_predicate_quality_and_adjective_gate',
    'phase3d6o_heading_artifact_and_clause_gate',
    'phase3d7_candidate_quality_consolidation',
    'phase3d6k_candidate_sleep_pruning',
    'phase3d6l1_relation_repair_safety',
    'phase3d6l2_definition_candidate_guard',
]

# Consolidated subject blocks from 3d6m/n/o plus additions observed in latest logs.
BAD_SUBJECT_EXACT = set()
BAD_SUBJECT_PREFIXES = ()
BAD_SUBJECT_CONTAINS = ()
CLAUSE_SUBJECT_PREFIXES = ()

BAD_OBJECT_EXACT = set()
BAD_OBJECT_PREFIXES = ()
BAD_OBJECT_CONTAINS = ()
NOMINAL_HINTS = {
    'protokoll', 'schnittstelle', 'framework', 'software', 'programm', 'betriebssystem', 'prozessor', 'mikroprozessor',
    'dateiformat', 'format', 'standard', 'algorithmus', 'architektur', 'netzwerk', 'datenbank', 'programmiersprache',
    'sprache', 'bibliothek', 'system', 'domain', 'server', 'client', 'unternehmen', 'projekt', 'diagramm', 'gerät',
    'geraet', 'tool', 'paket', 'modell', 'serie', 'familie', 'anwendung', 'spezifikation', 'verfahren', 'methode',
    'bus', 'route-over-protokoll', 'funk-rechnernetz', 'eingabegerät', 'eingabegeraet', 'implementierung',
}
PROPERTY_SUBJECT_HINTS = (
    'farbe', 'hintergrundfarbe', 'color', 'ursprüngliche domain', 'urspruengliche domain', 'codename', 'der name',
    'ihr codename', 'sitz', 'zentrale', 'hauptsitz', 'standort'
)


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
    return any(h in v for h in NOMINAL_HINTS)


def has_property_subject_hint(subject):
    s = norm_key(subject)
    return any(h in s for h in PROPERTY_SUBJECT_HINTS)


def consolidated_quality_reason(subject, relation, obj):
    s = norm_key(subject)
    r = relation_key(relation)
    o = norm_key(obj)
    if not s:
        return 'consolidated_empty_subject'
    if not o:
        return 'consolidated_empty_object'
    if s in BAD_SUBJECT_EXACT:
        return 'consolidated_bad_subject_exact'
    if any(s.startswith(p) for p in BAD_SUBJECT_PREFIXES):
        return 'consolidated_heading_or_frame_subject'
    if any(x in s for x in BAD_SUBJECT_CONTAINS) and token_count(subject) >= 4:
        return 'consolidated_heading_artifact_subject'
    if any(s.startswith(p) for p in CLAUSE_SUBJECT_PREFIXES) and token_count(subject) > 2:
        return 'consolidated_clause_fragment_subject'
    if norm_text(subject)[:1].islower() and token_count(subject) > 1:
        return 'consolidated_lowercase_subject_fragment'
    if token_count(subject) > 10:
        return 'consolidated_subject_too_long'
    if (' und ' in s or ' oder ' in s) and token_count(subject) > 4:
        return 'consolidated_coordinated_subject'

    if r in SAFE_RELATIONS:
        return ''
    if r not in ('is_a', 'definition'):
        return ''
    if has_property_subject_hint(subject):
        return ''
    if o in BAD_OBJECT_EXACT:
        return 'consolidated_bad_object_exact'
    if any(o.startswith(p) for p in BAD_OBJECT_PREFIXES):
        return 'consolidated_predicate_object_prefix'
    if any(x in o for x in BAD_OBJECT_CONTAINS):
        return 'consolidated_predicate_object_phrase'
    if any(o.endswith(suf) for suf in (' des', ' der', ' die', ' das', ' von', ' für', ' fuer', ' mit', ' bei', ' zu', ' als', ' und', ' oder', '(', '[', '{', ':')):
        return 'consolidated_object_incomplete_fragment'
    tc = token_count(obj)
    if tc < 2 and not has_nominal_hint(obj):
        return 'consolidated_object_too_short'
    if tc <= 3 and not has_nominal_hint(obj):
        if YEAR_RE.search(o) or any(x in o for x in ('groß', 'gross', 'hoch', 'gering', 'möglich', 'moeglich', 'kompatibel', 'verbreitet', 'frei', 'anfang', 'ende')):
            return 'consolidated_short_non_nominal_object'
    if tc > 15 or len(norm_text(obj)) > 150:
        return 'consolidated_object_too_long'
    return ''


def apply_patch(AdaptiveQuality):
    if getattr(AdaptiveQuality, '_phase3d7_candidate_quality_consolidated_patched', False):
        return
    original = AdaptiveQuality.classify_candidate

    def classify_candidate_consolidated(self, subject, relation, obj, confidence=0.0, scores=None):
        pre_reason = consolidated_quality_reason(subject, relation, obj)
        if pre_reason:
            return False, pre_reason
        allowed, reason = original(self, subject, relation, obj, confidence, scores)
        if not allowed:
            return allowed, reason
        post_reason = consolidated_quality_reason(subject, relation, obj)
        if post_reason:
            return False, post_reason
        return True, reason

    AdaptiveQuality.classify_candidate = classify_candidate_consolidated
    AdaptiveQuality._phase3d7_candidate_quality_consolidated_patched = True


def quality_gate_flags():
    try:
        from ki_system.adaptive_quality import AdaptiveQuality
        return {
            'phase3d6m': bool(getattr(AdaptiveQuality, '_phase3d6m_acceptance_tightening_patched', False)),
            'phase3d6n': bool(getattr(AdaptiveQuality, '_phase3d6n_predicate_quality_patched', False)),
            'phase3d6o': bool(getattr(AdaptiveQuality, '_phase3d6o_heading_clause_patched', False)),
            'phase3d7_consolidated': bool(getattr(AdaptiveQuality, '_phase3d7_candidate_quality_consolidated_patched', False)),
        }
    except Exception as exc:
        return {'error': str(exc)}


def install_quality_pack():
    applied = []
    errors = []
    try:
        from ki_system.adaptive_quality import AdaptiveQuality
    except Exception as exc:
        return {'status': 'quality_pack_install_error', 'applied': applied, 'errors': [{'module': 'adaptive_quality', 'error': str(exc)}]}
    for module_name, label in [
        ('ki_system.candidate_acceptance_tightening', 'phase3d6m'),
        ('ki_system.predicate_quality_gate', 'phase3d6n'),
        ('ki_system.heading_artifact_clause_gate', 'phase3d6o'),
    ]:
        try:
            mod = __import__(module_name, fromlist=['apply_patch'])
            mod.apply_patch(AdaptiveQuality)
            applied.append(label)
        except Exception as exc:
            errors.append({'module': module_name, 'error': str(exc)})
    try:
        apply_patch(AdaptiveQuality)
        applied.append('phase3d7_consolidated')
    except Exception as exc:
        errors.append({'module': 'candidate_quality_consolidation', 'error': str(exc)})
    return {'status': 'quality_pack_installed_phase3d7', 'applied': applied, 'errors': errors, 'flags': quality_gate_flags()}


def install_reader_status(CorpusReader):
    quality_info = install_quality_pack()
    if getattr(CorpusReader, '_phase3d7_quality_pack_status_patched', False):
        return {'status': 'already_installed_phase3d7', 'quality_info': quality_info}
    original = CorpusReader.read_once

    def read_once_with_phase3d7_quality_pack(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if isinstance(result, dict):
            result['status'] = 'adaptive_alignment_corpus_reader_phase3d7'
            result['candidate_quality_consolidation'] = {
                'status': 'candidate_quality_consolidation_phase3d7',
                'message': 'Consolidated 3d6m/3d6n/3d6o quality gates active. No facts/relations promotion.',
                'patch_order': list(PATCH_ORDER),
                'quality_info': quality_info,
                'quality_gate_flags': quality_gate_flags(),
                'fact_promotion': 'disabled',
                'direct_fact_writes': 'disabled',
                'direct_relation_writes': 'disabled',
                'created_at': int(time.time()),
            }
        return result

    CorpusReader.read_once = read_once_with_phase3d7_quality_pack
    CorpusReader._phase3d7_quality_pack_status_patched = True
    return {'status': 'installed_phase3d7', 'quality_info': quality_info}
