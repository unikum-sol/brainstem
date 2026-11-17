# -*- coding: utf-8 -*-
"""Figures for the preprint "Learning on an experience clock".

Reads the measured BrainStem data read-only and writes SVG figures plus
figure_data.json next to this script. Standard library only, so the
figures can be rebuilt without plotting packages:

    python make_figures.py

Data sources (copied unchanged into ../data, see ../data/README.md):
  data/seed_baseline/seed_0..4   per-cycle metrics and summaries of the
                                 five-seed baseline (code 283091a)
  data/det_1000                  the 1,000-cycle quality run of 16 November
                                 2026 (code of the learning-clock change, run alone)
  data/table_comparisons/*.txt   table-by-table results of the A/A, restart
                                 and run-seed tests

The statistical curves (Figures 6 and 7) are computed here; the Monte Carlo
part uses a fixed seed, so the figures are reproducible too.
"""
import csv, json, math, os, random, re, statistics as st
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
BASE = os.path.join(DATA, "seed_baseline")
DETDIR = os.path.join(DATA, "det_1000")
TABLES = os.path.join(DATA, "table_comparisons")

# Colours (light surface, validated categorical order: blue, orange, aqua)
SURF, INK, INK2, MUTED, GRID = "#ffffff", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
BAND = "#cde2fb"
FONT = "font-family:Helvetica,Arial,sans-serif"


# ------------------------------------------------------------------ data
def rows(d):
    return list(csv.DictReader(open(os.path.join(d, "learn_metrics.csv"), encoding="utf-8")))


def summary(d):
    return json.load(open(os.path.join(d, "learn_summary.json"), encoding="utf-8"))


def table_counts(name):
    first = open(os.path.join(TABLES, name), encoding="utf-8").readline()
    m = re.search(r"identical tables (\d+), differing (\d+)", first)
    return int(m.group(1)), int(m.group(2))


SEEDS = list(range(5))
SR = {s: rows(os.path.join(BASE, "seed_%d" % s)) for s in SEEDS}
SS = {s: summary(os.path.join(BASE, "seed_%d" % s)) for s in SEEDS}
DET = rows(DETDIR)
DETS = summary(DETDIR)
COLS = [c for c in SR[0][0] if c != "seconds"]

data = {}
data["tables"] = {
    "before_fix_AA": table_counts("aa_baseline.txt"),
    "after_fix_AA": table_counts("aa_v4.txt"),
    "restart": table_counts("aa_resume.txt"),
    "other_run_seed": table_counts("aa_seed1.txt"),
}
data["det_vs_seed0_differing_cells"] = sum(1 for i in range(len(DET)) for c in COLS if DET[i][c] != SR[0][i][c])
data["det_vs_seed0_cells_compared"] = len(DET) * len(COLS)
data["first_divergent_cycle"] = {s: next((int(SR[s][i]["cycle"]) for i in range(1000)
                                          if any(SR[s][i][c] != SR[0][i][c] for c in COLS)), None) for s in SEEDS[1:]}
data["first_sleep_cycle_seed0"] = next(int(r["cycle"]) for r in SR[0] if r["state"] == "sleep")
data["wall"] = {
    "det_sum_s": sum(float(r["seconds"]) for r in DET), "det_median_s": st.median(float(r["seconds"]) for r in DET),
    "seed0_sum_s": sum(float(r["seconds"]) for r in SR[0]), "seed0_median_s": st.median(float(r["seconds"]) for r in SR[0]),
}
meas = {}
for s in SEEDS:
    sm = SS[s]
    meas[s] = {"stable_gain": sm["stable_end"] - sm["stable_start"], "facts": sm["facts"], "relations": sm["relations"],
               "capture_rate": sm["captured_uncensored"] / sm["tagged_uncensored"]}
data["seed_measures"] = meas
data["sleep_cycles"] = {s: sum(1 for r in SR[s] if r["state"] == "sleep") for s in SEEDS}

# Two-sided 0.975 quantiles of Student's t (df 1 to 19)
T975 = [None, 12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
        2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093]


# ---------------------------------------------------------------- SVG kit
class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.p = w, h, ['<rect width="%d" height="%d" fill="%s"/>' % (w, h, SURF)]

    def add(self, s):
        self.p.append(s)

    def text(self, x, y, s, size=12, color=INK2, anchor="start", weight="normal", rot=None):
        tr = ' transform="rotate(%d %.1f %.1f)"' % (rot, x, y) if rot else ""
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.add('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="%s" font-weight="%s" style="%s"%s>%s</text>'
                 % (x, y, size, color, anchor, weight, FONT, tr, s))

    def save(self, name):
        body = "\n".join(self.p)
        open(os.path.join(HERE, name), "w", encoding="utf-8").write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">\n%s\n</svg>\n'
            % (self.w, self.h, self.w, self.h, body))


class Panel:
    def __init__(self, svg, x, y, w, h, xr, yr):
        self.s, self.x, self.y, self.w, self.h, self.xr, self.yr = svg, x, y, w, h, xr, yr

    def X(self, v):
        return self.x + (v - self.xr[0]) / (self.xr[1] - self.xr[0]) * self.w

    def Y(self, v):
        return self.y + self.h - (v - self.yr[0]) / (self.yr[1] - self.yr[0]) * self.h

    def axes(self, xt, yt, xl, yl, xfmt=str, yfmt=str, title=None):
        s = self.s
        for v in yt:
            s.add('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (self.x, self.x + self.w, self.Y(v), self.Y(v), GRID))
            s.text(self.x - 6, self.Y(v) + 4, yfmt(v), 11, MUTED, "end")
        for v in xt:
            s.text(self.X(v), self.y + self.h + 16, xfmt(v), 11, MUTED, "middle")
        s.add('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="1"/>' % (self.x, self.x + self.w, self.y + self.h, self.y + self.h, MUTED))
        s.text(self.x + self.w / 2, self.y + self.h + 34, xl, 12, INK2, "middle")
        s.text(self.x - 46, self.y + self.h / 2, yl, 12, INK2, "middle", rot=-90)
        if title:
            s.text(self.x, self.y - 12, title, 13, INK, "start", "bold")

    def line(self, pts, color, width=2, dash=None, opacity=1):
        d = " ".join("%.1f,%.1f" % (self.X(a), self.Y(b)) for a, b in pts)
        da = ' stroke-dasharray="%s"' % dash if dash else ""
        self.s.add('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round" opacity="%s"%s/>'
                   % (d, color, width, opacity, da))

    def dot(self, a, b, color, r=4.5):
        self.s.add('<circle cx="%.1f" cy="%.1f" r="%s" fill="%s" stroke="%s" stroke-width="2"/>' % (self.X(a), self.Y(b), r, color, SURF))

    def hline(self, v, color, dash="5 4", width=1.5):
        self.s.add('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="%s" stroke-dasharray="%s"/>'
                   % (self.x, self.x + self.w, self.Y(v), self.Y(v), color, width, dash))

    def vline(self, v, color, dash="5 4", width=1.5):
        self.s.add('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="%s" stroke-dasharray="%s"/>'
                   % (self.X(v), self.X(v), self.y, self.y + self.h, color, width, dash))


def legend(svg, x, y, items):
    for i, (label, color, dash) in enumerate(items):
        yy = y + i * 18
        da = ' stroke-dasharray="%s"' % dash if dash else ""
        svg.add('<line x1="%d" x2="%d" y1="%d" y2="%d" stroke="%s" stroke-width="2.5"%s/>' % (x, x + 22, yy, yy, color, da))
        svg.text(x + 28, yy + 4, label, 11, INK2)


# ------------------------------------------------------------- Figure 1
def fig1():
    s = Svg(760, 300)
    box = lambda x, y, w, h, fill, stroke: s.add('<rect x="%d" y="%d" width="%d" height="%d" rx="6" fill="%s" stroke="%s" stroke-width="1.5"/>' % (x, y, w, h, fill, stroke))
    arrow = lambda x1, y1, x2, y2: s.add('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.5" marker-end="url(#a)"/>' % (x1, y1, x2, y2, INK2))
    s.add('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker></defs>' % INK2)
    s.text(20, 26, "One learning cycle (one durable transaction)", 13, INK, weight="bold")
    box(20, 44, 170, 70, "#eef5fd", C1)
    s.text(105, 68, "cycle transaction", 12, INK, "middle", "bold")
    s.text(105, 86, "advance(): cycle += 1", 11, INK2, "middle")
    s.text(105, 102, "kept by a step boundary", 11, INK2, "middle")
    arrow(190, 79, 240, 79)
    box(240, 44, 250, 70, "#f7f7f5", MUTED)
    s.text(365, 68, "36 learning phases in fixed order", 12, INK, "middle", "bold")
    s.text(365, 86, "time:  now() = base + cycle", 11, INK2, "middle")
    s.text(365, 102, "noise: rng(phase, purpose)", 11, INK2, "middle")
    arrow(490, 79, 540, 79)
    box(540, 44, 200, 70, "#eef5fd", C1)
    s.text(640, 68, "one commit at cycle end", 12, INK, "middle", "bold")
    s.text(640, 86, "state(t+1) = F(state(t),", 11, INK2, "middle")
    s.text(640, 102, "cycle, run_seed)", 11, INK2, "middle")
    s.text(20, 156, "Inputs of every random stream (counter-based seeding)", 13, INK, weight="bold")
    xs = [20, 150, 280, 410]
    for x, lab, sub in zip(xs, ["run_seed", "cycle", "phase", "purpose"],
                           ["replicate", "learning clock", "module name", "e.g. replay pick"]):
        box(x, 172, 110, 46, "#fdf0ea", C2)
        s.text(x + 55, 192, lab, 12, INK, "middle", "bold")
        s.text(x + 55, 208, sub, 10, INK2, "middle")
    for x in xs:
        arrow(x + 55, 218, 590, 252)
    box(540, 240, 200, 46, "#f7f7f5", MUTED)
    s.text(640, 260, "blake2b, 64-bit seed", 12, INK, "middle", "bold")
    s.text(640, 276, "random.Random(seed)", 11, INK2, "middle")
    s.text(20, 262, "Wall-clock time stays outside learning:", 11, INK2)
    s.text(20, 278, "GUI, import, logs, log compaction, WAL maintenance.", 11, INK2)
    s.save("fig1_clock_schematic.svg")


# ------------------------------------------------------------- Figure 2
def fig2():
    t = data["tables"]
    bars = [("A/A before the fix (100 cycles,", "time columns excluded)", t["before_fix_AA"]),
            ("A/A after the fix (100 cycles,", "all columns incl. timestamps)", t["after_fix_AA"]),
            ("Restart: 50 + 50 cycles", "vs. 100 cycles in one process", t["restart"]),
            ("Other run seed (1 vs. 0)", "100 cycles", t["other_run_seed"])]
    s = Svg(760, 300)
    s.text(20, 24, "Tables of the database that end identical in two runs", 13, INK, weight="bold")
    x0, w, top, bh, gap = 250, 330, 52, 30, 26
    p = Panel(s, x0, top, w, 4 * (bh + gap) - gap, (0, 160), (0, 1))
    for v in (0, 40, 80, 120, 160):
        s.add('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s"/>' % (p.X(v), p.X(v), top - 6, top + 4 * (bh + gap) - gap, GRID))
        s.text(p.X(v), top + 4 * (bh + gap) + 2, str(v), 11, MUTED, "middle")
    s.text(x0 + w / 2, top + 4 * (bh + gap) + 22, "number of tables", 12, INK2, "middle")
    for i, (l1, l2, (same, diff)) in enumerate(bars):
        y = top + i * (bh + gap)
        s.text(x0 - 10, y + 12, l1, 11, INK, "end")
        s.text(x0 - 10, y + 26, l2, 11, INK2, "end")
        xa, xb, xc = p.X(0), p.X(same), p.X(same + diff)
        s.add('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="4" fill="%s"/>' % (xa, y, max(0, xb - xa - 1), bh, C1))
        if diff:
            s.add('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="4" fill="%s"/>' % (xb + 1, y, xc - xb - 1, bh, C2))
        s.text(xc + 6, y + 20, "%d identical, %d differing" % (same, diff), 11, INK2)
    legend(s, 520, 30 - 12, [])
    s.add('<rect x="470" y="14" width="12" height="12" rx="2" fill="%s"/>' % C1)
    s.text(487, 24, "identical", 11, INK2)
    s.add('<rect x="550" y="14" width="12" height="12" rx="2" fill="%s"/>' % C2)
    s.text(567, 24, "differing", 11, INK2)
    s.save("fig2_table_identity.svg")


# ------------------------------------------------------------- Figure 3
def fig3():
    s = Svg(760, 350)
    def cum(rs):
        out, acc = [(0.0, 0)], 0.0
        for r in rs:
            acc += float(r["seconds"])
            out.append((acc / 3600.0, int(r["stable"]) - 4505))
        return out
    a, b = cum(DET), cum(SR[0])
    p1 = Panel(s, 70, 50, 280, 210, (0, 6), (0, 340))
    p1.axes([0, 1, 2, 3, 4, 5, 6], [0, 100, 200, 300], "wall-clock time (hours)", "stable hypotheses gained",
            title="(a) against wall-clock time")
    p1.line(a, C2, 2.5)
    p1.line(b, C1, 2.5)
    s.text(p1.X(a[-1][0]) + 8, p1.Y(a[-1][1]) + 10, "alone: %.1f h" % a[-1][0], 11, INK2)
    s.text(p1.X(2.4), p1.Y(255), "5 runs at once: %.1f h" % b[-1][0], 11, INK2)
    p2 = Panel(s, 440, 50, 280, 210, (0, 1000), (0, 340))
    p2.axes([0, 250, 500, 750, 1000], [0, 100, 200, 300], "learning cycle (learning clock)", "stable hypotheses gained",
            title="(b) against the learning clock")
    p2.line([(int(r["cycle"]), int(r["stable"]) - 4505) for r in DET], C2, 5, opacity=0.55)
    p2.line([(int(r["cycle"]), int(r["stable"]) - 4505) for r in SR[0]], C1, 2)
    s.text(p2.X(560), p2.Y(110), "both curves coincide", 11, INK2)
    s.text(p2.X(560), p2.Y(80), "(0 of %d logged values differ)" % data["det_vs_seed0_cells_compared"], 11, INK2)
    legend(s, 70, 322, [("16 Nov quality run, code before the speed-up, run alone", C2, None)])
    legend(s, 430, 322, [("benchmark seed 0, code 283091a, 5 runs at once", C1, None)])
    s.save("fig3_experience_vs_wall.svg")


# ------------------------------------------------------------- Figure 4
def fig4():
    s = Svg(760, 330)
    p1 = Panel(s, 70, 50, 300, 210, (0, 1000), (0, 340))
    p1.axes([0, 250, 500, 750, 1000], [0, 100, 200, 300], "learning cycle", "stable hypotheses gained",
            title="(a) five run seeds, same code and start")
    shades = [C1, "#1c5cab", "#5598e7", "#104281", "#86b6ef"]
    for k in SEEDS:
        pts = [(int(r["cycle"]), int(r["stable"]) - 4505) for r in SR[k]]
        p1.line(pts, shades[k], 1.6)
    ends = sorted(((int(SR[k][-1]["stable"]) - 4505, k) for k in SEEDS))
    s.text(p1.X(980), p1.Y(40), "gains after 1,000 cycles: %d to %d" % (ends[0][0], ends[-1][0]), 11, INK2, "end")
    rng_pts = []
    for i in range(1000):
        vals = [int(SR[k][i]["stable"]) for k in SEEDS]
        rng_pts.append((int(SR[0][i]["cycle"]), max(vals) - min(vals)))
    p2 = Panel(s, 450, 50, 270, 210, (0, 1000), (0, 30))
    p2.axes([0, 250, 500, 750, 1000], [0, 10, 20, 30], "learning cycle", "range across seeds (max - min)",
            title="(b) spread between the seeds")
    p2.line(rng_pts, C1, 2)
    fd = min(data["first_divergent_cycle"].values())
    p2.vline(fd, C2)
    s.text(p2.X(fd) + 6, p2.Y(27), "cycle %d: first values" % fd, 11, INK2)
    s.text(p2.X(fd) + 6, p2.Y(24.5), "that depend on the seed", 11, INK2)
    s.text(70, 312, "All 24 logged signals are identical in all seeds through cycle %d; cycle %d is the first sleep cycle."
           % (fd - 1, data["first_sleep_cycle_seed0"]), 11, INK2)
    s.save("fig4_seed_trajectories.svg")


# ------------------------------------------------------------- Figure 5
def fig5():
    keys = [("stable_gain", "stable hypotheses", 5.2), ("facts", "facts", 7.2),
            ("relations", "relations", 5.0), ("capture_rate", "capture rate (K5)", 0.006)]
    s = Svg(760, 350)
    p = Panel(s, 80, 50, 620, 220, (0, 4), (-6, 4))
    p.axes([], [-6, -4, -2, 0, 2, 4], "", "deviation from the five-seed mean (%)", yfmt=lambda v: "%+d" % v if v else "0",
           title="Seed baseline: identical code, five run seeds, 1,000 cycles each")
    out = []
    for j, (k, lab, sd) in enumerate(keys):
        vals = [data["seed_measures"][sd_][k] for sd_ in SEEDS]
        mean = st.mean(vals)
        half = T975[4] * math.sqrt(2) * st.stdev(vals) / math.sqrt(5) / mean * 100
        cx = j + 0.5
        s.add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.8"/>'
              % (p.X(cx - 0.28), p.Y(half), p.X(cx + 0.28) - p.X(cx - 0.28), p.Y(-half) - p.Y(half), BAND))
        for i, v in enumerate(vals):
            p.dot(cx - 0.16 + 0.08 * i, (v - mean) / mean * 100, C1)
        s.text(p.X(cx), p.y + p.h + 18, lab, 12, INK, "middle")
        s.text(p.X(cx), p.y + p.h + 33, "mean %s, SD %s" % (("%.3f" % mean) if mean < 2 else ("%.1f" % mean),
                                                           ("%.4f" % st.stdev(vals)) if mean < 2 else ("%.1f" % st.stdev(vals))), 10, MUTED, "middle")
        out.append({"measure": k, "mean": mean, "sd": st.stdev(vals), "half_width_pct": half})
    p.hline(-5, C2)
    s.text(p.X(4) - 4, p.Y(-5) - 6, "non-inferiority margin: -5 % of the reference mean", 11, INK2, "end")
    s.add('<rect x="80" y="326" width="14" height="10" fill="%s"/>' % BAND)
    s.text(100, 335, "expected 95 % half-width of a paired mean difference (5 seeds, uncorrelated variants)", 11, INK2)
    data["half_widths"] = out
    s.save("fig5_seed_baseline.svg")


# ------------------------------------------------------------- Figure 6
def fig6():
    s = Svg(760, 330)
    p1 = Panel(s, 70, 50, 290, 210, (3, 19), (0, 6))
    p1.axes([3, 5, 7, 9, 11, 13, 15, 17, 19], [0, 1, 2, 3, 4, 5, 6], "number of run seeds per variant",
            "95 % half-width (% of mean)", title="(a) resolution of a paired comparison")
    curves = []
    for (k, lab, col) in [("stable_gain", "stable hypotheses", C1), ("facts", "facts", C2), ("relations", "relations", C3)]:
        vals = [data["seed_measures"][x][k] for x in SEEDS]
        cv = st.stdev(vals) / st.mean(vals)
        pts = [(n, T975[n - 1] * math.sqrt(2) * cv / math.sqrt(n) * 100) for n in range(3, 20)]
        p1.line(pts, col, 2)
        curves.append((lab, col, None))
    p1.hline(5, INK2)
    s.text(p1.X(19), p1.Y(5) - 6, "margin 5 %", 11, INK2, "end")
    p1.vline(5, MUTED, "2 3", 1)
    legend(s, p1.X(9.5), p1.Y(4.1), curves)
    p2 = Panel(s, 450, 50, 270, 210, (0, 1), (0, 1))
    p2.axes([0, 0.2, 0.4, 0.6, 0.8, 1.0], [0, 0.2, 0.4, 0.6, 0.8, 1.0], "per-seed failure probability p",
            "probability that the criterion passes", xfmt=lambda v: "%.1f" % v, yfmt=lambda v: "%.1f" % v,
            title="(b) operating characteristic of the pass rule")
    def oc(n, c, p):
        return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(c + 1))
    grid = [i / 100 for i in range(101)]
    p2.line([(q, oc(5, 1, q)) for q in grid], C1, 2)
    p2.line([(q, oc(5, 0, q)) for q in grid], C2, 2)
    p2.line([(q, oc(10, 1, q)) for q in grid], C3, 2, dash="6 4")
    legend(s, 560, 72, [("5 seeds, at most 1 failure", C1, None), ("5 seeds, none (K9)", C2, None),
                        ("10 seeds, at most 1 failure", C3, "6 4")])
    data["oc"] = {str(q): {"5_1": oc(5, 1, q), "5_0": oc(5, 0, q), "10_1": oc(10, 1, q)} for q in (0.1, 0.3, 0.5)}
    s.save("fig6_seed_count_and_pass_rule.svg")


# ------------------------------------------------------------- Figure 7
def fig7():
    """Probability of the verdict "not worse" against the true mean difference,
    for the paired t interval and for the percentile bootstrap used by the tool.
    Both lower bounds are location-scale equivariant, so standard normal
    samples are drawn once and shifted and scaled analytically."""
    n, reps = 5, 20000
    counts = [c for c in product(range(n + 1), repeat=n) if sum(c) == n]          # 126 resamples
    w = [math.factorial(n) / math.prod(math.factorial(x) for x in c) / n ** n for c in counts]
    rng = random.Random(20261117)
    lt, lb, cov_t, cov_b = [], [], 0, 0
    for _ in range(reps):
        z = [rng.gauss(0, 1) for _ in range(n)]
        m, sd = st.mean(z), st.stdev(z)
        lt.append(m - T975[n - 1] * sd / math.sqrt(n))
        hi_t = m + T975[n - 1] * sd / math.sqrt(n)
        dist = sorted(zip((sum(ci * zi for ci, zi in zip(c, z)) / n for c in counts), w))
        acc, lo, hi = 0.0, None, None
        for v, p in dist:
            acc += p
            if lo is None and acc >= 0.025:
                lo = v
            if hi is None and acc >= 0.975:
                hi = v
        lb.append(lo)
        cov_t += lt[-1] <= 0 <= hi_t
        cov_b += lo <= 0 <= hi
    cv = st.stdev([data["seed_measures"][x]["stable_gain"] for x in SEEDS]) / st.mean(
        [data["seed_measures"][x]["stable_gain"] for x in SEEDS]) * 100
    sdd = math.sqrt(2) * cv                                                     # SD of a paired difference, % of mean
    margin = 5.0
    mus = [x / 4 for x in range(-40, 9)]
    pt = [(mu, sum(1 for v in lt if mu + sdd * v > -margin) / reps) for mu in mus]
    pb = [(mu, sum(1 for v in lb if mu + sdd * v > -margin) / reps) for mu in mus]
    at = lambda curve, x: next(p for mu, p in curve if abs(mu - x) < 1e-9)
    data["noninferiority_sim"] = {"reps": reps, "sd_diff_pct": sdd, "coverage_t": cov_t / reps, "coverage_boot": cov_b / reps,
                                  "pass_at_margin_t": at(pt, -5.0), "pass_at_margin_boot": at(pb, -5.0),
                                  "pass_at_0_t": at(pt, 0.0), "pass_at_0_boot": at(pb, 0.0),
                                  "pass_at_-2.5_t": at(pt, -2.5), "pass_at_-2.5_boot": at(pb, -2.5)}
    s = Svg(760, 370)
    p = Panel(s, 80, 50, 620, 220, (-10, 2), (0, 1))
    p.axes(list(range(-10, 3, 2)), [0, 0.2, 0.4, 0.6, 0.8, 1.0], "true mean difference B minus A (% of the reference mean)",
           "probability of the verdict \"not worse\"", xfmt=lambda v: "%+d" % v if v else "0", yfmt=lambda v: "%.1f" % v,
           title="Non-inferiority verdict with 5 paired seeds (stable hypotheses, SD of a difference %.2f %%)" % sdd)
    p.vline(-5, INK2)
    s.text(p.X(-5) - 6, p.Y(0.93), "margin -5 %", 11, INK2, "end")
    p.hline(0.025, MUTED, "2 3", 1)
    s.text(p.X(-10) + 4, p.Y(0.025) - 5, "nominal 2.5 %", 10, MUTED)
    p.line(pt, C1, 2.2)
    p.line(pb, C2, 2.2)
    legend(s, 120, 322, [("paired t interval (lower 95 % bound)", C1, None)])
    legend(s, 420, 322, [("percentile bootstrap, as in benchmark.py", C2, None)])
    s.text(80, 355, "Monte Carlo, %d normal samples, exact bootstrap distribution over all 126 resamples, fixed seed." % reps, 10, MUTED)
    s.save("fig7_noninferiority_oc.svg")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7):
        f()
    json.dump(data, open(os.path.join(HERE, "figure_data.json"), "w", encoding="utf-8"), indent=1, default=str)
    print(json.dumps({k: data[k] for k in data if k not in ("seed_measures", "oc")}, indent=1, default=str))
    print(json.dumps(data["oc"], indent=1))
