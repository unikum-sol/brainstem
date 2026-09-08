from dataclasses import dataclass
from collections import Counter
import json, re
from ki_system.text_utils import tokenize, cosine, sentences
from ki_system.wiki_quality import clean_wikipedia_text
@dataclass(slots=True)
class Hit: chunk_id:int; title:str; path:str; score:float; text:str; method:str
def hit_dict(h): return {'chunk_id':h.chunk_id,'title':h.title,'path':h.path,'score':round(float(h.score),4),'text':h.text,'method':h.method}
def _terms(q): return tokenize(q)
def _phrase(q): return ' '.join(_terms(q)).lower().strip()
def _clean(t):
    return re.sub(r'\s+', ' ', clean_wikipedia_text(t or '')).strip()
def semantic_search(memory,query,limit=20,kind=None):
    query=(query or '').strip(); hits=[]; seen=set(); terms=_terms(query); fts=' OR '.join(terms[:12])
    if fts:
        try:
            for r in memory.fts_search(fts,limit*3):
                h=Hit(r['rowid'],r['title'],r['path'],1/(1+abs(float(r['score'] or 0))),_clean(r['text']),'fts')
                hits.append(h); seen.add(h.chunk_id)
        except Exception: pass
    qph=_phrase(query)
    if qph:
        like=f'%{qph}%'
        try:
            rows=memory.rows('SELECT chunks.id AS id,chunks.text AS text,chunks.metadata_json AS metadata_json,documents.title AS title,documents.path AS path FROM chunks JOIN documents ON documents.id=chunks.document_id WHERE lower(chunks.text) LIKE ? OR lower(chunks.metadata_json) LIKE ? LIMIT ?',(like,like,limit*3))
            for r in rows:
                if r['id'] in seen: continue
                try: meta=json.loads(r['metadata_json'] or '{}')
                except Exception: meta={}
                art=(meta.get('article') or '').replace('_',' ').lower(); score=2.0 if qph in art else 1.0
                hits.append(Hit(r['id'],r['title'],r['path'],score,_clean(r['text']),'phrase')); seen.add(r['id'])
        except Exception: pass
    if len(hits)<limit:
        qc=Counter(terms)
        for r in memory.iter_chunks():
            if r['id'] in seen: continue
            txt=_clean(r['text']); sim=cosine(qc,Counter(tokenize(txt)))
            if sim>0: hits.append(Hit(r['id'],r['title'],r['path'],sim,txt,'semantic'))
    return sorted(hits,key=lambda h:h.score,reverse=True)[:limit]
def summarize(hits,query,max_sentences=6):
    out=[]; ql=_phrase(query)
    for h in hits:
        for s in sentences(h.text):
            sc=sum(1 for t in _terms(query) if t in s.lower())+(1 if ql and ql in s.lower() else 0)
            if sc: out.append({'score':sc,'source':h.title,'chunk_id':h.chunk_id,'sentence':s})
    return sorted(out,key=lambda x:x['score'],reverse=True)[:max_sentences]
def answer(memory,question):
    hits=semantic_search(memory,question,12)
    if not hits: return {'answer':'Keine passenden lokalen Quellen gefunden.','sources':[],'summary':[]}
    summ=summarize(hits,question,6)
    good=[x for x in summ if x['score']>=1]
    ans=' '.join(x['sentence'] for x in good[:3]) if good else 'Ich habe lokale Treffer gefunden, aber keine eindeutige Definition in den besten Treffern erkannt. Die besten Quellen enthalten eher Erwähnungen oder Quellen-/Listenabschnitte.'
    return {'answer':ans,'sources':[hit_dict(h) for h in hits[:5]],'summary':summ,'facts_first':False}
