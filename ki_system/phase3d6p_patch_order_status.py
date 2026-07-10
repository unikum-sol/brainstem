from __future__ import annotations
import time

PATCH_ORDER = [
    'candidate_acceptance_tightening_phase3d6m',
    'predicate_quality_and_adjective_gate_phase3d6n',
    'heading_artifact_and_clause_gate_phase3d6o',
    'candidate_sleep_pruning_phase3d6k',
    'relation_repair_safety_phase3d6l1',
    'definition_candidate_guard_phase3d6l2',
    'status_label_and_patch_order_phase3d6p',
]


def _safe_apply_quality_gates():
    """Apply quality gates in deterministic order when modules are available.

    Existing modules are idempotent: each module sets a class flag and therefore does not
    double-wrap AdaptiveQuality. This function is intentionally conservative and does not
    create facts/relations or alter database contents.
    """
    applied = []
    errors = []
    try:
        from ki_system.adaptive_quality import AdaptiveQuality
    except Exception as exc:
        return {'applied': applied, 'errors': [{'module': 'adaptive_quality', 'error': str(exc)}]}

    for module_name, label in [
        ('ki_system.candidate_acceptance_tightening', 'phase3d6m_candidate_acceptance_tightening'),
        ('ki_system.predicate_quality_gate', 'phase3d6n_predicate_quality_and_adjective_gate'),
        ('ki_system.heading_artifact_clause_gate', 'phase3d6o_heading_artifact_and_clause_gate'),
    ]:
        try:
            mod = __import__(module_name, fromlist=['apply_patch'])
            mod.apply_patch(AdaptiveQuality)
            applied.append(label)
        except Exception as exc:
            errors.append({'module': module_name, 'error': str(exc)})
    return {'applied': applied, 'errors': errors}


def _flag(obj, name):
    try:
        return bool(getattr(obj, name, False))
    except Exception:
        return False


def _quality_gate_flags():
    try:
        from ki_system.adaptive_quality import AdaptiveQuality
        return {
            'phase3d6m_candidate_acceptance_tightening': _flag(AdaptiveQuality, '_phase3d6m_acceptance_tightening_patched'),
            'phase3d6n_predicate_quality_and_adjective_gate': _flag(AdaptiveQuality, '_phase3d6n_predicate_quality_patched'),
            'phase3d6o_heading_artifact_and_clause_gate': _flag(AdaptiveQuality, '_phase3d6o_heading_clause_patched'),
        }
    except Exception as exc:
        return {'error': str(exc)}


def _reader_flags(CorpusReader):
    return {
        'phase3d6k_candidate_sleep_pruning': _flag(CorpusReader, '_phase3d6k_sleep_pruning_patched'),
        'phase3d6l1_relation_repair_safety': _flag(CorpusReader, '_phase3d6l1_relation_repair_patched'),
        'phase3d6l2_definition_candidate_guard': _flag(CorpusReader, '_phase3d6l2_definition_guard_patched'),
        'phase3d6p_status_label_and_patch_order': _flag(CorpusReader, '_phase3d6p_status_label_patched'),
    }


def install(CorpusReader):
    """Install final status-label wrapper for CorpusReader.

    This patch intentionally only changes observability:
    - it applies available quality gates in deterministic order;
    - it annotates output with a patch order block;
    - it sets the corpus_reader status label to phase3d6p.

    It does not write facts, write relations, promote candidates, delete rows, or change
    any existing memory safety gates.
    """
    quality_setup = _safe_apply_quality_gates()
    if getattr(CorpusReader, '_phase3d6p_status_label_patched', False):
        return {'status': 'already_installed_phase3d6p', 'quality_setup': quality_setup}

    original = CorpusReader.read_once

    def read_once_with_phase3d6p_status(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if isinstance(result, dict):
            result['status'] = 'adaptive_alignment_corpus_reader_phase3d6p'
            result['patch_order_status'] = {
                'status': 'patch_order_status_phase3d6p',
                'message': 'Patch order verified/annotated. No facts/relations promotion.',
                'patch_order': list(PATCH_ORDER),
                'quality_gate_flags': _quality_gate_flags(),
                'reader_patch_flags': _reader_flags(CorpusReader),
                'quality_setup': quality_setup,
                'fact_promotion': 'disabled',
                'direct_fact_writes': 'disabled',
                'direct_relation_writes': 'disabled',
                'created_at': int(time.time()),
            }
        return result

    CorpusReader.read_once = read_once_with_phase3d6p_status
    CorpusReader._phase3d6p_status_label_patched = True
    return {'status': 'installed_phase3d6p', 'quality_setup': quality_setup}
