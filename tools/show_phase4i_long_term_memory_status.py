
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sqlite3, os

p = ROOT / "ki_memory.sqlite3"
con = sqlite3.connect(str(p))
cur = con.cursor()

def ex(t):
    return cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None

def count(t):
    return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] if ex(t) else "missing"

def cols(t):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()] if ex(t) else []

print("db:", p)
for t in ["facts", "relations", "questions"]:
    print(t, count(t))
for t in [
    "context_hypotheses", "context_pattern_memory", "hypothesis_stability_scores",
    "long_term_pattern_memory", "pattern_stability_history", "role_confusion_memory",
    "neuromodulator_pattern_profiles", "long_term_consolidation_state",
    "neuromodulator_learning_state", "hypothesis_learning_updates", "sleep_consolidation_decisions",
]:
    print(t, count(t))

for t in ["long_term_pattern_memory", "role_confusion_memory", "neuromodulator_pattern_profiles", "long_term_consolidation_state"]:
    print(t+"_columns:", cols(t))

if ex("long_term_pattern_memory"):
    print("long_term_top:", cur.execute("SELECT pattern_key, dominant_role, observations, ROUND(avg_confidence,3), ROUND(avg_uncertainty,3), ROUND(stability,3), last_decision FROM long_term_pattern_memory ORDER BY observations DESC LIMIT 10").fetchall())
if ex("neuromodulator_pattern_profiles"):
    print("neuro_profiles:", cur.execute("SELECT role, observations, ROUND(avg_dopamine,3), ROUND(avg_gaba,3), ROUND(avg_confidence,3), ROUND(avg_uncertainty,3) FROM neuromodulator_pattern_profiles ORDER BY observations DESC LIMIT 10").fetchall())
if ex("role_confusion_memory"):
    print("role_confusions:", cur.execute("SELECT from_role, to_role, count, ROUND(avg_revision_pressure,3), ROUND(avg_self_score,3), status FROM role_confusion_memory ORDER BY count DESC LIMIT 10").fetchall())
if ex("long_term_consolidation_state"):
    print("long_term_state:", cur.execute("SELECT key,value FROM long_term_consolidation_state ORDER BY key").fetchall())

print("facts_rel_questions:", {t: count(t) for t in ["facts", "relations", "questions"]})
