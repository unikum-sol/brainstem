# -*- coding: utf-8 -*-
"""BrainStem - Diagnose: Ist Cortisol Stufe 2 aktiv, und lief sie stabil?

BRAINSTEM_CORTISOL_STAGE2_DIAGNOSTIC_V1

Rein lesend, aendert NICHTS an der Datenbank. Kein Schreibzugriff, keine
Transaktion. Kann sicher NEBEN einem laufenden Autonomes Lernen oder
Drift-Test ausgefuehrt werden (kurzer Timeout, bricht sofort ab statt zu
warten, falls die DB gerade beschaeftigt ist).

Hintergrund: Direkte Codepruefung von
v8_phase7cort_stability_watch_release.py zeigte, dass WATCH_PARAMS bereits
"stage": 2 als Standardwert enthaelt und _apply_stage2_nudges() bei JEDEM
Zyklus automatisch aufgerufen wird -- Cortisol Stufe 2 ist demnach bereits
aktiv, nicht mehr im reinen Beobachtermodus. Dieses Skript prueft, ob sie
in der Praxis auch tatsaechlich (a) jemals eingegriffen hat, (b) dabei
stabil blieb (keine automatischen Rollbacks), und (c) ob "allostatic_load"
je hoch genug war, um ueberhaupt Eingriffe auszuloesen.

Ausfuehrung (aus dem Projekt-Root, mit main.py auf gleicher Ebene):
    python diagnose_cortisol_stage2.py
Optional mit explizitem DB-Pfad:
    python diagnose_cortisol_stage2.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3
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


def _count(con, table, where=""):
    if not _table_exists(con, table):
        return None
    try:
        sql = "SELECT COUNT(*) FROM " + table
        if where:
            sql += " WHERE " + where
        return int(con.execute(sql).fetchone()[0])
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
        print("  python diagnose_cortisol_stage2.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3")
        return 1

    # Kurzer Timeout: dieses Skript soll NIE einen laufenden Zyklus blockieren.
    con = sqlite3.connect(db_path, timeout=5)
    con.row_factory = sqlite3.Row

    section("1) CORTISOL_STATE - aktueller Gesamtzustand")
    cs = _kv(con, "cortisol_state")
    if not cs:
        print("KEINE Daten in cortisol_state gefunden -- Phase 7cort hat noch nie gelaufen.")
        con.close()
        return 0

    for k in ("stage", "cycle_count", "cortisol_level", "last_regime",
              "last_allostatic_load", "warmup_cycles", "cooldown", "cooldown_left",
              "nudge_cap", "cycle_budget",
              "stage2_applications", "stage2_rollbacks",
              "last_stage2_budget_used", "last_stage2_changes", "last_stage2_error"):
        print("  %-26s: %s" % (k, cs.get(k, "(fehlt)")))

    stage = str(cs.get("stage", "?"))
    applications = int(cs.get("stage2_applications", 0) or 0)
    rollbacks = int(cs.get("stage2_rollbacks", 0) or 0)

    print()
    if stage == "2":
        print("-> BESTAETIGT: Stage ist 2 (aktiver Regler, nicht reiner Beobachter).")
    else:
        print("-> Stage ist %s, NICHT 2 -- Stufe 2 ist auf diesem Datenbankstand nicht aktiv." % stage)

    section("2) HAT STUFE 2 JEMALS TATSAECHLICH EINGEGRIFFEN?")
    print("stage2_applications (Zyklen mit tatsaechlich angewendeter Aenderung):", applications)
    print("stage2_rollbacks (automatische Rollbacks wegen fehlgeschlagener Nachbedingung):", rollbacks)
    print()
    if applications == 0:
        print("-> Stufe 2 ist zwar AKTIV (stage=2), hat aber noch KEINEN einzigen echten")
        print("   Eingriff vorgenommen. Das bedeutet: allostatic_load hat bislang nie den")
        print("   'load_high'-Schwellenwert erreicht (siehe Abschnitt 3), ODER es gab nie")
        print("   eine passende Empfehlung (recommended). Stufe 2 ist damit technisch aktiv,")
        print("   aber PRAKTISCH NOCH UNGETESTET unter echter Last.")
    elif rollbacks == 0:
        print("-> BESTAETIGT: Stufe 2 hat %d mal tatsaechlich eingegriffen, dabei KEIN" % applications)
        print("   einziges Mal einen automatischen Rollback ausgeloest. Das spricht fuer")
        print("   einen stabilen, funktionierenden Regler unter echten Bedingungen.")
    else:
        ratio = rollbacks / max(1, applications + rollbacks)
        print("-> Stufe 2 hat %d mal eingegriffen UND dabei %d mal einen automatischen" % (applications, rollbacks))
        print("   Rollback ausgeloest (%.1f%% der Versuche). Das verdient eine genauere" % (ratio * 100))
        print("   Betrachtung von 'last_stage2_error' oben, bevor Stufe 2 als 'stabil'")
        print("   fuer die Graduierungs-Voraussetzung gilt.")

    section("3) WARUM (NICHT)? DER ALLOSTATIC-LOAD-VERLAUF")
    load_high = float(cs.get("load_high", 0.6) or 0.6)
    print("Aktueller load_high-Schwellenwert (ab hier duerfen Eingriffe stattfinden):", load_high)
    if not _table_exists(con, "stability_watch_events"):
        print("Tabelle stability_watch_events existiert nicht.")
    else:
        total_events = _count(con, "stability_watch_events")
        elevated_events = _count(con, "stability_watch_events", "elevated=1")
        print("Gesamtanzahl aufgezeichneter Zyklen:", total_events)
        print("Davon mit elevated=1 (allostatic_load >= load_high):", elevated_events)
        row = con.execute(
            "SELECT MAX(allostatic_load), AVG(allostatic_load) FROM stability_watch_events"
        ).fetchone()
        if row and row[0] is not None:
            print("Hoechster je gemessener allostatic_load: %.4f | Durchschnitt: %.4f" % (row[0], row[1] or 0.0))
        print()
        print("Letzte 10 Zyklen (neuester zuerst):")
        rows = con.execute(
            "SELECT cycle_index, allostatic_load, cortisol_level, regime, dominant_signal, "
            "elevated, recommended_json FROM stability_watch_events ORDER BY id DESC LIMIT 10"
        ).fetchall()
        for r in rows:
            rec_preview = (r["recommended_json"] or "{}")
            if len(rec_preview) > 40:
                rec_preview = rec_preview[:37] + "..."
            print("  cycle=%-8s load=%.4f cortisol=%.4f regime=%-8s dominant=%-24s elevated=%s rec=%s" % (
                r["cycle_index"], r["allostatic_load"], r["cortisol_level"],
                r["regime"], r["dominant_signal"], r["elevated"], rec_preview))

    section("4) ZUSAMMENFASSUNG FUER DIE GRADUIERUNGS-ENTSCHEIDUNG")
    print("Ihre eigene Roadmap-Bedingung fuer den Start der Hypothesen-Graduierung")
    print("lautet: 'Cortisol Stufe 2 aktiv UND stabil'.")
    print()
    print("  stage == 2:", stage == "2", "(technisch aktiv)")
    if applications > 0 and rollbacks == 0:
        print("  Praktisch erprobt und stabil: JA (%d Eingriffe, 0 Rollbacks)" % applications)
        print()
        print("-> Beide Teile der Bedingung sind nach dieser Diagnose erfuellt.")
    elif applications == 0:
        print("  Praktisch erprobt: NEIN (0 Eingriffe bislang)")
        print()
        print("-> 'Aktiv' ja, aber 'stabil unter echter Last erprobt' noch nicht belegt,")
        print("   da nie eine Gelegenheit zum Eingreifen bestand. Das ist kein Fehler,")
        print("   sondern koennte bedeuten, dass das System bislang schlicht nie in")
        print("   einen Zustand mit allostatic_load >= %.2f geraten ist." % load_high)
    else:
        print("  Praktisch erprobt, aber mit Rollbacks: siehe Abschnitt 2 fuer Details.")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
