# -*- coding: utf-8 -*-
"""Lern-Reset fuer BrainStem: setzt die DB so zurueck, dass NUR der importierte Korpus bleibt
(chunks, chunks_fts*, documents, settings/config, sqlite-intern). Alles vom Lernsystem Erzeugte wird geleert.
Default = DRY-RUN (zeigt nur an, aendert nichts). Echter Reset nur mit --apply (macht vorher ein Backup)."""
import sqlite3, shutil, sys, time
from pathlib import Path

def _tables(con):
    try:
        return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    except Exception:
        return []

def _rowcount(con, t):
    try:
        return con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
    except Exception:
        return -1

def _is_keep(name):
    n = name.lower()
    if n == "chunks":
        return True
    if n.startswith("chunks_fts"):
        return True
    if n == "documents":
        return True
    if "setting" in n or "config" in n:
        return True
    if n.startswith("sqlite_"):
        return True
    if n == "import_state":
        return True
    return False

def reset_learning(db_path="ki_memory.sqlite3", dry_run=True):
    report = {"kept": [], "wipe": [], "backup": None, "deleted": {}}
    con = sqlite3.connect(db_path)
    all_tables = _tables(con)
    keep = [t for t in all_tables if _is_keep(t)]
    wipe = [t for t in all_tables if not _is_keep(t)]
    report["kept"] = sorted(keep)
    report["wipe"] = [(t, _rowcount(con, t)) for t in sorted(wipe)]
    if dry_run:
        con.close()
        return report
    con.close()
    bak = db_path + ".bak_reset_" + str(int(time.time()))
    shutil.copy2(db_path, bak)
    report["backup"] = bak
    con = sqlite3.connect(db_path)
    for t in sorted(wipe):
        before = _rowcount(con, t)
        try:
            con.execute("DELETE FROM " + t)
            report["deleted"][t] = before
        except Exception as e:
            report["deleted"][t] = "ERR: " + str(e)
    con.commit()
    try:
        con.execute("VACUUM")
    except Exception:
        pass
    con.commit()
    con.close()
    return report

def _main():
    dry = "--apply" not in sys.argv
    db = "ki_memory.sqlite3"
    print("=" * 60)
    print("BRAINSTEM LERN-RESET " + ("(DRY-RUN - aendert nichts)" if dry else "(APPLY - echter Reset)"))
    print("=" * 60)
    rep = reset_learning(db, dry_run=dry)
    print("\nBEHALTEN (KEEP):")
    for t in rep["kept"]:
        print("  + " + t)
    print("\nWIRD GELEERT (WIPE):")
    for t, n in rep["wipe"]:
        print("  - %-42s %s Zeilen" % (t, n))
    if dry:
        print("\nDRY-RUN: es wurde NICHTS geaendert.")
        print("Fuer den echten Reset (mit automatischem Backup):")
        print("   python reset_learning.py --apply")
    else:
        print("\nBackup angelegt:", rep["backup"])
        print("\nGeleert:")
        for t, n in rep["deleted"].items():
            print("  - %-42s %s" % (t, n))
        print("\nFERTIG: Nur der importierte Korpus bleibt, Lernsystem ist zurueckgesetzt.")

if __name__ == "__main__":
    _main()
