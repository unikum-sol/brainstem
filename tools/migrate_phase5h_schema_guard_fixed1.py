
import sys, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from ki_system.v8_phase5h_schema_guard_fixed1 import ensure_phase5h_schema, evaluate_strategy_experiment_outcomes
print('schema:', ensure_phase5h_schema('ki_memory.sqlite3'))
print('outcome_learning:', evaluate_strategy_experiment_outcomes('ki_memory.sqlite3'))
