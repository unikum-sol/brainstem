import re
ALLOW_SHORT_TOPICS={'china','japan','venus','erde','mond','sonne','mars','paris','rom','atom','stern','linux','sqlite','theater'}
WIKI_NOISE_EXACT=set('infobox sidebar navbox metadata template vorlage kategorie category commons wikimedia wikipedia wikidata mediawiki bearbeiten quelltext weiterleitung redirect navigation portal einzelnachweise belege quellen links siehe literatur weblink weblinks creative attribution license lizenz datei file image bild thumb webarchive isbn issn doi pmid arxiv gnd viaf lccn jstor style class span website html http https www wurde wurden werden hatte haben kann können sowie dabei auch oder eine einer eines über ueber unter nach zwischen beispiel verschiedene bestimmungen mittlerer herausgegeben wartung abmessungen benannt entdeckt tätig taetig lösung loesung einheiten prozent datenbank journal zehntausend hundert tausend million millionen staaten vereinigte volksrepublik republik chinesisch deutsch englisch micha owski philkeenan hannaharendt'.split())
BAD_SUFFIXES=('keit','igkeit','ungen','tion','tionen','istisch','ische','ischer','isches','isch')
GOOD_SUFFIXES=('logie','physik','chemie','biologie','technik','system','theorie','modell','methode','struktur','maschine','element','energie','planet','stern','atom','zelle','mechanik','medizin','musik','kunst','geschichte','software','observatorium')
NAME_LIKE_RE=re.compile(r'^[a-zäöüß]+(?:-[a-zäöüß]+)?$')
def normalize_topic_from_question(question):
    q=(question or '').strip().strip('?!.'); low=q.lower()
    for p in ('was ist ','wer ist ','was sind ','wer sind ','was bedeutet '):
        if low.startswith(p): return q[len(p):].strip().strip('?!.').lower()
    return low
def _basic_word_ok(t):
    if len(t)<4 or len(t)>40 or any(c.isdigit() for c in t) or '_' in t or '/' in t or '\\' in t or t.startswith('-') or t.endswith('-') or t.count('-')>1: return False
    if not t.replace('-','').isalpha(): return False
    if sum(1 for c in t if c in 'aeiouäöüy')==0 and len(t)>6: return False
    return bool(NAME_LIKE_RE.match(t))
def _bad_frag(t):
    if t in ALLOW_SHORT_TOPICS: return False
    return len(t)<=5 or (len(t)<=8 and any(t.endswith(s) for s in ('owski','ewski','ski','son','sen')))
def is_good_topic(term):
    t=(term or '').strip().lower().strip('.,;:!?()[]{}"\'')
    if ' ' in t: return is_good_topic_phrase(t)
    if len(t)<5 or len(t)>55 or t in WIKI_NOISE_EXACT or _bad_frag(t) or not _basic_word_ok(t): return False
    if len(t)<=10 and t.endswith(BAD_SUFFIXES) and not t.endswith(GOOD_SUFFIXES): return False
    return True
def is_good_topic_phrase(phrase):
    p=' '.join((phrase or '').lower().replace('_',' ').split()).strip('.,;:!?()[]{}"\'')
    parts=[x.strip('-') for x in p.split() if x.strip('-')]
    if len(p)<8 or len(p)>80 or not (2<=len(parts)<=4): return False
    return all(_basic_word_ok(x) for x in parts)
def topic_to_question(topic): return f'Was ist {topic.strip().lower()}?'
def clean_wikipedia_text(text):
    lines=[]
    for raw in (text or '').splitlines():
        line=' '.join(raw.split()).strip()
        if not line or len(line)<3: continue
        if re.search(r'einzelnachweise|weblinks|siehe auch|creative commons|wikimedia|wikidata|isbn|doi|webarchive|bearbeiten|quelltext', line, re.I): continue
        lines.append(line)
    return '\n'.join(lines)

# PHASE3D7_QUESTION_GUARD_WIKI_QUALITY
try:
    from ki_system.question_guard import is_good_topic as _qg_is_good_topic, topic_to_question as _qg_topic_to_question, normalize_topic_from_question as _qg_normalize_topic_from_question
    is_good_topic = _qg_is_good_topic
    topic_to_question = _qg_topic_to_question
    normalize_topic_from_question = _qg_normalize_topic_from_question
except Exception:
    pass
