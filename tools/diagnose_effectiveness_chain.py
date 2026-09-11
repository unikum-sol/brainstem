# -*- coding: utf-8 -*-
"""BrainStem - Diagnose: Warum bleibt effectiveness/inhibitory_readiness bei 0?

BRAINSTEM_EFFECTIVENESS_CHAIN_DIAGNOSTIC_V1

Rein lesend, aendert NICHTS an der Datenbank. Kein Schreibzugriff, keine
Transaktion. Kann sicher NEBEN einem laufenden Drift-Test oder Autonomem
Lernen ausgefuehrt werden (kurzer Timeout, bricht sofort ab statt zu
warten, falls die DB gerade beschaeftigt ist).

Hintergrund: Sowohl "effectiveness" (im Drift-Report immer 0.0000) als
auch "inhibitory_readiness" (in der kooperativen Schlaf-Autoritaet seit
tausenden Zyklen eingefroren) haengen strukturell an derselben Kette:

  phase5g_experiment_outcomes (Zeilenanzahl)
    -> phase6a: outcome_observation_available (0 oder 1)
    -> phase6a_sleep_replay_cycles.outcome_observation_available
    -> phase6b: outcome_obs -> evidence_state -> allowed
    -> effectiveness_score (nur != 0, wenn allowed=1)
    -> phase6b_effectiveness_events (wird JEDEN Zyklus neu geschrieben,
       aber effectiveness_score bleibt 0.0, solange allowed=0 ist)

Da Phase-5g-Experimente in diesem Projekt bewusst produktiv geschlossen
bleiben (Stage-B-Sicherheitsgrenze), ist phase5g_experiment_outcomes
strukturell leer -- das ist erwartetes, korrektes Verhalten, kein Fehler.
Dieses Skript macht diese Kette transparent sichtbar, damit man auf
einen Blick sieht, WARUM ein Wert bei 0/eingefroren bleibt, statt es nur
zu vermuten.

Ausfuehrung (aus dem Projekt-Root, mit main.py auf gleicher Ebene):
    python diagnose_effectiveness_chain.py
Optional mit explizitem DB-Pfad:
    python diagnose_effectiveness_chain.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path


def _table_exists(con, table):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(con, table):
    if not _table_exists(con, table):
        return []
    return [r[1] for r in con.execute("PRAGMA table_info(" + table + ")").fetchall()]


def _kv(con, table):
    if not _table_exists(con, table):
        return {}
    cols = _columns(con, table)
    if "key" not in cols or "value" not in cols:
        return {}
    return dict(con.execute("SELECT key,value FROM " + table).fetchall())


def _count(con, table):
    if not _table_exists(con, table):
        return None
    try:
        return int(con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
    except Exception:
        return None


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "ki_memory.sqlite3"
    if not Path(db_path).exists():
        print("FEHLER: Datenbank nicht gefunden unter:", db_path)
        print("Bitte Pfad als Argument angeben, z.B.:")
        print("  python diagnose_effectiveness_chain.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3")
        return 1

    # Kurzer Timeout: dieses Skript soll NIE einen laufenden Zyklus/Drift-Test blockieren.
    con = sqlite3.connect(db_path, timeout=5)
    con.row_factory = sqlite3.Row

    section("1) DIE WURZEL: phase5g_experiment_outcomes")
    p5g_count = _count(con, "phase5g_experiment_outcomes")
    print("Zeilenanzahl:", p5g_count if p5g_count is not None else "(Tabelle existiert nicht)")
    if p5g_count == 0:
        print("-> LEER. Das ist die strukturelle Ursache fuer alles Folgende.")
        print("   Phase-5g-Experimente sind laut Projektdesign produktiv")
        print("   geschlossen (Stage-B-Sicherheitsgrenze) -- diese Tabelle")
        print("   bleibt deshalb erwartungsgemaess leer, solange das so ist.")
    elif p5g_count and p5g_count > 0:
        print("-> Enthaelt Daten. Die Kette unten sollte dann NICHT mehr")
        print("   dauerhaft bei 0/eingefroren bleiben -- falls doch, bitte")
        print("   die Detailwerte unten genauer betrachten.")

    section("2) PHASE 6A - letzte Replay-Zyklen (outcome_observation_available)")
    if not _table_exists(con, "phase6a_sleep_replay_cycles"):
        print("Tabelle phase6a_sleep_replay_cycles existiert nicht.")
    else:
        cols = set(_columns(con, "phase6a_sleep_replay_cycles"))
        wanted = ["id", "created_at", "candidate_count", "replay_events",
                  "population_available", "outcome_observation_available",
                  "outcome_observation_count", "evidence_state", "evidence_reason"]
        select_cols = [c for c in wanted if c in cols]
        rows = con.execute(
            "SELECT " + ", ".join(select_cols) +
            " FROM phase6a_sleep_replay_cycles ORDER BY id DESC LIMIT 5"
        ).fetchall()
        print("Letzte 5 Zyklen (neuester zuerst):")
        for r in rows:
            d = dict(zip(select_cols, r))
            print("  id=%s | population_available=%s | outcome_observation_available=%s | evidence_state=%s" % (
                d.get("id"), d.get("population_available"),
                d.get("outcome_observation_available"), d.get("evidence_state")))
        if rows:
            latest = dict(zip(select_cols, rows[0]))
            if str(latest.get("outcome_observation_available")) in ("0", "0.0", "None"):
                print("\n-> BESTAETIGT: outcome_observation_available ist 0 im neuesten Zyklus.")
                print("   Das blockiert effectiveness_score strukturell in Phase 6b (siehe Abschnitt 3).")

    section("3) PHASE 6B - Freshness-Kette und letzte Effectiveness-Events")
    p6b_state = _kv(con, "phase6b_state")
    print("phase6b_state.last_consumed_phase6a_cycle_id:", p6b_state.get("last_consumed_phase6a_cycle_id", "(nie gesetzt)"))
    if not _table_exists(con, "phase6b_effectiveness_events"):
        print("Tabelle phase6b_effectiveness_events existiert nicht.")
    else:
        cols = set(_columns(con, "phase6b_effectiveness_events"))
        wanted = ["id", "cycle_index", "created_at", "population_available",
                  "outcome_observation_available", "comparison_window_available",
                  "evidence_state", "evidence_reason", "effectiveness_score",
                  "plateau_flag", "source_phase6a_fresh"]
        select_cols = [c for c in wanted if c in cols]
        rows = con.execute(
            "SELECT " + ", ".join(select_cols) +
            " FROM phase6b_effectiveness_events ORDER BY id DESC LIMIT 5"
        ).fetchall()
        total = _count(con, "phase6b_effectiveness_events")
        print("Gesamtanzahl aufgezeichneter Effectiveness-Events:", total)
        print("Letzte 5 Events (neuester zuerst):")
        for r in rows:
            d = dict(zip(select_cols, r))
            print("  id=%s | cycle=%s | evidence_state=%-38s | effectiveness_score=%s | fresh=%s" % (
                d.get("id"), d.get("cycle_index"), d.get("evidence_state"),
                d.get("effectiveness_score"), d.get("source_phase6a_fresh")))
        if rows:
            latest = dict(zip(select_cols, rows[0]))
            state = str(latest.get("evidence_state"))
            print()
            if state == "population_without_outcome_observation":
                print("-> BESTAETIGT: evidence_state ist 'population_without_outcome_observation'.")
                print("   Das bedeutet: Es GIBT Replay-Aktivitaet (Population vorhanden),")
                print("   aber effectiveness_score bleibt bei 0.0, weil phase5g_experiment_outcomes")
                print("   leer ist (siehe Abschnitt 1). Das ist strukturell erwartetes Verhalten,")
                print("   kein Fehler und kein Anzeigeproblem -- es wird tatsaechlich jeden Zyklus")
                print("   neu berechnet und als 0.0 geschrieben.")
            elif state == "no_population":
                print("-> evidence_state ist 'no_population': Es gab noch KEINE Replay-Kandidaten")
                print("   in diesem Zyklus. Anders als der obige Fall -- hier fehlt es schon an")
                print("   Kandidaten, nicht nur an Outcome-Beobachtung.")
            elif state in ("outcome_observed_change", "outcome_observed_no_change"):
                print("-> evidence_state ist '%s': effectiveness_score wird jetzt echt berechnet"
                      " (nicht mehr strukturell blockiert)." % state)

    section("4) PHASE 6A - Bias-Kette (exploration_bias / plasticity_level)")
    meta = _kv(con, "phase6a_meta_plasticity_state")
    for k in ("last_exploration_bias", "last_plasticity_level", "last_consolidation_bias",
              "last_inhibition_bias", "last_revision_bias", "last_avg_outcome_score",
              "last_avg_no_candidate_rate", "last_avg_overlap_score"):
        print("  %-28s: %s" % (k, meta.get(k, "(fehlt)")))

    section("5) PHASE 6B - Plastizitaets-Anpassungen (wurde je etwas WIRKLICH geaendert?)")
    if not _table_exists(con, "phase6b_plasticity_adjustments"):
        print("Tabelle phase6b_plasticity_adjustments existiert nicht.")
    else:
        cols = set(_columns(con, "phase6b_plasticity_adjustments"))
        wanted = ["id", "cycle_index", "adjustment_type", "evidence_state", "state_change_allowed"]
        select_cols = [c for c in wanted if c in cols]
        rows = con.execute(
            "SELECT " + ", ".join(select_cols) +
            " FROM phase6b_plasticity_adjustments ORDER BY id DESC LIMIT 5"
        ).fetchall()
        total = _count(con, "phase6b_plasticity_adjustments")
        allowed_total = None
        if "state_change_allowed" in cols:
            try:
                allowed_total = con.execute(
                    "SELECT COUNT(*) FROM phase6b_plasticity_adjustments WHERE state_change_allowed=1"
                ).fetchone()[0]
            except Exception:
                allowed_total = None
        print("Gesamtanzahl Eintraege:", total, "| davon mit state_change_allowed=1:", allowed_total)
        print("Letzte 5 (neuester zuerst):")
        for r in rows:
            d = dict(zip(select_cols, r))
            print("  id=%s | cycle=%s | adjustment_type=%-24s | evidence_state=%-38s | allowed=%s" % (
                d.get("id"), d.get("cycle_index"), d.get("adjustment_type"),
                d.get("evidence_state"), d.get("state_change_allowed")))
        if allowed_total == 0:
            print()
            print("-> BESTAETIGT: state_change_allowed war NOCH NIE 1. Das heisst: exploration_bias,")
            print("   plasticity_level und die anderen Bias-Werte wurden von Phase 6b bislang")
            print("   NIE tatsaechlich veraendert -- konsistent mit dem eingefrorenen Zustand aus")
            print("   Abschnitt 4 oben.")

    section("6) ZUSAMMENFASSUNG")
    print("Wenn phase5g_experiment_outcomes leer ist (Abschnitt 1), UND")
    print("evidence_state = 'population_without_outcome_observation' (Abschnitt 3), UND")
    print("state_change_allowed nie 1 war (Abschnitt 5):")
    print()
    print("  -> effectiveness=0.0000 im Drift-Report UND das eingefrorene")
    print("     exploration_bias/plasticity_level/inhibitory_readiness haben")
    print("     dieselbe Ursache: Phase-5g-Experimente sind produktiv geschlossen.")
    print("     Das ist eine bewusste Design-Grenze dieses Projekts (Stage-B-")
    print("     Sicherheitsgate), KEIN Bug und KEIN Anzeigefehler.")
    print()
    print("  -> Diese Werte werden sich erst dann bewegen, wenn/falls Phase-5g-")
    print("     Experimente als eigener, spaeterer Schritt bewusst geoeffnet werden.")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
