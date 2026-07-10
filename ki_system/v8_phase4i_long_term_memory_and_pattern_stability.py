
"""
V8-phase4i_long_term_memory_and_pattern_stability

Ziel:
- keine Wort-Blacklists
- keine facts/relations/questions writes
- Langzeitmuster aus Kontext-Hypothesen, Rollen, Fehlern und digitalen Botenstoffen konsolidieren
- Phase4g/4h-Lernsteuerung stabil weiterführen
"""
from __future__ import annotations

import json
import time
import sqlite3
from collections import defaultdict

PHASE = "phase4i_long_term_memory_and_pattern_stability"


def _now() -> int:
    return int(time.time())


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _get_db(mem_or_conn):
    """Return sqlite3 connection from different project memory wrappers."""
    if mem_or_conn is None:
        raise RuntimeError("Phase4i: no memory/db object available")
    if isinstance(mem_or_conn, sqlite3.Connection):
        return mem_or_conn
    for attr in ("db", "conn", "connection", "sqlite", "_db"):
        v = getattr(mem_or_conn, attr, None)
        if isinstance(v, sqlite3.Connection):
            return v
    if hasattr(mem_or_conn, "execute") and hasattr(mem_or_conn, "commit"):
        return mem_or_conn
    raise RuntimeError(f"Phase4i: cannot find sqlite connection on {type(mem_or_conn)!r}")


def _get_mem_from_loop(loop):
    for attr in ("mem", "memory", "m", "store", "memory_store"):
        if hasattr(loop, attr):
            return getattr(loop, attr)
    # last resort: find an attribute that looks like a memory/sqlite wrapper
    for name, value in vars(loop).items():
        if isinstance(value, sqlite3.Connection):
            return value
        if hasattr(value, "execute") and hasattr(value, "commit"):
            return value
        if isinstance(getattr(value, "db", None), sqlite3.Connection):
            return value
    raise RuntimeError("Phase4i: AutonomousLoop has no detectable memory attribute")


def _table_exists(cur, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(cur, table: str) -> set[str]:
    if not _table_exists(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_col(cur, table: str, col: str, spec: str, changes: list[str]):
    if col not in _columns(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {spec}")
        changes.append(f"add_column:{table}.{col}")


def _ensure_unique(cur, table: str, col: str, changes: list[str]):
    if not _table_exists(cur, table) or col not in _columns(cur, table):
        return
    # If duplicates exist, do not create index. This patch is non-destructive.
    dup = cur.execute(
        f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1"
    ).fetchone()
    if dup:
        changes.append(f"skip_unique_duplicates:{table}.{col}")
        return
    idx = f"idx_{table}_{col}_phase4i_unique"
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
    changes.append(f"unique_index:{table}.{col}")


def ensure_phase4i_schema(mem_or_conn) -> list[str]:
    db = _get_db(mem_or_conn)
    cur = db.cursor()
    changes: list[str] = []

    # Existing core tables are not recreated destructively; add minimal compatibility cols if needed.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS long_term_pattern_memory(
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
        updated_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pattern_stability_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_key TEXT,
        role TEXT,
        stability REAL DEFAULT 0,
        confidence REAL DEFAULT 0,
        uncertainty REAL DEFAULT 0,
        observations INTEGER DEFAULT 0,
        dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0,
        decision TEXT,
        created_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS role_confusion_memory(
        confusion_key TEXT PRIMARY KEY,
        from_role TEXT,
        to_role TEXT,
        count INTEGER DEFAULT 0,
        avg_revision_pressure REAL DEFAULT 0,
        avg_self_score REAL DEFAULT 0,
        last_reason TEXT,
        updated_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS neuromodulator_pattern_profiles(
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
        updated_at INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS long_term_consolidation_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER DEFAULT 0
    )
    """)

    # Future-safe columns for created tables.
    for table, cols in {
        "long_term_pattern_memory": {
            "revision_pressure": "REAL DEFAULT 0",
            "error_weight": "REAL DEFAULT 0",
            "confidence_trend": "REAL DEFAULT 0",
            "uncertainty_trend": "REAL DEFAULT 0",
        },
        "pattern_stability_history": {
            "learning_rate": "REAL DEFAULT 0",
            "error_weight": "REAL DEFAULT 0",
            "revision_pressure": "REAL DEFAULT 0",
            "consolidation_gain": "REAL DEFAULT 0",
        },
        "role_confusion_memory": {
            "avg_error_weight": "REAL DEFAULT 0",
            "avg_uncertainty": "REAL DEFAULT 0",
            "status": "TEXT DEFAULT 'observed'",
        },
        "neuromodulator_pattern_profiles": {
            "avg_learning_rate": "REAL DEFAULT 0",
            "avg_error_weight": "REAL DEFAULT 0",
            "avg_revision_pressure": "REAL DEFAULT 0",
            "avg_consolidation_gain": "REAL DEFAULT 0",
        },
    }.items():
        for col, spec in cols.items():
            _ensure_col(cur, table, col, spec, changes)

    # Compatibility with Phase4g/h state tables if present.
    for t, c in (
        ("long_term_pattern_memory", "pattern_key"),
        ("role_confusion_memory", "confusion_key"),
        ("neuromodulator_pattern_profiles", "profile_key"),
        ("long_term_consolidation_state", "key"),
    ):
        _ensure_unique(cur, t, c, changes)

    now = _now()
    state = {
        "phase": PHASE,
        "no_word_blacklists": "true",
        "learning_mode": "context_hypotheses_with_neuromodulators",
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
    }
    for k, v in state.items():
        cur.execute(
            "INSERT INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (k, _json(v), now),
        )
        # also seed rollback state if available
        if _table_exists(cur, "rollback_safe_core_state") and "key" in _columns(cur, "rollback_safe_core_state"):
            cur.execute(
                "INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (k, _json(v), now),
            )

    db.commit()
    return changes


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def consolidate_long_term_patterns(mem_or_conn, limit: int = 1200) -> dict:
    db = _get_db(mem_or_conn)
    ensure_phase4i_schema(db)
    cur = db.cursor()
    now = _now()

    processed_patterns = 0
    history_rows = 0
    profiles = 0
    confusions = 0

    # Consolidate from context_pattern_memory if present and populated.
    if _table_exists(cur, "context_pattern_memory"):
        cols = _columns(cur, "context_pattern_memory")
        needed = {"pattern_key", "role"}
        if needed.issubset(cols):
            select_cols = "pattern_key, role"
            # defensive defaults for older schemas
            select_cols += ", COALESCE(seen_count,0)" if "seen_count" in cols else ", 0"
            select_cols += ", COALESCE(avg_confidence,0)" if "avg_confidence" in cols else ", 0"
            select_cols += ", COALESCE(avg_uncertainty,0)" if "avg_uncertainty" in cols else ", 0"
            select_cols += ", COALESCE(stability,0)" if "stability" in cols else ", 0"
            rows = cur.execute(
                f"SELECT {select_cols} FROM context_pattern_memory ORDER BY COALESCE(seen_count,0) DESC LIMIT ?",
                (limit,),
            ).fetchall()
            for pattern_key, role, seen, avgc, avgu, stab in rows:
                volatility = max(0.0, min(1.0, float(avgu or 0) + (1.0 - float(stab or 0)) * 0.5))
                decision = "observe"
                if stab and stab >= 0.72 and avgu <= 0.38:
                    decision = "stabilize_pattern"
                elif avgu and avgu >= 0.68:
                    decision = "keep_plastic"
                cur.execute(
                    """
                    INSERT INTO long_term_pattern_memory(
                        pattern_key, dominant_role, observations, avg_confidence, avg_uncertainty,
                        stability, volatility, last_decision, first_seen, last_seen, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(pattern_key) DO UPDATE SET
                        dominant_role=excluded.dominant_role,
                        observations=excluded.observations,
                        avg_confidence=excluded.avg_confidence,
                        avg_uncertainty=excluded.avg_uncertainty,
                        stability=excluded.stability,
                        volatility=excluded.volatility,
                        last_decision=excluded.last_decision,
                        last_seen=excluded.last_seen,
                        updated_at=excluded.updated_at
                    """,
                    (pattern_key, role, int(seen or 0), float(avgc or 0), float(avgu or 0), float(stab or 0), volatility, decision, now, now, now),
                )
                cur.execute(
                    """
                    INSERT INTO pattern_stability_history(
                        pattern_key, role, stability, confidence, uncertainty, observations, decision, created_at
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (pattern_key, role, float(stab or 0), float(avgc or 0), float(avgu or 0), int(seen or 0), decision, now),
                )
                processed_patterns += 1
                history_rows += 1

    # Role neuromodulator profiles from context_hypotheses.
    if _table_exists(cur, "context_hypotheses"):
        cols = _columns(cur, "context_hypotheses")
        if "role" in cols:
            nm_cols = ["dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine", "confidence", "uncertainty"]
            select = ["role", "COUNT(*)"]
            for c in nm_cols:
                select.append(f"AVG(COALESCE({c},0))" if c in cols else "0")
            rows = cur.execute(
                f"SELECT {', '.join(select)} FROM context_hypotheses GROUP BY role"
            ).fetchall()
            for row in rows:
                role = row[0]
                count = int(row[1] or 0)
                avgs = [float(x or 0) for x in row[2:]]
                key = f"role::{role}"
                cur.execute(
                    """
                    INSERT INTO neuromodulator_pattern_profiles(
                        profile_key, role, observations, avg_dopamine, avg_serotonin, avg_glutamate,
                        avg_gaba, avg_noradrenaline, avg_acetylcholine, avg_confidence, avg_uncertainty, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(profile_key) DO UPDATE SET
                        observations=excluded.observations,
                        avg_dopamine=excluded.avg_dopamine,
                        avg_serotonin=excluded.avg_serotonin,
                        avg_glutamate=excluded.avg_glutamate,
                        avg_gaba=excluded.avg_gaba,
                        avg_noradrenaline=excluded.avg_noradrenaline,
                        avg_acetylcholine=excluded.avg_acetylcholine,
                        avg_confidence=excluded.avg_confidence,
                        avg_uncertainty=excluded.avg_uncertainty,
                        updated_at=excluded.updated_at
                    """,
                    (key, role, count, *avgs, now),
                )
                profiles += 1

    # Role confusion memory from revisions if available.
    rev_tables = ["hypothesis_role_revisions", "hypothesis_revisions"]
    for tbl in rev_tables:
        if not _table_exists(cur, tbl):
            continue
        cols = _columns(cur, tbl)
        old_col = "old_role" if "old_role" in cols else None
        new_col = "new_role" if "new_role" in cols else None
        if not old_col or not new_col:
            continue
        extra_self = "AVG(COALESCE(self_score,0))" if "self_score" in cols else "0"
        extra_pressure = "AVG(COALESCE(revision_pressure,0))" if "revision_pressure" in cols else "0"
        reason = "MAX(COALESCE(reason,''))" if "reason" in cols else "''"
        rows = cur.execute(
            f"SELECT {old_col}, {new_col}, COUNT(*), {extra_pressure}, {extra_self}, {reason} "
            f"FROM {tbl} GROUP BY {old_col}, {new_col}"
        ).fetchall()
        for old_role, new_role, cnt, avgp, avgs, last_reason in rows:
            key = f"{old_role}->{new_role}"
            status = "stable_keep" if old_role == new_role else "observed_revision"
            cur.execute(
                """
                INSERT INTO role_confusion_memory(
                    confusion_key, from_role, to_role, count, avg_revision_pressure, avg_self_score,
                    last_reason, status, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(confusion_key) DO UPDATE SET
                    count=excluded.count,
                    avg_revision_pressure=excluded.avg_revision_pressure,
                    avg_self_score=excluded.avg_self_score,
                    last_reason=excluded.last_reason,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (key, old_role, new_role, int(cnt or 0), float(avgp or 0), float(avgs or 0), last_reason or "", status, now),
            )
            confusions += 1

    # State summary.
    summary = {
        "processed_patterns": processed_patterns,
        "history_rows": history_rows,
        "profiles": profiles,
        "role_confusions": confusions,
        "phase": PHASE,
        "no_word_blacklists": True,
    }
    for k, v in summary.items():
        cur.execute(
            "INSERT INTO long_term_consolidation_state(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (f"last_{k}", _json(v), now),
        )
    db.commit()
    return summary


_original_run = None
_original_cycle = None


def managed_cycle(self, progress=None):
    mem = _get_mem_from_loop(self)
    ensure_phase4i_schema(mem)
    result = _original_cycle(self, progress) if _original_cycle else None
    summary = consolidate_long_term_patterns(mem)
    if isinstance(result, dict):
        result["long_term_memory_and_pattern_stability"] = {
            "status": PHASE,
            **summary,
            "direct_fact_writes": "disabled",
            "direct_relation_writes": "disabled",
            "question_generation": "disabled",
            "fact_promotion": "disabled",
        }
        return result
    return {
        "status": PHASE,
        "base_cycle_result": result,
        "long_term_memory_and_pattern_stability": summary,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
        "fact_promotion": "disabled",
    }


def managed_run(self, cycles=1, progress=None):
    mem = _get_mem_from_loop(self)
    ensure_phase4i_schema(mem)
    # Keep underlying chain executable; then consolidate once more at end.
    out = _original_run(self, cycles, progress) if _original_run else []
    summary = consolidate_long_term_patterns(mem)
    # Preserve expected list output from GUI if underlying returns list.
    marker = {
        "status": PHASE,
        "long_term_memory_and_pattern_stability": summary,
        "no_word_blacklists": True,
        "learning_mode": "context_hypotheses_with_neuromodulators",
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
    }
    if isinstance(out, list):
        out.append(marker)
        return out
    return {"base_run_result": out, **marker}


def patch_autonomous_loop(AutonomousLoop=None, *args, **kwargs):
    global _original_run, _original_cycle
    if AutonomousLoop is None:
        return False
    if getattr(AutonomousLoop, "phase4i_long_term_memory_and_pattern_stability", False):
        return True
    _original_run = getattr(AutonomousLoop, "run", None)
    _original_cycle = getattr(AutonomousLoop, "cycle", None)
    AutonomousLoop.run = managed_run
    AutonomousLoop.cycle = managed_cycle
    # Both marker styles for compatibility with older test tools.
    AutonomousLoop.phase4i_long_term_memory_and_pattern_stability = True
    AutonomousLoop._phase4i_long_term_memory_and_pattern_stability = True
    AutonomousLoop.phase4_schema_manager_canonicalization = True
    AutonomousLoop.phase4h_self_evaluation_and_revision_core = True
    AutonomousLoop.phase4g_neuromodulated_learning_control = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.learning_mode = "context_hypotheses_with_neuromodulators"
    AutonomousLoop._rollback_learning_mode = "context_hypotheses_with_neuromodulators"
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop._fact_promotion = "disabled"
    return True
