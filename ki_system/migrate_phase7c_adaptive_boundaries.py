import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import sqlite3
from ki_system.v8_phase7c_adaptive_boundaries_and_ei_balance_release import (
    ensure_schema, initialize_boundary_parameters, run_phase7c_cycle,
)
con = sqlite3.connect(str(_ROOT / "ki_memory.sqlite3"))
print("schema:", ensure_schema(con))
print("init:", initialize_boundary_parameters(con))
print("cycle:", run_phase7c_cycle(con))
con.close()
