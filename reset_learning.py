from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import reset_learning_current_schema_v2_1 as engine

ROOT = Path(__file__).resolve().parent
DB = ROOT / "ki_memory.sqlite3"
BACKUP_DIR = ROOT / "backups"
REPORT = ROOT / "reset_learning_report.json"


def main() -> int:
    try:
        if not DB.is_file():
            raise engine.ResetError("database missing: " + str(DB))

        gate = engine.preflight(DB, ROOT)
        if gate.get("blockers"):
            raise engine.ResetError("reset blocked by preflight: " + repr(gate["blockers"]))

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        backup = BACKUP_DIR / ("ki_memory_before_learning_reset_" + stamp + ".sqlite3")
        counter = 1
        while backup.exists():
            backup = BACKUP_DIR / ("ki_memory_before_learning_reset_" + stamp + "_" + str(counter) + ".sqlite3")
            counter += 1

        result = engine.apply(DB, ROOT, backup)
        result["preflight_gate"] = {
            "verdict": gate.get("verdict"),
            "blockers": gate.get("blockers", []),
        }
        engine.atomic_json(REPORT, result)

        print(json.dumps({
            "verdict": result["verdict"],
            "backup": str(backup),
            "live_tables": result["classification"]["live_count"],
            "kept_tables": result["classification"]["keep_count"],
            "wiped_tables": result["classification"]["wipe_count"],
            "keep_changed": result.get("keep_changed", {}),
            "nonzero_wiped_after_bootstrap": result.get("nonzero_wiped_after_bootstrap", {}),
            "report": str(REPORT),
        }, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print("SAFE_ABORT " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
