from ki_system.memory import Memory
from ki_system.autonomous_corpus_reader import CorpusReader
import json, time
m = Memory('ki_memory.sqlite3')
r = CorpusReader(m)
for i in range(4):
    print('=== Corpus Reader Zyklus', i+1, '===')
    print(json.dumps(r.read_once(batch_size=50), ensure_ascii=False, indent=2))
    time.sleep(0.2)
m.close()
