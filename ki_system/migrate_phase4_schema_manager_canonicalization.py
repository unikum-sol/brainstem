
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system.v8_phase4_schema_manager_canonicalization import ensure_phase4_schema
from ki_system.memory import Memory
m = Memory('ki_memory.sqlite3')
try:
    res = ensure_phase4_schema(m)
    print('OK: phase4 canonical schema migration completed')
    print('changes:', res.get('changes'))
finally:
    try: m.close()
    except Exception: pass
