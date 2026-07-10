# -*- coding: utf-8 -*-
"""Kompletter Systemtest BrainStem: 12 Botenstoffe, 7d/7e/7f/7g, Cortisol, Leseabdeckung, Registry, Safety.
Nur lesend + Standalone-Beobachter. Aendert kein Lernen."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
con = sqlite3.connect(str(ROOT / "ki_memory.sqlite3")); con.row_factory = sqlite3.Row

def one(sql):
    try: return con.execute(sql).fetchone()
    except Exception as e: return ("ERR", str(e))
def tables():
    return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
def colset(t):
    try: return set(c[1] for c in con.execute("PRAGMA table_info(" + t + ")").fetchall())
    except Exception: return set()
def find_kv(keynames):
    want = [k.lower() for k in keynames]
    for t in tables():
        cs = colset(t)
        if "key" in cs and "value" in cs:
            try: d = dict(con.execute("SELECT key,value FROM " + t + "").fetchall())
            except Exception: continue
            low = {}
            for k, v in d.items(): low[str(k).lower()] = v
            for w in want:
                if w in low: return low[w]
    return None

print("=" * 58)
print("BRAINSTEM SYSTEMTEST (komplett, 12 Botenstoffe)")
print("=" * 58)

from ki_system.autonomous import AutonomousLoop as L
cyc = getattr(L.cycle, "__module__", "") or ""
print("\n[1] KETTE / KOMPASS")
print("  cycle-Spitze :", cyc)
print("  7g/7f/7e/7d  :", getattr(L,"phase7g_bdnf_growth_consolidation_release",False),
      getattr(L,"phase7f_orexin_wake_endurance_release",False),
      getattr(L,"phase7e_histamine_wake_arousal_release",False),
      getattr(L,"phase7d_slow_wave_sleep_substructure_release",False))
print("  fact_promotion:", getattr(L,"fact_promotion",None), "| no_blacklists:", getattr(L,"no_word_blacklists",None))

print("\n[2] 7d SLOW-WAVE")
for k in ("cycle_count","total_slow_wave_sleeps","total_reinforced","total_weakened","phase_version"):
    r = one("SELECT value FROM phase7d_slow_wave_params WHERE key='" + k + "' UNION ALL SELECT value FROM phase7d_state WHERE key='" + k + "'")
    print("  " + k + ":", r[0] if r else None)
r = one("SELECT COUNT(*),AVG(candidates_survived),AVG(candidates_participated),AVG(weakened),AVG(adaptive_threshold_avg) FROM phase7d_slow_wave_cycles WHERE reason='self_regulating_slow_wave_sleep'")
sel_sharp = False
if r and r[0]:
    print("  v2-Zyklen: %d | avg surv/part/weak/thr: %.2f / %.2f / %.2f / %.2f" % (r[0], r[1], r[2], r[3], r[4]))
    sel_sharp = (r[1] < r[2]) and (r[3] > 0)

print("\n[3] 7e HISTAMIN")
from ki_system.v8_phase7e_histamine_wake_arousal_release import run_phase7e_cycle
h = run_phase7e_cycle(con)
print("  regime:", h["regime"], "| hist:", h["histamine_level"], "| ade:", h["adenosine_level"], "| gate:", h["reciprocal_gate"])

print("\n[4] 7f OREXIN")
from ki_system.v8_phase7f_orexin_wake_endurance_release import run_phase7f_cycle
o = run_phase7f_cycle(con)
print("  regime:", o["regime"], "| orexin:", o["orexin_level"], "| unread:", o["unread_fraction"], "| progress:", o["marginal_progress"])

print("\n[5] 7g BDNF")
from ki_system.v8_phase7g_bdnf_growth_consolidation_release import run_phase7g_cycle
g = run_phase7g_cycle(con)
print("  regime:", g["regime"], "| bdnf:", g["bdnf_level"], "| consistency:", g["consolidation_consistency"], "| progress:", g["marginal_progress"], "| activity:", g["activity_level"])

print("\n[6] CORTISOL-WAECHTER")
from ki_system.v8_phase7cort_stability_watch_release import run_stability_watch
c = run_stability_watch(con)
print("  regime:", c["regime"], "| load:", c["allostatic_load"], "| cortisol:", c["cortisol_level"], "| rec:", c["recommended"], "| applied:", c["applied"])

print("\n[7] LESEABDECKUNG")
ch = "chunks" if "chunks" in tables() else next((t for t in tables() if "chunk" in t.lower() and ("text" in colset(t) or "content" in colset(t))), None)
cov = None
if ch:
    total = one("SELECT COUNT(*) FROM " + ch)[0]
    covered = 0
    if "chunk_attention_scores" in tables() and "chunk_id" in colset("chunk_attention_scores"):
        covered = one("SELECT COUNT(DISTINCT chunk_id) FROM chunk_attention_scores")[0]
    cov = 100.0 * covered / total if total else 0.0
    print("  Chunk-Tabelle:", ch, "| gesamt:", total, "| gelesen:", covered, "(%.1f%%)" % cov)
    for t in tables():
        if "reading" in t.lower() and "queue" in t.lower() and "status" in colset(t):
            p = one("SELECT COUNT(*) FROM " + t + " WHERE LOWER(COALESCE(status,''))='pending'")
            print("  " + t + " pending:", p[0] if p else None)
else:
    print("  (keine Chunk-Tabelle gefunden)")

print("\n[8] BOTENSTOFFE (#1-#12)")
present = {}
core = ("dopamine","serotonin","noradrenaline","acetylcholine","glutamate","gaba","histamine","orexin","bdnf")
try: nm = dict(con.execute("SELECT key,value FROM phase6a_neuromodulated_sleep_state").fetchall())
except Exception: nm = {}
for k in core:
    v = nm.get(k); present[k] = v is not None
    print("  %-16s: %s" % (k, v if v is not None else "-"))
ade = find_kv(["adenosine_level","adenosine"]); present["adenosine"] = ade is not None
print("  %-16s: %s" % ("adenosine", ade if ade is not None else "-"))
twoag = find_kv(["endocannabinoid_2ag","2ag_current","two_ag_level"])
aea = find_kv(["endocannabinoid_anandamide","anandamide_level","anandamide"])
ecb = (twoag is not None) or (aea is not None); present["endocannabinoid"] = ecb
if ecb: print("  %-16s: 2AG=%s, AEA=%s" % ("endocannabinoid", twoag, aea))
else: print("  %-16s: -" % "endocannabinoid")

print("\n[9] SAFETY")
safe = []
for t in ("facts","relations","questions"):
    r = one("SELECT COUNT(*) FROM " + t)
    safe.append(r[0] if isinstance(r[0], int) else -1)
print("  facts/relations/questions:", safe)
safe_ok = safe == [0,0,0]

print("\n[10] REGISTRY")
try:
    import ki_system.phase_registry as PR
    exp = getattr(PR,"EXPECTED_TOP_MODULE",None)
    last = PR.LOAD_ORDER[-1]["label"] if getattr(PR,"LOAD_ORDER",None) else None
    print("  Eintraege:", len(PR.LOAD_ORDER), "| letzter:", last, "| EXPECTED_TOP:", exp)
    print("  cycle auf EXPECTED_TOP:", cyc.endswith(exp or "___"))
except Exception as e:
    print("  (registry nicht lesbar:", e, ")")

con.close()

print("\n" + "=" * 58)
print("FAZIT")
print("=" * 58)
missing = [k for k, v in present.items() if not v]
all12 = len(missing) == 0
def mark(b): return "OK" if b else "X"
print("  [%s] 7g ist Ketten-Spitze" % mark("phase7g" in cyc))
print("  [%s] Kompass-Flags gesetzt" % mark(getattr(L,"fact_promotion",None)=="disabled"))
print("  [%s] Uebergangssperre 0/0/0" % mark(safe_ok))
print("  [%s] Cortisol beobachtet (applied=False)" % mark(c["applied"]==False))
print("  [%s] Selektion scharf (surv<part & weak>0)" % mark(sel_sharp))
print("  [%s] Alle 12 Botenstoffe sichtbar%s" % (mark(all12), "" if all12 else " (fehlt: " + ",".join(missing) + ")"))
if cov is not None:
    print("  [i] Leseabdeckung: %.1f%%" % cov)
print("=" * 58)