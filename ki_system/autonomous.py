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
