from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.v8_phase4p_gap_resolution_and_learning_outcome_tracking import ensure_phase4p_schema, evaluate_gap_resolutions
print('schema:', ensure_phase4p_schema())
print('resolution:', evaluate_gap_resolutions())
