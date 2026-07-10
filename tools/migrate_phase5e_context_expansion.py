import sys, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system.v8_phase5e_context_expansion_and_gap_closure_release import ensure_phase5e_schema, apply_context_expansion_and_gap_closure
print('schema:', ensure_phase5e_schema())
print('context_expansion:', apply_context_expansion_and_gap_closure())
