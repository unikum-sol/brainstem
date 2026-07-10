
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase4i_runtime_schema_guard_fixed3 import ensure_phase4i_schema, consolidate_long_term_memory
m = Memory('ki_memory.sqlite3')
changes = ensure_phase4i_schema(m)
print('migration:', {'status':'ok','phase':'phase4i_runtime_schema_guard_fixed3','changes':changes})
print('summary:', consolidate_long_term_memory(m))
close = getattr(m, 'close', None)
if callable(close): close()
