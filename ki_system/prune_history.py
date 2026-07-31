# -*- coding: utf-8 -*-
"""Ringpuffer-Pruning fuer reine Log-/History-Tabellen (behaelt die letzten N Zeilen).
Strikte Whitelist. Default = DRY-RUN. Echt nur mit --apply (Backup davor). Selbst-Test: --selftest.
Aktives Lernmaterial (context_hypotheses, phase5g/5f/5i, *_state) wird NIEMALS angefasst."""
import sqlite3, os, shutil, sys, time
from pathlib import Path

PRUNE_SPECS = [
    ("pattern_stability_history", 50000),
    ("phase6a_sleep_replay_events", 50000),
    ("hypothesis_learning_updates", 50000),
    ("gap_resolution_outcomes", 50000),
    ("hypothesis_self_evaluations", 50000),
    ("hypothesis_role_revisions", 100000),
    ("context_expansion_actions", 50000),
    ("context_learning_events", 50000),
    ("neuromodulated_attention_events", 50000),
    ("phase5b_reread_diversity_events", 50000),
    ("phase7d_up_state_events", 50000),
    ("rereading_candidate_links", 100000),
    ("gap_driven_rereading_actions", 100000),
]

HARD_FORBIDDEN_EXACT = {
    "context_hypotheses", "phase5g_experiment_outcomes", "phase5g_strategy_experiments",
    "phase5f_context_window_experiments", "phase5i_outcome_driven_experiments",
    "chunks", "documents", "import_state",
}

def _forbidden(t):
    n = t.lower()
    if n in HARD_FORBIDDEN_EXACT:
        return True
    if "state" in n or "setting" in n or "config" in n:
        return True
    if n.startswith("chunks_fts") or n.startswith("sqlite_"):
        return True
    return False

def _table_exists(con, t):
    try:
        return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
    except Exception:
        return False

def _has_id(con, t):
    try:
        return "id" in [r[1] for r in con.execute("PRAGMA table_info(" + t + ")").fetchall()]
    except Exception:
        return False

def _count(con, t):
    try:
        return con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
    except Exception:
        return -1

def plan(con, specs=PRUNE_SPECS):
    out = []
    for t, keep in specs:
        if _forbidden(t):
            out.append((t, keep, "FORBIDDEN(skip)", 0)); continue
        if not _table_exists(con, t):
            out.append((t, keep, "missing", 0)); continue
        if not _has_id(con, t):
            out.append((t, keep, "no_id(skip)", 0)); continue
        n = _count(con, t)
        if n <= keep:
            out.append((t, keep, "ok_small(nothing)", 0))
        else:
            out.append((t, keep, "will_prune", n - keep))
    return out

def prune_table(con, t, keep):
    if _forbidden(t):   # defense in depth
        return (t, "FORBIDDEN-ABORT", 0, 0)
    before = _count(con, t)
    if before <= keep:
        return (t, "nothing", before, before)
    maxid = con.execute("SELECT MAX(id) FROM " + t).fetchone()[0]
    cutoff = maxid - keep
    con.execute("DELETE FROM " + t + " WHERE id <= ?", (cutoff,))
    con.commit()
    after = _count(con, t)
    return (t, "pruned", before, after)

def _main():
    dry = "--apply" not in sys.argv
    db = "ki_memory.sqlite3"
    print("=" * 62)
    print("HISTORY-PRUNING " + ("(DRY-RUN - aendert nichts)" if dry else "(APPLY)"))
    print("=" * 62)
    if not os.path.exists(db):
        print("ERROR: ki_memory.sqlite3 nicht gefunden."); return
    con = sqlite3.connect(db, timeout=120)
    pl = plan(con)
    total = 0
    print("\nPLAN:")
    for t, keep, status, est in pl:
        extra = ("  (~%d loeschen, behalte %d)" % (est, keep)) if status == "will_prune" else ""
        print("  %-40s keep %-7d -> %s%s" % (t, keep, status, extra))
        total += est
    print("\nGeschaetzt zu loeschende Zeilen gesamt:", total)
    if dry:
        con.close()
        print("\nDRY-RUN: nichts geaendert. Echter Lauf (mit Backup + VACUUM):")
        print("   python prune_history.py --apply")
        return
    con.close()
    bak = db + ".bak_prune_" + str(int(time.time()))
    print("\nErstelle Backup (~GB, kann dauern) ...")
    shutil.copy2(db, bak)
    print("Backup:", bak)
    con = sqlite3.connect(db, timeout=300)
    print("\nPrune:")
    for t, keep, status, est in pl:
        if status != "will_prune":
            continue
        r = prune_table(con, t, keep)
        print("  %-40s %s: %d -> %d" % (r[0], r[1], r[2], r[3]))
    print("\nVACUUM (gibt Speicher frei, kann bei GB dauern) ...")
    t0 = time.time()
    try:
        con.execute("VACUUM"); con.commit()
        print("VACUUM ok (%.1fs)" % (time.time() - t0))
    except Exception as e:
        print("VACUUM Fehler:", e)
    con.close()
    sz = os.path.getsize(db) / (1024 * 1024)
    print("\nFERTIG. DB jetzt: %.1f MB" % sz)

def _selftest():
    print("SELFTEST prune_history")
    db = "prune_selftest.sqlite3"
    if os.path.exists(db): os.remove(db)
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE pattern_stability_history(id INTEGER PRIMARY KEY, val REAL)")
    c.executemany("INSERT INTO pattern_stability_history(val) VALUES(?)", [(0.1,)] * 120000)
    c.execute("CREATE TABLE hypothesis_role_revisions(id INTEGER PRIMARY KEY, old_role TEXT)")
    c.executemany("INSERT INTO hypothesis_role_revisions(old_role) VALUES(?)", [("x",)] * 40000)
    c.execute("CREATE TABLE context_hypotheses(id INTEGER PRIMARY KEY)")
    c.executemany("INSERT INTO context_hypotheses DEFAULT VALUES", [()] * 5000)
    c.execute("CREATE TABLE phase6a_sleep_replay_events(id INTEGER PRIMARY KEY)")
    c.executemany("INSERT INTO phase6a_sleep_replay_events DEFAULT VALUES", [()] * 10)
    c.commit()
    res = {}
    pl = dict((t, (status, est)) for t, keep, status, est in plan(c))
    res["psh_will_prune"] = "PASS" if pl["pattern_stability_history"][0] == "will_prune" and pl["pattern_stability_history"][1] == 70000 else "FAIL(%s)" % str(pl["pattern_stability_history"])
    res["hrr_ok_small"] = "PASS" if pl["hypothesis_role_revisions"][0] == "ok_small(nothing)" else "FAIL(%s)" % str(pl["hypothesis_role_revisions"])
    res["p6a_ok_small"] = "PASS" if pl["phase6a_sleep_replay_events"][0] == "ok_small(nothing)" else "FAIL"
    # defense: context_hypotheses als Spec -> muss FORBIDDEN sein
    dl = dict((t, status) for t, keep, status, est in plan(c, [("context_hypotheses", 100)]))
    res["ch_forbidden"] = "PASS" if dl["context_hypotheses"] == "FORBIDDEN(skip)" else "FAIL(%s)" % dl["context_hypotheses"]
    # apply
    for t, keep, status, est in pl.items() if False else plan(c):
        if status == "will_prune":
            prune_table(c, t, keep)
    res["psh_after_50k"] = "PASS" if _count(c, "pattern_stability_history") == 50000 else "FAIL(%d)" % _count(c, "pattern_stability_history")
    res["hrr_untouched"] = "PASS" if _count(c, "hypothesis_role_revisions") == 40000 else "FAIL"
    res["ch_untouched"] = "PASS" if _count(c, "context_hypotheses") == 5000 else "FAIL"
    # direct defense call
    r = prune_table(c, "context_hypotheses", 100)
    res["ch_direct_abort"] = "PASS" if r[1] == "FORBIDDEN-ABORT" and _count(c, "context_hypotheses") == 5000 else "FAIL"
    c.close(); os.remove(db)
    order = ["psh_will_prune","hrr_ok_small","p6a_ok_small","ch_forbidden","psh_after_50k","hrr_untouched","ch_untouched","ch_direct_abort"]
    allp = all(res[k].startswith("PASS") for k in order)
    for k in order:
        print("  [%s] %-16s: %s" % ("OK" if res[k].startswith("PASS") else "X", k, res[k]))
    print("OVERALL:", "ALL PASS" if allp else "SOME FAILED")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        _main()
