# -*- coding: utf-8 -*-
"""BrainStem Non-Productive Recheck Initialization Attribution, Cursor Wrap & Fairness Telemetry V1.2.

V1.2 wraps the validated V1.1 contract without changing its eligibility logic.
It adds exact initialization attribution, per-watermark change accounting,
cursor-wrap evidence, and awaiting-pool fairness telemetry.
"""
from __future__ import annotations
import argparse, importlib.util, json, sqlite3, tempfile
from pathlib import Path
from typing import Any, Dict, List

VERSION = "non_productive_recheck_initialization_cursor_wrap_fairness_telemetry_v1_2"
BASE_FILE = "v8_non_productive_delayed_evidence_recheck_watermark_awaiting_state_contract_v1_1.py"
TELEMETRY_COLUMNS = {
    "recheck_rows_first_evaluation": "INTEGER NOT NULL DEFAULT 0",
    "recheck_rows_previously_evaluated": "INTEGER NOT NULL DEFAULT 0",
    "event_watermark_changed": "INTEGER NOT NULL DEFAULT 0",
    "read_watermark_changed": "INTEGER NOT NULL DEFAULT 0",
    "stability_watermark_changed": "INTEGER NOT NULL DEFAULT 0",
    "recheck_rows_any_watermark_changed_after_initialization": "INTEGER NOT NULL DEFAULT 0",
    "recheck_cursor_before": "TEXT NOT NULL DEFAULT ''",
    "recheck_cursor_after": "TEXT NOT NULL DEFAULT ''",
    "recheck_cursor_wrapped": "INTEGER NOT NULL DEFAULT 0",
    "awaiting_pool_before": "INTEGER NOT NULL DEFAULT 0",
    "awaiting_pool_after": "INTEGER NOT NULL DEFAULT 0",
    "never_rechecked_rows": "INTEGER NOT NULL DEFAULT 0",
    "previously_rechecked_rows": "INTEGER NOT NULL DEFAULT 0",
    "min_recheck_count": "INTEGER NOT NULL DEFAULT 0",
    "max_recheck_count": "INTEGER NOT NULL DEFAULT 0",
}
SCHEMA_TABLES = {"non_productive_real_outcome_observation_shadow_cycles": ["id"] + list(TELEMETRY_COLUMNS)}

def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _q(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'

def _load_base(path: Path):
    spec = importlib.util.spec_from_file_location("brainstem_np_recheck_v1_1_base", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load V1.1 base: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _base_path() -> Path:
    return Path(__file__).resolve().with_name(BASE_FILE)

def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    return [str(row[1]) for row in con.execute("PRAGMA table_info(" + _q(table) + ")")]

def ensure_schema(con: sqlite3.Connection, base) -> None:
    base.ensure_schema(con)
    columns = set(_columns(con, base.CYCLES))
    for name, declaration in TELEMETRY_COLUMNS.items():
        if name not in columns:
            con.execute("ALTER TABLE " + _q(base.CYCLES) + " ADD COLUMN " + _q(name) + " " + declaration)
            columns.add(name)
    now = base.now()
    defaults = {
        "telemetry_version": "v1.2",
        "last_recheck_rows_first_evaluation": "0",
        "last_recheck_rows_previously_evaluated": "0",
        "last_recheck_cursor_wrapped": "false",
        "last_never_rechecked_rows": "0",
        "last_previously_rechecked_rows": "0",
        "runtime_registration": "not_opened",
        "productive_writes": "disabled",
        "phase5i_writes": "disabled",
    }
    for key, value in defaults.items():
        con.execute(
            "INSERT OR IGNORE INTO " + base.STATE + "(key,value,updated_at) VALUES(?,?,?)",
            (key, value, now),
        )

def _self_check_schema(con: sqlite3.Connection, base) -> None:
    base.self_check(con)
    cycle_columns = set(_columns(con, base.CYCLES))
    missing = [name for name in SCHEMA_TABLES[base.CYCLES] if name not in cycle_columns]
    if missing:
        raise RuntimeError("V1.2 cycle schema missing: " + ", ".join(missing))

def _awaiting_pool(con: sqlite3.Connection, base) -> int:
    return int(con.execute("SELECT COUNT(*) FROM " + base.SHADOW + " WHERE non_productive_eligible=0").fetchone()[0])

def _fairness(con: sqlite3.Connection, base) -> Dict[str, int]:
    row = con.execute(
        "SELECT "
        "SUM(CASE WHEN recheck_count=0 THEN 1 ELSE 0 END),"
        "SUM(CASE WHEN recheck_count>0 THEN 1 ELSE 0 END),"
        "COALESCE(MIN(recheck_count),0),COALESCE(MAX(recheck_count),0) "
        "FROM " + base.SHADOW + " WHERE non_productive_eligible=0"
    ).fetchone()
    return {
        "never_rechecked_rows": int(row[0] or 0),
        "previously_rechecked_rows": int(row[1] or 0),
        "min_recheck_count": int(row[2] or 0),
        "max_recheck_count": int(row[3] or 0),
    }

def _snapshot_selected(con: sqlite3.Connection, base, cursor: str, limit: int) -> List[Dict[str, Any]]:
    result = []
    for row in base.recheck_rows(con, cursor, limit):
        result.append({
            "eligibility_key": str(row[0]),
            "last_evaluated_at": int(con.execute("SELECT last_evaluated_at FROM " + base.SHADOW + " WHERE eligibility_key=?", (row[0],)).fetchone()[0] or 0),
            "recheck_count": int(con.execute("SELECT recheck_count FROM " + base.SHADOW + " WHERE eligibility_key=?", (row[0],)).fetchone()[0] or 0),
            "event": int(row[6] or 0), "read": int(row[7] or 0), "stability": int(row[8] or 0),
        })
    return result

def run_phase(con: sqlite3.Connection, limit: int = 512, recheck_limit: int = 512) -> Dict[str, Any]:
    base = _load_base(_base_path())
    ensure_schema(con, base)
    _self_check_schema(con, base)
    state_before = base._read_kv(con, base.STATE)
    cursor_before = str(state_before.get("recheck_cursor_key", "") or "")
    bounded_recheck = min(max(0, int(recheck_limit)), min(max(1, int(limit)), base.LIMIT))
    selected_before = _snapshot_selected(con, base, cursor_before, bounded_recheck)
    pool_before = _awaiting_pool(con, base)
    selected_keys = [item["eligibility_key"] for item in selected_before]
    first = sum(1 for item in selected_before if item["recheck_count"] == 0 or item["last_evaluated_at"] == 0)
    previous = len(selected_before) - first
    wrapped = bool(cursor_before and any(key <= cursor_before for key in selected_keys))

    result = base.run_phase(con, limit, recheck_limit)
    state_after = base._read_kv(con, base.STATE)
    cursor_after = str(state_after.get("recheck_cursor_key", "") or "")
    event_changed = read_changed = stability_changed = changed_after_initialization = 0
    before_map = {item["eligibility_key"]: item for item in selected_before}
    if selected_keys:
        placeholders = ",".join("?" for _ in selected_keys)
        rows = con.execute(
            "SELECT eligibility_key,last_event_watermark,last_read_watermark,last_stability_watermark "
            "FROM " + base.SHADOW + " WHERE eligibility_key IN (" + placeholders + ")",
            tuple(selected_keys),
        ).fetchall()
        for key, event_wm, read_wm, stability_wm in rows:
            old = before_map[str(key)]
            event_delta = int(event_wm or 0) != old["event"]
            read_delta = int(read_wm or 0) != old["read"]
            stability_delta = int(stability_wm or 0) != old["stability"]
            event_changed += int(event_delta)
            read_changed += int(read_delta)
            stability_changed += int(stability_delta)
            if old["recheck_count"] > 0 and (event_delta or read_delta or stability_delta):
                changed_after_initialization += 1

    pool_after = _awaiting_pool(con, base)
    fairness = _fairness(con, base)
    cycle_id = int(con.execute("SELECT MAX(id) FROM " + base.CYCLES).fetchone()[0])
    telemetry = {
        "recheck_rows_first_evaluation": first,
        "recheck_rows_previously_evaluated": previous,
        "event_watermark_changed": event_changed,
        "read_watermark_changed": read_changed,
        "stability_watermark_changed": stability_changed,
        "recheck_rows_any_watermark_changed_after_initialization": changed_after_initialization,
        "recheck_cursor_before": cursor_before,
        "recheck_cursor_after": cursor_after,
        "recheck_cursor_wrapped": int(wrapped),
        "awaiting_pool_before": pool_before,
        "awaiting_pool_after": pool_after,
        **fairness,
    }
    assignments = ",".join(_q(name) + "=?" for name in telemetry)
    con.execute(
        "UPDATE " + base.CYCLES + " SET " + assignments + " WHERE id=?",
        tuple(telemetry.values()) + (cycle_id,),
    )
    base.write_state(con, {
        "telemetry_version": "v1.2",
        "last_recheck_rows_first_evaluation": first,
        "last_recheck_rows_previously_evaluated": previous,
        "last_event_watermark_changed": event_changed,
        "last_read_watermark_changed": read_changed,
        "last_stability_watermark_changed": stability_changed,
        "last_recheck_rows_any_watermark_changed_after_initialization": changed_after_initialization,
        "last_recheck_cursor_wrapped": bool(wrapped),
        "last_never_rechecked_rows": fairness["never_rechecked_rows"],
        "last_previously_rechecked_rows": fairness["previously_rechecked_rows"],
        "runtime_registration": "not_opened",
        "productive_writes": "disabled",
        "phase5i_writes": "disabled",
    }, base.now())
    result.update(telemetry)
    result["phase"] = VERSION
    result["mode"] = "shadow_recheck_telemetry"
    return result

def run_database(path: Path, limit: int, recheck_limit: int) -> Dict[str, Any]:
    con = sqlite3.connect(str(path))
    try:
        con.execute("BEGIN IMMEDIATE")
        result = run_phase(con, limit, recheck_limit)
        con.commit()
        return result
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base_source = Path(__file__).resolve().with_name(BASE_FILE)
        target_base = root / BASE_FILE
        target_base.write_bytes(base_source.read_bytes())
        global _base_path
        original = _base_path
        _base_path = lambda: target_base
        try:
            db = root / "test.sqlite3"
            con = sqlite3.connect(str(db))
            con.executescript(
                "CREATE TABLE modern_gap_phase5f_shadow_observation_v2_latest(stable_observation_key TEXT,shadow_key TEXT,hypothesis_id INTEGER,latest_source_updated_at INTEGER,latest_projection_fingerprint TEXT,target_chunk_ids TEXT);"
                "CREATE TABLE context_learning_events(hypothesis_id INTEGER,event_type TEXT,created_at INTEGER);"
                "CREATE TABLE reading_queue(chunk_id INTEGER,status TEXT,read_count INTEGER,updated_at INTEGER);"
                "CREATE TABLE hypothesis_stability_scores(hypothesis_id INTEGER,stability REAL,updated_at INTEGER);"
                "CREATE TABLE facts(id INTEGER);CREATE TABLE relations(id INTEGER);CREATE TABLE questions(id INTEGER);CREATE TABLE internal_learning_gaps(id INTEGER);CREATE TABLE phase5i_outcome_driven_experiments(id INTEGER);CREATE TABLE modern_outcome_bridge_shadow(id INTEGER);"
                "INSERT INTO modern_gap_phase5f_shadow_observation_v2_latest VALUES('o','s',1,100,'p','[10]');"
            )
            con.commit()
            base = _load_base(target_base)
            base.run_phase(con, 1, 0)
            con.commit()
            first = run_phase(con, 1, 1)
            con.commit()
            assert first["recheck_rows_first_evaluation"] == 1
            assert first["recheck_rows_previously_evaluated"] == 0
            con.execute("INSERT INTO context_learning_events VALUES(1,'raw_observation_reobserved',110)")
            con.commit()
            second = run_phase(con, 1, 1)
            con.commit()
            assert second["recheck_rows_first_evaluation"] == 0
            assert second["recheck_rows_previously_evaluated"] == 1
            assert second["event_watermark_changed"] == 1
            assert second["recheck_rows_any_watermark_changed_after_initialization"] == 1
            assert second["recheck_cursor_wrapped"] == 1
            assert second["productive_writes"] == 0 and second["phase5i_writes"] == 0
            con.close()
        finally:
            _base_path = original
    print("SELFTEST PASS")
    print(_canon({"initialization_attribution": True, "watermark_types": True, "cursor_wrap": True, "fairness": True, "productive_writes": False, "phase5i_writes": False}))
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    run = sub.add_parser("run")
    run.add_argument("--db", default="ki_memory.sqlite3")
    run.add_argument("--limit", type=int, default=512)
    run.add_argument("--recheck-limit", type=int, default=512)
    args = parser.parse_args()
    if args.cmd == "selftest":
        return selftest()
    print(_canon(run_database(Path(args.db), args.limit, args.recheck_limit)))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
