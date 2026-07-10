
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sqlite3
from ki_system.gui_phase6a_dashboard_helpers import _latest_phase6a_values

db_path = ROOT / "ki_memory.sqlite3"
print("db:", db_path)
con = sqlite3.connect(str(db_path))
cur = con.cursor()

def count(t):
    try:
        return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except Exception:
        return 0

print("facts", count("facts"))
print("relations", count("relations"))
print("questions", count("questions"))
print("phase6a_neuromodulated_sleep_state", count("phase6a_neuromodulated_sleep_state"))
print("phase6a_meta_plasticity_state", count("phase6a_meta_plasticity_state"))
vals = _latest_phase6a_values(con)
print("latest_phase6a_values:", vals)
con.close()
