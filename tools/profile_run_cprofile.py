import sys, cProfile, pstats, io, time
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ki_system.memory import Memory
from ki_system.autonomous import AutonomousLoop

mem = Memory(str(_ROOT / "ki_memory.sqlite3"))
loop = AutonomousLoop(mem)

print("Profiling loop.run(1) with cProfile ... (one real cycle)")
pr = cProfile.Profile()
t0 = time.perf_counter()
pr.enable()
try:
    loop.run(1)
except Exception as exc:
    print("run raised:", exc)
pr.disable()
wall = time.perf_counter() - t0

s = io.StringIO()
ps = pstats.Stats(pr, stream=s)
print("=" * 72)
print("TOP 30 by CUMULATIVE time:")
print("=" * 72)
ps.sort_stats("cumulative").print_stats(30)
print(s.getvalue())

s2 = io.StringIO()
ps2 = pstats.Stats(pr, stream=s2)
print("=" * 72)
print("TOP 30 by TOTAL (self) time:")
print("=" * 72)
ps2.sort_stats("tottime").print_stats(30)
print(s2.getvalue())

print("WALL CLOCK run(1): %.3f s" % wall)
try:
    mem.db.close()
except Exception:
    pass