
# V8-phase4i runtime schema guard FIXED3
# Purpose: robust Phase4i runtime consolidation without relying on missing external functions.
# Project compass: no word blacklists, no facts/relations/questions, hypotheses remain hypotheses.

import json, time, importlib
from collections import defaultdict

PHASE = "phase4i_runtime_schema_guard_fixed3"


def _conn(db):
    return getattr(db, 'db', db)


def _execute(db, sql, params=()):
    return _conn(db).execute(sql, params)


def _fetchall(db, sql, params=()):
    return _conn(db).execute(sql, params).fetchall()


def _fetchone(db, sql, params=()):
    return _conn(db).execute(sql, params).fetchone()


def _commit(db):
    c = _conn(db)
    if hasattr(c, 'commit'):
        c.commit()


def _table_exists(db, table):
    return _fetchone(db, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)) is not None


def _cols(db, table):
    if not _table_exists(db, table):
        return []
    return [r[1] for r in _fetchall(db, f"PRAGMA table_info({table})")]


def _add_col(db, table, col, spec, changes):
    if not _table_exists(db, table):
        return
    if col not in _cols(db, table):
        _execute(db, f"ALTER TABLE {table} ADD COLUMN {col} {spec}")
        changes.append(f"add_column:{table}.{col}")


def _unique(db, table, col, changes):
    if _table_exists(db, table) and col in _cols(db, table):
        idx = f"idx_{table}_{col}_phase4i_fixed3_unique"
        _execute(db, f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")


def _upsert_state(db, table, key, value):
    ensure_phase4i_schema(db)
    now = int(time.time())
    _execute(db, f"INSERT INTO {table}(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, json.dumps(value, ensure_ascii=False), now))


def ensure_phase4i_schema(db):
    """Canonical Phase4i schema guard. Idempotent and safe for old DB variants."""
    changes = []
    # Core upstream tables used by Phase4h/4g/4i
    _execute(db, """CREATE TABLE IF NOT EXISTS context_hypotheses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chunk_id INTEGER,
        role TEXT,
        subject TEXT,
        relation_hint TEXT,
        object TEXT,
        text_excerpt TEXT,
        source_title TEXT,
        confidence REAL DEFAULT 0,
        uncertainty REAL DEFAULT 1,
        status TEXT DEFAULT 'hypothesis',
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        signature TEXT,
        evidence_count INTEGER DEFAULT 1,
        created_at INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0,
        self_score REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        revision_count INTEGER DEFAULT 0,
        last_evaluated_at INTEGER DEFAULT 0,
        last_revision_reason TEXT
    )""")
    for col, spec in [
        ('role','TEXT'), ('subject','TEXT'), ('relation_hint','TEXT'), ('object','TEXT'), ('text_excerpt','TEXT'), ('source_title','TEXT'),
        ('confidence','REAL DEFAULT 0'), ('uncertainty','REAL DEFAULT 1'), ('status',"TEXT DEFAULT 'hypothesis'"),
        ('dopamine','REAL DEFAULT 0'), ('serotonin','REAL DEFAULT 0'), ('glutamate','REAL DEFAULT 0'), ('gaba','REAL DEFAULT 0'), ('noradrenaline','REAL DEFAULT 0'), ('acetylcholine','REAL DEFAULT 0'),
        ('signature','TEXT'), ('evidence_count','INTEGER DEFAULT 1'), ('created_at','INTEGER DEFAULT 0'), ('updated_at','INTEGER DEFAULT 0'),
        ('self_score','REAL DEFAULT 0'), ('revision_pressure','REAL DEFAULT 0'), ('revision_count','INTEGER DEFAULT 0'), ('last_evaluated_at','INTEGER DEFAULT 0'), ('last_revision_reason','TEXT')
    ]:
        _add_col(db, 'context_hypotheses', col, spec, changes)

    _execute(db, """CREATE TABLE IF NOT EXISTS context_pattern_memory(
        pattern_key TEXT PRIMARY KEY,
        role TEXT,
        seen_count INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 1,
        stability REAL DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    for col, spec in [('role','TEXT'),('seen_count','INTEGER DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 1'),('stability','REAL DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(db, 'context_pattern_memory', col, spec, changes)

    _execute(db, """CREATE TABLE IF NOT EXISTS hypothesis_role_revisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis_id INTEGER,
        old_role TEXT,
        new_role TEXT,
        revision_pressure REAL DEFAULT 0,
        reason TEXT,
        changed INTEGER DEFAULT 0,
        self_score REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        uncertainty REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0
    )""")
    for col, spec in [('old_role','TEXT'),('new_role','TEXT'),('revision_pressure','REAL DEFAULT 0'),('reason','TEXT'),('changed','INTEGER DEFAULT 0'),('self_score','REAL DEFAULT 0'),('error_weight','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 0'),('created_at','INTEGER DEFAULT 0')]:
        _add_col(db, 'hypothesis_role_revisions', col, spec, changes)

    _execute(db, """CREATE TABLE IF NOT EXISTS long_term_pattern_memory(
        pattern_key TEXT PRIMARY KEY,
        dominant_role TEXT,
        observations INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 1,
        stability REAL DEFAULT 0,
        volatility REAL DEFAULT 0,
        last_decision TEXT,
        neuromodulator_profile TEXT,
        first_seen INTEGER DEFAULT 0,
        last_seen INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        confidence_trend REAL DEFAULT 0,
        uncertainty_trend REAL DEFAULT 0
    )""")
    for col, spec in [('dominant_role','TEXT'),('observations','INTEGER DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 1'),('stability','REAL DEFAULT 0'),('volatility','REAL DEFAULT 0'),('last_decision','TEXT'),('neuromodulator_profile','TEXT'),('first_seen','INTEGER DEFAULT 0'),('last_seen','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0'),('revision_pressure','REAL DEFAULT 0'),('error_weight','REAL DEFAULT 0'),('confidence_trend','REAL DEFAULT 0'),('uncertainty_trend','REAL DEFAULT 0')]:
        _add_col(db, 'long_term_pattern_memory', col, spec, changes)

    _execute(db, """CREATE TABLE IF NOT EXISTS pattern_stability_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_key TEXT,
        role TEXT,
        stability REAL DEFAULT 0,
        confidence REAL DEFAULT 0,
        uncertainty REAL DEFAULT 1,
        observations INTEGER DEFAULT 0,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        decision TEXT,
        created_at INTEGER DEFAULT 0,
        learning_rate REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 1,
        volatility REAL DEFAULT 0,
        confidence_trend REAL DEFAULT 0,
        uncertainty_trend REAL DEFAULT 0,
        details TEXT,
        updated_at INTEGER DEFAULT 0
    )""")
    for col, spec in [('pattern_key','TEXT'),('role','TEXT'),('stability','REAL DEFAULT 0'),('confidence','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 1'),('observations','INTEGER DEFAULT 0'),('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),('decision','TEXT'),('created_at','INTEGER DEFAULT 0'),('learning_rate','REAL DEFAULT 0'),('error_weight','REAL DEFAULT 0'),('revision_pressure','REAL DEFAULT 0'),('consolidation_gain','REAL DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 1'),('volatility','REAL DEFAULT 0'),('confidence_trend','REAL DEFAULT 0'),('uncertainty_trend','REAL DEFAULT 0'),('details','TEXT'),('updated_at','INTEGER DEFAULT 0')]:
        _add_col(db, 'pattern_stability_history', col, spec, changes)

    _execute(db, """CREATE TABLE IF NOT EXISTS role_confusion_memory(
        confusion_key TEXT PRIMARY KEY,
        from_role TEXT,
        to_role TEXT,
        count INTEGER DEFAULT 0,
        avg_revision_pressure REAL DEFAULT 0,
        avg_self_score REAL DEFAULT 0,
        last_reason TEXT,
        updated_at INTEGER DEFAULT 0,
        avg_error_weight REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        status TEXT DEFAULT 'observe'
    )""")
    for col, spec in [('from_role','TEXT'),('to_role','TEXT'),('count','INTEGER DEFAULT 0'),('avg_revision_pressure','REAL DEFAULT 0'),('avg_self_score','REAL DEFAULT 0'),('last_reason','TEXT'),('updated_at','INTEGER DEFAULT 0'),('avg_error_weight','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 0'),('status',"TEXT DEFAULT 'observe'")]:
        _add_col(db, 'role_confusion_memory', col, spec, changes)

    _execute(db, """CREATE TABLE IF NOT EXISTS neuromodulator_pattern_profiles(
        profile_key TEXT PRIMARY KEY,
        role TEXT,
        observations INTEGER DEFAULT 0,
        avg_dopamine REAL DEFAULT 0,
        avg_serotonin REAL DEFAULT 0,
        avg_glutamate REAL DEFAULT 0,
        avg_gaba REAL DEFAULT 0,
        avg_noradrenaline REAL DEFAULT 0,
        avg_acetylcholine REAL DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 1,
        updated_at INTEGER DEFAULT 0,
        avg_learning_rate REAL DEFAULT 0,
        avg_error_weight REAL DEFAULT 0,
        avg_revision_pressure REAL DEFAULT 0,
        avg_consolidation_gain REAL DEFAULT 0
    )""")
    for col, spec in [('role','TEXT'),('observations','INTEGER DEFAULT 0'),('avg_dopamine','REAL DEFAULT 0'),('avg_serotonin','REAL DEFAULT 0'),('avg_glutamate','REAL DEFAULT 0'),('avg_gaba','REAL DEFAULT 0'),('avg_noradrenaline','REAL DEFAULT 0'),('avg_acetylcholine','REAL DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 1'),('updated_at','INTEGER DEFAULT 0'),('avg_learning_rate','REAL DEFAULT 0'),('avg_error_weight','REAL DEFAULT 0'),('avg_revision_pressure','REAL DEFAULT 0'),('avg_consolidation_gain','REAL DEFAULT 0')]:
        _add_col(db, 'neuromodulator_pattern_profiles', col, spec, changes)

    _execute(db, "CREATE TABLE IF NOT EXISTS long_term_consolidation_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    for table, col in [('long_term_pattern_memory','pattern_key'),('role_confusion_memory','confusion_key'),('neuromodulator_pattern_profiles','profile_key'),('long_term_consolidation_state','key')]:
        _unique(db, table, col, changes)
    _commit(db)
    return changes


def _decision(stability, volatility, observations):
    if observations >= 5 and stability >= 0.68 and volatility <= 0.25:
        return 'stabilize_pattern'
    if volatility >= 0.45 or stability < 0.35:
        return 'observe_with_revision_pressure'
    return 'observe'


def consolidate_long_term_memory(db, limit=1200):
    ensure_phase4i_schema(db)
    now = int(time.time())
    processed = history = profiles = confusions = 0

    rows = []
    if _table_exists(db, 'context_pattern_memory'):
        rows = _fetchall(db, """
            SELECT pattern_key, COALESCE(role,'unknown'), COALESCE(seen_count,0),
                   COALESCE(avg_confidence,0), COALESCE(avg_uncertainty,1), COALESCE(stability,0)
            FROM context_pattern_memory
            ORDER BY COALESCE(seen_count,0) DESC, COALESCE(stability,0) DESC
            LIMIT ?
        """, (int(limit),))

    for key, role, seen, avgc, avgu, stab in rows:
        seen = int(seen or 0); avgc = float(avgc or 0); avgu = float(avgu if avgu is not None else 1); stab = float(stab or 0)
        volatility = max(0.0, min(1.0, avgu - avgc + (0.15 if seen < 3 else 0.0)))
        dec = _decision(stab, volatility, seen)
        profile = json.dumps({'role': role, 'confidence': round(avgc,3), 'uncertainty': round(avgu,3), 'stability': round(stab,3)}, ensure_ascii=False)
        _execute(db, """
            INSERT INTO long_term_pattern_memory(pattern_key,dominant_role,observations,avg_confidence,avg_uncertainty,stability,volatility,last_decision,neuromodulator_profile,first_seen,last_seen,updated_at,revision_pressure,error_weight,confidence_trend,uncertainty_trend)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(pattern_key) DO UPDATE SET
              dominant_role=excluded.dominant_role,
              observations=excluded.observations,
              avg_confidence=excluded.avg_confidence,
              avg_uncertainty=excluded.avg_uncertainty,
              stability=excluded.stability,
              volatility=excluded.volatility,
              last_decision=excluded.last_decision,
              neuromodulator_profile=excluded.neuromodulator_profile,
              last_seen=excluded.last_seen,
              updated_at=excluded.updated_at,
              revision_pressure=excluded.revision_pressure,
              error_weight=excluded.error_weight,
              confidence_trend=excluded.confidence_trend,
              uncertainty_trend=excluded.uncertainty_trend
        """, (key, role, seen, avgc, avgu, stab, volatility, dec, profile, now, now, now, max(0,avgu-avgc), avgu, avgc-stab, avgu-(1-stab)))
        _execute(db, """
            INSERT INTO pattern_stability_history(pattern_key,role,observations,avg_confidence,avg_uncertainty,confidence,uncertainty,stability,volatility,decision,details,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (key, role, seen, avgc, avgu, avgc, avgu, stab, volatility, dec, profile, now, now))
        processed += 1; history += 1

    # Neuromodulator profiles per role from context_hypotheses.
    if _table_exists(db, 'context_hypotheses'):
        prof_rows = _fetchall(db, """
            SELECT COALESCE(role,'unknown'), COUNT(*),
                   AVG(COALESCE(dopamine,0)), AVG(COALESCE(serotonin,0)), AVG(COALESCE(glutamate,0)),
                   AVG(COALESCE(gaba,0)), AVG(COALESCE(noradrenaline,0)), AVG(COALESCE(acetylcholine,0)),
                   AVG(COALESCE(confidence,0)), AVG(COALESCE(uncertainty,1))
            FROM context_hypotheses GROUP BY COALESCE(role,'unknown')
        """)
        for role, obs, dop, ser, glu, gaba, nor, ace, avgc, avgu in prof_rows:
            pkey = str(role)
            _execute(db, """
                INSERT INTO neuromodulator_pattern_profiles(profile_key,role,observations,avg_dopamine,avg_serotonin,avg_glutamate,avg_gaba,avg_noradrenaline,avg_acetylcholine,avg_confidence,avg_uncertainty,updated_at,avg_learning_rate,avg_error_weight,avg_revision_pressure,avg_consolidation_gain)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(profile_key) DO UPDATE SET
                  role=excluded.role, observations=excluded.observations,
                  avg_dopamine=excluded.avg_dopamine, avg_serotonin=excluded.avg_serotonin,
                  avg_glutamate=excluded.avg_glutamate, avg_gaba=excluded.avg_gaba,
                  avg_noradrenaline=excluded.avg_noradrenaline, avg_acetylcholine=excluded.avg_acetylcholine,
                  avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty,
                  updated_at=excluded.updated_at, avg_learning_rate=excluded.avg_learning_rate,
                  avg_error_weight=excluded.avg_error_weight, avg_revision_pressure=excluded.avg_revision_pressure,
                  avg_consolidation_gain=excluded.avg_consolidation_gain
            """, (pkey, role, int(obs or 0), float(dop or 0), float(ser or 0), float(glu or 0), float(gaba or 0), float(nor or 0), float(ace or 0), float(avgc or 0), float(avgu if avgu is not None else 1), now, 0.0, float(avgu if avgu is not None else 1), max(0.0, float(avgu if avgu is not None else 1)-float(avgc or 0)), float(avgc or 0)))
            profiles += 1

    # Role confusion memory from revisions. No word filters, only role transition statistics.
    if _table_exists(db, 'hypothesis_role_revisions'):
        rev_rows = _fetchall(db, """
            SELECT COALESCE(old_role,'unknown'), COALESCE(new_role,'unknown'), COUNT(*),
                   AVG(COALESCE(revision_pressure,0)), AVG(COALESCE(self_score,0)),
                   AVG(COALESCE(error_weight,0)), AVG(COALESCE(uncertainty,0)), COALESCE(MAX(reason),'observe')
            FROM hypothesis_role_revisions GROUP BY COALESCE(old_role,'unknown'), COALESCE(new_role,'unknown')
        """)
        for old, new, cnt, rp, ss, ew, unc, reason in rev_rows:
            ckey = f'{old}->{new}'
            status = 'stable_keep' if old == new else 'role_transition_observed'
            _execute(db, """
                INSERT INTO role_confusion_memory(confusion_key,from_role,to_role,count,avg_revision_pressure,avg_self_score,last_reason,updated_at,avg_error_weight,avg_uncertainty,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(confusion_key) DO UPDATE SET
                  from_role=excluded.from_role, to_role=excluded.to_role, count=excluded.count,
                  avg_revision_pressure=excluded.avg_revision_pressure, avg_self_score=excluded.avg_self_score,
                  last_reason=excluded.last_reason, updated_at=excluded.updated_at,
                  avg_error_weight=excluded.avg_error_weight, avg_uncertainty=excluded.avg_uncertainty,
                  status=excluded.status
            """, (ckey, old, new, int(cnt or 0), float(rp or 0), float(ss or 0), reason, now, float(ew or 0), float(unc or 0), status))
            confusions += 1

    summary = {
        'status': 'long_term_consolidated_phase4i_fixed3',
        'processed_patterns': processed,
        'history_rows': history,
        'profiles': profiles,
        'role_confusions': confusions,
        'phase': PHASE,
        'no_word_blacklists': True,
    }
    for k, v in {
        'phase': PHASE,
        'no_word_blacklists': 'true',
        'learning_mode': 'context_hypotheses_with_neuromodulators',
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'disabled',
        'last_processed_patterns': processed,
        'last_history_rows': history,
        'last_profiles': profiles,
        'last_role_confusions': confusions,
    }.items():
        _execute(db, "INSERT INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, json.dumps(v, ensure_ascii=False), now))
    _commit(db)
    summary['created_at'] = now
    return summary


def _resolve_memory(loop):
    for name in ('mem','memory','m','store','memory_store'):
        if hasattr(loop, name):
            val = getattr(loop, name)
            if val is not None:
                return val
    # fallback: first attr with execute/db
    for val in vars(loop).values():
        if hasattr(val, 'execute') or hasattr(val, 'db'):
            return val
    raise AttributeError('No memory object found on AutonomousLoop instance')


def managed_run(self, cycles=1, progress=None):
    mem = _resolve_memory(self)
    ensure_phase4i_schema(mem)
    try:
        base = importlib.import_module('ki_system.v8_phase4h_self_evaluation_and_revision_core')
        result = base.managed_run(self, cycles, progress)
    except Exception:
        # Re-raise; do not hide learning/runtime errors.
        raise
    mem = _resolve_memory(self)
    summary = consolidate_long_term_memory(mem)
    if isinstance(result, list):
        result.append({'phase4i_long_term_consolidation': summary})
    return result


def managed_cycle(self, progress=None):
    mem = _resolve_memory(self)
    ensure_phase4i_schema(mem)
    base = importlib.import_module('ki_system.v8_phase4h_self_evaluation_and_revision_core')
    result = base.managed_cycle(self, progress)
    mem = _resolve_memory(self)
    summary = consolidate_long_term_memory(mem)
    if isinstance(result, dict):
        result['phase4i_long_term_consolidation'] = summary
    return result


def patch_autonomous_loop(*args, **kwargs):
    try:
        from ki_system.autonomous import AutonomousLoop
    except Exception:
        return False
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    # both marker styles for compatibility with older test tools
    AutonomousLoop.phase4i_runtime_schema_guard_fixed3 = True
    AutonomousLoop._phase4i_runtime_schema_guard_fixed3 = True
    AutonomousLoop.phase4i_runtime_schema_guard_fixed2 = True
    AutonomousLoop._phase4i_runtime_schema_guard_fixed2 = True
    AutonomousLoop.phase4i_long_term_memory_and_pattern_stability = True
    AutonomousLoop._phase4i_long_term_memory_and_pattern_stability = True
    AutonomousLoop.phase4h_self_evaluation_and_revision_core = True
    AutonomousLoop.phase4g_neuromodulated_learning_control = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.learning_mode = 'context_hypotheses_with_neuromodulators'
    AutonomousLoop._rollback_learning_mode = 'context_hypotheses_with_neuromodulators'
    AutonomousLoop.fact_promotion = 'disabled'
    AutonomousLoop._fact_promotion = 'disabled'
    return True

# Safe idempotent patch on import.
try:
    patch_autonomous_loop()
except Exception as exc:
    print('[PHASE4I_RUNTIME_SCHEMA_GUARD_FIXED3_IMPORT_ERROR]', exc)
