from ki_system.memory import Memory
from ki_system.candidate_type_refinement import CandidateTypeRefiner
import json
m = Memory('ki_memory.sqlite3')
r = CandidateTypeRefiner(m)
print(json.dumps(r.refine_once(batch_size=800), ensure_ascii=False, indent=2))
try:
    m.close()
except Exception:
    pass
