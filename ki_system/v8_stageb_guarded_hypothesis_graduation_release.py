# -*- coding: utf-8 -*-
"""Stage-B guarded hypothesis graduation with productive fact closure.

Graduates at most one uncertain hypothesis per cycle to stable_hypothesis.
No facts, relations, or questions are written. Eligibility requires three
separate Phase-7d consolidation survival cycles, warm-up completion, active
status, and the canonical Phase-6b critic gate.
"""
from __future__ import annotations
import json, os, sqlite3, time
from pathlib import Path

PHASE = "stageb_guarded_hypothesis_graduation_release"
VERSION = "stageb_cd_v1"
STATE = "stageb_graduation_state"
EVENTS = "stageb_graduation_events"
PROTECTED = ("facts", "relations", "questions")
# BRAINSTEM_LEXICAL_LAYER_GRADUATION_ELIGIBILITY_V1: this project's own
# lexical-emergence concept (docs/lexical_emergence_concept.md) explicitly
# requires the new 'uncertain_lexical_boundary' hypothesis role (see
# v8_phase0_lexical_boundary_observation_release.py) to graduate through
# this EXACT SAME consolidation-survival + critic-gate mechanism as every
# other hypothesis -- not a separate, duplicated graduation path. Extending
# a small, explicit, easy-to-audit mapping (rather than a generic
# "uncertain_*" prefix-match convention) is a deliberately conservative
# choice for this safety-critical module: every currently-known eligible
# role is named here explicitly, so no future, unrelated role could ever
# accidentally become graduation-eligible via a wildcard match. Extending
# _candidates()/run_graduation_cycle() below to iterate this map instead of
# a single hardcoded role produces IDENTICAL behavior to before whenever
# the matched role is 'uncertain_hypothesis' (the only role that existed
# prior to this change) -- byte-for-byte the same resulting SQL and
# decision strings -- and only takes a new code path when a row's role is
# 'uncertain_lexical_boundary'.
ELIGIBLE_ROLES = {
    "uncertain_hypothesis": "stable_hypothesis",
    "uncertain_lexical_boundary": "stable_lexical_boundary",
    # BRAINSTEM_RELATIONS_EMERGENCE_SLICE1_V1 (25 September 2026): the
    # extension point this module's own comment above already documents --
    # see BrainStem_Relations_Ontology_Questions_Emergence_Concept.md,
    # Abschnitt 10.1, point 1. Identical graduation criteria as every
    # other role (>=3 survived phase7d consolidations, critic gate where
    # available); no special-casing added for relation hypotheses.
    "uncertain_relation_hypothesis": "stable_relation_hypothesis",
}
SCHEMA_TABLES = {
    STATE: [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    EVENTS: [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("created_at","INTEGER"),("cycle_index","INTEGER"),
             ("hypothesis_id","INTEGER"),("old_role","TEXT"),("new_role","TEXT"),("survival_cycles","INTEGER"),
             ("critic_allowed","INTEGER"),("critic_penalty","REAL"),("critic_reason","TEXT"),
             ("decision","TEXT"),("details","TEXT"),("facts_before","INTEGER"),("facts_after","INTEGER"),
             ("relations_before","INTEGER"),("relations_after","INTEGER"),("questions_before","INTEGER"),
             ("questions_after","INTEGER")],
}
DEFAULTS = {"enabled":"true","warmup_cycles":"50","cycle_count":"0","minimum_7d_survivals":"3",
            "promotion_budget":"1","total_graduated":"0","fact_promotion":"disabled",
            "direct_fact_writes":"disabled","direct_relation_writes":"disabled","question_writes":"disabled",
            "mode":"consolidation_gated_stable_hypothesis_only",
            # BRAINSTEM_GRADUATION_NEUROMODULATOR_COUPLING_V1 (28 September
            # 2026): see the block comment above _neuromodulators() (near
            # _select_role_by_divisive_normalization) for the full,
            # literature-grounded derivation of both gains. Both are
            # exactly inert (no behavior change from before this delivery)
            # at their respective messenger's neutral baseline of 0.5.
            "selection_pressure_ach_novelty_gain":"0.6",
            "selection_pressure_gaba_temperature_gain":"0.5",
            "selection_pressure_temperature_base":"1.0"}

def _now(): return int(time.time())
def _table_exists(con,t): return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
def _columns(con,t): return [r[1] for r in con.execute("PRAGMA table_info("+t+")")] if _table_exists(con,t) else []
def _read_kv(con,table):
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())
def _set(con,k,v):
    con.execute("INSERT INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(k,str(v).lower() if isinstance(v,bool) else str(v),_now()))
def _int(v,d=0):
    try: return int(float(v))
    except Exception: return d
def _float(v,d=0.0):
    try: return float(v)
    except Exception: return d
def _count(con,t): return int(con.execute("SELECT COUNT(*) FROM "+t).fetchone()[0]) if _table_exists(con,t) else 0
def _protected(con): return {t:_count(con,t) for t in PROTECTED}
def resolve_db(obj=None):
    if isinstance(obj,sqlite3.Connection): obj.row_factory=sqlite3.Row; return obj
    if obj is not None:
        for a in ("db","conn","con","connection"):
            v=getattr(obj,a,None)
            if isinstance(v,sqlite3.Connection): v.row_factory=sqlite3.Row; return v
        for a in ("mem","memory"):
            v=getattr(obj,a,None)
            if v is not None and v is not obj:
                try: return resolve_db(v)
                except Exception: pass
    path="ki_memory.sqlite3"
    p=Path(__file__).resolve().parent.parent/path
    if not os.path.exists(path) and p.exists(): path=str(p)
    con=sqlite3.connect(path,timeout=30); con.row_factory=sqlite3.Row; return con

def ensure_schema(con):
    for table,defs in SCHEMA_TABLES.items():
        if not _table_exists(con,table): con.execute("CREATE TABLE "+table+" ("+", ".join(n+" "+d for n,d in defs)+")")
        else:
            live=set(_columns(con,table))
            for n,d in defs:
                if n not in live and "PRIMARY KEY" not in d.upper() and "AUTOINCREMENT" not in d.upper(): con.execute("ALTER TABLE "+table+" ADD COLUMN "+n+" "+d)
    con.execute("CREATE INDEX IF NOT EXISTS idx_stageb_grad_cycle ON "+EVENTS+"(cycle_index)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_stageb_grad_hyp ON "+EVENTS+"(hypothesis_id)")
    for k,v in DEFAULTS.items(): con.execute("INSERT OR IGNORE INTO "+STATE+"(key,value,updated_at) VALUES(?,?,?)",(k,v,_now()))
    con.commit(); return _self_check_schema(con)
def _self_check_schema(con):
    missing=[]
    for t,defs in SCHEMA_TABLES.items():
        live=set(_columns(con,t)); missing += [t+"."+n for n,_ in defs if n not in live]
    if missing: raise RuntimeError("stageb graduation schema missing: "+repr(missing))
    return {"overall":True,"missing":[]}
def _bias_state(con):
    st=_read_kv(con,"phase6a_meta_plasticity_state") if _table_exists(con,"phase6a_meta_plasticity_state") else {}
    return {"plasticity_level":_float(st.get("last_plasticity_level"),.5),"exploration_bias":_float(st.get("last_exploration_bias"),.5),
            "consolidation_bias":_float(st.get("last_consolidation_bias"),.5),"inhibition_bias":_float(st.get("last_inhibition_bias"),.3),
            "revision_bias":_float(st.get("last_revision_bias"),.5)}
def _critic(con,anchor_consistency):
    try:
        from ki_system import v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release as p6b
        return p6b._critic_gate(con,_bias_state(con),anchor_consistency)
    except Exception as exc:
        return False,1.0,"critic_gate_unavailable:"+type(exc).__name__
def _candidates(con,minimum,limit=64,role_filter=None,exclude_ids=None):
    if not _table_exists(con,"context_hypotheses") or not _table_exists(con,"phase7d_consolidation_survivors"): return []
    cols=set(_columns(con,"context_hypotheses")); role_expr="COALESCE(h.role,'')" if "role" in cols else "''"; status_expr="COALESCE(h.status,'active')" if "status" in cols else "'active'"
    # BRAINSTEM_LEXICAL_LAYER_GRADUATION_ELIGIBILITY_V1: role_expr is
    # aliased explicitly ("AS matched_role") so callers get a clean,
    # predictable dict key regardless of the expression's own literal SQL
    # text (previously unaliased and unused by any caller). The eligible-
    # role list is built ONLY from this module's own fixed ELIGIBLE_ROLES
    # keys (never from external/user input), so simple string
    # concatenation into the IN(...) list is safe here.
    # BRAINSTEM_DIVISIVE_NORMALIZATION_BUDGET_SHARING_V1 (25 September 2026):
    # role_filter/exclude_ids added so this same function can be reused both
    # for cross-role PRESSURE counting (_role_pressure() below, role_filter
    # unset -> original global-role-list behavior, byte-for-byte unchanged
    # SQL when called exactly as before) and for fetching the single, top
    # eligible candidate WITHIN one already-selected role (role_filter set
    # to exactly one role -- see run_graduation_cycle()'s new selection
    # loop). exclude_ids lets the same-cycle loop skip a hypothesis id
    # already handled earlier in the same cycle (relevant only if
    # promotion_budget is ever configured above its current hard clamp of
    # 1; harmless and inert while that clamp remains in place).
    roles_to_use = [role_filter] if role_filter else list(ELIGIBLE_ROLES)
    role_list = ",".join("'" + r.replace("'", "''") + "'" for r in roles_to_use)
    exclude_clause = ""
    params = [minimum]
    if exclude_ids:
        exclude_clause = " AND h.id NOT IN (" + ",".join("?" for _ in exclude_ids) + ")"
        params = [minimum] + list(exclude_ids)
    q=("SELECT h.id,"+role_expr+" AS matched_role,"+status_expr+" AS matched_status,COUNT(DISTINCT s.cycle_index) AS survived,AVG(COALESCE(s.final_consistency,0)) AS consistency "
       "FROM context_hypotheses h JOIN phase7d_consolidation_survivors s ON s.source_table='context_hypotheses' AND s.source_id=h.id "
       "WHERE "+role_expr+" IN ("+role_list+") AND "+status_expr+"='active' AND COALESCE(s.reinforced,0)=1"+exclude_clause+" "
       "GROUP BY h.id HAVING COUNT(DISTINCT s.cycle_index)>=? ORDER BY survived DESC,consistency DESC,h.id ASC LIMIT ?")
    params.append(limit)
    return [dict(r) for r in con.execute(q,tuple(params)).fetchall()]

# BRAINSTEM_DIVISIVE_NORMALIZATION_BUDGET_SHARING_V1 (25 September 2026)
#
# BACKGROUND: BrainStem_Relations_Ontology_Questions_Emergence_Concept.md
# (Abschnitt 9.4) identifies a real starvation risk introduced by Relations
# Slice 1: this module's own `promotion_budget` (hard-clamped to at most 1
# graduation per real cycle) was, until this change, shared across ALL
# ELIGIBLE_ROLES via a single, flat, global `ORDER BY survived DESC,
# consistency DESC` -- meaning sentence-level hypotheses (the oldest,
# highest-volume population in this project's real corpus) would almost
# always outrank freshly-created relation hypotheses for that single slot,
# indefinitely. Abschnitt 9.4 prescribes divisive normalization (Carandini &
# Heeger 2011/2012, "the canonical neural computation") to fairly share a
# single scarce resource across competing populations, proportional to
# each population's current "Bedarfsdruck" (demand pressure).
#
# IMPORTANT, EXPLICITLY DOCUMENTED DEVIATION FROM ABSCHNITT 9.4'S LITERAL
# WORDING: that section defines pressure as "Anzahl aktuell graduierter,
# aber noch nicht befoerderter Kandidaten" (count of ALREADY-GRADUATED but
# not-yet-PROMOTED candidates), implying the scarce resource sits at the
# fact/relation PROMOTION step. A direct audit of
# v8_stageb_fact_promotion_release.py and v8_stageb_relation_promotion_
# release.py found this assumption does not hold in the actual, implemented
# architecture: both promotion modules process up to 200 already-graduated
# events per cycle with no artificial per-cycle cap of their own -- there is
# effectively NO scarcity or competition at the promotion step at all. The
# real, single scarce resource in this codebase is exactly one level
# upstream: THIS module's own shared `promotion_budget` at hypothesis
# GRADUATION time. Divisive normalization is therefore applied here, at
# graduation, with pressure redefined as the count of candidates PER ROLE
# that already satisfy this module's own, unchanged eligibility criteria
# (>=minimum_7d_survivals, reinforced, active) -- i.e. "how many are
# currently waiting at the front door to graduate" for each role. This
# adapts Abschnitt 9.4's INTENT (prevent one population from starving
# another at a shared scarce resource) to where that scarcity actually
# lives in the real system, rather than mechanically applying the formula
# at a step where it would be a complete no-op.
#
# MECHANISM: for the (still hard-capped, still =<1) budget available this
# cycle, one role is selected per remaining budget slot via
# divisive-normalized, weighted-random selection --
#   share(role) = pressure(role) / (sum(pressure) + sigma)
# -- using the EXACT SAME Efraimidis-Spirakis weighted-sampling-without-
# replacement formula already used elsewhere in this codebase (see
# v8_phase7d_slow_wave_sleep_substructure_release.py's own up-state
# selection: key = rnd.random() ** (1/max(eps,weight)), keep the largest
# key), rather than introducing a second, independent randomization
# convention. Once a role is selected, that role's own single top-ranked
# eligible candidate (by the module's pre-existing survived/consistency
# ordering, now scoped to just that role) receives the graduation attempt
# -- every other safety mechanism (critic gate, protected-counts check,
# savepoint/rollback, event logging) is completely unchanged.
_SIGMA_DEFAULT = 1.0

# BRAINSTEM_GRADUATION_NEUROMODULATOR_COUPLING_V1 (28 September 2026)
#
# BACKGROUND: a project-wide neuromodulator-coverage review found this
# module's own divisive-normalization role selection (see the block above)
# was entirely neuromodulator-blind -- pressure/shares depended only on
# raw eligible-candidate counts, with no path for the six-core botenstoffe
# to influence which role's candidate is even attempted. Two couplings are
# added here, following the exact literature-grounded combination already
# agreed for this specific mechanism:
#
# (1) Acetylcholine -> per-role NOVELTY bias on effective pressure.
#     Douchamps, Jeewajee, Blundell, Burgess & Lever (2013, J Neurosci
#     33(20):8689-8704) show acetylcholine shifts hippocampal circuit
#     dynamics toward ENCODING NEW information in genuinely novel
#     environments (three independently-confirmed predictions, including a
#     cholinergic-antagonist-reversible shift in place-cell theta phase).
#     Gomez-Ocadiz, Trippa, Zhang, Posani, Cocco, Monasson & Schmidt-Hieber
#     (2022, Nat Commun 13:4122) independently confirm, at the synaptic
#     level, that this novelty-driven encoding-vs-retrieval switch is itself
#     acetylcholine-dependent (blocked by the muscarinic antagonist
#     atropine). Applied here as: a role that has historically graduated
#     LESS OFTEN than others (relative novelty) receives a boost to its
#     effective pressure when acetylcholine is elevated -- directly
#     resolving the real, measured starvation risk this project's own
#     Abschnitt 9.4 divisive-normalization work was built to address
#     (sentence-level hypotheses' sheer historical volume would otherwise
#     always out-rank newer, structurally rarer roles such as relation or
#     lexical-boundary hypotheses), but via a real, literature-grounded
#     mechanism rather than an arbitrary tie-breaker.
#
#     "Historical graduation count" is read directly from this module's
#     own, already-existing EVENTS log (decision LIKE 'graduated_to_%',
#     grouped by new_role) -- no new tracking table, no new counting
#     mechanism; the ledger this project already keeps for full
#     auditability is reused as-is.
#
# (2) GABA -> a temperature exponent sharpening (or flattening) the FINAL
#     role-selection competition. Katzner, Busse & Carandini (2011,
#     J Neurosci 31(16):5931-5941) -- the same Carandini whose divisive-
#     normalization formalism (2011/2012) already underlies this entire
#     mechanism -- show directly, via GABA_A blockade (gabazine) in cat V1,
#     that intact GABAergic inhibition sharpens stimulus selectivity;
#     blocking it broadens/flattens the response profile across competing
#     stimuli. Applied here as a temperature exponent on each role's raw
#     pressure BEFORE computing shares: high GABA raises the exponent,
#     amplifying the already-dominant role's relative advantage (sharper,
#     more decisive competition); low GABA lowers it toward 1.0 (flatter,
#     more permissive competition, giving under-pressure roles comparatively
#     more of a chance). This is a genuine, disclosed trade-off with (1)'s
#     own fairness intent, not a contradiction masked as one: focused,
#     high-inhibition attentional states narrowing decisively onto the
#     currently-dominant signal is itself the literature-documented,
#     biologically correct behavior for elevated GABA, not a bug.
#
# NOTE on `sigma` (pre-existing parameter, left untouched): a direct
# mathematical check confirms `sigma` in share(role) = pressure(role) /
# (sum(pressure)+sigma) cancels out completely in the Efraimidis-Spirakis
# selection probability regardless of its value (the same additive
# constant appears in every role's denominator, so it never changes which
# role has the largest key). This was already true before this delivery
# and remains a harmless, disclosed technical footnote -- not something
# this delivery silently "fixes", since sigma is not the mechanism being
# extended here. The two new couplings above operate on the pressure
# values BEFORE the shares/sigma step (novelty bias) and via a genuine
# exponent (GABA temperature) specifically because a further additive
# constant would have been equally inert.
#
# Both couplings use the same symmetric, self-regulating gain pattern
# already established project-wide (v8_phase7d_slow_wave_sleep_
# substructure_release.py's own acetylcholine gate; v8_stageb_gap_
# detection_release.py's own noradrenaline/serotonin couplings): a factor
# that is EXACTLY the pre-existing behavior at the neutral baseline (0.5)
# for both acetylcholine and gaba, so calibrated defaults remain unchanged
# unless the corresponding messenger genuinely deviates from neutral.
def _neuromodulators(con):
    """Identical access pattern to every other module in this chain that
    reads the shared six-core neuromodulator snapshot (e.g. v8_stageb_
    question_promotion_release.py's / v8_stageb_gap_detection_release.py's
    own _neuromodulators()) -- no new messenger responsibility introduced."""
    defaults = {
        "dopamine": 0.5, "serotonin": 0.6, "glutamate": 0.4,
        "gaba": 0.4, "noradrenaline": 0.3, "acetylcholine": 0.5,
    }
    if not _table_exists(con, "phase6a_neuromodulated_sleep_state"):
        return defaults
    values = _read_kv(con, "phase6a_neuromodulated_sleep_state")
    for key in tuple(defaults):
        try:
            defaults[key] = float(values.get(key, defaults[key]))
        except (TypeError, ValueError):
            pass
    return defaults


def _historical_role_graduations(con):
    """Per-role count of how many times that role has EVER actually
    graduated in this project's real history, read directly from this
    module's own, already-existing EVENTS log -- reused as-is, no new
    table. new_role stores the TARGET role name (e.g. 'stable_hypothesis')
    on a real graduation event, so this maps each target name back to its
    ELIGIBLE_ROLES source key."""
    counts = {role: 0 for role in ELIGIBLE_ROLES}
    if not _table_exists(con, EVENTS):
        return counts
    target_to_role = {target: role for role, target in ELIGIBLE_ROLES.items()}
    rows = con.execute(
        "SELECT new_role, COUNT(*) FROM " + EVENTS + " WHERE decision LIKE 'graduated_to_%' GROUP BY new_role"
    ).fetchall()
    for new_role, count in rows:
        role = target_to_role.get(new_role)
        if role is not None:
            counts[role] = int(count or 0)
    return counts


def _effective_pressure(con, raw_pressure, state):
    """Applies the acetylcholine novelty bias (see block comment above) to
    each role's raw eligibility-count pressure. Returns (effective_pressure
    dict, diagnostic dict for the event log)."""
    neuromod = _neuromodulators(con)
    acetylcholine = neuromod["acetylcholine"]
    ach_gain = _float(state.get("selection_pressure_ach_novelty_gain"), 0.6)
    historical = _historical_role_graduations(con)
    total_historical = sum(historical.values())
    effective = {}
    novelty_by_role = {}
    for role, pressure in raw_pressure.items():
        if total_historical > 0:
            novelty = 1.0 - (historical.get(role, 0) / total_historical)
        else:
            # No graduation has ever happened for ANY role yet -- neutral,
            # unbiased midpoint rather than an undefined/maximal novelty
            # value with no real history behind it.
            novelty = 0.5
        novelty_by_role[role] = novelty
        effective[role] = pressure * max(0.0, 1.0 + ach_gain * (acetylcholine - 0.5) * novelty)
    diagnostics = {
        "acetylcholine": acetylcholine,
        "gaba": neuromod["gaba"],
        "historical_graduations": historical,
        "novelty_by_role": novelty_by_role,
    }
    return effective, diagnostics


def _role_pressure(con, minimum):
    """Per-role count of candidates that already satisfy this module's own
    graduation-eligibility SQL (see _candidates() above), used as the
    'Bedarfsdruck' input to divisive normalization. A dedicated COUNT query
    per role (not a re-slice of a LIMITed candidate list) so pressure is
    accurate even if a role's true backlog exceeds _candidates()'s own
    per-call limit."""
    pressure = {}
    for role in ELIGIBLE_ROLES:
        rows = _candidates(con, minimum, limit=100000, role_filter=role)
        pressure[role] = len(rows)
    return pressure


def _select_role_by_divisive_normalization(pressure, rnd, sigma=_SIGMA_DEFAULT, temperature=1.0):
    """Returns (selected_role_or_None, shares_dict): one role, chosen via
    Efraimidis-Spirakis weighted sampling where the weight of each role is
    its divisive-normalized share:
    share(role) = pressure(role)**temperature / (sum(pressure**temperature) + sigma).
    Roles with zero pressure are excluded outright (nothing to graduate
    there this cycle regardless of share). selected_role is None if every
    role has zero pressure (shares_dict is then empty too), so the caller
    can always safely unpack a 2-tuple regardless of outcome.

    BRAINSTEM_GRADUATION_NEUROMODULATOR_COUPLING_V1: `temperature` (see the
    module-level block comment above _neuromodulators() for the full
    GABA-grounded derivation) is applied as an EXPONENT on each role's own
    pressure value, before the sigma-normalized share is computed -- unlike
    `sigma` itself (an additive constant shared identically across every
    role, and therefore provably inert to which role wins, see that same
    comment), an exponent genuinely changes the relative gap between a
    dominant and a minority role's share whenever temperature != 1.0.
    temperature=1.0 (the value at GABA's own neutral baseline of 0.5)
    reduces this exactly to the original, unmodified formula."""
    eligible = {role: count for role, count in pressure.items() if count > 0}
    if not eligible:
        return None, {}
    temperature = max(1e-3, temperature)
    powered = {role: count ** temperature for role, count in eligible.items()}
    total = sum(powered.values())
    shares = {role: value / (total + sigma) for role, value in powered.items()}
    keyed = [(rnd.random() ** (1.0 / max(1e-6, share)), role) for role, share in shares.items()]
    keyed.sort(key=lambda x: x[0], reverse=True)
    return keyed[0][1], shares
def _log(con,cycle,hid,old,new,surv,allowed,penalty,reason,decision,details,b,a):
    con.execute("INSERT INTO "+EVENTS+"(created_at,cycle_index,hypothesis_id,old_role,new_role,survival_cycles,critic_allowed,critic_penalty,critic_reason,decision,details,facts_before,facts_after,relations_before,relations_after,questions_before,questions_after) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(_now(),cycle,hid,old,new,surv,1 if allowed else 0,penalty,reason,decision,json.dumps(details,sort_keys=True),b["facts"],a["facts"],b["relations"],a["relations"],b["questions"],a["questions"]))
def run_graduation_cycle(obj=None,cycle_index=None):
    con=resolve_db(obj); ensure_schema(con); st=_read_kv(con,STATE); cycle=_int(cycle_index,_int(st.get("cycle_count"),0)+1); _set(con,"cycle_count",cycle)
    before=_protected(con); warmup=_int(st.get("warmup_cycles"),50); minimum=max(3,_int(st.get("minimum_7d_survivals"),3)); budget=min(1,max(0,_int(st.get("promotion_budget"),1)))
    if str(st.get("enabled","true")).lower()!="true" or cycle<=warmup or budget==0:
        con.commit(); return {"phase":PHASE,"graduated":0,"reason":"disabled_warmup_or_zero_budget","cycle_index":cycle,"protected_unchanged":True}
    graduated=0; decisions=[]
    # BRAINSTEM_DIVISIVE_NORMALIZATION_BUDGET_SHARING_V1 (25 September 2026):
    # pressure/shares are computed ONCE per cycle (a snapshot), matching the
    # fact that `budget` is hard-clamped to at most 1 above -- with budget
    # never exceeding 1, at most a single role-selection draw ever happens
    # per cycle in practice, so recomputing pressure mid-cycle would have no
    # observable effect; the loop below is nonetheless written generally
    # (tracking already-handled ids and re-selecting per remaining budget
    # slot) so it remains correct if that clamp is ever relaxed in the
    # future. random.Random is seeded from the same per-cycle `cycle` index
    # so a given cycle's role selection is itself reproducible/replayable
    # for diagnostics, while still varying cycle-to-cycle.
    import random as _random_module
    _rnd = _random_module.Random("stageb_graduation_role_select:%d" % cycle)
    _pressure = _role_pressure(con, minimum)
    # BRAINSTEM_GRADUATION_NEUROMODULATOR_COUPLING_V1 (28 September 2026):
    # raw _pressure (unchanged, still used below to zero out an
    # unexpectedly-emptied role mid-cycle) is converted to an
    # acetylcholine-biased effective pressure once per cycle, and GABA sets
    # this cycle's temperature exponent -- see the block comment above
    # _neuromodulators() for the full derivation. Both computed once per
    # cycle (matching the pre-existing pressure snapshot's own once-per-
    # cycle scope, since budget remains hard-clamped to at most 1).
    _effective_pressure_snapshot, _neuromod_diagnostics = _effective_pressure(con, _pressure, st)
    _temperature_base = _float(st.get("selection_pressure_temperature_base"), 1.0)
    _gaba_gain = _float(st.get("selection_pressure_gaba_temperature_gain"), 0.5)
    _temperature = _temperature_base + _gaba_gain * (_neuromod_diagnostics["gaba"] - 0.5)
    handled_ids = set()
    con.execute("SAVEPOINT stageb_graduation")
    try:
        while graduated < budget:
            selected_role, shares = _select_role_by_divisive_normalization(
                _effective_pressure_snapshot, _rnd, temperature=_temperature
            )
            if selected_role is None:
                break
            role_candidates = _candidates(con, minimum, limit=1, role_filter=selected_role, exclude_ids=handled_ids)
            if not role_candidates:
                # Pressure said this role had eligible candidates, but a
                # concurrent state change (or an already-handled id this
                # cycle) left none -- do not retry the same role forever;
                # zero its (effective) pressure for this cycle's remaining
                # draws and continue.
                _effective_pressure_snapshot[selected_role] = 0
                continue
            cand = role_candidates[0]
            handled_ids.add(cand["id"])
            allowed,penalty,reason=_critic(con,_float(cand.get("consistency"),0.0)); decision="blocked_by_critic"
            # BRAINSTEM_LEXICAL_LAYER_GRADUATION_ELIGIBILITY_V1: old_role is
            # now read from the candidate row itself (via the "matched_role"
            # alias) instead of being hardcoded, and new_role is looked up
            # from ELIGIBLE_ROLES. Whenever old_role=='uncertain_hypothesis'
            # (the only value that existed before this change), new_role is
            # ALWAYS 'stable_hypothesis' -- identical, unchanged behavior.
            old_role=cand.get("matched_role") or "uncertain_hypothesis"
            new_role=ELIGIBLE_ROLES.get(old_role,"stable_hypothesis")
            if allowed:
                cur=con.execute("UPDATE context_hypotheses SET role=?,updated_at=? WHERE id=? AND role=? AND COALESCE(status,'active')='active'",(new_role,_now(),cand["id"],old_role))
                if cur.rowcount==1: graduated+=1; decision="graduated_to_"+new_role
            after_now=_protected(con)
            if after_now!=before: raise RuntimeError("protected_productive_counts_changed")
            _log(con,cycle,cand["id"],old_role,new_role if decision.startswith("graduated") else old_role,cand["survived"],allowed,penalty,reason,decision,{"budget":budget,"minimum_7d_survivals":minimum,"anchor_consistency":cand.get("consistency"),"divisive_normalization_pressure":_pressure,"divisive_normalization_effective_pressure":_effective_pressure_snapshot,"divisive_normalization_shares":shares,"divisive_normalization_temperature":_temperature,"neuromodulator_diagnostics":_neuromod_diagnostics,"selected_role":selected_role},before,after_now)
            decisions.append({"hypothesis_id":cand["id"],"decision":decision,"survival_cycles":cand["survived"],"critic_reason":reason,"role":old_role})
            # Whether graduated or blocked_by_critic, this specific
            # hypothesis id is already excluded from future draws this
            # cycle via handled_ids above -- the next while-loop iteration
            # re-rolls across all roles' current pressure, so one role
            # being repeatedly blocked by the critic gate cannot prevent
            # other roles' candidates from being tried this same cycle.
        after=_protected(con)
        if after!=before: raise RuntimeError("protected_productive_counts_changed")
        _set(con,"total_graduated",_int(st.get("total_graduated"),0)+graduated); _set(con,"last_graduated",graduated); _set(con,"last_decisions",json.dumps(decisions,sort_keys=True)); _set(con,"fact_promotion","disabled")
        con.execute("RELEASE SAVEPOINT stageb_graduation"); con.commit()
        return {"phase":PHASE,"version":VERSION,"cycle_index":cycle,"graduated":graduated,"budget":budget,"decisions":decisions,"protected_unchanged":True,"fact_promotion":"disabled"}
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_graduation"); con.execute("RELEASE SAVEPOINT stageb_graduation"); con.commit(); raise

def managed_cycle(self,progress=None):
    downstream=None
    try:
        from ki_system import v8_cooperative_core_neuromodulator_sleep_authority_release as m
        downstream=m.managed_cycle(self,progress)
    except Exception as exc: downstream={"status":"downstream_error","error":str(exc)}
    try: result=run_graduation_cycle(self)
    except Exception as exc: result={"phase":PHASE,"status":"error","error":type(exc).__name__+":"+str(exc),"graduated":0}
    return {"phase":PHASE,"downstream_result":downstream,"stageb_graduation_result":result}
def managed_run(self,cycles=1,progress=None): return {"phase":PHASE,"results":[managed_cycle(self,progress) for _ in range(max(1,int(cycles or 1)))]}
def autoload(AutonomousLoop):
    AutonomousLoop.cycle=managed_cycle; AutonomousLoop.run=managed_run; AutonomousLoop.stageb_guarded_hypothesis_graduation=True
    AutonomousLoop.fact_promotion="disabled"; AutonomousLoop.direct_fact_writes="disabled"; AutonomousLoop.direct_relation_writes="disabled"
    return AutonomousLoop
