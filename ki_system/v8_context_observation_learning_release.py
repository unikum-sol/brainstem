# -*- coding: utf-8 -*-
"""Canonical BrainStem raw-observation learning entry point.

This module owns only input observation, exact signature re-observation,
chunk provenance, and sensory-deprivation input suppression. Semantic
learning, consolidation, roles, confidence, and outcomes remain downstream.
"""
from __future__ import annotations

import hashlib
import json
import re
import time

from ki_system.db_bootstrap import ensure_schema_for

PHASE = "context_observation_learning_release"
LEARNING_MODE = "context_hypotheses_with_neuromodulators"
_SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WS_RE = re.compile(r"\s+")
_REQUIRED_SCHEMA = {
    "reading_queue": {"chunk_id", "priority", "reason", "attention_score", "read_count", "status", "last_read", "updated_at"},
    "context_hypotheses": {"id", "chunk_id", "role", "subject", "relation_hint", "object", "text_excerpt", "source_title", "confidence", "uncertainty", "status", "dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine", "signature", "evidence_count", "created_at", "updated_at"},
    "context_learning_events": {"id", "hypothesis_id", "event_type", "role", "details", "dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine", "created_at"},
}


from ki_system import learning_clock as _learning_clock
def _now():
    return _learning_clock.now()


def _norm(value, limit=700):
    return _WS_RE.sub(" ", (value or "").replace("\x00", " ")).strip()[:limit]


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _db(loop):
    memory = getattr(loop, "mem", None) or getattr(loop, "memory", None) or getattr(loop, "db", None)
    connection = getattr(memory, "db", None) or getattr(memory, "conn", None) or memory
    if not hasattr(connection, "execute"):
        raise RuntimeError("sqlite connection not found")
    return connection


def _table_exists(connection, table):
    return connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(connection, table):
    if not _table_exists(connection, table):
        return set()
    return {row[1] for row in connection.execute("PRAGMA table_info(" + table + ")").fetchall()}


def _self_check_schema(connection):
    missing = []
    for table, required in _REQUIRED_SCHEMA.items():
        absent = sorted(required - _columns(connection, table))
        missing.extend(table + "." + column for column in absent)
    if missing:
        raise RuntimeError("Context observation schema missing: " + ", ".join(missing))
    return True


_CHECKED = {}


def ensure_schema(connection):
    # Checked once per connection; insert_observation() calls this per sentence.
    if _CHECKED.get(id(connection)) is connection:
        return True
    ensure_schema_for(connection)
    _self_check_schema(connection)
    if len(_CHECKED) > 256:
        _CHECKED.clear()
    _CHECKED[id(connection)] = connection
    return True


def _chunk_columns(connection):
    columns = _columns(connection, "chunks")
    chunk_id = "id" if "id" in columns else ("chunk_id" if "chunk_id" in columns else None)
    text = "text" if "text" in columns else ("content" if "content" in columns else None)
    title = "title" if "title" in columns else None
    return chunk_id, text, title


def _neuromodulators(connection):
    defaults = {
        "dopamine": 0.5,
        "serotonin": 0.6,
        "glutamate": 0.4,
        "gaba": 0.4,
        "noradrenaline": 0.3,
        "acetylcholine": 0.5,
    }
    if not _table_exists(connection, "neuromodulator_state"):
        return defaults
    columns = _columns(connection, "neuromodulator_state")
    if not {"key", "value"}.issubset(columns):
        return defaults
    values = dict(connection.execute("SELECT key,value FROM neuromodulator_state").fetchall())
    for key in tuple(defaults):
        try:
            defaults[key] = float(values.get(key, defaults[key]))
        except (TypeError, ValueError):
            pass
    return defaults


def _deprivation_active(connection):
    if not _table_exists(connection, "deprivation_state"):
        return False
    columns = _columns(connection, "deprivation_state")
    if not {"key", "value"}.issubset(columns):
        return False
    row = connection.execute("SELECT value FROM deprivation_state WHERE key=?", ("active",)).fetchone()
    if not row:
        return False
    return str(row[0]).strip().strip('"').strip("'").lower() in {"1", "true", "yes", "on", "active"}


SEED_STATE_TABLE = "reading_queue_seed_state"


def seed_queue(connection, target=2000):
    ensure_schema(connection)
    if not _table_exists(connection, "chunks"):
        return {"seeded": 0, "reason": "chunks_missing"}
    pending = connection.execute("SELECT COUNT(*) FROM reading_queue WHERE status='pending'").fetchone()[0]
    if pending >= target:
        return {"seeded": 0, "reason": "enough_pending", "pending": pending}
    chunk_id, _text, _title = _chunk_columns(connection)
    if not chunk_id:
        return {"seeded": 0, "reason": "chunk_id_missing"}
    # Once every chunk is in the queue, the search below finds nothing until
    # new chunks are imported. Queue rows are never deleted while learning
    # (only a learning reset clears the queue, and it clears this table too),
    # and new chunks get higher ids, so an unchanged largest chunk id means
    # the search would still find nothing. Saves a scan of all chunks.
    connection.execute("CREATE TABLE IF NOT EXISTS " + SEED_STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT)")
    max_id = connection.execute("SELECT MAX(" + chunk_id + ") FROM chunks").fetchone()[0]
    marker = connection.execute("SELECT value FROM " + SEED_STATE_TABLE + " WHERE key='all_queued_up_to_chunk_id'").fetchone()
    if marker is not None and max_id is not None and str(max_id) == str(marker[0]):
        connection.commit()
        return {"seeded": 0, "pending_before": pending}
    rows = connection.execute(
        "SELECT c." + chunk_id + " FROM chunks c LEFT JOIN reading_queue rq ON rq.chunk_id=c." + chunk_id +
        " WHERE rq.chunk_id IS NULL ORDER BY c." + chunk_id + " ASC LIMIT ?",
        (target - pending,),
    ).fetchall()
    if len(rows) < target - pending and max_id is not None:
        connection.execute("INSERT OR REPLACE INTO " + SEED_STATE_TABLE + "(key,value) VALUES('all_queued_up_to_chunk_id',?)",
                           (str(max_id),))
    now = _now()
    for (value,) in rows:
        connection.execute(
            "INSERT OR IGNORE INTO reading_queue(chunk_id,priority,reason,attention_score,status,updated_at) VALUES(?,?,?,?,?,?)",
            (value, 0.5, "context_observation_seed", 0.5, "pending", now),
        )
    connection.commit()
    return {"seeded": len(rows), "pending_before": pending}


GATING_TABLE = "sleep_input_gating_state"
# Default since 14 November 2026: full gating (no reading in sleep), chosen
# after a three-arm comparison and an advisory council, and confirmed on
# 15 November 2026 by the pre-registered runs in
# Audits/Sleep_Input_Gating_Preregistration_2026-11-14.md (all criteria met in
# both pairs). The graded variant (gain_immature 0.3, gain_mature 0.05) and no
# gating (enabled false) stay available.
GATING_DEFAULTS = {"enabled": "true", "gain_immature": "0.0", "gain_mature": "0.0", "base_chunks": "32"}


def _sleep_input_gain(connection):
    """Graded sensory gating during sleep (decision F2, advisory council of
    14 November 2026). In sleep the thalamus attenuates sensory input but does
    not switch it off; the sleeper stays a "vigilant sleeper" (McCormick & Bal
    1994; Andrillon & Kouider 2020). Infants still learn during sleep, adults
    only narrowly (Fifer et al. 2010; Tarullo et al. 2016; Arzi et al. 2012;
    Zust et al. 2019), and input close to a reactivation can cancel its benefit
    (Schreiner, Lehmann & Rasch 2015). Gain in sleep: from gain_immature to
    gain_mature with maturity, times (1 - depth); depth is the position of sleep
    pressure between the switch thresholds, so deep early sleep reads least.
    Returns (gain, sleeping, details); gain 1.0 in wake or when disabled."""
    connection.execute("CREATE TABLE IF NOT EXISTS " + GATING_TABLE + " (key TEXT PRIMARY KEY, value TEXT)")
    for k, v in GATING_DEFAULTS.items():
        connection.execute("INSERT OR IGNORE INTO " + GATING_TABLE + "(key,value) VALUES(?,?)", (k, v))
    st = dict(connection.execute("SELECT key,value FROM " + GATING_TABLE).fetchall())
    sw = {}
    if _table_exists(connection, "cooperative_sleep_wake_state"):
        sw = dict(connection.execute("SELECT key,value FROM cooperative_sleep_wake_state").fetchall())
    sleeping = str(sw.get("state", "wake")).lower() == "sleep"
    if not sleeping or str(st.get("enabled", "false")).lower() != "true":
        return 1.0, sleeping, {"gated": False}

    def _f(v, d):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d
    maturity = 0.0
    if _table_exists(connection, "phase7a_adenosine_state"):
        row = connection.execute("SELECT value FROM phase7a_adenosine_state WHERE key='developmental_maturity'").fetchone()
        maturity = min(1.0, max(0.0, _f(row[0] if row else 0.0, 0.0)))
    depth = min(1.0, max(0.0, _f(sw.get("pressure_position"), 1.0)))
    g_imm, g_mat = _f(st.get("gain_immature"), 0.3), _f(st.get("gain_mature"), 0.05)
    gain = max(0.0, min(1.0, (g_mat + (g_imm - g_mat) * (1.0 - maturity)) * (1.0 - depth)))
    return gain, sleeping, {"gated": True, "maturity": round(maturity, 4), "depth": round(depth, 4), "gain": round(gain, 4)}


def _sentences(text):
    return [part.strip() for part in _SENT_RE.split(_norm(text, 3000)) if part.strip()]


def _raw_hypothesis(sentence):
    observed = _norm(sentence)
    return {
        "role": "uncertain_hypothesis",
        "subject": observed[:180],
        "relation_hint": "",
        "object": "",
        "text_excerpt": observed,
        "confidence": 0.0,
        "uncertainty": 1.0,
    }


def _signature(hypothesis):
    material = "|".join([
        hypothesis["role"],
        hypothesis["subject"].lower()[:80],
        hypothesis["relation_hint"],
        hypothesis["object"].lower()[:120],
        hypothesis["text_excerpt"].lower()[:160],
    ])
    return hashlib.sha1(material.encode("utf-8", "ignore")).hexdigest()


def insert_observation(connection, chunk_id, sentence, title, neuromodulators, sleep_encoded=False):
    ensure_schema(connection)
    hypothesis = _raw_hypothesis(sentence)
    signature = _signature(hypothesis)
    now = _now()
    existing = connection.execute(
        "SELECT id,evidence_count FROM context_hypotheses WHERE signature=? LIMIT 1",
        (signature,),
    ).fetchone()
    if existing:
        hypothesis_id = existing[0]
        evidence_count = int(existing[1] or 1) + 1
        new_confidence = 1.0 - (1.0 / (1.0 + evidence_count))
        new_uncertainty = 1.0 / (1.0 + evidence_count)
        if sleep_encoded:
            # Input during sleep sets no recency tag: the replay window of 7d
            # orders by updated_at and must reflect wake experience (Wilson &
            # McNaughton 1994; tags from wake: Frey & Morris 1997). Before, sleep
            # re-observations filled the window with frequent template sentences.
            connection.execute(
                "UPDATE context_hypotheses SET evidence_count=?, confidence=?, uncertainty=? WHERE id=?",
                (evidence_count, new_confidence, new_uncertainty, hypothesis_id),
            )
        else:
            connection.execute(
                "UPDATE context_hypotheses SET evidence_count=?, confidence=?, uncertainty=?, updated_at=? WHERE id=?",
                (evidence_count, new_confidence, new_uncertainty, now, hypothesis_id),
            )
        if not sleep_encoded:
            # A trace first encoded in sleep becomes eligible for replay and
            # capture once it is confirmed in wake.
            connection.execute("UPDATE context_hypotheses SET origin=NULL WHERE id=? AND origin='sleep_encoded'",
                               (hypothesis_id,))
        event_type = "raw_observation_reobserved"
    else:
        cursor = connection.execute(
            "INSERT INTO context_hypotheses(chunk_id,role,subject,relation_hint,object,text_excerpt,source_title,confidence,uncertainty,status,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,signature,evidence_count,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                chunk_id, hypothesis["role"], hypothesis["subject"], hypothesis["relation_hint"],
                hypothesis["object"], hypothesis["text_excerpt"], title, hypothesis["confidence"],
                hypothesis["uncertainty"], "active", neuromodulators["dopamine"],
                neuromodulators["serotonin"], neuromodulators["glutamate"], neuromodulators["gaba"],
                neuromodulators["noradrenaline"], neuromodulators["acetylcholine"], signature, 1, now, now,
            ),
        )
        hypothesis_id = cursor.lastrowid
        if sleep_encoded:
            # Sleep-encoded traces are weak and implicit: flagged, not replayed
            # or captured until confirmed in wake (Ruch, Zust & Henke 2020).
            connection.execute("UPDATE context_hypotheses SET origin='sleep_encoded' WHERE id=?", (hypothesis_id,))
        event_type = "raw_observation_created"
    connection.execute(
        "INSERT INTO context_learning_events(hypothesis_id,event_type,role,details,dopamine,serotonin,glutamate,gaba,noradrenaline,acetylcholine,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            hypothesis_id, event_type, hypothesis["role"],
            _json({"chunk_id": chunk_id, "signature": signature, "input_mode": "raw_observation"}),
            neuromodulators["dopamine"], neuromodulators["serotonin"], neuromodulators["glutamate"],
            neuromodulators["gaba"], neuromodulators["noradrenaline"], neuromodulators["acetylcholine"], now,
        ),
    )
    return hypothesis_id, hypothesis


def _chunks(connection, limit=32):
    if not _table_exists(connection, "chunks"):
        return []
    chunk_id, text, title = _chunk_columns(connection)
    ids = [row[0] for row in connection.execute(
        "SELECT chunk_id FROM reading_queue WHERE status='pending' ORDER BY attention_score DESC, priority DESC, chunk_id ASC LIMIT ?",
        (limit,),
    ).fetchall()]
    if not ids or not chunk_id or not text:
        return []
    placeholders = ",".join("?" for _ in ids)
    title_expr = title if title else "''"
    query = "SELECT " + chunk_id + "," + title_expr + "," + text + " FROM chunks WHERE " + chunk_id + " IN (" + placeholders + ")"
    return [{"id": row[0], "title": row[1] or "", "text": row[2] or ""} for row in connection.execute(query, ids).fetchall()]


def _stop(loop):
    return any(bool(getattr(loop, name, False)) for name in ("stop_requested", "cancel", "auto_stop"))


def observation_cycle(loop, progress=None):
    connection = _db(loop)
    ensure_schema(connection)
    if _deprivation_active(connection):
        return [{
            "status": "context_observation_deprivation_no_input",
            "message": "Sensorischer Entzug aktiv: kein Queue-Seeding, kein Chunk-Lesen, keine neuen Input-Hypothesen.",
            "deprivation_active": True,
            "direct_fact_writes": "disabled",
            "direct_relation_writes": "disabled",
            "fact_promotion": "disabled",
            "no_word_blacklists": True,
            "learning_mode": LEARNING_MODE,
            "reading_queue_seed": {"seeded": 0, "reason": "sensory_deprivation"},
            "totals": {"chunks_read": 0, "hypotheses_created_or_updated": 0},
        }]
    gain, sleeping, gating = _sleep_input_gain(connection)
    limit = int(round(32 * gain))
    seed = seed_queue(connection, 2000) if limit > 0 else {"seeded": 0, "reason": "sleep_input_gated"}
    neuromodulators = _neuromodulators(connection)
    chunks = _chunks(connection, limit) if limit > 0 else []
    sleep_encoded = bool(sleeping and gating.get("gated"))
    hypotheses = 0
    now = _now()
    total = max(1, len(chunks))
    for index, chunk in enumerate(chunks, 1):
        if _stop(loop):
            break
        chunk_hypotheses = 0
        for sentence in _sentences(chunk["text"]):
            insert_observation(connection, chunk["id"], sentence, chunk["title"], neuromodulators, sleep_encoded)
            hypotheses += 1
            chunk_hypotheses += 1
        connection.execute(
            "UPDATE reading_queue SET status=?, read_count=COALESCE(read_count,0)+1, last_read=?, updated_at=? WHERE chunk_id=?",
            ("read_candidate" if chunk_hypotheses else "read_no_candidate", now, now, chunk["id"]),
        )
        if progress:
            try:
                progress(index, total, "context observation learning")
            except Exception:
                pass
    connection.commit()
    return [{
        "status": "context_observation_learning_cycle",
        "message": "Raw observations and exact re-observations recorded; semantic learning remains downstream.",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "fact_promotion": "disabled",
        "no_word_blacklists": True,
        "learning_mode": LEARNING_MODE,
        "reading_queue_seed": seed,
        "sleep_input_gating": gating,
        "totals": {"chunks_read": len(chunks), "hypotheses_created_or_updated": hypotheses},
    }]


def observation_run(loop, cycles=5, progress=None):
    for attr in ("stop_requested", "cancel", "auto_stop"):
        if hasattr(loop, attr) and isinstance(getattr(loop, attr), bool):
            setattr(loop, attr, False)
    output = []
    for _index in range(max(1, int(cycles or 1))):
        if _stop(loop):
            output.append([{"status": "stopped", "message": "Stop-Anforderung erkannt."}])
            break
        output.append(observation_cycle(loop, progress))
    return output


def patch_autonomous_loop(AutonomousLoop=None):
    if AutonomousLoop is None:
        from ki_system.autonomous import AutonomousLoop
    AutonomousLoop.cycle = observation_cycle
    AutonomousLoop.run = observation_run
    AutonomousLoop.context_observation_learning_release = True
    AutonomousLoop.no_word_blacklists = True
    AutonomousLoop.fact_promotion = "disabled"
    AutonomousLoop.direct_fact_writes = "disabled"
    AutonomousLoop.direct_relation_writes = "disabled"
    return True
