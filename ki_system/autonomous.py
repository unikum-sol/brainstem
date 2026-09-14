# -*- coding: utf-8 -*-
"""Minimaler BrainStem-Loop-Kern.

Die konkrete Lernkette wird ausschliesslich durch phase_registry.py installiert.
Dieses Modul enthaelt keine Wortfilter, Extraktionsregeln oder direkten Writes.
"""

class AutonomousLoop:
    learning_mode = "context_hypotheses_with_neuromodulators"
    fact_promotion = "disabled"
    direct_fact_writes = "disabled"
    direct_relation_writes = "disabled"
    no_word_blacklists = True

    def __init__(self, memory):
        self.memory = memory
        self.cancel = False

    def stop(self):
        self.cancel = True

try:
    from ki_system.phase_registry import load_all as _load_all_phases
    _BRAINSTEM_LOAD_REPORT = _load_all_phases(globals(), AutonomousLoop)
except Exception as _phase_registry_exc:
    import traceback as _tb
    print("[PHASE_REGISTRY_LOAD_ERROR]", _phase_registry_exc)
    _tb.print_exc()
    # BRAINSTEM_FATAL_LOAD_REPORT_ALWAYS_SET_FIX_V1: previously,
    # _BRAINSTEM_LOAD_REPORT was only ever assigned inside the try block.
    # If phase_registry.load_all() itself raised (rather than one of its
    # individually-caught per-module entries), this module-level name was
    # never defined at all. Any caller checking it via getattr(..., None)
    # (as systemtest.py already does) would then treat a TOTAL phase-chain
    # load failure as "no report available" -- silently equivalent to
    # "not fatal" -- which is the opposite of correct. This is now always a
    # dict with an explicit fatal=True in this total-crash case, so callers
    # (see main.py's admin-GUI startup check, and get_load_report() below)
    # can reliably distinguish "never even attempted to report" from
    # "attempted and failed".
    _BRAINSTEM_LOAD_REPORT = {
        "loaded": [], "dead_code": [],
        "errors": [("PHASE_REGISTRY_LOAD_CRASH", repr(_phase_registry_exc))],
        "self_check": {"ok": False}, "fatal": True,
    }


def get_load_report():
    """Stable, explicit accessor for the phase-registry load report
    computed once at import time of this module. Always returns a dict
    containing at least a "fatal" boolean key, regardless of whether
    phase_registry.load_all() succeeded, partially failed, or crashed
    entirely. Intended for callers (e.g. main.py) that need to decide
    whether it is safe to start autonomous learning."""
    return _BRAINSTEM_LOAD_REPORT
