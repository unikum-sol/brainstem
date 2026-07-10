from __future__ import annotations
import re

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
YEAR_RE = re.compile(r'\b(18|19|20)\d{2}\b')

# Headings glued to entity phrases, question/evaluation starts, and clause fragments
# that repeatedly slipped through previous phases.
QUESTION_OR_EVAL_EXACT = {
    'wie gut', 'wie', 'was', 'warum', 'wieso', 'wozu', 'wann', 'wer', 'welche', 'welcher', 'welches',
}
QUESTION_OR_EVAL_PREFIXES = (
    'wie gut ', 'wie funktioniert ', 'was ist ', 'was ', 'warum ', 'wieso ', 'welche ', 'welcher ', 'welches ',
)
HEADING_ARTIFACT_PREFIXES = (
    'entwicklung die ', 'entwicklung der ', 'entwicklung das ',
    'lokalisierung ', 'sicherheitsaspekte bei ', 'sicherheitsaspekte ',
    'bit durch ', 'durch den externen ', 'durch die externe ',
    'bekannte prozessoren ', 'bekannte prozessoren mit ',
    'evolution der sprache ', 'evolution des ', 'evolution die ',
    'systeminformationen unter ', 'grundlegende konzepte ', 'haftung für ', 'haftung fuer ',
    'vertreter unter anderem ', 'operationen mit ', 'videos und audiodateien ',
    'anmerkungen ', 'präambel ', 'preambel ', 'problembehebung ', 'trivia ', 'logo ',
    'adolph ', 'oblivion ', 'bounty men ', 's bounty ', 'pc mit ', 'pcs mit ',
    'dateisystem ', 'lediglich ', 'm-programmen ', 'alle posts ', 'pooles identität ', 'pooles identitaet ',
    'der codename lautet ', 'codename lautet ', 'der begriff ', 'ein bekannter subtyp ',
)
HEADING_ARTIFACT_CONTAINS = (
    ' die folgenden ', ' folgende ', ' bekannten prozessoren ', ' anmerkungen ', ' lokalisierung ',
    ' entwicklung die ', ' entwicklung der ', ' evolution der ', ' sicherheitsaspekte ', ' grundlagen ',
    ' problembehebung ', ' im vergleich ', ' bei der verwendung ',
)
CLAUSE_START_EXACT = {
    'der effekt', 'der f-wert des startknotens', 'die texelfüllrate und die speicherbandbreite',
    'die texelfuellrate und die speicherbandbreite', 'viele sonique-visualisierungen', 'hiervon',
}
CLAUSE_START_PREFIXES = (
    'der effekt ', 'die erwartungen ', 'die verwendung ', 'die verbindung zum ', 'die cpu benötigt ', 'die cpu benoetigt ',
    'eine weniger ', 'das dem menschen ', 'wenn der ', 'weil ', 'welcher ', 'ist sichtbar ', 'beschrieben ',
    'verwenden ebenfalls ', 'fest dem ', 'der physische ', 'die dann ', 'das virus ', 's ', 'se ', 'ser ',
)
BAD_OBJECT_PREFIXES = (
    'vor allem ', 'speziell für ', 'speziell fuer ', 'laut ', 'daher ', 'damit ', 'dabei ', 'deshalb ',
    'theoretische ', 'zufällig ', 'zufaellig ', 'frei programmierbar', 'relativ ', 'vollständig ', 'vollstaendig ',
    'völlig ', 'voellig ', 'erstes ergebnis ', 'erstes ', 'ige ', 'e ', 's ', 'se ', 'ser ',
)
BAD_OBJECT_CONTAINS = (
    ' vor allem ', ' speziell für ', ' speziell fuer ', ' laut ', ' dafür ', ' dafuer ',
    'frei programmierbar', 'case- in sensitive', 'case insensitive', 'case-insensitive',
    'zu beachten', 'für höhere taktraten', 'fuer hoehere taktraten', 'für server und workstations ausgelegt',
    'fuer server und workstations ausgelegt', 'ausgelegt', 'verbreitet', 'zufällig angeordnet', 'zufaellig angeordnet',
    'theoretische maximalwerte', 'im handel', 'direkt möglich', 'direkt moeglich', 'relativ problemlos',
)

NOMINAL_HINTS = {
    'protokoll', 'schnittstelle', 'framework', 'software', 'programm', 'betriebssystem', 'prozessor',
    'mikroprozessor', 'dateiformat', 'format', 'standard', 'algorithmus', 'architektur', 'netzwerk',
    'datenbank', 'programmiersprache', 'sprache', 'bibliothek', 'system', 'domain', 'server', 'client',
    'unternehmen', 'projekt', 'diagramm', 'gerät', 'geraet', 'tool', 'paket', 'modell', 'serie', 'familie',
    'anwendung', 'spezifikation', 'verfahren', 'methode', 'schnittstelle', 'bus', 'route-over-protokoll',
}
SAFE_RELATIONS = {'located_in', 'has_color', 'has_name', 'has_original_domain', 'has_property_value'}


def norm_text(value):
    return ' '.join(str(value or '').replace('_', ' ').split()).strip()


def norm_key(value):
    return norm_text(value).lower()[:280]


def relation_key(value):
    return norm_text(value).lower().replace(' ', '_')[:80]


def tokens(value):
    return [t.lower() for t in WORD_RE.findall(norm_text(value))]


def token_count(value):
    return len(tokens(value))


def has_nominal_hint(text):
    t = norm_key(text)
    return any(h in t for h in NOMINAL_HINTS)


def heading_subject_reason(subject):
    s = norm_key(subject)
    if not s:
        return 'clause_empty_subject'
    if s in QUESTION_OR_EVAL_EXACT or any(s.startswith(p) for p in QUESTION_OR_EVAL_PREFIXES):
        return 'clause_question_or_evaluation_subject'
    if any(s.startswith(p) for p in HEADING_ARTIFACT_PREFIXES):
        return 'heading_artifact_subject'
    if any(x in s for x in HEADING_ARTIFACT_CONTAINS) and token_count(subject) >= 4:
        return 'heading_artifact_subject'
    if s in CLAUSE_START_EXACT or any(s.startswith(p) for p in CLAUSE_START_PREFIXES):
        return 'clause_fragment_subject'
    # Title + entity mashups: multiple capitalized tokens and long-ish phrase with no clean nominal relation.
    if token_count(subject) >= 7 and any(x in s for x in (' der ', ' die ', ' das ', ' bei ', ' durch ', ' unter ')):
        return 'heading_mixed_title_subject'
    return ''


def clause_object_reason(subject, relation, obj):
    r = relation_key(relation)
    if r in SAFE_RELATIONS:
        return ''
    if r not in ('is_a', 'definition'):
        return ''
    o = norm_key(obj)
    if not o:
        return 'clause_empty_object'
    if any(o.startswith(p) for p in BAD_OBJECT_PREFIXES):
        return 'clause_predicate_object_prefix'
    if any(x in o for x in BAD_OBJECT_CONTAINS):
        return 'clause_predicate_object_phrase'
    # Short non-nominal fragments are usually states, dates, or stray values.
    tc = token_count(obj)
    if tc <= 3 and not has_nominal_hint(obj):
        if YEAR_RE.search(o) or any(x in o for x in ('groß', 'gross', 'hoch', 'gering', 'möglich', 'moeglich', 'kompatibel', 'verbreitet', 'frei', 'anfang', 'ende')):
            return 'clause_short_non_nominal_object'
    return ''


def heading_artifact_clause_reason(subject, relation, obj):
    sr = heading_subject_reason(subject)
    if sr:
        return sr
    return clause_object_reason(subject, relation, obj)


def apply_patch(AdaptiveQuality):
    if getattr(AdaptiveQuality, '_phase3d6o_heading_clause_patched', False):
        return
    original = AdaptiveQuality.classify_candidate

    def classify_candidate_heading_clause_gated(self, subject, relation, obj, confidence=0.0, scores=None):
        pre_reason = heading_artifact_clause_reason(subject, relation, obj)
        if pre_reason:
            return False, pre_reason
        allowed, reason = original(self, subject, relation, obj, confidence, scores)
        if not allowed:
            return allowed, reason
        post_reason = heading_artifact_clause_reason(subject, relation, obj)
        if post_reason:
            return False, post_reason
        return True, reason

    AdaptiveQuality.classify_candidate = classify_candidate_heading_clause_gated
    AdaptiveQuality._phase3d6o_heading_clause_patched = True
