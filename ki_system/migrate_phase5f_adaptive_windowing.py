import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ki_system.memory import Memory
from ki_system.v8_phase5f_context_expansion_effectiveness_and_adaptive_windowing_release import ensure_schema, apply_adaptive_windowing
m=Memory('ki_memory.sqlite3')
print('schema:', ensure_schema(m))
print('adaptive_windowing:', apply_adaptive_windowing(m))
