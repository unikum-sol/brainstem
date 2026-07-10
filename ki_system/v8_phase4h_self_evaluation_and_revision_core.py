# -*- coding: utf-8 -*-
"""V8 phase4h self evaluation and revision core.

No word blacklists. No facts/relations/questions writes.
Self-evaluation and role revision are driven by context dynamics and neuromodulators.
"""
from __future__ import annotations
import json, time
from collections import Counter

_ORIG_RUN = None
_ORIG_CYCLE = None

def _now(): return int(time.time())
def _json(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True)
def _clamp(x, lo=0.0, hi=1.0):
    try: x=float(x)
    except Exception: x=0.0
    return max(lo, min(hi, x))

def _conn_from_loop(loop):
    for attr in ('mem','memory','m','store','memory_store'):
        obj=getattr(loop,attr,None)
        if obj is None: continue
        db=getattr(obj,'db',None) or getattr(obj,'conn',None) or getattr(obj,'con',None)
        if db is not None and hasattr(db,'execute'): return db
        if hasattr(obj,'execute'): return obj
    for obj in getattr(loop,'__dict__',{}).values():
        db=getattr(obj,'db',None) or getattr(obj,'conn',None) or getattr(obj,'con',None)
        if db is not None and hasattr(db,'execute'): return db
        if hasattr(obj,'execute'): return obj
    raise RuntimeError('phase4h: no sqlite connection found on AutonomousLoop')

def _table_exists(db, table):
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None

def _cols(db, table):
    if not _table_exists(db,table): return set()
    return {r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()}

def _add_col(db, table, col, decl):
    if col not in _cols(db,table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        return True
    return False

def _ensure_unique(db, table, col, name):
    if not _table_exists(db, table) or col not in _cols(db, table): return False
    dup=db.execute(f"SELECT {col}, COUNT(*) FROM {table} WHERE {col} IS NOT NULL GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
    if dup: return False
    db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table}({col})")
    return True

def ensure_phase4h_schema(db):
    changes=[]
    db.execute("""CREATE TABLE IF NOT EXISTS context_hypotheses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, role TEXT, subject TEXT, relation_hint TEXT, object TEXT,
        text_excerpt TEXT, source_title TEXT, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1, status TEXT DEFAULT 'hypothesis',
        dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0,
        signature TEXT, evidence_count INTEGER DEFAULT 1
    )""")
    for col,decl in [('self_score','REAL DEFAULT 0'),('revision_pressure','REAL DEFAULT 0'),('revision_count','INTEGER DEFAULT 0'),('last_evaluated_at','INTEGER DEFAULT 0'),('last_revision_reason','TEXT')]:
        if _add_col(db,'context_hypotheses',col,decl): changes.append(f'add_column:context_hypotheses.{col}')

    db.execute("""CREATE TABLE IF NOT EXISTS hypothesis_feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, feedback_type TEXT, signal REAL DEFAULT 0, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0
    )""")
    for col,decl in [('hypothesis_id','INTEGER'),('feedback_type','TEXT'),('signal','REAL DEFAULT 0'),('reason','TEXT'),('details','TEXT'),('created_at','INTEGER DEFAULT 0')]:
        if _add_col(db,'hypothesis_feedback',col,decl): changes.append(f'add_column:hypothesis_feedback.{col}')

    db.execute("""CREATE TABLE IF NOT EXISTS hypothesis_error_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, error_type TEXT, severity REAL DEFAULT 0, reason TEXT, details TEXT, role TEXT, error_signal REAL DEFAULT 0, created_at INTEGER DEFAULT 0
    )""")
    for col,decl in [('hypothesis_id','INTEGER'),('error_type','TEXT'),('severity','REAL DEFAULT 0'),('reason','TEXT'),('details','TEXT'),('role','TEXT'),('error_signal','REAL DEFAULT 0'),('created_at','INTEGER DEFAULT 0')]:
        if _add_col(db,'hypothesis_error_events',col,decl): changes.append(f'add_column:hypothesis_error_events.{col}')

    db.execute("""CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(
        hypothesis_id INTEGER, stability REAL DEFAULT 0, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1,
        feedback_count INTEGER DEFAULT 0, error_count INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0,
        role TEXT, evidence_count INTEGER DEFAULT 0, conflict_count INTEGER DEFAULT 0, last_reason TEXT
    )""")
    for col,decl in [('stability','REAL DEFAULT 0'),('confidence','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 1'),('feedback_count','INTEGER DEFAULT 0'),('error_count','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0'),('role','TEXT'),('evidence_count','INTEGER DEFAULT 0'),('conflict_count','INTEGER DEFAULT 0'),('last_reason','TEXT')]:
        if _add_col(db,'hypothesis_stability_scores',col,decl): changes.append(f'add_column:hypothesis_stability_scores.{col}')
    if _ensure_unique(db,'hypothesis_stability_scores','hypothesis_id','idx_hypothesis_stability_scores_hid_phase4h_unique'):
        changes.append('unique_index:hypothesis_stability_scores.hypothesis_id')

    db.execute("""CREATE TABLE IF NOT EXISTS neuromodulator_learning_state(
        id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id INTEGER,
        dopamine REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0,
        gaba REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0,
        learning_rate REAL DEFAULT 0, error_weight REAL DEFAULT 0, revision_pressure REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0, exploration_pressure REAL DEFAULT 0, inhibition_level REAL DEFAULT 0, created_at INTEGER DEFAULT 0
    )""")
    for col,decl in [('cycle_id','INTEGER'),('dopamine','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('learning_rate','REAL DEFAULT 0'),('error_weight','REAL DEFAULT 0'),('revision_pressure','REAL DEFAULT 0'),('consolidation_gain','REAL DEFAULT 0'),('exploration_pressure','REAL DEFAULT 0'),('inhibition_level','REAL DEFAULT 0'),('created_at','INTEGER DEFAULT 0')]:
        if _add_col(db,'neuromodulator_learning_state',col,decl): changes.append(f'add_column:neuromodulator_learning_state.{col}')

    db.execute("""CREATE TABLE IF NOT EXISTS hypothesis_learning_updates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,hypothesis_id INTEGER,old_confidence REAL DEFAULT 0,new_confidence REAL DEFAULT 0,
        old_uncertainty REAL DEFAULT 1,new_uncertainty REAL DEFAULT 1,dopamine_effect REAL DEFAULT 0,noradrenaline_effect REAL DEFAULT 0,
        acetylcholine_effect REAL DEFAULT 0,gaba_effect REAL DEFAULT 0,serotonin_effect REAL DEFAULT 0,glutamate_effect REAL DEFAULT 0,
        update_reason TEXT,created_at INTEGER DEFAULT 0
    )""")
    for col,decl in [('dopamine_effect','REAL DEFAULT 0'),('noradrenaline_effect','REAL DEFAULT 0'),('acetylcholine_effect','REAL DEFAULT 0'),('gaba_effect','REAL DEFAULT 0'),('serotonin_effect','REAL DEFAULT 0'),('glutamate_effect','REAL DEFAULT 0'),('update_reason','TEXT'),('created_at','INTEGER DEFAULT 0')]:
        if _add_col(db,'hypothesis_learning_updates',col,decl): changes.append(f'add_column:hypothesis_learning_updates.{col}')

    db.execute("""CREATE TABLE IF NOT EXISTS hypothesis_self_evaluations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,hypothesis_id INTEGER,role TEXT,confidence REAL DEFAULT 0,uncertainty REAL DEFAULT 0,
        stability REAL DEFAULT 0,feedback_signal REAL DEFAULT 0,error_signal REAL DEFAULT 0,self_score REAL DEFAULT 0,revision_pressure REAL DEFAULT 0,
        dopamine REAL DEFAULT 0,serotonin REAL DEFAULT 0,glutamate REAL DEFAULT 0,gaba REAL DEFAULT 0,noradrenaline REAL DEFAULT 0,acetylcholine REAL DEFAULT 0,
        evaluation_reason TEXT,created_at INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS hypothesis_role_revisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,hypothesis_id INTEGER,old_role TEXT,new_role TEXT,old_confidence REAL DEFAULT 0,new_confidence REAL DEFAULT 0,
        old_uncertainty REAL DEFAULT 1,new_uncertainty REAL DEFAULT 1,revision_pressure REAL DEFAULT 0,serotonin_stabilization REAL DEFAULT 0,
        gaba_inhibition REAL DEFAULT 0,glutamate_plasticity REAL DEFAULT 0,reason TEXT,applied INTEGER DEFAULT 0,created_at INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS self_evaluation_cycles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,evaluated INTEGER DEFAULT 0,revised INTEGER DEFAULT 0,stable INTEGER DEFAULT 0,uncertain INTEGER DEFAULT 0,
        avg_self_score REAL DEFAULT 0,avg_revision_pressure REAL DEFAULT 0,created_at INTEGER DEFAULT 0
    )""")
    db.execute("CREATE TABLE IF NOT EXISTS revision_strategy_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS learning_strategy_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS rollback_safe_core_state(key TEXT PRIMARY KEY,value TEXT,updated_at INTEGER DEFAULT 0)")

    for table,col in [('revision_strategy_state','key'),('learning_strategy_state','key'),('rollback_safe_core_state','key')]:
        _ensure_unique(db,table,col,f'idx_{table}_{col}_phase4h_unique')
    now=_now()
    for k,v in {'phase':'phase4h_self_evaluation_and_revision_core','no_word_blacklists':'true','learning_mode':'context_hypotheses_with_neuromodulators','fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'disabled'}.items():
        db.execute("INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,repr(v),now))
    if changes: db.commit()
    return changes

def _latest_nm_state(db):
    row=None
    if _table_exists(db,'neuromodulator_learning_state'):
        try:
            row=db.execute("SELECT dopamine,noradrenaline,acetylcholine,gaba,serotonin,glutamate,learning_rate,error_weight,revision_pressure,consolidation_gain,exploration_pressure,inhibition_level FROM neuromodulator_learning_state ORDER BY id DESC LIMIT 1").fetchone()
        except Exception: row=None
    if row:
        keys=['dopamine','noradrenaline','acetylcholine','gaba','serotonin','glutamate','learning_rate','error_weight','revision_pressure','consolidation_gain','exploration_pressure','inhibition_level']
        return dict(zip(keys,[float(x or 0) for x in row]))
    return dict(dopamine=0.28,noradrenaline=0.34,acetylcholine=0.34,gaba=0.35,serotonin=0.35,glutamate=0.31,learning_rate=0.18,error_weight=0.35,revision_pressure=0.22,consolidation_gain=0.25,exploration_pressure=0.3,inhibition_level=0.35)

def _feedback_error_maps(db, ids):
    if not ids: return {},{}
    ph=','.join('?' for _ in ids)
    fb={}; er={}
    if _table_exists(db,'hypothesis_feedback'):
        for hid,avg,cnt in db.execute(f"SELECT hypothesis_id, AVG(COALESCE(signal,0)), COUNT(*) FROM hypothesis_feedback WHERE hypothesis_id IN ({ph}) GROUP BY hypothesis_id",ids):
            fb[int(hid)]=(float(avg or 0),int(cnt or 0))
    if _table_exists(db,'hypothesis_error_events'):
        for hid,avg,cnt in db.execute(f"SELECT hypothesis_id, AVG(COALESCE(severity,error_signal,0)), COUNT(*) FROM hypothesis_error_events WHERE hypothesis_id IN ({ph}) GROUP BY hypothesis_id",ids):
            er[int(hid)]=(float(avg or 0),int(cnt or 0))
    return fb,er

def _stability_map(db, ids):
    if not ids or not _table_exists(db,'hypothesis_stability_scores'): return {}
    ph=','.join('?' for _ in ids); out={}
    for hid,stab,ev,conflict in db.execute(f"SELECT hypothesis_id, COALESCE(stability,0), COALESCE(evidence_count,0), COALESCE(conflict_count,0) FROM hypothesis_stability_scores WHERE hypothesis_id IN ({ph})",ids):
        out[int(hid)]=(float(stab or 0),int(ev or 0),int(conflict or 0))
    return out

def _proposed_role(role, conf, unc, stab, fb, er, revp, self_score):
    if unc>=0.74 or revp>=0.56 or er>=0.65:
        return 'uncertain_hypothesis','high_uncertainty_or_revision_pressure'
    if role=='uncertain_hypothesis' and conf>=0.52 and stab>=0.50 and er<0.45:
        return 'stable_hypothesis','uncertain_became_stable_by_evidence'
    if role=='stable_hypothesis' and (unc>conf+0.12 or er>0.55):
        return 'uncertain_hypothesis','stable_destabilized_by_error_or_uncertainty'
    if self_score>=0.68 and stab>=0.6 and conf>unc:
        return role,'stable_keep'
    return role,'keep_role'

def self_evaluate_and_revise(db, limit=240):
    ensure_phase4h_schema(db); now=_now(); nm=_latest_nm_state(db)
    rows=db.execute("SELECT id, role, COALESCE(confidence,0), COALESCE(uncertainty,1), COALESCE(status,'hypothesis') FROM context_hypotheses ORDER BY COALESCE(last_evaluated_at,0) ASC, id DESC LIMIT ?",(int(limit),)).fetchall()
    ids=[int(r[0]) for r in rows]
    fbmap,ermap=_feedback_error_maps(db,ids); stmap=_stability_map(db,ids)
    evaluated=revised=stable=uncertain=0; score_sum=revp_sum=0.0; role_counts=Counter()
    for hid,role,conf,unc,status in rows:
        hid=int(hid); role=role or 'raw_hypothesis'; conf=float(conf or 0); unc=float(unc or 1)
        fb,fbn=fbmap.get(hid,(0.0,0)); er,ern=ermap.get(hid,(0.0,0)); stab,ev,conflicts=stmap.get(hid,(0.0,0,0))
        self_score=_clamp(0.30*conf+0.24*stab+0.15*max(0,fb)+0.06*nm['dopamine']+0.05*nm['serotonin']-0.22*unc-0.16*er-0.05*nm['gaba'])
        revp=_clamp(max(0.0,unc-conf)+0.30*er+0.12*nm['noradrenaline']+0.07*nm['glutamate']-0.10*nm['serotonin']-0.06*nm['gaba'])
        db.execute("INSERT INTO hypothesis_self_evaluations(hypothesis_id,role,confidence,uncertainty,stability,feedback_signal,error_signal,self_score,revision_pressure,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,evaluation_reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(hid,role,conf,unc,stab,fb,er,self_score,revp,nm['dopamine'],nm['serotonin'],nm['glutamate'],nm['gaba'],nm['noradrenaline'],nm['acetylcholine'],'phase4h_self_evaluation_contextual_no_word_blacklists',now))
        new_role,reason=_proposed_role(role,conf,unc,stab,fb,er,revp,self_score)
        lr=_clamp(nm['learning_rate'],0.03,0.30)
        new_conf=_clamp(conf+(self_score-0.5)*lr*(1.0-0.55*nm['gaba']))
        new_unc=_clamp(unc-(self_score-0.5)*lr*0.75+revp*0.04+er*0.03)
        applied=1 if new_role!=role else 0
        if applied: revised+=1
        db.execute("UPDATE context_hypotheses SET role=?, confidence=?, uncertainty=?, self_score=?, revision_pressure=?, revision_count=COALESCE(revision_count,0)+?, last_evaluated_at=?, last_revision_reason=?, updated_at=? WHERE id=?",(new_role,round(new_conf,4),round(new_unc,4),round(self_score,4),round(revp,4),applied,now,reason,now,hid))
        db.execute("INSERT INTO hypothesis_role_revisions(hypothesis_id,old_role,new_role,old_confidence,new_confidence,old_uncertainty,new_uncertainty,revision_pressure,serotonin_stabilization,gaba_inhibition,glutamate_plasticity,reason,applied,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(hid,role,new_role,conf,new_conf,unc,new_unc,revp,nm['serotonin'],nm['gaba'],nm['glutamate'],reason,applied,now))
        db.execute("INSERT INTO hypothesis_learning_updates(hypothesis_id,old_confidence,new_confidence,old_uncertainty,new_uncertainty,dopamine_effect,noradrenaline_effect,acetylcholine_effect,gaba_effect,serotonin_effect,glutamate_effect,update_reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(hid,conf,new_conf,unc,new_unc,nm['dopamine'],nm['noradrenaline'],nm['acetylcholine'],nm['gaba'],nm['serotonin'],nm['glutamate'],'phase4h_self_evaluation_revision_update',now))
        db.execute("INSERT INTO hypothesis_stability_scores(hypothesis_id,stability,confidence,uncertainty,feedback_count,error_count,evidence_count,conflict_count,last_reason,role,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(hypothesis_id) DO UPDATE SET stability=excluded.stability,confidence=excluded.confidence,uncertainty=excluded.uncertainty,feedback_count=excluded.feedback_count,error_count=excluded.error_count,evidence_count=excluded.evidence_count,conflict_count=excluded.conflict_count,last_reason=excluded.last_reason,role=excluded.role,updated_at=excluded.updated_at",(hid,round(_clamp(0.55*stab+0.45*self_score),4),round(new_conf,4),round(new_unc,4),fbn,ern,max(1,ev),conflicts,'phase4h_self_evaluation_sync',new_role,now))
        evaluated+=1; score_sum+=self_score; revp_sum+=revp; role_counts[new_role]+=1
        if new_role=='stable_hypothesis': stable+=1
        if new_role=='uncertain_hypothesis': uncertain+=1
    avg_score=round(score_sum/max(1,evaluated),4); avg_revp=round(revp_sum/max(1,evaluated),4)
    db.execute("INSERT INTO self_evaluation_cycles(evaluated,revised,stable,uncertain,avg_self_score,avg_revision_pressure,created_at) VALUES(?,?,?,?,?,?,?)",(evaluated,revised,stable,uncertain,avg_score,avg_revp,now))
    for k,v in {'phase':'phase4h_self_evaluation_and_revision_core','last_evaluated':evaluated,'last_revised':revised,'last_stable':stable,'last_uncertain':uncertain,'last_avg_self_score':avg_score,'last_avg_revision_pressure':avg_revp,'no_word_blacklists':'true','fact_promotion':'disabled'}.items():
        db.execute("INSERT INTO revision_strategy_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,repr(v),now))
    db.commit()
    return {'status':'phase4h_self_evaluation_complete','evaluated':evaluated,'revised':revised,'stable':stable,'uncertain':uncertain,'avg_self_score':avg_score,'avg_revision_pressure':avg_revp,'role_counts':dict(role_counts)}

def managed_cycle(self, progress=None):
    db=_conn_from_loop(self); ensure_phase4h_schema(db)
    base=_ORIG_CYCLE(self, progress) if _ORIG_CYCLE else None
    ev=self_evaluate_and_revise(db)
    return {'status':'phase4h_self_evaluation_and_revision_core','base_cycle':base,'self_evaluation_and_revision':ev,'direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'disabled','fact_promotion':'disabled','no_word_blacklists':True,'learning_mode':'context_hypotheses_with_neuromodulators'}

def managed_run(self, cycles=5, progress=None):
    out=[]; total=max(1,int(cycles or 1))
    for i in range(total):
        if getattr(self,'cancel',False) or getattr(self,'auto_stop',False) or getattr(self,'stop_requested',False):
            out.append({'status':'stopped','message':'Stop-Anforderung erkannt.'}); break
        out.append(managed_cycle(self, progress))
        if progress:
            try: progress(i+1,total,'phase4h self evaluation')
            except Exception: pass
    return out

def patch_autonomous_loop(loop_cls=None,*args,**kwargs):
    global _ORIG_RUN,_ORIG_CYCLE
    if loop_cls is None:
        try:
            from ki_system.autonomous import AutonomousLoop as loop_cls
        except Exception: return False
    if _ORIG_RUN is None: _ORIG_RUN=getattr(loop_cls,'run',None)
    if _ORIG_CYCLE is None: _ORIG_CYCLE=getattr(loop_cls,'cycle',None)
    loop_cls.run=managed_run; loop_cls.cycle=managed_cycle
    vals={'phase4h_self_evaluation_and_revision_core':True,'phase4g_neuromodulated_learning_control':True,'no_word_blacklists':True,'learning_mode':'context_hypotheses_with_neuromodulators','fact_promotion':'disabled'}
    for k,v in vals.items():
        setattr(loop_cls,k,v); setattr(loop_cls,'_'+k,v)
    return True
try:
    patch_autonomous_loop()
except Exception:
    pass
