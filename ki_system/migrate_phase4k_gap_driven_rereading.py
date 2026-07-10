import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase4k_gap_driven_rereading_and_learning_strategy import ensure_phase4k_schema, activate_gap_driven_rereading

m = Memory()
print('schema:', ensure_phase4k_schema(m))
print('strategy:', activate_gap_driven_rereading(m, max_gaps=25, chunks_per_gap=4))
close = getattr(m, 'close', None)
if callable(close):
    close()
