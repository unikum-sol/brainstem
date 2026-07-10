import sys, sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system.v8_phase4h_self_evaluation_and_revision_core import ensure_phase4h_schema
con=sqlite3.connect(str(ROOT/'ki_memory.sqlite3'))
changes=ensure_phase4h_schema(con); con.commit(); con.close()
print('OK: phase4h self evaluation schema migration completed')
print('changes:', changes)
