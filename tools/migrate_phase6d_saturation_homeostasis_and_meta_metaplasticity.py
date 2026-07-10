import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import sqlite3
from ki_system.v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release import (
    ensure_schema, initialize_meta_metaplasticity_parameters, run_phase6d_cycle,
)

db_path = _ROOT / "ki_memory.sqlite3"
con = sqlite3.connect(str(db_path))
print("db:", db_path)
print("schema:", ensure_schema(con))
print("init_params:", initialize_meta_metaplasticity_parameters(con))
print("cycle:", run_phase6d_cycle(con))
con.close()
