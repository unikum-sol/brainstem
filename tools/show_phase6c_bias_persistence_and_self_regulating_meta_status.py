import sqlite3

def ex(cur, table):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def count(cur, table):
    if not ex(cur, table):
        return "missing"
    return cur.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]

con = sqlite3.connect("ki_memory.sqlite3")
cur = con.cursor()
print("db: ki_memory.sqlite3")

phase6c_tables = [
    "phase6c_state",
    "phase6c_meta_control_parameters",
    "phase6c_target_bias_state",
    "phase6c_regulation_events",
]
phase6b_tables = [
    "phase6b_state",
    "phase6b_anchor_pool",
    "phase6b_critic_snapshot",
    "phase6b_effectiveness_events",
    "phase6b_plasticity_adjustments",
    "phase6b_distilled_knowledge",
    "phase6b_l2m_metrics",
]
phase6a_tables = [
    "phase6a_sleep_replay_cycles",
    "phase6a_meta_plasticity_state",
    "phase6a_neuromodulated_sleep_state",
    "phase6a_plasticity_adjustments",
]

print("--- counts phase6c ---")
for t in phase6c_tables:
    print(t, count(cur, t))
print("--- counts phase6b ---")
for t in phase6b_tables:
    print(t, count(cur, t))
print("--- counts phase6a ---")
for t in phase6a_tables:
    print(t, count(cur, t))

if ex(cur, "phase6c_state"):
    print("phase6c_state:", cur.execute(
        "SELECT key,value FROM phase6c_state ORDER BY key"
    ).fetchall())

if ex(cur, "phase6c_meta_control_parameters"):
    print("meta_control_parameters:")
    for row in cur.execute(
        "SELECT parameter_key, ROUND(current_value,4), ROUND(default_value,4), "
        " ROUND(min_value,4), ROUND(max_value,4), driver_botenstoff, driver_metric, "
        " updated_at FROM phase6c_meta_control_parameters "
        "ORDER BY parameter_key"
    ).fetchall():
        print("  ", row)

if ex(cur, "phase6c_target_bias_state"):
    print("target_bias_state:", cur.execute(
        "SELECT key, ROUND(CAST(value AS REAL),4) FROM phase6c_target_bias_state ORDER BY key"
    ).fetchall())

if ex(cur, "phase6c_regulation_events"):
    print("regulation_events_recent:")
    for row in cur.execute(
        "SELECT cycle_index, parameter_key, ROUND(pre_value,4), ROUND(post_value,4), "
        " ROUND(delta,4), driver_botenstoff, driver_metric, ROUND(driver_value,4), reason "
        "FROM phase6c_regulation_events ORDER BY id DESC LIMIT 10"
    ).fetchall():
        print("  ", row)

if ex(cur, "phase6b_plasticity_adjustments"):
    print("latest_phase6b_adjustment:", cur.execute(
        "SELECT cycle_index, adjustment_type, ROUND(pre_plasticity_level,3), "
        " ROUND(post_plasticity_level,3), ROUND(pre_exploration_bias,3), "
        " ROUND(post_exploration_bias,3), critic_gate_result "
        "FROM phase6b_plasticity_adjustments ORDER BY id DESC LIMIT 1"
    ).fetchone())

print("safety_facts_rel_questions:", {t: count(cur, t) for t in ["facts","relations","questions"]})

con.close()
