import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase4i_runtime_autoload_and_periodic_consolidation_fix import ensure_phase4i_runtime_schema, consolidate_long_term_memory
m=Memory('ki_memory.sqlite3'); db=m.db if hasattr(m,'db') else m
print('OK: phase4i runtime schema changes:', ensure_phase4i_runtime_schema(db))
print('summary:', consolidate_long_term_memory(db))
try: m.close()
except Exception: pass
