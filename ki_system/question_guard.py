from __future__ import annotations
import re
BAD_TOPICS = {
 'größer','groesser','kleine','kleiner','bekannt','bekannte','bekannter','jedoch','aber','und','oder','sowie','dabei','dadurch','damit','dies','diese','dieser','dieses','andere',
 'cm-flak','cm-gebirgshaubitze 40','gecs','days','reasons','reason','da 02','da 20','da 2','10+2','cover','cover des albums','auf dem cover des albums',
 'der text','creative commons','begriffsklärungsseite','begriffsklaerungsseite','deutsch','1/deutsch','german artillery of world','the encyclopedia of weapons of world',
 'verfügbar unter creative commons attribution-share alike 4','verfuegbar unter creative commons attribution-share alike 4','modus die 24 mannschaften','in zwei gruppen zu je 12 teams eingeteilt'
}
BAD_PARTS = ('creative commons','attribution-share alike','verfügbar unter','verfuegbar unter','encyclopedia of weapons','german artillery of world','begriffsklärungsseite','begriffsklaerungsseite','unterscheidung mehrerer','auf dem cover','cover des albums','zu je 12 teams','in zwei gruppen','modus die','uhrenwerke gebr','zentrale plattform','horizontal gelagerte munition')
BAD_PREFIXES = ('bei ','vor ','im ','in ','an ','auf ','aus ','mit ','für ','fuer ','von ','nach ','unten ','oben ','cover ','der text','die liste','technische beschreibung','museale rezeption','the encyclopedia of ','german artillery of ','world war ','auch die ','dadurch ','dabei ')
BAD_SINGLE_WORDS = {'ist','war','hat','hatte','wurde','wurden','sein','sind','sehr','nur','fast','auch','noch','mehr','wenig','viel','alt','neu'}
ALLOWED_SYMBOL_TOPIC_RE = re.compile(r'^(?:\d+[,.]?\d*[- ]?cm[- ][\wÄÖÜäöüß.]+|\d+[/][\w\-]+|\d{1,3},\d{3} .+|\d+[,.]?\d*\s+[A-Za-zÄÖÜäöüß].+)$', re.U)
DA_CODE_RE = re.compile(r'^da\s*\d{1,3}\.?$', re.I)

def normalize_text(x: str | None) -> str:
    return ' '.join((x or '').strip().replace('_',' ').split())
def normalize_topic(topic: str | None) -> str:
    return normalize_text(topic).lower()
def normalize_topic_from_question(question: str | None) -> str:
    q=normalize_text(question); low=q.lower()
    m=re.match(r'^(?:was|wer)\s+ist\s+(.+?)\??$', low, re.I)
    return normalize_topic(m.group(1)) if m else normalize_topic(q)
def is_bad_topic(topic: str | None) -> bool:
    t=normalize_topic(topic)
    if not t or t in BAD_TOPICS or t in BAD_SINGLE_WORDS: return True
    if DA_CODE_RE.match(t): return True
    if any(part in t for part in BAD_PARTS): return True
    if any(t.startswith(p) for p in BAD_PREFIXES): return True
    if t.startswith('cm-'): return True
    if len(t)<4 or len(t)>85 or len(t.split())>7: return True
    if any(ch in t for ch in ['+','/']) and not ALLOWED_SYMBOL_TOPIC_RE.match(t): return True
    return False
def is_good_topic(topic: str | None) -> bool: return not is_bad_topic(topic)
def is_good_question(question: str | None) -> bool: return is_good_topic(normalize_topic_from_question(question))
def topic_to_question(topic: str) -> str: return f"Was ist {normalize_text(topic)}?"
def classify_question(question: str | None):
    topic=normalize_topic_from_question(question)
    return (False, topic, 'low_quality_topic') if is_bad_topic(topic) else (True, topic, 'ok')
