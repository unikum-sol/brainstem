# BrainStem: Projekt- und Funktionsstatus

**Stand:** 12.11.2026, 09:49 Uhr
**Umfang:** Code (`ki_system/`, `main.py`), Produktionsdatenbank `ki_memory.sqlite3`, Testergebnisse vom 12.11.2026

---

## 1. Zusammenfassung

| Bereich | Status |
|---|---|
| Lernkette | 36 Phasen, alle laden fehlerfrei, Kettenspitze: Stage-B Question-Chunk-Feedback |
| Lernen auf allen Ebenen | aktiv: Sätze, Wortgrenzen und Relationen konsolidieren und graduieren |
| Selbstkorrektur | aktiv und nachgewiesen: Cue-Konkurrenz, Revision, Rücknahme von Fakten, Rekonsolidierung |
| Emergenz von Relationen, Kategorien, Fragen | aktiv und produktiv |
| Botenstoffe | 12 Botenstoffe aktiv, 19 neuromodulierte Schwellen und Budgets |
| Systemtest | alle 7 Prüfpunkte OK |
| Geschwindigkeit | ca. 1,3 bis 1,6 s pro Zyklus auf Produktionsgröße, ca. 0,9 s auf kleinem Korpus |
| Produktionsdatenbank | 5,57 GB, Integritätsprüfung OK; die neuen Mechanismen sind darauf noch nicht gelaufen |

---

## 2. Code-Stand

- **Paket:** `ki_system`, 59 Python-Module, zusammen mit `main.py` 19.022 Zeilen
- **Einstieg:** `python main.py --gui` (Admin-GUI), `python main.py --user-gui` (lesende Dialog-GUI)
- **Systemprüfung:** `python -m ki_system.systemtest` (arbeitet auf einer Kopie der Datenbank)
- **Lern-Reset mit Korpuserhalt:** GUI-Button oder `python -m ki_system.reset_learning --apply`
- Alle Module kompilieren fehlerfrei.

---

## 3. Lernkette (Ausführungsreihenfolge)

Jede Phase ruft zuerst die vorher registrierte Phase auf und erledigt danach ihren eigenen Teil. Dadurch entspricht die Ausführungsreihenfolge der Registrierungsreihenfolge in `phase_registry.py`.

| Nr. | Phase | Funktion | Status |
|---|---|---|---|
| 1 | Context Observation | liest Textabschnitte, zerlegt sie in Sätze, legt Satz-Hypothesen an oder beobachtet sie erneut (Belegzahl, Konfidenz) | aktiv |
| 2 | Phase 0 Lexical | Wortgrenzen aus dem ungeteilten Zeichenstrom per Verzweigungsentropie | aktiv |
| 3 | Phase 5b | verfeinert Lesestrategien aus Ergebnissen, hartnäckigen Lücken und Clustern; diversifiziert die Leseauswahl | aktiv, feste Steuerwerte (siehe 9) |
| 4 | Phase 5c | bewertet Lernergebnisse und gruppiert interne Lernfragen | aktiv |
| 5 | Phase 5d | Beobachtungs- und Strategiegedächtnis | aktiv, teils feste Ersatzwerte (siehe 9) |
| 6 | Stage-B Gap Detection | erkennt Lücken: „stalled“ (oft gesehen, nie gefestigt) und „contested“ (Cue-Konkurrenz); Habituation und Dishabituation | aktiv |
| 7 | Phase 5e | plant Kontexterweiterungen rund um Lücken und erhöht die Priorität benachbarter Abschnitte | aktiv |
| 8 | Phase 5f | misst die Wirksamkeit der Kontextfenster und passt sie an | aktiv, feste Steuerwerte (siehe 9) |
| 9 | Phase 5g | wählt Kontextstrategien aus und führt das Experimentgedächtnis | aktiv, teils feste Ersatzwerte (siehe 9) |
| 10 | Phase 5h | wertet Strategie-Experimente aus und lernt daraus (Strategiegedächtnis) | aktiv, feste Steuerwerte (siehe 9) |
| 11 | Phase 5i | diversifiziert Strategien anhand der Ergebnisse | aktiv |
| 12 | Phase 6a | Schlaf-Replay und Meta-Plastizität; berechnet Dopamin, Serotonin, Noradrenalin, Acetylcholin aus dem Replay (phasisch) und mischt den tonischen Zielwert bei | aktiv |
| 13 | Phase 6b | misst die Wirksamkeit des Replays, passt die Plastizität an, Critic-Gate | aktiv |
| 14 | Phase 6c | hält Bias-Werte über Zyklen und regelt Meta-Parameter selbst | aktiv |
| 15 | Phase 6d | Sättigungs-Homöostase (gleitende Schwelle) und Meta-Metaplastizität | aktiv |
| 16 | Phase 7a | Adenosin: Schlafdruck mit gesteuerter Entladung im Schlaf | aktiv |
| 17 | Phase 7b | Endocannabinoide: 2-AG als schnelle Bremse, Anandamid als langsame Rückführung gesättigter Werte | aktiv |
| 18 | Phase 7b1 | Wake-Chain-Brücke: führt 6a bis 7b in fester Reihenfolge aus | aktiv |
| 19 | Phase 7c | adaptive Grenzen, sanftes Abschneiden an Grenzen, Glutamat-GABA-Gleichgewicht | aktiv |
| 20 | Connection Accelerator | setzt schnelle SQLite-Einstellungen für jede neue Verbindung | aktiv |
| 21 | Phase 7d | Tiefschlaf-Konsolidierung mit priorisiertem Replay (siehe 4.1) | aktiv |
| 22 | Phase 7e | Histamin: Wachheit, Gegenspieler zu Adenosin | aktiv |
| 23 | Phase 7f | Orexin: Lese-Ausdauer und Neugier | aktiv |
| 24 | Phase 7g | BDNF: aktivitätsabhängiges Wachstum und Festigung | aktiv |
| 25 | Phase 7cort | Cortisol: Stabilitätswächter, Stufe 2 (vorsichtiger Regler) | aktiv, im Betrieb ruhig |
| 26 | Cooperative Core | gemeinsame Dynamik der sechs Kern-Botenstoffe, Schlaf-Wach-Steuerung | aktiv |
| 27 | Stage-B Graduation | höchstens eine Graduierung pro Zyklus, Rollen konkurrieren über divisive Normalisierung | aktiv |
| 28 | Stage-B Contradiction Detection | entscheidet Cue-Konkurrenzen nach Belegen; zeichnet ungeprüfte Oberflächen-Kontraste auf | aktiv |
| 29 | Stage-B Hypothesis Revision | stuft unterlegene, gefestigte Hypothesen zurück, schließt die Lücke | aktiv |
| 30 | Stage-B Fact Promotion | graduierte Satz- und Wortgrenzen-Hypothesen werden Fakten; Rücknahme bei Revision | aktiv |
| 31 | Phase 0b Relational Binding | bindet gemeinsam auftretende Elemente (PMI, Richtung aus Position) | aktiv |
| 32 | Stage-B Relation Promotion | graduierte Relations-Hypothesen werden Relationen | aktiv |
| 33 | Stage-B Ontology Cluster Observation | Label Propagation über den Relationsgraphen, Prototyp-Anker | aktiv |
| 34 | Stage-B Ontology Promotion | stabile Cluster werden Ontologie-Einträge (Mitgliedschaft) | aktiv |
| 35 | Stage-B Question Promotion | hartnäckige Lücken werden Fragen | aktiv |
| 36 | Stage-B Question-Chunk Feedback | offene Fragen lenken das Lesen (Quelle und Volltextsuche) | aktiv |

---

## 4. Zentrale Mechanismen

### 4.1 Priorisiertes Replay (Phase 7d)

| Element | Funktion | Kopplung |
|---|---|---|
| Spur „Anker“ | gefestigtes Wissen wird verschränkt mit abgespielt und so vor Überschreiben geschützt | Serotonin |
| Spur „markierte Überlebende“ | Hypothesen mit 1 bis 2 Konsolidierungen, Markierung verfällt nach einem Zeitfenster | Dopamin (Anteil und Lebensdauer der Markierung) |
| Spur „neu“ | pro Rolle gezogen: teils aus kürzlich gesehenem Material, teils zufällig über den ganzen Bestand | Noradrenalin (Anteil), Dopamin (Anteil kürzlich gesehen) |
| Startaktivität | aus der Wiederholungsgeschichte der Hypothese (häufig Gesehenes festigt sich eher) | |
| Auslese | Schwelle innerhalb jeder Population (Anker, Strategie-Experimente, Hypothesen) | GABA, Glutamat, Acetylcholin |
| Rollenanteile | Sätze 50 %, Relationen 25 %, Wortgrenzen 25 % der neuen Plätze, ungenutzte Plätze gehen an die anderen Rollen | |

**Status:** aktiv. Im 150-Zyklen-Test erreichte die Graduierung das vorgesehene Budget von einer Graduierung pro Zyklus.

### 4.2 Selbstkorrektur durch Cue-Konkurrenz

| Schritt | Modul | Status |
|---|---|---|
| Gelernter Hinweisreiz: kürzestes Präfix, das an einer gelernten Wortgrenze endet und einen Mindestanteil des Musters abdeckt (Anteil über Acetylcholin) | `v8_cue_competition.py` | aktiv |
| Konkurrenten: andere beobachtete Vervollständigungen desselben Cues | Gap Detection | aktiv |
| Entscheidung allein nach Belegen: „resolvable“, „confirmed“, „open“; Schwelle über Noradrenalin | Contradiction Detection | aktiv |
| Rückstufung der unterlegenen Hypothese, Schließen der Lücke | Hypothesis Revision | aktiv |
| Rücknahme des Fakts | Fact Promotion | aktiv |
| Rekonsolidierung: nach einer Revision zählen nur neue Konsolidierungen | Graduation | aktiv |

**Nachweis:** Ein Testszenario mit eindeutigem Konkurrenten wird korrigiert, ein knappes Szenario bleibt unverändert. In Lernläufen auf echten Wikipedia-Abschnitten traten Korrekturen ohne künstlichen Anstoß auf, z. B. Cue „August“ (gespeichert 1 Beleg, Konkurrent 6) und Cue „April 20“ (1 gegen 3). Zurückgestufte Hypothesen graduierten nicht sofort erneut.

### 4.3 Emergenz-Ebenen

| Ebene | Funktion | Status |
|---|---|---|
| Wortgrenzen | Verzweigungsentropie über Kontext der Länge 3, Mindestbeobachtungen 8, Schwelle 1,0 Bit | aktiv, nimmt mit eigener Quote an der Konsolidierung teil |
| Relationen | PMI-Existenztest, Richtung aus Positionsasymmetrie (Schwelle für Deutsch 0,72) | aktiv |
| Kategorien | Label Propagation, Prototyp als Anker, Platzhalter-Relation `member_of_cluster` | aktiv |
| Fragen | Promotion hartnäckiger Lücken, Priorität über Dopamin und Acetylcholin | aktiv |
| Lese-Rückkopplung | Quelle der Frage und per Volltextsuche gefundene Abschnitte erhalten höhere Priorität | aktiv |
| Habituation | unproduktive Lücken werden umkehrbar „habituated“ | aktiv |

### 4.4 Neuromodulierte Schwellen und Budgets

19 Kopplungen; jede liefert beim Neutralwert 0,5 genau den kalibrierten Grundwert.

| Kopplung | Botenstoff |
|---|---|
| Existenzschwelle der Lückenerkennung | Noradrenalin |
| Habituationsschwelle | Serotonin |
| Existenzschwelle der Relationsbindung | Noradrenalin |
| Richtungsschwelle der Relationsbindung | Acetylcholin |
| Revisionsbudget | Acetylcholin |
| Entscheidungsverhältnis der Cue-Konkurrenz | Noradrenalin |
| Cue-Länge | Acetylcholin |
| Rollendruck bei der Graduierung | Acetylcholin |
| Temperatur der divisiven Normalisierung | GABA |
| Replay-Anteile Anker / markiert / neu | Serotonin / Dopamin / Noradrenalin |
| Lebensdauer der Markierung, Anteil kürzlich gesehener Proben | Dopamin |
| Stabilitätsserie der Kategorien | Serotonin |
| Mindestgröße der Kategorien (Richtung wird aus Ergebnissen gelernt) | Noradrenalin |
| Überlappungsschwelle der Kategorien | Dopamin |
| Budget der Kategorie-Promotion | Acetylcholin |
| Existenzschwelle der Fragen | Noradrenalin |
| Priorität der Fragen | Dopamin, Acetylcholin |
| Stärke der Lese-Rückkopplung | über die Priorität der Frage |
| Konsolidierungsschranke in Phase 7d | Acetylcholin |

### 4.5 Weitere Module

| Modul | Funktion | Status |
|---|---|---|
| `autonomous.py` | Kern der Lernschleife; die Kette wird von der Registry eingehängt | aktiv |
| `phase_registry.py` | Ladereihenfolge, Fehlererfassung, Selbstprüfung der Kette | aktiv |
| `db_bootstrap.py` | zentrales, idempotentes Schema: Tabellen, Spalten, Indizes, Ausdrucks-Indizes | aktiv |
| `db_runtime.py` | konsistente Datenbank-Schnappschüsse | aktiv |
| `memory.py` | Datenbankzugriff, Dokumente und Abschnitte, Volltextindex | aktiv |
| `ingest.py` | Import von ZIM, TXT, PDF, Fortsetzen nach Abbruch | aktiv |
| `search.py`, `dialogue.py`, `text_utils.py`, `wiki_quality.py` | Suche, Antwort, Dialog, neutrale Texthilfen ohne Wortfilter | aktiv |
| `semantic_evidence.py` | Oberflächen-Belege und ungeprüfte Textkontraste (werden nie automatisch aufgelöst) | aktiv |
| `v8_cue_competition.py` | gelernte Cues und konkurrierende Vervollständigungen | aktiv |
| `v8_outcome_aggregates.py` | per Trigger laufend gepflegte Summen über die Experiment-Ergebnisse für 5h und 5i | aktiv |
| `fractional_control.py` | begrenzte Fehlerdiffusion für diskrete Budgets (Ontologie) | aktiv |
| `v8_cycle_diagnostics_release.py` | wertet Zyklusergebnisse rekursiv auf Fehler aus | aktiv |
| `v8_sensory_deprivation.py`, `v8_deprivation_runner.py` | Lernen ohne neuen Input, CSV-Protokoll, Drift-Bericht | aktiv (GUI) |
| `v8_wal_maintenance_release.py` | Pflege des Write-Ahead-Logs | aktiv |
| `reset_learning.py` | Lern-Reset mit Korpuserhalt, Probelauf, Vollbackup, Prüfungen | aktiv, getestet |
| `systemtest.py` | Systemprüfung auf einer Datenbankkopie | aktiv |
| `gui_app.py`, `user_gui.py` | Admin-GUI und lesende Dialog-GUI | aktiv, getestet |

---

## 5. Produktionsdatenbank

| Kennzahl | Wert |
|---|---|
| Dateigröße | 5,57 GB |
| Tabellen / Indizes | 147 / 71 |
| Integritätsprüfung | OK |
| Dokumente / Abschnitte | 2 / 167.661 |
| Gelesene Abschnitte seit dem letzten Lern-Reset | 62.244 (37,1 %) |
| Lernzyklen seit dem letzten Lern-Reset | 1.947 (davon 1.294 Tiefschlaf-Zyklen) |
| Hypothesen gesamt | 937.552 |
| davon Satz unsicher / stabil | 609.096 / 36 |
| davon Wortgrenze unsicher | 320.032 |
| davon Relation unsicher | 8.388 |
| Fakten / Relationen / Kategorien | 36 / 0 / 0 |
| Fragen offen / aufgelöst | 202 / 11 |
| Wissenslücken | 514 |
| Experiment-Ergebnisse | 901.852 |
| Wortgrenzen-Statistik (Übergänge) | 432.587 |
| Fortschritt Wortgrenzen-Ebene / Relations-Ebene | bis Abschnitt 15.576 / bis Abschnitt 5.872 |

**Botenstoffe (letzter Zustand):** Dopamin 0,31, Serotonin 0,34, Noradrenalin 0,80, Acetylcholin 0,56, Glutamat 0,68, GABA 0,47; Cortisol Stufe 2, Regime „calm“.

**Hinweis:** Die Datenbank wurde zuletzt mit einem Stand betrieben, der das priorisierte Replay und die Cue-Konkurrenz noch nicht enthielt. Graduierungen stehen deshalb seit Zyklus 1.226 still, Relationen und Kategorien gibt es dort noch nicht. Beim nächsten Start legt der Bootstrap einmalig die neuen Indizes und die Aggregat-Tabelle an (Sekunden bis wenige Minuten).

---

## 6. Testergebnisse vom 12.11.2026

| Test | Ergebnis |
|---|---|
| Systemtest auf einer Kopie der Produktionsdatenbank | 7 von 7 Prüfpunkten OK |
| 150 Zyklen auf frischer DB mit 300 echten Wikipedia-Abschnitten | 0 Fehler, 0 versteckte Fehlerzustände, Integrität OK |
| davon Graduierungen Satz / Wortgrenze / Relation | 35 / 15 / 35 |
| davon Fakten / Relationen / Kategorien / Fragen | 33 / 12 / 11 / 117 |
| davon Revisionen ohne künstlichen Anstoß | 2 (keine sofortige Wieder-Graduierung) |
| 10 und 20 Zyklen auf einer Kopie der Produktionsdatenbank | 0 Fehler, 1,3 bis 1,6 s pro Zyklus |
| Korrekturtest (eindeutig / knapp / echter Zyklus) | korrigiert / unverändert / im ersten Zyklus korrigiert |
| Inkrementelle Aggregate gegen vollständige Neuberechnung | Abweichung 0, auch nach Einfügen, Upsert, Ändern, Löschen |
| Lern-Reset über Kommandozeile und GUI | erfolgreich, Korpus und Volltextsuche erhalten |
| Admin-GUI (alle Reiter, Schließen) und Lese-GUI (Suche, Antwort, Chat) | 0 Fehler |

---

## 7. Performance

| Messung | Zeit pro Zyklus |
|---|---|
| Produktionsgröße, Stand vor den Optimierungen | 22,5 s |
| Produktionsgröße, aktueller Stand | 1,3 bis 1,6 s |
| Kleiner Korpus (300 Abschnitte), aktueller Stand | 0,9 s |

Wirksame Maßnahmen:
- Schema-Prüfung einmal pro Datenbankverbindung statt pro beobachtetem Satz
- laufend gepflegte Summen für die Auswertungen von 5h und 5i (Trigger) statt Neuberechnung über 0,9 Mio. Zeilen
- gezielte Indizes auf häufig abgefragten Spalten, Ausdrucks-Indizes für die Replay-Kandidatenwahl in Phase 6a
- genau ein eindeutiger Index pro Tabellenspalte
- zwischengespeicherte Volltextsuchen der Lese-Rückkopplung, gültig bis zum nächsten Import

---

## 8. Laufzeit-Eigenschaften

- Ein Prozess, ein CPU-Kern, keine GPU
- SQLite im WAL-Modus, 60 s Wartezeit bei Sperren
- deterministische Reihenfolge der Phasen; Zufall nur in Replay-Auswahl und Rauschen, pro Zyklus geseedet
- jeder Phasenfehler wird im Zyklusergebnis erfasst und vom Diagnosemodul ausgewertet

---

## 9. Bekannte Einschränkungen und offene Punkte

| Punkt | Auswirkung | Einordnung |
|---|---|---|
| Phasen 5f und 5h arbeiten mit festen Steuerwerten (Lernrate, Fehlergewicht, Botenstoffwerte) statt mit dem echten Zustand der Botenstoffe | Strategielernen dort nicht neuromoduliert | offen, nächster Schritt |
| Phasen 5b, 5d und 5g fragen Tabellen ab, die im aktuellen System nicht entstehen, und rechnen dann mit festen Ersatzwerten | Teile ihrer Bewertung sind konstant | offen |
| Botenstoffe stehen im Zustand hohes Noradrenalin / niedriges Serotonin | Kopplungen arbeiten dauerhaft im „Alarm“-Bereich | beobachten, ob sich das mit mehr geschlossenen Lücken ändert |
| Neue Mechanismen noch nicht auf der Produktionsdatenbank gelaufen | Langzeitverhalten auf dem vollen Korpus unbekannt | nächster Schritt |
| Fakten sind beobachtete Sätze mit der Relation `observed_as` | noch keine Aussagen über Inhalte | gewollt im Tabula-rasa-Ansatz |
| Relationselemente sind früh oft einzelne Zeichen oder Wortstücke | frühe Relationen und Kategorien sind Rauschen | gewollt, verbessert sich mit gelernten Wortgrenzen |
| Ungeprüfte Textkontraste werden nie automatisch aufgelöst | viele offene Kontraste in der Tabelle | gewollt (Wiederholung ist keine Wahrheit) |
| Pro Zyklus höchstens eine Graduierung | begrenzt die Lerngeschwindigkeit | gewolltes Budget |
| `assets/Project-Structure.png` fehlt im Projektordner | Bild im README wird lokal nicht angezeigt | offen |
| `Audits/System_Audit_2026-09-28.md` | beschreibt den Stand vom 28.09.2026 | historisches Dokument |
