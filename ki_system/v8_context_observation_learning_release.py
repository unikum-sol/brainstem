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


def _now():
    return int(time.time())


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


def ensure_schema(connection):
    ensure_schema_for(connection)
    _self_check_schema(connection)
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
    rows = connection.execute(
        "SELECT c." + chunk_id + " FROM chunks c LEFT JOIN reading_queue rq ON rq.chunk_id=c." + chunk_id +
        " WHERE rq.chunk_id IS NULL ORDER BY c." + chunk_id + " ASC LIMIT ?",
        (target - pending,),
    ).fetchall()
    now = _now()
    for (value,) in rows:
        connection.execute(
            "INSERT OR IGNORE INTO reading_queue(chunk_id,priority,reason,attention_score,status,updated_at) VALUES(?,?,?,?,?,?)",
            (value, 0.5, "context_observation_seed", 0.5, "pending", now),
        )
    connection.commit()
    return {"seeded": len(rows), "pending_before": pending}


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


def insert_observation(connection, chunk_id, sentence, title, neuromodulators):
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
        connection.execute(
            "UPDATE context_hypotheses SET evidence_count=?, updated_at=? WHERE id=?",
            (evidence_count, now, hypothesis_id),
        )
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
    seed = seed_queue(connection, 2000)
    neuromodulators = _neuromodulators(connection)
    chunks = _chunks(connection, 32)
    hypotheses = 0
    now = _now()
    total = max(1, len(chunks))
    for index, chunk in enumerate(chunks, 1):
        if _stop(loop):
            break
        chunk_hypotheses = 0
        for sentence in _sentences(chunk["text"]):
            insert_observation(connection, chunk["id"], sentence, chunk["title"], neuromodulators)
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
