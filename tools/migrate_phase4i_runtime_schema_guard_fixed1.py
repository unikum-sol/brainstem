import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase4i_runtime_schema_guard_fixed1 import ensure_phase4i_runtime_schema

m = Memory('ki_memory.sqlite3')
try:
    print('OK: phase4i runtime schema guard FIXED1 migration completed')
    print('changes:', ensure_phase4i_runtime_schema(m))
finally:
    # Some project Memory versions do not expose close(). Do not fail after a successful migration.
    close = getattr(m, 'close', None)
    if callable(close):
        close()
