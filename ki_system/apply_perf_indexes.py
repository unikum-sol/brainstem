import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import sqlite3
from ki_system.v8_perf0_runtime_acceleration_release import apply_all
db_path = _ROOT / "ki_memory.sqlite3"
con = sqlite3.connect(str(db_path))
report = apply_all(con)
print("=== PERF0 apply_all report ===")
print("PRAGMAs:")
for k, v in report["pragmas"].items():
    print("  ", k, "=", v)
print("Indexes created:", report["indexes"]["created"])
print("Indexes skipped:")
for s in report["indexes"]["skipped"]:
    print("  ", s)
con.close()
