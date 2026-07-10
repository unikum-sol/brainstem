from ki_system.memory import Memory
from ki_system.relation_repair import RelationRepairer
import json
m = Memory('ki_memory.sqlite3')
r = RelationRepairer(m)
print(json.dumps(r.repair_once(batch_size=500, include_rejected=True), ensure_ascii=False, indent=2))
try:
    m.close()
except Exception:
    pass
