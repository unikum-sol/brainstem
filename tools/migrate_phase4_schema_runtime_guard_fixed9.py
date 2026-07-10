
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase4_schema_runtime_guard_fixed9 import ensure_phase4_schema
m = Memory('ki_memory.sqlite3')
changes = ensure_phase4_schema(m)
print('OK: phase4 schema runtime guard FIXED9 migration completed')
print('changes:', changes)
