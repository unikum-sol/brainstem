
from __future__ import annotations
import sqlite3, time, json
PHASE='phase4i_runtime_autoload_and_periodic_consolidation_fix'
LEARNING_MODE='context_hypotheses_with_neuromodulators'
def _json(x):
    try: return json.dumps(x, ensure_ascii=False)
    except Exception: return json.dumps({'repr':repr(x)}, ensure_ascii=False)
def _db_from_loop(loop):
    for obj in [getattr(loop,n,None) for n in ('mem','memory','m','store','memory_store','db','conn','con')] + [loop]:
        if obj is None: continue
        if isinstance(obj, sqlite3.Connection): return obj
        for a in ('db','conn','con','connection'):
            if hasattr(obj,a) and isinstance(getattr(obj,a), sqlite3.Connection): return getattr(obj,a)
        if hasattr(obj,'execute') and hasattr(obj,'commit'): return obj
    raise RuntimeError('Could not resolve sqlite connection')
def _ex(db,t): return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _cols(db,t): return [r[1] for r in db.execute(f'PRAGMA table_info({t})').fetchall()] if _ex(db,t) else []
def _add(db,t,c,d):
    if _ex(db,t) and c not in _cols(db,t): db.execute(f'ALTER TABLE {t} ADD COLUMN {c} {d}'); return True
    return False
def _unique(db,t,c):
    if not _ex(db,t) or c not in _cols(db,t): return False
    dup=db.execute(f'SELECT {c},COUNT(*) FROM {t} WHERE {c} IS NOT NULL GROUP BY {c} HAVING COUNT(*)>1 LIMIT 1').fetchone()
    if dup: return False
    db.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_{c}_phase4i_runtime_unique ON {t}({c})'); return True
def ensure_phase4i_runtime_schema(db):
    changes=[]; now=int(time.time())
    db.execute("CREATE TABLE IF NOT EXISTS long_term_pattern_memory(pattern_key TEXT PRIMARY KEY, dominant_role TEXT, observations INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, volatility REAL DEFAULT 0, last_decision TEXT, neuromodulator_profile TEXT, first_seen INTEGER DEFAULT 0, last_seen INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0, revision_pressure REAL DEFAULT 0, error_weight REAL DEFAULT 0, confidence_trend REAL DEFAULT 0, uncertainty_trend REAL DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS pattern_stability_history(id INTEGER PRIMARY KEY AUTOINCREMENT, pattern_key TEXT, role TEXT, observations INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, volatility REAL DEFAULT 0, decision TEXT, created_at INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS role_confusion_memory(confusion_key TEXT PRIMARY KEY, from_role TEXT, to_role TEXT, count INTEGER DEFAULT 0, avg_revision_pressure REAL DEFAULT 0, avg_self_score REAL DEFAULT 0, last_reason TEXT, updated_at INTEGER DEFAULT 0, avg_error_weight REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, status TEXT DEFAULT 'observe')")
    db.execute("CREATE TABLE IF NOT EXISTS neuromodulator_pattern_profiles(profile_key TEXT PRIMARY KEY, role TEXT, observations INTEGER DEFAULT 0, avg_dopamine REAL DEFAULT 0, avg_serotonin REAL DEFAULT 0, avg_glutamate REAL DEFAULT 0, avg_gaba REAL DEFAULT 0, avg_noradrenaline REAL DEFAULT 0, avg_acetylcholine REAL DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, updated_at INTEGER DEFAULT 0, avg_learning_rate REAL DEFAULT 0, avg_error_weight REAL DEFAULT 0, avg_revision_pressure REAL DEFAULT 0, avg_consolidation_gain REAL DEFAULT 0)")
    db.execute("CREATE TABLE IF NOT EXISTS long_term_consolidation_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    for t,c in [('long_term_pattern_memory','pattern_key'),('role_confusion_memory','confusion_key'),('neuromodulator_pattern_profiles','profile_key'),('long_term_consolidation_state','key')]:
        if _unique(db,t,c): changes.append('unique_index:%s.%s'%(t,c))
    for k,v in {'phase':PHASE,'no_word_blacklists':'true','learning_mode':LEARNING_MODE,'fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'disabled'}.items():
        db.execute('INSERT INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at',(k,_json(v),now))
    db.commit(); return changes
def _state_num(db,k):
    if not _ex(db,'reading_strategy_state'): return 0.0
    r=db.execute('SELECT value FROM reading_strategy_state WHERE key=?',(k,)).fetchone()
    try: return float(str(r[0]).strip("'\"")) if r else 0.0
    except Exception: return 0.0
def consolidate_long_term_memory(db, limit=1200):
    ensure_phase4i_runtime_schema(db); now=int(time.time()); processed=history=profiles=confusions=0
    source=[]
    if _ex(db,'context_pattern_memory') and {'pattern_key','role'}.issubset(set(_cols(db,'context_pattern_memory'))):
        cols=set(_cols(db,'context_pattern_memory')); seen='seen_count' if 'seen_count' in cols else ('seen' if 'seen' in cols else '1'); avgc='avg_confidence' if 'avg_confidence' in cols else '0'; avgu='avg_uncertainty' if 'avg_uncertainty' in cols else '0'; stab='stability' if 'stability' in cols else '0'
        source=db.execute(f'SELECT pattern_key,role,{seen},{avgc},{avgu},{stab} FROM context_pattern_memory ORDER BY {seen} DESC LIMIT ?',(limit,)).fetchall()
    elif _ex(db,'context_hypotheses') and {'role','confidence','uncertainty'}.issubset(set(_cols(db,'context_hypotheses'))):
        keyexpr="COALESCE(signature, role || ':' || substr(COALESCE(text_excerpt,''),1,80))" if 'signature' in _cols(db,'context_hypotheses') else "role || ':' || substr(COALESCE(text_excerpt,''),1,80)"
        source=db.execute(f'SELECT {keyexpr},role,COUNT(*),AVG(confidence),AVG(uncertainty),MAX(0,AVG(confidence)-AVG(uncertainty)+0.5) FROM context_hypotheses GROUP BY 1,2 ORDER BY COUNT(*) DESC LIMIT ?',(limit,)).fetchall()
    for key,role,seen,avgc,avgu,stab in source:
        key=str(key or '')[:240]; role=str(role or 'unknown'); seen=int(seen or 0); avgc=float(avgc or 0); avgu=float(avgu or 0); stab=float(stab or max(0,min(1,avgc-avgu+0.5))); vol=max(0,min(1,avgu))
        dec='stabilize_candidate_pattern' if seen>=5 and stab>=0.68 and avgu<=0.42 else ('keep_uncertain_for_learning' if avgu>=0.70 else 'observe')
        db.execute('INSERT INTO long_term_pattern_memory(pattern_key,dominant_role,observations,avg_confidence,avg_uncertainty,stability,volatility,last_decision,neuromodulator_profile,first_seen,last_seen,updated_at,revision_pressure,error_weight,confidence_trend,uncertainty_trend) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(pattern_key) DO UPDATE SET dominant_role=excluded.dominant_role, observations=excluded.observations, avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty, stability=excluded.stability, volatility=excluded.volatility, last_decision=excluded.last_decision, neuromodulator_profile=excluded.neuromodulator_profile, last_seen=excluded.last_seen, updated_at=excluded.updated_at, revision_pressure=excluded.revision_pressure, error_weight=excluded.error_weight, confidence_trend=excluded.confidence_trend, uncertainty_trend=excluded.uncertainty_trend',(key,role,seen,avgc,avgu,stab,vol,dec,_json({'role':role,'stability':round(stab,3)}),now,now,now,max(0,avgu-avgc),avgu,avgc,-avgu))
        db.execute('INSERT INTO pattern_stability_history(pattern_key,role,observations,avg_confidence,avg_uncertainty,stability,volatility,decision,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(key,role,seen,avgc,avgu,stab,vol,dec,now)); processed+=1; history+=1
    if _ex(db,'context_hypotheses'):
        cols=set(_cols(db,'context_hypotheses')); need={'role','dopamine','serotonin','glutamate','gaba','noradrenaline','acetylcholine','confidence','uncertainty'}
        if need.issubset(cols):
            for role,obs,dop,ser,glu,gaba,nor,ach,avgc,avgu in db.execute('SELECT role,COUNT(*),AVG(dopamine),AVG(serotonin),AVG(glutamate),AVG(gaba),AVG(noradrenaline),AVG(acetylcholine),AVG(confidence),AVG(uncertainty) FROM context_hypotheses GROUP BY role').fetchall():
                db.execute('INSERT INTO neuromodulator_pattern_profiles(profile_key,role,observations,avg_dopamine,avg_serotonin,avg_glutamate,avg_gaba,avg_noradrenaline,avg_acetylcholine,avg_confidence,avg_uncertainty,updated_at,avg_learning_rate,avg_error_weight,avg_revision_pressure,avg_consolidation_gain) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(profile_key) DO UPDATE SET observations=excluded.observations, avg_dopamine=excluded.avg_dopamine, avg_serotonin=excluded.avg_serotonin, avg_glutamate=excluded.avg_glutamate, avg_gaba=excluded.avg_gaba, avg_noradrenaline=excluded.avg_noradrenaline, avg_acetylcholine=excluded.avg_acetylcholine, avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty, updated_at=excluded.updated_at, avg_learning_rate=excluded.avg_learning_rate, avg_error_weight=excluded.avg_error_weight, avg_revision_pressure=excluded.avg_revision_pressure, avg_consolidation_gain=excluded.avg_consolidation_gain',(f'role:{role}',role,int(obs or 0),float(dop or 0),float(ser or 0),float(glu or 0),float(gaba or 0),float(nor or 0),float(ach or 0),float(avgc or 0),float(avgu or 0),now,_state_num(db,'last_learning_rate'),_state_num(db,'last_error_weight'),_state_num(db,'last_revision_pressure'),_state_num(db,'last_consolidation_gain'))); profiles+=1
    for k,v in {'phase':PHASE,'last_phase':'phase4i_long_term_memory_runtime_active','last_processed_patterns':processed,'last_history_rows':history,'last_profiles':profiles,'last_role_confusions':confusions,'last_no_word_blacklists':True,'learning_mode':LEARNING_MODE,'fact_promotion':'disabled','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'disabled','updated_at':now}.items():
        db.execute('INSERT INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at',(k,_json(v),now))
    db.commit(); return {'processed_patterns':processed,'history_rows':history,'profiles':profiles,'role_confusions':confusions,'phase':PHASE,'no_word_blacklists':True}
def _base_cycle(loop,progress=None):
    try:
        from ki_system import v8_phase4h_self_evaluation_and_revision_core as p4h
        return p4h.managed_cycle(loop, progress)
    except Exception as exc: return {'status':'phase4i_base_cycle_error','error':str(exc)}
def managed_cycle(self,progress=None):
    db=_db_from_loop(self); ensure_phase4i_runtime_schema(db); base=_base_cycle(self,progress); summ=consolidate_long_term_memory(db)
    if isinstance(base,dict): base.update({'long_term_memory':summ,'phase4i_long_term_memory_and_pattern_stability':True,'no_word_blacklists':True}); return base
    return {'status':'phase4i_runtime_cycle','base':base,'long_term_memory':summ,'no_word_blacklists':True}
def managed_run(self,cycles=1,progress=None):
    out=[]
    for i in range(max(1,int(cycles or 1))):
        if progress:
            try: progress(i+1,max(1,int(cycles or 1)),'phase4i long-term memory')
            except Exception: pass
        out.append(managed_cycle(self,progress))
    return out
def patch_autonomous_loop(AutonomousLoop=None,*args,**kwargs):
    if AutonomousLoop is None:
        try:
            from ki_system.autonomous import AutonomousLoop as AL; AutonomousLoop=AL
        except Exception: return False
    AutonomousLoop.cycle=managed_cycle; AutonomousLoop.run=managed_run
    for k,v in {'phase4i_long_term_memory_and_pattern_stability':True,'_phase4i_long_term_memory_and_pattern_stability':True,'phase4i_runtime_autoload_and_periodic_consolidation_fix':True,'_phase4i_runtime_autoload_and_periodic_consolidation_fix':True,'phase4h_self_evaluation_and_revision_core':True,'phase4g_neuromodulated_learning_control':True,'no_word_blacklists':True,'_no_word_blacklists':True,'learning_mode':LEARNING_MODE,'_learning_mode':LEARNING_MODE,'fact_promotion':'disabled','_fact_promotion':'disabled'}.items():
        try: setattr(AutonomousLoop,k,v)
        except Exception: pass
    return True
