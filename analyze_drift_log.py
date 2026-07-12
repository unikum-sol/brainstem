# -*- coding: utf-8 -*-
import csv, glob, math, sys

# neueste drift_log CSV finden
files = sorted(glob.glob("drift_log_*.csv"))
if not files:
    print("Keine drift_log_*.csv gefunden."); sys.exit(0)
path = files[-1]
print("Analysiere:", path)

rows = []
with open(path, encoding="utf-8") as f:
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        rows.append(line)
rdr = csv.DictReader(rows)
data = []
for r in rdr:
    try:
        data.append({k: float(r[k]) for k in ("glutamate", "endocannabinoid_2ag", "orexin")})
    except Exception:
        pass

n = len(data)
print("Datenzeilen:", n)
if n < 3:
    sys.exit(0)

glu = [d["glutamate"] for d in data]
ecb = [d["endocannabinoid_2ag"] for d in data]
orx = [d["orexin"] for d in data]

def stats(v):
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
    return min(v), max(v), m, sd

gmin, gmax, gm, gsd = stats(glu)
emin, emax, em, esd = stats(ecb)
print("\nGlutamat  min/max/mean: %.4f / %.4f / %.4f" % (gmin, gmax, gm))
print("2AG       min/max/mean: %.4f / %.4f / %.4f  (std %.4f)" % (emin, emax, em, esd))

# 2AG-Spikes
thr = max(0.1, em + esd)
spikes = [i for i in range(n) if ecb[i] > thr]
print("\n2AG-Spikes (>%.3f): %d" % (thr, len(spikes)))
if spikes:
    avg_mag = sum(ecb[i] for i in spikes) / len(spikes)
    print("  durchschnittliche Spike-Hoehe: %.4f" % avg_mag)
    # Glutamat am Spike vs. davor
    ups = 0
    for i in spikes:
        if i >= 1 and glu[i] >= glu[i - 1]:
            ups += 1
    print("  Spikes, bei denen Glutamat >= Vorwert: %d / %d (%.0f%%)" % (ups, len(spikes), 100.0 * ups / len(spikes)))

def pearson(a, b):
    ma = sum(a) / len(a); mb = sum(b) / len(b)
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(len(a)))
    da = (sum((x - ma) ** 2 for x in a)) ** 0.5
    db = (sum((x - mb) ** 2 for x in b)) ** 0.5
    return num / (da * db) if da > 0 and db > 0 else 0.0

corr0 = pearson(ecb, glu)
corr_lag = pearson(ecb[1:], glu[:-1])  # Glutamat[t-1] -> 2AG[t]
print("\nKorrelation 2AG[t] vs Glutamat[t]     : %.3f" % corr0)
print("Korrelation 2AG[t] vs Glutamat[t-1]   : %.3f  (Glutamat als Ausloeser?)" % corr_lag)
print("Glutamat max: %.4f  (naehert sich Obergrenze 0.72? %s)" % (gmax, "JA" if gmax > 0.72 else "nein"))

# Orexin-Verlauf
up = sum(1 for i in range(1, n) if orx[i] > orx[i - 1])
down = sum(1 for i in range(1, n) if orx[i] < orx[i - 1])
print("\nOrexin  first %.4f -> last %.4f | Schritte hoch/runter: %d / %d" % (orx[0], orx[-1], up, down))
print("  -> %s" % ("monotone Selbst-Daempfung (gesund)" if down > up * 3 else "oszilliert/gemischt"))

print("\n=== VERDIKT ===")
if abs(corr0) > 0.3 or abs(corr_lag) > 0.3:
    print("2AG korreliert mit Glutamat -> retrograde Bremse reagiert auf Erregung (FEATURE)")
else:
    print("2AG-Spikes ohne klaren Glutamat-Bezug -> im Code tracen (moeglicher Trigger woanders)")