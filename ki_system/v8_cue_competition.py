# -*- coding: utf-8 -*-
"""Cue competition: learned partial cues and their competing completions.

NO LINGUISTIC PRIOR. The cue ends at a boundary the system LEARNED itself:
a position whose preceding character context has high branching entropy in
the Phase-0 transition statistics (lexical_context_transitions). Early on
these boundaries are noisy, so early cues and competitions are noisy too --
by design: the decisive-evidence requirement keeps that noise from
reverting anything, and both the boundaries and the competitions sharpen as
the lexical layer learns.

Mechanism:
- A stored pattern is retrieved from a partial cue (pattern completion in
  the CA3 auto-associative network).
- Memories bound to the same cue compete for retrieval; the stronger,
  repeatedly retrieved one suppresses its competitors (retrieval-induced
  forgetting).
- A consolidated memory is only destabilized when its reactivation meets
  a prediction error, i.e. decisively stronger contrary evidence.
- Acetylcholine sets the balance between pattern separation and pattern
  completion: high ACh requires a longer cue (fewer competitions), low ACh
  lets a shorter cue suffice (more competition).
- Noradrenaline (unexpected uncertainty) scales the decisive evidence
  ratio in the contradiction detector.

Literatur: Rolls 2016; Yassa & Stark 2011; Anderson, Bjork & Bjork 1994;
Sevenster, Beckers & Kindt 2013; Hasselmo 2006; Hasselmo & McGaughy 2004;
Yu & Dayan 2005
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

TRANSITIONS_TABLE = "lexical_context_transitions"
LEXICAL_STATE = "phase0_lexical_state"
SENTENCE_ROLES = ("uncertain_hypothesis", "stable_hypothesis")
SUBJECT_SPAN = 180  # length of context_hypotheses.subject for sentence hypotheses

DEFAULTS = {
    # Minimal fraction of the stored pattern the cue must cover (partial-cue
    # completion), at neutral acetylcholine.
    "cue_fraction_base": 0.5,
    "cue_fraction_ach_gain": 0.6,
    "cue_fraction_min": 0.25,
    "cue_fraction_max": 0.9,
    # Candidate competitors fetched per cue (bounded cost).
    "competitor_fetch_limit": 2000,
}


def _table_exists(con, table) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _kv(con, table) -> Dict[str, str]:
    if not _table_exists(con, table):
        return {}
    try:
        return dict(con.execute("SELECT key,value FROM " + table).fetchall())
    except Exception:
        return {}


def _f(v, d):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _i(v, d):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def neuromodulators(con) -> Dict[str, float]:
    """Shared six-core snapshot, same access pattern as the Stage-B modules."""
    values = {"dopamine": 0.5, "serotonin": 0.5, "glutamate": 0.5,
              "gaba": 0.5, "noradrenaline": 0.5, "acetylcholine": 0.5}
    st = _kv(con, "phase6a_neuromodulated_sleep_state")
    for key in values:
        values[key] = _f(st.get(key), values[key])
    return values


def cue_fraction(acetylcholine: float, params: Optional[Dict[str, float]] = None) -> float:
    p = dict(DEFAULTS)
    p.update(params or {})
    frac = p["cue_fraction_base"] * (1.0 + p["cue_fraction_ach_gain"] * (acetylcholine - 0.5))
    return max(p["cue_fraction_min"], min(p["cue_fraction_max"], frac))


def _entropy_bits(counts) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


def learned_boundaries(con, text: str) -> List[int]:
    """Positions i (cut between text[i-1] and text[i]) the lexical layer
    currently treats as boundaries -- exactly its own criterion: the
    preceding k-character context has been seen >= min_observations times
    and its next-character branching entropy is >= the threshold."""
    if not text or not _table_exists(con, TRANSITIONS_TABLE):
        return []
    st = _kv(con, LEXICAL_STATE)
    k = max(1, _i(st.get("context_length"), 3))
    min_obs = max(1, _i(st.get("min_observations"), 8))
    threshold = _f(st.get("entropy_threshold_bits"), 1.0)
    if len(text) <= k:
        return []
    contexts = sorted({text[i - k:i] for i in range(k, len(text))})
    dist: Dict[str, Dict[str, int]] = {}
    for start in range(0, len(contexts), 400):
        part = contexts[start:start + 400]
        for ctx, nxt, cnt in con.execute(
                "SELECT context, next_char, count FROM " + TRANSITIONS_TABLE +
                " WHERE context IN (" + ",".join("?" for _ in part) + ")", part).fetchall():
            dist.setdefault(ctx, {})[nxt] = int(cnt or 0)
    out = []
    for i in range(k, len(text)):
        d = dist.get(text[i - k:i])
        if not d:
            continue
        if sum(d.values()) < min_obs:
            continue
        if _entropy_bits(d.values()) >= threshold:
            out.append(i)
    return out


def learned_cue(con, text: str, acetylcholine: float) -> Optional[str]:
    """Shortest prefix of `text` that ends at a learned boundary and covers
    at least cue_fraction(acetylcholine) of the pattern. Must be a proper
    prefix (a partial cue). None if the lexical layer has not learned a
    usable boundary there yet."""
    text = (text or "").strip()
    if len(text) < 4:
        return None
    min_len = int(math.ceil(len(text) * cue_fraction(acetylcholine)))
    for pos in learned_boundaries(con, text):
        if pos >= min_len and pos < len(text):
            cue = text[:pos]
            if cue.strip():
                return cue
    return None


def competitors(con, cue: str, own_id: int, own_excerpt: str, limit: int = 5,
                fetch_limit: int = DEFAULTS["competitor_fetch_limit"]) -> List[Tuple[int, str, int, str]]:
    """Other sentence hypotheses that are completions of the same cue but
    differ from the stored pattern. Returns (id, excerpt, evidence, role),
    strongest first. Uses the index on context_hypotheses(subject) through a
    prefix range."""
    if not cue:
        return []
    probe = cue[:SUBJECT_SPAN]
    rows = con.execute(
        "SELECT id, text_excerpt, COALESCE(evidence_count,0), role FROM context_hypotheses "
        "WHERE subject >= ? AND subject < ? AND +role IN (?,?) AND COALESCE(status,'active')='active' "
        "LIMIT ?",
        (probe, probe + "\U0010ffff", SENTENCE_ROLES[0], SENTENCE_ROLES[1], int(fetch_limit)),
    ).fetchall()
    own = (own_excerpt or "").strip()
    out = []
    for hid, excerpt, ev, role in rows:
        if int(hid) == int(own_id):
            continue
        ex = (excerpt or "").strip()
        if not ex or ex == own or not ex.startswith(cue):
            continue
        out.append((int(hid), ex, int(ev or 0), role))
    out.sort(key=lambda r: (-r[2], r[0]))
    return out[:limit]
