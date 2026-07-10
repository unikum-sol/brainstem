from dataclasses import dataclass
from collections import Counter
import json
from ki_system.text_utils import tokenize
from ki_system.search import semantic_search
from ki_system import nlp
from ki_system.wiki_quality import is_good_topic, is_good_topic_phrase, normalize_topic_from_question, topic_to_question
from ki_system.neuromodulators import NeuromodulatorManager
from ki_system.topic_affect import TopicAffect, normalize_topic, static_bad_topic
from ki_system.chunk_affect import ChunkAffect
from ki_system.extraction_diagnostics import seed_questions_from_extraction_diagnostics, run_extraction_diagnostics
from ki_system.relation_quality import filter_relations

@dataclass(slots=True)
class _Candidate:
    topic: str
    source: str
    score: float

class AutonomousLoop:
    def __init__(self, memory):
        self.memory = memory; self.cancel = False
        try: self.neuro = NeuromodulatorManager(memory)
        except Exception: self.neuro = None
        try: self.topic_affect = TopicAffect(memory)
        except Exception: self.topic_affect = None
        try: self.chunk_affect = ChunkAffect(memory)
        except Exception: self.chunk_affect = None
        self._ensure_indexes()
    def _ensure_indexes(self):
        if getattr(self.memory,'readonly',False): return
        try:
            with self.memory.lock:
                self.memory.db.execute('CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status)'); self.memory.db.commit()
        except Exception: pass
    def stop(self): self.cancel=True
    def _mark(self,qid,status):
        try: self.memory.update_question(qid,status)
        except Exception: pass
    def _behavior(self):
        if self.neuro:
            try: return self.neuro.behavior_modifiers()
            except Exception: pass
        return {'mode':'Ausgewogen','exploration':0.6,'precision':0.6,'filter_strictness':0.6,'cycle_factor':1.0,'attempt_factor':1.0,'state':{}}
    def _trend(self):
        if self.neuro:
            try: return self.neuro.trend_summary(30)
            except Exception: pass
        return {'trend':'Keine Historie','productivity_index':0.0,'fatigue_index':0.0,'overload_index':0.0,'stability_index':0.0,'totals':{}}
    def _no_ext_ratio(self,trend):
        totals=trend.get('totals') or {}; checked=int(totals.get('checked',0) or 0)
        return int(totals.get('no_extractable',0) or 0)/max(1,checked) if checked>0 else 0.0
    def _prefer_consolidation(self,behavior,trend):
        fatigue=float(trend.get('fatigue_index',0) or 0); prod=float(trend.get('productivity_index',0) or 0); overload=float(trend.get('overload_index',0) or 0); no_ratio=self._no_ext_ratio(trend)
        if behavior.get('mode')=='Schutz/Konsolidierung': return True,'Modus Schutz/Konsolidierung'
        if False and no_ratio>=0.985 and prod<0.03: return True, f'Extremer Leerlauf erkannt: no_extractable {no_ratio:.2f}, Produktivität {prod:.2f}'
        if fatigue>=0.78 and prod<0.04: return True, f'Müdigkeit sehr hoch ({fatigue:.2f}) und Produktivität sehr niedrig ({prod:.2f})'
        if overload>=0.72: return True,f'Überlastung hoch ({overload:.2f})'
        return False,'Lernmodus bevorzugt'
    def _effective_limits(self,cycles,behavior,trend):
        no_ratio=self._no_ext_ratio(trend); prod=float(trend.get('productivity_index',0) or 0)
        eff=max(1,int(round(cycles*behavior.get('cycle_factor',1.0)))); attempts=max(12,int(max(25,eff*10)*behavior.get('attempt_factor',1.0)))
        if no_ratio>=0.90 and prod<0.06: eff=min(eff,4); attempts=min(attempts,24)
        elif no_ratio>=0.80 and prod<0.10: eff=min(eff,3); attempts=min(attempts,22)
        return eff,attempts
    def _good_topic(self,topic):
        t=normalize_topic(topic)
        if static_bad_topic(t): return False
        if self.topic_affect and self.topic_affect.is_blocked(t): return False
        return is_good_topic(t)
    def _cleanup(self,limit=30000):
        n=0
        for r in self.memory.rows("SELECT id,question FROM questions WHERE status='open' LIMIT ?",(limit,)):
            topic=normalize_topic_from_question(r['question'])
            if not self._good_topic(topic):
                self._mark(r['id'],'low_quality_topic'); n+=1
                if self.topic_affect: self.topic_affect.update(topic,'low_quality_topic',no_extractable=1)
        return n
    def _existing(self): return {normalize_topic_from_question(r['question']) for r in self.memory.rows('SELECT question FROM questions LIMIT 500000')}
    def _title_topic(self,title,strictness=0.6):
        t=(title or '').replace('_',' ').split('#')[0].lower().strip()
        if ':' in t and t.split(':',1)[0] in {'datei','file','template','vorlage','kategorie','category','portal','wikipedia'}: return ''
        if '(' in t: t=t.split('(',1)[0].strip()
        parts=[p for p in tokenize(t) if p]
        if not parts: return ''
        phrase=' '.join(parts[:4])
        if strictness<0.88 and is_good_topic_phrase(phrase) and not (self.topic_affect and self.topic_affect.is_blocked(phrase)): return phrase
        for p in parts:
            if self._good_topic(p): return p
        return ''
    def generate_quality_questions(self,limit=120,strictness=0.6,exploration=0.6):
        existing=self._existing(); candidates=[]; title_limit=int(900+900*exploration)
        for r in self.memory.rows('SELECT metadata_json,COUNT(*) AS c FROM chunks GROUP BY metadata_json ORDER BY c DESC LIMIT ?',(title_limit,)):
            try: title=(json.loads(r['metadata_json'] or '{}').get('article') or '')
            except Exception: title=''
            topic=self._title_topic(title,strictness)
            if topic and topic not in existing:
                score=4+(r['c'] or 0)/20+(self.topic_affect.score_for(topic) if self.topic_affect else 0); candidates.append(_Candidate(topic,'article_title',score))
        best={}
        for c in candidates:
            if c.topic not in best or c.score>best[c.topic].score: best[c.topic]=c
        selected=sorted(best.values(),key=lambda x:x.score,reverse=True)[:limit]
        for c in selected: self.memory.add_question(topic_to_question(c.topic),.98)
        return {'created':len(selected),'selected':[{'topic':c.topic,'source':c.source,'score':c.score} for c in selected[:10]]}
    def _pick_open_question(self):
        try: rows=self.memory.rows("SELECT questions.*,COALESCE(topic_affect.score,0) AS tscore FROM questions LEFT JOIN topic_affect ON topic_affect.topic=lower(replace(replace(replace(questions.question,'Was ist ',''),'?',''),'_',' ')) WHERE questions.status='open' ORDER BY tscore DESC,priority DESC,questions.id ASC LIMIT 60")
        except Exception: rows=self.memory.open_questions(60)
        for q in rows:
            topic=normalize_topic_from_question(q['question'])
            if self._good_topic(topic): return q
            self._mark(q['id'],'low_quality_topic')
            if self.topic_affect: self.topic_affect.update(topic,'low_quality_topic',no_extractable=1)
        return None
    def _extractable(self,hits,topic,precision=0.6):
        prod=[]; max_hits=8 if precision>=0.85 else 12
        for h in hits[:max_hits]:
            if self.cancel: break
            try: rels=filter_relations(nlp.extract_relations(h.text,context_subject=topic or h.title), context_subject=topic or h.title)
            except Exception: rels=[]
            if rels: prod.append((h,rels))
            if len(prod)>=8: break
        return prod
    def _learn(self,prod,progress=None):
        stats={'facts':0,'relations':0,'ontology':0,'chunks':len(prod),'relations_seen':0}
        for i,(h,rels) in enumerate(prod,1):
            if progress: progress(i,max(1,len(prod)),f'Autonom Treffer {i}/{len(prod)}')
            before=self.memory.stats().get('facts',0)
            for s,r,o,c in rels:
                fid=self.memory.add_fact(s,r,o,c,h.chunk_id); self.memory.add_relation(s,r,o,c,h.chunk_id); stats['relations_seen']+=1
                if fid:
                    stats['facts']+=1; stats['relations']+=1
                    if r=='is_a': self.memory.add_ontology(s,o,'is_a',c,fid); stats['ontology']+=1
            if self.chunk_affect: self.chunk_affect.update(h.chunk_id,relations_seen=len(rels),new_facts=max(0,self.memory.stats().get('facts',before)-before))
        return stats
    def _chunk_context(self,row):
        try: return json.loads(row['metadata_json'] or '{}').get('article') or row['title'] or ''
        except Exception: return row['title'] or ''
    def _consolidation_pass(self,behavior,progress=None,limit=None):
        if limit is None: limit=180 if behavior.get('mode')=='Schutz/Konsolidierung' else 120
        rows=self.chunk_affect.candidate_chunks(limit) if self.chunk_affect else []
        if not rows: rows=self.memory.rows('SELECT chunks.id,chunks.text,chunks.metadata_json,documents.title,documents.path FROM chunks JOIN documents ON documents.id=chunks.document_id ORDER BY chunks.id DESC LIMIT ?',(limit,))
        stats={'checked_chunks':0,'relations_seen':0,'facts':0,'relations':0,'ontology':0}
        for i,row in enumerate(rows,1):
            if self.cancel: break
            if progress: progress(i,max(1,len(rows)),f'Autonome Konsolidierung {i}/{len(rows)}')
            try: rels=filter_relations(nlp.extract_relations(row['text'] or '',context_subject=self._chunk_context(row)), context_subject=self._chunk_context(row))
            except Exception: rels=[]
            stats['checked_chunks']+=1; stats['relations_seen']+=len(rels); before=self.memory.stats().get('facts',0)
            for s,r,o,c in rels:
                fid=self.memory.add_fact(s,r,o,c,row['id']); self.memory.add_relation(s,r,o,c,row['id'])
                if fid:
                    stats['facts']+=1; stats['relations']+=1
                    if r=='is_a': self.memory.add_ontology(s,o,'is_a',c,fid); stats['ontology']+=1
            if self.chunk_affect: self.chunk_affect.update(row['id'],relations_seen=len(rels),new_facts=max(0,self.memory.stats().get('facts',before)-before))
        return stats
    def _reseed_questions_from_chunks(self,limit=80):
        existing=self._existing(); made=0
        rows=self.memory.rows('SELECT chunks.id,chunks.text,chunks.metadata_json,documents.title FROM chunks JOIN documents ON documents.id=chunks.document_id ORDER BY chunks.id DESC LIMIT 2500')
        for row in rows:
            if self.cancel or made>=limit: break
            topic=self._title_topic(self._chunk_context(row),strictness=0.55)
            if topic and topic not in existing and self._good_topic(topic): self.memory.add_question(topic_to_question(topic),.72); existing.add(topic); made+=1; continue
            for tok,_ in Counter(tokenize(row['text'] or '')).most_common(18):
                if self._good_topic(tok) and tok not in existing: self.memory.add_question(topic_to_question(tok),.35); existing.add(tok); made+=1; break
        return made
    def _question_learning_pass(self,effective_cycles,max_attempts,behavior,progress=None):
        out=[]; summary={'checked':0,'productive':0,'new_facts':0,'already_known':0,'no_extractable':0,'no_sources':0,'bad_question':0,'errors':0}
        if self.memory.rows("SELECT COUNT(*) AS c FROM questions WHERE status='open'")[0]['c']<effective_cycles:
            gen=self.generate_quality_questions(max(60,int(effective_cycles*20)),behavior.get('filter_strictness',0.6),behavior.get('exploration',0.6)); out.append({'status':'generated_quality_questions','message':str(gen['created'])+' hochwertige neue Fragen erzeugt.','selected':gen.get('selected',[])})
            if gen['created']==0: out.append({'status':'reseed_questions','message':f'{self._reseed_questions_from_chunks(80)} Reserve-Fragen aus Chunks erzeugt.'})
        attempts=0; done=0
        while done<effective_cycles and attempts<max_attempts and not self.cancel:
            attempts+=1; q=self._pick_open_question()
            if not q:
                if self._reseed_questions_from_chunks(80)==0: break
                q=self._pick_open_question()
            if not q: break
            question=q['question']; topic=normalize_topic_from_question(question); summary['checked']+=1; self._mark(q['id'],'processing')
            try:
                hits=semantic_search(self.memory,question,8 if behavior.get('precision',0.6)>=0.9 else 12)
                if not hits: self._mark(q['id'],'no_sources'); summary['no_sources']+=1; self.topic_affect and self.topic_affect.update(topic,'no_sources',no_sources=1); continue
                prod=self._extractable(hits,topic,behavior.get('precision',0.6))
                if not prod: self._mark(q['id'],'no_extractable_relations'); summary['no_extractable']+=1; self.topic_affect and self.topic_affect.update(topic,'no_extractable',no_extractable=1); continue
                before=self.memory.stats().get('facts',0); learned=self._learn(prod,progress); new=max(0,self.memory.stats().get('facts',before)-before); status='done' if new else 'already_known'; self._mark(q['id'],status); summary['productive']+=1; summary['new_facts']+=new
                if not new: summary['already_known']+=1
                self.topic_affect and self.topic_affect.update(topic,status,new_facts=new,already_known=1 if not new else 0,relations_seen=learned.get('relations_seen',0))
                out.append({'question':question,'topic':topic,'hits':len(hits),'productive_hits':len(prod),'new_facts':new,'status':status,'topic_score':self.topic_affect.score_for(topic) if self.topic_affect else 0,'learn':learned}); done+=1
            except Exception as exc:
                self._mark(q['id'],'error'); summary['errors']+=1; self.topic_affect and self.topic_affect.update(topic,'error',errors=1); out.append({'question':question,'topic':topic,'status':'error','error':str(exc)})
        return out,summary,done,attempts
    def run(self,cycles=5,progress=None):
        behavior=self._behavior(); trend=self._trend(); prefer,reason=self._prefer_consolidation(behavior,trend); effective,max_attempts=self._effective_limits(cycles,behavior,trend)
        out=[{'status':'neuromodulated_behavior_phase3d6','message':f"Modus: {behavior.get('mode')} | Trend: {trend.get('trend')} | Entscheidung: {'Konsolidierung' if prefer else 'Lernen'} | Grund: {reason} | Limits: cycles={effective}, attempts={max_attempts}",'behavior':behavior,'trend':trend}]
        summary={'checked':0,'productive':0,'new_facts':0,'already_known':0,'no_extractable':0,'no_sources':0,'bad_question':0,'errors':0}
        cleaned=self._cleanup(); summary['bad_question']+=cleaned
        if cleaned: out.append({'status':'topic_quality_cleanup','message':f'{cleaned} schlechte offene Fragen auf low_quality_topic gesetzt.'})
        if prefer:
            cons=self._consolidation_pass(behavior,progress); out.append({'status':'autonomous_sleep_consolidation','message':f"Autonome Konsolidierung: Chunks geprüft {cons['checked_chunks']} | Relationen gesehen {cons['relations_seen']} | Neue Fakten {cons['facts']}",'learn':cons}); summary['productive']+=1 if cons['facts']>0 else 0; summary['new_facts']+=cons['facts']
        else:
            q_out,q_sum,done,_=self._question_learning_pass(effective,max_attempts,behavior,progress); out.extend(q_out)
            for k in summary: summary[k]+=q_sum.get(k,0)
            if False and summary['new_facts']==0 and (summary['productive']==0 or done<effective) and not self.cancel:
                cons=self._consolidation_pass(behavior,progress); out.append({'status':'autonomous_fallback_consolidation','message':f"Fallback-Konsolidierung: Chunks geprüft {cons['checked_chunks']} | Relationen gesehen {cons['relations_seen']} | Neue Fakten {cons['facts']}",'learn':cons}); summary['productive']+=1 if cons['facts']>0 else 0; summary['new_facts']+=cons['facts']
        affect_summary={}
        try:
            if self.topic_affect: affect_summary['topics']=self.topic_affect.summary(6)
            if self.chunk_affect: affect_summary['chunks']=self.chunk_affect.summary(6)
        except Exception as exc: affect_summary={'error':str(exc)}
        out.insert(0,{'status':'summary','message':f"Geprüfte Fragen: {summary['checked']} | Produktiv: {summary['productive']} | Neue Fakten: {summary['new_facts']} | Bereits bekannt: {summary['already_known']} | Ohne extrahierbare Relationen: {summary['no_extractable']} | Ohne Quellen: {summary['no_sources']}",'summary':summary,'affect_summary':affect_summary})
        try:
            mgr=NeuromodulatorManager(self.memory)
            if summary['new_facts']==0 and summary['productive']==0: mgr.apply_recovery_tick('phase3c1 idle/no-new-facts recovery')
            state=mgr.apply_autonomous_result(out); out.append({'status':'neuromodulators','message':mgr.short_status(),'state':state.as_dict(),'behavior_next':mgr.behavior_modifiers(),'trend_next':mgr.trend_summary(30) if hasattr(mgr,'trend_summary') else {}})
        except Exception as exc: out.append({'status':'neuromodulators_error','message':str(exc)})
        
        # PHASE3D1_EXTRACTION_DIAGNOSTICS: Diagnose und Frage-Reseed bei Leerlauf
        try:
            if summary.get('new_facts', 0) == 0:
                diag_seed = seed_questions_from_extraction_diagnostics(self.memory, limit=36)
                out.append({'status':'extraction_diagnostics_phase3d1','message':f"Diagnose: Relationen gesehen {diag_seed.get('diagnostics',{}).get('relations_seen',0)} | bekannt {diag_seed.get('diagnostics',{}).get('known_relations',0)} | potentiell neu {diag_seed.get('diagnostics',{}).get('potentially_new_relations',0)} | neue Fragen {diag_seed.get('created',0)}",'diagnostics':diag_seed})
        except Exception as exc:
            out.append({'status':'extraction_diagnostics_phase3d1_error','message':str(exc)})
        self.memory.log('autonomous_learning',out); return out

# PHASE3C2_ANTI_CONSOLIDATION_LOCK: anti-lock calibration installed

# PHASE3C3_FORCE_LEARNING_PROBE: historical idle no longer forces permanent consolidation

# PHASE3C4_ANTI_FALLBACK_LOOP: fallback consolidation disabled after failed learning probe

# PHASE3D2_RELATION_QUALITY_GATE enabled

# PHASE3D3_STRICT_RELATION_TOPIC_GATE enabled

# PHASE3D4_PREPOSITION_FRAGMENT_GATE enabled

# PHASE3D5_IS_A_DEFINITION_GATE enabled

# PHASE3D6_SUBJECT_ALIGNMENT_GATE enabled

# >>> CENTRAL_PHASE_REGISTRY (refactored patch loader) >>>
# Ersetzt den frueheren langen Monkey-Patch-Block. Reihenfolge & Aufrufe: ki_system/phase_registry.py
try:
    from ki_system.phase_registry import load_all as _load_all_phases
    _BRAINSTEM_LOAD_REPORT = _load_all_phases(globals(), AutonomousLoop)
except Exception as _phase_registry_exc:
    import traceback as _tb
    print('[PHASE_REGISTRY_LOAD_ERROR]', _phase_registry_exc); _tb.print_exc()
# <<< CENTRAL_PHASE_REGISTRY (refactored patch loader) <<<
