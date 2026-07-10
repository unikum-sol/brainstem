
# V8-phase4g_neuromodulated_attention_queue_activation
# Ziel: Digitale Botenstoffe steuern Lernen UND Aufmerksamkeit.
# Sicherheit: keine facts/relations/questions writes, keine Wort-Blacklists, keine Fact-Promotion.
from __future__ import annotations

import json
import math
import time
import sqlite3
from collections import defaultdict

PHASE = "phase4g_neuromodulated_attention_queue_activation"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"


def _now() -> int:
    return int(time.time())


def _json(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"repr": repr(obj)}, ensure_ascii=False)


def _clamp(v, lo=0.0, hi=1.0):
    try:
        v = float(v)
    except Exception:
        v = 0.0
    return max(lo, min(hi, v))


def _get_conn(mem_or_loop):
    """Robust: akzeptiert Memory-Objekt, AutonomousLoop oder sqlite3.Connection."""
    if isinstance(mem_or_loop, sqlite3.Connection):
        return mem_or_loop
    # direkte Memory-ähnliche Objekte
    for attr in ("db", "conn", "connection"):
        db = getattr(mem_or_loop, attr, None)
        if isinstance(db, sqlite3.Connection):
            return db
    # Loop-Objekte: bekannte Namen
    for attr in ("mem", "memory", "m", "store", "memory_store"):
        obj = getattr(mem_or_loop, attr, None)
        if obj is not None:
            try:
                return _get_conn(obj)
            except Exception:
                pass
    # Fallback: Attribute durchsuchen
    for obj in getattr(mem_or_loop, "__dict__", {}).values():
        try:
            return _get_conn(obj)
        except Exception:
            continue
    raise AttributeError("Keine sqlite3.Connection im Objekt gefunden")


def _table_exists(cur, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(cur, table: str):
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _ensure_table(cur, table: str, cols_sql: str):
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table} ({cols_sql})")


def _add_col(cur, table: str, col: str, decl: str, changes: list[str]):
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        changes.append(f"add_column:{table}.{col}")


def _unique(cur, table: str, col: str, changes: list[str]):
    if _table_exists(cur, table) and col in _cols(cur, table):
        # Nur setzen, wenn keine Duplikate vorhanden sind.
        dup = cur.execute(f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1 LIMIT 1").fetchone()
        if dup:
            changes.append(f"skip_unique_duplicates:{table}.{col}")
            return
        idx = f"idx_{table}_{col}_phase4g_unique"
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({col})")
        changes.append(f"unique_index:{table}.{col}")


def ensure_phase4g_schema(mem_or_loop) -> list[str]:
    con = _get_conn(mem_or_loop)
    cur = con.cursor()
    changes: list[str] = []

    # Bestehende Kern-Tabellen tolerant anlegen/erweitern.
    _ensure_table(cur, "reading_queue", "chunk_id INTEGER PRIMARY KEY, priority REAL DEFAULT 0, reason TEXT, attention_score REAL DEFAULT 0, read_count INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', last_read INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0")
    for c, d in [
        ("priority", "REAL DEFAULT 0"), ("reason", "TEXT"), ("attention_score", "REAL DEFAULT 0"),
        ("read_count", "INTEGER DEFAULT 0"), ("status", "TEXT DEFAULT 'pending'"), ("last_read", "INTEGER DEFAULT 0"), ("updated_at", "INTEGER DEFAULT 0"),
    ]:
        _add_col(cur, "reading_queue", c, d, changes)

    _ensure_table(cur, "context_hypotheses", "id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, role TEXT, subject TEXT, relation_hint TEXT, object TEXT, text_excerpt TEXT, source_title TEXT, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1, status TEXT DEFAULT 'hypothesis', dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, signature TEXT, evidence_count INTEGER DEFAULT 1, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0")
    for c, d in [
        ("role", "TEXT"), ("subject", "TEXT"), ("relation_hint", "TEXT"), ("object", "TEXT"),
        ("text_excerpt", "TEXT"), ("source_title", "TEXT"), ("confidence", "REAL DEFAULT 0"),
        ("uncertainty", "REAL DEFAULT 1"), ("status", "TEXT DEFAULT 'hypothesis'"),
        ("dopamine", "REAL DEFAULT 0"), ("serotonin", "REAL DEFAULT 0"), ("glutamate", "REAL DEFAULT 0"),
        ("gaba", "REAL DEFAULT 0"), ("noradrenaline", "REAL DEFAULT 0"), ("acetylcholine", "REAL DEFAULT 0"),
        ("signature", "TEXT"), ("evidence_count", "INTEGER DEFAULT 1"), ("created_at", "INTEGER DEFAULT 0"), ("updated_at", "INTEGER DEFAULT 0"),
    ]:
        _add_col(cur, "context_hypotheses", c, d, changes)

    _ensure_table(cur, "neuromodulated_attention_events", "id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, hypothesis_id INTEGER, event_type TEXT, attention_reason TEXT, novelty REAL DEFAULT 0, uncertainty REAL DEFAULT 0, reward REAL DEFAULT 0, fatigue REAL DEFAULT 0, attention_score REAL DEFAULT 0, dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, summary TEXT, details TEXT, created_at INTEGER DEFAULT 0")
    for c, d in [
        ("chunk_id", "INTEGER"), ("hypothesis_id", "INTEGER"), ("event_type", "TEXT"), ("attention_reason", "TEXT"),
        ("novelty", "REAL DEFAULT 0"), ("uncertainty", "REAL DEFAULT 0"), ("reward", "REAL DEFAULT 0"),
        ("fatigue", "REAL DEFAULT 0"), ("attention_score", "REAL DEFAULT 0"), ("dopamine", "REAL DEFAULT 0"),
        ("serotonin", "REAL DEFAULT 0"), ("glutamate", "REAL DEFAULT 0"), ("gaba", "REAL DEFAULT 0"),
        ("noradrenaline", "REAL DEFAULT 0"), ("acetylcholine", "REAL DEFAULT 0"), ("summary", "TEXT"),
        ("details", "TEXT"), ("created_at", "INTEGER DEFAULT 0"),
    ]:
        _add_col(cur, "neuromodulated_attention_events", c, d, changes)

    _ensure_table(cur, "hypothesis_feedback", "id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, feedback_type TEXT, signal REAL DEFAULT 0, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0")
    for c, d in [("hypothesis_id", "INTEGER"), ("feedback_type", "TEXT"), ("signal", "REAL DEFAULT 0"), ("reason", "TEXT"), ("details", "TEXT"), ("created_at", "INTEGER DEFAULT 0")]:
        _add_col(cur, "hypothesis_feedback", c, d, changes)

    _ensure_table(cur, "hypothesis_revisions", "id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, old_role TEXT, new_role TEXT, old_confidence REAL DEFAULT 0, new_confidence REAL DEFAULT 0, old_uncertainty REAL DEFAULT 1, new_uncertainty REAL DEFAULT 1, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0")
    for c, d in [("hypothesis_id", "INTEGER"), ("old_role", "TEXT"), ("new_role", "TEXT"), ("old_confidence", "REAL DEFAULT 0"), ("new_confidence", "REAL DEFAULT 0"), ("old_uncertainty", "REAL DEFAULT 1"), ("new_uncertainty", "REAL DEFAULT 1"), ("reason", "TEXT"), ("details", "TEXT"), ("created_at", "INTEGER DEFAULT 0")]:
        _add_col(cur, "hypothesis_revisions", c, d, changes)

    _ensure_table(cur, "hypothesis_error_events", "id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, error_type TEXT, severity REAL DEFAULT 0, role TEXT, error_signal REAL DEFAULT 0, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0")
    for c, d in [("hypothesis_id", "INTEGER"), ("error_type", "TEXT"), ("severity", "REAL DEFAULT 0"), ("role", "TEXT"), ("error_signal", "REAL DEFAULT 0"), ("reason", "TEXT"), ("details", "TEXT"), ("created_at", "INTEGER DEFAULT 0")]:
        _add_col(cur, "hypothesis_error_events", c, d, changes)

    _ensure_table(cur, "chunk_attention_scores", "chunk_id INTEGER PRIMARY KEY, attention_score REAL DEFAULT 0, novelty_score REAL DEFAULT 0, uncertainty_score REAL DEFAULT 0, reward_score REAL DEFAULT 0, fatigue_score REAL DEFAULT 0, learning_rate REAL DEFAULT 0, error_weight REAL DEFAULT 0, revision_pressure REAL DEFAULT 0, consolidation_gain REAL DEFAULT 0, exploration_pressure REAL DEFAULT 0, inhibition_level REAL DEFAULT 0, last_reason TEXT, updated_at INTEGER DEFAULT 0")
    for c, d in [
        ("attention_score", "REAL DEFAULT 0"), ("novelty_score", "REAL DEFAULT 0"), ("uncertainty_score", "REAL DEFAULT 0"),
        ("reward_score", "REAL DEFAULT 0"), ("fatigue_score", "REAL DEFAULT 0"), ("learning_rate", "REAL DEFAULT 0"),
        ("error_weight", "REAL DEFAULT 0"), ("revision_pressure", "REAL DEFAULT 0"), ("consolidation_gain", "REAL DEFAULT 0"),
        ("exploration_pressure", "REAL DEFAULT 0"), ("inhibition_level", "REAL DEFAULT 0"), ("last_reason", "TEXT"), ("updated_at", "INTEGER DEFAULT 0"),
    ]:
        _add_col(cur, "chunk_attention_scores", c, d, changes)

    _ensure_table(cur, "attention_queue_state", "key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0")
    for c, d in [("value", "TEXT"), ("updated_at", "INTEGER DEFAULT 0")]: _add_col(cur, "attention_queue_state", c, d, changes)
    _ensure_table(cur, "reading_strategy_state", "key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0")
    for c, d in [("value", "TEXT"), ("updated_at", "INTEGER DEFAULT 0")]: _add_col(cur, "reading_strategy_state", c, d, changes)

    _ensure_table(cur, "neuromodulator_learning_state", "id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id TEXT, dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, learning_rate REAL DEFAULT 0, error_weight REAL DEFAULT 0, revision_pressure REAL DEFAULT 0, consolidation_gain REAL DEFAULT 0, exploration_pressure REAL DEFAULT 0, inhibition_level REAL DEFAULT 0, summary TEXT, created_at INTEGER DEFAULT 0")

    _ensure_table(cur, "hypothesis_learning_updates", "id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, old_confidence REAL DEFAULT 0, new_confidence REAL DEFAULT 0, old_uncertainty REAL DEFAULT 1, new_uncertainty REAL DEFAULT 1, dopamine_effect REAL DEFAULT 0, serotonin_effect REAL DEFAULT 0, glutamate_effect REAL DEFAULT 0, gaba_effect REAL DEFAULT 0, noradrenaline_effect REAL DEFAULT 0, acetylcholine_effect REAL DEFAULT 0, update_reason TEXT, created_at INTEGER DEFAULT 0")

    _ensure_table(cur, "sleep_consolidation_decisions", "id INTEGER PRIMARY KEY AUTOINCREMENT, cluster_key TEXT, old_stability REAL DEFAULT 0, new_stability REAL DEFAULT 0, dopamine_gain REAL DEFAULT 0, serotonin_stabilization REAL DEFAULT 0, gaba_inhibition REAL DEFAULT 0, glutamate_plasticity REAL DEFAULT 0, decision TEXT, details TEXT, created_at INTEGER DEFAULT 0")

    # Tabellen aus Phase4def vollständig absichern.
    _ensure_table(cur, "hypothesis_clusters", "cluster_key TEXT PRIMARY KEY, role TEXT, size INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, example TEXT, updated_at INTEGER DEFAULT 0")
    for c, d in [("role", "TEXT"), ("size", "INTEGER DEFAULT 0"), ("avg_confidence", "REAL DEFAULT 0"), ("avg_uncertainty", "REAL DEFAULT 0"), ("stability", "REAL DEFAULT 0"), ("example", "TEXT"), ("updated_at", "INTEGER DEFAULT 0")]:
        _add_col(cur, "hypothesis_clusters", c, d, changes)

    _ensure_table(cur, "hypothesis_stability_scores", "hypothesis_id INTEGER PRIMARY KEY, stability REAL DEFAULT 0, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1, feedback_count INTEGER DEFAULT 0, error_count INTEGER DEFAULT 0, role TEXT, evidence_count INTEGER DEFAULT 0, conflict_count INTEGER DEFAULT 0, last_reason TEXT, updated_at INTEGER DEFAULT 0")
    for c, d in [("stability", "REAL DEFAULT 0"), ("confidence", "REAL DEFAULT 0"), ("uncertainty", "REAL DEFAULT 1"), ("feedback_count", "INTEGER DEFAULT 0"), ("error_count", "INTEGER DEFAULT 0"), ("role", "TEXT"), ("evidence_count", "INTEGER DEFAULT 0"), ("conflict_count", "INTEGER DEFAULT 0"), ("last_reason", "TEXT"), ("updated_at", "INTEGER DEFAULT 0")]:
        _add_col(cur, "hypothesis_stability_scores", c, d, changes)

    _ensure_table(cur, "context_pattern_memory", "pattern_key TEXT PRIMARY KEY, role TEXT, seen_count INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, updated_at INTEGER DEFAULT 0")
    for c, d in [("role", "TEXT"), ("seen_count", "INTEGER DEFAULT 0"), ("avg_confidence", "REAL DEFAULT 0"), ("avg_uncertainty", "REAL DEFAULT 0"), ("stability", "REAL DEFAULT 0"), ("updated_at", "INTEGER DEFAULT 0")]:
        _add_col(cur, "context_pattern_memory", c, d, changes)

    _ensure_table(cur, "neuromodulator_sleep_events", "id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, summary TEXT, details TEXT, dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, created_at INTEGER DEFAULT 0")
    for c, d in [("event_type", "TEXT"), ("summary", "TEXT"), ("details", "TEXT"), ("dopamine", "REAL DEFAULT 0"), ("serotonin", "REAL DEFAULT 0"), ("glutamate", "REAL DEFAULT 0"), ("gaba", "REAL DEFAULT 0"), ("noradrenaline", "REAL DEFAULT 0"), ("acetylcholine", "REAL DEFAULT 0"), ("created_at", "INTEGER DEFAULT 0")]:
        _add_col(cur, "neuromodulator_sleep_events", c, d, changes)

    _ensure_table(cur, "learning_strategy_state", "key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0")
    for c, d in [("value", "TEXT"), ("updated_at", "INTEGER DEFAULT 0")]: _add_col(cur, "learning_strategy_state", c, d, changes)
    _ensure_table(cur, "rollback_safe_core_state", "key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0")
    for c, d in [("value", "TEXT"), ("updated_at", "INTEGER DEFAULT 0")]: _add_col(cur, "rollback_safe_core_state", c, d, changes)

    # Unique-Indizes für ON CONFLICT.
    for t, c in [
        ("reading_queue", "chunk_id"), ("chunk_attention_scores", "chunk_id"), ("attention_queue_state", "key"),
        ("reading_strategy_state", "key"), ("hypothesis_clusters", "cluster_key"), ("hypothesis_stability_scores", "hypothesis_id"),
        ("context_pattern_memory", "pattern_key"), ("learning_strategy_state", "key"), ("rollback_safe_core_state", "key"),
        ("context_role_stats", "role"),
    ]:
        _unique(cur, t, c, changes)

    # Sicherheitsstatus.
    now = _now()
    state = {
        "phase": PHASE,
        "no_word_blacklists": "true",
        "learning_mode": LEARNING_MODE,
        "fact_promotion": "disabled",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
    }
    for k, v in state.items():
        cur.execute("INSERT INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (k, repr(v), now))

    con.commit()
    return changes


def _seed_reading_queue(con, minimum_pending=2000, batch=640):
    cur = con.cursor()
    if not _table_exists(cur, "chunks") or not _table_exists(cur, "reading_queue"):
        return 0
    pending = cur.execute("SELECT COUNT(*) FROM reading_queue WHERE status='pending'").fetchone()[0]
    if pending >= minimum_pending:
        return 0
    now = _now()
    rows = cur.execute("""
        SELECT c.id FROM chunks c
        LEFT JOIN reading_queue rq ON rq.chunk_id=c.id
        WHERE rq.chunk_id IS NULL
        ORDER BY c.id
        LIMIT ?
    """, (batch,)).fetchall()
    for (cid,) in rows:
        cur.execute("INSERT OR IGNORE INTO reading_queue(chunk_id,priority,reason,attention_score,read_count,status,last_read,updated_at) VALUES(?,?,?,?,?,?,?,?)", (cid, 0.5, "phase4g_seed_pending", 0.5, 0, "pending", 0, now))
    con.commit()
    return len(rows)


def _aggregate_neuromodulators(con):
    cur = con.cursor()
    if not _table_exists(cur, "neuromodulated_attention_events"):
        return {}
    row = cur.execute("""
        SELECT AVG(COALESCE(dopamine,0)), AVG(COALESCE(serotonin,0)), AVG(COALESCE(glutamate,0)),
               AVG(COALESCE(gaba,0)), AVG(COALESCE(noradrenaline,0)), AVG(COALESCE(acetylcholine,0)),
               AVG(COALESCE(uncertainty,0)), AVG(COALESCE(reward,0)), AVG(COALESCE(fatigue,0)), COUNT(*)
        FROM neuromodulated_attention_events
    """).fetchone()
    if not row or not row[-1]:
        return {
            "dopamine": 0.35, "serotonin": 0.45, "glutamate": 0.45, "gaba": 0.35,
            "noradrenaline": 0.45, "acetylcholine": 0.45, "uncertainty": 0.5, "reward": 0.25, "fatigue": 0.1, "n": 0,
        }
    keys = ["dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine", "uncertainty", "reward", "fatigue", "n"]
    return {k: (0 if v is None else float(v)) for k, v in zip(keys, row)}


def _learning_control_values(nm):
    dopamine = _clamp(nm.get("dopamine", 0.35))
    serotonin = _clamp(nm.get("serotonin", 0.45))
    glutamate = _clamp(nm.get("glutamate", 0.45))
    gaba = _clamp(nm.get("gaba", 0.35))
    nor = _clamp(nm.get("noradrenaline", 0.45))
    ach = _clamp(nm.get("acetylcholine", 0.45))
    unc = _clamp(nm.get("uncertainty", 0.5))
    rew = _clamp(nm.get("reward", 0.25))
    fat = _clamp(nm.get("fatigue", 0.1))
    learning_rate = _clamp(0.12 + 0.18*glutamate + 0.10*ach + 0.08*dopamine - 0.12*gaba)
    error_weight = _clamp(0.20 + 0.35*nor + 0.25*unc - 0.08*serotonin)
    revision_pressure = _clamp(0.15 + 0.30*nor + 0.25*unc - 0.12*gaba - 0.05*serotonin)
    consolidation_gain = _clamp(0.10 + 0.25*dopamine + 0.22*serotonin - 0.10*unc)
    exploration_pressure = _clamp(0.15 + 0.35*glutamate + 0.20*nor - 0.10*gaba)
    inhibition_level = _clamp(0.10 + 0.35*gaba + 0.18*unc + 0.10*fat)
    attention_score = _clamp(0.18 + 0.22*nor + 0.20*ach + 0.16*unc + 0.14*rew + 0.10*glutamate - 0.16*fat - 0.10*gaba)
    return dict(learning_rate=learning_rate, error_weight=error_weight, revision_pressure=revision_pressure,
                consolidation_gain=consolidation_gain, exploration_pressure=exploration_pressure,
                inhibition_level=inhibition_level, attention_score=attention_score)


def activate_neuromodulated_learning_control(mem_or_loop, limit_hypotheses=240) -> dict:
    """Aktiviert Lernen: Attention, Lernrate, Fehlergewichtung, Revision, Konsolidierung."""
    con = _get_conn(mem_or_loop)
    ensure_phase4g_schema(con)
    cur = con.cursor()
    now = _now()
    seeded = _seed_reading_queue(con)
    nm = _aggregate_neuromodulators(con)
    ctrl = _learning_control_values(nm)

    cycle_id = f"phase4g:{now}"
    cur.execute("""
        INSERT INTO neuromodulator_learning_state(cycle_id,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,
            learning_rate,error_weight,revision_pressure,consolidation_gain,exploration_pressure,inhibition_level,summary,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (cycle_id, nm.get('dopamine',0), nm.get('serotonin',0), nm.get('glutamate',0), nm.get('gaba',0), nm.get('noradrenaline',0), nm.get('acetylcholine',0),
          ctrl['learning_rate'], ctrl['error_weight'], ctrl['revision_pressure'], ctrl['consolidation_gain'], ctrl['exploration_pressure'], ctrl['inhibition_level'], _json({'source':'aggregate_attention_events'}), now))

    # Chunk Attention aus Attention Events berechnen.
    chunk_rows = cur.execute("""
        SELECT chunk_id,
               AVG(COALESCE(novelty,0)), AVG(COALESCE(uncertainty,0)), AVG(COALESCE(reward,0)), AVG(COALESCE(fatigue,0)),
               AVG(COALESCE(dopamine,0)), AVG(COALESCE(gaba,0)), AVG(COALESCE(noradrenaline,0)), AVG(COALESCE(acetylcholine,0)), COUNT(*)
        FROM neuromodulated_attention_events
        WHERE chunk_id IS NOT NULL
        GROUP BY chunk_id
        ORDER BY COUNT(*) DESC, MAX(id) DESC
        LIMIT 500
    """).fetchall() if _table_exists(cur, "neuromodulated_attention_events") else []

    updated_chunks = 0
    for cid, nov, unc, rew, fat, dop, gaba, nor, ach, n in chunk_rows:
        nov, unc, rew, fat, dop, gaba, nor, ach = [_clamp(x or 0) for x in (nov, unc, rew, fat, dop, gaba, nor, ach)]
        score = _clamp(0.18 + 0.18*nov + 0.18*unc + 0.14*rew + 0.14*nor + 0.12*ach + 0.08*dop - 0.12*fat - 0.10*gaba)
        cur.execute("""
            INSERT INTO chunk_attention_scores(chunk_id,attention_score,novelty_score,uncertainty_score,reward_score,fatigue_score,
                learning_rate,error_weight,revision_pressure,consolidation_gain,exploration_pressure,inhibition_level,last_reason,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(chunk_id) DO UPDATE SET attention_score=excluded.attention_score, novelty_score=excluded.novelty_score,
                uncertainty_score=excluded.uncertainty_score, reward_score=excluded.reward_score, fatigue_score=excluded.fatigue_score,
                learning_rate=excluded.learning_rate, error_weight=excluded.error_weight, revision_pressure=excluded.revision_pressure,
                consolidation_gain=excluded.consolidation_gain, exploration_pressure=excluded.exploration_pressure,
                inhibition_level=excluded.inhibition_level, last_reason=excluded.last_reason, updated_at=excluded.updated_at
        """, (cid, score, nov, unc, rew, fat, ctrl['learning_rate'], ctrl['error_weight'], ctrl['revision_pressure'], ctrl['consolidation_gain'], ctrl['exploration_pressure'], ctrl['inhibition_level'], 'phase4g_neuromodulated_learning_control', now))
        cur.execute("UPDATE reading_queue SET priority=?, attention_score=?, reason=?, updated_at=? WHERE chunk_id=?", (score, score, 'phase4g_neuromodulated_learning_control', now, cid))
        updated_chunks += 1

    # Hypothesen-Lernupdates: Botenstoffe steuern Confidence/Uncertainty, aber keine Faktenpromotion.
    hyp_rows = cur.execute("""
        SELECT id, role, COALESCE(confidence,0), COALESCE(uncertainty,1)
        FROM context_hypotheses
        ORDER BY id DESC
        LIMIT ?
    """, (limit_hypotheses,)).fetchall() if _table_exists(cur, "context_hypotheses") else []
    updated_hyp = 0
    revisions = 0
    for hid, role, conf, unc in hyp_rows:
        oldc, oldu = _clamp(conf), _clamp(unc)
        dopamine_effect = 0.035 * _clamp(nm.get('dopamine', 0.35))
        serotonin_effect = 0.020 * _clamp(nm.get('serotonin', 0.45))
        glutamate_effect = 0.020 * _clamp(nm.get('glutamate', 0.45))
        ach_effect = 0.018 * _clamp(nm.get('acetylcholine', 0.45))
        gaba_effect = -0.030 * ctrl['inhibition_level']
        old_uncertainty_high = (oldu > oldc + 0.18)
        nor_effect = (-0.025 * ctrl['error_weight']) if old_uncertainty_high else (0.010 * _clamp(nm.get('noradrenaline',0.45)))
        delta_c = ctrl['learning_rate'] * (dopamine_effect + serotonin_effect + glutamate_effect + ach_effect + nor_effect + gaba_effect)
        delta_u = -ctrl['consolidation_gain'] * 0.025 + ctrl['error_weight'] * (0.018 if old_uncertainty_high else -0.008) + ctrl['inhibition_level']*0.006
        newc = _clamp(oldc + delta_c)
        newu = _clamp(oldu + delta_u)
        if abs(newc-oldc) < 0.0005 and abs(newu-oldu) < 0.0005:
            continue
        cur.execute("""
            INSERT INTO hypothesis_learning_updates(hypothesis_id,old_confidence,new_confidence,old_uncertainty,new_uncertainty,
                dopamine_effect,serotonin_effect,glutamate_effect,gaba_effect,noradrenaline_effect,acetylcholine_effect,update_reason,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (hid, oldc, newc, oldu, newu, dopamine_effect, serotonin_effect, glutamate_effect, gaba_effect, nor_effect, ach_effect, 'phase4g_neuromodulated_learning_control', now))
        cur.execute("UPDATE context_hypotheses SET confidence=?, uncertainty=?, updated_at=? WHERE id=?", (newc, newu, now, hid))
        if old_uncertainty_high and ctrl['revision_pressure'] > 0.35:
            cur.execute("""
                INSERT INTO hypothesis_revisions(hypothesis_id,old_role,new_role,old_confidence,new_confidence,old_uncertainty,new_uncertainty,reason,details,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (hid, role, role, oldc, newc, oldu, newu, 'revision_pressure_without_role_change', _json({'revision_pressure': ctrl['revision_pressure']}), now))
            revisions += 1
        updated_hyp += 1

    # Fehlerereignisse mit Error Weight markieren.
    if _table_exists(cur, "hypothesis_error_events"):
        cur.execute("UPDATE hypothesis_error_events SET error_signal=COALESCE(error_signal, severity, 0) * ?, reason=COALESCE(reason,'phase4g_weighted_error_signal') WHERE error_signal IS NULL OR error_signal=0", (ctrl['error_weight'],))

    # Schlafkonsolidierungsentscheidungen.
    decision_count = 0
    if _table_exists(cur, "hypothesis_clusters"):
        for key, stab in cur.execute("SELECT cluster_key, COALESCE(stability,0) FROM hypothesis_clusters ORDER BY updated_at DESC LIMIT 80").fetchall():
            old = _clamp(stab)
            new = _clamp(old + ctrl['consolidation_gain']*0.05 + _clamp(nm.get('dopamine',0))*0.02 - ctrl['inhibition_level']*0.025)
            decision = 'stabilize' if new >= old else 'hold_due_to_inhibition'
            cur.execute("""
                INSERT INTO sleep_consolidation_decisions(cluster_key,old_stability,new_stability,dopamine_gain,serotonin_stabilization,gaba_inhibition,glutamate_plasticity,decision,details,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (key, old, new, _clamp(nm.get('dopamine',0))*0.02, _clamp(nm.get('serotonin',0))*0.02, ctrl['inhibition_level']*0.025, ctrl['exploration_pressure']*0.02, decision, _json({'phase':PHASE}), now))
            cur.execute("UPDATE hypothesis_clusters SET stability=?, updated_at=? WHERE cluster_key=?", (new, now, key))
            decision_count += 1

    for key, value in {
        'phase': PHASE,
        'learning_mode': LEARNING_MODE,
        'last_learning_rate': ctrl['learning_rate'],
        'last_error_weight': ctrl['error_weight'],
        'last_revision_pressure': ctrl['revision_pressure'],
        'last_consolidation_gain': ctrl['consolidation_gain'],
        'last_exploration_pressure': ctrl['exploration_pressure'],
        'last_inhibition_level': ctrl['inhibition_level'],
        'last_updated_chunks': updated_chunks,
        'last_updated_hypotheses': updated_hyp,
        'last_sleep_decisions': decision_count,
    }.items():
        cur.execute("INSERT INTO reading_strategy_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, repr(value), now))
        cur.execute("INSERT INTO attention_queue_state(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key, repr(value), now))

    con.commit()
    return {
        'status': PHASE,
        'seeded_reading_queue': seeded,
        'updated_chunk_attention_scores': updated_chunks,
        'updated_hypothesis_learning': updated_hyp,
        'revision_events': revisions,
        'sleep_consolidation_decisions': decision_count,
        'learning_control': ctrl,
        'no_word_blacklists': True,
        'fact_promotion': 'disabled',
        'direct_fact_writes': 'disabled',
        'direct_relation_writes': 'disabled',
        'question_generation': 'disabled',
    }


def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop as AL
        AutonomousLoop = AL
    # Idempotent speichern
    if not hasattr(AutonomousLoop, '_phase4g_previous_run'):
        AutonomousLoop._phase4g_previous_run = AutonomousLoop.run
    if not hasattr(AutonomousLoop, '_phase4g_previous_cycle'):
        AutonomousLoop._phase4g_previous_cycle = AutonomousLoop.cycle
    prev_run = AutonomousLoop._phase4g_previous_run
    prev_cycle = AutonomousLoop._phase4g_previous_cycle

    def managed_cycle(self, progress=None):
        ensure_phase4g_schema(self)
        # Erst bestehendes Phase4def-Lernen ausführen, dann Lernsteuerung anwenden.
        result = prev_cycle(self, progress)
        control = activate_neuromodulated_learning_control(self)
        if isinstance(result, dict):
            result['phase4g_neuromodulated_learning_control'] = control
            return result
        return {'phase4_previous_cycle_result': result, 'phase4g_neuromodulated_learning_control': control}

    def managed_run(self, cycles=1, progress=None):
        ensure_phase4g_schema(self)
        results = []
        # Wir rufen bewusst cycle direkt, damit Phase4g sicher nach jedem Zyklus greift.
        for i in range(int(cycles or 1)):
            if getattr(self, 'stop_requested', False) or getattr(self, 'cancel', False):
                break
            if progress:
                try:
                    progress(i+1, cycles, 'phase4g neuromodulated learning control')
                except Exception:
                    pass
            results.append(managed_cycle(self, progress=None))
        return results

    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    # Marker, beide Namensvarianten.
    for name in [
        'phase4g_neuromodulated_attention_queue_activation', '_phase4g_neuromodulated_attention_queue_activation',
        'phase4g_neuromodulated_learning_control', '_phase4g_neuromodulated_learning_control',
    ]:
        setattr(AutonomousLoop, name, True)
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop._no_word_blacklists = True
    AutonomousLoop.learning_mode = LEARNING_MODE
    AutonomousLoop._rollback_learning_mode = LEARNING_MODE
    AutonomousLoop.fact_promotion = 'disabled'
    AutonomousLoop._fact_promotion = 'disabled'
    return AutonomousLoop


# Beim direkten Import patchen, wenn möglich.
try:
    from ki_system.autonomous import AutonomousLoop as _AL
    patch_autonomous_loop(_AL)
except Exception as _exc:
    # Nicht crashen: Installer/Test kann explizit patchen.
    pass
