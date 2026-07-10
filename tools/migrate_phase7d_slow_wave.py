import sys
from pathlib import Path
_R=Path(__file__).resolve().parent.parent
if str(_R) not in sys.path: sys.path.insert(0,str(_R))
import sqlite3
from ki_system.v8_phase7d_slow_wave_sleep_substructure_release import ensure_schema, initialize_slow_wave_parameters, run_phase7d_cycle
con=sqlite3.connect(str(_R/"ki_memory.sqlite3"))
print("schema:",ensure_schema(con))
print("init:",initialize_slow_wave_parameters(con))
print("cycle:",run_phase7d_cycle(con))
con.close()
