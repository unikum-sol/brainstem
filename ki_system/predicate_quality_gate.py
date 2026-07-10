from __future__ import annotations
import re

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
YEAR_RE = re.compile(r'\b(18|19|20)\d{2}\b')

# Subjects that are headings, frames, discourse markers, or predicate carriers rather than stable entities.
PREDICATE_BAD_SUBJECT_EXACT = {
    'leider', 'hierzu', 'darüber hinaus', 'darueber hinaus', 'insofern', 'bislang', 'vielmehr', 'dagegen',
    'hiervon', 'hierbei', 'hiermit', 'dann', 'was', 'daher', 'deshalb', 'damit', 'allerdings',
    'zukunft', 'codierung', 'erweiterungen', 'operationen mit dateigruppen', 'dateisystem',
}
PREDICATE_BAD_SUBJECT_PREFIXES = (
    'wie bei ', 'als ', 'laut ', 'aufgrund ', 'ohne ', 'neben ', 'zur ', 'zum ', 'im ', 'am ',
    'sicherheitsaspekte bei ', 'lokalisierung ', 'evolution der sprache ', 'evolution des ',
    'bekannte prozessoren ', 'haftung für ', 'haftung fuer ', 'probleme ', 'grundlegende konzepte ',
    'operationen mit ', 'versuche eines ', 'ein offenes problem', 'ein anderes problem', 'ein bekannter ',
    'jede monotone heuristik', 'knoten auf der closed list', 'der knoten ', 'wert', 'die gefundene lösung',
    'die gefundene loesung', 'der kürzeste pfad', 'der kuerzeste pfad', 'monotonie', 'die verwendete heuristik',
    'lediglich ', 'm-programmen', 'der algorithmus', 'algorithmus', 'der funktionsumfang',
    'der pulse', 'bit-programme', 'upcoming', 'kommerzielle antivirensoftware', 'der verwaltungsrat',
    'der inhalt', 'der code von ', 'das risiko ', 'das novum ', 'der pool', 'pooles identität', 'pooles identitaet',
    'alle posts ', 'die nutzung', 'der begriff ', 'präambel ', 'preambel ', 'pc', 'pcs mit ',
    'vertreter unter anderem', 'oblivion ', 'halt datensymbole', 'google-freies smartphone ',
)

# Objects below are mostly predicates/adjectival complements. For a safe fact graph these must not be accepted as is_a.
ADJECTIVE_OBJECT_EXACT = {
    'kostenlos', 'anonym', 'vollständig', 'vollstaendig', 'optimal', 'vollständig und optimal', 'vollstaendig und optimal',
    'verfügbar', 'verfuegbar', 'lauffähig', 'lauffaehig', 'kompatibel', 'inkompatibel', 'invertiert',
    'monoton', 'zulässig', 'zulaessig', 'bekannt', 'selten', 'hoch', 'hiermit', 'zurück', 'zurueck',
    'nutzdaten', 'zurück', 'zurueck', 'variabel', 'geeignet', 'möglich', 'moeglich', 'erforderlich', 'notwendig',
}
ADJECTIVE_OBJECT_PREFIXES = (
    'auch verfügbar', 'auch verfuegbar', 'auch zulässig', 'auch zulaessig', 'auch möglich', 'auch moeglich',
    'daher ', 'deshalb ', 'damit ', 'dabei ', 'jedoch ', 'allerdings ', 'leider ', 'nur ', 'noch ', 'nun ',
    'völlig ', 'voellig ', 'vollständig ', 'vollstaendig ', 'optimal ', 'entscheidend für ', 'entscheidend fuer ',
    'wesentlicher unterschied ', 'wesentlich ', 'verwandt mit ', 'ursprüngliche version', 'urspruengliche version',
    'ab sofort ', 'zwischen ', 'zu diesem zeitpunkt ', 'je modell ', 'in der regel ', 'meist ', 'bereits ',
    'abschließend betrachtet', 'abschliessend betrachtet', 'ausführlich ', 'ausfuehrlich ', 'frei erfunden',
    'wegen ', 'bis zur ', 'über freie ', 'ueber freie ', 'gemessene ', 'e ', 's ', 'se ', 'ser ',
)
ADJECTIVE_OBJECT_CONTAINS = (
    ' nicht ', 'nicht ', ' nicht', 'nicht exakt definiert', 'nicht grundsätzlich', 'nicht grundsaetzlich',
    'nicht plattformunabhängig', 'nicht plattformunabhaengig', 'nicht bekannt', 'nicht sichtbar',
    'nicht betroffen', 'nicht notwendig', 'nicht möglich', 'nicht moeglich', 'nicht erforderlich',
    'nicht kompatibel', 'nicht weiter betrachtet', 'daher case', 'case- in sensitive', 'case-insensitive',
    'relativ problemlos möglich', 'relativ problemlos moeglich', 'gut geeignet', 'wenig überzeugt', 'wenig ueberzeugt',
    'administratorrechte', 'kompatible prozessoren', 'bessere wahl', 'noch eingeschränkt', 'noch eingeschraenkt',
    'entscheidend für die positionierung', 'entscheidend fuer die positionierung', 'für marketingzwecke', 'fuer marketingzwecke',
    'für empfehlungssysteme', 'fuer empfehlungssysteme', 'fortlaufend nummeriert', 'geschlossen',
)

# These are nominal heads that make an object more likely to be definition-like.
NOMINAL_OBJECT_HINTS = {
    'protokoll', 'schnittstelle', 'framework', 'software', 'programm', 'betriebssystem', 'prozessor', 'mikroprozessor',
    'dateiformat', 'format', 'standard', 'algorithmus', 'architektur', 'netzwerk', 'datenbank', 'programmiersprache',
    'sprache', 'bibliothek', 'system', 'domain', 'server', 'client', 'unternehmen', 'projekt', 'diagramm', 'gerät',
    'geraet', 'tool', 'paket', 'anwendung', 'modell', 'spezifikation', 'methode', 'verfahren', 'familie', 'serie',
    'implementierung', 'spezifikation', 'route-over-protokoll', 'funk-rechnernetz', 'eingabegerät', 'eingabegeraet',
}

PROPERTY_SUBJECT_HINTS = (
    'farbe', 'hintergrundfarbe', 'color', 'ursprüngliche domain', 'urspruengliche domain', 'codename', 'der name',
    'ihr codename', 'sitz', 'zentrale', 'hauptsitz', 'standort'
)

SAFE_RELATIONS = {'located_in', 'has_color', 'has_name', 'has_original_domain', 'has_property_value'}


def norm_text(value):
    return ' '.join(str(value or '').replace('_', ' ').split()).strip()


def norm_key(value):
    return norm_text(value).lower()[:260]


def relation_key(value):
    return norm_text(value).lower().replace(' ', '_')[:80]


def tokens(value):
    return [t.lower() for t in WORD_RE.findall(norm_text(value))]


def token_count(value):
    return len(tokens(value))


def has_nominal_object_hint(obj):
    o = norm_key(obj)
    return any(h in o for h in NOMINAL_OBJECT_HINTS)


def has_property_subject_hint(subject):
    s = norm_key(subject)
    return any(h in s for h in PROPERTY_SUBJECT_HINTS)


def subject_predicate_reason(subject):
    s = norm_key(subject)
    if not s:
        return 'predicate_empty_subject'
    if s in PREDICATE_BAD_SUBJECT_EXACT:
        return 'predicate_discourse_subject'
    if any(s.startswith(prefix) for prefix in PREDICATE_BAD_SUBJECT_PREFIXES):
        return 'predicate_frame_subject'
    # Heading + entity artifacts often contain title words followed by a phrase.
    if any(marker in s for marker in (' bei ', ' unter ', ' die folgenden ', ' folgende ', ' lokalisierung ', ' evolution ', ' präambel ', ' preambel ')) and token_count(subject) > 4:
        return 'predicate_heading_artifact_subject'
    return ''


def object_predicate_reason(subject, relation, obj):
    r = relation_key(relation)
    if r in SAFE_RELATIONS:
        return ''
    if r not in ('is_a', 'definition'):
        return ''
    if has_property_subject_hint(subject):
        # Let property repair tools type these, but still block obvious predicate phrases.
        pass
    o = norm_key(obj)
    if not o:
        return 'predicate_empty_object'
    if o in ADJECTIVE_OBJECT_EXACT:
        return 'predicate_adjective_object_exact'
    if any(o.startswith(prefix) for prefix in ADJECTIVE_OBJECT_PREFIXES):
        return 'predicate_adjective_object_prefix'
    if any(fragment in o for fragment in ADJECTIVE_OBJECT_CONTAINS):
        return 'predicate_adjective_object_phrase'
    # Short adjective-like objects without a nominal head are unsafe as is_a.
    tc = token_count(obj)
    if tc <= 4 and not has_nominal_object_hint(obj):
        low = set(tokens(obj))
        adjective_markers = {'kompatibel', 'verfügbar', 'verfuegbar', 'lauffähig', 'lauffaehig', 'anonym', 'kostenlos', 'optimal', 'vollständig', 'vollstaendig', 'monoton', 'zulässig', 'zulaessig', 'bekannt', 'selten', 'hoch', 'variabel', 'geeignet'}
        if low & adjective_markers:
            return 'predicate_short_adjective_object'
    if tc <= 2 and YEAR_RE.search(o):
        return 'predicate_date_or_number_fragment'
    return ''


def predicate_quality_reason(subject, relation, obj):
    sr = subject_predicate_reason(subject)
    if sr:
        return sr
    return object_predicate_reason(subject, relation, obj)


def apply_patch(AdaptiveQuality):
    if getattr(AdaptiveQuality, '_phase3d6n_predicate_quality_patched', False):
        return
    original = AdaptiveQuality.classify_candidate

    def classify_candidate_predicate_gated(self, subject, relation, obj, confidence=0.0, scores=None):
        pre_reason = predicate_quality_reason(subject, relation, obj)
        if pre_reason:
            return False, pre_reason
        allowed, reason = original(self, subject, relation, obj, confidence, scores)
        if not allowed:
            return allowed, reason
        post_reason = predicate_quality_reason(subject, relation, obj)
        if post_reason:
            return False, post_reason
        return True, reason

    AdaptiveQuality.classify_candidate = classify_candidate_predicate_gated
    AdaptiveQuality._phase3d6n_predicate_quality_patched = True
