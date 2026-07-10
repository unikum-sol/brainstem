
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ki_system.v8_phase4_schema_runtime_guard_fixed11 import ensure_phase4_schema
res = ensure_phase4_schema('ki_memory.sqlite3')
print('OK: phase4 schema runtime guard FIXED11 migration completed')
print('changes:', res.get('changes'))
