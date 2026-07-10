from ki_system.memory import Memory
from ki_system.autonomous_corpus_reader import CorpusReader
import json
m=Memory('ki_memory.sqlite3')
r=CorpusReader(m)
print(json.dumps(r.read_once(batch_size=50), ensure_ascii=False, indent=2))
try: m.close()
except Exception: pass
