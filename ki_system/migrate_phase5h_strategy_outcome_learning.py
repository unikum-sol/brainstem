
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.v8_phase5h_strategy_experiment_outcome_learning_release import ensure_schema, evaluate_strategy_experiment_outcomes
try:
    from ki_system.memory import Memory
    m = Memory()
except Exception:
    m = None
print('schema:', ensure_schema(m))
print('outcome_learning:', evaluate_strategy_experiment_outcomes(m))
