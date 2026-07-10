from pathlib import Path
import sys, sqlite3
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ki_system import v8_phase4g_neuromodulated_learning_control as lc
p = ROOT / "ki_memory.sqlite3"
con = sqlite3.connect(str(p))
lc.ensure_phase4_schema(con)
con.commit(); con.close()
print("OK: phase4g neuromodulated learning control migration completed")
