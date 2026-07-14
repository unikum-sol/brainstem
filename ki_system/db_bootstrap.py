# -*- coding: utf-8 -*-
"""Adaptive DB Bootstrap for the KI System (creates DB + base + phase tables)."""
from __future__ import annotations
import os, sqlite3, importlib
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_SCHEMA: Dict[str, List[Tuple[str, str]]] = {
    "facts": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("subject","TEXT"),("relation","TEXT"),("object","TEXT"),("confidence","REAL DEFAULT 0"),("source_chunk_id","INTEGER"),("created_at","INTEGER"),("updated_at","INTEGER")],
    "relations": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("subject","TEXT"),("relation","TEXT"),("object","TEXT"),("confidence","REAL DEFAULT 0"),("source_chunk_id","INTEGER"),("created_at","INTEGER")],
    "questions": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("question","TEXT"),("priority","REAL DEFAULT 0"),("status","TEXT DEFAULT 'open'"),("created_at","INTEGER"),("updated_at","INTEGER")],
    "documents": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("path","TEXT"),("title","TEXT"),("kind","TEXT"),("metadata_json","TEXT"),("source_score","REAL DEFAULT 1"),("created_at","INTEGER")],
    "chunks": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("document_id","INTEGER"),("chunk_index","INTEGER"),("text","TEXT"),("token_count","INTEGER"),("title","TEXT"),("metadata_json","TEXT"),("import_key","TEXT"),("created_at","INTEGER")],
    "ontology": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("subject","TEXT"),("super","TEXT"),("relation","TEXT"),("confidence","REAL DEFAULT 0"),("source_fact_id","INTEGER")],
    "context_hypotheses": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("subject","TEXT"),("hypothesis","TEXT"),("confidence","REAL DEFAULT 0"),("phase6a_replay_priority","REAL DEFAULT 0"),("phase6a_replay_weight","REAL DEFAULT 0"),("phase6a_meta_plasticity","REAL DEFAULT 0"),("phase6a_sleep_replay_count","INTEGER DEFAULT 0"),("phase6a_last_replayed_at","INTEGER DEFAULT 0"),("phase6a_replay_reason","TEXT"),("created_at","INTEGER")],
    "internal_learning_gaps": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("gap_key","TEXT"),("gap_reason","TEXT"),("priority","REAL DEFAULT 0"),("status","TEXT DEFAULT 'open'"),("created_at","INTEGER")],
    "phase5g_experiment_outcomes": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("strategy","TEXT"),("outcome_score","REAL DEFAULT 0"),("closure_delta","REAL DEFAULT 0"),("overlap_score","REAL DEFAULT 0"),("created_at","INTEGER")],
    "phase5h_strategy_outcome_memory": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("strategy","TEXT"),("outcome_score","REAL DEFAULT 0"),("confidence","REAL DEFAULT 0"),("created_at","INTEGER")],
    "phase6a_sleep_replay_cycles": [("id","INTEGER PRIMARY KEY AUTOINCREMENT"),("candidate_count","INTEGER"),("replay_events","INTEGER"),("avg_outcome_score","REAL"),("avg_closure_delta","REAL"),("avg_overlap_score","REAL"),("persistent_gap_pressure","REAL"),("plasticity_level","REAL"),("exploration_bias","REAL"),("consolidation_bias","REAL"),("created_at","INTEGER")],
    "phase6a_meta_plasticity_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
    "phase6a_neuromodulated_sleep_state": [("key","TEXT PRIMARY KEY"),("value","TEXT"),("updated_at","INTEGER")],
}

PHASE_REGISTRY: List[Tuple[str, str]] = [
    ("v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release", "phase6a"),
    ("v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release", "phase6b"),
    ("v8_phase6c_bias_persistence_and_self_regulating_meta_release", "phase6c"),
    ("v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release", "phase6d"),
    ("v8_phase7a_adenosine_homeostat_release", "phase7a"),
    ("v8_phase7b_endocannabinoid_retrograde_gain_control_release", "phase7b"),
]

def register_phase_module(module_name, phase_name):
    for m, _ in PHASE_REGISTRY:
        if m == module_name:
            return
    PHASE_REGISTRY.append((module_name, phase_name))

def _table_exists(con, table):
    return con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

def _columns(con, table):
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]

def _apply_base_schema(con):
    report = {"created_tables": [], "added_columns": []}
    for table, cols in BASE_SCHEMA.items():
        if not _table_exists(con, table):
            col_defs = ", ".join(name + " " + spec for name, spec in cols)
            con.execute("CREATE TABLE " + table + " (" + col_defs + ")")
            report["created_tables"].append(table)
        else:
            existing = set(_columns(con, table))
            for name, spec in cols:
                if name in existing: continue
                spec_up = spec.upper()
                if "PRIMARY KEY" in spec_up or "AUTOINCREMENT" in spec_up: continue
                con.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + spec)
                report["added_columns"].append(table + "." + name)
    con.commit()
    return report

def _bootstrap_phase_modules(con):
    bootstrapped, phase_reports, errors = [], {}, []
    for mod_name, phase_name in PHASE_REGISTRY:
        try:
            mod = importlib.import_module("ki_system." + mod_name)
        except ImportError:
            continue
        except Exception as exc:
            errors.append((phase_name, "import_error: " + str(exc)))
            continue
        fn = getattr(mod, "ensure_schema", None)
        if fn is None: continue
        try:
            r = fn(con)
            phase_reports[phase_name] = r
            bootstrapped.append(phase_name)
        except Exception as exc:
            errors.append((phase_name, "ensure_schema_error: " + str(exc)))
    con.commit()
    return bootstrapped, phase_reports, errors
_PERF_INDEXES = [
    ("hypothesis_learning_updates", "hypothesis_id", "idx_hlu_hyp"),
    ("hypothesis_feedback", "hypothesis_id", "idx_hfb_hyp"),
    ("hypothesis_error_events", "hypothesis_id", "idx_hee_hyp"),
    ("hypothesis_stability_scores", "hypothesis_id", "idx_hss_hyp"),
    ("phase5f_context_window_experiments", "target_chunk_id", "idx_p5f_tgt"),
]

def ensure_perf_indexes(con):
    created = []
    for table, col, name in _PERF_INDEXES:
        try:
            if not _table_exists(con, table):
                continue
            if col not in _columns(con, table):
                continue
            exists = con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
            if exists:
                continue
            con.execute("CREATE INDEX IF NOT EXISTS " + name + " ON " + table + "(" + col + ")")
            created.append(name)
        except Exception:
            continue
    con.commit()
    return created
def ensure_database_exists(db_path):
    p = Path(db_path)
    db_created = not p.exists()
    if db_created:
        p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p), timeout=30.0)
    try:
        try: con.execute("PRAGMA journal_mode=WAL")
        except Exception: pass
        base_report = _apply_base_schema(con)
        bootstrapped, phase_reports, errors = _bootstrap_phase_modules(con)
        perf_indexes = ensure_perf_indexes(con)
        con.commit()
        return {"db_created": db_created, "db_path": str(p.resolve()),
                "perf_indexes_created": perf_indexes,
                "base_tables_created": base_report["created_tables"],
                "base_columns_added": base_report["added_columns"],
                "phases_bootstrapped": bootstrapped,
                "phase_reports": phase_reports, "errors": errors}
    finally:
        con.close()

def print_bootstrap_report(report):
    print("=" * 60)
    print("KI Database Bootstrap Report")
    print("=" * 60)
    print("DB path:      ", report.get("db_path"))
    print("DB created:   ", report.get("db_created"))
    print("Base tables:  ", report.get("base_tables_created") or "(none new)")
    added = report.get("base_columns_added") or []
    if added:
        print("Base columns added:")
        for a in added: print("  +", a)
    print("Phases bootstrapped:", report.get("phases_bootstrapped") or "(none)")
    for phase, r in (report.get("phase_reports") or {}).items():
        if isinstance(r, dict):
            ct = r.get("created_tables") or []; ac = r.get("added_columns") or []; ci = r.get("created_indexes") or []
            print("  " + phase + ":")
            if ct: print("    new tables :", ct)
            if ac: print("    new columns:", ac)
            if ci: print("    new indexes:", ci)
    for phase, e in (report.get("errors") or []):
        print("  !", phase, "->", e)
    print("=" * 60)
