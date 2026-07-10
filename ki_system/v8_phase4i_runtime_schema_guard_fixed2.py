
"""V8 phase4i runtime schema guard FIXED2.

Purpose:
- Make Phase4i the final runtime layer without depending on older modules exposing
  consolidate_long_term_memory().
- Keep project compass: no word blacklists, no facts/relations/questions writes.
- Run Phase4h/Phase4g base learning, then periodically consolidate long-term
  pattern memory using canonical Phase4 tables.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Optional

PHASE = "phase4i_runtime_schema_guard_fixed2"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _conn(obj: Any) -> Optional[sqlite3.Connection]:
    """Best-effort extraction of sqlite3.Connection from Memory/Loop/connection."""
    if isinstance(obj, sqlite3.Connection):
        return obj
    for name in ("db", "conn", "con", "connection"):
        v = getattr(obj, name, None)
        if isinstance(v, sqlite3.Connection):
            return v
    for name in ("mem", "memory", "m", "store", "memory_store"):
        v = getattr(obj, name, None)
        c = _conn(v) if v is not None and v is not obj else None
        if c is not None:
            return c
    # scan shallow attrs for a Memory-like object, but avoid callables/private noise
    try:
        for name, v in vars(obj).items():
            if name.startswith("_") or callable(v):
                continue
            c = _conn(v) if v is not obj else None
            if c is not None:
                return c
    except Exception:
        pass
    return None


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(db: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(db, table):
        return set()
    return {r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_col(db: sqlite3.Connection, table: str, name: str, decl: str, changes: list[str]) -> None:
    if name not in _cols(db, table):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
        changes.append(f"add_column:{table}.{name}")


def _unique(db: sqlite3.Connection, table: str, column: str, changes: list[str]) -> None:
    if not _table_exists(db, table) or column not in _cols(db, table):
        return
    # Avoid creating a unique index if duplicate keys already exist.
    dup = db.execute(
        f"SELECT {column}, COUNT(*) FROM {table} WHERE {column} IS NOT NULL GROUP BY {column} HAVING COUNT(*)>1 LIMIT 1"
    ).fetchone()
    if dup:
        changes.append(f"skip_unique_duplicates:{table}.{column}")
        return
    idx = f"idx_{table}_{column}_phase4i_fixed2_unique"
    db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({column})")
    changes.append(f"unique_index:{table}.{column}")


def ensure_phase4i_schema(db_or_mem: Any) -> dict[str, Any]:
    db = _conn(db_or_mem)
    if db is None:
        return {"status": "no_connection", "changes": []}
    changes: list[str] = []

    # Core long-term tables. Use flexible definitions; add missing columns to old tables below.
    db.execute("""CREATE TABLE IF NOT EXISTS long_term_pattern_memory(
        pattern_key TEXT PRIMARY KEY,
        dominant_role TEXT,
        observations INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
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
    db.execute("""CREATE TABLE IF NOT EXISTS pattern_stability_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_key TEXT,
        role TEXT,
        observations INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        stability REAL DEFAULT 0,
        volatility REAL DEFAULT 0,
        confidence REAL DEFAULT 0,
        uncertainty REAL DEFAULT 0,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        learning_rate REAL DEFAULT 0,
        error_weight REAL DEFAULT 0,
        revision_pressure REAL DEFAULT 0,
        consolidation_gain REAL DEFAULT 0,
        confidence_trend REAL DEFAULT 0,
        uncertainty_trend REAL DEFAULT 0,
        decision TEXT,
        details TEXT,
        created_at INTEGER DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS role_confusion_memory(
        confusion_key TEXT PRIMARY KEY,
        from_role TEXT,
        to_role TEXT,
        count INTEGER DEFAULT 0,
        avg_revision_pressure REAL DEFAULT 0,
        avg_self_score REAL DEFAULT 0,
        avg_error_weight REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0,
        last_reason TEXT,
        status TEXT DEFAULT 'observe',
        updated_at INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS neuromodulator_pattern_profiles(
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
        avg_uncertainty REAL DEFAULT 0,
        avg_learning_rate REAL DEFAULT 0,
        avg_error_weight REAL DEFAULT 0,
        avg_revision_pressure REAL DEFAULT 0,
        avg_consolidation_gain REAL DEFAULT 0,
        updated_at INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS long_term_consolidation_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )""")

    # Add every known/future Phase4i column to existing older tables.
    for table, defs in {
        "long_term_pattern_memory": {
            "dominant_role":"TEXT", "observations":"INTEGER DEFAULT 0", "avg_confidence":"REAL DEFAULT 0",
            "avg_uncertainty":"REAL DEFAULT 0", "stability":"REAL DEFAULT 0", "volatility":"REAL DEFAULT 0",
            "last_decision":"TEXT", "neuromodulator_profile":"TEXT", "first_seen":"INTEGER DEFAULT 0",
            "last_seen":"INTEGER DEFAULT 0", "updated_at":"INTEGER DEFAULT 0", "revision_pressure":"REAL DEFAULT 0",
            "error_weight":"REAL DEFAULT 0", "confidence_trend":"REAL DEFAULT 0", "uncertainty_trend":"REAL DEFAULT 0",
        },
        "pattern_stability_history": {
            "pattern_key":"TEXT", "role":"TEXT", "observations":"INTEGER DEFAULT 0",
            "avg_confidence":"REAL DEFAULT 0", "avg_uncertainty":"REAL DEFAULT 0", "stability":"REAL DEFAULT 0",
            "volatility":"REAL DEFAULT 0", "confidence":"REAL DEFAULT 0", "uncertainty":"REAL DEFAULT 0",
            "dopamine":"REAL DEFAULT 0", "serotonin":"REAL DEFAULT 0", "glutamate":"REAL DEFAULT 0", "gaba":"REAL DEFAULT 0",
            "noradrenaline":"REAL DEFAULT 0", "acetylcholine":"REAL DEFAULT 0", "learning_rate":"REAL DEFAULT 0",
            "error_weight":"REAL DEFAULT 0", "revision_pressure":"REAL DEFAULT 0", "consolidation_gain":"REAL DEFAULT 0",
            "confidence_trend":"REAL DEFAULT 0", "uncertainty_trend":"REAL DEFAULT 0", "decision":"TEXT",
            "details":"TEXT", "created_at":"INTEGER DEFAULT 0", "updated_at":"INTEGER DEFAULT 0",
        },
        "role_confusion_memory": {
            "from_role":"TEXT", "to_role":"TEXT", "count":"INTEGER DEFAULT 0", "avg_revision_pressure":"REAL DEFAULT 0",
            "avg_self_score":"REAL DEFAULT 0", "avg_error_weight":"REAL DEFAULT 0", "avg_uncertainty":"REAL DEFAULT 0",
            "last_reason":"TEXT", "status":"TEXT DEFAULT 'observe'", "updated_at":"INTEGER DEFAULT 0",
        },
        "neuromodulator_pattern_profiles": {
            "role":"TEXT", "observations":"INTEGER DEFAULT 0", "avg_dopamine":"REAL DEFAULT 0", "avg_serotonin":"REAL DEFAULT 0",
            "avg_glutamate":"REAL DEFAULT 0", "avg_gaba":"REAL DEFAULT 0", "avg_noradrenaline":"REAL DEFAULT 0",
            "avg_acetylcholine":"REAL DEFAULT 0", "avg_confidence":"REAL DEFAULT 0", "avg_uncertainty":"REAL DEFAULT 0",
            "avg_learning_rate":"REAL DEFAULT 0", "avg_error_weight":"REAL DEFAULT 0", "avg_revision_pressure":"REAL DEFAULT 0",
            "avg_consolidation_gain":"REAL DEFAULT 0", "updated_at":"INTEGER DEFAULT 0",
        },
        "long_term_consolidation_state": {"value":"TEXT", "updated_at":"INTEGER DEFAULT 0"},
    }.items():
        for col, decl in defs.items():
            _add_col(db, table, col, decl, changes)

    for table, col in (
        ("long_term_pattern_memory", "pattern_key"),
        ("role_confusion_memory", "confusion_key"),
        ("neuromodulator_pattern_profiles", "profile_key"),
        ("long_term_consolidation_state", "key"),
    ):
        _unique(db, table, col, changes)

    now = int(time.time())
    state = {
        "phase": PHASE,
        "no_word_blacklists": True,
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
    }
    for k, v in state.items():
        db.execute(
            "INSERT INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (k, _json(v), now),
        )
    db.commit()
    return {"status": "ok", "phase": PHASE, "changes": changes}


def _get_nm_state(db: sqlite3.Connection) -> dict[str, float]:
    # Latest aggregate learning-control state if available.
    d = {
        "learning_rate": 0.0,
        "error_weight": 0.0,
        "revision_pressure": 0.0,
        "consolidation_gain": 0.0,
    }
    if _table_exists(db, "neuromodulator_learning_state"):
        cols = _cols(db, "neuromodulator_learning_state")
        wanted = [k for k in d if k in cols]
        if wanted:
            row = db.execute(
                f"SELECT {','.join(wanted)} FROM neuromodulator_learning_state ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                for k, v in zip(wanted, row):
                    d[k] = float(v or 0)
    return d


def consolidate_long_term_memory(db_or_mem: Any, limit: int = 1200) -> dict[str, Any]:
    db = _conn(db_or_mem)
    if db is None:
        return {"status": "no_connection", "processed_patterns": 0}
    ensure_phase4i_schema(db)
    now = int(time.time())
    nm = _get_nm_state(db)

    processed = 0
    history = 0
    profiles = 0
    confusions = 0

    if _table_exists(db, "context_pattern_memory"):
        c = _cols(db, "context_pattern_memory")
        sel_seen = "seen_count" if "seen_count" in c else ("seen" if "seen" in c else "1")
        sel_conf = "avg_confidence" if "avg_confidence" in c else "0"
        sel_unc = "avg_uncertainty" if "avg_uncertainty" in c else "0"
        sel_stab = "stability" if "stability" in c else "0"
        rows = db.execute(
            f"SELECT pattern_key, role, {sel_seen}, {sel_conf}, {sel_unc}, {sel_stab} "
            "FROM context_pattern_memory ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        for key, role, seen, avgc, avgu, stab in rows:
            seen = int(seen or 0)
            avgc = float(avgc or 0)
            avgu = float(avgu or 0)
            stab = float(stab or max(0.0, min(1.0, (avgc + max(0, 1-avgu))/2)))
            vol = round(max(0.0, min(1.0, avgu + abs(0.5-avgc)*0.2)), 3)
            decision = "observe"
            if stab >= 0.72 and avgu <= 0.35:
                decision = "stabilize"
            elif avgu >= 0.70:
                decision = "keep_uncertain"
            profile = _json({"role": role, **nm})
            db.execute(
                "INSERT INTO long_term_pattern_memory(pattern_key,dominant_role,observations,avg_confidence,avg_uncertainty,stability,volatility,last_decision,neuromodulator_profile,first_seen,last_seen,updated_at,revision_pressure,error_weight,confidence_trend,uncertainty_trend) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(pattern_key) DO UPDATE SET dominant_role=excluded.dominant_role, observations=excluded.observations, avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty, stability=excluded.stability, volatility=excluded.volatility, last_decision=excluded.last_decision, neuromodulator_profile=excluded.neuromodulator_profile, last_seen=excluded.last_seen, updated_at=excluded.updated_at, revision_pressure=excluded.revision_pressure, error_weight=excluded.error_weight, confidence_trend=excluded.confidence_trend, uncertainty_trend=excluded.uncertainty_trend",
                (key, role, seen, avgc, avgu, stab, vol, decision, profile, now, now, now, nm["revision_pressure"], nm["error_weight"], avgc-0.5, avgu-0.5),
            )
            db.execute(
                "INSERT INTO pattern_stability_history(pattern_key,role,observations,avg_confidence,avg_uncertainty,stability,volatility,confidence,uncertainty,learning_rate,error_weight,revision_pressure,consolidation_gain,decision,details,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (key, role, seen, avgc, avgu, stab, vol, avgc, avgu, nm["learning_rate"], nm["error_weight"], nm["revision_pressure"], nm["consolidation_gain"], decision, _json({"source":"phase4i_fixed2"}), now, now),
            )
            processed += 1
            history += 1

    # Role profiles from context_hypotheses.
    if _table_exists(db, "context_hypotheses"):
        cols = _cols(db, "context_hypotheses")
        if "role" in cols:
            def avgcol(name: str) -> str:
                return f"AVG(COALESCE({name},0))" if name in cols else "0"
            rows = db.execute(
                f"SELECT role, COUNT(*), {avgcol('dopamine')}, {avgcol('serotonin')}, {avgcol('glutamate')}, {avgcol('gaba')}, {avgcol('noradrenaline')}, {avgcol('acetylcholine')}, {avgcol('confidence')}, {avgcol('uncertainty')} "
                "FROM context_hypotheses GROUP BY role"
            ).fetchall()
            for role, obs, dopa, sero, glu, gaba, nor, acet, conf, unc in rows:
                key = f"role:{role}"
                db.execute(
                    "INSERT INTO neuromodulator_pattern_profiles(profile_key,role,observations,avg_dopamine,avg_serotonin,avg_glutamate,avg_gaba,avg_noradrenaline,avg_acetylcholine,avg_confidence,avg_uncertainty,avg_learning_rate,avg_error_weight,avg_revision_pressure,avg_consolidation_gain,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(profile_key) DO UPDATE SET observations=excluded.observations, avg_dopamine=excluded.avg_dopamine, avg_serotonin=excluded.avg_serotonin, avg_glutamate=excluded.avg_glutamate, avg_gaba=excluded.avg_gaba, avg_noradrenaline=excluded.avg_noradrenaline, avg_acetylcholine=excluded.avg_acetylcholine, avg_confidence=excluded.avg_confidence, avg_uncertainty=excluded.avg_uncertainty, avg_learning_rate=excluded.avg_learning_rate, avg_error_weight=excluded.avg_error_weight, avg_revision_pressure=excluded.avg_revision_pressure, avg_consolidation_gain=excluded.avg_consolidation_gain, updated_at=excluded.updated_at",
                    (key, role, int(obs or 0), float(dopa or 0), float(sero or 0), float(glu or 0), float(gaba or 0), float(nor or 0), float(acet or 0), float(conf or 0), float(unc or 0), nm["learning_rate"], nm["error_weight"], nm["revision_pressure"], nm["consolidation_gain"], now),
                )
                profiles += 1

    # Role confusion memory from revisions if available, otherwise stable self-roles.
    if _table_exists(db, "hypothesis_role_revisions"):
        rc = _cols(db, "hypothesis_role_revisions")
        if {"old_role", "new_role"}.issubset(rc):
            rows = db.execute(
                "SELECT old_role,new_role,COUNT(*),AVG(COALESCE(revision_pressure,0)),AVG(COALESCE(self_score,0)) FROM hypothesis_role_revisions GROUP BY old_role,new_role"
            ).fetchall()
            for old, new, cnt, rp, ss in rows:
                key = f"{old}->{new}"
                db.execute(
                    "INSERT INTO role_confusion_memory(confusion_key,from_role,to_role,count,avg_revision_pressure,avg_self_score,avg_error_weight,avg_uncertainty,last_reason,status,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(confusion_key) DO UPDATE SET count=excluded.count, avg_revision_pressure=excluded.avg_revision_pressure, avg_self_score=excluded.avg_self_score, avg_error_weight=excluded.avg_error_weight, avg_uncertainty=excluded.avg_uncertainty, last_reason=excluded.last_reason, status=excluded.status, updated_at=excluded.updated_at",
                    (key, old, new, int(cnt or 0), float(rp or 0), float(ss or 0), nm["error_weight"], 0.0, "observed_revision_history", "observe", now),
                )
                confusions += 1
    elif _table_exists(db, "context_role_stats"):
        c = _cols(db, "context_role_stats")
        seen_col = "seen_count" if "seen_count" in c else "seen"
        rows = db.execute(f"SELECT role,{seen_col},avg_uncertainty FROM context_role_stats").fetchall()
        for role, cnt, unc in rows:
            key = f"{role}->{role}"
            db.execute(
                "INSERT INTO role_confusion_memory(confusion_key,from_role,to_role,count,avg_revision_pressure,avg_self_score,avg_error_weight,avg_uncertainty,last_reason,status,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(confusion_key) DO UPDATE SET count=excluded.count, avg_uncertainty=excluded.avg_uncertainty, updated_at=excluded.updated_at",
                (key, role, role, int(cnt or 0), 0.0, 0.0, nm["error_weight"], float(unc or 0), "stable_keep", "observe", now),
            )
            confusions += 1

    state = {
        "phase": PHASE,
        "last_phase": PHASE,
        "last_processed_patterns": processed,
        "last_history_rows": history,
        "last_profiles": profiles,
        "last_role_confusions": confusions,
        "last_no_word_blacklists": True,
        "no_word_blacklists": True,
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
    }
    for k, v in state.items():
        db.execute(
            "INSERT INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (k, _json(v), now),
        )
    db.commit()
    return {"status":"consolidated","phase":PHASE,"processed_patterns":processed,"history_rows":history,"profiles":profiles,"role_confusions":confusions,"no_word_blacklists":True}


# Runtime wrapping
_ORIG_RUN = None
_ORIG_CYCLE = None

def _base_run(self, cycles=1, progress=None):
    try:
        from ki_system import v8_phase4h_self_evaluation_and_revision_core as h
        fn = getattr(h, "managed_run", None) or getattr(h, "safe_run", None)
        if callable(fn):
            return fn(self, cycles, progress)
    except Exception:
        pass
    if _ORIG_RUN:
        return _ORIG_RUN(self, cycles, progress)
    return []


def _base_cycle(self, progress=None):
    try:
        from ki_system import v8_phase4h_self_evaluation_and_revision_core as h
        fn = getattr(h, "managed_cycle", None) or getattr(h, "safe_cycle", None)
        if callable(fn):
            return fn(self, progress)
    except Exception:
        pass
    if _ORIG_CYCLE:
        return _ORIG_CYCLE(self, progress)
    return {"status":"no_base_cycle"}


def managed_run(self, cycles=1, progress=None):
    db = _conn(self)
    if db is not None:
        ensure_phase4i_schema(db)
    res = _base_run(self, cycles, progress)
    db = _conn(self)
    summary = consolidate_long_term_memory(db) if db is not None else {"status":"no_connection"}
    if isinstance(res, list):
        res.append({"phase4i_long_term_memory": summary})
    return res


def managed_cycle(self, progress=None):
    db = _conn(self)
    if db is not None:
        ensure_phase4i_schema(db)
    res = _base_cycle(self, progress)
    db = _conn(self)
    summary = consolidate_long_term_memory(db) if db is not None else {"status":"no_connection"}
    if isinstance(res, dict):
        res["phase4i_long_term_memory"] = summary
    return res


def patch_autonomous_loop(*args, **kwargs):
    global _ORIG_RUN, _ORIG_CYCLE
    try:
        from ki_system.autonomous import AutonomousLoop
    except Exception:
        return False
    if _ORIG_RUN is None and getattr(AutonomousLoop.run, "__module__", "") != __name__:
        _ORIG_RUN = AutonomousLoop.run
    if _ORIG_CYCLE is None and getattr(AutonomousLoop.cycle, "__module__", "") != __name__:
        _ORIG_CYCLE = AutonomousLoop.cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    for name in (
        "phase4i_runtime_schema_guard_fixed2",
        "_phase4i_runtime_schema_guard_fixed2",
        "phase4i_long_term_memory_and_pattern_stability",
        "_phase4i_long_term_memory_and_pattern_stability",
        "phase4g_neuromodulated_learning_control",
        "_phase4g_neuromodulated_learning_control",
        "phase4h_self_evaluation_and_revision_core",
        "_phase4h_self_evaluation_and_revision_core",
    ):
        setattr(AutonomousLoop, name, True)
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop._rollback_learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop._fact_promotion = "disabled"
    return True

try:
    patch_autonomous_loop()
except Exception as exc:
    print("[PHASE4I_RUNTIME_SCHEMA_GUARD_FIXED2_AUTOLOAD_ERROR]", exc)
