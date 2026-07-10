import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from ki_system.v8_phase5d_integrated_observation_and_strategy_memory_release import ensure_phase5d_schema, apply_integrated_observation_and_strategy_memory
print('schema:', ensure_phase5d_schema())
print('observation:', apply_integrated_observation_and_strategy_memory())
