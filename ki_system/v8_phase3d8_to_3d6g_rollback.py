
# V8_PHASE3D8_TO_3D6G_ROLLBACK_SAFE_CORE
# Purpose:
#   Restore the runtime behavior to a 3d6g-like safe core:
#   - no lexical blacklist quality gates
#   - no direct facts writes
#   - no direct relations writes
#   - no question generation
#   - no fact promotion
#   - safe autonomous corpus reading into hypotheses/candidates only
#
# This module intentionally does NOT delete old files. It supersedes the later
# 3d6h..3d8 runtime hooks by patching AutonomousLoop.run/cycle at import time.

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PATCH_ID = "V8_PHASE3D8_TO_3D6G_ROLLBACK_SAFE_CORE"
STATUS_LOOP = "true_safe_autonomous_loop_phase3d6g_rollback"
STATUS_READER = "true_safe_corpus_reader_phase3d6g_no_word_blacklists"


def _db_path_from_memory(memory: Any) -> Path:
    p = getattr(memory, "path", None)
    if p is not None:
        return Path(p)
    db = getattr(memory, "db", None)
    # sqlite3.Connection doesn't expose the path reliably; fall back to cwd DB.
    return Path("ki_memory.sqlite3")


def _connect(memory: Any) -> sqlite3.Connection:
    db = getattr(memory, "db", None)
    if isinstance(db, sqlite3.Connection):
        return db
    return sqlite3.connect(str(_db_path_from_memory(memory)), check_same_thread=False)


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _columns(cur: sqlite3.Cursor, table: str) -> List[str]:
    if not _table_exists(cur, table):
        return []
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _ensure_safe_schema(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reading_queue (
            chunk_id INTEGER PRIMARY KEY,
            priority REAL DEFAULT 0,
            reason TEXT,
            attention_score REAL DEFAULT 0,
            read_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            last_read INTEGER DEFAULT 0,
            updated_at INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidate_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            relation TEXT,
            object TEXT,
            status TEXT DEFAULT 'raw_hypothesis',
            confidence REAL DEFAULT 0.0,
            source_chunk_id INTEGER,
            context TEXT,
            created_at INTEGER DEFAULT 0,
            updated_at INTEGER DEFAULT 0,
            candidate_type TEXT,
            hypothesis_role TEXT,
            uncertainty REAL DEFAULT 1.0,
            evidence_count INTEGER DEFAULT 1,
            error_signal REAL DEFAULT 0.0,
            learning_notes TEXT
        )
    """)
    # Add missing columns if candidate_relations already existed.
    cols = set(_columns(cur, "candidate_relations"))
    additions = {
        "candidate_type": "TEXT",
        "hypothesis_role": "TEXT",
        "uncertainty": "REAL DEFAULT 1.0",
        "evidence_count": "INTEGER DEFAULT 1",
        "error_signal": "REAL DEFAULT 0.0",
        "learning_notes": "TEXT",
        "updated_at": "INTEGER DEFAULT 0",
        "created_at": "INTEGER DEFAULT 0",
        "context": "TEXT",
        "source_chunk_id": "INTEGER",
        "confidence": "REAL DEFAULT 0.0",
        "status": "TEXT DEFAULT 'raw_hypothesis'",
    }
    for name, typ in additions.items():
        if name not in cols:
            try:
                cur.execute(f"ALTER TABLE candidate_relations ADD COLUMN {name} {typ}")
            except Exception:
                pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS context_learning_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            chunk_id INTEGER,
            subject TEXT,
            relation TEXT,
            object TEXT,
            hypothesis_role TEXT,
            uncertainty REAL,
            neuromodulators_json TEXT,
            created_at INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS context_learning_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at INTEGER DEFAULT 0
        )
    """)
    con.commit()


def _get_chunk_columns(cur: sqlite3.Cursor) -> Tuple[str, Optional[str], Optional[str]]:
    cols = _columns(cur, "chunks")
    if not cols:
        raise RuntimeError("Tabelle 'chunks' fehlt. Bitte ZIM zuerst importieren.")
    id_col = "id" if "id" in cols else ("chunk_id" if "chunk_id" in cols else cols[0])
    text_col = None
    for c in ("text", "content", "chunk_text", "body"):
        if c in cols:
            text_col = c; break
    title_col = None
    for c in ("title", "article_title", "path"):
        if c in cols:
            title_col = c; break
    if text_col is None:
        # Pick first TEXT-ish column as last resort.
        info = cur.execute("PRAGMA table_info(chunks)").fetchall()
        for _, name, typ, *_ in info:
            if "TEXT" in (typ or "").upper():
                text_col = name; break
    if text_col is None:
        raise RuntimeError("Keine Textspalte in 'chunks' gefunden.")
    return id_col, text_col, title_col


def _seed_reading_queue(con: sqlite3.Connection, target_pending: int = 2000) -> int:
    cur = con.cursor()
    if not _table_exists(cur, "chunks"):
        return 0
    pending = cur.execute("SELECT COUNT(*) FROM reading_queue WHERE status='pending'").fetchone()[0]
    if pending >= target_pending:
        return 0
    id_col, _text_col, _title_col = _get_chunk_columns(cur)
    need = target_pending - pending
    now = int(time.time())
    rows = cur.execute(f"""
        SELECT c.{id_col}
        FROM chunks c
        LEFT JOIN reading_queue rq ON rq.chunk_id = c.{id_col}
        WHERE rq.chunk_id IS NULL
        ORDER BY c.{id_col}
        LIMIT ?
    """, (need,)).fetchall()
    for (cid,) in rows:
        cur.execute("""
            INSERT OR IGNORE INTO reading_queue
            (chunk_id, priority, reason, attention_score, read_count, status, last_read, updated_at)
            VALUES (?, 0.0, 'phase3d6g_safe_core_seed', 0.0, 0, 'pending', 0, ?)
        """, (cid, now))
    con.commit()
    return len(rows)


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
# We deliberately avoid word blacklist gates. These are structural relation cues,
# not blocklists. They are used to form hypotheses, not to ban words.
_REL_PATTERNS = [
    (re.compile(r"^(.{2,120}?)\s+(?:ist|sind|war|waren)\s+(?:ein|eine|einer|eines|der|die|das)?\s*(.{2,180})$", re.I), "is_a"),
    (re.compile(r"^(.{2,120}?)\s+(?:befindet sich|liegt|sitzt)\s+(?:in|bei|auf)\s+(.{2,120})$", re.I), "located_in"),
    (re.compile(r"^(.{2,120}?)\s+(?:besteht aus|umfasst|enthält)\s+(.{2,180})$", re.I), "has_part"),
    (re.compile(r"^(.{2,120}?)\s+(?:heißt|trägt den Namen|wird genannt)\s+(.{2,120})$", re.I), "has_name"),
]


def _role_from_hypothesis(subj: str, rel: str, obj: str) -> str:
    s = (subj or "").strip()
    o = (obj or "").strip()
    # Role classification, not hard rejection. The same word may be useful in
    # another role/context later.
    if rel == "located_in":
        return "relation_hypothesis"
    if rel in ("has_part", "has_name"):
        return "property_hypothesis"
    if re.search(r"\b\d{3,4}\b|seit|bis|am|im jahr", o, re.I):
        return "temporal_hypothesis"
    if re.search(r"\bbeispiel\b|zum beispiel|etwa", s + " " + o, re.I):
        return "example_hypothesis"
    if re.search(r"\b(erforderlich|notwendig|möglich|verfügbar|kompatibel|programmiert|programmierbar|kostenlos|fertig|aktiv|inaktiv)\b", o, re.I):
        return "property_hypothesis"
    if len(s.split()) > 10 or len(o.split()) > 18:
        return "context_fragment"
    if rel == "is_a":
        return "definition_hypothesis"
    return "raw_hypothesis"


def _confidence_and_uncertainty(role: str, subj: str, obj: str) -> Tuple[float, float]:
    # Conservative: hypotheses are uncertain by default. Repeated evidence in
    # future phases should adjust these values through learning, not blacklists.
    base = {
        "definition_hypothesis": 0.35,
        "property_hypothesis": 0.30,
        "relation_hypothesis": 0.35,
        "temporal_hypothesis": 0.28,
        "example_hypothesis": 0.25,
        "context_fragment": 0.15,
        "raw_hypothesis": 0.20,
    }.get(role, 0.20)
    if len(subj.strip()) >= 3 and len(obj.strip()) >= 3:
        base += 0.05
    return min(base, 0.45), max(0.55, 1.0 - base)


def _candidate_exists(cur: sqlite3.Cursor, subj: str, rel: str, obj: str, chunk_id: int) -> bool:
    cols = _columns(cur, "candidate_relations")
    source_col = "source_chunk_id" if "source_chunk_id" in cols else None
    if source_col:
        row = cur.execute("""
            SELECT id FROM candidate_relations
            WHERE subject=? AND relation=? AND object=? AND source_chunk_id=?
            LIMIT 1
        """, (subj, rel, obj, chunk_id)).fetchone()
    else:
        row = cur.execute("""
            SELECT id FROM candidate_relations
            WHERE subject=? AND relation=? AND object=?
            LIMIT 1
        """, (subj, rel, obj)).fetchone()
    return row is not None


def _insert_hypothesis(con: sqlite3.Connection, chunk_id: int, subj: str, rel: str, obj: str, context: str, role: str) -> bool:
    cur = con.cursor()
    if _candidate_exists(cur, subj, rel, obj, chunk_id):
        return False
    conf, uncertainty = _confidence_and_uncertainty(role, subj, obj)
    now = int(time.time())
    cols = _columns(cur, "candidate_relations")
    values = {
        "subject": subj,
        "relation": rel,
        "object": obj,
        "status": role,
        "confidence": conf,
        "source_chunk_id": chunk_id,
        "context": context,
        "created_at": now,
        "updated_at": now,
        "candidate_type": role,
        "hypothesis_role": role,
        "uncertainty": uncertainty,
        "evidence_count": 1,
        "error_signal": 0.0,
        "learning_notes": "phase3d6g_rollback_hypothesis_no_word_blacklist",
    }
    use_cols = [c for c in values if c in cols]
    if not use_cols:
        return False
    placeholders = ",".join(["?"] * len(use_cols))
    sql = f"INSERT INTO candidate_relations ({','.join(use_cols)}) VALUES ({placeholders})"
    cur.execute(sql, [values[c] for c in use_cols])
    # Learning event is optional but useful.
    cur.execute("""
        INSERT INTO context_learning_events
        (event_type, chunk_id, subject, relation, object, hypothesis_role, uncertainty, neuromodulators_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "hypothesis_created", chunk_id, subj, rel, obj, role, uncertainty,
        json.dumps(_neuromodulator_snapshot(role, uncertainty), ensure_ascii=False), now
    ))
    return True


def _neuromodulator_snapshot(role: str, uncertainty: float) -> Dict[str, float]:
    # Lightweight digital neurotransmitter signal for learning control.
    novelty = 0.55 if role in ("raw_hypothesis", "context_fragment") else 0.4
    conflict = min(0.8, uncertainty)
    return {
        "dopamine": round(0.25 + (0.25 if role == "definition_hypothesis" else 0.10), 3),
        "noradrenaline": round(0.25 + novelty, 3),
        "acetylcholine": round(0.45 + (0.20 if uncertainty > 0.65 else 0.05), 3),
        "serotonin": 0.60,
        "gaba": round(0.30 + conflict * 0.35, 3),
        "glutamate": round(0.45 + novelty * 0.20, 3),
    }


def _extract_hypotheses(text: str) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    if not text:
        return out
    # Limit work per chunk. This is a safe learner, not a high-throughput final extractor.
    for sent in _SENT_SPLIT.split(text):
        sent = " ".join(sent.strip().split())
        if len(sent) < 12 or len(sent) > 450:
            continue
        for pat, rel in _REL_PATTERNS:
            m = pat.match(sent)
            if m:
                subj = m.group(1).strip(" :;,-–—\t")
                obj = m.group(2).strip(" :;,-–—\t")
                if subj and obj:
                    out.append((subj[:160], rel, obj[:240]))
                break
        if len(out) >= 8:
            break
    return out


def run_safe_core_reader(memory: Any, batch_size: int = 48) -> Dict[str, Any]:
    con = _connect(memory)
    _ensure_safe_schema(con)
    cur = con.cursor()
    seeded = _seed_reading_queue(con, 2000)
    id_col, text_col, title_col = _get_chunk_columns(cur)
    title_expr = f"c.{title_col}" if title_col else "''"
    rows = cur.execute(f"""
        SELECT rq.chunk_id, c.{text_col}, {title_expr}
        FROM reading_queue rq
        JOIN chunks c ON c.{id_col}=rq.chunk_id
        WHERE rq.status='pending'
        ORDER BY rq.priority DESC, rq.chunk_id ASC
        LIMIT ?
    """, (batch_size,)).fetchall()
    now = int(time.time())
    totals = {
        "chunks_read": 0,
        "raw_hypotheses": 0,
        "stored_hypotheses": 0,
        "definition_hypothesis": 0,
        "property_hypothesis": 0,
        "relation_hypothesis": 0,
        "temporal_hypothesis": 0,
        "example_hypothesis": 0,
        "context_fragment": 0,
        "raw_hypothesis": 0,
    }
    samples = []
    for chunk_id, text, title in rows:
        totals["chunks_read"] += 1
        hyps = _extract_hypotheses(text or "")
        totals["raw_hypotheses"] += len(hyps)
        stored_for_chunk = 0
        for subj, rel, obj in hyps:
            role = _role_from_hypothesis(subj, rel, obj)
            if _insert_hypothesis(con, int(chunk_id), subj, rel, obj, str(title or ""), role):
                totals["stored_hypotheses"] += 1
                totals[role] = totals.get(role, 0) + 1
                stored_for_chunk += 1
                if len(samples) < 12:
                    samples.append({
                        "hypothesis": [subj, rel, obj],
                        "role": role,
                        "context": str(title or ""),
                    })
        new_status = "read_hypothesis" if stored_for_chunk else "read_no_hypothesis"
        cur.execute("""
            UPDATE reading_queue
            SET status=?, read_count=COALESCE(read_count,0)+1, last_read=?, updated_at=?
            WHERE chunk_id=?
        """, (new_status, now, now, int(chunk_id)))
    con.commit()
    return {
        "status": STATUS_READER,
        "message": "3d6g rollback safe core: no lexical word blacklists; hypotheses only; no facts/relations/questions.",
        "seeded_reading_queue": seeded,
        "totals": totals,
        "samples": samples,
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
        "diagnostic_reseed": "disabled",
        "legacy_question_cycle": "disabled",
        "fact_promotion": "disabled",
        "word_blacklists": "disabled/superseded",
        "learning_mode": "context_hypotheses_with_neuromodulators",
    }


def _stop_requested(obj: Any) -> bool:
    for name in ("auto_stop", "stop_requested", "cancel", "cancelled"):
        val = getattr(obj, name, False)
        if isinstance(val, bool) and val:
            return True
    return False


def safe_cycle(self: Any, progress=None) -> List[Dict[str, Any]]:
    if _stop_requested(self):
        return [{"status": "stopped", "message": "Stop-Anforderung erkannt."}]
    mem = getattr(self, "mem", None) or getattr(self, "memory", None)
    if mem is None:
        return [{"status": "error", "message": "Keine Memory-Instanz im AutonomousLoop gefunden."}]
    if progress:
        try:
            progress(0, 1, "3d6g rollback safe core")
        except Exception:
            pass
    reader_result = run_safe_core_reader(mem, batch_size=48)
    if progress:
        try:
            progress(1, 1, "3d6g rollback safe core")
        except Exception:
            pass
    return [{
        "status": STATUS_LOOP,
        "message": "ROLLBACK SAFE CORE: restored 3d6g-like no-write learning. Later lexical blacklist gates superseded. Hypotheses only.",
        "direct_fact_writes": "disabled",
        "direct_relation_writes": "disabled",
        "question_generation": "disabled",
        "diagnostic_reseed": "disabled",
        "legacy_question_cycle": "disabled",
        "fact_promotion": "disabled",
        "word_blacklists": "disabled/superseded",
        "corpus_reader": reader_result,
    }]


def safe_run(self: Any, cycles: int = 5, progress=None) -> List[List[Dict[str, Any]]]:
    # Keep GUI-compatible nested list format established in previous safe loops.
    results: List[List[Dict[str, Any]]] = []
    try:
        cycles_i = int(cycles or 1)
    except Exception:
        cycles_i = 1
    cycles_i = max(1, min(cycles_i, 5))
    for i in range(cycles_i):
        if _stop_requested(self):
            results.append([{"status": "stopped", "message": "Stop-Anforderung erkannt."}])
            break
        if progress:
            try:
                progress(i + 1, cycles_i, "3d6g rollback safe core")
            except Exception:
                pass
        results.append(safe_cycle(self, progress=None))
    return results


def apply_patch() -> bool:
    try:
        from ki_system import autonomous as auto
        cls = getattr(auto, "AutonomousLoop", None)
        if cls is None:
            return False
        cls.cycle = safe_cycle
        cls.run = safe_run
        setattr(cls, "_phase3d8_to_3d6g_rollback_patched", True)
        setattr(cls, "_phase3d8_to_3d6g_no_word_blacklists", True)
        return True
    except Exception:
        return False


APPLIED = apply_patch()
