# -*- coding: utf-8 -*-
"""BrainStem - Diagnose: Ist Hypothesen-Graduierung bereits aktiv, und
warum wurde (noch) nie graduiert?

BRAINSTEM_HYPOTHESIS_GRADUATION_DIAGNOSTIC_V1

Rein lesend, aendert NICHTS an der Datenbank. Kein Schreibzugriff, keine
Transaktion. Kann sicher NEBEN einem laufenden Autonomes Lernen oder
Drift-Test ausgefuehrt werden (kurzer Timeout, bricht sofort ab statt zu
warten, falls die DB gerade beschaeftigt ist).

Hintergrund: Direkte Codepruefung von
v8_stageb_guarded_hypothesis_graduation_release.py zeigte, dass die
Graduierungslogik (uncertain_hypothesis -> stable_hypothesis)
VOLLSTAENDIG implementiert ist, per autoload() fest in die Zykluskette
eingehaengt wird, und DEFAULTS["enabled"]="true" als Standardwert nutzt
-- genau wie bei Cortisol Stufe 2 koennte dieser Mechanismus also bereits
aktiv laufen, ohne dass das bisher bekannt war.

Dieses Skript prueft:
  1) Ist enabled=true, und wie viele Zyklen sind seit dem Start vergangen
     (Warm-up-Schwelle: 50)?
  2) Wie viele Hypothesen erfuellen aktuell die Mindestanzahl bestaetigter,
     verstaerkter Phase-7d-Konsolidierungs-Ueberlebenszyklen (Standard: 3)?
  3) Wurde jemals tatsaechlich graduiert (total_graduated,
     stageb_graduation_events)?
  4) Falls Kandidaten vorhanden sind, aber nie graduiert wurde: blockiert
     der _critic_gate systematisch, oder gab es schlicht nie Kandidaten?

WICHTIGER HINWEIS ZUR TRENNSCHAERFE (aus den Paper-Prinzipien
uebernommen: "Bedarf ist noch keine Verbindung"): Dieses Skript weist
"Kandidat mit genug Konsolidierungen" und "tatsaechlich graduiert" ganz
bewusst getrennt aus, nicht als einen einzigen Wert.

Ausfuehrung (aus dem Projekt-Root, mit main.py auf gleicher Ebene):
    python diagnose_hypothesis_graduation.py
Optional mit explizitem DB-Pfad:
    python diagnose_hypothesis_graduation.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3
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
        print("  python diagnose_hypothesis_graduation.py Z:\\Temp\\Ki_System\\BrainStem\\ki_memory.sqlite3")
        return 1

    # Kurzer Timeout: dieses Skript soll NIE einen laufenden Zyklus blockieren.
    con = sqlite3.connect(db_path, timeout=5)
    con.row_factory = sqlite3.Row

    section("1) STAGEB_GRADUATION_STATE - aktueller Gesamtzustand")
    st = _kv(con, "stageb_graduation_state")
    if not st:
        print("KEINE Daten in stageb_graduation_state gefunden -- die Graduierungs-")
        print("Phase hat noch nie gelaufen (Tabelle existiert nicht oder ist leer).")
        con.close()
        return 0

    for k in ("enabled", "warmup_cycles", "cycle_count", "minimum_7d_survivals",
              "promotion_budget", "total_graduated", "last_graduated",
              "fact_promotion", "direct_fact_writes", "direct_relation_writes",
              "question_writes", "mode"):
        print("  %-24s: %s" % (k, st.get(k, "(fehlt)")))

    enabled = str(st.get("enabled", "true")).lower() == "true"
    cycle_count = int(float(st.get("cycle_count", 0) or 0))
    warmup = int(float(st.get("warmup_cycles", 50) or 50))
    minimum = int(float(st.get("minimum_7d_survivals", 3) or 3))
    total_graduated = int(float(st.get("total_graduated", 0) or 0))

    print()
    print("-> enabled:", enabled, "| cycle_count:", cycle_count, "| warmup_cycles:", warmup)
    if enabled and cycle_count > warmup:
        print("-> BESTAETIGT: Graduierung ist aktiv UND der Warm-up (%d Zyklen) ist" % warmup)
        print("   laengst ueberschritten (aktuell Zyklus %d). Graduierung LAEUFT bereits" % cycle_count)
        print("   bei jedem Zyklus real mit -- unabhaengig davon, ob je etwas graduiert wurde.")
    elif enabled and cycle_count <= warmup:
        print("-> Graduierung ist aktiv, aber der Warm-up ist noch NICHT abgeschlossen")
        print("   (Zyklus %d von %d benoetigt)." % (cycle_count, warmup))
    else:
        print("-> Graduierung ist NICHT aktiv (enabled=false).")

    section("2) WIE VIELE HYPOTHESEN ERFUELLEN AKTUELL DIE KONSOLIDIERUNGS-SCHWELLE?")
    print("Voraussetzung: role='uncertain_hypothesis', status='active', UND mindestens")
    print("%d bestaetigte, VERSTAERKTE (reinforced=1) Phase-7d-Konsolidierungs-" % minimum)
    print("Ueberlebenszyklen in phase7d_consolidation_survivors.")
    print()
    if not _table_exists(con, "context_hypotheses"):
        print("Tabelle context_hypotheses existiert nicht.")
    elif not _table_exists(con, "phase7d_consolidation_survivors"):
        print("Tabelle phase7d_consolidation_survivors existiert NICHT.")
        print("-> Das ist die strukturelle Ursache, falls es nie Kandidaten gab:")
        print("   OHNE diese Tabelle liefert _candidates() im Code IMMER eine leere")
        print("   Liste zurueck (siehe 'if not _table_exists(...): return []').")
    else:
        cols_h = set(_columns(con, "context_hypotheses"))
        role_expr = "COALESCE(role,'')" if "role" in cols_h else "''"
        status_expr = "COALESCE(status,'active')" if "status" in cols_h else "'active'"
        total_uncertain = _count(con, "context_hypotheses", role_expr + "='uncertain_hypothesis'")
        total_stable = _count(con, "context_hypotheses", role_expr + "='stable_hypothesis'")
        print("Hypothesen mit role='uncertain_hypothesis':", total_uncertain)
        print("Hypothesen mit role='stable_hypothesis' (bereits graduiert):", total_stable)
        print()
        # Direkter Nachbau der _candidates()-Query aus dem Original-Code, rein lesend.
        try:
            q = (
                "SELECT h.id, COUNT(DISTINCT s.cycle_index) AS survived, "
                "AVG(COALESCE(s.final_consistency,0)) AS consistency "
                "FROM context_hypotheses h JOIN phase7d_consolidation_survivors s "
                "ON s.source_table='context_hypotheses' AND s.source_id=h.id "
                "WHERE " + role_expr + "='uncertain_hypothesis' AND " + status_expr + "='active' "
                "AND COALESCE(s.reinforced,0)=1 "
                "GROUP BY h.id HAVING COUNT(DISTINCT s.cycle_index)>=? "
                "ORDER BY survived DESC, consistency DESC, h.id ASC LIMIT 64"
            )
            candidates = con.execute(q, (minimum,)).fetchall()
            print("Aktuelle Kandidaten, die JETZT die Graduierungs-Schwelle erfuellen:", len(candidates))
            if candidates:
                print("Erste 5 (nach Ueberlebenszyklen sortiert):")
                for r in candidates[:5]:
                    print("  hypothesis_id=%-8s survived_cycles=%s consistency=%.4f" % (
                        r["id"], r["survived"], r["consistency"] or 0.0))
            else:
                print("-> KEINE aktuellen Kandidaten gefunden. Entweder gibt es keine")
                print("   uncertain_hypothesis-Eintraege mit genug bestaetigten,")
                print("   verstaerkten Konsolidierungszyklen, oder")
                print("   phase7d_consolidation_survivors ist leer/unzureichend befuellt.")
        except Exception as exc:
            print("Kandidaten-Abfrage fehlgeschlagen:", type(exc).__name__, str(exc))

    section("3) WURDE JEMALS TATSAECHLICH GRADUIERT?")
    print("total_graduated (aus stageb_graduation_state):", total_graduated)
    events_count = _count(con, "stageb_graduation_events")
    print("Gesamtanzahl aufgezeichneter Graduierungs-Events:", events_count)
    if not _table_exists(con, "stageb_graduation_events"):
        print("Tabelle stageb_graduation_events existiert nicht.")
    elif events_count:
        graduated_count = _count(con, "stageb_graduation_events", "decision='graduated_to_stable_hypothesis'")
        blocked_count = _count(con, "stageb_graduation_events", "decision='blocked_by_critic'")
        print("Davon 'graduated_to_stable_hypothesis':", graduated_count)
        print("Davon 'blocked_by_critic':", blocked_count)
        print()
        print("Letzte 10 Events (neuester zuerst):")
        rows = con.execute(
            "SELECT cycle_index, hypothesis_id, survival_cycles, critic_allowed, "
            "critic_reason, decision FROM stageb_graduation_events ORDER BY id DESC LIMIT 10"
        ).fetchall()
        for r in rows:
            print("  cycle=%-8s hyp=%-8s survived=%-4s critic_allowed=%s reason=%-30s decision=%s" % (
                r["cycle_index"], r["hypothesis_id"], r["survival_cycles"],
                r["critic_allowed"], (r["critic_reason"] or "")[:30], r["decision"]))
        if events_count > 0 and graduated_count == 0:
            print()
            print("-> WICHTIG: Es gab bereits %d Bewertungs-Events, aber KEINE einzige" % events_count)
            print("   tatsaechliche Graduierung. Pruefen Sie die 'critic_reason'-Spalte")
            print("   oben, um zu sehen, WARUM der _critic_gate jeden Kandidaten")
            print("   blockiert hat.")
    else:
        print("-> Es gab noch KEIN einziges Bewertungs-Event. Das bedeutet: entweder")
        print("   wurde die Graduierungs-Phase noch nie mit mindestens einem")
        print("   qualifizierten Kandidaten durchlaufen, oder sie laeuft technisch noch")
        print("   gar nicht mit (siehe Abschnitt 1).")

    section("4) ZUSAMMENFASSUNG")
    if not st:
        print("Graduierung hat noch nie gelaufen.")
    else:
        if enabled and cycle_count > warmup and total_graduated > 0:
            print("Graduierung ist aktiv, Warm-up abgeschlossen, UND es wurden bereits")
            print("%d Hypothese(n) real graduiert. Dieser Mechanismus laeuft." % total_graduated)
        elif enabled and cycle_count > warmup and total_graduated == 0:
            print("Graduierung ist aktiv und Warm-up abgeschlossen, aber es wurde noch")
            print("NIE graduiert. Die Ursache liegt entweder bei fehlenden Kandidaten")
            print("(Abschnitt 2) oder bei einer durchgehenden Blockade durch den")
            print("_critic_gate (Abschnitt 3) -- bitte beide Abschnitte oben pruefen,")
            print("um zwischen diesen beiden Erklaerungen zu unterscheiden.")
        elif enabled and cycle_count <= warmup:
            print("Graduierung ist aktiv, aber der Warm-up ist noch nicht abgeschlossen.")
        else:
            print("Graduierung ist derzeit nicht aktiv.")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
