
# -*- coding: utf-8 -*-
"""
Phase6a GUI Dashboard Helper

Reads the current neuromodulated sleep replay / meta-plasticity state and updates
existing GUI labels/bars without changing learning logic.

Project compass:
- no word blacklists
- no facts/relations/questions writes
- no fact promotion
- display-only helper
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ORDER = ["dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine"]
LABELS = {
    "dopamine": "DA",
    "serotonin": "5-HT",
    "glutamate": "GLU",
    "gaba": "GABA",
    "noradrenaline": "NA",
    "acetylcholine": "ACh",
}
DEFAULTS = {
    "dopamine": 0.50,
    "serotonin": 0.60,
    "glutamate": 0.40,
    "gaba": 0.40,
    "noradrenaline": 0.30,
    "acetylcholine": 0.50,
}


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        value = float(str(value).strip().strip('"').strip("'"))
    except Exception:
        value = float(default)
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _memory_connection(mem: Any) -> Tuple[sqlite3.Connection, bool]:
    """Return a sqlite connection and whether the caller must close it."""
    if isinstance(mem, sqlite3.Connection):
        return mem, False
    for attr in ("db", "conn", "con", "connection", "sqlite"):
        con = getattr(mem, attr, None)
        if isinstance(con, sqlite3.Connection):
            return con, False
    for attr in ("db_path", "path", "filename", "file"):
        p = getattr(mem, attr, None)
        if p:
            return sqlite3.connect(str(p)), True
    # GUI is normally started from project root. This fallback keeps diagnostics usable.
    return sqlite3.connect("ki_memory.sqlite3"), True


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _kv_table(cur: sqlite3.Cursor, table: str) -> Dict[str, str]:
    if not _table_exists(cur, table):
        return {}
    try:
        return {str(k): str(v) for k, v in cur.execute(f"SELECT key,value FROM {table}").fetchall()}
    except Exception:
        return {}


def _latest_phase6a_values(mem: Any) -> Optional[Dict[str, Any]]:
    con, close = _memory_connection(mem)
    try:
        cur = con.cursor()
        sleep = _kv_table(cur, "phase6a_neuromodulated_sleep_state")
        meta = _kv_table(cur, "phase6a_meta_plasticity_state")
        if not sleep and not meta:
            return None

        nm = {}
        for key in ORDER:
            if key in sleep:
                nm[key] = _clamp(sleep.get(key), DEFAULTS[key])
            elif key in meta:
                nm[key] = _clamp(meta.get(key), DEFAULTS[key])
            else:
                nm[key] = DEFAULTS[key]

        def read_float(name: str, default: float = 0.0) -> float:
            if name in meta:
                return _clamp(meta.get(name), default)
            if name in sleep:
                return _clamp(sleep.get(name), default)
            alt = "last_" + name
            if alt in meta:
                return _clamp(meta.get(alt), default)
            if alt in sleep:
                return _clamp(sleep.get(alt), default)
            return default

        data = dict(nm)
        data.update({
            "plasticity_level": read_float("plasticity_level", read_float("last_plasticity_level", 0.0)),
            "exploration_bias": read_float("exploration_bias", read_float("last_exploration_bias", 0.0)),
            "revision_bias": read_float("revision_bias", read_float("last_revision_bias", 0.0)),
            "consolidation_bias": read_float("consolidation_bias", read_float("last_consolidation_bias", 0.0)),
            "inhibition_bias": read_float("inhibition_bias", read_float("last_inhibition_bias", 0.0)),
            "persistent_gap_pressure": read_float("persistent_gap_pressure", read_float("last_persistent_gap_pressure", 0.0)),
            "avg_outcome_score": read_float("avg_outcome_score", read_float("last_avg_outcome_score", 0.0)),
            "avg_closure_delta": read_float("avg_closure_delta", read_float("last_avg_closure_delta", 0.0)),
            "avg_overlap_score": read_float("avg_overlap_score", read_float("last_avg_overlap_score", 0.0)),
            "avg_no_candidate_rate": read_float("avg_no_candidate_rate", read_float("last_avg_no_candidate_rate", 0.0)),
            "candidate_count": int(float(meta.get("last_candidate_count", sleep.get("last_candidate_count", 0)) or 0)),
            "replay_events": int(float(meta.get("last_replay_events", sleep.get("last_replay_events", 0)) or 0)),
            "phase": sleep.get("phase", meta.get("phase", "phase6a_neuromodulated_sleep_replay")),
        })
        return data
    finally:
        if close:
            con.close()


def _fallback_old_dashboard(app: Any) -> bool:
    """Use the original NeuromodulatorManager if Phase6a state is not available."""
    try:
        from ki_system.neuromodulators import NeuromodulatorManager
        mgr = NeuromodulatorManager(app.mem)
        st = mgr.get_state().as_dict()
        beh = mgr.behavior_modifiers()
        mood = mgr.mood_state()
        app.neuro_text.configure(text="Neuromodulatoren: " + mgr.short_status())
        app.behavior_text.configure(
            text=(
                f"Verhalten: {beh.get('mode')} | Exploration {beh.get('exploration'):.2f} | "
                f"Präzision {beh.get('precision'):.2f} | Filter {beh.get('filter_strictness'):.2f}"
            )
        )
        if hasattr(mgr, "trend_status_line"):
            app.trend_text.configure(text=mgr.trend_status_line())
        app.neuro_bars.draw(st)
        app.mood_emoji.configure(text=mood.get("emoji", "(^_^)"))
        app.mood_name.configure(text=mood.get("name", "Ausgewogen"))
        return True
    except Exception as exc:
        try:
            app.neuro_text.configure(text="Neuromodulatoren: nicht verfügbar: " + str(exc))
        except Exception:
            pass
        return False


def _mode_from_phase6a(data: Dict[str, Any]) -> Tuple[str, str]:
    plasticity = data.get("plasticity_level", 0.0)
    exploration = data.get("exploration_bias", 0.0)
    revision = data.get("revision_bias", 0.0)
    consolidation = data.get("consolidation_bias", 0.0)
    persistent = data.get("persistent_gap_pressure", 0.0)
    if persistent >= 0.80 and plasticity >= 0.70:
        return "↯", "Reorganisation"
    if consolidation >= 0.60 and data.get("serotonin", 0.0) >= 0.55:
        return "(^_^)", "Konsolidierend"
    if exploration >= 0.65:
        return "(^_^)↗", "Explorativ"
    if revision >= 0.65:
        return "(!)", "Revision"
    return "(^_^)", "Ausgewogen"


def update_phase6a_neuromodulator_dashboard(app: Any) -> bool:
    """Update current GUI neuromodulator/dashboard widgets from Phase6a if possible.

    Returns True if an update was made. Falls back to the legacy manager when Phase6a
    state tables are not available yet.
    """
    data = _latest_phase6a_values(getattr(app, "mem", None))
    if not data:
        return _fallback_old_dashboard(app)

    state = {k: data.get(k, DEFAULTS[k]) for k in ORDER}
    short = " | ".join(f"{LABELS[k]} {state[k]:.2f}" for k in ORDER)
    app.neuro_text.configure(text="Neuromodulatoren: " + short + " | Quelle: Phase6a Sleep Replay")

    app.behavior_text.configure(
        text=(
            "Verhalten: Schlaf-Replay/Reorganisation | "
            f"Plastizität {data.get('plasticity_level', 0.0):.2f} | "
            f"Exploration {data.get('exploration_bias', 0.0):.2f} | "
            f"Revision {data.get('revision_bias', 0.0):.2f} | "
            f"Konsolidierung {data.get('consolidation_bias', 0.0):.2f} | "
            f"Hemmung {data.get('inhibition_bias', 0.0):.2f}"
        )
    )
    app.trend_text.configure(
        text=(
            f"Sleep Replay: Kandidaten {data.get('candidate_count', 0)} | Events {data.get('replay_events', 0)} | "
            f"Outcome {data.get('avg_outcome_score', 0.0):.3f} | "
            f"Closure {data.get('avg_closure_delta', 0.0):.3f} | "
            f"Overlap {data.get('avg_overlap_score', 0.0):.3f} | "
            f"Persistent {data.get('persistent_gap_pressure', 0.0):.2f}"
        )
    )
    try:
        app.neuro_bars.draw(state)
    except Exception:
        pass
    emoji, name = _mode_from_phase6a(data)
    try:
        app.mood_emoji.configure(text=emoji)
        app.mood_name.configure(text=name)
    except Exception:
        pass
    return True
