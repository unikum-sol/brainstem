"""Replay effectiveness as a cued-versus-uncued contrast (used by Phase 6b).

Biology measures the benefit of sleep replay item by item: memories that were
reactivated during sleep are compared with comparable memories that were not,
and the outcome is read out later (targeted memory reactivation: Rudoy, Voss,
Westerberg & Paller 2009; Rasch, Buechel, Gais & Born 2007; meta-analysis of
91 experiments: Hu, Cheng, Chiu & Paller 2020).

Version 2 (14 November 2026), after a second advisory council of three agents
(sleep neuroscience, measurement methodology, code and data facts):
- Outcome = capture. In synaptic tagging and capture, success means that a
  tagged trace is captured before its tag decays (Frey & Morris 1997; Redondo &
  Morris 2011). A trace counts as a success when it has reached three
  reinforced survivals, or has graduated, by cycle c+H; the cycle c itself
  counts, because that is where the cue acts. Version 1 counted "a further
  survival after c": a cued trace that was captured left the tagged track and
  could not survive again, so the success of the cue was scored as a failure
  (informative censoring by a competing event; Frangakis & Rubin 2002; Young
  et al. 2020).
- Enrollment: a trace enters at most one cohort per H cycles, so cohorts do not
  share items and their differences are close to independent (new-user design,
  Ray 2003). Version 1 put the same trace into about 25 overlapping cohorts,
  which made the standard error too small.
- Only traces inside the replay pool of Phase 7d are compared (emulated target
  trial: Hernan & Robins 2016). Inside the pool all tagged traces start with
  the same base score, so being cued is close to random.
- Comparison within strength strata (one or two survivals before c), because
  weak traces are replayed preferentially (Schapiro et al. 2018).
- Decision rule: the cohort differences are smoothed (EWMA, lambda 0.1) and
  flagged only beyond 2.814 standard errors (EWMA control chart, in-control
  run length about 500 looks: Lucas & Saccucci 1990). A plateau needs evidence
  of absence, not absence of evidence (Altman & Bland 1995): the equivalence
  bound |effect| + 1.645 SE < 0.03 (two one-sided tests, Schuirmann 1987) has
  to hold for a run of cohorts, followed by hysteresis.
- Without enough evidence the score is 0, with no plateau and no state change.
- The score effect_scale * tanh(z / 3) keeps the range of the previous
  contract of Phase 6b (about +-0.05; consumers: 6b, 6c, 6d, cortisol).

Expected result: a small positive effect at most. Nearly every tagged trace is
replayed within a few cycles anyway (the replay capacity is rarely binding), so
a single cue mostly gives a head start; biology shows the same ceiling for
well-learned items (Creery, Oudiette, Antony & Paller 2015).
Note: Phase 7d and Stage-B graduation keep separate cycle counters; they match
in normal operation, the offset is logged in `cue_effect_counter_offset`.
"""
import math
from typing import Any, Dict, Optional

COHORTS = "phase6b_replay_cohorts"
STATE = "phase6b_state"
VERSION = 2
HORIZON = 15
EWMA_ALPHA = 0.1
MIN_COHORTS = 8
MAX_SE = 0.1
EFFECT_SCALE = 0.05
FLAG_Z = 2.814
EQUIV_DELTA = 0.03
PLATEAU_RUN = 20
MAX_ASSIGN_PER_CALL = 5
CAPTURE_SURVIVALS = 3


def _table_exists(con, name) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _kv(con) -> Dict[str, str]:
    return dict(con.execute("SELECT key, value FROM " + STATE).fetchall()) if _table_exists(con, STATE) else {}


def _set(con, key, value) -> None:
    con.execute("INSERT INTO " + STATE + "(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)))


def _f(v, d=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return d


def ensure_schema(con) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS " + COHORTS + " (cycle_index INTEGER NOT NULL, source_id INTEGER NOT NULL, "
                "cued INTEGER NOT NULL, level INTEGER NOT NULL, matured INTEGER NOT NULL DEFAULT 0, success INTEGER, "
                "PRIMARY KEY(cycle_index, source_id))")
    con.execute("CREATE INDEX IF NOT EXISTS idx_phase6b_replay_cohorts_open ON " + COHORTS + "(matured, cycle_index)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_phase6b_replay_cohorts_source ON " + COHORTS + "(source_id, cycle_index)")
    if _table_exists(con, "phase7d_consolidation_survivors"):
        con.execute("CREATE INDEX IF NOT EXISTS idx_phase7d_survivors_source ON phase7d_consolidation_survivors"
                    "(source_table, source_id, cycle_index)")


def _migrate(con, st: Dict[str, str]) -> None:
    """Version 1 cohorts used another outcome; start the estimate afresh."""
    if int(_f(st.get("cue_effect_version"), 1)) == VERSION:
        return
    con.execute("DELETE FROM " + COHORTS)
    for key in ("cue_effect_ewma", "cue_effect_ewma_var", "cue_effect_cohorts", "cue_effect_null_run",
                "cue_effect_equiv_run"):
        con.execute("DELETE FROM " + STATE + " WHERE key=?", (key,))
    _set(con, "cue_effect_version", VERSION)


def _checkpoint(p6b: Dict[str, str]) -> int:
    return int(_f(p6b.get("phase7d_survivor_anchor_checkpoint_id"), 0))


def _assign(con, c: int, p6b: Dict[str, str]) -> int:
    cued = {r[0] for r in con.execute(
        "SELECT DISTINCT source_id FROM phase7d_up_state_events WHERE cycle_index=? AND source_table='context_hypotheses'",
        (c,))}
    if not cued:
        return 0
    row = con.execute("SELECT value FROM phase7d_state WHERE key='survivor_tag_window_applied'").fetchone() \
        if _table_exists(con, "phase7d_state") else None
    tag_window = max(1, int(_f(row[0], 300))) if row else 300
    cap_row = con.execute("SELECT value FROM phase7d_state WHERE key='reactivation_capacity'").fetchone() \
        if _table_exists(con, "phase7d_state") else None
    capacity = int(_f(cap_row[0], 0)) if cap_row else 0
    anchors = set()
    if _table_exists(con, "phase6b_anchor_pool"):
        anchors = {r[0] for r in con.execute(
            "SELECT source_id FROM phase6b_anchor_pool WHERE active=1 AND source_table='context_hypotheses'")}
    rows = con.execute(
        "SELECT s.source_id, COUNT(DISTINCT s.cycle_index), MAX(s.cycle_index) FROM phase7d_consolidation_survivors s "
        "JOIN context_hypotheses h ON h.id=s.source_id "
        "WHERE s.id>? AND s.reinforced=1 AND s.source_table='context_hypotheses' AND s.cycle_index<? "
        "AND h.role LIKE 'uncertain_%' GROUP BY s.source_id "
        "HAVING COUNT(DISTINCT s.cycle_index) IN (1,2) AND MAX(s.cycle_index)>=?",
        (_checkpoint(p6b), c, c - tag_window)).fetchall()
    pool = [r for r in rows if r[0] not in anchors]
    # Replay pool of 7d: tagged traces ordered by level and recency, capped by
    # the reactivation capacity. Traces outside the pool could never be cued.
    pool.sort(key=lambda r: (-int(r[1]), -int(r[2]), int(r[0])))
    if 0 < capacity < len(pool):
        pool = pool[:capacity]
    n = 0
    for sid, level, _last in pool:
        prev = con.execute("SELECT MAX(cycle_index) FROM " + COHORTS + " WHERE source_id=?", (sid,)).fetchone()[0]
        if prev is not None and c - int(prev) < HORIZON:
            continue
        con.execute("INSERT OR IGNORE INTO " + COHORTS + "(cycle_index, source_id, cued, level) VALUES(?,?,?,?)",
                    (c, sid, 1 if sid in cued else 0, int(level)))
        n += 1
    return n


def _cohort_effect(con, c: int):
    """Stratified cued-minus-uncued difference of the capture rate in one
    matured cohort, with its variance; None if no stratum has both arms."""
    num = den = var = 0.0
    for level in (1, 2):
        arms = {}
        for cued in (0, 1):
            r = con.execute("SELECT COUNT(*), COALESCE(SUM(success),0) FROM " + COHORTS +
                            " WHERE cycle_index=? AND level=? AND cued=?", (c, level, cued)).fetchone()
            arms[cued] = (int(r[0]), int(r[1]))
        (n0, s0), (n1, s1) = arms[0], arms[1]
        if n0 == 0 or n1 == 0:
            continue
        p0, p1 = (s0 + 0.5) / (n0 + 1.0), (s1 + 0.5) / (n1 + 1.0)
        w = (n0 * n1) / float(n0 + n1)
        num += w * (p1 - p0)
        den += w
        var += w * w * (p1 * (1 - p1) / (n1 + 1.0) + p0 * (1 - p0) / (n0 + 1.0))
    if den <= 0:
        return None
    return num / den, var / (den * den)


def _mature(con, upto: int, st: Dict[str, str], p6b: Dict[str, str]) -> int:
    cohorts = [r[0] for r in con.execute(
        "SELECT DISTINCT cycle_index FROM " + COHORTS + " WHERE matured=0 AND cycle_index<=? ORDER BY cycle_index", (upto,))]
    ewma = _f(st.get("cue_effect_ewma"), 0.0)
    ewma_var = _f(st.get("cue_effect_ewma_var"), 1.0)
    n_cohorts = int(_f(st.get("cue_effect_cohorts"), 0))
    equiv_run = int(_f(st.get("cue_effect_equiv_run"), 0))
    checkpoint = _checkpoint(p6b)
    has_grad = _table_exists(con, "stageb_graduation_events")
    grad_sql = ("EXISTS(SELECT 1 FROM stageb_graduation_events g WHERE g.hypothesis_id=" + COHORTS + ".source_id "
                "AND g.decision LIKE 'graduated_to_%' AND g.cycle_index>=? AND g.cycle_index<=?)") if has_grad else "0"
    for c in cohorts:
        params = [checkpoint, c + HORIZON, CAPTURE_SURVIVALS] + ([c, c + HORIZON] if has_grad else []) + [c]
        con.execute("UPDATE " + COHORTS + " SET matured=1, success=(CASE WHEN (SELECT COUNT(DISTINCT s.cycle_index) "
                    "FROM phase7d_consolidation_survivors s WHERE s.source_table='context_hypotheses' "
                    "AND s.source_id=" + COHORTS + ".source_id AND s.reinforced=1 AND s.id>? AND s.cycle_index<=?)>=? "
                    "OR " + grad_sql + " THEN 1 ELSE 0 END) WHERE cycle_index=? AND matured=0", params)
        eff = _cohort_effect(con, c)
        if eff is None:
            continue
        d, v = eff
        if n_cohorts == 0:
            ewma, ewma_var = d, v
        else:
            ewma = (1 - EWMA_ALPHA) * ewma + EWMA_ALPHA * d
            ewma_var = (1 - EWMA_ALPHA) ** 2 * ewma_var + EWMA_ALPHA ** 2 * v
        n_cohorts += 1
        se = math.sqrt(max(ewma_var, 1e-12))
        equivalent = n_cohorts >= MIN_COHORTS and abs(ewma) + 1.645 * se < EQUIV_DELTA
        equiv_run = equiv_run + 1 if equivalent else 0
    _set(con, "cue_effect_ewma", round(ewma, 8))
    _set(con, "cue_effect_ewma_var", round(ewma_var, 10))
    _set(con, "cue_effect_cohorts", n_cohorts)
    _set(con, "cue_effect_equiv_run", equiv_run)
    con.execute("DELETE FROM " + COHORTS + " WHERE matured=1 AND cycle_index<?", (upto - 10 * HORIZON,))
    return len(cohorts)


def _log_counter_offset(con) -> None:
    try:
        a = con.execute("SELECT value FROM phase7d_state WHERE key='cycle_count'").fetchone()
        b = con.execute("SELECT value FROM stageb_graduation_state WHERE key='cycle_count'").fetchone()
        if a and b:
            _set(con, "cue_effect_counter_offset", int(_f(b[0])) - int(_f(a[0])))
    except Exception:
        pass


def measure(con) -> Optional[Dict[str, Any]]:
    """Updates the cohorts and returns the effectiveness contract of 6b, or
    None if Phase 7d has not produced any up-state yet."""
    if not (_table_exists(con, "phase7d_up_state_events") and _table_exists(con, "phase7d_consolidation_survivors")
            and _table_exists(con, "context_hypotheses")):
        return None
    ensure_schema(con)
    last = con.execute("SELECT MAX(cycle_index) FROM phase7d_up_state_events").fetchone()[0]
    if last is None:
        return None
    last = int(last)
    _migrate(con, _kv(con))
    st = _kv(con)
    start = int(_f(st.get("cue_effect_last_assigned"), last - 1))
    assigned = 0
    for c in range(start + 1, min(last, start + MAX_ASSIGN_PER_CALL) + 1):
        assigned += _assign(con, c, st)
        _set(con, "cue_effect_last_assigned", c)
    matured = _mature(con, last - HORIZON, st, st)
    _log_counter_offset(con)
    st = _kv(con)
    n_cohorts = int(_f(st.get("cue_effect_cohorts"), 0))
    ewma = _f(st.get("cue_effect_ewma"), 0.0)
    se = math.sqrt(max(_f(st.get("cue_effect_ewma_var"), 1.0), 1e-12))
    z = ewma / se
    base = {"cue_effect": round(ewma, 6), "cue_effect_se": round(se, 6), "cue_effect_z": round(z, 4),
            "cue_cohorts": n_cohorts, "cue_assigned": assigned, "cue_matured": matured, "cue_version": VERSION}
    if n_cohorts < MIN_COHORTS or se > MAX_SE:
        base.update({"effectiveness_score": 0.0, "plateau_flag": 0, "state_change_allowed": 0,
                     "evidence_state": "outcome_observed_insufficient_comparison",
                     "evidence_reason": "cue_effect_insufficient_cohort"})
        return base
    if z > FLAG_Z:
        label = "cue_effect_positive"
    elif z < -FLAG_Z:
        label = "cue_effect_negative"
    else:
        label = "cue_effect_null"
    plateau = 1 if int(_f(st.get("cue_effect_equiv_run"), 0)) >= PLATEAU_RUN else 0
    if plateau:
        # One plateau signal per run of equivalent cohorts; the next one needs
        # a new run (hysteresis).
        _set(con, "cue_effect_equiv_run", 0)
        label = "cue_effect_equivalent_to_zero"
    # The evidence states keep the vocabulary that 6b, 6c and the critic gate
    # already understand; the cue-effect label goes into the reason.
    base.update({"effectiveness_score": round(EFFECT_SCALE * math.tanh(z / 3.0), 6), "plateau_flag": plateau,
                 "state_change_allowed": 1,
                 "evidence_state": "outcome_observed_no_change" if plateau else "outcome_observed_change",
                 "evidence_reason": label})
    return base
