from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system.v8_phase4def_schema_status_fix import ensure_phase4def_schema
ensure_phase4def_schema(ROOT/'ki_memory.sqlite3')
print('OK: phase4def schema migration completed')
