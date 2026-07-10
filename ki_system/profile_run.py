import sys, time
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ki_system.memory import Memory
from ki_system.autonomous import AutonomousLoop
from ki_system import search as search_mod
from ki_system import nlp as nlp_mod

timings = {}
counts = {}

def make_timer(name, orig):
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return orig(*args, **kwargs)
        finally:
            dt = time.perf_counter() - t0
            timings[name] = timings.get(name, 0.0) + dt
            counts[name] = counts.get(name, 0) + 1
    return wrapper

# Patch module-level functions
if hasattr(search_mod, "semantic_search"):
    search_mod.semantic_search = make_timer("search.semantic_search", search_mod.semantic_search)
if hasattr(nlp_mod, "extract_relations"):
    nlp_mod.extract_relations = make_timer("nlp.extract_relations", nlp_mod.extract_relations)

# Patch AutonomousLoop methods (class level, before instancing)
methods_to_time = [
    "_cleanup", "_existing", "generate_quality_questions",
    "_reseed_questions_from_chunks", "_question_learning_pass",
    "_consolidation_pass", "_pick_open_question", "_extractable", "_learn",
]
for m in methods_to_time:
    if hasattr(AutonomousLoop, m):
        orig = getattr(AutonomousLoop, m)
        setattr(AutonomousLoop, m, make_timer("loop." + m, orig))

# Patch Memory heavy methods
if hasattr(Memory, "iter_chunks"):
    Memory.iter_chunks = make_timer("memory.iter_chunks", Memory.iter_chunks)
if hasattr(Memory, "fts_search"):
    Memory.fts_search = make_timer("memory.fts_search", Memory.fts_search)

# Run ONE run(1) and measure
mem = Memory(str(_ROOT / "ki_memory.sqlite3"))
loop = AutonomousLoop(mem)
t_total0 = time.perf_counter()
try:
    res = loop.run(1)
except Exception as exc:
    print("run(1) raised:", exc)
t_total = time.perf_counter() - t_total0

print("=" * 72)
print("RUN(1) PROFILE - sorted by total time")
print("=" * 72)
rows = sorted(timings.items(), key=lambda x: x[1], reverse=True)
for name, dt in rows:
    c = counts.get(name, 0)
    per = (dt / c) if c else 0.0
    print("  %8.3fs total | %6d calls | %9.4fs/call | %s" % (dt, c, per, name))
print("  " + "-" * 64)
print("  %8.3fs TOTAL run(1) wall-clock" % t_total)
print("  %8.3fs sum of measured (nested/overlap possible)" % sum(timings.values()))
print()
print("HINWEIS: Dominiert 'search.semantic_search' oder 'memory.iter_chunks',")
print("ist der Full-Table-Scan ueber alle Chunks der Flaschenhals.")
try:
    mem.db.close()
except Exception:
    pass
