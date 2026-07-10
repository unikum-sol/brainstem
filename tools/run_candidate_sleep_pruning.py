from ki_system.memory import Memory
from ki_system.candidate_sleep_pruning import CandidateSleepPruner
import json
m = Memory('ki_memory.sqlite3')
p = CandidateSleepPruner(m)
print(json.dumps(p.prune_once(batch_size=500, include_old_candidates=True), ensure_ascii=False, indent=2))
try:
    m.close()
except Exception:
    pass
