
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sqlite3
from ki_system.v8_phase4def_schema_canonicalizer_fixed8 import ensure_phase4def_schema
con = sqlite3.connect(str(ROOT / 'ki_memory.sqlite3'))
changes = ensure_phase4def_schema(con)
print('OK: phase4def schema canonicalizer FIXED8 migration completed')
print('changed:', changes)
