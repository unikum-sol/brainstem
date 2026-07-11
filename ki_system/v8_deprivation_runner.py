# -*- coding: utf-8 -*-
"Sensory-Deprivation Runner + CSV-Log + Drift-Report fuer BrainStem."
import os, csv, sqlite3, time
from pathlib import Path

def _tables(con):
    try:
        return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    except Exception:
        return []

def _colset(con, t):
    try:
        return set(c[1] for c in con.execute("PRAGMA table_info(" + t + ")").fetchall())
    except Exception:
        return set()

def _kv(con, t):
    if t not in _tables(con):
        return {}
    cs = _colset(con, t)
    if "key" not in cs or "value" not in cs:
        return {}
    try:
        return dict(con.execute("SELECT key,value FROM " + t).fetchall())
    except Exception:
        return {}

def _find_kv(con, names):
    want = [n.lower() for n in names]
    for t in _tables(con):
        cs = _colset(con, t)
        if "key" in cs and "value" in cs:
            low = {}
            for k, v in _kv(con, t).items():
                low[str(k).lower()] = v
            for w in want:
                if w in low:
                    return low[w]
    return None

def _to_float(x, d=0.0):
    try:
        return float(x)
    except Exception:
        return d

def _first(con, sql):
    try:
        return con.execute(sql).fetchone()
    except Exception:
        return None

def _latest(con, table, col):
    if table not in _tables(con):
        return None
    cs = _colset(con, table)
    if col not in cs:
        return None
    idc = "id" if "id" in cs else "rowid"
    r = _first(con, "SELECT " + col + " FROM " + table + " ORDER BY " + idc + " DESC LIMIT 1")
    return r[0] if r else None

def _recent_col(con, colnames):
    for col in colnames:
        for t in _tables(con):
            if col in _colset(con, t):
                v = _latest(con, t, col)
                if v is not None:
                    return v
    return None

SNAPSHOT_KEYS = ["cycle", "ts",
                 "dopamine", "serotonin", "glutamate", "gaba", "noradrenaline", "acetylcholine",
                 "histamine", "orexin", "bdnf", "adenosine", "endocannabinoid_2ag", "cortisol",
                 "exploration_bias", "plasticity_level", "adaptive_threshold",
                 "survivors", "participated", "weakened", "effectiveness",
                 "reciprocal_gate", "allostatic_load"]

def collect_snapshot(con):
    snap = {}
    for k in SNAPSHOT_KEYS:
        snap[k] = 0.0
    sleep = _kv(con, "phase6a_neuromodulated_sleep_state")
    for k in ("dopamine", "serotonin", "glutamate", "gaba", "noradrenaline",
              "acetylcholine", "histamine", "orexin", "bdnf"):
        snap[k] = _to_float(sleep.get(k, 0.0))
    ade = _kv(con, "phase7a_adenosine_state").get("adenosine_level")
    if ade is None:
        ade = _find_kv(con, ["adenosine_level", "adenosine"])
    snap["adenosine"] = _to_float(ade)
    ecb = _kv(con, "phase7b_endocannabinoid_state").get("endocannabinoid_2ag")
    if ecb is None:
        ecb = _find_kv(con, ["endocannabinoid_2ag", "2ag_current", "two_ag_level"])
    snap["endocannabinoid_2ag"] = _to_float(ecb)
    snap["cortisol"] = _to_float(_kv(con, "cortisol_state").get("cortisol_level"))
    snap["exploration_bias"] = _to_float(_recent_col(con, ["exploration_bias", "last_exploration_bias"]))
    snap["plasticity_level"] = _to_float(_recent_col(con, ["plasticity_level", "last_plasticity_level"]))
    snap["adaptive_threshold"] = _to_float(_latest(con, "phase7d_slow_wave_cycles", "adaptive_threshold_avg"))
    snap["survivors"] = _to_float(_latest(con, "phase7d_slow_wave_cycles", "candidates_survived"))
    snap["participated"] = _to_float(_latest(con, "phase7d_slow_wave_cycles", "candidates_participated"))
    snap["weakened"] = _to_float(_latest(con, "phase7d_slow_wave_cycles", "weakened"))
    snap["effectiveness"] = _to_float(_latest(con, "phase6b_effectiveness_events", "effectiveness_score"))
    snap["reciprocal_gate"] = _to_float(_latest(con, "phase7e_histamine_cycles", "reciprocal_gate"))
    al = _latest(con, "stability_watch_events", "allostatic_load")
    if al is None:
        al = _kv(con, "cortisol_state").get("last_allostatic_load")
    snap["allostatic_load"] = _to_float(al)
    return snap

def _resolve_db(mem_or_con):
    if isinstance(mem_or_con, sqlite3.Connection):
        return mem_or_con, False
    for a in ("db", "con", "conn", "connection", "memory"):
        inner = getattr(mem_or_con, a, None)
        if isinstance(inner, sqlite3.Connection):
            return inner, False
    return sqlite3.connect("ki_memory.sqlite3", timeout=30.0), True

def run_deprivation(mem_or_con, cycle_fn, cycles=None, stop_flag=None, on_cycle=None, csv_path=None, set_flag_fn=None):
    con, should_close = _resolve_db(mem_or_con)
    if csv_path is None:
        csv_path = "drift_log_" + time.strftime("%Y%m%d_%H%M%S") + ".csv"
    rows = []
    f = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=SNAPSHOT_KEYS)
    writer.writeheader()
    if set_flag_fn is not None:
        try: set_flag_fn(True)
        except Exception: pass
    n = 0
    try:
        while True:
            if stop_flag is not None and stop_flag():
                break
            if cycles is not None and n >= cycles:
                break
            cycle_fn()
            n += 1
            snap = collect_snapshot(con)
            snap["cycle"] = n
            snap["ts"] = int(time.time())
            writer.writerow(snap)
            f.flush()
            rows.append(snap)
            if on_cycle is not None:
                try: on_cycle(n, snap)
                except Exception: pass
    finally:
        if set_flag_fn is not None:
            try: set_flag_fn(False)
            except Exception: pass
        try: f.close()
        except Exception: pass
        if should_close:
            try: con.close()
            except Exception: pass
    return {"cycles": n, "csv": csv_path, "rows": rows}

def compute_drift(rows):
    out = {}
    if not rows:
        return out, "keine_daten"
    keys = [k for k in SNAPSHOT_KEYS if k not in ("cycle", "ts")]
    count_signals = ("survivors", "participated", "weakened")
    any_div = False
    any_conv = False
    n = len(rows)
    for k in keys:
        vals = [_to_float(r.get(k, 0.0)) for r in rows]
        if not vals:
            continue
        first = vals[0]; last = vals[-1]
        delta = last - first
        minv = min(vals); maxv = max(vals); span = maxv - minv
        dpc = delta / max(1, n - 1)
        if k in count_signals:
            mean = sum(vals) / len(vals)
            base = mean if mean > 1e-6 else 1.0
            rel_delta = delta / base
            rel_span = span / base
            if rel_span < 0.5 and abs(rel_delta) < 0.25:
                verdict = "stabil"
            elif abs(rel_delta) > 0.5:
                verdict = "DIVERGIERT"
            else:
                verdict = "konvergiert"
        else:
            if span < 0.03:
                verdict = "stabil"
            elif (maxv >= 0.98 or minv <= 0.02) and abs(delta) > 0.1:
                verdict = "DIVERGIERT"
            elif abs(delta) > 0.05:
                verdict = "konvergiert"
            else:
                verdict = "stabil"
        if verdict == "DIVERGIERT": any_div = True
        elif verdict == "konvergiert": any_conv = True
        out[k] = {"first": round(first, 4), "last": round(last, 4), "delta": round(delta, 4),
                  "drift_per_cycle": round(dpc, 5), "min": round(minv, 4), "max": round(maxv, 4),
                  "span": round(span, 4), "verdict": verdict}
    overall = "DIVERGENZ-WARNUNG" if any_div else ("konvergenz" if any_conv else "kein_drift")
    return out, overall

def write_report(rows, csv_path):
    drift, overall = compute_drift(rows)
    lines = []
    lines.append("=" * 60)
    lines.append("DRIFT-REPORT  (Zyklen: %d)" % len(rows))
    lines.append("=" * 60)
    lines.append("%-20s %8s %8s %8s %8s  %s" % ("Signal", "first", "last", "delta", "span", "Urteil"))
    for k, d in drift.items():
        lines.append("%-20s %8.4f %8.4f %8.4f %8.4f  %s" % (k, d["first"], d["last"], d["delta"], d["span"], d["verdict"]))
    lines.append("-" * 60)
    lines.append("GESAMT: " + overall)
    lines.append("=" * 60)
    text = "\n".join(lines)
    try:
        with open(csv_path, "a", encoding="utf-8") as f:
            f.write("\n")
            for ln in lines:
                f.write("# " + ln + "\n")
    except Exception:
        pass
    return text, overall

def _selftest():
    print("SELFTEST compute_drift")
    div = []
    for i in range(20):
        eb = 0.80 + (0.20 * i / 19.0)
        div.append({"cycle": i + 1, "ts": 0, "exploration_bias": eb, "adenosine": 0.50})
    d, ov = compute_drift(div)
    a = "PASS" if d["exploration_bias"]["verdict"] == "DIVERGIERT" else "FAIL"
    b = "PASS" if d["adenosine"]["verdict"] == "stabil" else "FAIL"
    c = "PASS" if ov == "DIVERGENZ-WARNUNG" else "FAIL"
    print("  exploration DIVERGIERT:", a)
    print("  adenosine stabil:", b)
    print("  overall DIVERGENZ-WARNUNG:", c)
    stable = []
    for i in range(20):
        stable.append({"cycle": i + 1, "ts": 0, "adenosine": 0.50 + (0.01 if i % 2 else -0.01), "orexin": 0.70})
    d2, ov2 = compute_drift(stable)
    e = "PASS" if ov2 == "kein_drift" else "FAIL(" + ov2 + ")"
    print("  stable overall kein_drift:", e)
    print("OVERALL:", "ALL PASS" if all(x == "PASS" for x in (a, b, c, e)) else "SOME FAILED")

if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
