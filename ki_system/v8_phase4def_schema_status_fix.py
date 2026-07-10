# V8-phase4def schema/status fix FIXED1
from __future__ import annotations
import sqlite3, time
DB_DEFAULT = 'ki_memory.sqlite3'

def _cols(cur, table):
    try:
        return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()

def _table_exists(cur, table):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _ensure_col(cur, table, col, decl):
    if col not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

def ensure_phase4def_schema(db_or_path=DB_DEFAULT):
    close=False
    if isinstance(db_or_path, sqlite3.Connection):
        con=db_or_path
    else:
        con=sqlite3.connect(str(db_or_path)); close=True
    cur=con.cursor(); now=int(time.time())
    cur.execute("""CREATE TABLE IF NOT EXISTS rollback_safe_core_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    for k,v in {
        'phase':'phase4def_schema_status_fix_fixed1',
        'no_word_blacklists':'true',
        'learning_mode':'context_hypotheses_with_neuromodulators',
        'fact_promotion':'disabled',
        'direct_fact_writes':'disabled',
        'direct_relation_writes':'disabled',
        'question_generation':'disabled',
    }.items():
        cur.execute("INSERT OR REPLACE INTO rollback_safe_core_state(key,value,updated_at) VALUES(?,?,?)", (k, repr(v), now))

    cur.execute("""CREATE TABLE IF NOT EXISTS reading_queue(
        chunk_id INTEGER PRIMARY KEY, priority REAL DEFAULT 0, reason TEXT,
        attention_score REAL DEFAULT 0, read_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending', last_read INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS context_hypotheses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, role TEXT, subject TEXT,
        relation_hint TEXT, object TEXT, text_excerpt TEXT, source_title TEXT,
        confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1, status TEXT DEFAULT 'hypothesis',
        dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0,
        gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    for col, decl in [
        ('role','TEXT'),('subject','TEXT'),('relation_hint','TEXT'),('object','TEXT'),('text_excerpt','TEXT'),('source_title','TEXT'),
        ('confidence','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 1'),('status',"TEXT DEFAULT 'hypothesis'"),
        ('dopamine','REAL DEFAULT 0'),('serotonin','REAL DEFAULT 0'),('glutamate','REAL DEFAULT 0'),('gaba','REAL DEFAULT 0'),
        ('noradrenaline','REAL DEFAULT 0'),('acetylcholine','REAL DEFAULT 0'),('created_at','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _ensure_col(cur,'context_hypotheses',col,decl)

    cur.execute("""CREATE TABLE IF NOT EXISTS context_learning_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, chunk_id INTEGER,
        event_type TEXT, role TEXT, confidence REAL DEFAULT 0, uncertainty REAL DEFAULT 1,
        details TEXT, created_at INTEGER DEFAULT 0)""")
    for col, decl in [('hypothesis_id','INTEGER'),('chunk_id','INTEGER'),('event_type','TEXT'),('role','TEXT'),('confidence','REAL DEFAULT 0'),('uncertainty','REAL DEFAULT 1'),('details','TEXT'),('created_at','INTEGER DEFAULT 0')]:
        _ensure_col(cur,'context_learning_events',col,decl)

    # 4d/4e/4f tables
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, feedback_type TEXT,
        signal_strength REAL DEFAULT 0, source TEXT, details TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_revisions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, old_role TEXT, new_role TEXT,
        old_confidence REAL DEFAULT 0, new_confidence REAL DEFAULT 0, reason TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_error_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id INTEGER, error_type TEXT, error_signal REAL DEFAULT 0,
        role TEXT, details TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulated_attention_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, hypothesis_id INTEGER,
        attention_reason TEXT, novelty REAL DEFAULT 0, uncertainty REAL DEFAULT 0,
        reward REAL DEFAULT 0, fatigue REAL DEFAULT 0, dopamine REAL DEFAULT 0,
        serotonin REAL DEFAULT 0, glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0,
        noradrenaline REAL DEFAULT 0, acetylcholine REAL DEFAULT 0, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS context_role_stats(
        role TEXT, seen_count INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0,
        avg_uncertainty REAL DEFAULT 0, feedback_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    for col, decl in [('role','TEXT'),('seen_count','INTEGER DEFAULT 0'),('avg_confidence','REAL DEFAULT 0'),('avg_uncertainty','REAL DEFAULT 0'),('feedback_count','INTEGER DEFAULT 0'),('error_count','INTEGER DEFAULT 0'),('updated_at','INTEGER DEFAULT 0')]:
        _ensure_col(cur,'context_role_stats',col,decl)

    cur.execute("""CREATE TABLE IF NOT EXISTS chunk_attention_scores(
        chunk_id INTEGER PRIMARY KEY, attention_score REAL DEFAULT 0, novelty_score REAL DEFAULT 0,
        uncertainty_score REAL DEFAULT 0, reward_score REAL DEFAULT 0, fatigue_score REAL DEFAULT 0,
        last_reason TEXT, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS attention_queue_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reading_strategy_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_clusters(
        id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, cluster_key TEXT, hypothesis_count INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0,
        created_at INTEGER DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS hypothesis_stability_scores(
        hypothesis_id INTEGER PRIMARY KEY, stability_score REAL DEFAULT 0, revision_pressure REAL DEFAULT 0,
        confirmation_signal REAL DEFAULT 0, contradiction_signal REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS context_pattern_memory(
        pattern_key TEXT PRIMARY KEY, role TEXT, seen_count INTEGER DEFAULT 0,
        avg_confidence REAL DEFAULT 0, avg_uncertainty REAL DEFAULT 0, stability REAL DEFAULT 0, updated_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS neuromodulator_sleep_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, sleep_type TEXT, processed_hypotheses INTEGER DEFAULT 0,
        consolidated_clusters INTEGER DEFAULT 0, dopamine REAL DEFAULT 0, serotonin REAL DEFAULT 0,
        glutamate REAL DEFAULT 0, gaba REAL DEFAULT 0, noradrenaline REAL DEFAULT 0,
        acetylcholine REAL DEFAULT 0, details TEXT, created_at INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS learning_strategy_state(
        key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER DEFAULT 0)""")

    # populate role stats from hypotheses
    if _table_exists(cur,'context_hypotheses') and {'role','confidence','uncertainty'}.issubset(_cols(cur,'context_hypotheses')):
        rows=cur.execute("SELECT COALESCE(role,'unknown'), COUNT(*), AVG(COALESCE(confidence,0)), AVG(COALESCE(uncertainty,1)) FROM context_hypotheses GROUP BY COALESCE(role,'unknown')").fetchall()
        for role,count,avgc,avgu in rows:
            row=cur.execute("SELECT rowid FROM context_role_stats WHERE role=? LIMIT 1",(role,)).fetchone()
            if row:
                cur.execute("UPDATE context_role_stats SET seen_count=?, avg_confidence=?, avg_uncertainty=?, updated_at=? WHERE rowid=?",(count,avgc or 0,avgu or 1,now,row[0]))
            else:
                cur.execute("INSERT INTO context_role_stats(role,seen_count,avg_confidence,avg_uncertainty,updated_at) VALUES(?,?,?,?,?)",(role,count,avgc or 0,avgu or 1,now))

    # seed reading queue if empty and chunks table exists
    try:
        q=cur.execute("SELECT COUNT(*) FROM reading_queue").fetchone()[0]
        if q==0 and _table_exists(cur,'chunks'):
            ccols=_cols(cur,'chunks'); idcol='id' if 'id' in ccols else ('chunk_id' if 'chunk_id' in ccols else None)
            if idcol:
                for (cid,) in cur.execute(f"SELECT {idcol} FROM chunks ORDER BY {idcol} LIMIT 2000").fetchall():
                    cur.execute("INSERT OR IGNORE INTO reading_queue(chunk_id,priority,reason,attention_score,status,updated_at) VALUES(?,?,?,?,?,?)",(cid,0.5,'phase4def_schema_seed',0.5,'pending',now))
    except Exception:
        pass

    for k,v in {'phase4def_schema_status_fix':'fixed1','phase4d_hypothesis_feedback_error_learning':'enabled','phase4e_neuromodulated_attention_strategy':'enabled','phase4f_sleep_consolidation_self_improvement':'enabled'}.items():
        cur.execute("INSERT OR REPLACE INTO learning_strategy_state(key,value,updated_at) VALUES(?,?,?)",(k,repr(v),now))
    con.commit()
    if close: con.close()
    return True

if __name__=='__main__':
    ensure_phase4def_schema(DB_DEFAULT)
    print('OK: phase4def schema/status fixed and migrated safely')
