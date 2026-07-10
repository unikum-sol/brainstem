import sys, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system import v8_phase5c_learning_outcome_closure_and_question_cluster_resolution as p
print('schema:', p.ensure_schema())
print('closure:', p.apply_learning_outcome_closure())
