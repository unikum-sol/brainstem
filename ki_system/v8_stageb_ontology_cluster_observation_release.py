# -*- coding: utf-8 -*-
"""V8 Stage-B Ontology Cluster Observation -- Modul B, Slice 2
(Ontologie-Emergenz, Kategorienbildung).

Full concept: see BrainStem_Relations_Ontology_Questions_Emergence_Concept.md,
Abschnitt 3 (Modul B) and Abschnitt 10 (integration). This is the pure
observation half of Modul B; v8_stageb_ontology_promotion_release.py is the
promotion half.

WHAT THIS MODULE DOES: clusters the graph of already-promoted `relations`
rows (source -> relation -> target) into groups of structurally related
nodes using Label Propagation, tracks which clusters reappear stably across
multiple cycles, and identifies each stable cluster's prototype (highest-
centrality member). It writes NOTHING to `ontology` itself -- that is
v8_stageb_ontology_promotion_release.py's job, once a cluster has proven
stable enough (see Abschnitt 9.1's reconfirmation-based resolution to Label
Propagation's own non-determinism, applied here exactly as that section
already decided).

WHY THIS CLUSTERS OVER `relations`, NOT `facts` (a real design decision,
grounded in the literature rather than left ambiguous)
------------------------------------------------------
The concept document's original Abschnitt 3.2 wording ("mehrere `subject
ist_ein X`-artige Fakten mit aehnlichem Relationstyp") implicitly assumed
`facts.relation` would carry a genuine relation type by the time this
module was built. It does not: every promoted fact's `relation` column
remains the fixed placeholder "observed_as" (see v8_stageb_fact_promotion_
release.py) -- this was the original motivating problem for Relations
Slice 1 in the first place, and fixing it was never in that slice's scope.
`relations` (built by Slice 1), by contrast, DOES carry a genuine,
graph-meaningful edge (source, relation, target) with a real, if currently
simple, relation value.

This choice is independently supported by Complementary Learning Systems
theory: Sun, Advani, Spruston, Saxe & Fitzgerald (2023, Nature
Neuroscience, DOI 10.1038/s41593-023-01382-9) show that neocortical
structure-extraction only benefits generalization when it consolidates
over ALREADY hippocampally-extracted regularities, not raw episodic
traces directly -- unregulated transfer of raw, unstructured material
causes overfitting and HARMS generalization. Singh & Schapiro (2026, Phil.
Trans. R. Soc. B, DOI 10.1098/rstb.2025.0243) similarly describe a
division of labor in which structure learning (this module's job) operates
on a slower, less pattern-separated pathway that extracts regularities
ACROSS experiences, distinct from and downstream of the fast, individual-
episode-encoding pathway. Applied here: `relations` rows are themselves
already the product of Slice 1's own multi-cycle consolidation/graduation
process (i.e. already-extracted regularities, analogous to consolidated
traces) -- clustering over them, rather than over raw, unstructured facts
still carrying a meaningless placeholder relation, is the more defensible,
literature-grounded choice, not an arbitrary one.

Node identity in the graph is built from `relations.source`/`.target` text
directly (case-insensitively normalized), NOT from parsing any specific
relation-type string such as "ist_ein" -- Slice 1 never produces such a
value (it only ever produces the direction-neutral placeholder
'associated_with' once a direction is resolved, see Abschnitt 2.4.5).
Categories therefore emerge purely from graph CONNECTIVITY STRUCTURE (which
nodes are linked to which), never from grammar or vocabulary -- consistent
with this project's "keine Wortlisten, keine Grammatik" principle applied
at the ontology level.

MECHANISM
---------
1. Build an undirected graph: nodes = distinct, case-insensitively
   normalized `relations.source`/`.target` strings; edges = one per
   `relations` row (regardless of its `relation` value -- the type of
   relation is not currently used as an edge weight or filter, matching
   the concept document's own framing of Label Propagation as a purely
   structural, unsupervised method).
2. Run Label Propagation (Zhou et al.; see Hamilton's graph-statistics
   chapters, already accepted in this project's Abschnitt 2.3/9.1 as a
   non-gradient, fully transparent community-detection method): each node
   iteratively adopts the label held by the majority of its neighbors,
   ties broken deterministically, for a bounded number of iterations or
   until convergence.
3. Within each resulting cluster (size >= min_cluster_size), the member
   with the highest in-cluster degree (most edges to other cluster
   members) is marked the PROTOTYPE -- the Rosch (1971/1973) prototype-
   theory analogue already justified in Abschnitt 3.1: categories have a
   graded structure around a typical member, not a sharp defining
   boundary.
4. STABILITY (resolving Label Propagation's own non-determinism, per
   Abschnitt 9.1, decided before this module was built): each cluster is
   identified ACROSS cycles by its prototype's node key (not by LP's own
   arbitrary per-cycle label, which is not stable run-to-run). If this
   cycle's member set for a given prototype has Jaccard overlap >=
   overlap_threshold with that same prototype's LAST recorded member set,
   its stability streak increments; otherwise the streak resets. A
   prototype anchor from a previous cycle that does not reappear as a
   prototype at all this cycle has its streak explicitly reset to 0 (a
   signal this module's own promotion counterpart uses to trigger
   retraction of anything already promoted under that anchor).
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from typing import Any, Dict, List, Tuple

PHASE = "stageb_ontology_cluster_observation_release"
STATE_TABLE = "stageb_ontology_cluster_observation_state"
NODE_TABLE = "ontology_node_cluster_state"
STABILITY_TABLE = "ontology_cluster_stability_state"

DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    # A category needs a prototype plus at least this many other members
    # to be considered a candidate at all (a "cluster" of exactly 1 node
    # is not a category).
    "min_cluster_size": "2",
    # Jaccard-overlap threshold (0..1) for "the same cluster reappeared".
    #
    # BRAINSTEM_ONTOLOGY_EMERGENCE_SLICE2_CALIBRATION_V1 (25 September 2026)
    #
    # Lowered from the original, uncalibrated starting value of 0.6 to 0.4,
    # based on a controlled synthetic-graph experiment (full derivation in
    # the Slice 2 Review Report shipped with this delivery), directly
    # exercising the real, unmodified _label_propagation() and _jaccard()
    # functions from this module. Two ground-truth categories (Rosch's own
    # classic domains: Tier, Fahrzeug, Moebel) were built as a
    # prototype-plus-cross-linked graph with realistic cross-category noise
    # edges (mirroring the level of spurious co-occurrence PMI-gated
    # relations can still let through), then Label Propagation was run for
    # 60 cycles on this genuinely UNCHANGED graph.
    #
    # Key finding: because Label Propagation's own tie-breaking/shuffle
    # order varies cycle to cycle (its well-known non-determinism, see this
    # module's own docstring), the resulting member-set churn alone caused
    # false streak resets -- i.e. a genuinely stable, unchanged category
    # incorrectly treated as "not the same cluster reappearing" -- at a
    # rate of 28.7% of all cycle transitions under the original default of
    # 0.6, versus only 3.6% at 0.3, 6.6% at 0.4, and 9.0% at 0.5. At a false
    # reset rate above ~25%, a cluster needing 3 CONSECUTIVE reconfirming
    # cycles (stability_streak_required) to become promotion-eligible could
    # struggle to ever accumulate that streak under realistic noise,
    # indefinitely blocking promotion of genuinely stable categories.
    #
    # A companion test (gradual, one-member-at-a-time erosion of a genuine
    # category) found NO measurable recall cost from lowering this
    # threshold: at every tested value from 0.3 up to 0.6, gradual,
    # partial erosion was not reliably caught at all via this
    # consecutive-cycle Jaccard comparison (only a SUDDEN, complete
    # dissolution -- where the prototype vanishes from the graph entirely --
    # is reliably and immediately detected, and that detection is
    # independent of this threshold's value, since it is triggered by the
    # prototype's absence, not by a low Jaccard score). Given precision
    # improves substantially at lower values with no measured recall
    # tradeoff in this regime, 0.4 was chosen as a defensible middle ground
    # (meaningfully better than the original 0.6, without moving to the
    # most extreme low end tested).
    #
    # IMPORTANT, EXPLICIT CAVEAT (matching Slice 1's own calibration
    # caveat): this synthetic graph (19 nodes, three ground-truth
    # categories) is far smaller and structurally simpler than a real
    # production relations graph would be. This value is a validated,
    # defensible STARTING point given the evidence available, not a final,
    # production-calibrated number -- and going too low is not free either:
    # an unexamined risk (not directly measured in this experiment) is that
    # a very low threshold could cause two genuinely DIFFERENT clusters
    # that transiently share some members to be incorrectly treated as
    # "the same" cluster reappearing. Recalibrate against real production
    # relations-graph data before relying on this value long-term.
    "overlap_threshold": "0.4",
    # Consecutive-cycle streak required before a cluster becomes eligible
    # for promotion -- same "Bedarf ist noch keine Verbindung" 3-cycle
    # philosophy already used throughout this project (Stage-B graduation,
    # Phase 7d consolidation).
    "stability_streak_required": "3",
    "lp_max_iterations": "20",
    "clusters_observed_total": "0",
    "clusters_reconfirmed_total": "0",
    "clusters_reset_total": "0",
    # BRAINSTEM_ONTOLOGY_NEUROMODULATOR_COUPLING_V1 (28 September 2026)
    #
    # Root cause: this module never read the shared neuromodulator
    # snapshot at all -- unlike every other Stage-B module in this chain
    # (gap_detection, question_promotion, phase0b_relational_binding,
    # contradiction_detection, hypothesis_revision, guarded_hypothesis_
    # graduation), all of which couple at least one of their own
    # calibrated thresholds to a neuromodulator by this point in the
    # project.
    #
    # (1) Serotonin -> stability_streak_required. Grounded in a targeted
    # literature search specifically for this module (not the previously
    # only-general, un-cited serotonin/consolidation intuition): Grossman,
    # Bari & Cohen (2022, Current Biology 32(6):1339-1349), "Serotonin
    # neurons modulate learning rate through uncertainty" -- dorsal raphe
    # serotonin neurons track BOTH expected and unexpected uncertainty in
    # a changing environment, and their activity directly controls how
    # quickly learning adapts to new evidence (a real, causal "how much do
    # I trust this pattern's stability" meta-learning signal; reversible
    # inhibition of these neurons was shown to impair exactly this
    # adaptation). How many consecutive reconfirming cycles a cluster
    # needs before being trusted as "stable enough to promote" is exactly
    # this same question applied to this module's own graph-clustering
    # domain. High serotonin (environment assessed as stable/low-
    # uncertainty) LOWERS the required streak; low serotonin (high
    # perceived uncertainty) RAISES it -- the same direction already used
    # for this project's other serotonin coupling this session
    # (v8_stageb_gap_detection_release.py's own habituation threshold).
    #
    # (2) Noradrenaline -> min_cluster_size, SELF-REGULATING DIRECTION
    # (BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1, 28 September
    # 2026).
    #
    # BACKGROUND: this coupling originally reused, mechanically, the same
    # symmetric formula and Aston-Jones & Cohen (2005) Adaptive Gain
    # Theory direction already applied to every other existence-gate
    # threshold in this chain (high noradrenaline -> lower bar, matching
    # exploratory disengagement). On explicit review, this was found to
    # be an ANALOGY, not a mechanistically grounded choice for THIS
    # specific parameter: Aston-Jones & Cohen describe generic behavioral
    # exploration/exploitation, not graph topology. A targeted follow-up
    # search found a directly conflicting, more mechanistically specific
    # literature for the actual object this threshold governs (a graph-
    # clustering existence gate): Shine, Aburn, Breakspear & Poldrack
    # (2018, eLife 7:e31130) show, in an explicit network model, that
    # rising neural gain (the level at which noradrenaline acts) drives a
    # real topological transition from a SEGREGATED regime (many small,
    # specialized modules) to an INTEGRATED regime (few, large, densely
    # interconnected modules) -- the opposite prediction for this specific
    # parameter: at high noradrenaline, small clusters would be
    # comparatively MORE likely to be noise (everything tends to merge),
    # arguing for a HIGHER bar, not a lower one. Zerbi et al. (2019,
    # Neuron 103(4):702-718) confirm this causally (chemogenetic LC
    # activation in mice measurably increases whole-brain connectivity).
    #
    # Rather than picking either theory a priori, this module now applies
    # this project's own existing sliding-threshold-homeostasis philosophy
    # (Lee & Kirkwood 2019, BCM-style; already implemented project-wide in
    # v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release.py
    # for a different set of parameters) to let the DIRECTION of this
    # specific coupling be decided by this module's own real, already-
    # recorded promotion/retraction outcomes, rather than by either paper
    # alone: see _update_na_direction_sign() below for the concrete
    # mechanism. Until enough real outcome evidence exists, the direction
    # sign starts at exactly 0.0 (no modulation at all, min_cluster_size
    # stays at its unmodulated base value regardless of noradrenaline) --
    # a deliberately more honest starting point than silently assuming
    # either paper's direction without evidence specific to this
    # project's own real clustering behavior.
    #
    # overlap_threshold is deliberately NOT coupled here -- no
    # sufficiently specific, well-grounded neuromodulator mechanism was
    # found for "how much cross-cycle member churn still counts as the
    # same cluster reappearing" during this same literature search;
    # coupling it to GABA's own gain-sharpening role (used elsewhere in
    # this project, e.g. guarded_hypothesis_graduation's own temperature
    # exponent) would have been a forced, unevidenced analogy rather than
    # a grounded one. Left disclosed and open for separate discussion.
    #
    # ontology_promotion_budget (in v8_stageb_ontology_promotion_
    # release.py) is coupled to acetylcholine separately in that module's
    # own DEFAULTS -- promoting a stable cluster into a durable ontology
    # row is that module's own structural-encoding decision, distinct
    # from this module's own existence/stability gates.
    #
    # Both factors below are exactly inert (no behavior change from
    # before this delivery) at their respective messenger's neutral
    # baseline of 0.5.
    "selection_pressure_serotonin_gain": "0.5",
    # selection_pressure_na_gain now controls only the MAGNITUDE of the
    # min_cluster_size modulation; the SIGN (direction) is supplied
    # separately by na_direction_sign below, learned from real outcomes
    # rather than assumed -- see _update_na_direction_sign()'s own
    # docstring and this module's updated comment above DEFAULTS.
    "selection_pressure_na_gain": "0.5",
    # Learned direction sign for the noradrenaline -> min_cluster_size
    # coupling: -1.0 = Aston-Jones/Cohen direction (high NA -> lower bar),
    # +1.0 = Shine et al./Zerbi et al. direction (high NA -> higher bar),
    # 0.0 = no modulation (default, until enough real evidence exists).
    # Recomputed every cycle by _update_na_direction_sign(); not intended
    # to be hand-edited (though, like every other STATE_TABLE value in
    # this project, nothing prevents it).
    "na_direction_sign": "0.0",
    # Minimum number of promoted clusters in EACH of the two outcome
    # groups (retracted-at-least-once vs. survived-without-retraction for
    # at least na_direction_min_survival_window cycles) before the
    # direction sign above is allowed to commit to either non-zero value
    # -- matches this project's universal "do not trust a small sample"
    # convention (e.g. Phase 0's min_observations, phase0b's
    # min_pair_count).
    "na_direction_min_evidence_per_group": "5",
    # Minimum absolute difference between the two groups' average
    # noradrenaline-at-promotion values before committing to a direction
    # at all (avoids flip-flopping the sign on noise-level differences).
    "na_direction_margin": "0.05",
    # How many real cycles must pass, since a cluster's own first
    # promotion, without it being retracted, before that cluster counts
    # as genuine "surviving" evidence (rather than merely "has not yet
    # had a fair chance to fail").
    "na_direction_min_survival_window": "10",
    # Diagnostic snapshot of the last direction-sign computation,
    # persisted purely for transparency/audit (this project's own
    # established convention of never leaving a learned decision
    # unexplainable) -- recomputed, never hand-edited.
    "na_direction_retracted_avg_na": "",
    "na_direction_surviving_avg_na": "",
    "na_direction_retracted_count": "0",
    "na_direction_surviving_count": "0",
}


def _now() -> int:
    return int(time.time())


def _table_exists(con, table) -> bool:
    return con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return set()
    return {row[1] for row in con.execute("PRAGMA table_info(" + table + ")").fetchall()}


def ensure_schema(con) -> bool:
    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    if not _table_exists(con, NODE_TABLE):
        con.execute(
            "CREATE TABLE " + NODE_TABLE + " ("
            "node_key TEXT PRIMARY KEY, surface_form TEXT, current_cluster_label TEXT, "
            "degree INTEGER DEFAULT 0, updated_at INTEGER)"
        )
    if not _table_exists(con, STABILITY_TABLE):
        con.execute(
            "CREATE TABLE " + STABILITY_TABLE + " ("
            "prototype_key TEXT PRIMARY KEY, prototype_surface TEXT, member_keys_json TEXT, "
            "member_count INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, promoted INTEGER DEFAULT 0, "
            "first_seen_cycle INTEGER, last_seen_cycle INTEGER, updated_at INTEGER, "
            "noradrenaline_at_promotion REAL, promoted_at_cycle INTEGER, retracted_at_cycle INTEGER)"
        )
    else:
        # BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1: defensive
        # ALTER for a database that already has this table from before
        # this delivery -- see this module's own comment above DEFAULTS
        # for the full rationale behind these three new columns.
        existing_stability_cols = _columns(con, STABILITY_TABLE)
        for col_name, col_decl in (
            ("noradrenaline_at_promotion", "REAL"),
            ("promoted_at_cycle", "INTEGER"),
            ("retracted_at_cycle", "INTEGER"),
        ):
            if col_name not in existing_stability_cols:
                con.execute("ALTER TABLE " + STABILITY_TABLE + " ADD COLUMN " + col_name + " " + col_decl)
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    missing = [t for t in (STATE_TABLE, NODE_TABLE, STABILITY_TABLE) if not _table_exists(con, t)]
    if "source_cluster_key" not in _columns(con, "ontology"):
        missing.append("ontology.source_cluster_key")
    if missing:
        raise RuntimeError("stageb ontology cluster observation schema missing: " + repr(missing))
    return True


def _read_kv(con, table) -> Dict[str, str]:
    if not _table_exists(con, table):
        return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())


def _set_kv(con, table, key, value):
    con.execute(
        "INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
        (key, str(value), _now()),
    )


def _int(v, d=0) -> int:
    try:
        return int(float(v))
    except Exception:
        return d


def _float(v, d=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return d


def _neuromodulators(con) -> Dict[str, float]:
    """Identical access pattern to every other module in this chain that
    reads the shared six-core neuromodulator snapshot -- no new messenger
    responsibility introduced."""
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


def _update_na_direction_sign(con, state: Dict[str, str], cycle: int) -> float:
    """BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1 (28 September
    2026): decides, from this module's own real, already-recorded
    promotion/retraction history -- not from either competing paper alone
    (see this module's own comment above DEFAULTS for the full
    background) -- which of two directions the noradrenaline ->
    min_cluster_size coupling should currently take:
      -1.0 = Aston-Jones & Cohen (2005) direction: high noradrenaline at
             a cluster's promotion time predicts SURVIVAL (no later
             retraction) more than low noradrenaline does -> high NA
             should LOWER the bar.
      +1.0 = Shine et al. (2018)/Zerbi et al. (2019) direction: high
             noradrenaline at promotion time predicts eventual RETRACTION
             (dissolution) more than low noradrenaline does -> high NA
             should RAISE the bar.
       0.0 = not enough evidence yet, or the two groups' average
             noradrenaline-at-promotion values are too close to trust a
             direction (within na_direction_margin) -- the safe,
             no-modulation default.

    Two groups are read directly from STABILITY_TABLE, both requiring a
    real, already-elapsed outcome (not a prediction): "retracted" =
    clusters ever dissolved at least once after their own first
    promotion (retracted_at_cycle IS NOT NULL); "surviving" = clusters
    promoted at least na_direction_min_survival_window real cycles ago
    that have NEVER been retracted since. A minimum count in EACH group
    (na_direction_min_evidence_per_group) is required before either
    non-zero sign is permitted, matching this project's universal "do not
    trust a small sample" convention.

    Diagnostic values (group averages/counts) are persisted every call,
    purely for audit transparency, regardless of whether a direction is
    committed to."""
    min_evidence = max(1, _int(state.get("na_direction_min_evidence_per_group"), 5))
    margin = max(0.0, _float(state.get("na_direction_margin"), 0.05))
    survival_window = max(1, _int(state.get("na_direction_min_survival_window"), 10))

    retracted_row = con.execute(
        "SELECT COUNT(*), AVG(noradrenaline_at_promotion) FROM " + STABILITY_TABLE + " "
        "WHERE retracted_at_cycle IS NOT NULL AND noradrenaline_at_promotion IS NOT NULL"
    ).fetchone()
    surviving_row = con.execute(
        "SELECT COUNT(*), AVG(noradrenaline_at_promotion) FROM " + STABILITY_TABLE + " "
        "WHERE retracted_at_cycle IS NULL AND promoted_at_cycle IS NOT NULL "
        "AND noradrenaline_at_promotion IS NOT NULL AND (? - promoted_at_cycle) >= ?",
        (cycle, survival_window),
    ).fetchone()

    retracted_count = int(retracted_row[0] or 0)
    surviving_count = int(surviving_row[0] or 0)
    retracted_avg = retracted_row[1]
    surviving_avg = surviving_row[1]

    sign = 0.0
    if (retracted_count >= min_evidence and surviving_count >= min_evidence
            and retracted_avg is not None and surviving_avg is not None):
        diff = float(retracted_avg) - float(surviving_avg)
        if diff > margin:
            sign = 1.0
        elif diff < -margin:
            sign = -1.0

    _set_kv(con, STATE_TABLE, "na_direction_sign", sign)
    _set_kv(con, STATE_TABLE, "na_direction_retracted_avg_na",
            "" if retracted_avg is None else round(float(retracted_avg), 6))
    _set_kv(con, STATE_TABLE, "na_direction_surviving_avg_na",
            "" if surviving_avg is None else round(float(surviving_avg), 6))
    _set_kv(con, STATE_TABLE, "na_direction_retracted_count", retracted_count)
    _set_kv(con, STATE_TABLE, "na_direction_surviving_count", surviving_count)
    return sign


def _node_key(surface: str) -> str:
    return (surface or "").strip().lower()[:180]


def _build_graph(con) -> Tuple[Dict[str, str], Dict[str, set]]:
    """Returns (node_key -> a representative original-case surface form,
    node_key -> set of neighbor node_keys), built from every current
    `relations` row. Self-loops (source == target after normalization,
    which should not occur given Slice 1's own pair-identity rules, but
    guarded here defensively) are skipped."""
    surfaces: Dict[str, str] = {}
    neighbors: Dict[str, set] = {}
    if not _table_exists(con, "relations"):
        return surfaces, neighbors
    rows = con.execute("SELECT source, target FROM relations WHERE source IS NOT NULL AND target IS NOT NULL").fetchall()
    for source, target in rows:
        a_key, b_key = _node_key(source), _node_key(target)
        if not a_key or not b_key or a_key == b_key:
            continue
        surfaces.setdefault(a_key, source.strip()[:180])
        surfaces.setdefault(b_key, target.strip()[:180])
        neighbors.setdefault(a_key, set()).add(b_key)
        neighbors.setdefault(b_key, set()).add(a_key)
    return surfaces, neighbors


def _label_propagation(neighbors: Dict[str, set], max_iterations: int, rnd: random.Random) -> Dict[str, str]:
    """Standard asynchronous Label Propagation (Zhou et al.; see Hamilton's
    graph-statistics chapters). Each node starts with its own key as its
    label; on each iteration (processed in a per-iteration randomized
    order, matching the conventional asynchronous-LP formulation and this
    project's existing use of a per-cycle-seeded random.Random for
    reproducible-but-varying behavior), a node adopts whichever label is
    held by the plurality of its neighbors, ties broken by the
    alphabetically smallest label for full determinism given a tie. Stops
    early if no label changes in a full pass."""
    labels = {node: node for node in neighbors}
    nodes = list(neighbors.keys())
    for _ in range(max(1, max_iterations)):
        rnd.shuffle(nodes)
        changed = False
        for node in nodes:
            neighbor_labels = [labels[n] for n in neighbors.get(node, ()) if n in labels]
            if not neighbor_labels:
                continue
            counts: Dict[str, int] = {}
            for lbl in neighbor_labels:
                counts[lbl] = counts.get(lbl, 0) + 1
            best_count = max(counts.values())
            candidates = sorted(lbl for lbl, c in counts.items() if c == best_count)
            new_label = candidates[0]
            if new_label != labels[node]:
                labels[node] = new_label
                changed = True
        if not changed:
            break
    return labels


def _clusters_from_labels(labels: Dict[str, str], min_size: int) -> List[List[str]]:
    grouped: Dict[str, List[str]] = {}
    for node, label in labels.items():
        grouped.setdefault(label, []).append(node)
    return [members for members in grouped.values() if len(members) >= min_size]


def _prototype_of(cluster_members: List[str], neighbors: Dict[str, set]) -> str:
    """Highest in-cluster-degree member is the prototype (Rosch 1971/1973
    prototype-theory analogue, Abschnitt 3.1). Ties broken by
    alphabetically smallest node key for determinism."""
    member_set = set(cluster_members)
    best_node, best_degree = None, -1
    for node in sorted(cluster_members):
        degree = len(neighbors.get(node, set()) & member_set)
        if degree > best_degree:
            best_node, best_degree = node, degree
    return best_node


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def observe_ontology_clusters(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_ontology_cluster_observation_disabled"}

    base_min_cluster_size = max(2, _int(state.get("min_cluster_size"), 2))
    base_streak_required = max(1, _int(state.get("stability_streak_required"), 3))
    overlap_threshold = _float(state.get("overlap_threshold"), 0.6)
    max_iterations = max(1, _int(state.get("lp_max_iterations"), 20))
    cycle = _int(state.get("cycle_count"), 0) + 1

    # BRAINSTEM_ONTOLOGY_NEUROMODULATOR_COUPLING_V1 /
    # BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1: see DEFAULTS'
    # own comments for the full derivation. The serotonin factor is
    # exactly 1.0 (no behavior change) at serotonin's own neutral
    # baseline of 0.5. The noradrenaline factor is exactly 1.0 (no
    # modulation at all) whenever na_direction_sign is still 0.0 (the
    # default, until this module's own real promotion/retraction outcome
    # evidence earns a direction -- see _update_na_direction_sign()).
    neuromod = _neuromodulators(con)
    serotonin_gain = _float(state.get("selection_pressure_serotonin_gain"), 0.5)
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    na_direction_sign = _update_na_direction_sign(con, state, cycle)
    effective_streak_required = max(1, round(
        base_streak_required * (1.0 + serotonin_gain * (0.5 - neuromod["serotonin"]))
    ))
    min_cluster_size = max(2, round(
        base_min_cluster_size * (1.0 + na_gain * na_direction_sign * (neuromod["noradrenaline"] - 0.5))
    ))

    surfaces, neighbors = _build_graph(con)
    now = _now()

    if not neighbors:
        _set_kv(con, STATE_TABLE, "cycle_count", cycle)
        con.commit()
        return {"status": "stageb_ontology_cluster_observation_no_graph", "cycle_index": cycle}

    rnd = random.Random("stageb_ontology_cluster_lp:%d" % cycle)
    labels = _label_propagation(neighbors, max_iterations, rnd)
    clusters = _clusters_from_labels(labels, min_cluster_size)

    # Persist current per-node cluster-label snapshot (informational, read
    # by diagnostics; not itself the stability anchor -- see module
    # docstring on why the prototype key, not LP's own arbitrary label, is
    # used as the cross-cycle anchor).
    for node, label in labels.items():
        con.execute(
            "INSERT INTO " + NODE_TABLE + "(node_key,surface_form,current_cluster_label,degree,updated_at) "
            "VALUES(?,?,?,?,?) ON CONFLICT(node_key) DO UPDATE SET "
            "surface_form=excluded.surface_form,current_cluster_label=excluded.current_cluster_label,"
            "degree=excluded.degree,updated_at=excluded.updated_at",
            (node, surfaces.get(node, node), label, len(neighbors.get(node, ())), now),
        )

    this_cycle_prototypes = {}
    for members in clusters:
        prototype = _prototype_of(members, neighbors)
        member_keys = sorted(members)
        this_cycle_prototypes[prototype] = member_keys

    reconfirmed = 0
    newly_observed = 0
    reset_count = 0

    # Reconfirm or newly record every prototype seen THIS cycle.
    for prototype, member_keys in this_cycle_prototypes.items():
        existing = con.execute(
            "SELECT member_keys_json, streak, first_seen_cycle FROM " + STABILITY_TABLE + " WHERE prototype_key=?",
            (prototype,),
        ).fetchone()
        member_set = set(member_keys)
        if existing:
            prev_members_json, prev_streak, first_seen_cycle = existing
            try:
                prev_members = set(json.loads(prev_members_json or "[]"))
            except Exception:
                prev_members = set()
            overlap = _jaccard(member_set, prev_members)
            new_streak = (int(prev_streak or 0) + 1) if overlap >= overlap_threshold else 1
            if new_streak > 1:
                reconfirmed += 1
            con.execute(
                "UPDATE " + STABILITY_TABLE + " SET member_keys_json=?, member_count=?, streak=?, "
                "last_seen_cycle=?, updated_at=? WHERE prototype_key=?",
                (json.dumps(member_keys), len(member_keys), new_streak, cycle, now, prototype),
            )
        else:
            newly_observed += 1
            con.execute(
                "INSERT INTO " + STABILITY_TABLE + "(prototype_key,prototype_surface,member_keys_json,"
                "member_count,streak,promoted,first_seen_cycle,last_seen_cycle,updated_at) "
                "VALUES(?,?,?,?,?,0,?,?,?)",
                (prototype, surfaces.get(prototype, prototype), json.dumps(member_keys),
                 len(member_keys), 1, cycle, cycle, now),
            )

    # Any PREVIOUSLY-tracked prototype that did not reappear as a
    # prototype at all this cycle has its streak explicitly reset to 0 --
    # the signal v8_stageb_ontology_promotion_release.py uses to retract
    # anything already promoted under that anchor (cluster dissolution).
    previously_tracked = con.execute(
        "SELECT prototype_key FROM " + STABILITY_TABLE + " WHERE streak > 0"
    ).fetchall()
    for (prototype_key,) in previously_tracked:
        if prototype_key not in this_cycle_prototypes:
            con.execute(
                "UPDATE " + STABILITY_TABLE + " SET streak=0, updated_at=? WHERE prototype_key=?",
                (now, prototype_key),
            )
            reset_count += 1

    # BRAINSTEM_ONTOLOGY_NEUROMODULATOR_COUPLING_V1: the modulated streak
    # requirement is persisted under its OWN, distinct derived key --
    # deliberately NOT overwriting the calibrated base
    # "stability_streak_required" value itself, which would otherwise
    # compound across cycles (each cycle's modulation would apply on top
    # of the PREVIOUS cycle's already-modulated value instead of the
    # stable, inspectable base). v8_stageb_ontology_promotion_release.py
    # reads this derived key (falling back to the base key if absent, for
    # defensiveness against an older database).
    _set_kv(con, STATE_TABLE, "effective_stability_streak_required", effective_streak_required)
    _set_kv(con, STATE_TABLE, "cycle_count", cycle)
    _set_kv(con, STATE_TABLE, "clusters_observed_total",
            _int(state.get("clusters_observed_total"), 0) + len(clusters))
    _set_kv(con, STATE_TABLE, "clusters_reconfirmed_total",
            _int(state.get("clusters_reconfirmed_total"), 0) + reconfirmed)
    _set_kv(con, STATE_TABLE, "clusters_reset_total",
            _int(state.get("clusters_reset_total"), 0) + reset_count)
    con.commit()

    return {
        "status": "stageb_ontology_cluster_observation_cycle",
        "cycle_index": cycle,
        "graph_nodes": len(neighbors),
        "clusters_found": len(clusters),
        "newly_observed": newly_observed,
        "reconfirmed": reconfirmed,
        "reset_to_zero": reset_count,
    }


def _db(loop):
    memory = getattr(loop, "mem", None) or getattr(loop, "memory", None) or getattr(loop, "db", None)
    connection = getattr(memory, "db", None) or getattr(memory, "conn", None) or memory
    if not hasattr(connection, "execute"):
        raise RuntimeError("sqlite connection not found")
    return connection


_PREV_CYCLE = None
_PREV_RUN = None


def managed_cycle(self, progress=None):
    result_prev = _PREV_CYCLE(self, progress) if _PREV_CYCLE is not None else \
        {"status": "stageb_ontology_cluster_observation_no_previous_cycle"}
    try:
        con = _db(self)
        result = observe_ontology_clusters(con)
    except Exception as exc:
        result = {"status": "stageb_ontology_cluster_observation_error",
                  "error": type(exc).__name__ + ":" + str(exc)}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_ontology_cluster_observation_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_ontology_cluster_observation_release = True
    AutonomousLoop.no_word_blacklists = True
    return AutonomousLoop
