import re, html, math
from collections import Counter
STOP=set('der die das den dem des ein eine einer eines einem einen und oder aber auch sowie ist sind war waren wurde wurden werden im in am an auf aus mit von vom zur zum über ueber unter für fuer nicht als bei nach wie dann'.split())
def strip_html(text):
    text=html.unescape(text or '')
    text=re.sub(r'<script.*?</script>|<style.*?</style>',' ',text,flags=re.S|re.I)
    text=re.sub(r'<[^>]+>',' ',text)
    return re.sub(r'\s+',' ',text).strip()
def tokenize(text):
    toks=re.findall(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9\-]{1,}',(text or '').lower())
    return [t for t in toks if t not in STOP and len(t)>1]
def counter(text): return Counter(tokenize(text))
def cosine(a,b):
    if not a or not b: return 0.0
    dot=sum(a[k]*b.get(k,0) for k in a)
    na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0.0
def sentences(text):
    return [p.strip() for p in re.split(r'(?<=[.!?])\s+', (text or '').strip()) if len(p.strip())>20]
def sentence_score(s,q): return cosine(counter(s),q)
