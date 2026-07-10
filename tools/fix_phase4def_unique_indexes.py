import sqlite3

db_path = "ki_memory.sqlite3"

targets = [
    ("hypothesis_clusters", "cluster_key"),
    ("context_pattern_memory", "pattern_key"),
    ("chunk_attention_scores", "chunk_id"),
    ("hypothesis_stability_scores", "hypothesis_id"),
    ("context_role_stats", "role"),
]

con = sqlite3.connect(db_path)
cur = con.cursor()

for table, column in targets:
    table_exists = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()

    if not table_exists:
        print("SKIP missing table:", table)
        continue

    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]

    if column not in cols:
        print("SKIP missing column:", table, column)
        continue

    duplicates = cur.execute(
        f"""
        SELECT {column}, COUNT(*)
        FROM {table}
        GROUP BY {column}
        HAVING COUNT(*) > 1
        LIMIT 5
        """
    ).fetchall()

    if duplicates:
        print("SKIP duplicates exist:", table, column, duplicates)
        continue

    index_name = f"idx_{table}_{column}_unique"
    cur.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table}({column})"
    )
    print("OK unique:", table, column)

con.commit()
con.close()

print("DONE")