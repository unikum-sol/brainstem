# -*- coding: utf-8 -*-
"""V8 Stage-B Ontology Promotion -- Modul B, Slice 2 (Ontologie-Emergenz).

Full concept: see BrainStem_Relations_Ontology_Questions_Emergence_Concept.md,
Abschnitt 3 (Modul B) and Abschnitt 10 (integration).

Reads clusters recorded as stable (streak >= stability_streak_required) by
v8_stageb_ontology_cluster_observation_release.py and promotes each
non-prototype member of a newly-stable cluster into the `ontology` table as
a `child -> parent` row, with the cluster's prototype as `parent`. Retracts
(deletes) previously-promoted rows again if that cluster's own observation
streak is later reset to 0 (cluster dissolved) -- the ontology-level
equivalent of the retraction-on-reversal guarantee already implemented for
facts (v8_stageb_fact_promotion_release.py) and relations
(v8_stageb_relation_promotion_release.py).

`relation` is written as the fixed, explicit placeholder literal 'is_a' --
NOT a linguistically parsed or inferred label. This deliberately mirrors
fact promotion's own honest use of the placeholder 'observed_as': the
system has structurally identified a graded group-membership relationship
via graph connectivity (Label Propagation) and centrality (prototype
selection), but has NOT parsed, inferred, or been given any actual
linguistic category name or relation type. Labeling this as anything more
specific than 'is_a' would overstate what the mechanism has actually
established, and would risk smuggling a hidden, hand-authored grammar rule
into a system whose explicit, non-negotiable principle is "keine
Wortlisten, keine Grammatik". Confidence, not the relation label, carries
the graded, Rosch-style "how typical/central is this membership" signal.

BUDGET: this module has its OWN, independent per-cycle promotion budget
(`ontology_promotion_budget`), deliberately NOT shared with hypothesis
graduation's `promotion_budget` (see v8_stageb_guarded_hypothesis_
graduation_release.py's own BRAINSTEM_DIVISIVE_NORMALIZATION_BUDGET_
SHARING_V1 comment for the detailed reasoning): a direct audit confirmed
there is no actual shared scarce resource between hypothesis graduation
and ontology-cluster promotion in this architecture -- ontology candidates
are downstream of already-promoted `relations` rows and compete for
nothing that hypothesis graduation also needs. Introducing an artificial
shared budget between two mechanisms that do not actually compete would
add complexity without preventing any real starvation risk, so this
module's budget is deliberately its own, separate constant.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List

PHASE = "stageb_ontology_promotion_release"
STATE_TABLE = "stageb_ontology_promotion_state"
EVENTS_TABLE = "stageb_ontology_promotion_events"
STABILITY_TABLE = "ontology_cluster_stability_state"
RELATION_LABEL = "is_a"

DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    # How many newly-stable CLUSTERS (not child-rows -- one cluster with N
    # children still counts as a single promotion event producing N rows
    # atomically) may be promoted per real cycle. Deliberately its own,
    # independent constant -- see module docstring.
    "ontology_promotion_budget": "1",
    "clusters_promoted_total": "0",
    "clusters_retracted_total": "0",
    "child_rows_promoted_total": "0",
    # BRAINSTEM_ONTOLOGY_PROMOTION_NEUROMODULATOR_COUPLING_V1 (28 September
    # 2026)
    #
    # Root cause: this module never read the shared neuromodulator
    # snapshot at all. Coupled to acetylcholine using the same project-
    # internal convention already reused twice this session (v8_stageb_
    # guarded_hypothesis_graduation_release.py's own acetylcholine-novelty
    # pressure boost; v8_stageb_hypothesis_revision_release.py's own
    # acetylcholine-modulated revision_budget) -- v8_phase6a_
    # neuromodulated_sleep_replay_and_meta_plasticity_release.py's own
    # formula already ties acetylcholine directly to "revision_bias",
    # this project's own structural-revision/structural-encoding signal.
    # Promoting a stable cluster into a durable ontology row is exactly
    # this kind of structural-encoding decision (a NEW category is being
    # committed to the durable knowledge structure) -- so high
    # acetylcholine modestly raises this module's own effective
    # promotion budget, low acetylcholine modestly lowers it, mirroring
    # hypothesis_revision's own established direction and magnitude for
    # the same messenger. The hard on/off switch (budget==0 disables
    # promotion entirely) remains governed only by the raw, unmodulated
    # base value, exactly like hypothesis_revision's own convention.
    "selection_pressure_ach_gain": "0.6",
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
    # Defense-in-depth, mirroring the exact convention already established
    # by v8_stageb_relation_promotion_release.py's own ensure_schema(): add
    # the columns this module needs itself if missing, in addition to them
    # already being mirrored into db_bootstrap.py's central SCHEMA_TABLES.
    if _table_exists(con, "ontology"):
        cols = _columns(con, "ontology")
        if "source_cluster_key" not in cols:
            con.execute("ALTER TABLE ontology ADD COLUMN source_cluster_key TEXT")
        if "source_relation_ids" not in cols:
            con.execute("ALTER TABLE ontology ADD COLUMN source_relation_ids TEXT")
    # BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1 (28 September
    # 2026): defense-in-depth mirror of the same three columns
    # v8_stageb_ontology_cluster_observation_release.py's own
    # ensure_schema() already adds to STABILITY_TABLE (that module owns
    # this table's schema; this module also writes to it at promotion/
    # retraction time, matching the same cross-module column-write
    # convention already used for reading_queue's per-phase columns).
    if _table_exists(con, STABILITY_TABLE):
        stability_cols = _columns(con, STABILITY_TABLE)
        for col_name, col_decl in (
            ("noradrenaline_at_promotion", "REAL"),
            ("promoted_at_cycle", "INTEGER"),
            ("retracted_at_cycle", "INTEGER"),
        ):
            if col_name not in stability_cols:
                con.execute("ALTER TABLE " + STABILITY_TABLE + " ADD COLUMN " + col_name + " " + col_decl)
    if not _table_exists(con, STATE_TABLE):
        con.execute(
            "CREATE TABLE " + STATE_TABLE + " (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER)"
        )
    if not _table_exists(con, EVENTS_TABLE):
        con.execute(
            "CREATE TABLE " + EVENTS_TABLE + " ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, prototype_key TEXT, "
            "child_key TEXT, ontology_id INTEGER, confidence REAL, reason TEXT, created_at INTEGER)"
        )
    for k, v in DEFAULTS.items():
        con.execute(
            "INSERT OR IGNORE INTO " + STATE_TABLE + "(key,value,updated_at) VALUES(?,?,?)",
            (k, v, _now()),
        )
    con.commit()
    missing = []
    if "source_cluster_key" not in _columns(con, "ontology"):
        missing.append("ontology.source_cluster_key")
    if "source_relation_ids" not in _columns(con, "ontology"):
        missing.append("ontology.source_relation_ids")
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if not _table_exists(con, EVENTS_TABLE):
        missing.append(EVENTS_TABLE)
    if missing:
        raise RuntimeError("stageb ontology promotion schema missing: " + repr(missing))
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


def _relation_ids_for_edge(con, node_a: str, node_b: str) -> List[int]:
    """Every `relations` row whose (source, target) pair matches this edge
    in either direction, case-insensitively -- the full provenance list
    stored in ontology.source_relation_ids for this child/prototype pair."""
    rows = con.execute(
        "SELECT id, source, target FROM relations WHERE source IS NOT NULL AND target IS NOT NULL"
    ).fetchall()
    out = []
    for rid, source, target in rows:
        a = (source or "").strip().lower()[:180]
        b = (target or "").strip().lower()[:180]
        if {a, b} == {node_a, node_b}:
            out.append(rid)
    return out


def _promote_stable_clusters(con, now) -> Dict[str, int]:
    state = _read_kv(con, STATE_TABLE)
    base_budget = max(0, _int(state.get("ontology_promotion_budget"), 1))
    # BRAINSTEM_ONTOLOGY_PROMOTION_NEUROMODULATOR_COUPLING_V1: see
    # DEFAULTS' own comment for the full derivation. Exactly base_budget
    # (no behavior change) at acetylcholine's own neutral baseline of 0.5.
    # The structural on/off switch above deliberately stays governed only
    # by the raw, unmodulated base_budget.
    neuromod = _neuromodulators(con)
    ach_gain = _float(state.get("selection_pressure_ach_gain"), 0.6)
    acetylcholine = neuromod["acetylcholine"]
    effective_budget = max(0.0, base_budget * (1.0 + ach_gain * (acetylcholine - 0.5)))
    # SQLite's LIMIT clause requires an integer parameter (a float raises
    # "datatype mismatch", confirmed directly) -- round for the query
    # below while effective_budget itself remains available if ever
    # needed for diagnostics.
    budget = max(0, round(effective_budget))
    streak_state = _read_kv(con, "stageb_ontology_cluster_observation_state")
    # BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1: the observation
    # module's own cycle_count is the single, shared reference clock for
    # promoted_at_cycle/retracted_at_cycle timestamps below -- deliberately
    # NOT this module's own, separately-incremented cycle_count, since the
    # two counters are not otherwise guaranteed to stay numerically
    # identical (e.g. if either module were ever individually disabled for
    # a period), and the survival-window computation in
    # _update_na_direction_sign() requires one single, consistent clock.
    observation_cycle = _int(streak_state.get("cycle_count"), 0)
    noradrenaline_at_promotion = neuromod["noradrenaline"]
    # BRAINSTEM_ONTOLOGY_NEUROMODULATOR_COUPLING_V1: prefer the
    # observation module's own serotonin-modulated derived key (see that
    # module's own comment), falling back to the raw base key for
    # defensiveness against an older database that has not yet run a
    # cycle with this delivery applied.
    required_streak = max(1, _int(
        streak_state.get("effective_stability_streak_required",
                          streak_state.get("stability_streak_required")), 3))

    stable_unpromoted = con.execute(
        "SELECT prototype_key, prototype_surface, member_keys_json, streak FROM " + STABILITY_TABLE + " "
        "WHERE streak>=? AND promoted=0 ORDER BY streak DESC, prototype_key ASC LIMIT ?",
        (required_streak, budget if budget > 0 else 0),
    ).fetchall()

    clusters_promoted = 0
    child_rows_promoted = 0
    for prototype_key, prototype_surface, member_keys_json, streak in stable_unpromoted:
        try:
            member_keys = json.loads(member_keys_json or "[]")
        except Exception:
            continue
        children = [m for m in member_keys if m != prototype_key]
        if not children:
            continue
        # Confidence: same Bayesian pseudo-count formula already used
        # project-wide for hypothesis confidence
        # (BRAINSTEM_HYPOTHESIS_CONFIDENCE_FREEZE_FIX_V1) -- applied here to
        # the cluster's own reconfirmation streak, so a cluster reconfirmed
        # many times carries higher, but never absolute, confidence.
        confidence = 1.0 - (1.0 / (1.0 + int(streak)))
        node_rows = dict(con.execute(
            "SELECT node_key, surface_form FROM ontology_node_cluster_state WHERE node_key IN (%s)"
            % ",".join("?" for _ in member_keys), member_keys
        ).fetchall()) if member_keys else {}
        for child_key in children:
            child_surface = node_rows.get(child_key, child_key)
            relation_ids = _relation_ids_for_edge(con, prototype_key, child_key)
            cur = con.execute(
                "INSERT INTO ontology(child,parent,relation,confidence,fact_id,created_at,"
                "source_cluster_key,source_relation_ids) VALUES(?,?,?,?,?,?,?,?)",
                (child_surface[:180], prototype_surface[:180], RELATION_LABEL, confidence, None, now,
                 prototype_key, json.dumps(relation_ids)),
            )
            ontology_id = cur.lastrowid
            con.execute(
                "INSERT INTO " + EVENTS_TABLE + "(event_type,prototype_key,child_key,ontology_id,confidence,"
                "reason,created_at) VALUES(?,?,?,?,?,?,?)",
                ("ontology_promoted", prototype_key, child_key, ontology_id, confidence,
                 "stable_cluster_streak_%d" % streak, now),
            )
            child_rows_promoted += 1
        # BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1: capture this
        # cluster's noradrenaline-at-promotion/promoted_at_cycle only on
        # its OWN first-ever promotion (COALESCE preserves any value
        # already recorded by an earlier promotion, e.g. if this cluster
        # was previously retracted and is now being re-promoted) -- a
        # disclosed, deliberate simplification: each prototype_key
        # contributes at most one outcome data point over its whole
        # lifetime, tied to its FIRST promotion's noradrenaline value and
        # whether it was EVER subsequently retracted (see
        # _update_na_direction_sign()'s own docstring in the observation
        # module).
        con.execute(
            "UPDATE " + STABILITY_TABLE + " SET promoted=1, updated_at=?, "
            "noradrenaline_at_promotion=COALESCE(noradrenaline_at_promotion,?), "
            "promoted_at_cycle=COALESCE(promoted_at_cycle,?) WHERE prototype_key=?",
            (now, noradrenaline_at_promotion, observation_cycle, prototype_key),
        )
        clusters_promoted += 1

    return {"clusters_promoted": clusters_promoted, "child_rows_promoted": child_rows_promoted}


def _retract_dissolved_clusters(con, now) -> Dict[str, int]:
    """A cluster whose streak has been reset to 0 by the observation
    module (this cycle or an earlier one) but which was already promoted
    (promoted=1) has dissolved -- retract every ontology row carrying its
    source_cluster_key, mirroring fact/relation retraction-on-reversal.

    BRAINSTEM_ONTOLOGY_NA_DIRECTION_SELF_REGULATION_V1: this is also the
    single point in this codebase where a cluster's outcome becomes a
    real, elapsed "failure" data point for _update_na_direction_sign() in
    the observation module -- retracted_at_cycle is stamped here (via
    COALESCE, first retraction only, permanently marking this
    prototype_key as "has ever failed" even if later re-promoted and
    currently stable again -- see that module's own docstring for why
    this simplification was chosen)."""
    observation_cycle = _int(
        _read_kv(con, "stageb_ontology_cluster_observation_state").get("cycle_count"), 0)
    dissolved = con.execute(
        "SELECT prototype_key FROM " + STABILITY_TABLE + " WHERE streak=0 AND promoted=1"
    ).fetchall()
    retracted = 0
    for (prototype_key,) in dissolved:
        rows = con.execute(
            "SELECT id, child, parent, confidence FROM ontology WHERE source_cluster_key=?",
            (prototype_key,),
        ).fetchall()
        for ontology_id, child, parent, confidence in rows:
            con.execute("DELETE FROM ontology WHERE id=?", (ontology_id,))
            con.execute(
                "INSERT INTO " + EVENTS_TABLE + "(event_type,prototype_key,child_key,ontology_id,confidence,"
                "reason,created_at) VALUES(?,?,?,?,?,?,?)",
                ("ontology_retracted", prototype_key, child, ontology_id, confidence,
                 "cluster_dissolved_streak_reset_to_zero", now),
            )
            retracted += 1
        con.execute(
            "UPDATE " + STABILITY_TABLE + " SET promoted=0, updated_at=?, "
            "retracted_at_cycle=COALESCE(retracted_at_cycle,?) WHERE prototype_key=?",
            (now, observation_cycle, prototype_key),
        )
    return {"clusters_retracted": len(dissolved), "rows_retracted": retracted}


def run_ontology_promotion_cycle(con) -> Dict[str, Any]:
    ensure_schema(con)
    state = _read_kv(con, STATE_TABLE)
    if str(state.get("enabled", "true")).strip().lower() != "true":
        return {"status": "stageb_ontology_promotion_disabled"}
    now = _now()

    con.execute("SAVEPOINT stageb_ontology_promotion")
    try:
        promotion_result = _promote_stable_clusters(con, now)
        retraction_result = _retract_dissolved_clusters(con, now)

        _set_kv(con, STATE_TABLE, "cycle_count", _int(state.get("cycle_count"), 0) + 1)
        _set_kv(con, STATE_TABLE, "clusters_promoted_total",
                _int(state.get("clusters_promoted_total"), 0) + promotion_result["clusters_promoted"])
        _set_kv(con, STATE_TABLE, "child_rows_promoted_total",
                _int(state.get("child_rows_promoted_total"), 0) + promotion_result["child_rows_promoted"])
        _set_kv(con, STATE_TABLE, "clusters_retracted_total",
                _int(state.get("clusters_retracted_total"), 0) + retraction_result["clusters_retracted"])
        con.execute("RELEASE SAVEPOINT stageb_ontology_promotion")
        con.commit()
        return {
            "status": "stageb_ontology_promotion_cycle",
            "clusters_promoted": promotion_result["clusters_promoted"],
            "child_rows_promoted": promotion_result["child_rows_promoted"],
            "clusters_retracted": retraction_result["clusters_retracted"],
            "rows_retracted": retraction_result["rows_retracted"],
            "ontology_total": con.execute("SELECT COUNT(*) FROM ontology").fetchone()[0],
        }
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT stageb_ontology_promotion")
        con.execute("RELEASE SAVEPOINT stageb_ontology_promotion")
        con.commit()
        raise


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
        {"status": "stageb_ontology_promotion_no_previous_cycle"}
    try:
        con = _db(self)
        result = run_ontology_promotion_cycle(con)
    except Exception as exc:
        result = {"status": "stageb_ontology_promotion_error",
                  "error": type(exc).__name__ + ":" + str(exc)}
    return {"phase": PHASE, "downstream_result": result_prev, "stageb_ontology_promotion_result": result}


def managed_run(self, cycles=1, progress=None):
    return {"phase": PHASE, "results": [managed_cycle(self, progress) for _ in range(max(1, int(cycles or 1)))]}


def autoload(AutonomousLoop):
    global _PREV_CYCLE, _PREV_RUN
    _PREV_CYCLE = getattr(AutonomousLoop, "cycle", None)
    _PREV_RUN = getattr(AutonomousLoop, "run", None)
    AutonomousLoop.cycle = managed_cycle
    AutonomousLoop.run = managed_run
    AutonomousLoop.stageb_ontology_promotion_release = True
    AutonomousLoop.no_word_blacklists = True
    return AutonomousLoop
