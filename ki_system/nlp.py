import re, json
from collections import Counter
from ki_system.text_utils import tokenize
from ki_system.wiki_quality import is_good_topic

def clean(v): return re.sub(r'\s+',' ',re.split(r'[.;:!?\n]',(v or '').strip())[0]).strip()[:160]
def _add(out,s,r,o,c=.7):
    s=clean(s).strip(', '); o=clean(o)
    if len(s)>1 and len(o)>1 and s.lower() not in {'ist','war','sind','wurde'}: out.append((s,r,o,float(c)))
def extract_relations(text, context_subject=None):
    out=[]; text=text or ''; first=re.split(r'(?<=[.!?])\s+', re.sub(r'\s+',' ',text).strip())[0] if text.strip() else ''
    subj=clean((context_subject or '').replace('_',' '))
    if subj:
        m=re.search(r'(?:ist|war)\s+(?:die\s+)?hauptstadt\s+(?:von|des|der)?\s*([^.;!?\n]{2,120})', first, re.I)
        if m: _add(out,subj,'is_a','Hauptstadt',.88); _add(out,subj,'capital_of',m.group(1),.82)
        m=re.search(r'(?:ist|war)\s+(?:eine|ein)\s+(stadt|gemeinde|ort|dorf|metropole|hafenstadt|staat|land|republik|observatorium|institut|zentrum)', first, re.I)
        if m: _add(out,subj,'is_a',m.group(1),.84)
        m=re.search(r'(?:ist|war|sind|waren)\s+(?:ein|eine|einen|einem|einer|eines|der|die|das)?\s*([^.;!?\n]{3,120})', first, re.I)
        if m and len(clean(m.group(1)).split())<=10: _add(out,subj,'is_a',m.group(1),.72)
    patterns=[('is_a',r'\b(?P<s>[A-ZÄÖÜA-Za-zÄÖÜäöüß][\wÄÖÜäöüß\- ]{1,80}?)\s+(?:ist|sind|war|waren)\s+(?:ein|eine|der|die|das)?\s*(?P<o>[^.;!?\n]{2,160})'),('definition',r'\b(?P<s>[A-ZÄÖÜA-Za-zÄÖÜäöüß][\wÄÖÜäöüß\- ]{1,80}?)\s+(?:bezeichnet|beschreibt)\s+(?P<o>[^.;!?\n]{2,160})'),('located_in',r'\b(?P<s>[A-ZÄÖÜA-Za-zÄÖÜäöüß][\wÄÖÜäöüß\- ]{1,80}?)\s+(?:liegt in|befindet sich in)\s+(?P<o>[^.;!?\n]{2,120})')]
    for rel,pat in patterns:
        for m in re.finditer(pat,text,re.I): _add(out,m.group('s'),rel,m.group('o'),.75)
    seen=set(); res=[]
    for x in out:
        k=(x[0].lower(),x[1],x[2].lower())
        if k not in seen: seen.add(k); res.append(x)
    return res
def learn_from_memory(memory,progress=None,cancel=None):
    rows=list(memory.iter_chunks()); stats={'facts':0,'relations':0,'ontology':0,'questions':0,'relations_seen':0}
    for i,row in enumerate(rows):
        if cancel and cancel(): break
        try: meta=json.loads(row['metadata_json'] or '{}'); ctx=meta.get('article') or row['title']
        except Exception: ctx=row['title']
        for s,r,o,c in extract_relations(row['text'],ctx):
            fid=memory.add_fact(s,r,o,c,row['id']); memory.add_relation(s,r,o,c,row['id']); stats['relations_seen']+=1
            if fid:
                stats['facts']+=1; stats['relations']+=1
                if r=='is_a': memory.add_ontology(s,o,'is_a',c,fid); stats['ontology']+=1
        added=0
        for t,_ in Counter(tokenize(row['text'])).most_common(12):
            if is_good_topic(t): memory.add_question(f'Was ist {t}?',.4); stats['questions']+=1; added+=1
            if added>=2: break
        if progress: progress(i+1,len(rows),f'Lernen {i+1}/{len(rows)}')
    memory.log('learn_from_memory',stats); return stats
def detect_contradictions(memory): return {'contradictions':0}
def build_clusters(memory,top_n=30,cluster_size=8): return []
