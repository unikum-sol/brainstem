from __future__ import annotations
import hashlib, importlib.util, json, os, sqlite3, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "ki_memory.sqlite3"
BACKUP_DIR = ROOT / "backups"
REPORT = ROOT / "reset_learning_report.json"
KEEP_EXACT = {"documents", "chunks", "import_state", "settings", "sqlite_sequence"}
FTS_PREFIX = "chunks_fts"

class ResetError(RuntimeError):
    pass

def q(name):
    return '"' + name.replace('"', '""') + '"'

def connect(path, readonly=False):
    if readonly:
        con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=120)
        con.execute("PRAGMA query_only=ON")
    else:
        con = sqlite3.connect(str(path), timeout=120)
    con.execute("PRAGMA busy_timeout=120000")
    return con

def tables(con):
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]

def count(con, table):
    return int(con.execute("SELECT COUNT(*) FROM " + q(table)).fetchone()[0])

def classify(table):
    if table in KEEP_EXACT or table == FTS_PREFIX or table.startswith(FTS_PREFIX + "_"):
        return "keep"
    return "wipe"

def classification(con):
    live = tables(con)
    keep = sorted(t for t in live if classify(t) == "keep")
    wipe = sorted(t for t in live if classify(t) == "wipe")
    overlap = sorted(set(keep) & set(wipe))
    unknown = sorted(set(live) - set(keep) - set(wipe))
    complete = not overlap and not unknown and len(keep) + len(wipe) == len(live)
    return {"live": live, "live_count": len(live), "keep": keep, "keep_count": len(keep), "wipe": wipe, "wipe_count": len(wipe), "overlap": overlap, "unclassified": unknown, "complete": complete}

def checks(con):
    return {"quick_check": [r[0] for r in con.execute("PRAGMA quick_check").fetchall()], "integrity_check": [r[0] for r in con.execute("PRAGMA integrity_check").fetchall()], "foreign_key_check": con.execute("PRAGMA foreign_key_check").fetchall()}

def require_ok(value, label):
    if value["quick_check"] != ["ok"] or value["integrity_check"] != ["ok"] or value["foreign_key_check"]:
        raise ResetError(label + " failed: " + repr(value))

def backup_database(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    src = connect(source); dst = connect(target)
    try:
        src.backup(dst, pages=4096)
    finally:
        dst.close(); src.close()

def load_bootstrap():
    path = ROOT / "ki_system" / "db_bootstrap.py"
    if not path.is_file():
        raise ResetError("missing bootstrap: " + str(path))
    spec = importlib.util.spec_from_file_location("_brainstem_reset_bootstrap", str(path))
    if spec is None or spec.loader is None:
        raise ResetError("cannot load bootstrap")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def run_bootstrap(db):
    mod = load_bootstrap()
    if hasattr(mod, "ensure_database_exists"):
        return mod.ensure_database_exists(str(db))
    if hasattr(mod, "ensure_schema_for"):
        return mod.ensure_schema_for(str(db))
    raise ResetError("bootstrap API missing")

def clear_learning(db):
    con = connect(db)
    try:
        before_check = checks(con); require_ok(before_check, "before reset")
        cls = classification(con)
        if not cls["complete"]:
            raise ResetError("incomplete_or_overlapping_table_classification")
        before = {t: count(con, t) for t in cls["live"]}
        con.execute("BEGIN IMMEDIATE")
        try:
            for table in cls["wipe"]:
                con.execute("DELETE FROM " + q(table))
            if "sqlite_sequence" in cls["keep"] and cls["wipe"]:
                marks = ",".join("?" for _ in cls["wipe"])
                con.execute("DELETE FROM sqlite_sequence WHERE name IN (" + marks + ")", cls["wipe"])
            con.commit()
        except Exception:
            con.rollback(); raise
        after_reset = {t: count(con, t) for t in cls["live"]}
        reset_check = checks(con); require_ok(reset_check, "after reset")
    finally:
        con.close()
    bootstrap_result = run_bootstrap(db)
    con = connect(db)
    try:
        final_check = checks(con); require_ok(final_check, "after bootstrap")
        after = {t: count(con, t) for t in tables(con)}
        keep_changed = {t: {"before": before[t], "after": after.get(t)} for t in cls["keep"] if t != "sqlite_sequence" and after.get(t) != before[t]}
        nonzero = {t: after.get(t, 0) for t in cls["wipe"] if after.get(t, 0) != 0}
    finally:
        con.close()
    return {"classification": cls, "before_counts": before, "after_reset_counts": after_reset, "after_bootstrap_counts": after, "checks": {"before": before_check, "after_reset": reset_check, "after_bootstrap": final_check}, "keep_changed": keep_changed, "nonzero_wiped_after_bootstrap": nonzero, "bootstrap_result": bootstrap_result}

def preflight():
    with tempfile.TemporaryDirectory(prefix="brainstem_reset_") as td:
        copy = Path(td) / DB.name
        backup_database(DB, copy)
        result = clear_learning(copy)
        blockers = []
        if not result["classification"]["complete"]:
            blockers.append("incomplete_or_overlapping_table_classification")
        if result["keep_changed"]:
            blockers.append("preserved_corpus_or_config_changed")
        result.update({"temporary_copy_only": True, "production_database_changed": False, "blockers": blockers, "verdict": "RESET_COMPATIBLE" if not blockers else "RESET_NOT_COMPATIBLE"})
        return result

def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))

def unique_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / ("ki_memory_before_learning_reset_" + stamp + ".sqlite3")
    n = 1
    while path.exists():
        path = BACKUP_DIR / ("ki_memory_before_learning_reset_" + stamp + "_" + str(n) + ".sqlite3")
        n += 1
    return path

def apply():
    gate = preflight()
    if gate["blockers"]:
        raise ResetError("apply blocked by preflight: " + repr(gate["blockers"]))
    backup = unique_backup()
    backup_database(DB, backup)
    result = clear_learning(DB)
    result.update({"verdict": "RESET_APPLIED", "backup": str(backup), "production_database_changed": True, "preflight_gate": {"verdict": gate["verdict"], "blockers": gate["blockers"]}})
    atomic_json(REPORT, result)
    return result

def selftest():
    with tempfile.TemporaryDirectory(prefix="brainstem_reset_selftest_") as td:
        db = Path(td) / "t.sqlite3"; con = sqlite3.connect(str(db))
        con.executescript("CREATE TABLE documents(id INTEGER); CREATE TABLE chunks(id INTEGER); CREATE TABLE import_state(k TEXT); CREATE TABLE settings(k TEXT); CREATE VIRTUAL TABLE chunks_fts USING fts5(body); CREATE TABLE context_hypotheses(id INTEGER); CREATE TABLE phase7d_state(k TEXT);")
        cls = classification(con); con.close()
        assert cls["complete"] and "documents" in cls["keep"] and "chunks_fts_data" in cls["keep"] and "context_hypotheses" in cls["wipe"] and "phase7d_state" in cls["wipe"]
    print("SELFTEST_PASS")

def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
            selftest(); return 0
        if len(sys.argv) > 1:
            raise ResetError("no parameters required; run: python reset_learning.py")
        if not DB.is_file():
            raise ResetError("database missing: " + str(DB))
        result = apply()
        print(json.dumps({"verdict": result["verdict"], "backup": result["backup"], "live_tables": result["classification"]["live_count"], "kept_tables": result["classification"]["keep_count"], "wiped_tables": result["classification"]["wipe_count"], "keep_changed": result["keep_changed"], "nonzero_wiped_after_bootstrap": result["nonzero_wiped_after_bootstrap"], "report": str(REPORT)}, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print("SAFE_ABORT " + type(exc).__name__ + ": " + str(exc), file=sys.stderr); return 1

if __name__ == "__main__":
    raise SystemExit(main())
