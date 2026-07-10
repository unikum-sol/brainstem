import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import sqlite3
from ki_system.db_bootstrap import ensure_database_exists
from ki_system.v8_phase7a_adenosine_homeostat_release import (
    ensure_schema, initialize_adenosine_parameters, run_phase7a_cycle,
)

db_path = _ROOT / "ki_memory.sqlite3"
print("db bootstrap:", ensure_database_exists(str(db_path)))
con = sqlite3.connect(str(db_path))
print("db:", db_path)
print("schema:", ensure_schema(con))
print("init_params:", initialize_adenosine_parameters(con))
print("cycle:", run_phase7a_cycle(con))
con.close()
