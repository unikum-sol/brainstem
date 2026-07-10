
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase4j_internal_learning_questions_and_gap_detection import ensure_phase4j_schema, detect_internal_learning_gaps
m = Memory()
print("schema:", ensure_phase4j_schema(m))
print("gaps:", detect_internal_learning_gaps(m))
close = getattr(m, "close", None)
if callable(close):
    close()
