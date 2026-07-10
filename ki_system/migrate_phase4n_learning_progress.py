
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system.v8_phase4n_learning_progress_evaluation_and_adaptive_strategy import ensure_phase4n_schema, evaluate_learning_progress
try:
    from ki_system.memory import Memory
    m=Memory()
except Exception:
    m=None
print('schema:', ensure_phase4n_schema(m))
print('controller:', evaluate_learning_progress(m))
close=getattr(m,'close',None)
if callable(close): close()
