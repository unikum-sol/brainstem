# -*- coding: utf-8 -*-
import csv, glob, sys

files = sorted(glob.glob("drift_log_*.csv"))
if not files:
    print("Keine drift_log_*.csv gefunden."); sys.exit(0)
path = files[-1]
print("=" * 60)
print("2-AG VOLLANALYSE  |  Datei:", path)
print("=" * 60)

rows = []
with open(path, encoding="utf-8") as f:
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        rows.append(line)
rdr = csv.DictReader(rows)

# alle numerischen Spalten einsammeln
cols = ["glutamate", "gaba", "adenosine", "endocannabinoid_2ag", "orexin", "histamine",
        "exploration_bias", "plasticity_level", "adaptive_threshold", "effectiveness",
        "reciprocal_gate", "allostatic_load", "cortisol", "noradrenaline", "dopamine"]
data = {c: [] for c in cols}
ok = 0
for r in rdr:
    try:
        vals = {c: float(r[c]) for c in cols if c in r and r[c] not in (None, "")}
        if "endocannabinoid_2ag" not in vals:
            continue
        for c in cols:
            data[c].append(vals.get(c, 0.0))
        ok += 1
    except Exception:
        pass
n = ok
print("Datenzeilen:", n)
if n < 5:
    sys.exit(0)

ecb = data["endocannabinoid_2ag"]

def pearson(a, b):
    m = len(a)
    ma = sum(a) / m; mb = sum(b) / m
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(m))
    da = (sum((x - ma) ** 2 for x in a)) ** 0.5
    db = (sum((x - mb) ** 2 for x in b)) ** 0.5
    return num / (da * db) if da > 0 and db > 0 else 0.0

def lag(sig):
    # Korrelation 2AG[t] vs sig[t-1]  (fuehrt sig dem 2AG voraus?)
    return pearson(ecb[1:], sig[:-1])

print("\n[A] Korrelationen mit 2AG  (gleichzeitig | verzoegert sig[t-1]->2AG[t])")
results = []
for c in cols:
    if c == "endocannabinoid_2ag":
        continue
    c0 = pearson(ecb, data[c])
    cl = lag(data[c])
    results.append((max(abs(c0), abs(cl)), c, c0, cl))
results.sort(reverse=True)
for strength, c, c0, cl in results:
    marker = " <==" if strength > 0.25 else ""
    print("  %-18s  gleich %+.3f | lag %+.3f%s" % (c, c0, cl, marker))

# Spikes analysieren
em = sum(ecb) / n
esd = (sum((x - em) ** 2 for x in ecb) / n) ** 0.5
thr = max(0.1, em + esd)
spikes = [i for i in range(n) if ecb[i] > thr]
print("\n[B] 2AG-Spikes (>%.3f): %d von %d Zyklen (%.1f%%)" % (thr, len(spikes), n, 100.0 * len(spikes) / n))

# Was ist an Spikes anders? Vergleiche Mittelwerte an Spikes vs Nicht-Spikes fuer Top-Treiber
def mean_at(idxs, sig):
    return sum(sig[i] for i in idxs) / len(idxs) if idxs else 0.0
nonspikes = [i for i in range(n) if i not in set(spikes)]
print("\n[C] Mittelwerte an Spike- vs Nicht-Spike-Zyklen (Top-Treiber):")
for strength, c, c0, cl in results[:6]:
    ms = mean_at(spikes, data[c]); mn = mean_at(nonspikes, data[c])
    print("  %-18s  Spike %.4f | sonst %.4f | Diff %+.4f" % (c, ms, mn, ms - mn))

# Adenosin-Override-Hypothese: feuert 2AG wenn adenosine hoch?
ade = data["adenosine"]
ade_hi = [i for i in spikes if ade[i] >= sum(ade)/n]
print("\n[D] Von %d Spikes bei ueberdurchschnittlichem Adenosin: %d (%.0f%%)" % (
    len(spikes), len(ade_hi), 100.0*len(ade_hi)/len(spikes) if spikes else 0))

print("\n" + "=" * 60)
print("DEUTUNG")
print("=" * 60)
top = results[0]
print("  Staerkster Treiber: %s (|r|=%.3f)" % (top[1], top[0]))
glu_lead = [r for r in results if r[1] == "glutamate"][0]
print("  Glutamat-Lead (sig[t-1]->2AG): %+.3f" % glu_lead[3])
if top[0] > 0.25:
    print("  -> 2AG reagiert primaer auf: %s. Retrograde Bremse plausibel (FEATURE)." % top[1])
else:
    print("  -> kein einzelner starker Treiber; 2AG wird von mehreren kleinen Quellen getriggert.")
print("=" * 60)
