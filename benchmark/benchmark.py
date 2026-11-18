"""BrainStem benchmark: several run seeds per variant, criteria fixed in advance.

Learning is reproducible (learning_clock.py), so one run seed is one exact
sample; variance between runs comes from the run seed alone. A comparison
therefore uses several seeds per variant and the same seeds for both
(common random numbers), reports every seed, and judges paired differences
with intervals instead of single runs (Henderson et al. 2018; Bouthillier et
al. 2021; Pineau et al. 2021). See PROTOCOL.md.

Commands
  run      python benchmark.py run --snapshot DB --code PROJECT --label A
                                   --out DIR [--seeds 0,1,2,3,4] [--cycles 1000]
                                   [--parallel 2] [--keep-db]
  compare  python benchmark.py compare --out DIR --a A --b B [--margin 0.05]
  report   python benchmark.py report --out DIR --a A
  branch   python benchmark.py branch --out DIR --label A --arm fail|sham --k K
                                   [--checkpoint 500] [--cycles 300] [--seeds ...]
  k7       python benchmark.py k7 --out DIR --label A

K7 since 17 November 2026 (PROTOCOL.md, amendment 1): a responsiveness probe.
The main runs of a variant save a checkpoint (run --checkpoint-at 500); a
fail branch and a sham branch continue from it with injected experiment
outcomes, and the unperturbed main run is the control arm.

PROJECT is a folder that contains ki_system/ (for example the BrainStem
project folder or a code backup). DIR collects one folder per label and seed
with the per-cycle metrics, the run summary and a manifest.
"""
import argparse, csv, hashlib, json, math, os, platform, random, shutil, sqlite3
import statistics as st, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
BOOTSTRAP_SAMPLES = 10000

# ---------------------------------------------------------------- criteria
# K1 to K9 as pre-registered on 12 November 2026 (calibration criteria),
# K5 with the 250-cycle capture window of 16 November 2026.
CRITERIA = {
    "K1": "mean reward prediction error below 0.02 in wake and in sleep",
    "K2": "phasic dopamine at 0 or 1 in under 2 % of cycles",
    "K3": "noradrenaline sleep/wake at most 0.5 and acetylcholine sleep/wake at most 0.6",
    "K4": "no meta parameter at a bound",
    "K5": "capture rate of tagged traces at least 0.85 (runs of 1,000 cycles or more)",
    "K6": "graduations per 1,000 cycles (compared between variants, not judged alone)",
    "K7": "learning-rate spread above 0.01, values within [0.05, 0.95] (legacy, information only since 17 November 2026; see k7)",
    "K8": "no neuromodulator at 0 or 1 in 5 % of cycles or more",
    "K9": "no exceptions and no diagnostic findings",
}
# Growth and quality measures compared between variants.
OUTCOMES = ["stable_gain", "graduations_per_1000", "capture_rate", "facts", "relations"]


def _vals(rows, key, state=None):
    out = []
    for r in rows:
        if state and r.get("state") != state:
            continue
        try:
            out.append(float(r[key]))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def _mean(v):
    return st.mean(v) if v else float("nan")


def evaluate(run_dir):
    """Numeric measures and criterion results of one finished run."""
    rows = list(csv.DictReader(open(os.path.join(run_dir, "learn_metrics.csv"), encoding="utf-8")))
    s = json.load(open(os.path.join(run_dir, "learn_summary.json"), encoding="utf-8"))
    n = len(rows)
    m = {"cycles": n, "run_seed": s.get("run_seed")}
    m["rpe_wake"], m["rpe_sleep"] = _mean(_vals(rows, "rpe", "wake")), _mean(_vals(rows, "rpe", "sleep"))
    dp = _vals(rows, "dopamine_phasic")
    m["da_phasic_at_bound"] = sum(1 for x in dp if x <= 0.02 or x >= 0.98) / max(1, len(dp))
    naw, nas = _mean(_vals(rows, "noradrenaline", "wake")), _mean(_vals(rows, "noradrenaline", "sleep"))
    acw, acs = _mean(_vals(rows, "acetylcholine", "wake")), _mean(_vals(rows, "acetylcholine", "sleep"))
    m["na_ratio"] = nas / naw if naw else float("nan")
    m["ach_ratio"] = acs / acw if acw else float("nan")
    m["meta_at_bound"] = max(_vals(rows, "meta_at_bound") or [0])
    m["capture_rate"] = (s["captured_uncensored"] / s["tagged_uncensored"]) if s.get("tagged_uncensored") else float("nan")
    m["stable_gain"] = s["stable_end"] - s["stable_start"]
    m["graduations_per_1000"] = m["stable_gain"] * 1000.0 / max(1, n)
    pl = _vals(rows, "plasticity")
    m["plasticity_sd"] = st.pstdev(pl) if len(pl) > 1 else 0.0
    m["plasticity_min"], m["plasticity_max"] = (min(pl), max(pl)) if pl else (float("nan"), float("nan"))
    worst = 0.0
    for k in ("dopamine", "serotonin", "noradrenaline", "acetylcholine", "glutamate", "gaba",
              "histamine", "orexin", "bdnf", "adenosine"):
        v = _vals(rows, k)
        if v:
            worst = max(worst, sum(1 for x in v if x <= 0.02 or x >= 0.98) / len(v))
    m["worst_modulator_at_bound"] = worst
    m["exceptions"], m["diag_findings"] = s["exceptions"], s["diag_findings"]
    m["facts"], m["relations"] = s.get("facts"), s.get("relations")
    m["quick_check"] = s.get("quick_check")
    for key in ("stable_lost", "facts_retracted", "revisions", "unsourced_facts", "unsourced_relations"):
        m[key] = s.get(key)
    eta = _vals(rows, "eta", "wake")
    m["eta_wake_mean"] = _mean(eta) if eta else float("nan")
    m["wall_median_s"] = st.median(_vals(rows, "seconds")) if rows else float("nan")
    ok = {
        "K1": abs(m["rpe_wake"]) < 0.02 and abs(m["rpe_sleep"]) < 0.02,
        "K2": m["da_phasic_at_bound"] < 0.02,
        "K3": m["na_ratio"] <= 0.5 and m["ach_ratio"] <= 0.6,
        "K4": m["meta_at_bound"] == 0,
        "K5": (m["capture_rate"] >= 0.85) if n >= 1000 and not math.isnan(m["capture_rate"]) else None,
        "K6": None,
        "K7": m["plasticity_sd"] > 0.01 and m["plasticity_min"] >= 0.05 and m["plasticity_max"] <= 0.95,
        "K8": worst < 0.05,
        "K9": m["exceptions"] == 0 and m["diag_findings"] == 0 and m["quick_check"] == "ok",
    }
    return m, ok


# ---------------------------------------------------------------- running
def _code_hash(code_dir):
    h = hashlib.sha256()
    for name in sorted(os.listdir(code_dir)):
        if name.endswith(".py"):
            h.update(name.encode())
            h.update(open(os.path.join(code_dir, name), "rb").read())
    return h.hexdigest()[:16]


def _snapshot_id(path):
    st_ = os.stat(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(1 << 20))
        f.seek(max(0, st_.st_size - (1 << 20)))
        h.update(f.read(1 << 20))
    return {"path": os.path.abspath(path), "bytes": st_.st_size, "head_tail_sha256": h.hexdigest()[:16]}


def _prepare(run_dir, snapshot, code_dir):
    os.makedirs(run_dir, exist_ok=True)
    target_code = os.path.join(run_dir, "ki_system")
    if os.path.isdir(target_code):
        shutil.rmtree(target_code)
    shutil.copytree(code_dir, target_code, ignore=shutil.ignore_patterns("__pycache__"))
    for suffix in ("", "-wal", "-shm"):
        p = os.path.join(run_dir, "ki_memory.sqlite3" + suffix)
        if os.path.exists(p):
            os.remove(p)
    shutil.copyfile(snapshot, os.path.join(run_dir, "ki_memory.sqlite3"))


def cmd_run(a):
    code_dir = os.path.join(os.path.abspath(a.code), "ki_system")
    if not os.path.isdir(code_dir):
        sys.exit("no ki_system folder in " + a.code)
    seeds = [s.strip() for s in a.seeds.split(",") if s.strip()]
    manifest = {"label": a.label, "seeds": seeds, "cycles": a.cycles, "code": os.path.abspath(a.code),
                "code_sha256": _code_hash(code_dir), "snapshot": _snapshot_id(a.snapshot),
                "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                "machine": platform.platform(), "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    base = os.path.join(a.out, a.label)
    os.makedirs(base, exist_ok=True)
    json.dump(manifest, open(os.path.join(base, "manifest.json"), "w", encoding="utf-8"), indent=1)
    queue = list(seeds); running = []
    while queue or running:
        while queue and len(running) < a.parallel:
            seed = queue.pop(0)
            run_dir = os.path.join(base, "seed_" + seed)
            _prepare(run_dir, a.snapshot, code_dir)
            log = open(os.path.join(run_dir, "run.log"), "w", encoding="utf-8")
            extra = ["checkpoint_at=%d" % a.checkpoint_at] if a.checkpoint_at else []
            proc = subprocess.Popen([sys.executable, os.path.join(HERE, "run_one.py"), run_dir, str(a.cycles),
                                     a.label + "_s" + seed, seed] + extra, stdout=log, stderr=subprocess.STDOUT)
            running.append((seed, run_dir, proc, log))
            print("started", a.label, "seed", seed, flush=True)
        time.sleep(5)
        for item in list(running):
            seed, run_dir, proc, log = item
            if proc.poll() is not None:
                log.close(); running.remove(item)
                print("finished", a.label, "seed", seed, "rc", proc.returncode, flush=True)
                if not a.keep_db:
                    for suffix in ("", "-wal", "-shm"):
                        p = os.path.join(run_dir, "ki_memory.sqlite3" + suffix)
                        if os.path.exists(p):
                            os.remove(p)
    manifest["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(manifest, open(os.path.join(base, "manifest.json"), "w", encoding="utf-8"), indent=1)
    print(report_arm(a.out, a.label))


# ---------------------------------------------------------------- reporting
def _arm(out, label):
    base = os.path.join(out, label)
    res = {}
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if name.startswith("seed_") and os.path.exists(os.path.join(d, "learn_summary.json")):
            res[name[5:]] = evaluate(d)
    return res


def _fmt(x, nd=3):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return "n/a" if math.isnan(x) else ("%." + str(nd) + "f") % x
    return str(x)


def _pass_rule(oks, key):
    vals = [ok[key] for ok in oks if ok[key] is not None]
    if not vals:
        return "n/a"
    need = len(vals) if key == "K9" else max(1, len(vals) - 1)
    return "pass" if sum(vals) >= need else "FAIL"


def report_arm(out, label):
    arm = _arm(out, label)
    if not arm:
        return "no finished runs for " + label
    lines = ["## " + label, "", "| seed | " + " | ".join(CRITERIA) + " | stable gain | facts | relations | capture | wall median |",
             "|---|" + "---|" * (len(CRITERIA) + 5)]
    for seed, (m, ok) in arm.items():
        cells = ["-" if ok[k] is None else ("ok" if ok[k] else "no") for k in CRITERIA]
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (seed, " | ".join(cells), m["stable_gain"], m["facts"],
                                                                m["relations"], _fmt(m["capture_rate"]), _fmt(m["wall_median_s"], 2)))
    oks = [ok for _, ok in arm.values()]
    lines += ["", "Pass rule: a criterion passes when it holds in all seeds but at most one; K9 must hold in every seed.", ""]
    lines.append("| criterion | result |")
    lines.append("|---|---|")
    for k, text in CRITERIA.items():
        lines.append("| %s %s | %s |" % (k, text, _pass_rule(oks, k)))
    lines += ["", "| measure | mean | SD | min | max |", "|---|---|---|---|---|"]
    for key in OUTCOMES:
        v = [m[key] for m, _ in arm.values() if isinstance(m[key], (int, float)) and not math.isnan(m[key])]
        if v:
            lines.append("| %s | %s | %s | %s | %s |" % (key, _fmt(st.mean(v), 2), _fmt(st.stdev(v) if len(v) > 1 else 0.0, 2),
                                                       _fmt(min(v), 2), _fmt(max(v), 2)))
    return "\n".join(lines)


def _bootstrap_ci(diffs, rng):
    means = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(0.025 * BOOTSTRAP_SAMPLES)], means[int(0.975 * BOOTSTRAP_SAMPLES) - 1]


def cmd_compare(a):
    A, B = _arm(a.out, a.a), _arm(a.out, a.b)
    seeds = sorted(set(A) & set(B), key=lambda s: (len(s), s))
    rng = random.Random(20261116)  # fixed: the report itself is reproducible
    lines = [report_arm(a.out, a.a), "", report_arm(a.out, a.b), "",
             "## %s against %s (paired by seed: %s)" % (a.b, a.a, ", ".join(seeds)), "",
             "Non-inferiority margin: %.0f %% of the mean of %s, fixed before the runs." % (100 * a.margin, a.a), "",
             "| measure | mean %s | mean %s | mean difference | bootstrap 95 %% interval | %s better in | verdict |" % (a.a, a.b, a.b),
             "|---|---|---|---|---|---|---|"]
    for key in OUTCOMES:
        pairs = [(A[s][0][key], B[s][0][key]) for s in seeds
                 if all(isinstance(x, (int, float)) and not math.isnan(x) for x in (A[s][0][key], B[s][0][key]))]
        if len(pairs) < 2:
            continue
        d = [b - x for x, b in pairs]
        lo, hi = _bootstrap_ci(d, rng)
        ma = st.mean(x for x, _ in pairs)
        bound = -a.margin * abs(ma)
        verdict = "not worse" if lo > bound else "inconclusive or worse"
        better = sum(1 for x in d if x > 0)
        lines.append("| %s | %s | %s | %s | %s to %s | %d of %d | %s |" % (
            key, _fmt(ma, 2), _fmt(st.mean(b for _, b in pairs), 2), _fmt(st.mean(d), 2), _fmt(lo, 2), _fmt(hi, 2),
            better, len(d), verdict))
    lines += ["", "With five seeds the interval is wide; the verdict rests on the pre-set margin, not on p-values."]
    text = "\n".join(lines)
    path = os.path.join(a.out, "compare_%s_vs_%s.md" % (a.b, a.a))
    open(path, "w", encoding="utf-8").write(text + "\n")
    print(text)
    print("\nwritten:", path)


def cmd_report(a):
    text = report_arm(a.out, a.a)
    open(os.path.join(a.out, "report_%s.md" % a.a), "w", encoding="utf-8").write(text + "\n")
    print(text)


# ---------------------------------------------------------------- K7 probe
def _clear_db(d):
    for suffix in ("", "-wal", "-shm"):
        q = os.path.join(d, "ki_memory.sqlite3" + suffix)
        if os.path.exists(q):
            os.remove(q)


def cmd_branch(a):
    """Continue each seed's checkpoint with a fail or sham probe."""
    seeds = [x.strip() for x in a.seeds.split(",") if x.strip()]
    queue = list(seeds); running = []
    while queue or running:
        while queue and len(running) < a.parallel:
            seed = queue.pop(0)
            src = os.path.join(a.out, a.label, "seed_" + seed)
            ckpt = os.path.join(src, "checkpoint_%d.sqlite3" % a.checkpoint)
            dst = os.path.join(a.out, a.label + "_" + a.arm, "seed_" + seed)
            os.makedirs(dst, exist_ok=True)
            if os.path.isdir(os.path.join(dst, "ki_system")):
                shutil.rmtree(os.path.join(dst, "ki_system"))
            shutil.copytree(os.path.join(src, "ki_system"), os.path.join(dst, "ki_system"),
                            ignore=shutil.ignore_patterns("__pycache__"))
            _clear_db(dst)
            shutil.copyfile(ckpt, os.path.join(dst, "ki_memory.sqlite3"))
            log = open(os.path.join(dst, "run.log"), "w", encoding="utf-8")
            proc = subprocess.Popen([sys.executable, os.path.join(HERE, "run_one.py"), dst, str(a.cycles),
                                     "%s_%s_s%s" % (a.label, a.arm, seed), seed, "probe=" + a.arm, "probe_start=1",
                                     "probe_len=%d" % a.probe_len, "probe_k=%d" % a.k],
                                    stdout=log, stderr=subprocess.STDOUT)
            running.append((seed, dst, proc, log)); print("started", a.arm, "seed", seed, flush=True)
        time.sleep(5)
        for item in list(running):
            seed, dst, proc, log = item
            if proc.poll() is not None:
                log.close(); running.remove(item)
                print("finished", a.arm, "seed", seed, "rc", proc.returncode, flush=True)
                _clear_db(dst)


def _rows(d):
    return list(csv.DictReader(open(os.path.join(d, "learn_metrics.csv"), encoding="utf-8")))


def _series(rows, key):
    out = []
    for r in rows:
        try:
            out.append(float(r[key]))
        except (KeyError, TypeError, ValueError):
            out.append(float("nan"))
    return out


def _max_window_mean(v, width=5):
    best = float("-inf")
    for i in range(0, len(v) - width + 1):
        w = v[i:i + width]
        if not any(math.isnan(x) for x in w):
            best = max(best, sum(w) / width)
    return best


def cmd_k7(a):
    """Evaluate the responsiveness probe (pre-registration Nachtrag 3).

    All windows count from the probe onset t0, the first cycle with injected
    rows in the fail arm (the sham arm starts at the same cycle, because all
    arms are identical up to it): manipulation, response and specificity in
    cycles t0 .. t0+9 (surprise is transient and the arms drift apart in their
    sleep timing later), relaxation as the mean difference over t0+150 ..
    t0+249."""
    base = os.path.join(a.out, a.label)
    seeds = sorted(n[5:] for n in os.listdir(base) if n.startswith("seed_"))
    lines = ["## K7 responsiveness probe for %s (delta %.3f)" % (a.label, a.delta), "",
             "| seed | onset | manipulation: max 5-cycle mean surprise difference, first 10 cycles | response: max 5-cycle mean d, first 10 cycles | specificity: max 5-cycle mean abs(sham minus control), first 10 cycles | relaxation: mean d, cycles 151-250 after onset | eta in bounds | result |",
             "|---|---|---|---|---|---|---|---|"]
    passed = valid = total = 0
    for seed in seeds:
        try:
            ctrl = _rows(os.path.join(base, "seed_" + seed))[a.checkpoint:]
            fail = _rows(os.path.join(a.out, a.label + "_fail", "seed_" + seed))
            sham = _rows(os.path.join(a.out, a.label + "_sham", "seed_" + seed))
        except FileNotFoundError:
            continue
        total += 1
        pr = _series(fail, "probe_rows")
        t0 = next((i for i, x in enumerate(pr) if x > 0), 0)
        n = min(len(ctrl), len(fail), len(sham))
        ce, fe, se = _series(ctrl, "eta_raw")[:n], _series(fail, "eta_raw")[:n], _series(sham, "eta_raw")[:n]
        cs, fs = _series(ctrl, "surprise")[:n], _series(fail, "surprise")[:n]
        w = slice(t0, t0 + 10)
        d = [x - y for x, y in zip(fe, ce)]
        manip = _max_window_mean([x - y for x, y in zip(fs, cs)][w])
        response = _max_window_mean(d[w])
        spec = _max_window_mean([abs(x - y) for x, y in zip(se, ce)][w])
        late = d[t0 + 150:t0 + 250]
        relax = st.mean(late) if len(late) >= 50 else float("nan")
        etas = [x for arm in (ctrl, fail, sham) for x in _series(arm, "eta")[:n] if not math.isnan(x)]
        bounds = all(0.05 - 1e-9 <= x <= 1.0 + 1e-9 for x in etas)
        ok_valid = manip >= 0.10
        ok = ok_valid and response >= a.delta and spec < a.delta / 2 and abs(relax) < a.delta / 2 and bounds
        valid += ok_valid; passed += ok
        lines.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
            seed, t0 + 1, _fmt(manip), _fmt(response), _fmt(spec), _fmt(relax), "yes" if bounds else "no",
            "invalid" if not ok_valid else ("pass" if ok else "FAIL")))
    verdict = "pass" if total and passed >= max(1, total - 1) else "FAIL"
    lines += ["", "K7: %s (%d of %d seeds pass, %d valid; rule: all seeds but at most one)" % (verdict, passed, total, valid)]
    text = "\n".join(lines)
    open(os.path.join(a.out, "k7_%s.md" % a.label), "w", encoding="utf-8").write(text + "\n")
    print(text)

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--snapshot", required=True); r.add_argument("--code", required=True)
    r.add_argument("--label", required=True); r.add_argument("--out", required=True)
    r.add_argument("--seeds", default="0,1,2,3,4"); r.add_argument("--cycles", type=int, default=1000)
    r.add_argument("--parallel", type=int, default=2); r.add_argument("--keep-db", action="store_true")
    r.add_argument("--checkpoint-at", type=int, default=0)
    br = sub.add_parser("branch")
    br.add_argument("--out", required=True); br.add_argument("--label", required=True)
    br.add_argument("--arm", required=True, choices=["fail", "sham"]); br.add_argument("--k", type=int, required=True)
    br.add_argument("--checkpoint", type=int, default=500); br.add_argument("--cycles", type=int, default=300)
    br.add_argument("--probe-len", type=int, default=10); br.add_argument("--seeds", default="0,1,2,3,4")
    br.add_argument("--parallel", type=int, default=5)
    k7 = sub.add_parser("k7")
    k7.add_argument("--out", required=True); k7.add_argument("--label", required=True)
    k7.add_argument("--checkpoint", type=int, default=500); k7.add_argument("--delta", type=float, default=0.05)
    c = sub.add_parser("compare")
    c.add_argument("--out", required=True); c.add_argument("--a", required=True); c.add_argument("--b", required=True)
    c.add_argument("--margin", type=float, default=0.05)
    rp = sub.add_parser("report")
    rp.add_argument("--out", required=True); rp.add_argument("--a", required=True)
    a = p.parse_args()
    {"run": cmd_run, "compare": cmd_compare, "report": cmd_report, "branch": cmd_branch, "k7": cmd_k7}[a.cmd](a)


if __name__ == "__main__":
    main()
