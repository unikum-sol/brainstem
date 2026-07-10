from __future__ import annotations
import json, re, time
from collections import Counter

WORD_RE = re.compile(r'[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9+.#-]*')
COLOR_WORDS = {'rot','grün','gruen','blau','gelb','schwarz','weiß','weiss','grau','orange','violett','lila','braun','pink','cyan','magenta','red','green','blue','yellow','black','white','gray','grey','purple','brown'}
STOP_OBJECTS = {'der','die','das','ein','eine','einer','eines','mit','bei','zu','von','für','fuer','als','und','oder','poker','sex','linux','casino','broome'}
BAD_OBJECT_PHRASES = (
    'nicht erforderlich','nicht möglich','nicht moeglich','nicht notwendig','nicht zulässig','nicht zulaessig','nicht gestattet',
    'nicht unumstritten','nicht dazu gedacht','nicht vorhanden','noch kein weg bekannt','zu beginn leer','zeit aktiv','seitdem gestattet',
    'dabei ','damit ','deshalb ','und dass','und heute','also nicht','zu nennen','bisher nicht bekannt','offiziell notwendig',
    'berechtigt, eine','gegenüber dem normalen','gegenueber dem normalen','dazu nicht zugelassen', 'verfügbar', 'verfuegbar'
)
BAD_SUBJECT_EXACT = {'neu','heute','bekannt','was','allerdings','beliebt','insbesondere','zunächst','zunaechst','nachfolger','als eigenschaften'}
BAD_SUBJECT_PREFIXES = (
    'seit ','anfang ','mitte ','ende ','bis dahin','zu beginn','ein wohnsitz','eine niederlassung','ein lokaler wohnsitz',
    'insbesondere ein wohnsitz','die folgenden','folgende','weitere','einer der','eine der','eines der','eigenschaften ',
    'nur staatsbürger','nur staatsbuerger','einzig die veröffentlichung','einzig die veroeffentlichung','generische begriffe',
    'die verwendung','verbreitung nach offiziellen angaben','second-level-domains folgende','die erste kommerziell',
    'diese version','innerhalb dieses containers'
)
LOCATION_SUBJECT_HINTS = ('sitz','zentrale','hauptsitz','standort')
PROPERTY_SUBJECT_HINTS = ('farbe','hintergrundfarbe','color','größe','groesse','geschwindigkeit','leistung','auflösung','aufloesung','höhe','hoehe','breite','temperatur','spannung','frequenz','takt','gewicht','anzahl','codename','name')
TECH_HINTS = ('diagramm','protokoll','framework','software','programm','betriebssystem','prozessor','mikroprozessor','dateiformat','format','standard','algorithmus','architektur','netzwerk','datenbank','sprache','bibliothek','schnittstelle','system','domain','server','client','cpu','gpu','unternehmen','projekt')
SAFE_REJECT_REASONS_FOR_REPAIR = {'prune_object_too_short','too_short','too_short_object'}
RISKY_REPAIR_REASONS = {'repair_short_definition_candidate','repair_location_relation','repair_property_value','repair_name_property','repair_color_property'}


def norm_text(v): return ' '.join(str(v or '').replace('_',' ').split()).strip()
def norm_key(v): return norm_text(v).lower()[:180]
def relation_key(v): return norm_text(v).lower().replace(' ','_')[:80]
def tokens(v): return [t.lower() for t in WORD_RE.findall(norm_text(v))]
def token_count(v): return len(tokens(v))
def has_bad_object(obj):
    o=norm_key(obj)
    return o in STOP_OBJECTS or any(p in o for p in BAD_OBJECT_PHRASES) or any(o.endswith(s) for s in (' des',' der',' die',' das',' von',' für',' fuer',' mit',' bei',' zu',' als',' und',' oder','(', '[', '{', ':'))
def has_bad_subject(subj):
    s=norm_key(subj)
    return s in BAD_SUBJECT_EXACT or any(s.startswith(p) for p in BAD_SUBJECT_PREFIXES) or (norm_text(subj)[:1].islower() and token_count(subj)>2) or token_count(subj)>11 or (' und ' in s and token_count(subj)>5)
def has_tech_hint(subj): return any(h in norm_key(subj) for h in TECH_HINTS)
def has_property_hint(subj): return any(h in norm_key(subj) for h in PROPERTY_SUBJECT_HINTS)
def has_location_hint(subj): return any(h in norm_key(subj) for h in LOCATION_SUBJECT_HINTS)

class RelationRepairer:
    VERSION='phase3d6l1_relation_repair_safety_fix'
    def __init__(self, memory):
        self.memory=memory; self.ensure_schema(); self.state=self.load_state()
    def ensure_schema(self):
        with self.memory.lock:
            db=self.memory.db
            db.execute("CREATE TABLE IF NOT EXISTS relation_repair_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at INTEGER)")
            db.execute("""CREATE TABLE IF NOT EXISTS relation_repair_events(id INTEGER PRIMARY KEY AUTOINCREMENT,candidate_id INTEGER,subject TEXT,old_relation TEXT,object TEXT,new_relation TEXT,old_status TEXT,new_status TEXT,candidate_type TEXT,reason TEXT,confidence REAL,created_at INTEGER)""")
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_relations'").fetchone():
                cols={r['name'] for r in db.execute('PRAGMA table_info(candidate_relations)').fetchall()}
                for col, ddl in {'candidate_type':'TEXT','repaired_relation':'TEXT','repair_reason':'TEXT','repair_confidence':'REAL DEFAULT 0','original_relation':'TEXT','original_object':'TEXT'}.items():
                    if col not in cols: db.execute(f'ALTER TABLE candidate_relations ADD COLUMN {col} {ddl}')
            db.commit()
    def load_state(self):
        row=self.memory.db.execute("SELECT value_json FROM relation_repair_state WHERE key='state'").fetchone()
        if row:
            try:
                state=json.loads(row['value_json']);
                if isinstance(state,dict):
                    state['version']=self.VERSION; state.setdefault('total_checked',0); state.setdefault('total_repaired',0); state.setdefault('total_reverted',0); state.setdefault('repair_batch_size',350); return state
            except Exception: pass
        state={'version':self.VERSION,'total_checked':0,'total_repaired':0,'total_reverted':0,'repair_batch_size':350,'last_run_at':0}
        self.save_state(state); return state
    def save_state(self,state=None):
        state=state or self.state
        with self.memory.lock:
            self.memory.db.execute("INSERT OR REPLACE INTO relation_repair_state(key,value_json,updated_at) VALUES(?,?,?)",('state',json.dumps(state,ensure_ascii=False),int(time.time())))
            self.memory.db.commit()
    def classify_repair(self, subject, relation, obj, old_status='candidate', reject_reason=None):
        s=norm_key(subject); r=relation_key(relation); o=norm_key(obj); tc_o=token_count(obj); tc_s=token_count(subject)
        if not s or not o or not r: return None
        if has_bad_subject(subject) or has_bad_object(obj): return None
        # Do not resurrect hard rejects. Only repair short-object rejects with strong semantic hints.
        if old_status=='rejected' and reject_reason not in SAFE_REJECT_REASONS_FOR_REPAIR:
            return None
        if r in ('is_a','definition') and o in COLOR_WORDS and any(h in s for h in ('farbe','hintergrundfarbe','color')):
            return {'new_relation':'has_color','new_status':'property_candidate','candidate_type':'color_property','reason':'repair_color_property','confidence':0.92}
        if has_location_hint(subject) and 1 <= tc_o <= 5 and not has_bad_object(obj):
            return {'new_relation':'located_in','new_status':'relation_repair_candidate','candidate_type':'location_relation','reason':'repair_location_relation','confidence':0.78}
        if r in ('is_a','definition') and any(h in s for h in ('codename','der name','ihr codename')) and 1 <= tc_o <= 8:
            return {'new_relation':'has_name','new_status':'property_candidate','candidate_type':'name_property','reason':'repair_name_property','confidence':0.72}
        if r in ('is_a','definition') and has_property_hint(subject) and 1 <= tc_o <= 8:
            return {'new_relation':'has_property_value','new_status':'property_candidate','candidate_type':'property_value','reason':'repair_property_value','confidence':0.68}
        if r in ('is_a','definition') and 1 <= tc_o <= 3 and has_tech_hint(subject) and old_status!='rejected':
            return {'new_relation':'is_a','new_status':'definition_candidate','candidate_type':'short_definition_candidate','reason':'repair_short_definition_candidate','confidence':0.64}
        if old_status=='rejected' and reject_reason in SAFE_REJECT_REASONS_FOR_REPAIR and 1 <= tc_o <= 3 and 2 <= tc_s <= 8 and not has_bad_object(obj):
            return {'new_relation':r,'new_status':'needs_relation_repair','candidate_type':'ambiguous_short_object','reason':'mark_needs_relation_repair_short_object','confidence':0.45}
        return None
    def revert_unsafe_repairs(self, batch_size=500):
        if not self.memory.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_relations'").fetchone():
            return {'checked':0,'reverted':0,'samples':[]}
        rows=self.memory.rows("""SELECT id,subject,relation,object,status,reject_reason,candidate_type,repair_reason,original_relation,original_object FROM candidate_relations WHERE status IN ('definition_candidate','property_candidate','relation_repair_candidate','needs_relation_repair') LIMIT ?""",(int(batch_size),))
        now=int(time.time()); checked=0; reverted=0; samples=[]
        for row in rows:
            checked+=1
            unsafe = has_bad_subject(row['subject']) or has_bad_object(row['object'])
            if row['repair_reason'] in RISKY_REPAIR_REASONS and unsafe:
                oldstatus=row['status']; oldrel=row['relation']
                newrel=row['original_relation'] or row['relation']
                with self.memory.lock:
                    self.memory.db.execute("UPDATE candidate_relations SET status='rejected', reject_reason='relation_repair_reverted_unsafe', relation=?, candidate_type='unsafe_repair_reverted', repair_reason='rollback_unsafe_relation_repair', updated_at=? WHERE id=?",(newrel,now,row['id']))
                    self.memory.db.execute("INSERT INTO relation_repair_events(candidate_id,subject,old_relation,object,new_relation,old_status,new_status,candidate_type,reason,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(row['id'],row['subject'],oldrel,row['object'],newrel,oldstatus,'rejected','unsafe_repair_reverted','rollback_unsafe_relation_repair',0.0,now))
                    self.memory.db.commit()
                reverted+=1
                if len(samples)<12: samples.append({'id':row['id'],'candidate':[row['subject'],oldrel,row['object']],'reason':'rollback_unsafe_relation_repair'})
        self.state['total_reverted']=int(self.state.get('total_reverted',0))+reverted; self.save_state()
        return {'checked':checked,'reverted':reverted,'samples':samples}
    def repair_once(self,batch_size=350,include_rejected=True):
        self.ensure_schema(); rollback=self.revert_unsafe_repairs(batch_size=500)
        statuses="'candidate','rejected','needs_relation_repair'" if include_rejected else "'candidate','needs_relation_repair'"
        rows=self.memory.rows(f"""SELECT id,subject,relation,object,status,reject_reason,confidence,COALESCE(candidate_type,'') AS candidate_type FROM candidate_relations WHERE status IN ({statuses}) AND (candidate_type IS NULL OR candidate_type='') ORDER BY id ASC LIMIT ?""",(int(batch_size),))
        now=int(time.time()); counts=Counter(); samples=[]
        for row in rows:
            counts['checked']+=1
            repair=self.classify_repair(row['subject'],row['relation'],row['object'],row['status'],row['reject_reason'])
            if not repair:
                counts['unchanged']+=1; continue
            with self.memory.lock:
                self.memory.db.execute("""UPDATE candidate_relations SET original_relation=COALESCE(original_relation, relation), original_object=COALESCE(original_object, object), repaired_relation=?, candidate_type=?, repair_reason=?, repair_confidence=?, status=?, relation=?, updated_at=? WHERE id=?""",(repair['new_relation'],repair['candidate_type'],repair['reason'],float(repair['confidence']),repair['new_status'],repair['new_relation'],now,row['id']))
                self.memory.db.execute("INSERT INTO relation_repair_events(candidate_id,subject,old_relation,object,new_relation,old_status,new_status,candidate_type,reason,confidence,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(row['id'],row['subject'],row['relation'],row['object'],repair['new_relation'],row['status'],repair['new_status'],repair['candidate_type'],repair['reason'],float(repair['confidence']),now))
                self.memory.db.commit()
            counts['repaired']+=1; counts[repair['new_status']]+=1; counts[repair['reason']]+=1
            if len(samples)<12: samples.append({'id':row['id'],'from':[row['subject'],row['relation'],row['object'],row['status']],'to':[row['subject'],repair['new_relation'],row['object'],repair['new_status']],'candidate_type':repair['candidate_type'],'reason':repair['reason'],'confidence':round(float(repair['confidence']),3)})
        self.state['total_checked']=int(self.state.get('total_checked',0))+counts['checked']; self.state['total_repaired']=int(self.state.get('total_repaired',0))+counts['repaired']; self.state['last_run_at']=now; self.save_state()
        return {'status':'relation_repair_phase3d6l1','checked':counts['checked'],'repaired':counts['repaired'],'unchanged':counts['unchanged'],'rollback':rollback,'typed_counts':{k:v for k,v in counts.items() if k not in ('checked','repaired','unchanged')},'samples':samples,'state':dict(self.state)}

def apply_patch(CorpusReader):
    if getattr(CorpusReader,'_phase3d6l1_relation_repair_patched',False): return
    original=CorpusReader.read_once
    def read_once_with_relation_repair(self,*args,**kwargs):
        result=original(self,*args,**kwargs)
        try:
            repairer=getattr(self,'_phase3d6l1_relation_repairer',None)
            if repairer is None:
                repairer=RelationRepairer(self.memory); self._phase3d6l1_relation_repairer=repairer
            repair=repairer.repair_once(batch_size=350,include_rejected=True)
            if isinstance(result,dict):
                result['relation_repair_and_candidate_typing']=repair; result['status']='adaptive_alignment_corpus_reader_phase3d6l1'
        except Exception as exc:
            if isinstance(result,dict): result['relation_repair_and_candidate_typing']={'status':'relation_repair_error_phase3d6l1','error':str(exc)}
        return result
    CorpusReader.read_once=read_once_with_relation_repair
    CorpusReader._phase3d6l1_relation_repair_patched=True
