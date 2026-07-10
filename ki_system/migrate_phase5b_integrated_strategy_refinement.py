
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system import v8_phase5b_integrated_strategy_refinement_release as p
print('schema:', p.ensure_phase5b_schema())
print('strategy:', p.apply_strategy_refinement())
