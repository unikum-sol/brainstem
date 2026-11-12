# -*- coding: utf-8 -*-
"""Current learning controls, read from the live neuromodulator state.

The reading-strategy phases (5b, 5f, 5g, 5h, 5i) steer and record their
decisions with six learning controls plus the six core neuromodulators. They
are taken from the state that Phase 6a (sleep replay and meta-plasticity) and
Phase 7c (E/I balance) maintain every cycle:

- learning_rate        <- plasticity level (meta-plasticity)
- exploration_pressure <- exploration bias
- consolidation_gain   <- consolidation bias
- inhibition_level     <- inhibition bias
- revision_pressure    <- revision bias
- error_weight         <- noradrenaline: arousal from unexpected outcomes
                          scales how strongly new evidence and errors are
                          weighted (Yu & Dayan 2005; Nassar et al. 2012)
- dopamine, serotonin, glutamate, gaba, noradrenaline, acetylcholine
                       <- the shared six-core snapshot

The calibrated base values are used only for a key that has not been written
yet (fresh database before the first sleep cycle).

Literatur: Yu & Dayan 2005; Nassar et al. 2012
"""
from __future__ import annotations

from typing import Dict

BASE = {
    "learning_rate": 0.234, "error_weight": 0.407, "revision_pressure": 0.312,
    "exploration_pressure": 0.31, "inhibition_level": 0.349, "consolidation_gain": 0.297,
    "dopamine": 0.5, "serotonin": 0.4, "glutamate": 0.31, "gaba": 0.349,
    "noradrenaline": 0.407, "acetylcholine": 0.312,
}
META_KEYS = {
    "learning_rate": "last_plasticity_level",
    "exploration_pressure": "last_exploration_bias",
    "consolidation_gain": "last_consolidation_bias",
    "inhibition_level": "last_inhibition_bias",
    "revision_pressure": "last_revision_bias",
}
NEUROMODULATORS = ("dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine")


def _kv(con, table) -> Dict[str, str]:
    try:
        return dict(con.execute("SELECT key,value FROM " + table).fetchall())
    except Exception:
        return {}


def _num(value, default):
    try:
        v = float(str(value).strip("'\""))
    except (TypeError, ValueError):
        return default
    return min(1.0, max(0.0, v))


def current_controls(con) -> Dict[str, float]:
    meta = _kv(con, "phase6a_meta_plasticity_state")
    sleep = _kv(con, "phase6a_neuromodulated_sleep_state")
    out = dict(BASE)
    for name, key in META_KEYS.items():
        out[name] = _num(meta.get(key, sleep.get(key)), BASE[name])
    for name in NEUROMODULATORS:
        out[name] = _num(sleep.get(name), BASE[name])
    out["error_weight"] = _num(sleep.get("noradrenaline"), BASE["error_weight"])
    return out
