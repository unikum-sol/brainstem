import sys,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase4l_gap_cluster_planning_and_strategy_balance import ensure_schema,apply_strategy_balance
m=Memory(); db=getattr(m,'conn',None)
if db is None:
 import sqlite3; db=sqlite3.connect('ki_memory.sqlite3'); db.row_factory=sqlite3.Row
print('schema:', {'status':'ok','phase':'phase4l_gap_cluster_planning_and_strategy_balance','changes':ensure_schema(db)})
print('strategy:', apply_strategy_balance(db))
db.commit()
close=getattr(m,'close',None)
if callable(close): close()
