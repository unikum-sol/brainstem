
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from ki_system.v8_phase4m_active_learning_loop_controller import ensure_phase4m_schema, active_learning_controller
try:
    from ki_system.memory import Memory
    m = Memory('ki_memory.sqlite3')
except Exception:
    import sqlite3
    m = sqlite3.connect('ki_memory.sqlite3')
print('schema:', ensure_phase4m_schema(m))
print('controller:', active_learning_controller(m))
close = getattr(m, 'close', None)
if callable(close): close()
