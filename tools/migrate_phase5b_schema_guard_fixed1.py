from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.v8_phase5b_schema_guard_fixed1 import ensure_phase5b_schema, apply_strategy_refinement_safe
print('schema:', ensure_phase5b_schema())
print('strategy:', apply_strategy_refinement_safe())
