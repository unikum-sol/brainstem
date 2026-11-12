# -*- coding: utf-8 -*-
"""Promote stable graph clusters as association membership, not taxonomy."""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List

PHASE = "stageb_ontology_promotion_release"
STATE_TABLE = "stageb_ontology_promotion_state"
EVENTS_TABLE = "stageb_ontology_promotion_events"
STABILITY_TABLE = "ontology_cluster_stability_state"
RELATION_LABEL = "member_of_cluster"

DEFAULTS = {
    "enabled": "true",
    "cycle_count": "0",
    "ontology_promotion_budget": "1",
    "clusters_promoted_total": "0",
    "clusters_retracted_total": "0",
    "child_rows_promoted_total": "0",
    "selection_pressure_ach_gain": "0.6",
    "promotion_fractional_remainder": "0.0",
    "effective_promotion_budget_continuous": "1.0",
    "effective_promotion_budget": "1",

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
    required = {'stageb_ontology_promotion_state': ['key', 'value', 'updated_at'], 'ontology_cluster_stability_state': ['prototype_key', 'member_keys_json', 'streak', 'promoted', 'min_size_eligible'], 'ontology': ['source_cluster_key', 'source_relation_ids']}
    return [table + "." + column for table, columns in required.items()
            for column in columns if column not in _columns(con, table)]


def ensure_schema(con) -> bool:
    from ki_system.semantic_evidence import ensure_schema as ensure_evidence
    ensure_evidence(con)
    if _table_exists(con, "ontology"):
        cols = _columns(con, "ontology")
        if "source_cluster_key" not in cols:
            con.execute("ALTER TABLE ontology ADD COLUMN source_cluster_key TEXT")
        if "source_relation_ids" not in cols:
            con.execute("ALTER TABLE ontology ADD COLUMN source_relation_ids TEXT")
    if _table_exists(con, STABILITY_TABLE):
        stability_cols = _columns(con, STABILITY_TABLE)
        for col_name, col_decl in (
            ("noradrenaline_at_promotion", "REAL"),
            ("promoted_at_cycle", "INTEGER"),
            ("retracted_at_cycle", "INTEGER"),
            ("min_size_eligible", "INTEGER DEFAULT 1"),
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
    if _table_exists(con, STABILITY_TABLE) and "min_size_eligible" not in _columns(con, STABILITY_TABLE):
        missing.append(STABILITY_TABLE + ".min_size_eligible")
    if not _table_exists(con, STATE_TABLE):
        missing.append(STATE_TABLE)
    if not _table_exists(con, EVENTS_TABLE):
        missing.append(EVENTS_TABLE)
    missing.extend(_self_check_schema(con))
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
    neuromod = _neuromodulators(con)
    ach_gain = _float(state.get("selection_pressure_ach_gain"), 0.6)
    acetylcholine = neuromod["acetylcholine"]
    from ki_system.fractional_control import finite, fractional_integer
    # Keep the existing positive structural-encoding direction; no SWS changes.
    acetylcholine = max(0.0, min(1.0, finite(acetylcholine, 0.5)))
    ach_gain = max(0.0, min(1.0, finite(ach_gain, 0.6)))
    effective_budget = max(0.0, base_budget * (1.0 + ach_gain * (acetylcholine - 0.5)))
    streak_state = _read_kv(con, "stageb_ontology_cluster_observation_state")
    observation_cycle = _int(streak_state.get("cycle_count"), 0)
    noradrenaline_at_promotion = neuromod["noradrenaline"]
    required_streak = max(1, _int(
        streak_state.get("effective_stability_streak_required",
                          streak_state.get("stability_streak_required")), 3))

    eligible_exists = con.execute(
        "SELECT 1 FROM " + STABILITY_TABLE +
        " WHERE streak>=? AND promoted=0 AND COALESCE(min_size_eligible,1)=1 LIMIT 1",
        (required_streak,),
    ).fetchone() is not None
    if base_budget == 0 or not eligible_exists:
        budget, next_carry = 0, 0.0
    else:
        budget, next_carry = fractional_integer(
            effective_budget, finite(state.get("promotion_fractional_remainder"), 0.0))
    _set_kv(con, STATE_TABLE, "promotion_fractional_remainder", next_carry)
    _set_kv(con, STATE_TABLE, "effective_promotion_budget_continuous", effective_budget)
    _set_kv(con, STATE_TABLE, "effective_promotion_budget", budget)

    stable_unpromoted = con.execute(
        "SELECT prototype_key, prototype_surface, member_keys_json, streak FROM " + STABILITY_TABLE + " "
        "WHERE streak>=? AND promoted=0 AND COALESCE(min_size_eligible,1)=1 "
        "ORDER BY streak DESC, prototype_key ASC LIMIT ?",
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
            con.execute("UPDATE ontology SET evidence_kind='graph_cluster',semantic_status='association_only' WHERE id=?",
                        (ontology_id,))
            con.execute(
                "INSERT INTO " + EVENTS_TABLE + "(event_type,prototype_key,child_key,ontology_id,confidence,"
                "reason,created_at) VALUES(?,?,?,?,?,?,?)",
                ("ontology_promoted", prototype_key, child_key, ontology_id, confidence,
                 "stable_cluster_streak_%d" % streak, now),
            )
            child_rows_promoted += 1
        con.execute(
            "UPDATE " + STABILITY_TABLE + " SET promoted=1, updated_at=?, "
            "noradrenaline_at_promotion=COALESCE(noradrenaline_at_promotion,?), "
            "promoted_at_cycle=COALESCE(promoted_at_cycle,?) WHERE prototype_key=?",
            (now, noradrenaline_at_promotion, observation_cycle, prototype_key),
        )
        clusters_promoted += 1

    return {"clusters_promoted": clusters_promoted, "child_rows_promoted": child_rows_promoted}


def _retract_dissolved_clusters(con, now) -> Dict[str, int]:
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
