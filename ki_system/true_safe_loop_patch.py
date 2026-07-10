from __future__ import annotations


def _flag_is_true(obj, name):
    if not hasattr(obj, name):
        return False
    value = getattr(obj, name)
    if callable(value):
        return False
    return bool(value)


def _safe_progress(progress, current, total, message, result):
    """Call GUI progress with the legacy-safe signature.

    The GUI App.progress signature is progress(c, t, msg='').
    Previous safe_run versions accidentally called progress(i, result), so t became a list
    and Tkinter crashed in max(1, t). This wrapper always passes a numeric total.
    """
    if not progress:
        return
    try:
        progress(int(current), int(max(1, total)), str(message or ''))
        return
    except TypeError:
        pass
    except Exception:
        return
    # Fallback for potential one-argument progress callbacks.
    try:
        progress(result)
    except Exception:
        pass


def apply_patch(autonomous_globals):
    from ki_system.autonomous_corpus_reader import CorpusReader
    cls = autonomous_globals.get('AutonomousLoop')
    if cls is None:
        return False

    def _get_memory(self):
        for attr in ('memory', 'mem', 'db', 'm'):
            if hasattr(self, attr):
                candidate = getattr(self, attr)
                if hasattr(candidate, 'db') and hasattr(candidate, 'lock'):
                    return candidate
        raise AttributeError('No Memory-like attribute found on AutonomousLoop instance')

    def safe_cycle(self, attempts=24, *args, **kwargs):
        try:
            memory = _get_memory(self)
            if not hasattr(self, '_phase3d6k1_corpus_reader'):
                self._phase3d6k1_corpus_reader = CorpusReader(memory)
            try:
                attempts_i = int(attempts or 24)
            except Exception:
                attempts_i = 24
            result = self._phase3d6k1_corpus_reader.read_once(batch_size=max(20, attempts_i * 2))
        except Exception as exc:
            result = {'status': 'adaptive_alignment_corpus_reader_error_phase3d6k1', 'error': str(exc)}
        return [{
            'status': 'adaptive_alignment_true_safe_brain_cycle_phase3d6k1',
            'message': 'ADAPTIVE ALIGNMENT SAFE: GUI progress callback fixed. Corpus Reader + adaptive semantic gate + alignment/role learning + candidate sleep pruning. Keine direkten Fakten/Relationen.',
            'direct_fact_writes': 'disabled',
            'direct_relation_writes': 'disabled',
            'question_generation': 'disabled',
            'diagnostic_reseed': 'disabled',
            'legacy_question_cycle': 'disabled',
            'fact_promotion': 'disabled',
            'corpus_reader': result,
        }]

    def safe_run(self, cycles=1, progress=None, *args, **kwargs):
        for attr in ('stop_requested', 'cancel', 'auto_stop', '_stop_requested'):
            if hasattr(self, attr) and not callable(getattr(self, attr)):
                try:
                    setattr(self, attr, False)
                except Exception:
                    pass
        try:
            cycles_i = int(cycles or 1)
        except Exception:
            cycles_i = 1
        try:
            attempts = int(kwargs.get('attempts', 24) or 24)
        except Exception:
            attempts = 24
        collected = []
        for i in range(cycles_i):
            current = i + 1
            if _flag_is_true(self, 'stop_requested') or _flag_is_true(self, 'cancel') or _flag_is_true(self, 'auto_stop') or _flag_is_true(self, '_stop_requested'):
                result = [{'status': 'stopped', 'message': 'Stop-Anforderung erkannt.'}]
                collected.append(result)
                _safe_progress(progress, current, cycles_i, 'gestoppt', result)
                break
            result = safe_cycle(self, attempts=attempts)
            collected.append(result)
            # IMPORTANT: second argument must be numeric total, never the result list.
            _safe_progress(progress, current, cycles_i, 'adaptive safe', result)
        return collected

    def safe_generate_quality_questions(self, *args, **kwargs):
        return {'created': 0, 'selected': [], 'status': 'disabled_phase3d6k1'}

    cls.cycle = safe_cycle
    cls.run = safe_run
    cls.generate_quality_questions = safe_generate_quality_questions
    for name in ('run_continuous', 'run_forever', 'continuous_learning', 'autonomous_loop', 'loop'):
        if hasattr(cls, name):
            setattr(cls, name, safe_run)
    cls._phase3d6k1_gui_progress_fixed = True
    return True
