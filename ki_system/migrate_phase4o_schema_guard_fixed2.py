import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ki_system.v8_phase4o_schema_guard_fixed2 import ensure_phase4o_schema
print('schema:', ensure_phase4o_schema())
try:
    from ki_system.v8_phase4o_strategy_effectiveness_feedback_loop import evaluate_strategy_effectiveness
    print('feedback:', evaluate_strategy_effectiveness())
except Exception as exc:
    print('feedback_skip_or_error:', repr(exc))
