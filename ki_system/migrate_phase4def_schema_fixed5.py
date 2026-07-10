
from pathlib import Path
import sqlite3, time
DB_PATH = Path('ki_memory.sqlite3')

def _table_exists(cur, name):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

def _cols(cur, table):
    if not _table_exists(cur, table):
        return set()
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}

def _add(cur, table, name, typ):
    if name not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
        return True
    return False

def migrate_connection(con):
    cur = con.cursor(); changed=[]; now=int(time.time())
    cur.execute("CREATE TABLE IF NOT EXISTS context_learning_events(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    for name, typ in [
        ('hypothesis_id','INTEGER'),('event_type','TEXT'),('role','TEXT'),('details','TEXT'),
        ('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),
        ('gaba','REAL DEFAULT 0'),('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),
        ('created_at','INTEGER DEFAULT 0')]:
        if _add(cur,'context_learning_events',name,typ): changed.append(f'context_learning_events.{name}')
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, feedback_type TEXT, feedback_score REAL DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_revisions(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, old_role TEXT, new_role TEXT, reason TEXT, details TEXT, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_error_events(id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, error_type TEXT, role TEXT, severity REAL DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS chunk_attention_scores(chunk_id INTEGER PRIMARY KEY, attention_score REAL DEFAULT 0, novelty REAL DEFAULT 0, uncertainty REAL DEFAULT 0, reward REAL DEFAULT 0, fatigue REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS attention_queue_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS reading_strategy_state(key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_clusters(id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, signature TEXT, size INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(hypothesis_id INTEGER PRIMARY KEY, stability_score REAL DEFAULT 0, evidence_count INTEGER DEFAULT 0, contradiction_count INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events(id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, details TEXT, dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, created_at INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS rollback_safe_core_state(key TEXT PRIMARY KEY, value TEXT)")
    for k,v in {'phase':"'phase4def_schema_runtime_fixed5'", 'no_word_blacklists':"'true'", 'learning_mode':"'context_hypotheses_with_neuromodulators'", 'fact_promotion':"'disabled'", 'direct_fact_writes':"'disabled'", 'direct_relation_writes':"'disabled'", 'question_generation':"'disabled'"}.items():
        cur.execute("INSERT OR REPLACE INTO rollback_safe_core_state(key,value) VALUES(?,?)", (k,v))
    con.commit(); return changed

def main():
    if not DB_PATH.exists():
        print('WARNUNG: DB nicht gefunden:', DB_PATH.resolve()); return
    con=sqlite3.connect(DB_PATH); changed=migrate_connection(con); con.close()
    print('OK: phase4def schema runtime FIXED5 migration completed')
    print('changed:', changed)
if __name__ == '__main__': main()
