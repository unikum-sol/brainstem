from __future__ import annotations

def apply_patch(memory_module_globals):
    from ki_system.corpus_memory import ensure_corpus_schema, insert_candidate
    def make_guard(method_name):
        def guarded(self, subject=None, relation=None, obj=None, *args, **kwargs):
            try:
                # tolerate positional variants
                vals=[subject, relation, obj] + list(args)
                s=vals[0] if len(vals)>0 else kwargs.get('subject','')
                r=vals[1] if len(vals)>1 else kwargs.get('relation','')
                o=vals[2] if len(vals)>2 else kwargs.get('object', kwargs.get('obj',''))
                confidence=kwargs.get('confidence', 0.0)
                source=kwargs.get('source','')
                ensure_corpus_schema(self)
                insert_candidate(self, s, r, o, confidence or 0.0, None, str(source or method_name), str(source or method_name), {'novelty_score':0.5}, 'candidate', None)
            except Exception:
                pass
            return False
        guarded._phase3d6d_guarded=True
        return guarded
    for _name,_obj in list(memory_module_globals.items()):
        if isinstance(_obj,type):
            for meth in ['add_fact','add_relation','add_relations','store_relation','insert_relation','add_ontology']:
                if hasattr(_obj,meth):
                    current=getattr(_obj,meth)
                    if not getattr(current,'_phase3d6d_guarded',False):
                        setattr(_obj,meth,make_guard(meth))
