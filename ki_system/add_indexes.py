# -*- coding: utf-8 -*-
"""Legt fehlende Indizes auf die tatsaechlich gefilterten Spalten an (behebt SQL-Flaschenhals).
Default = DRY-RUN (zeigt Plan, aendert nichts). Echt nur mit --apply (Backup davor).
Selbst-Test: python add_indexes.py --selftest"""
import sqlite3, os, shutil, sys, time
from pathlib import Path

INDEX_SPECS = [
    ("hypothesis_learning_updates", "hypothesis_id", "idx_hlu_hyp"),
    ("hypothesis_feedback", "hypothesis_id", "idx_hfb_hyp"),
    ("hypothesis_error_events", "hypothesis_id", "idx_hee_hyp"),
    ("hypothesis_stability_scores", "hypothesis_id", "idx_hss_hyp"),
    ("phase5f_context_window_experiments", "target_chunk_id", "idx_p5f_tgt"),
]

def _table_exists(con, t):
    try:
        return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
    except Exception:
        return False

def _col_exists(con, t, c):
    try:
        return c in [r[1] for r in con.execute("PRAGMA table_info(" + t + ")").fetchall()]
    except Exception:
        return False

def _index_exists(con, name):
    try:
        return con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone() is not None
    except Exception:
        return False

def plan(con):
    out = []
    for t, c, name in INDEX_SPECS:
        if not _table_exists(con, t):
            status = "table_missing"
        elif not _col_exists(con, t, c):
            status = "col_missing"
        elif _index_exists(con, name):
            status = "exists"
        else:
            status = "will_create"
        out.append((t, c, name, status))
    return out

def apply_indexes(con):
    results = []
    for t, c, name, status in plan(con):
        if status != "will_create":
            results.append((name, status))
            continue
        t0 = time.time()
        try:
            con.execute("CREATE INDEX IF NOT EXISTS " + name + " ON " + t + "(" + c + ")")
            con.commit()
            results.append((name, "created %.1fs" % (time.time() - t0)))
        except Exception as e:
            results.append((name, "ERR: " + str(e)))
    return results

def _main():
    dry = "--apply" not in sys.argv
    db = "ki_memory.sqlite3"
    print("=" * 60)
    print("INDEX-TOOL " + ("(DRY-RUN - aendert nichts)" if dry else "(APPLY)"))
    print("=" * 60)
    if not os.path.exists(db):
        print("ERROR: ki_memory.sqlite3 nicht gefunden."); return
    con = sqlite3.connect(db, timeout=60)
    print("\nPLAN:")
    for t, c, name, status in plan(con):
        print("  %-40s %-16s -> %s" % (t + "(" + c + ")", name, status))
    if dry:
        con.close()
        print("\nDRY-RUN: nichts geaendert. Echt anlegen (mit Backup):")
        print("   python add_indexes.py --apply")
        return
    con.close()
    bak = db + ".bak_idx_" + str(int(time.time()))
    print("\nErstelle Backup (kann bei ~5.6GB einen Moment dauern) ...")
    shutil.copy2(db, bak)
    print("Backup:", bak)
    con = sqlite3.connect(db, timeout=120)
    print("\nLege Indizes an:")
    for name, res in apply_indexes(con):
        print("  %-16s : %s" % (name, res))
    con.close()
    print("\nFERTIG: Indizes angelegt. Lookups auf diese Spalten sind jetzt schnell.")

def _selftest():
    print("SELFTEST add_indexes")
    db = "idx_selftest.sqlite3"
    if os.path.exists(db): os.remove(db)
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE hypothesis_learning_updates(id INTEGER PRIMARY KEY, hypothesis_id INTEGER, val REAL)")
    c.execute("CREATE TABLE hypothesis_feedback(id INTEGER PRIMARY KEY, hypothesis_id INTEGER)")
    c.execute("CREATE TABLE phase5f_context_window_experiments(id INTEGER PRIMARY KEY, target_chunk_id INTEGER)")
    # hypothesis_error_events fehlt komplett -> table_missing
    # hypothesis_stability_scores hat die Spalte nicht -> col_missing
    c.execute("CREATE TABLE hypothesis_stability_scores(id INTEGER PRIMARY KEY, something REAL)")
    for i in range(50):
        c.execute("INSERT INTO hypothesis_learning_updates(hypothesis_id,val) VALUES(?,?)", (i % 5, 0.1))
    c.commit()
    p = dict((name, status) for t, col, name, status in plan(c))
    res = {}
    res["will_create"] = "PASS" if p.get("idx_hlu_hyp") == "will_create" else "FAIL(%s)" % p.get("idx_hlu_hyp")
    res["table_missing"] = "PASS" if p.get("idx_hee_hyp") == "table_missing" else "FAIL(%s)" % p.get("idx_hee_hyp")
    res["col_missing"] = "PASS" if p.get("idx_hss_hyp") == "col_missing" else "FAIL(%s)" % p.get("idx_hss_hyp")
    # nichts erstellt im Dry-Plan
    res["dry_no_create"] = "PASS" if not _index_exists(c, "idx_hlu_hyp") else "FAIL"
    apply_indexes(c)
    res["created"] = "PASS" if _index_exists(c, "idx_hlu_hyp") and _index_exists(c, "idx_hfb_hyp") and _index_exists(c, "idx_p5f_tgt") else "FAIL"
    res["skip_missing"] = "PASS" if not _index_exists(c, "idx_hee_hyp") and not _index_exists(c, "idx_hss_hyp") else "FAIL"
    c.close(); os.remove(db)
    allp = all(v.startswith("PASS") for v in res.values())
    for k in ("will_create", "table_missing", "col_missing", "dry_no_create", "created", "skip_missing"):
        print("  [%s] %-14s: %s" % ("OK" if res[k].startswith("PASS") else "X", k, res[k]))
    print("OVERALL:", "ALL PASS" if allp else "SOME FAILED")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        _main()