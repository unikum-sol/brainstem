from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import re
import time

BASELINE={
    'dopamine':0.50,'serotonin':0.60,'glutamate':0.40,'gaba':0.40,'noradrenaline':0.30,'acetylcholine':0.50,
}
SOFT_LIMITS={name:(0.05,0.95) for name in BASELINE}
LABELS={'dopamine':'DA','serotonin':'5-HT','glutamate':'GLU','gaba':'GABA','noradrenaline':'NA','acetylcholine':'ACh'}
COLORS={'dopamine':'#f4c542','serotonin':'#3fbf7f','glutamate':'#ef6c4f','gaba':'#5b7cfa','noradrenaline':'#9b5de5','acetylcholine':'#00bcd4'}

def clamp(value, low=0.0, high=1.0): return max(low, min(high, float(value)))

@dataclass(slots=True)
class NeuromodulatorState:
    dopamine:float=BASELINE['dopamine']
    serotonin:float=BASELINE['serotonin']
    glutamate:float=BASELINE['glutamate']
    gaba:float=BASELINE['gaba']
    noradrenaline:float=BASELINE['noradrenaline']
    acetylcholine:float=BASELINE['acetylcholine']
    def bounded(self, soft:bool=True)->'NeuromodulatorState':
        for name in BASELINE:
            lo,hi=SOFT_LIMITS.get(name,(0.0,1.0)) if soft else (0.0,1.0)
            setattr(self,name,clamp(getattr(self,name),lo,hi))
        return self
    def as_dict(self)->dict: return asdict(self)

class NeuromodulatorManager:
    def __init__(self,memory):
        self.memory=memory; self._ensure_tables(); self._ensure_state()
    def _ensure_tables(self):
        if getattr(self.memory,'readonly',False): return
        sql=("CREATE TABLE IF NOT EXISTS neuromodulator_state(id INTEGER PRIMARY KEY CHECK(id=1),dopamine REAL,serotonin REAL,glutamate REAL,gaba REAL,noradrenaline REAL,acetylcholine REAL,updated_at INTEGER);"
             "CREATE TABLE IF NOT EXISTS neuromodulator_events(id INTEGER PRIMARY KEY,event TEXT,delta_json TEXT,reason TEXT,state_json TEXT,created_at INTEGER);")
        with self.memory.lock:
            self.memory.db.executescript(sql); self.memory.db.commit()
    def _ensure_state(self):
        if getattr(self.memory,'readonly',False): return
        row=self.memory.rows('SELECT COUNT(*) AS c FROM neuromodulator_state WHERE id=1')[0]
        if row['c']==0:
            s=NeuromodulatorState().bounded()
            with self.memory.lock:
                self.memory.db.execute('INSERT INTO neuromodulator_state(id,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,updated_at) VALUES(?,?,?,?,?,?,?,?)',(1,s.dopamine,s.serotonin,s.glutamate,s.gaba,s.noradrenaline,s.acetylcholine,int(time.time())))
                self.memory.db.commit()
    def get_state(self)->NeuromodulatorState:
        try:
            rows=self.memory.rows('SELECT * FROM neuromodulator_state WHERE id=1')
            if rows:
                r=rows[0]
                return NeuromodulatorState(r['dopamine'],r['serotonin'],r['glutamate'],r['gaba'],r['noradrenaline'],r['acetylcholine']).bounded()
        except Exception: pass
        return NeuromodulatorState().bounded()
    def _save_state(self,s:NeuromodulatorState):
        if getattr(self.memory,'readonly',False): return
        s.bounded()
        with self.memory.lock:
            self.memory.db.execute('UPDATE neuromodulator_state SET dopamine=?,serotonin=?,glutamate=?,gaba=?,noradrenaline=?,acetylcholine=?,updated_at=? WHERE id=1',(s.dopamine,s.serotonin,s.glutamate,s.gaba,s.noradrenaline,s.acetylcholine,int(time.time())))
            self.memory.db.commit()
    def adaptive_homeostasis(self,s:NeuromodulatorState,base_strength:float=0.045)->NeuromodulatorState:
        for name,base in BASELINE.items():
            value=getattr(s,name); distance=abs(value-base); strength=base_strength+min(0.12,distance*0.18)
            setattr(s,name,value*(1.0-strength)+base*strength)
        return s.bounded()
    def apply_event(self,event:str,delta=None,reason:str='')->NeuromodulatorState:
        if getattr(self.memory,'readonly',False): return self.get_state()
        delta=delta or {}; s=self.adaptive_homeostasis(self.get_state())
        for name,change in delta.items():
            if name in BASELINE: setattr(s,name,getattr(s,name)+float(change))
        s=self.adaptive_homeostasis(s,base_strength=0.025).bounded(); self._save_state(s)
        with self.memory.lock:
            self.memory.db.execute('INSERT INTO neuromodulator_events(event,delta_json,reason,state_json,created_at) VALUES(?,?,?,?,?)',(event,json.dumps(delta,ensure_ascii=False),reason,json.dumps(s.as_dict(),ensure_ascii=False),int(time.time())))
            self.memory.db.commit()
        return s
    def apply_recovery_tick(self,reason:str='recovery_tick')->NeuromodulatorState:
        return self.apply_event('recovery_tick',{},reason)
    def apply_autonomous_result(self,result:list)->NeuromodulatorState:
        summary={}
        for item in result or []:
            if isinstance(item,dict) and item.get('status')=='summary': summary=item.get('summary') or {}; break
        checked=int(summary.get('checked',0) or 0); productive=int(summary.get('productive',0) or 0); new_facts=int(summary.get('new_facts',0) or 0); already_known=int(summary.get('already_known',0) or 0); no_extractable=int(summary.get('no_extractable',0) or 0); errors=int(summary.get('errors',0) or 0)
        delta={}; reason=f'autonom: checked={checked}, productive={productive}, new_facts={new_facts}, already_known={already_known}, no_extractable={no_extractable}, errors={errors}'
        productive_ratio=productive/max(1,checked); no_ratio=no_extractable/max(1,checked)
        if new_facts>0:
            delta['dopamine']=min(0.08,0.018*new_facts); delta['glutamate']=min(0.05,0.008*new_facts); delta['serotonin']=min(0.035,0.006*new_facts); delta['gaba']=-min(0.045,0.010*new_facts); delta['acetylcholine']=0.010
        elif productive>0:
            delta['serotonin']=0.018; delta['acetylcholine']=0.018; delta['gaba']=-0.020; delta['dopamine']=-0.004 if already_known>=productive else 0.006
        elif checked>0 and no_ratio>=0.75:
            delta['gaba']=0.030; delta['dopamine']=-0.018; delta['glutamate']=-0.014; delta['acetylcholine']=0.006
        else: delta['serotonin']=0.006
        if checked>0 and productive_ratio>=0.30:
            delta['gaba']=delta.get('gaba',0.0)-0.015; delta['acetylcholine']=delta.get('acetylcholine',0.0)+0.012
        if errors>0:
            delta['noradrenaline']=delta.get('noradrenaline',0.0)+min(0.08,0.025*errors); delta['serotonin']=delta.get('serotonin',0.0)-min(0.05,0.015*errors); delta['gaba']=delta.get('gaba',0.0)+min(0.04,0.012*errors)
        return self.apply_event('autonomous_result_phase2',delta,reason)
    def behavior_modifiers(self)->dict:
        s=self.get_state()
        exploration=clamp(0.45+s.dopamine*0.55+s.glutamate*0.35-s.gaba*0.35,0.15,1.20)
        precision=clamp(0.45+s.acetylcholine*0.45+s.gaba*0.15+s.serotonin*0.10,0.25,1.25)
        filter_strictness=clamp(0.45+s.gaba*0.45+s.noradrenaline*0.15-s.dopamine*0.20,0.25,1.15)
        cycle_factor=clamp(0.75+s.dopamine*0.45+s.glutamate*0.25-s.gaba*0.25,0.50,1.35)
        attempt_factor=clamp(0.85+s.acetylcholine*0.25-s.gaba*0.20+s.serotonin*0.10,0.55,1.25)
        if s.gaba>0.78 and s.dopamine<0.25: mode='Schutz/Konsolidierung'
        elif exploration>0.85: mode='Exploration'
        elif precision>0.85: mode='Präzision'
        else: mode='Ausgewogen'
        return {'mode':mode,'exploration':exploration,'precision':precision,'filter_strictness':filter_strictness,'cycle_factor':cycle_factor,'attempt_factor':attempt_factor,'state':s.as_dict()}
    def mood_state(self)->dict:
        s=self.get_state(); b=self.behavior_modifiers()
        if s.noradrenaline>=0.70 and s.serotonin<=0.45: return {'emoji':'(!o!)','name':'Alarm/Unsicher','reason':'viel Alarm bei niedriger Stabilität'}
        if s.glutamate>=0.72 and s.noradrenaline>=0.55: return {'emoji':'(@_@)','name':'Überlastet','reason':'hohe Aktivierung und hoher Alarm'}
        if s.serotonin<=0.32 and s.dopamine<=0.32 and s.glutamate<=0.32: return {'emoji':'(u_u)','name':'Müde','reason':'niedrige Stabilität, Motivation und Lernaktivierung'}
        if s.gaba>=0.78 and s.dopamine<=0.28: return {'emoji':'(-_-)','name':'Schutz/Konsolidierung','reason':'hohe Bremse bei niedriger Motivation'}
        if s.dopamine<=0.25 and s.glutamate<=0.28: return {'emoji':'(._-)','name':'Träge','reason':'niedrige Motivation und Lernaktivierung'}
        if s.dopamine>=0.62 and s.acetylcholine>=0.55 and s.gaba<=0.55: return {'emoji':'(^o^)','name':'Produktiv','reason':'Motivation/Fokus hoch, Bremse niedrig'}
        if s.dopamine>=0.62 and s.glutamate>=0.52: return {'emoji':'(o_o)','name':'Explorativ','reason':'hohe Motivation und Lernaktivierung'}
        if s.acetylcholine>=0.68 or b.get('precision',0.0)>=0.84: return {'emoji':'(._.)','name':'Fokussiert','reason':'hoher Fokus/hohe Präzision'}
        return {'emoji':'(^_^)','name':'Ausgewogen','reason':'keine kritischen Ausschläge'}
    def short_status(self)->str:
        s=self.get_state(); return f"DA {s.dopamine:.2f} | 5-HT {s.serotonin:.2f} | GLU {s.glutamate:.2f} | GABA {s.gaba:.2f} | NA {s.noradrenaline:.2f} | ACh {s.acetylcholine:.2f}"

    # ---------------- Phase 3a: Trendgedächtnis ----------------
    def recent_events(self, limit:int=30)->list:
        try:
            rows=self.memory.rows('SELECT event,delta_json,reason,state_json,created_at FROM neuromodulator_events ORDER BY id DESC LIMIT ?', (int(limit),))
        except Exception:
            return []
        events=[]
        for r in reversed(rows):
            try: state=json.loads(r['state_json'] or '{}')
            except Exception: state={}
            try: delta=json.loads(r['delta_json'] or '{}')
            except Exception: delta={}
            events.append({'event':r['event'],'delta':delta,'reason':r['reason'] or '', 'state':state, 'created_at':r['created_at']})
        return events
    def _extract_metric(self, reason:str, name:str)->int:
        m=re.search(rf'{re.escape(name)}\s*=\s*(-?\d+)', reason or '')
        return int(m.group(1)) if m else 0
    def trend_summary(self, limit:int=30)->dict:
        events=self.recent_events(limit)
        if not events:
            s=self.get_state(); return {'status':'Keine Historie','events':0,'trend':'neutral','productivity_index':0.0,'fatigue_index':0.0,'overload_index':0.0,'stability_index':round(s.serotonin,3),'delta':{},'recommendation':'Erst einige autonome Zyklen sammeln.'}
        first=events[0].get('state') or {}; last=events[-1].get('state') or self.get_state().as_dict()
        delta={name:round(float(last.get(name,BASELINE[name]))-float(first.get(name,BASELINE[name])),4) for name in BASELINE}
        totals={'checked':0,'productive':0,'new_facts':0,'no_extractable':0,'errors':0,'already_known':0}
        for e in events:
            reason=e.get('reason','')
            for name in totals: totals[name]+=self._extract_metric(reason,name)
        checked=max(1,totals['checked'])
        productivity_index=clamp((totals['new_facts']*1.0 + totals['productive']*0.35)/checked,0.0,1.0)
        fatigue_index=clamp((totals['no_extractable']/checked)*0.65 + max(0.0, float(last.get('gaba',0.4))-0.4)*0.60 + max(0.0,0.45-float(last.get('dopamine',0.5)))*0.55,0.0,1.0)
        overload_index=clamp(float(last.get('noradrenaline',0.3))*0.45 + float(last.get('glutamate',0.4))*0.35 + max(0.0,0.45-float(last.get('serotonin',0.6)))*0.65 + totals['errors']*0.04,0.0,1.0)
        stability_index=clamp(float(last.get('serotonin',0.6))*0.60 + (1.0-abs(float(last.get('gaba',0.4))-0.45))*0.25 + (1.0-overload_index)*0.15,0.0,1.0)
        if overload_index>=0.70: trend='Überlastung steigt'; rec='Fehler/Konflikte prüfen, autonomes Lernen kurz bremsen.'
        elif fatigue_index>=0.70: trend='Erschöpfung/Leerlauf'; rec='Konsolidierung oder neue Quellen/Artikel importieren.'
        elif productivity_index>=0.25: trend='Produktiv'; rec='Autonomes Lernen kann weiterlaufen.'
        elif stability_index>=0.68: trend='Stabil'; rec='Normalbetrieb.'
        else: trend='Neutral'; rec='Weiter beobachten.'
        return {'status':'OK','events':len(events),'trend':trend,'productivity_index':round(productivity_index,3),'fatigue_index':round(fatigue_index,3),'overload_index':round(overload_index,3),'stability_index':round(stability_index,3),'totals':totals,'delta':delta,'recommendation':rec}
    def trend_status_line(self)->str:
        t=self.trend_summary(30)
        return f"Trend: {t.get('trend')} | Prod {t.get('productivity_index'):.2f} | Müdigkeit {t.get('fatigue_index'):.2f} | Überlast {t.get('overload_index'):.2f} | Stabil {t.get('stability_index'):.2f}"
