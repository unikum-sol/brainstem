import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ki_system.db_bootstrap import ensure_database_exists, print_bootstrap_report

db_path = _ROOT / "ki_memory.sqlite3"
if len(sys.argv) >= 2:
    db_path = Path(sys.argv[1])

report = ensure_database_exists(str(db_path))
print_bootstrap_report(report)
