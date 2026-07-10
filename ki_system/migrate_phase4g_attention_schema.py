
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sqlite3
from ki_system.v8_phase4g_neuromodulated_attention_queue_activation import ensure_phase4g_schema
con = sqlite3.connect(str(ROOT / 'ki_memory.sqlite3'))
changes = ensure_phase4g_schema(con)
con.close()
print('OK: phase4g neuromodulated learning schema migration completed')
print('changes:', changes)
