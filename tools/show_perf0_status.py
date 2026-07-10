import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import sqlite3
con = sqlite3.connect(str(_ROOT / "ki_memory.sqlite3"))
cur = con.cursor()
def ex(t):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
print("db:", _ROOT / "ki_memory.sqlite3")
for p in ["journal_mode", "synchronous", "cache_size", "temp_store", "mmap_size", "page_size"]:
    print("PRAGMA", p, "=", cur.execute("PRAGMA " + p).fetchone()[0])
if ex("perf0_state"):
    print("perf0_state:")
    for row in cur.execute("SELECT key,value FROM perf0_state ORDER BY key").fetchall():
        print("  ", row[0], "=", row[1])
print("indexes on hot tables:")
for t in ["context_hypotheses", "phase5g_experiment_outcomes", "phase6b_anchor_pool", "questions", "reading_queue", "chunk_attention_scores"]:
    if ex(t):
        idxs = [r[1] for r in cur.execute("PRAGMA index_list(" + t + ")").fetchall()]
        print("  ", t, "->", idxs)
con.close()
