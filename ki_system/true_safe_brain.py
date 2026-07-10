from __future__ import annotations

def apply_patch(AutonomousLearner):
    from ki_system.autonomous_corpus_reader import CorpusReader
    def safe_cycle(self,*args,**kwargs):
        try:
            attempts=kwargs.get('attempts', None)
            if attempts is None and args:
                try: attempts=int(args[0])
                except Exception: attempts=24
            if attempts is None: attempts=24
            if not hasattr(self,'corpus_reader'):
                self.corpus_reader=CorpusReader(self.memory)
            result=self.corpus_reader.read_once(batch_size=max(20,int(attempts)*2))
        except Exception as exc:
            result={'status':'true_safe_corpus_reader_error','error':str(exc)}
        return [{'status':'true_safe_brain_cycle_phase3d6d','message':'TRUE SAFE: Nur Corpus Reader/Kandidaten/Musterlernen. Alter Fragen-/Diagnosezyklus deaktiviert.','direct_fact_writes':'disabled','direct_relation_writes':'disabled','question_generation':'disabled','diagnostic_reseed':'disabled','corpus_reader':result}]
    def safe_run(self, cycles=1, attempts=24, callback=None, *args, **kwargs):
        for i in range(int(cycles or 1)):
            if getattr(self,'stop_requested',False): break
            res=safe_cycle(self, attempts=attempts)
            if callback: callback(i+1,res)
        return None
    AutonomousLearner.cycle=safe_cycle
    AutonomousLearner.run=safe_run
    for name in ['run_continuous','run_forever','continuous_learning','autonomous_loop','loop']:
        if hasattr(AutonomousLearner,name):
            setattr(AutonomousLearner,name,safe_run)
    AutonomousLearner._phase3d6d_true_safe_patched=True
