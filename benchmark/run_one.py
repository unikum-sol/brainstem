"""One benchmark run: learning with sensory input on a prepared copy.

Usage: python run_one.py <copy_dir> <cycles> <label> <run_seed>
The copy holds ki_system/ and ki_memory.sqlite3. The run seed selects the
replicate (learning_clock.py); everything else is identical between runs.
Writes <copy>/learn_metrics.csv (one row per cycle) and
<copy>/learn_summary.json. Started by benchmark.py.
"""
import csv, json, os, sqlite3, sys, time, traceback
root = sys.argv[1]; cycles = int(sys.argv[2]); label = sys.argv[3]; run_seed = sys.argv[4]
sys.path.insert(0, root); os.chdir(root)
from ki_system.db_bootstrap import ensure_database_exists
db = os.path.join(root, "ki_memory.sqlite3")
print(label, "bootstrap errors:", ensure_database_exists(db).get("errors"), flush=True)
from ki_system import learning_clock
_seed_con = sqlite3.connect(db)
learning_clock.set_run_seed(_seed_con, run_seed)
_seed_con.close()
from ki_system.memory import Memory
from ki_system.autonomous import AutonomousLoop
from ki_system import v8_cycle_diagnostics_release as diag
mem = Memory(db); c = mem.db; loop = AutonomousLoop(mem)

def kv(t):
    try: return {r[0]: r[1] for r in c.execute(f"SELECT key,value FROM {t}").fetchall()}
    except Exception: return {}
def one(sql, d=None):
    try:
        r = c.execute(sql).fetchone(); return r[0] if r and r[0] is not None else d
    except Exception: return d
def fnum(x):
    try: return round(float(x), 6)
    except Exception: return ""

start = {t: one(f"SELECT COALESCE(MAX(id),0) FROM {t}", 0) for t in
         ("phase7d_consolidation_survivors", "phase6c_regulation_events", "phase6d_saturation_events",
          "phase7c_boundary_events", "phase6b_plasticity_adjustments", "phase6b_critic_snapshot")}
stable0 = one("SELECT COUNT(*) FROM context_hypotheses WHERE role>='stable_' AND role<'stable`'", 0)
cols = ["cycle", "seconds", "state", "dopamine", "dopamine_phasic", "serotonin", "noradrenaline", "acetylcholine",
        "glutamate", "gaba", "histamine", "orexin", "bdnf", "adenosine", "cortisol", "rpe", "pressure",
        "plasticity", "exploration", "consolidation", "inhibition", "revision", "meta_at_bound", "stable", "adj_applied"]
out = open(os.path.join(root, "learn_metrics.csv"), "w", newline="", encoding="utf-8")
w = csv.DictWriter(out, fieldnames=cols); w.writeheader()
exc = 0; findings = 0; t0 = time.time()
for i in range(1, cycles + 1):
    ts = time.time()
    try:
        res = loop.cycle(); c.commit()
        s = diag.summarize_cycle_result(res); findings += len(s["fatal_errors"]) + len(s["warnings"])
    except Exception:
        exc += 1; print(label, "EXCEPTION", i, traceback.format_exc()[-600:], flush=True); continue
    nm = kv("phase6a_neuromodulated_sleep_state"); meta = kv("phase6a_meta_plasticity_state")
    row = {"cycle": i, "seconds": round(time.time() - ts, 3), "state": kv("cooperative_sleep_wake_state").get("state", ""),
           "dopamine": fnum(nm.get("dopamine")), "dopamine_phasic": fnum(nm.get("dopamine_phasic")),
           "serotonin": fnum(nm.get("serotonin")), "noradrenaline": fnum(nm.get("noradrenaline")),
           "acetylcholine": fnum(nm.get("acetylcholine")), "glutamate": fnum(nm.get("glutamate")), "gaba": fnum(nm.get("gaba")),
           "histamine": fnum(nm.get("histamine")), "orexin": fnum(nm.get("orexin")), "bdnf": fnum(nm.get("bdnf")),
           "adenosine": fnum(kv("phase7a_adenosine_state").get("adenosine_level")),
           "cortisol": fnum(kv("cortisol_state").get("cortisol_level")),
           "rpe": fnum(meta.get("reward_prediction_error")), "pressure": fnum(meta.get("last_persistent_gap_pressure")),
           "plasticity": fnum(meta.get("last_plasticity_level")), "exploration": fnum(meta.get("last_exploration_bias")),
           "consolidation": fnum(meta.get("last_consolidation_bias")), "inhibition": fnum(meta.get("last_inhibition_bias")),
           "revision": fnum(meta.get("last_revision_bias")),
           "meta_at_bound": one("SELECT COUNT(*) FROM phase6c_meta_control_parameters WHERE current_value<=min_value+1e-9 OR current_value>=max_value-1e-9", 0),
           "stable": one("SELECT COUNT(*) FROM context_hypotheses WHERE role>='stable_' AND role<'stable`'", 0),
           "adj_applied": one("SELECT state_change_allowed FROM phase6b_plasticity_adjustments ORDER BY id DESC LIMIT 1", "")}
    w.writerow(row); out.flush()
    if i % 100 == 0:
        print(f"{label} cycle {i}: {row['state']} DA={row['dopamine']} NA={row['noradrenaline']} plast={row['plasticity']} stable={row['stable']} {row['seconds']}s", flush=True)
out.close()
tag = c.execute("SELECT COUNT(*), SUM(n>=3) FROM (SELECT source_id, COUNT(DISTINCT cycle_index) n FROM phase7d_consolidation_survivors "
                "WHERE id>? AND reinforced=1 AND source_table='context_hypotheses' GROUP BY source_id)", (start["phase7d_consolidation_survivors"],)).fetchone()
# Right-censoring: a trace needs a median of 62 and at most about 240 cycles
# from its first tag to its third survival (measured on the production state,
# 16 November 2026). Only traces first tagged at least CAPTURE_WINDOW cycles
# before the end of the run count for the capture rate.
CAPTURE_WINDOW = 250
tag_m = c.execute("SELECT COUNT(*), SUM(n>=3) FROM (SELECT source_id, MIN(cycle_index) f, COUNT(DISTINCT cycle_index) n "
                  "FROM phase7d_consolidation_survivors WHERE id>? AND reinforced=1 AND source_table='context_hypotheses' "
                  "GROUP BY source_id) WHERE f <= (SELECT MAX(cycle_index) FROM phase7d_consolidation_survivors) - ?",
                  (start["phase7d_consolidation_survivors"], CAPTURE_WINDOW)).fetchone()
summary = {"label": label, "run_seed": run_seed, "cycles": cycles, "exceptions": exc, "diag_findings": findings, "elapsed_s": round(time.time() - t0),
           "stable_start": stable0, "stable_end": one("SELECT COUNT(*) FROM context_hypotheses WHERE role>='stable_' AND role<'stable`'", 0),
           "tagged": tag[0], "captured": tag[1] or 0,
           "tagged_uncensored": tag_m[0], "captured_uncensored": tag_m[1] or 0, "capture_window": CAPTURE_WINDOW,
           "regulation_events": one(f"SELECT COUNT(*) FROM phase6c_regulation_events WHERE id>{start['phase6c_regulation_events']}", 0),
           "saturation_events": one(f"SELECT COUNT(*) FROM phase6d_saturation_events WHERE id>{start['phase6d_saturation_events']}", 0),
           "boundary_events": one(f"SELECT COUNT(*) FROM phase7c_boundary_events WHERE id>{start['phase7c_boundary_events']}", 0),
           "critic_snapshots": one(f"SELECT COUNT(*) FROM phase6b_critic_snapshot WHERE snapshot_id>{start['phase6b_critic_snapshot']}", 0),
           "facts": one("SELECT COUNT(*) FROM facts", 0), "relations": one("SELECT COUNT(*) FROM relations", 0),
           "quick_check": one("PRAGMA quick_check", "")}
json.dump(summary, open(os.path.join(root, "learn_summary.json"), "w"), indent=1)
print(label, "DONE", json.dumps(summary), flush=True)
