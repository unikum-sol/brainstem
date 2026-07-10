from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.v8_phase5a_integrated_self_improving_learning_release import ensure_phase5a_schema, integrated_control_step
print('schema:', ensure_phase5a_schema())
print('integrated:', integrated_control_step())
