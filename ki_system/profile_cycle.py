import sys, time
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import sqlite3
db_path = _ROOT / "ki_memory.sqlite3"

def timed(label, fn):
    t0 = time.perf_counter()
    try:
        fn()
        ok = "ok"
    except Exception as e:
        ok = "ERR: " + str(e)[:80]
    dt = time.perf_counter() - t0
    return (label, dt, ok)

results = []
con = sqlite3.connect(str(db_path))
con.row_factory = sqlite3.Row

def q_count():
    con.execute("SELECT COUNT(*) FROM context_hypotheses").fetchone()
def q_ch_sort():
    con.execute("SELECT id FROM context_hypotheses ORDER BY phase6a_replay_weight DESC LIMIT 400").fetchall()
def q_5g_sort():
    con.execute("SELECT id FROM phase5g_experiment_outcomes ORDER BY outcome_score ASC LIMIT 540").fetchall()
results.append(timed("query: COUNT context_hypotheses", q_count))
results.append(timed("query: ORDER BY replay_weight LIMIT 400", q_ch_sort))
results.append(timed("query: ORDER BY outcome_score LIMIT 540", q_5g_sort))
con.close()

def make_phase_runner(modname, fnname):
    def runner():
        m = __import__("ki_system." + modname, fromlist=[fnname])
        fn = getattr(m, fnname, None)
        if fn is None:
            raise RuntimeError("no " + fnname)
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        try:
            fn(c)
        finally:
            c.close()
    return runner

phases = [
    ("6a sleep_replay", "v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release", "sleep_replay_and_meta_plasticity"),
    ("6b run_cycle", "v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "run_phase6b_cycle"),
    ("6c run_cycle", "v8_phase6c_bias_persistence_and_self_regulating_meta_release", "run_phase6c_cycle"),
    ("6d run_cycle", "v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "run_phase6d_cycle"),
    ("7a run_cycle", "v8_phase7a_adenosine_homeostat_release", "run_phase7a_cycle"),
    ("7b run_cycle", "v8_phase7b_endocannabinoid_retrograde_gain_control_release", "run_phase7b_cycle"),
]
for label, mod, fn in phases:
    results.append(timed(label, make_phase_runner(mod, fn)))

results.sort(key=lambda x: x[1], reverse=True)
print("=== CYCLE PROFILE (sorted by time) ===")
total = 0.0
for label, dt, ok in results:
    total += dt
    print("  %8.3fs  %-45s  %s" % (dt, label, ok))
print("  --------")
print("  %8.3fs  TOTAL (note: some phases re-run wake path internally)" % total)
