
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sqlite3
from ki_system.v8_phase4i_long_term_memory_and_pattern_stability import ensure_phase4i_schema, consolidate_long_term_patterns

con = sqlite3.connect(str(ROOT / "ki_memory.sqlite3"))
changes = ensure_phase4i_schema(con)
summary = consolidate_long_term_patterns(con)
print("OK: phase4i long-term memory schema migration completed")
print("changes:", changes)
print("summary:", summary)
