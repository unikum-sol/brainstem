from __future__ import annotations

def apply_patch(AutonomousLearner):
    if getattr(AutonomousLearner, '_phase3d6b_safe_brain_cycle_patched', False): return
    from ki_system.autonomous_corpus_reader import CorpusReader
    def safe_brain_cycle(self, *args, **kwargs):
        try:
            if not hasattr(self, 'corpus_reader'):
                self.corpus_reader = CorpusReader(self.memory)
            attempts = kwargs.get('attempts', None)
            if attempts is None and args:
                try: attempts = int(args[0])
                except Exception: attempts = 24
            if attempts is None: attempts = 24
            corpus_result = self.corpus_reader.read_once(batch_size=max(20, int(attempts) * 2))
        except Exception as exc:
            corpus_result = {'status': 'safe_autonomous_corpus_reader_error', 'error': str(exc)}
        return [{'status':'safe_autonomous_brain_cycle_phase3d6b','message':'Autonomes Lernen SAFE: Corpus Reading + Kandidatenbildung + Musterlernen. Direkter alter Faktenzyklus ist deaktiviert.','direct_fact_writes':'disabled','corpus_reader':corpus_result}]
    AutonomousLearner.cycle = safe_brain_cycle
    AutonomousLearner._phase3d6b_safe_brain_cycle_patched = True
