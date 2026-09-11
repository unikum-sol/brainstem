# -*- coding: utf-8 -*-
"""BrainStem - Diagnose: Critic-Snapshot-Struktur und Graduierungs-Pipeline

BRAINSTEM_GRADUATION_PIPELINE_DIAGNOSTIC_V1

Rein lesend, aendert NICHTS an der Datenbank. Kein Schreibzugriff, keine
Transaktion. Kann sicher NEBEN einem laufenden Autonomes Lernen oder
Drift-Test ausgefuehrt werden (kurzer Timeout, bricht sofort ab statt zu
warten, falls die DB gerade beschaeftigt ist).

Hintergrund: Direkte Codepruefung von
v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release.py
zeigte, dass _critic_gate() IMMER "no_critic_snapshot" (und damit
allowed=True) zurueckgibt, solange kein aktiver Eintrag in
phase6b_critic_snapshot existiert. Ein Snapshot kann wiederum NUR
entstehen, wenn state_change_allowed=1 war -- was direkt an
outcome_observation_available haengt, was wiederum direkt an
phase5g_experiment_outcomes (bekannt strukturell leer) gekoppelt ist.
Das bedeutet: der Critic-Gate der Hypothesen-Graduierung lief bislang
IMMER im reinen Durchwink-Modus, nicht wegen eines Fehlers, sondern als
direkte, bisher unbekannte Folgeerscheinung derselben Stage-B-Grenze.

Dieses Skript beantwortet zusaetzlich die zweite offene Frage: Warum gab
es zwischen Zyklus 1.641 und dem aktuellen Stand (11.500+) keine einzige
weitere Graduierung? Dafuer wird unterschieden zwischen:
  a) natuerlicher Seltenheit (die Anzahl frisch qualifizierender
     Kandidaten sinkt organisch, weil die Grundgesamtheit waechst und
     3-fache verstaerkte Konsolidierung ohnehin selten ist), und
  b) einer echten Blockade in der zugrunde liegenden Pipeline
     (phase7d_consolidation_survivors erzeugt selbst keine neuen
     verstaerkten Ueberlebenszyklen mehr).

Ausfuehrung (aus dem Projekt-Root, mit main.py auf gleicher Ebene):
    python diagnose_graduation_pipeline.py
Optional mit explizitem DB-Pfad:
    python diagnose_graduation_pipeline.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3
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
        print("  python diagnose_graduation_pipeline.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3")
        return 1

    # Kurzer Timeout: dieses Skript soll NIE eine laufende Lernsession blockieren.
    con = sqlite3.connect(db_path, timeout=5)
    con.row_factory = sqlite3.Row

    section("1) CRITIC-SNAPSHOT STRUKTUR - lief der Critic je mit echter Grundlage?")
    snap_total = _count(con, "phase6b_critic_snapshot")
    snap_active = _count(con, "phase6b_critic_snapshot", "active=1")
    print("Gesamtanzahl je erstellter Critic-Snapshots:", snap_total)
    print("Davon aktuell aktiv (active=1):", snap_active)

    allowed_total = _count(con, "phase6b_plasticity_adjustments", "state_change_allowed=1")
    adj_total = _count(con, "phase6b_plasticity_adjustments")
    p5g_count = _count(con, "phase5g_experiment_outcomes")
    print()
    print("phase6b_plasticity_adjustments gesamt:", adj_total,
          "| davon state_change_allowed=1:", allowed_total)
    print("phase5g_experiment_outcomes Zeilenanzahl:", p5g_count)
    print()
    if snap_total is None:
        print("-> Tabelle phase6b_critic_snapshot existiert nicht -- Phase 6b hat")
        print("   noch nie gelaufen. Keine weitere Aussage moeglich.")
    elif snap_total == 0:
        print("-> BESTAETIGT: Es wurde noch NIE ein Critic-Snapshot erstellt.")
        print("   Das erklaert vollstaendig, warum _critic_gate() bislang IMMER")
        print("   'no_critic_snapshot' (und damit allowed=True, KEINE echte Pruefung)")
        print("   zurueckgegeben hat -- fuer JEDE Graduierungsentscheidung bisher,")
        print("   nicht nur fuer Hypothesen-Graduierung, sondern auch fuer jede")
        print("   Phase-6b-Plastizitaetsanpassung.")
        if p5g_count == 0:
            print()
            print("   Ursache strukturell bestaetigt: state_change_allowed war deshalb")
            print("   nie 1 (siehe oben, %s von %s), weil phase5g_experiment_outcomes" % (
                allowed_total, adj_total))
            print("   leer ist -- exakt dieselbe Stage-B-Sicherheitsgrenze, die bereits")
            print("   fuer effectiveness/exploration_bias/plasticity_level bekannt war.")
    else:
        print("-> Es gab bereits %d echte(n) Critic-Snapshot(s). Der Critic-Gate hat" % snap_total)
        print("   damit zumindest zeitweise eine echte Vergleichsgrundlage gehabt.")

    section("2) AKTUELLE VERTEILUNG: WIE NAH SIND UNSICHERE HYPOTHESEN AN DER SCHWELLE?")
    if not _table_exists(con, "context_hypotheses") or not _table_exists(con, "phase7d_consolidation_survivors"):
        print("Benoetigte Tabellen fehlen.")
    else:
        cols_h = set(_columns(con, "context_hypotheses"))
        role_expr = "COALESCE(role,'')" if "role" in cols_h else "''"
        status_expr = "COALESCE(status,'active')" if "status" in cols_h else "'active'"
        total_uncertain = _count(con, "context_hypotheses", role_expr + "='uncertain_hypothesis'")
        print("Gesamtanzahl role='uncertain_hypothesis':", total_uncertain)
        print()
        try:
            # Effizient: zuerst auf der (viel kleineren) Survivor-Tabelle aggregieren,
            # danach erst per Primaerschluessel-Join gegen context_hypotheses filtern
            # (kein Vollscan der 1,59-Mio.-Zeilen-Tabelle).
            q = (
                "SELECT CASE WHEN t.survived>=3 THEN '3+' WHEN t.survived=2 THEN '2' "
                "WHEN t.survived=1 THEN '1' ELSE '0' END AS bucket, COUNT(*) AS n "
                "FROM (SELECT source_id, COUNT(DISTINCT cycle_index) AS survived "
                "FROM phase7d_consolidation_survivors "
                "WHERE source_table='context_hypotheses' AND COALESCE(reinforced,0)=1 "
                "GROUP BY source_id) t "
                "JOIN context_hypotheses h ON h.id=t.source_id "
                "WHERE " + role_expr + "='uncertain_hypothesis' AND " + status_expr + "='active' "
                "GROUP BY bucket ORDER BY bucket"
            )
            rows = con.execute(q).fetchall()
            found = {r["bucket"]: r["n"] for r in rows}
            with_any_survivor = sum(found.values())
            print("Verteilung der VERSTAERKTEN (reinforced=1) Konsolidierungs-Ueberlebenszyklen")
            print("unter aktuell aktiven uncertain_hypothesis-Eintraegen:")
            for bucket in ("1", "2", "3+"):
                print("  %s bestaetigte Zyklen: %s Hypothese(n)" % (bucket, found.get(bucket, 0)))
            zero_survivors = (total_uncertain or 0) - with_any_survivor
            print("  0 bestaetigte Zyklen (kein einziger Survivor-Eintrag): %d Hypothese(n)" % max(0, zero_survivors))
            print()
            near_threshold = found.get("2", 0)
            if near_threshold > 0:
                print("-> Es gibt %d Hypothese(n), die BEREITS 2 von 3 noetigen Zyklen erreicht" % near_threshold)
                print("   haben -- diese stehen kurz vor der Qualifikation. Das spricht eher")
                print("   fuer 'noch nicht lange genug beobachtet' als fuer eine Blockade.")
            else:
                print("-> KEINE Hypothese hat aktuell auch nur 2 von 3 noetigen Zyklen erreicht.")
                print("   Das ist ein staerkeres Indiz dafuer, dass der Nachschub an neuen")
                print("   Kandidaten ins Stocken geraten sein koennte (siehe Abschnitt 3/4).")
        except Exception as exc:
            print("Verteilungs-Abfrage fehlgeschlagen:", type(exc).__name__, str(exc))

    section("3) GRADUIERUNGS-RATE UEBER DIE ZEIT (pro 1000-Zyklen-Fenster)")
    if not _table_exists(con, "stageb_graduation_events"):
        print("Tabelle stageb_graduation_events existiert nicht.")
    else:
        try:
            rows = con.execute(
                "SELECT (cycle_index/1000)*1000 AS window_start, "
                "COUNT(*) AS total_events, "
                "SUM(CASE WHEN decision='graduated_to_stable_hypothesis' THEN 1 ELSE 0 END) AS graduated "
                "FROM stageb_graduation_events GROUP BY window_start ORDER BY window_start"
            ).fetchall()
            print("Fenster-Start | Bewertungen gesamt | davon graduiert")
            for r in rows:
                print("  %-13s | %-19s | %s" % (r["window_start"], r["total_events"], r["graduated"]))
            if rows and rows[-1]["graduated"] == 0 and any(r["graduated"] > 0 for r in rows[:-1]):
                print()
                print("-> Bestaetigt: die Graduierungsrate ist in den juengsten Fenstern auf 0")
                print("   gefallen, nachdem sie in frueheren Fenstern positiv war.")
        except Exception as exc:
            print("Zeitfenster-Abfrage fehlgeschlagen:", type(exc).__name__, str(exc))

    section("4) WIRD DIE ZUGRUNDE LIEGENDE KONSOLIDIERUNGS-PIPELINE SELBST NOCH GESPEIST?")
    print("Praeft: entstehen weiterhin laufend NEUE verstaerkte (reinforced=1)")
    print("Konsolidierungs-Ueberlebenseintraege in phase7d_consolidation_survivors,")
    print("unabhaengig davon, ob daraus je eine vollstaendige 3er-Kette wird?")
    if not _table_exists(con, "phase7d_consolidation_survivors"):
        print("Tabelle phase7d_consolidation_survivors existiert nicht.")
    else:
        cols_s = set(_columns(con, "phase7d_consolidation_survivors"))
        if "cycle_index" in cols_s:
            try:
                # BRAINSTEM_GRADUATION_DIAG_GAP_DETECTION_FIX_V1: a simple
                # GROUP BY only returns windows that actually contain rows.
                # If the pipeline went completely silent for the most
                # recent thousands of cycles, that silence would otherwise
                # be invisible (no "empty" row is ever produced to show
                # it). Fixed by explicitly comparing the highest recorded
                # cycle_index here against an independent, live cycle
                # reference from another frequently-updated state table,
                # so a large gap is detected even when every window that
                # DOES exist still looks "healthy" in isolation.
                current_cycle_ref = None
                for state_table, key in (
                    ("stageb_graduation_state", "cycle_count"),
                    ("phase6b_state", "cycle_count"),
                    ("cortisol_state", "cycle_count"),
                ):
                    if _table_exists(con, state_table):
                        row = con.execute(
                            "SELECT value FROM " + state_table + " WHERE key=?", (key,)
                        ).fetchone()
                        if row is not None:
                            try:
                                current_cycle_ref = int(float(row[0]))
                                break
                            except Exception:
                                pass

                rows = con.execute(
                    "SELECT (cycle_index/1000)*1000 AS window_start, COUNT(*) AS total, "
                    "SUM(CASE WHEN COALESCE(reinforced,0)=1 THEN 1 ELSE 0 END) AS reinforced_n "
                    "FROM phase7d_consolidation_survivors "
                    "WHERE source_table='context_hypotheses' "
                    "GROUP BY window_start ORDER BY window_start"
                ).fetchall()
                max_cycle_row = con.execute(
                    "SELECT MAX(cycle_index) FROM phase7d_consolidation_survivors "
                    "WHERE source_table='context_hypotheses'"
                ).fetchone()
                max_cycle_seen = max_cycle_row[0] if max_cycle_row and max_cycle_row[0] is not None else None

                print()
                print("Fenster-Start | Survivor-Eintraege gesamt | davon verstaerkt (reinforced=1)")
                shown = rows[-15:] if len(rows) > 15 else rows
                for r in shown:
                    print("  %-13s | %-25s | %s" % (r["window_start"], r["total"], r["reinforced_n"]))
                if len(rows) > 15:
                    print("  (nur die letzten 15 von %d Fenstern gezeigt)" % len(rows))

                print()
                print("Hoechster in phase7d_consolidation_survivors vorkommender cycle_index:", max_cycle_seen)
                print("Aktueller, unabhaengig ermittelter Zyklus-Referenzwert:", current_cycle_ref)

                gap = None
                if max_cycle_seen is not None and current_cycle_ref is not None:
                    gap = current_cycle_ref - max_cycle_seen
                    print("Differenz (Referenz - hoechster Survivor-Eintrag):", gap)

                if gap is not None and gap > 500:
                    print()
                    print("-> BESTAETIGT (Luecken-Erkennung): Der letzte Survivor-Eintrag liegt %d" % gap)
                    print("   Zyklen hinter dem aktuellen Stand zurueck. Die Pipeline erzeugt seit")
                    print("   geraumer Zeit KEINE neuen verstaerkten Ueberlebenseintraege mehr --")
                    print("   das ist ein starkes Indiz fuer eine echte Blockade, nicht nur")
                    print("   natuerliche Seltenheit.")
                elif rows:
                    recent_reinforced = sum(r["reinforced_n"] for r in rows[-3:]) if len(rows) >= 3 else sum(r["reinforced_n"] for r in rows)
                    print()
                    print("-> Keine grosse Zeitluecke erkannt. Die Pipeline erzeugt weiterhin")
                    print("   laufend neue verstaerkte Ueberlebenseintraege (%d in den juengsten" % recent_reinforced)
                    print("   gezeigten Fenstern). Das spricht dafuer, dass eine vollstaendige")
                    print("   3er-Kette pro Hypothese schlicht selten ist, nicht dass die Pipeline")
                    print("   blockiert waere.")
                else:
                    print()
                    print("-> Keine Survivor-Eintraege fuer context_hypotheses gefunden.")
            except Exception as exc:
                print("Zeitfenster-Abfrage fehlgeschlagen:", type(exc).__name__, str(exc))
        else:
            total_s = _count(con, "phase7d_consolidation_survivors")
            reinforced_s = _count(con, "phase7d_consolidation_survivors", "COALESCE(reinforced,0)=1")
            print("Keine cycle_index-Spalte vorhanden fuer Zeitfenster-Analyse.")
            print("Gesamtanzahl Survivor-Eintraege:", total_s, "| davon verstaerkt:", reinforced_s)

    section("5) ZUSAMMENFASSUNG")
    print("Kritischer struktureller Fund (Abschnitt 1): der Critic-Gate der")
    print("Hypothesen-Graduierung lief bislang OHNE JEDE echte inhaltliche Pruefung --")
    print("nicht wegen eines Fehlers, sondern weil ein Critic-Snapshot strukturell")
    print("erst entstehen kann, wenn phase5g_experiment_outcomes Daten enthaelt.")
    print("Alle bisherigen 36 Graduierungen wurden damit ausschliesslich durch das")
    print("Konsolidierungs-Kriterium (>=3 verstaerkte Ueberlebenszyklen) abgesichert,")
    print("nicht zusaetzlich durch eine Abweichungspruefung gegen eine Referenz.")
    print()
    print("Zur Frage 'natuerliche Seltenheit vs. Blockade' (Abschnitte 2-4): bitte")
    print("die konkreten Zahlen oben gemeinsam auswerten -- eine schnelle Regel:")
    print("  - Abschnitt 4 zeigt weiterhin aktiven Nachschub UND Abschnitt 2 zeigt")
    print("    Hypothesen kurz vor der Schwelle -> eher natuerliche Seltenheit.")
    print("  - Abschnitt 4 zeigt versiegten Nachschub ODER Abschnitt 2 zeigt gar")
    print("    keine Hypothese nahe der Schwelle -> eher eine echte Blockade,")
    print("    die eine gezielte Ursachensuche in Phase 7d rechtfertigt.")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
