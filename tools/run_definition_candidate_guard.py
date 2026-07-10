from ki_system.memory import Memory
from ki_system.definition_candidate_guard import DefinitionCandidateGuard
import json
m = Memory('ki_memory.sqlite3')
g = DefinitionCandidateGuard(m)
print(json.dumps(g.guard_once(batch_size=500), ensure_ascii=False, indent=2))
try:
    m.close()
except Exception:
    pass
