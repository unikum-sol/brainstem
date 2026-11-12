# -*- coding: utf-8 -*-
"""Stage-B ontology cluster observation (category emergence).

Clusters the graph of promoted relations with Label Propagation, tracks which
clusters reappear across cycles and anchors each cluster's identity to its
prototype, the most central member, instead of Label Propagation's arbitrary
per-cycle label. Clustering runs over already extracted relations rather than
raw episodes: structure is extracted from consolidated regularities
(complementary learning systems). Writes nothing to `ontology`; promotion is
done by v8_stageb_ontology_promotion_release.py.

Literatur: Rosch 1973; Sun et al. 2023; Singh & Schapiro 2026
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
    "overlap_threshold": "0.4",
    # Consecutive-cycle streak required before a cluster becomes eligible
    # for promotion -- same "Bedarf ist noch keine Verbindung" 3-cycle
    # philosophy already used throughout this project (Stage-B graduation,
    # Phase 7d consolidation).
    "stability_streak_required": "3",
    "lp_max_iterations": "20",
    # Engineering hypothesis: higher dopamine tolerates modest membership change.
    # The papers do not specify a Jaccard formula or a universal direction.
    "selection_pressure_dopamine_gain": "0.5",
    "na_size_fractional_remainder": "0.0",
    "na_size_previous_direction": "0.0",
    "effective_min_cluster_size": "2",
    "effective_min_cluster_size_continuous": "2.0",
    "effective_overlap_threshold": "0.4",
    "size_gate_blocked_clusters": "0",

    "clusters_observed_total": "0",
    "clusters_reconfirmed_total": "0",
    "clusters_reset_total": "0",
    # Literatur: Grossman et al. 2022; Aston-Jones & Cohen 2005; Shine et al. 2018; Zerbi et al. 2019; Lee & Kirkwood 2019
    "selection_pressure_serotonin_gain": "0.5",
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
    "na_direction_min_survival_window": "10",
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


def _self_check_schema(con):
    required = {'stageb_ontology_cluster_observation_state': ['key', 'value', 'updated_at'], 'ontology_cluster_stability_state': ['prototype_key', 'member_keys_json', 'streak', 'promoted', 'min_size_eligible']}
    return [table + "." + column for table, columns in required.items()
            for column in columns if column not in _columns(con, table)]


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
            "noradrenaline_at_promotion REAL, promoted_at_cycle INTEGER, retracted_at_cycle INTEGER, "
            "min_size_eligible INTEGER DEFAULT 1)"
        )
    else:
        existing_stability_cols = _columns(con, STABILITY_TABLE)
        for col_name, col_decl in (
            ("noradrenaline_at_promotion", "REAL"),
            ("promoted_at_cycle", "INTEGER"),
            ("retracted_at_cycle", "INTEGER"),
            ("min_size_eligible", "INTEGER DEFAULT 1"),
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
    if "min_size_eligible" not in _columns(con, STABILITY_TABLE):
        missing.append(STABILITY_TABLE + ".min_size_eligible")
    missing.extend(_self_check_schema(con))
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
    """Learn the sign of the noradrenaline -> min_cluster_size coupling from
    promotion/retraction outcomes. Two literature findings disagree on the
    direction, so the sign stays 0 until both outcome groups hold enough
    evidence and differ by more than the configured margin.

    Literatur: Aston-Jones & Cohen 2005; Shine et al. 2018; Zerbi et al. 2019
    """
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
    """Highest in-cluster-degree member is the prototype (Rosch 1973)."""
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

    neuromod = _neuromodulators(con)
    serotonin_gain = _float(state.get("selection_pressure_serotonin_gain"), 0.5)
    na_gain = _float(state.get("selection_pressure_na_gain"), 0.5)
    na_direction_sign = _update_na_direction_sign(con, state, cycle)
    effective_streak_required = max(1, round(
        base_streak_required * (1.0 + serotonin_gain * (0.5 - neuromod["serotonin"]))
    ))
    from ki_system.fractional_control import finite, fractional_integer
    na = max(0.0, min(1.0, finite(neuromod["noradrenaline"], 0.5)))
    na_gain = max(0.0, min(1.0, finite(na_gain, 0.5)))
    size_target = max(2.0, base_min_cluster_size *
                      (1.0 + na_gain * na_direction_sign * (na - 0.5)))
    # Preserve learned direction; never invent evidence or permit singleton categories.
    carry = finite(state.get("na_size_fractional_remainder"), 0.0)
    if finite(state.get("na_size_previous_direction"), 0.0) != na_direction_sign:
        carry = 0.0
    min_cluster_size, next_carry = fractional_integer(size_target, carry, minimum=2)
    dopamine = max(0.0, min(1.0, finite(neuromod["dopamine"], 0.5)))
    dopamine_gain = max(0.0, min(1.0, finite(state.get("selection_pressure_dopamine_gain"), 0.5)))
    base_overlap_threshold = max(0.0, min(1.0, finite(overlap_threshold, 0.4)))
    overlap_threshold = max(0.0, min(1.0, base_overlap_threshold *
                            (1.0 + dopamine_gain * (0.5 - dopamine))))
    _set_kv(con, STATE_TABLE, "effective_overlap_threshold", overlap_threshold)
    _set_kv(con, STATE_TABLE, "effective_min_cluster_size_continuous", size_target)
    _set_kv(con, STATE_TABLE, "effective_min_cluster_size", min_cluster_size)
    _set_kv(con, STATE_TABLE, "na_size_previous_direction", na_direction_sign)

    surfaces, neighbors = _build_graph(con)
    now = _now()

    if not neighbors:
        _set_kv(con, STATE_TABLE, "cycle_count", cycle)
        con.commit()
        return {"status": "stageb_ontology_cluster_observation_no_graph", "cycle_index": cycle}

    rnd = random.Random("stageb_ontology_cluster_lp:%d" % cycle)
    labels = _label_propagation(neighbors, max_iterations, rnd)
    _set_kv(con, STATE_TABLE, "na_size_fractional_remainder", next_carry)
    # Track all structurally valid clusters. NA gates NEW promotions only:
    # a transient size schedule must not masquerade as graph dissolution.
    clusters = _clusters_from_labels(labels, 2)

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

    blocked = 0
    for prototype, member_keys in this_cycle_prototypes.items():
        eligible = int(len(member_keys) >= min_cluster_size)
        blocked += int(not eligible)
        con.execute("UPDATE " + STABILITY_TABLE + " SET min_size_eligible=? WHERE prototype_key=?",
                    (eligible, prototype))
    _set_kv(con, STATE_TABLE, "size_gate_blocked_clusters", blocked)

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
