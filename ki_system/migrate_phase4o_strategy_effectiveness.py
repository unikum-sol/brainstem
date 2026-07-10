
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.v8_phase4o_strategy_effectiveness_feedback_loop import ensure_phase4o_schema, evaluate_strategy_effectiveness
print('schema:', ensure_phase4o_schema())
print('feedback:', evaluate_strategy_effectiveness())
