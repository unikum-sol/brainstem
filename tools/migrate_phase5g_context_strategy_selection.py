import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system import v8_phase5g_context_strategy_selection_and_experiment_memory_release as p
print('schema:', p.ensure_schema())
print('strategy:', p.apply_context_strategy_selection())
