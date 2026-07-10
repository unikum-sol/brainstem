
import sqlite3
from ki_system.v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release import ensure_phase6a_schema, sleep_replay_and_meta_plasticity

con = sqlite3.connect('ki_memory.sqlite3')
print('schema:', ensure_phase6a_schema(con))
print('sleep_replay:', sleep_replay_and_meta_plasticity(con))
con.close()
