# -*- coding: utf-8 -*-
"""BrainStem - Diagnose: Kooperative Schlaf-Autoritaet vs. Phase-7a-Homeostat.

BRAINSTEM_SLEEP_AUTHORITY_DIAGNOSTIC_V1

Rein lesend, aendert NICHTS an der Datenbank. Kein Schreibzugriff, keine
Transaktion. Kann sicher waehrend eines laufenden Autonomes-Lernens
ausgefuehrt werden (nutzt einen kurzen Timeout und gibt sofort auf, statt
zu blockieren, falls die DB gerade beschaeftigt ist).

Zweck: Objektive Klaerung, ob das Ausbleiben von "sleep" in der GUI-Anzeige
(cooperative_sleep_wake_state) ein Datenreife-Effekt (die vier Nicht-
Adenosin-Komponenten des kooperativen Scores sind einfach noch nicht weit
genug von ihren Startwerten entfernt) oder eine echte Regression ist
(z.B. war der kooperative Zustand in einem frueheren Lauf schon einmal
"sleep", jetzt trotz vergleichbarer oder hoeherer Werte nicht mehr).

Ausfuehrung (aus dem Projekt-Root, mit main.py auf gleicher Ebene):
    python diagnose_sleep_authority.py
Optional mit explizitem DB-Pfad:
    python diagnose_sleep_authority.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3
"""
from __future__ import annotations
import sqlite3
import sys
import json
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


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "ki_memory.sqlite3"
    if not Path(db_path).exists():
        print("FEHLER: Datenbank nicht gefunden unter:", db_path)
        print("Bitte Pfad als Argument angeben, z.B.:")
        print("  python diagnose_sleep_authority.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3")
        return 1

    # Kurzer Timeout: dieses Skript soll NIE eine laufende Lernsession blockieren.
    con = sqlite3.connect(db_path, timeout=5)
    con.row_factory = sqlite3.Row

    section("1) KOOPERATIVE SCHLAF-AUTORITAET - aktueller Zustand")
    coop_state = _kv(con, "cooperative_sleep_wake_state")
    if not coop_state:
        print("KEINE Daten in cooperative_sleep_wake_state gefunden.")
        print("-> Die kooperative Autoritaet hat noch KEINEN einzigen Zyklus abgeschlossen.")
    else:
        for k in ("state", "previous_state", "cycle_count", "sleep_score",
                  "enter_threshold", "exit_threshold", "min_dwell_cycles",
                  "dwell_cycles", "transition_reason",
                  "adenosine_pressure", "arousal_release",
                  "inhibitory_readiness", "consolidation_readiness", "stress_block"):
            print("  %-24s: %s" % (k, coop_state.get(k, "(fehlt)")))

    section("2) KOOPERATIVE SCHLAF-AUTORITAET - vollstaendiger Verlauf (alle Zyklen)")
    if not _table_exists(con, "cooperative_sleep_wake_cycles"):
        print("Tabelle cooperative_sleep_wake_cycles existiert nicht.")
    else:
        rows = con.execute(
            "SELECT cycle_index, state, previous_state, transitioned, reason, "
            "sleep_score, adenosine_pressure, arousal_release, inhibitory_readiness, "
            "consolidation_readiness, stress_block "
            "FROM cooperative_sleep_wake_cycles ORDER BY cycle_index ASC"
        ).fetchall()
        print("Anzahl aufgezeichneter Zyklen:", len(rows))
        if not rows:
            print("-> Noch keine einzige Aufzeichnung. Die Autoritaet lief noch nie durch.")
        else:
            sleep_rows = [r for r in rows if str(r["state"]).lower() == "sleep"]
            transitions = [r for r in rows if r["transitioned"]]
            print("Davon mit state='sleep':", len(sleep_rows))
            print("Davon mit einer Zustandsuebergang (transitioned=1):", len(transitions))
            if transitions:
                print("\n  Alle aufgezeichneten Uebergaenge:")
                for r in transitions:
                    print("    Zyklus %5s: %-6s -> %-6s (Grund: %s, Score: %.4f)" % (
                        r["cycle_index"], r["previous_state"], r["state"],
                        r["reason"], r["sleep_score"] or 0.0))
            else:
                print("-> In der gesamten aufgezeichneten Historie gab es KEINEN einzigen")
                print("   Uebergang. Das ist der zentrale Befund fuer die Klaerung:")
                print("   Wenn dieser DB-Stand bereits Hunderte Zyklen enthaelt und nie")
                print("   'sleep' erreicht wurde, deutet das eher auf eine Kalibrierungs-")
                print("   oder Regressionsfrage hin. Wenn dieser DB-Stand erst wenige")
                print("   Zyklen alt ist (siehe Zyklenanzahl oben), ist ein Datenreife-")
                print("   Effekt weiterhin die wahrscheinlichere Erklaerung.")

            print("\n  Score-Statistik ueber alle Zyklen:")
            scores = [r["sleep_score"] for r in rows if r["sleep_score"] is not None]
            if scores:
                print("    min=%.4f  max=%.4f  letzter=%.4f  Schwelle(enter)=%s" % (
                    min(scores), max(scores), scores[-1],
                    coop_state.get("enter_threshold", "0.62 (Default)")))
                closest = max(rows, key=lambda r: (r["sleep_score"] or -1))
                print("    Hoechster je erreichter Score bei Zyklus %s: %.4f" % (
                    closest["cycle_index"], closest["sleep_score"] or 0.0))
                print("      Komponenten zu diesem Zeitpunkt:")
                print("        adenosine_pressure     = %.4f (Gewicht 35%%)" % (closest["adenosine_pressure"] or 0.0))
                print("        arousal_release        = %.4f (Gewicht 25%%)" % (closest["arousal_release"] or 0.0))
                print("        inhibitory_readiness    = %.4f (Gewicht 20%%)" % (closest["inhibitory_readiness"] or 0.0))
                print("        consolidation_readiness = %.4f (Gewicht 12%%)" % (closest["consolidation_readiness"] or 0.0))
                print("        stress_block (invertiert)= %.4f (Gewicht 8%%)" % (closest["stress_block"] or 0.0))
                # Welche Komponente war am weitesten von "gut" entfernt?
                contributions = {
                    "adenosine_pressure (35%)": 0.35 * (closest["adenosine_pressure"] or 0.0),
                    "arousal_release (25%)": 0.25 * (closest["arousal_release"] or 0.0),
                    "inhibitory_readiness (20%)": 0.20 * (closest["inhibitory_readiness"] or 0.0),
                    "consolidation_readiness (12%)": 0.12 * (closest["consolidation_readiness"] or 0.0),
                    "stress_freedom (8%)": 0.08 * (1.0 - (closest["stress_block"] or 0.0)),
                }
                print("\n      Beitrag jeder Komponente zum Gesamtscore an diesem Punkt:")
                for name, val in sorted(contributions.items(), key=lambda kv: kv[1]):
                    print("        %-30s: %.4f" % (name, val))
                weakest = min(contributions.items(), key=lambda kv: kv[1])
                print("\n      -> Schwaechster Beitrag: %s" % weakest[0])
                print("         Das ist die Komponente, die am meisten fehlt, um die 0.62-Schwelle zu erreichen.")

    section("3) PHASE 7A (legacy Adenosin-Homeostat) - aktueller Zustand")
    p7a = _kv(con, "phase7a_adenosine_state")
    if not p7a:
        print("KEINE Daten in phase7a_adenosine_state gefunden.")
    else:
        for k in ("homeostat_mode", "adenosine_level", "mode_entered_cycle",
                  "sleep_dwell_cycles", "minimum_sleep_cycles",
                  "total_sleep_cycles", "total_wake_cycles",
                  "transition_count", "threshold_high", "threshold_low"):
            print("  %-24s: %s" % (k, p7a.get(k, "(fehlt)")))

    section("4) PHASE 7A - Ereignis-Historie (Schlaf-Ein-/Austritte)")
    if not _table_exists(con, "phase7a_adenosine_events"):
        print("Tabelle phase7a_adenosine_events existiert nicht.")
    else:
        events = con.execute(
            "SELECT cycle_index, event_type, adenosine_level, action_taken, reason "
            "FROM phase7a_adenosine_events "
            "WHERE event_type IN ('sleep_downscale','sleep_discharge','idle_decay') "
            "ORDER BY cycle_index ASC"
        ).fetchall()
        print("Anzahl Schlaf-bezogener Ereignisse:", len(events))
        if events:
            first, last = events[0], events[-1]
            print("  Erstes Ereignis: Zyklus %s (%s)" % (first["cycle_index"], first["event_type"]))
            print("  Letztes Ereignis: Zyklus %s (%s)" % (last["cycle_index"], last["event_type"]))
            exits = [e for e in events if e["action_taken"] == "exit_to_wake"]
            print("  Davon 'exit_to_wake' (Aufwach-Ereignisse):", len(exits))
        else:
            print("-> Phase 7a war laut Ereignisprotokoll noch NIE im Schlafmodus.")

    section("5) GUI-SEITIGE ENTSCHEIDUNGSLOGIK (zur Einordnung)")
    print("Die GUI (gui_app.py, read_all_neuromods) nutzt AUSSCHLIESSLICH den")
    print("kooperativen Zustand aus Abschnitt 1/2, NICHT Phase 7a aus Abschnitt 3/4,")
    print("sofern cooperative_sleep_wake_state.state bereits 'wake' oder 'sleep' ist.")
    print("Das bedeutet: Ein Schlafzustand von Phase 7a allein macht die GUI/den")
    print("Mood-Indikator NICHT 'schlaeft' anzeigen, wenn die kooperative Autoritaet")
    print("gleichzeitig 'wake' meldet.")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
