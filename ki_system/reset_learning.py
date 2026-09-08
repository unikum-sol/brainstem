# -*- coding: utf-8 -*-
"""Modern BrainStem learning reset.

Default mode is read-only dry-run. Productive reset requires --apply.
The imported corpus and explicit project configuration tables are preserved;
all other user tables are cleared. Before any productive write, a complete
sibling project backup is created, with the SQLite database copied through the
SQLite backup API. The current bootstrap is executed after clearing the
learning state, followed by integrity and corpus-preservation checks.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import py_compile
import shutil
import sqlite3
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "ki_memory.sqlite3"
REPORT = ROOT / "reset_learning_report.txt"
RESULT = ROOT / "reset_learning_result.json"

# Explicitly preserved project-owned tables. No broad setting/config heuristic.
KEEP_EXACT = {
    "documents",
    "chunks",
    "import_state",
    "settings",
}

# FTS5 creates implementation-owned shadow tables beside chunks_fts.
KEEP_PREFIXES = ("chunks_fts",)

# These tables must remain empty after reset and the current bootstrap.
# They represent learned content or productive outputs, not bootstrap defaults.
POST_BOOTSTRAP_EMPTY = {
    "facts",
    "relations",
    "questions",
    "context_hypotheses",
    "context_learning_events",
    "internal_learning_gaps",
    "phase5f_context_window_experiments",
    "phase5g_experiment_outcomes",
    "phase5i_outcome_driven_experiments",
    "phase6a_sleep_replay_cycles",
    "phase6b_effectiveness_events",
    "phase6b_plasticity_adjustments",
    "phase6b_l2m_metrics",
    "modern_gap_candidate_shadow",
    "modern_outcome_bridge_shadow",
}


class ResetError(RuntimeError):
    pass


def _quote_identifier(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ResetError("invalid SQLite identifier")
    return '"' + name.replace('"', '""') + '"'


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _tables(con: sqlite3.Connection) -> List[str]:
    return [
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]


def _user_tables(con: sqlite3.Connection) -> List[str]:
    return [table for table in _tables(con) if not table.startswith("sqlite_")]


def _rowcount(con: sqlite3.Connection, table: str) -> int:
    return int(con.execute("SELECT COUNT(*) FROM " + _quote_identifier(table)).fetchone()[0])


def _columns(con: sqlite3.Connection, table: str) -> List[Tuple[Any, ...]]:
    return con.execute("PRAGMA table_info(" + _quote_identifier(table) + ")").fetchall()


def _schema_signature(con: sqlite3.Connection, table: str) -> str:
    return hashlib.sha256(repr(_columns(con, table)).encode("utf-8")).hexdigest()


def _is_keep(name: str) -> bool:
    lower = name.lower()
    if lower in KEEP_EXACT:
        return True
    return any(lower == prefix or lower.startswith(prefix + "_") for prefix in KEEP_PREFIXES)


def _classification(con: sqlite3.Connection) -> Tuple[List[str], List[str]]:
    tables = _user_tables(con)
    keep = sorted(table for table in tables if _is_keep(table))
    wipe = sorted(table for table in tables if not _is_keep(table))
    if set(keep) & set(wipe):
        raise ResetError("KEEP/WIPE classification overlap")
    if sorted(keep + wipe) != sorted(tables):
        raise ResetError("KEEP/WIPE classification incomplete")
    missing_required = sorted(table for table in ("documents", "chunks") if table not in keep)
    if missing_required:
        raise ResetError("required corpus tables missing: " + repr(missing_required))
    return keep, wipe


def _snapshot_kept(con: sqlite3.Connection, keep: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    return {
        table: {
            "rows": _rowcount(con, table),
            "schema_sha256": _schema_signature(con, table),
        }
        for table in keep
    }


def _database_checks(con: sqlite3.Connection) -> Dict[str, Any]:
    return {
        "quick_check": [row[0] for row in con.execute("PRAGMA quick_check")],
        "integrity_check": [row[0] for row in con.execute("PRAGMA integrity_check")],
        "foreign_key_check": [list(row) for row in con.execute("PRAGMA foreign_key_check")],
    }


def _checks_ok(checks: Dict[str, Any]) -> bool:
    return (
        checks.get("quick_check") == ["ok"]
        and checks.get("integrity_check") == ["ok"]
        and checks.get("foreign_key_check") == []
    )


def _sqlite_backup(source: Path, destination: Path) -> None:
    source_con = sqlite3.connect(str(source), timeout=120)
    destination_con = sqlite3.connect(str(destination), timeout=120)
    try:
        source_con.backup(destination_con, pages=4096)
    finally:
        destination_con.close()
        source_con.close()


def _restore_database(backup_db: Path, target_db: Path) -> None:
    source_con = sqlite3.connect(str(backup_db), timeout=120)
    target_con = sqlite3.connect(str(target_db), timeout=120)
    try:
        source_con.backup(target_con, pages=4096)
    finally:
        target_con.close()
        source_con.close()


def _backup_ignore(_directory: str, names: Sequence[str]) -> set:
    ignored = {"__pycache__"} if "__pycache__" in names else set()
    for name in ("ki_memory.sqlite3", "ki_memory.sqlite3-wal", "ki_memory.sqlite3-shm"):
        if name in names:
            ignored.add(name)
    return ignored


def _create_full_backup(db_path: Path) -> Tuple[Path, Path, Dict[str, Any]]:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_root = ROOT.parent / (ROOT.name + "_fullbackup_before_learning_reset_" + stamp)
    backup_root.mkdir(parents=False, exist_ok=False)
    try:
        for item in ROOT.iterdir():
            if item.name in {db_path.name, db_path.name + "-wal", db_path.name + "-shm", "__pycache__"}:
                continue
            destination = backup_root / item.name
            if item.is_dir():
                shutil.copytree(item, destination, ignore=_backup_ignore)
            else:
                shutil.copy2(item, destination)
        backup_db = backup_root / db_path.name
        _sqlite_backup(db_path, backup_db)
        con = sqlite3.connect(str(backup_db), timeout=120)
        try:
            checks = _database_checks(con)
        finally:
            con.close()
        if not _checks_ok(checks):
            raise ResetError("backup database checks failed: " + repr(checks))
        if not (backup_root / "ki_system").is_dir() or not (backup_root / "reset_learning.py").is_file():
            raise ResetError("full project backup completeness check failed")
        return backup_root, backup_db, checks
    except Exception:
        shutil.rmtree(backup_root, ignore_errors=True)
        raise


def _trigger_rows(con: sqlite3.Connection) -> List[Tuple[Any, ...]]:
    return con.execute(
        "SELECT name,tbl_name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name"
    ).fetchall()


def _reset_sequences(con: sqlite3.Connection, wipe: Iterable[str]) -> int:
    if not _table_exists(con, "sqlite_sequence"):
        return 0
    wipe_list = list(wipe)
    if not wipe_list:
        return 0
    placeholders = ",".join("?" for _ in wipe_list)
    cursor = con.execute(
        "DELETE FROM sqlite_sequence WHERE name IN (" + placeholders + ")",
        wipe_list,
    )
    return max(0, int(cursor.rowcount if cursor.rowcount is not None else 0))


def _run_current_bootstrap(db_path: Path) -> Dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    module_name = "ki_system.db_bootstrap"
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
    else:
        module = importlib.import_module(module_name)
    ensure_database_exists = getattr(module, "ensure_database_exists", None)
    if callable(ensure_database_exists):
        result = ensure_database_exists(str(db_path))
    else:
        ensure_schema_for = getattr(module, "ensure_schema_for", None)
        if not callable(ensure_schema_for):
            raise ResetError("current bootstrap exposes no supported entry point")
        result = ensure_schema_for(str(db_path))
    if isinstance(result, dict) and result.get("errors"):
        raise ResetError("bootstrap reported errors: " + repr(result.get("errors")))
    return result if isinstance(result, dict) else {"result": result}


def _atomic_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(str(temporary), str(path))


def _render_report(result: Dict[str, Any]) -> str:
    lines = [
        "=" * 79,
        "BRAINSTEM MODERN LEARNING RESET",
        "=" * 79,
        "Mode: " + result["mode"],
        "Verdict: " + result["verdict"],
        "Database: " + result["database"],
        "Kept tables: " + json.dumps(result["kept_tables"], ensure_ascii=False),
        "Wiped table count: " + str(len(result["wipe_plan"])),
        "Wipe plan rows: " + str(sum(item["rows"] for item in result["wipe_plan"])),
        "Backup: " + str(result.get("backup")),
        "Corpus preserved: " + str(result.get("corpus_preserved")),
        "Post-bootstrap empty checks: " + json.dumps(result.get("post_bootstrap_empty_checks"), sort_keys=True),
        "Final database checks: " + json.dumps(result.get("final_checks"), sort_keys=True),
        "Error: " + str(result.get("error")),
        "=" * 79,
        "",
    ]
    return "\n".join(lines)


def _write_results(result: Dict[str, Any]) -> None:
    _atomic_json(RESULT, result)
    REPORT.write_text(_render_report(result), encoding="utf-8")


def build_plan(db_path: Path) -> Dict[str, Any]:
    if not db_path.is_file():
        raise ResetError("database missing: " + str(db_path))
    con = sqlite3.connect(str(db_path), timeout=120)
    try:
        checks = _database_checks(con)
        if not _checks_ok(checks):
            raise ResetError("database precheck failed: " + repr(checks))
        trigger_rows = _trigger_rows(con)
        if trigger_rows:
            raise ResetError("database contains triggers; reset refuses implicit trigger side effects")
        keep, wipe = _classification(con)
        kept_snapshot = _snapshot_kept(con, keep)
        wipe_plan = [{"table": table, "rows": _rowcount(con, table)} for table in wipe]
        return {
            "database": str(db_path.resolve()),
            "kept_tables": keep,
            "kept_snapshot": kept_snapshot,
            "wipe_plan": wipe_plan,
            "pre_checks": checks,
            "trigger_count": len(trigger_rows),
        }
    finally:
        con.close()


def reset_learning(db_path: str = "ki_memory.sqlite3", dry_run: bool = True) -> Dict[str, Any]:
    path = Path(db_path)
    if not path.is_absolute():
        path = ROOT / path
    plan = build_plan(path)
    result: Dict[str, Any] = {
        "mode": "dry_run" if dry_run else "apply",
        "verdict": "DRY_RUN_OK" if dry_run else "RUNNING",
        "database": plan["database"],
        "kept_tables": plan["kept_tables"],
        "kept_snapshot": plan["kept_snapshot"],
        "wipe_plan": plan["wipe_plan"],
        "pre_checks": plan["pre_checks"],
        "backup": None,
        "deleted": {},
        "sequence_rows_reset": 0,
        "bootstrap": None,
        "corpus_preserved": None,
        "post_bootstrap_empty_checks": {},
        "final_checks": None,
        "error": None,
    }
    if dry_run:
        _write_results(result)
        return result

    backup_root: Path | None = None
    backup_db: Path | None = None
    try:
        backup_root, backup_db, backup_checks = _create_full_backup(path)
        result["backup"] = str(backup_root)
        result["backup_checks"] = backup_checks

        con = sqlite3.connect(str(path), timeout=300, isolation_level=None)
        try:
            con.execute("PRAGMA foreign_keys=OFF")
            con.execute("BEGIN IMMEDIATE")
            try:
                for item in plan["wipe_plan"]:
                    table = item["table"]
                    before = _rowcount(con, table)
                    con.execute("DELETE FROM " + _quote_identifier(table))
                    after = _rowcount(con, table)
                    if after != 0:
                        raise ResetError("table not empty after DELETE: " + table)
                    result["deleted"][table] = before
                result["sequence_rows_reset"] = _reset_sequences(
                    con, [item["table"] for item in plan["wipe_plan"]]
                )
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
        finally:
            con.close()

        result["bootstrap"] = _run_current_bootstrap(path)

        con = sqlite3.connect(str(path), timeout=300)
        try:
            current_keep = _snapshot_kept(con, plan["kept_tables"])
            corpus_preserved = current_keep == plan["kept_snapshot"]
            result["corpus_preserved"] = corpus_preserved
            if not corpus_preserved:
                raise ResetError("kept corpus/configuration tables changed")

            empty_checks = {
                table: _rowcount(con, table)
                for table in sorted(POST_BOOTSTRAP_EMPTY)
                if _table_exists(con, table)
            }
            result["post_bootstrap_empty_checks"] = empty_checks
            nonzero = {table: rows for table, rows in empty_checks.items() if rows != 0}
            if nonzero:
                raise ResetError("learning/output tables repopulated by bootstrap: " + repr(nonzero))

            final_checks = _database_checks(con)
            result["final_checks"] = final_checks
            if not _checks_ok(final_checks):
                raise ResetError("final database checks failed: " + repr(final_checks))
        finally:
            con.close()

        con = sqlite3.connect(str(path), timeout=300)
        try:
            con.execute("VACUUM")
            con.commit()
            post_vacuum_checks = _database_checks(con)
            result["post_vacuum_checks"] = post_vacuum_checks
            if not _checks_ok(post_vacuum_checks):
                raise ResetError("post-VACUUM checks failed: " + repr(post_vacuum_checks))
        finally:
            con.close()

        result["verdict"] = "RESET_OK"
        _write_results(result)
        return result
    except Exception as exc:
        result["verdict"] = "RESET_FAILED_ROLLBACK_REQUIRED"
        result["error"] = type(exc).__name__ + ": " + str(exc)
        rollback_error = None
        if backup_db is not None and backup_db.is_file():
            try:
                _restore_database(backup_db, path)
                restored = sqlite3.connect(str(path), timeout=300)
                try:
                    restore_checks = _database_checks(restored)
                finally:
                    restored.close()
                result["rollback_checks"] = restore_checks
                if not _checks_ok(restore_checks):
                    rollback_error = "restored database checks failed: " + repr(restore_checks)
            except Exception as restore_exc:
                rollback_error = type(restore_exc).__name__ + ": " + str(restore_exc)
        else:
            rollback_error = "verified backup database unavailable"
        result["rollback_error"] = rollback_error
        if rollback_error is None:
            result["verdict"] = "RESET_FAILED_ROLLED_BACK"
        _write_results(result)
        raise


def _selftest() -> int:
    with tempfile.TemporaryDirectory(prefix="brainstem_reset_selftest_") as temporary:
        database = Path(temporary) / "test.sqlite3"
        con = sqlite3.connect(str(database))
        try:
            con.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, title TEXT)")
            con.execute("CREATE TABLE chunks(id INTEGER PRIMARY KEY, text TEXT)")
            con.execute("CREATE TABLE chunks_fts_data(id INTEGER PRIMARY KEY, block BLOB)")
            con.execute("CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT)")
            con.execute("CREATE TABLE context_hypotheses(id INTEGER PRIMARY KEY, text TEXT)")
            con.execute("INSERT INTO documents VALUES(1,'doc')")
            con.execute("INSERT INTO chunks VALUES(1,'text')")
            con.execute("INSERT INTO chunks_fts_data VALUES(1,X'00')")
            con.execute("INSERT INTO settings VALUES('x','y')")
            con.execute("INSERT INTO context_hypotheses VALUES(1,'learned')")
            con.commit()
            keep, wipe = _classification(con)
            if keep != ["chunks", "chunks_fts_data", "documents", "settings"]:
                raise ResetError("selftest KEEP mismatch: " + repr(keep))
            if wipe != ["context_hypotheses"]:
                raise ResetError("selftest WIPE mismatch: " + repr(wipe))
            snapshot = _snapshot_kept(con, keep)
            con.execute("DELETE FROM context_hypotheses")
            con.commit()
            if _rowcount(con, "context_hypotheses") != 0:
                raise ResetError("selftest delete failed")
            if _snapshot_kept(con, keep) != snapshot:
                raise ResetError("selftest preserved data changed")
            checks = _database_checks(con)
            if not _checks_ok(checks):
                raise ResetError("selftest checks failed")
        finally:
            con.close()
    print("SELFTEST OK")
    print("EXPLICIT KEEP CLASSIFICATION OK")
    print("PRESERVED TABLE INVARIANT OK")
    print("DATABASE CHECKS OK")
    return 0


def _print_summary(result: Dict[str, Any]) -> None:
    print("=" * 79)
    print("BRAINSTEM MODERN LEARNING RESET")
    print("=" * 79)
    print("MODE:", result["mode"])
    print("VERDICT:", result["verdict"])
    print("DATABASE:", result["database"])
    print("KEEP:", result["kept_tables"])
    print("WIPE TABLES:", len(result["wipe_plan"]))
    print("WIPE ROWS:", sum(item["rows"] for item in result["wipe_plan"]))
    if result["mode"] == "dry_run":
        print("DATABASE WRITES: none")
        print("Apply only with: python reset_learning.py --apply")
    else:
        print("FULL BACKUP:", result.get("backup"))
        print("CORPUS PRESERVED:", result.get("corpus_preserved"))
        print("FINAL CHECKS:", result.get("final_checks"))
    print("REPORT:", REPORT)
    print("RESULT:", RESULT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="perform the productive reset")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    if args.selftest:
        return _selftest()
    try:
        result = reset_learning(args.db, dry_run=not args.apply)
        _print_summary(result)
        return 0
    except Exception as exc:
        print("RESET FAILED:", type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        traceback.print_exc()
        if REPORT.is_file():
            print("REPORT:", REPORT, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
