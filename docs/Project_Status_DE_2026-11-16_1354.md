# BrainStem: Projekt- und Funktionsstatus

**Stand:** 16.11.2026, 13:54 Uhr
**Zählweise:** Alle Zyklenangaben sind Systemzyklen (ein Aufruf von `AutonomousLoop.cycle()`, ein Durchlauf der ganzen Phasenkette). Ein Dauerlern-Zyklus der GUI umfasst 5 Systemzyklen; 1.000 Zyklen entsprechen also 200 GUI-Zyklen. Der Entzug-Tab der GUI zählt Systemzyklen.
**Umfang:** Code (`ki_system/`, `main.py`), Produktionsdatenbank `ki_memory.sqlite3`, Testergebnisse vom 12. und 13.11.2026, Produktionslauf vom 13.11.2026, Pakete A bis D und C5 des Arbeitsplans

---

## 1. Zusammenfassung

| Bereich | Status |
|---|---|
| Lernkette | 36 Phasen, ein Wartungsschritt für die Aufbewahrung der Protokolle und die Zyklustransaktion, alle laden fehlerfrei, Kettenspitze: Zyklustransaktion (`v8_cycle_transaction`) |
| Lernen auf allen Ebenen | aktiv: Sätze, Wortgrenzen und Relationen konsolidieren und graduieren |
| Selbstkorrektur | aktiv und nachgewiesen: Cue-Konkurrenz, Revision, Rücknahme von Fakten, Rekonsolidierung |
| Emergenz von Relationen, Kategorien, Fragen | aktiv und produktiv |
| Botenstoffe | 12 Botenstoffe aktiv, 22 neuromodulierte Schwellen, Raten und Budgets, Strategiephasen 5b bis 5i mit echten Steuerwerten; Dopamin ist ein Belohnungs-Vorhersagefehler, Noradrenalin enthält die Überraschung, Noradrenalin, Acetylcholin und Serotonin sinken im Schlaf |
| Plastizität, Meta- und Meta-Metaplastizität | voll aktiv: die Replay-Wirksamkeit passt Plastizität und Biases an, 16 Meta-Parameter regeln sich selbst mit homöostatischer Rückstellkraft, kein Regler sättigt |
| Schlafen und Wachen | ein gemeinsamer Auslöser: ein einziger Schlaf-Wach-Schalter mit Hysterese; Adenosin folgt der Lernlast; entwicklungsabhängiger Schlafanteil: etwa zwei Drittel Schlaf im unreifen Zustand, sinkt mit wachsendem konsolidiertem Wissen zum Erwachsenenrhythmus (etwa 55 Wach- und 22 Schlafzyklen) |
| Systemtest | alle 7 Prüfpunkte OK (auch nach den Paketen A bis D und C5) |
| Arbeitsplan, Pakete A bis D und C5 (13.11.2026) | Aufbewahrung und Verdichtung der Protokolle, weniger Schreibzugriffe, Schließungssignal der Experimente behoben (R1), Replay-Wirksamkeit als Vergleich reaktiviert gegen nicht reaktiviert (R5), Exploration nach Lernfortschritt, stabile Ontologie; Abschlusslauf über 1.000 Zyklen erfüllt K1 bis K9 |
| Produktionslauf | 5.000 Zyklen auf dem vollen Korpus ohne Ausnahmen oder versteckte Fehler; stabile Hypothesen 36 auf 2.597, Fakten 36 auf 819, Relationen 0 auf 493; Korpus vollständig gelesen; kein Regler an einer Grenze |
| Geschwindigkeit | Rechenanteil etwa 2,6 s CPU-Zeit pro Zyklus auf dem aktuellen Produktionsstand, ein Commit pro Zyklus; die Wandzeit schwankt mit dem Speicherpool zwischen etwa 2 und 10 s (Median 2,3 s im letzten Prüflauf) |
| Produktionsdatenbank | 8,09 GB nach dem zweiten Produktionslauf (5.000 Zyklen, 15.11.2026); Größe ab Zyklus 1.750 konstant, 17,5 Mio. alte Protokollzeilen durch die Aufbewahrung entfernt; Integritätsprüfung OK; jeder Fakt und jede Relation ist bis zum Chunk rückverfolgbar |

---

## 2. Code-Stand

- **Paket:** `ki_system`, 65 Python-Module, zusammen mit `main.py` 22.358 Zeilen
- **Einstieg:** `python main.py --gui` (Admin-GUI), `python main.py --user-gui` (lesende Dialog-GUI)
- **Systemprüfung:** `python -m ki_system.systemtest` (arbeitet auf einer Kopie der Datenbank)
- **Einmalige Verdichtung der Protokolle:** `python -m ki_system.compact_logs <db> [--cutoff-ts EPOCH] [--vacuum]`
- **Lern-Reset mit Korpuserhalt:** GUI-Button oder `python -m ki_system.reset_learning --apply`
- Alle Module kompilieren fehlerfrei.

---

## 3. Lernkette (Ausführungsreihenfolge)

Jede Phase ruft zuerst die vorher registrierte Phase auf und erledigt danach ihren eigenen Teil. Dadurch entspricht die Ausführungsreihenfolge der Registrierungsreihenfolge in `phase_registry.py`.

| Nr. | Phase | Funktion | Status |
|---|---|---|---|
| 1 | Context Observation | liest Textabschnitte, zerlegt sie in Sätze, legt Satz-Hypothesen an oder beobachtet sie erneut (Belegzahl, Konfidenz) | aktiv |
| 2 | Phase 0 Lexical | Wortgrenzen aus dem ungeteilten Zeichenstrom per Verzweigungsentropie | aktiv |
| 3 | Phase 5b | verfeinert Lesestrategien aus Ergebnissen, hartnäckigen Lücken und Clustern; gruppiert die echten Fragen nach Lückentyp und Rolle; diversifiziert die Leseauswahl; wirkt mit gedämpftem Schritt auf Explorations- und Hemmungs-Bias zurück; die Exploration steigt, wenn der Lernfortschritt stockt, und sinkt, solange gelernt wird | aktiv, echte Steuerwerte, Rückkopplung aktiv |
| 4 | Phase 5c | bewertet die Fragen-Gruppen aus 5b (Größe, Priorität, Lösungsanteil) und straft unergiebige Leseziele ab | aktiv |
| 5 | Phase 5d | Beobachtungs- und Strategiegedächtnis aus echten Kennzahlen (Experiment-Ergebnisse, geschlossene Lücken, Graduierungen, offene Fragen, Steuerwerte) | aktiv |
| 6 | Stage-B Gap Detection | erkennt Lücken: „stalled“ (oft gesehen, nie gefestigt) und „contested“ (Cue-Konkurrenz); Habituation und Dishabituation; hält den Lösungswert jeder Lücke aktuell (geschlossen = 1, sonst 0) | aktiv |
| 7 | Phase 5e | plant Kontexterweiterungen rund um Lücken und erhöht die Priorität benachbarter Abschnitte | aktiv |
| 8 | Phase 5f | misst die Wirksamkeit der Kontextfenster und passt sie an (Fensterbreite abhängig von Hemmung und Exploration) | aktiv, echte Steuerwerte |
| 9 | Phase 5g | wählt Kontextstrategien aus und führt das Experimentgedächtnis | aktiv, echte Steuerwerte |
| 10 | Phase 5h | wertet Strategie-Experimente aus und lernt daraus; speichert zu jedem Ergebnis die echten Steuerwerte und Botenstoffe; eine geschlossene Lücke ergibt den vollen Schließungsgewinn; schreibt nur geänderte Bewertungen | aktiv, echte Steuerwerte |
| 11 | Phase 5i | diversifiziert Strategien anhand der Ergebnisse | aktiv, echte Steuerwerte |
| 12 | Phase 6a | Schlaf-Replay und Meta-Plastizität; bestimmt den Lernstand aus repräsentativen aktuellen Fenstern, berechnet Dopamin (Belohnungs-Vorhersagefehler), Serotonin, Noradrenalin (Druck und Überraschung) und Acetylcholin, mischt den tonischen Zielwert bei, wendet den Schlaftonus an und führt die frischen Biases in den gemeinsamen Bias-Zustand | aktiv |
| 13 | Phase 6b | misst die Wirksamkeit des Replays als Vergleich reaktivierter mit nicht reaktivierten markierten Spuren (targeted memory reactivation), passt die Plastizität an, Critic-Gate; Anpassungen gehen in den dauerhaften Bias-Zielwert ein | aktiv |
| 14 | Phase 6c | hält Bias-Werte über Zyklen (dauerhafter Zielwert, gespeist von 5b, 6b, 6d, 7a, 7b) und regelt Meta-Parameter selbst | aktiv |
| 15 | Phase 6d | Sättigungs-Homöostase (gleitende Schwelle) und Meta-Metaplastizität | aktiv |
| 16 | Phase 7a | Adenosin als Schlafdruck (Prozess S): sättigender Anstieg mit der Lernlast im Wachen, schneller solange das System unreif ist, exponentieller Abbau im Schlaf; setzt gesättigte Biases beim Einschlafen zurück; entscheidet selbst nicht über den Schlaf | aktiv, liest den Schalterzustand |
| 17 | Phase 7b | Endocannabinoide: 2-AG als schnelle Bremse, Anandamid als langsame Rückführung gesättigter Werte | aktiv |
| 18 | Phase 7b1 | Wake-Chain-Brücke: führt 6a bis 7b in fester Reihenfolge aus | aktiv |
| 19 | Phase 7c | adaptive Grenzen, sanftes Abschneiden an Grenzen, Glutamat-GABA-Gleichgewicht | aktiv |
| 20 | Connection Accelerator | setzt schnelle SQLite-Einstellungen für jede neue Verbindung | aktiv |
| 21 | Phase 7d | Tiefschlaf-Konsolidierung mit priorisiertem Replay (siehe 4.1) | aktiv |
| 22 | Phase 7e | Histamin: Wachheit, Gegenspieler zu Adenosin; im Schlaf vom Schalter gehemmt (Flip-Flop) | aktiv, liest den Schalterzustand |
| 23 | Phase 7f | Orexin: Lese-Ausdauer und Neugier | aktiv |
| 24 | Phase 7g | BDNF: aktivitätsabhängiges Wachstum und Festigung | aktiv |
| 25 | Phase 7cort | Cortisol: Stabilitätswächter, Stufe 2 (vorsichtiger Regler) | aktiv, im Betrieb ruhig |
| 26 | Cooperative Core | gemeinsame Dynamik der sechs Kern-Botenstoffe; der einzige Schlaf-Wach-Schalter (siehe 4.7) | aktiv |
| 27 | Stage-B Graduation | höchstens eine Graduierung pro Zyklus, Rollen konkurrieren über divisive Normalisierung | aktiv |
| 28 | Stage-B Contradiction Detection | entscheidet Cue-Konkurrenzen nach Belegen; Textalternativen an einer Stelle werden als Satzrahmen erfasst, nur ein spezifischer, geschlossener Rahmen aus verschiedenen Artikeln mit einer stabilen Seite wird zum ungeprüften Widerspruch | aktiv |
| 29 | Stage-B Hypothesis Revision | stuft unterlegene, gefestigte Hypothesen zurück, schließt die Lücke | aktiv |
| 30 | Stage-B Fact Promotion | graduierte Satz- und Wortgrenzen-Hypothesen werden Fakten; Rücknahme bei Revision | aktiv |
| 31 | Phase 0b Relational Binding | bindet gemeinsam auftretende Elemente (PMI, Richtung aus Position) | aktiv |
| 32 | Stage-B Relation Promotion | graduierte Relations-Hypothesen werden Relationen | aktiv |
| 33 | Stage-B Ontology Cluster Observation | deterministische, warm gestartete Label Propagation über den Relationsgraphen, Prototyp-Anker; zählt Schlafphasen je Cluster; Gnadenfrist von 60 Zyklen vor der Auflösung | aktiv |
| 34 | Stage-B Ontology Promotion | stabile Cluster mit mindestens 3 Mitgliedern, beobachtet in mindestens 3 Schlafphasen, werden Ontologie-Einträge (Mitgliedschaft) | aktiv |
| 35 | Stage-B Question Promotion | hartnäckige Lücken werden Fragen | aktiv |
| 36 | Stage-B Question-Chunk Feedback | offene Fragen lenken das Lesen (Quelle und Volltextsuche); globaler Zerfall gebündelt alle 10 Zyklen | aktiv |
| + | Protokoll-Aufbewahrung (Wartung) | hält die rohen Ereignisprotokolle der Experimente der letzten 1.000 Zyklen; löscht ältere Zeilen im Schlaf mit Zeilenbudget; Langzeitsummen bleiben erhalten | aktiv |
| + | Zyklustransaktion (`v8_cycle_transaction`) | ein dauerhafter Commit pro Zyklus: innerhalb eines Zyklus ist ein Commit der Memory-Verbindung eine Schrittgrenze (Savepoint), ein Rollback setzt bis zur letzten Grenze zurück; der Zyklus schreibt einmal am Ende fest, auch bei einer Ausnahme | aktiv |

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

22 Kopplungen; jede liefert beim Neutralwert 0,5 genau den kalibrierten Grundwert.

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
| Anstiegsrate von Adenosin im Wachen | Glutamat |
| Abbaurate von Adenosin im Schlaf | GABA |
| Schlaf- und Wachschwelle (gemeinsam verschoben, höchstens 0,1) | Histamin, Orexin, Noradrenalin, Acetylcholin, Cortisol gegen GABA |

### 4.5 Steuerwerte der Strategiephasen

Die Phasen 5b, 5d, 5f, 5g, 5h und 5i beziehen ihre Steuerwerte über `v8_learning_controls.py` aus dem echten Zustand:

| Steuerwert | Quelle |
|---|---|
| Lernrate | Plastizitätsniveau aus Phase 6a |
| Explorationsdruck | Explorations-Bias aus Phase 6a |
| Konsolidierung | Konsolidierungs-Bias aus Phase 6a |
| Hemmung | Hemmungs-Bias aus Phase 6a |
| Revisionsdruck | Revisions-Bias aus Phase 6a |
| Fehlergewicht | Noradrenalin (Erregung durch unerwartete Ergebnisse gewichtet neue Belege und Fehler; Yu & Dayan 2005; Nassar et al. 2012) |
| Dopamin, Serotonin, Glutamat, GABA, Noradrenalin, Acetylcholin | gemeinsamer Botenstoff-Zustand aus Phase 6a und 7c |

Die kalibrierten Grundwerte gelten nur, solange ein Wert noch nicht geschrieben wurde (frische Datenbank vor dem ersten Schlafzyklus).

**Rückkopplung der Strategie (Phase 5b):** Viele hartnäckige, ungelöste Lücken schieben in Richtung Exploration, Erfolg in Richtung Ausnutzung (Cohen, McClure & Yu 2007). Die Empfehlung von 5b verschiebt den dauerhaften Bias-Zielwert mit einem gedämpften Schritt (Parameter `bias_feedback_gain`, Grundwert 0,5). Gegenkräfte: Sättigungs-Homöostase (6d) und Anandamid-Rückführung (7b).

### 4.6 Weitere Module

| Modul | Funktion | Status |
|---|---|---|
| `autonomous.py` | Kern der Lernschleife; die Kette wird von der Registry eingehängt | aktiv |
| `phase_registry.py` | Ladereihenfolge, Fehlererfassung, Selbstprüfung der Kette | aktiv |
| `db_bootstrap.py` | zentrales, idempotentes Schema: Tabellen, Spalten, Indizes, Ausdrucks-Indizes | aktiv |
| `db_runtime.py` | konsistente Datenbank-Schnappschüsse | aktiv |
| `memory.py` | Datenbankzugriff, Dokumente und Abschnitte, Volltextindex | aktiv |
| `ingest.py` | Import von ZIM, TXT, PDF, Fortsetzen nach Abbruch | aktiv |
| `search.py`, `dialogue.py`, `text_utils.py`, `wiki_quality.py` | Suche, Antwort, Dialog, neutrale Texthilfen ohne Wortfilter | aktiv |
| `semantic_evidence.py` | Oberflächen-Belege; Satzrahmen mit Füllern und Quellen (`semantic_text_frames`); ungeprüfte Textkontraste nur nach den Rahmenregeln, nie automatisch aufgelöst | aktiv |
| `v8_cue_competition.py` | gelernte Cues und konkurrierende Vervollständigungen | aktiv |
| `v8_outcome_aggregates.py` | per Trigger laufend gepflegte Summen über die Experiment-Ergebnisse für 5d, 5h und 5i | aktiv |
| `v8_learning_controls.py` | Steuerwerte und Botenstoffe der Strategiephasen aus dem echten Zustand | aktiv |
| `fractional_control.py` | begrenzte Fehlerdiffusion für diskrete Budgets (Ontologie) | aktiv |
| `v8_cycle_diagnostics_release.py` | wertet Zyklusergebnisse rekursiv auf Fehler aus | aktiv |
| `v8_sensory_deprivation.py`, `v8_deprivation_runner.py` | Lernen ohne neuen Input, CSV-Protokoll, Drift-Bericht | aktiv (GUI) |
| `v8_wal_maintenance_release.py` | Pflege des Write-Ahead-Logs | aktiv |
| `reset_learning.py` | Lern-Reset mit Korpuserhalt, Probelauf, Vollbackup, Prüfungen | aktiv, getestet |
| `systemtest.py` | Systemprüfung auf einer Datenbankkopie | aktiv |
| `gui_app.py`, `user_gui.py` | Admin-GUI und lesende Dialog-GUI; die Admin-GUI zeigt einen einzigen Schlafzustand mit Schlafdruck, beiden Schwellen, Verweildauer, Reifegrad und dem Grund des letzten Wechsels | aktiv, getestet |

### 4.7 Schlafen und Wachen: ein gemeinsamer Auslöser

Bisher konnten zwei unabhängige Mechanismen die Konsolidierung starten: der Adenosin-Homöostat in Phase 7a (mit eigenem Schlafmodus) und ein gewichteter Schlaf-Score im Cooperative Core. Phase 7d schlief, sobald einer von beiden „Schlaf“ meldete. Im Betrieb löste nur Phase 7a aus (Produktionsdatenbank: 259 Wechsel in 1.947 Zyklen, etwa 5 Wach- und 10 Schlafzyklen pro Episode, 66 % Schlaf); der kooperative Score erreichte seine Schwelle nie.

Jetzt entscheidet genau ein Schalter: der Schlaf-Wach-Schalter im Cooperative Core. Phase 7a, Phase 7d, Phase 7e und die GUI lesen seinen Zustand.

| Element | Funktion | Grundlage |
|---|---|---|
| Schlafdruck S (Adenosin, Phase 7a) | wach: `S = 1 - (1 - S) * exp(-k_wach)`, Schlaf: `S = S * exp(-k_schlaf)` | Zwei-Prozess-Modell (Borbély 1982; Daan, Beersma & Borbély 1984) |
| Zeitkonstanten | Verhältnis von Anstieg zu Abbau wie in den Anpassungen an Menschen (18,2 h / 4,2 h); Grundraten 0,0154 und 0,0666 pro Zyklus | Skeldon, Dijk & Derks 2014 |
| Wie stark S steigt | `k_wach = 0,0154 * (0,5 + Last) * Glutamat-Faktor`; Last = neue Hypothesen und Experiment-Ergebnisse des Zyklus im Verhältnis zum eigenen laufenden Neuheitsniveau, `n / (n + Referenz)` | Adenosin sammelt sich mit neuronaler Aktivität (Porkka-Heiskanen et al. 1997; Brambilla, Chapman & Greene 2005); Schlafbedarf wächst mit dem Lernen im Wachen (Tononi & Cirelli 2006; Huber et al. 2004) |
| Wie schnell S fällt | `k_schlaf = 0,0666 * GABA-Faktor` | tieferer Tiefschlaf bei stärkerer GABAerger Hemmung (Walsh et al. 2008) |
| Wann das System schläft | S erreicht die obere Schwelle 0,67 | obere Schwelle des Zwei-Prozess-Modells |
| Wann das System aufwacht | S ist bis zur unteren Schwelle 0,17 abgebaut | untere Schwelle des Zwei-Prozess-Modells |
| Schwellenverschiebung | beide Schwellen verschieben sich gemeinsam um `0,1 * (Wachantrieb - Schlafantrieb)`, höchstens 0,1; Wachantrieb aus Histamin, Orexin, Noradrenalin, Acetylcholin, Cortisol; Schlafantrieb aus GABA, Hemmungs-Bias und niedrigem Glutamat | Flip-Flop zwischen VLPO und Wachsystem (Saper, Chou & Scammell 2001; Saper, Scammell & Lu 2005) |
| Gegenseitige Hemmung | im Schlaf wird das Histamin-Ziel halbiert; weniger Histamin senkt den Wachantrieb und stabilisiert den Schlaf | VLPO hemmt den tuberomammillären Kern (Sherin et al. 1998; Takahashi, Lin & Sakai 2006) |
| Einschlafen | gesättigte Meta-Plastizitäts-Biases werden zur Mitte gezogen | synaptische Renormalisierung (Tononi & Cirelli 2006) |
| Entwicklungsabhängiger Schlafanteil | `k_wach` wird mit `1 + 4 * (1 - Reife)` multipliziert, `Reife = Wissen / (Wissen + 1000)`, Wissen = Nettozahl der Hypothesen in einer stabilen Rolle (Revisionen zählen zurück); ein frisches System baut den Druck fünfmal schneller auf und schläft etwa zwei Drittel der Zeit | Neugeborene schlafen etwa zwei Drittel des Tages, der Anteil sinkt mit dem Alter (Roffwarg, Muzio & Dement 1966); bei jüngeren Kindern baut sich der Schlafdruck schneller auf, der Abbau bleibt gleich (Jenni, Achermann & Carskadon 2005; Tarokh, Carskadon & Achermann 2012); der Schlafbedarf sinkt mit der Hirnreifung (Feinberg & Campbell 2010) |

**Nicht zu früh, nicht zu spät.** Eine Wachphase dauert `0,92 / k_wach` Zyklen: bei typischer Last etwa 11 bis 13 Zyklen im frischen und etwa 55 bis 65 Zyklen im reifen System, zwischen etwa 7 (Neugeborenes, hohe Last, viel Glutamat) und 150 Zyklen (reif, kein neues Material). Sie endet damit immer innerhalb des dopamin-modulierten Fensters der synaptischen Markierungen in Phase 7d (225 bis 375 Zyklen), sodass markierte Spuren konsolidiert werden, bevor sie zerfallen. Eine Schlafphase dauert etwa 20 bis 23 Zyklen. Jede Wachphase sammelt mehrere tausend neue Hypothesen, mehr als eine Schlafphase wiederholen kann; das Replay bleibt also selektiv.

**Migration:** Veraltete Schlüssel der alten Mechanismen (Schlafmodus von Phase 7a, Schlaf-Score, feste Ein- und Ausschaltschwellen, Mindestverweildauer) werden beim ersten Lauf automatisch entfernt. Der gespeicherte Adenosinwert bleibt erhalten.

---

### 4.8 Botenstoff-Signale und Plastizitätskette

| Signal | Berechnung | Grundlage |
|---|---|---|
| Belohnung pro Zyklus | 0,5 x Ergebnis neuer Experimente + 0,3 x Graduierung + 0,2 x gelöste Lücke | |
| Dopamin (phasisch) | 0,5 + 1,5 x Belohnungs-Vorhersagefehler; Erwartung je Zustand (wach, Schlaf) mit Rate 0,1 gelernt | Schultz, Dayan & Montague 1997; Sutton & Barto 2018 |
| Tonisches Dopaminziel, Serotonin | langfristige mittlere Belohnung (langsames Mittel, Rate 0,02), Konsolidierung, Ankerstabilität | Niv et al. 2007 |
| Noradrenalin | persistenter Druck plus Überraschung (Betrag des Vorhersagefehlers) plus Überlappung | Yu & Dayan 2005; Aston-Jones & Cohen 2005 |
| Persistenter Druck | 0,5 x (1 - Schließung) + 0,3 x (1 - Ergebnis) + 0,2 x Überlappung (Gewichtssumme 1, keine Sättigung) | |
| Lernfortschritt (Orexin, BDNF) | schnelles minus langsames Mittel der Belohnung | Oudeyer, Kaplan & Hafner 2007 |
| Schlaftonus | Noradrenalin x 0,3, Acetylcholin x 0,4, Serotonin x 0,5 | Yang & Eschenko 2025; Trulson & Jacobs 1979; Hasselmo & McGaughy 2004 |
| Gemeinsamer Bias-Zustand | frische 6a-Werte fließen mit Rate 0,1 pro Zyklus ein; 5b, 6b, 6d, 7a und 7b ändern ihn additiv | |
| Meta-Parameter (6c) | Schritte relativ zum Bereich, Rückstellkraft 0,25 zum Grundwert, 2-AG-Dämpfungsfaktor | Turrigiano 2008 |
| Meta-Metaplastizität (6d) | Lernraten der Meta-Parameter und der fünf Biases; der Schritt weg von einer gesättigten Grenze wird erleichtert | Abraham & Bear 1996; Lee & Kirkwood 2019 |
| BDNF | senkt die Überlebensschwelle und verstärkt die Verstärkung in der Tiefschlaf-Konsolidierung | Bramham & Messaoudi 2005 |
| Adaptive Grenzen (7c) | Bereiche verengen sich nur, solange ein Parameter tatsächlich geregelt wird, nie unter die halbe kalibrierte Breite | |

Der ausführliche Bericht ist `Audits/Neuromodulator_Plasticity_Fix_Calibration_2026-11-12_1722.md`.

---

## 5. Produktionsdatenbank

Stand nach dem Produktionslauf vom 13.11.2026 (5.000 Zyklen). Am 14.11.2026 wurden die Ereignisprotokolle gelöscht, die älter als die letzten 1.000 Zyklen des Laufs sind (etwa 27 Mio. Zeilen), und die Datei wurde verdichtet; die gelernten Inhalte sind unverändert.

| Kennzahl | Wert |
|---|---|
| Dateigröße | 5,82 GB nach der Verdichtung (20,5 GB nach dem Lauf, 5,57 GB davor) |
| Tabellen / Indizes | 159 / 86 |
| Integritätsprüfung | OK |
| Dokumente / Abschnitte | 2 / 167.661 |
| Gelesene Abschnitte seit dem letzten Lern-Reset | 167.661 (100 %) |
| Lernzyklen seit dem letzten Lern-Reset | 6.947 |
| Hypothesen gesamt | 2.430.058 |
| davon Satz unsicher / stabil | 1.590.914 / 819 |
| davon Wortgrenze unsicher / stabil | 829.109 / 553 |
| davon Relation unsicher / stabil | 7.438 / 1.225 |
| Fakten / Relationen / Kategorien | 819 / 493 / 4 |
| Fragen offen / aufgelöst | 52 / 273 |
| Wissenslücken offen / habituiert / geschlossen | 950 / 146.921 / 101 |
| Experiment-Ergebnisse | 3.287.455 |
| Wortgrenzen-Statistik (Übergänge) | 846.782 |

**Botenstoffe (letzter Zustand, Schlaf):** Dopamin 0,58, Serotonin 0,28, Noradrenalin 0,18, Acetylcholin 0,21, Glutamat 0,64, GABA 0,46; Cortisol Stufe 2, Regime „calm“.

**Wachstum:** Die Experimentphasen schreiben je Zyklus mehrere hundert Ereigniszeilen. Seit dem 13.11.2026 hält die Protokoll-Aufbewahrung davon nur die letzten 1.000 Zyklen. Die Datei wächst deshalb in den nächsten 1.000 Zyklen um etwa 3 GB und danach vor allem mit dem Gelernten.

**Verdichtung vom 14.11.2026:** 27,0 Mio. Zeilen in 843 s gelöscht, VACUUM 232 s; Langzeitsummen vorher und nachher 3.287.455 Beobachtungen; Fakten 819, Relationen 493, Ontologie 4, stabile Hypothesen 2.597, Chunks 167.661 vorher und nachher; alle drei Trigger der Zusammenfassungen vorhanden.

**Rückverfolgbarkeit:** 30 Fakten aus den ersten Graduierungen vom 23. und 24.09.2026 hatten keine direkte Chunk-Angabe (die damalige Beförderungslogik übernahm sie nicht); sie wurde aus ihren Quell-Hypothesen nachgetragen. Alle 819 Fakten und 493 Relationen zeigen jetzt direkt auf einen vorhandenen Chunk.

Backups: vor dem Lauf `A:\ClaudeCode\Brainstem_db_backup_20261113_vor_langzeitlauf`, nach dem Lauf (vor der Verdichtung) `A:\ClaudeCode\Brainstem_db_backup_20261113_nach_langzeitlauf`.

---

## 6. Testergebnisse vom 12. und 13.11.2026

### Prüflauf R8, 16.11.2026: Satzrahmen und ein Commit pro Zyklus

Einzelheiten in `Audits/Test_Run_R8_2026-11-16_1354.md`.

| Punkt | Ergebnis |
|---|---|
| Expertenrat zu Textkontrasten | Alternativen an einer Stelle sind Rahmen mit Füllern, die Evidenz, aus der Wortklassen entstehen (Harris 1954, Mintz 2003, Gómez 2002), keine Widersprüche; Widerspruch nur, wenn eine Seite stabil ist, das seltenste gemeinsame Wort spezifisch ist (df höchstens Wurzel aus N), die Stelle geschlossen ist (höchstens 3 Füller) und die Seiten aus verschiedenen Artikeln stammen; eine Lücke pro Rahmen, habituiert, wenn sich die Stelle öffnet, jede Änderung protokolliert und umkehrbar |
| Suche | nur die seltensten Hinweiswörter (Präfixfilter), höchstens 2,5 % des Index an Treffern, die 64 besten nach bm25; offline 98,4 % der spezifischen Paare des alten Verfahrens wiedergefunden |
| A/B über je 1.000 Zyklen auf gleichen Produktionskopien | alle neun Kriterien in beiden erfüllt; alter Code gegen Rahmen: stabile Hypothesen +319 gegen +339, Graduierungen 319 gegen 339, K5 0,896 gegen 0,898, Fragen 355 gegen 355; ungeprüfte Widersprüche +27.032 gegen 0; gepaarte Blöcke zu 50 Zyklen: B minus A +1,0 pro Block, 95-%-Intervall -1,4 bis +3,4 (Mittel 16,0) |
| Rahmen | 50.742 Rahmen aus 319.469 Paaren, 375 paradigmatisch; die häufigsten sind Zitierbausteine; 1.728 alte Lücken pro Paar neu eingeordnet und habituiert (protokolliert), Neueinordnung abgeschlossen |
| Ein Commit pro Zyklus | 1 statt etwa 74 Commits; gleiche CPU-Zeit; etwa 20 bis 35 % weniger geschrieben; Wandzeit auf dem Speicherpool nicht messbar verschieden |
| Prüflauf mit Rahmen und Bündelung, 500 Zyklen | 0 Ausnahmen, 0 Diagnosemeldungen, K6 320, K7 0,011; K5 0,807, auf gleich langen Fenstern über dem alten Code (0,72 bis 0,74); Median 2,3 s pro Zyklus |

### Prüflauf R7, 16.11.2026

Einzelheiten in `Audits/Test_Run_R7_2026-11-16_0830.md`.

| Punkt | Ergebnis |
|---|---|
| Partielle Indizes auf der Lückentabelle | von 276.246 Lücken sind 274.623 habituiert; sechs partielle Indizes passen genau zu den Filtern der Phasen 5e, 5f, 5g, 5i, 6a und der Lückenerkennung; elf Abfragen mit gleichen Ergebnissen, 2,1 s auf 0,03 s pro Zyklus |
| Weitere Indizes | abdeckender Index für die Mittelwerte in 5d und die Zählung in 6a, `contradictions(subject, relation)`; 5b und 5c überspringen die Duplikatsuche, wenn der eindeutige Index existiert |
| Kalibrierkriterien | alle neun über 1.000 Zyklen erfüllt, 0 Ausnahmen, 0 Diagnosemeldungen, K5 0,886 mit dem neuen Fenster |
| Geschwindigkeit | CPU-Zeit 2,6 s pro Zyklus in schnellen wie langsamen Zyklen (vorher etwa 5,1 s); Wandzeit 2,4 s in 39 % der Zyklen und 8,7 s in den übrigen, der Unterschied ist Warten auf die Commits im Speicherpool |

### Prüflauf R6, 16.11.2026

Umsetzung des Expertenrats vom 15.11.2026; Einzelheiten in `Audits/Test_Run_R6_2026-11-16_0308.md`.

| Punkt | Ergebnis |
|---|---|
| Ontologie aus Wörtern | Beförderung nur, wenn Prototyp und mindestens `min_promotion_size` Mitglieder Worteinheiten sind (alphabetisch, mindestens 4 Buchstaben, oder bestätigte lexikalische Einheiten); ein beförderter Silben-Cluster mit eigenem Grund zurückgenommen; seitdem keine Beförderung, Ontologie leer |
| Stabil gegen stabil | zwei gefestigte Sätze mit gleichem Hinweisreiz bestehen jetzt nebeneinander (Status `coexisting`), die Revision überspringt einen stabilen Sieger; kein solcher Fall in 1.000 Zyklen, 59 Revisionen mit unsicherem Sieger |
| Fehler gefunden und behoben | die Beförderung in die Ontologie scheiterte in jedem Zyklus („no such savepoint“), weil eine Schemaprüfung mit eigenem Commit innerhalb des Savepoints lief; Kontrolle über 200 Zyklen nach der Behebung: 0 Ausnahmen, 0 Diagnosemeldungen |
| Kalibrierkriterien | K1 bis K4 und K6 bis K9 nach der Behebung erfüllt; K5 nur durch Zensierung am Ende kurzer Läufe niedriger |
| Geschwindigkeit | Phase 5b 0,59 auf 0,012 s, Phase 5d 0,35 auf 0,18 s, gleiche Werte |

### Zweiter Produktionslauf über 5.000 Zyklen (15.11.2026, 06:45 bis 13:57 Uhr)

Auf der verdichteten Produktionsdatenbank mit allen Änderungen vom 14.11.2026 und vollem Sinnes-Gating im Schlaf; Einzelheiten in `Audits/Production_Run_2_2026-11-15_1357.md`.

| Kennzahl | Ergebnis |
|---|---|
| Stabilität | 5.000 von 5.000 Zyklen, 0 Ausnahmen, 0 versteckte Fehler, Integrität OK, kein Meta-Parameter an einer Grenze |
| Lernen | stabile Hypothesen 2.597 auf 4.505, Fakten 819 auf 1.136, Relationen 493 auf 1.067, Fangquote 97,4 % |
| Datenbank | 5,82 auf 8,09 GB, ab Zyklus 1.750 konstant; 17,5 Mio. alte Protokollzeilen entfernt |
| Zykluszeit (Median) | 2,7 s steigend auf 5,9 s |
| Ontologie | 110 befördert, 112 nach der Gnadenfrist zurückgenommen (vorher 1.013 und 1.010) |
| Replay-Wirksamkeit | 463 Kohorten, +0,028 (Standardfehler 0,088), keine Fehlalarme |
| Inhaltsgewichtete Reife (Schatten) | 0,081, gegenüber 0,82 nach der Zählung |

### Arbeiten vom 14.11.2026

| Punkt | Ergebnis |
|---|---|
| Replay-Wirksamkeit, Version 2 | Zielgröße Einfangen; eine Kohorte je Spur und Horizont; Alarm erst ab 2,814 Standardfehlern; Plateau nur mit Äquivalenztest (Expertenrat aus drei Agenten). Lauf über 1.000 Zyklen: K1 bis K9 erfüllt, Effekt +0,135 (z 1,66), vorher -0,051 durch Zensierung |
| Sinnes-Gating im Schlaf | Vergleich dreier Varianten nach einem Lern-Reset und vorab festgelegte Bestätigung (zwei Paare, bis 3.000 Zyklen): volles Gating lernt gleich viel oder etwas mehr bei etwa 30 % kürzerer Laufzeit; jetzt Standard |
| Inhaltsgewichtete Reife | Schattenmodus in Phase 7a, nicht an den Schlaf gekoppelt |
| Lern-Reset | war durch die Trigger der Zusammenfassungen blockiert; behoben |
| Entzugslauf über 1.500 Zyklen | Urteil „konvergenz“, alle 21 Signale stabil oder konvergierend |
| GUI | Lernen, Stopp, CSV-Logger, Drift-Reiter und CSV Viewer funktionieren |

### Arbeitsplan, Pakete A bis D und C5 (13.11.2026, 23:20 Uhr)

Tests auf Kopien der Produktionsdatenbank; die Produktionsdatenbank ist unverändert. Einzelheiten in `Audits/Pakete_A-D_C5_2026-11-13_2320.md`.

| Punkt | Ergebnis |
|---|---|
| A: Aufbewahrung, Verdichtung | neuer Wartungsschritt hält 1.000 Zyklen roher Protokolle; Verdichtung einer Kopie von 20,5 GB auf 5,8 GB, etwa 27 Mio. Zeilen entfernt, Langzeitsummen unverändert (3.287.455 Beobachtungen), Integrität OK, 24 Minuten Löschen und 5 Minuten VACUUM |
| B: Schreiblast | 5h schreibt 479 statt 1.200 Bewertungen je Zyklus; gebündelter Zerfall; neuer Index auf den Widerspruchsstatus; es bleiben etwa 17.000 Schreibzugriffe je Zyklus, überwiegend echtes Lernen |
| C1 / R1: Schließungssignal | Ursache: 5h las eine nie beschriebene Spalte; behoben, eine geschlossene Lücke ergibt den vollen Schließungsgewinn (Schultz 1997); 24 % der Bewertungen melden jetzt eine Schließung (vorher 0 %) |
| C2 / R5: Replay-Wirksamkeit | neues Maß: reaktivierte gegen nicht reaktivierte markierte Spuren, nach Stärke getrennt, Ergebnis 30 Zyklen später (targeted memory reactivation: Rudoy 2009, Rasch 2007, Hu 2020); 567 Kohorten, Effekt -0,051 (Standardfehler 0,037, nicht gesichert); 4 Plateau-Signale in 1.000 Zyklen statt zufälliger Schwellenüberschreitungen in 335 von 6.947 Zyklen |
| C3: Exploration | folgt dem Lernfortschritt (Aston-Jones & Cohen 2005, Oudeyer 2007, Gottlieb 2013); bewegt sich zwischen 0,54 und 0,81 statt dauerhaft bei 0,75 |
| C5: Ontologie | deterministische, warm gestartete Label Propagation, Beförderung nach 3 Schlafphasen (Gómez 2006, Friedrich 2015), Gnadenfrist, Mindestgröße 3; 10 Cluster befördert und 1 zurückgenommen in 1.000 Zyklen (Produktionslauf: etwa 203 und 202 je 1.000 Zyklen) |
| D: GUI auf der 20-GB-Datenbank | Zählabfragen brauchten beim ersten Aufruf bis zu 5,8 s, Index ergänzt; alle Dashboard-Abfragen auf der verdichteten Kopie höchstens 0,1 s |
| Abschlusslauf über 1.000 Zyklen | K1 bis K9 erfüllt (Graduierungen 633, Fangquote 95,0 %, Vorhersagefehler 0,008 / 0,000, kein Regler an einer Grenze), 0 Ausnahmen, 0 versteckte Fehler, Integrität OK; Systemtest 7 von 7 OK |
| Noch nicht gefahren | 1.500-Zyklen-Entzugslauf gegen die Stabilitäts-Referenz; GUI-Schritte D2 bis D4 |

### Produktionslauf über 5.000 Zyklen (13.11.2026, 06:17 bis 19:00 Uhr)

Lernlauf mit Eingang auf der Produktionsdatenbank; Einzelheiten in `Audits/Production_Run_2026-11-13_1912.md`.

| Kennzahl | Ergebnis |
|---|---|
| Stabilität | 5.000 von 5.000 Zyklen, 0 Ausnahmen, 0 versteckte Fehler, Integrität OK |
| Lernen | stabile Hypothesen 36 auf 2.597, Fakten 36 auf 819 (920 befördert, 101 nach verlorenen Widersprüchen zurückgenommen), Relationen 0 auf 493, Fragen 213 auf 325 (273 aufgelöst) |
| Konsolidierung | 2.661 markierte Spuren, davon 2.629 eingefangen (98,8 %) |
| Korpus | vollständig gelesen ab Zyklus 3.300; die Konsolidierung läuft danach weiter (+655 stabile Hypothesen) |
| Schlaf | Schlafanteil sinkt mit der Reife von 63 % auf 45 %; Wachphasen verlängern sich von 16 auf 27 Zyklen, Schlafphasen bleiben bei 23 Zyklen |
| Botenstoffe | Wach/Schlaf-Verhältnisse über den Lauf gleich; Orexin sinkt bei erschöpftem Korpus auf 0,23 („gesättigt“); BDNF bleibt bei 0,63 („Wachstum“) |
| Regler | in keinem Zyklus ein Meta-Parameter an einer Grenze; Sättigungshomöostase 6d nie nötig; Cortisol ruhig (Mittel 0,10) |
| Strategie | Kontraste belegen 12 % der Strategie-Experimente (vorher 59 %) |
| Zykluszeit | steigt von 3,5 s auf etwa 11 s und bleibt ab Zyklus 2.000 dort; Ursache: Abschluss von etwa 55 MB verstreuter Schreibzugriffe je Zyklus in eine wachsende 20-GB-Datei |
| Begutachtete Punkte R1 bis R8 | R2, R3, R4, R6, R7, R8 erledigt; R1 (`closure_delta` der Experimente weiterhin 0) und R5 (kein messbarer Replay-Effekt im Fenster von 6b) bleiben offen |

### Drift-Urteil über Fenstermittel (13.11.2026, 06:09 Uhr)

| Test | Ergebnis |
|---|---|
| Selbsttest des Runners (`v8_deprivation_runner.py --selftest`) | 6 von 6 bestanden, darunter zwei neue Fälle: ein ruhendes Signal mit später Schwankung und ein oszillierendes Signal ohne Trend (beide fielen mit dem alten Erst-gegen-letzt-Urteil durch) |
| Stabilitäts-Referenz neu bewertet | Gesamturteil „konvergenz“ unverändert; gemeldet nur noch Noradrenalin (+0,054, Reifung) und die Überlebenden im Tiefschlaf (bessere Konsolidierung), alle übrigen Signale „stabil“ |
| Drift-Lauf mit Habituation neu bewertet | vorher „DIVERGENZ-WARNUNG“, jetzt „konvergenz“; allostatische Last „stabil“ (0,114 auf 0,112) |

### Kalibrierung an Lernläufen mit Eingang (20:09 Uhr)

Drei Läufe mit aktuellem Code und ein Kontrolllauf mit dem Code von vor der Botenstoff-Behebung, je 1.000 Zyklen mit Sinneseingang, jeweils auf einer eigenen frischen Kopie der Produktionsdatenbank. Die neun Abnahmekriterien wurden vor den Läufen festgelegt (`Audits/learning_calibration_2026-11-12/criteria.md`).

| Test | Ergebnis |
|---|---|
| Abnahmekriterien K1 bis K9 | in allen drei Läufen erfüllt; keine Nachkalibrierung nötig |
| Belohnungs-Vorhersagefehler wach / Schlaf | +0,009 / 0,000 |
| Noradrenalin und Acetylcholin im Schlaf relativ zum Wachzustand | 0,33 und 0,44 (Kontrolllauf: 0,99 und 0,99) |
| Graduierungen je 1.000 Zyklen | 634 ± 14 (Kontrolllauf 592) |
| Fangquote markierter Spuren | 95 bis 96 % (Kontrolllauf 84 %) |
| Meta-Parameter an einer Grenze, Sättigungseingriffe | 0 / 0 |
| Lernrate | Standardabweichung 0,04, Bereich 0,45 bis 0,85 (Kontrolllauf: fest 0,78) |
| Ausnahmen, versteckte Fehler, Integrität | 0 / 0 / ok |
| Zykluszeit | 1,55 s auf 2,87 s über 1.000 Zyklen, im Kontrolllauf gleich (Datenwachstum, nicht die Behebung) |

Der Entzugslauf über 1.500 Zyklen bleibt als Stabilitäts-Referenz erhalten (`Audits/Stability_Reference_Drift_2026-11-12_1905.md`): Urteil „konvergenz“, keine Divergenz, kein Regler an einer Grenze. Er dient als Regressionstest nach Änderungen, nicht als Grundlage der Kalibrierung. Einzelheiten: `Audits/Learning_Calibration_2026-11-12_2009.md`.

### Botenstoffe und Plastizität nach Behebung und Kalibrierung (17:22 Uhr)

| Test | Ergebnis |
|---|---|
| 400 Zyklen auf frischer DB (12.000 Abschnitte aus dem Korpus-Backup) | 0 Fehler, Integrität OK, 1,78 s pro Zyklus |
| Dopamin | Standardabweichung vorher 0,005, jetzt 0,162; Bereich 0,12 bis 0,93; wach 0,53, Schlaf 0,52 |
| Noradrenalin / Acetylcholin / Serotonin, wach gegen Schlaf | 0,61 / 0,22, 0,50 / 0,22, 0,50 / 0,27 (vorher kein Unterschied) |
| Persistenter Druck | vorher in jedem Zyklus 1,000; jetzt 0,64 bis 0,93, sinkt mit dem Lernerfolg |
| Lernrate | vorher ein eingefrorener Wert; jetzt 0,51 bis 0,85 |
| Plastizitätsanpassungen (6b), Kritiker-Schnappschüsse, Regelereignisse (6c) | vorher 0 / 0 / 0; jetzt 384 / 41 / 4.472 |
| Meta-Parameter an einer Grenze, Sättigungseingriffe (6d) | 0 / 0 |
| Reaktionstest (Erfolg und Misserfolg eingespielt) | Dopamin-Ausschüttung bei unerwarteter Belohnung, Einbruch unter den Ruhewert bei ausbleibender Belohnung, abklingende Antwort bei anhaltender Belohnung, tiefer Einbruch bei Misserfolg; Noradrenalin steigt mit der Überraschung |
| 80 Zyklen auf einer Kopie der Produktionsdatenbank | 0 Fehler, 1,57 s pro Zyklus, 61 Graduierungen |
| End-to-End-Test mit Suche nach versteckten Fehlern, Systemtest, Admin-GUI | 0 Befunde, 7 von 7 OK, 0 Fehler |

### Entwicklungsabhängiger Schlafanteil (13:16 Uhr)

| Test | Ergebnis |
|---|---|
| 400 Zyklen auf frischer DB mit 12.000 echten Abschnitten (Quelle: Korpus-Backup-Datenbank), Standard-Reifung | 0 Fehler, Integrität OK; Wachphasen 12 bis 16 Zyklen, Schlaf 21 bis 23 Zyklen; Schlafanteil 61,8 %; Reife 0 auf 0,19 |
| Graduierungen | 231 (Satz 168, Wortgrenze 63); mit festem Erwachsenenrhythmus im gleichen Aufbau 103 |
| Markierte Survivors | 275 markiert, 242 konsolidiert, 3 vor der Konsolidierung verfallen |
| Gleicher Lauf mit schneller Reifung (Halbreife bei 50 statt 1.000 stabilen Hypothesen) | Wachphasen wachsen von 13 auf 30 Zyklen, Schlafanteil sinkt von 68 % (Zyklen 51 bis 100) auf 44 bis 46 % (Zyklen 151 bis 400) bei Reife 0,80; 199 Graduierungen, 3 Markierungen verfallen |
| 60 Zyklen auf einer Kopie der Produktionsdatenbank | 0 Fehler, 1,35 s pro Zyklus; wach 11 bis 12, Schlaf 22 Zyklen (Reife etwa 0,05); 28 Graduierungen |
| Systemtest | 7 von 7 Prüfpunkten OK |
| Admin-GUI (Schlafanzeige mit Reife, Statusbericht, CSV-Export) | 0 Fehler |

### Schlafschalter (12:50 Uhr)

| Test | Ergebnis |
|---|---|
| 400 Zyklen auf frischer DB mit 12.000 echten Wikipedia-Abschnitten | 0 Fehler, Integrität OK, 1,82 s pro Zyklus |
| Schlafrhythmus | Wachphasen 66, 54, 55, 56, 57 Zyklen; Schlafphasen 22, 22, 22, 22, 23 Zyklen; Schlafanteil 27,8 % |
| Graduierungen | 103 (Satz 71, Wortgrenze 32); 78 im Schlaf, 25 in den ersten Wachzyklen danach |
| Markierte Survivors | 129 markiert, 108 erreichten drei Überlebensrunden, 3 verfielen vor der Konsolidierung |
| Histamin | fällt im Schlaf (etwa 0,42 auf 0,26) und erholt sich nach dem Aufwachen |
| 120 Zyklen auf einer Kopie der Produktionsdatenbank (Migration) | 0 Fehler, 1,25 s pro Zyklus; alte Schlüssel entfernt; Wachphasen 35 (Start bei Adenosin 0,40) und 78 Zyklen, Schlafphase 22 Zyklen; 6 Satz-, 2 Wortgrenzen- und 4 Relations-Graduierungen |
| Systemtest | 7 von 7 Prüfpunkten OK |
| Admin-GUI (unsichtbarer Test der Schlafanzeige, des Statusberichts und des CSV-Exports) | 0 Fehler |
| Vergleich mit dem alten Auslöser, 150 Zyklen, gleicher Aufbau | alt: 97 Graduierungen, etwa 66 % Schlafzyklen; neu: 19 Graduierungen nach 150 Zyklen (erster Schlaf bei Zyklus 67), 103 nach 400 Zyklen; Graduierungen pro Schlafzyklus fast gleich (alt 0,98, neu 0,93) |

### Frühere Tests (12:16 Uhr)

| Test | Ergebnis |
|---|---|
| Systemtest auf einer Kopie der Produktionsdatenbank | 7 von 7 Prüfpunkten OK |
| 200 Zyklen auf frischer DB mit 300 echten Wikipedia-Abschnitten | 0 Fehler, 0 versteckte Fehlerzustände, Integrität OK |
| davon Graduierungen Satz / Wortgrenze / Relation | 49 / 28 / 52 |
| davon Fakten / Relationen / Kategorien / Fragen | 48 / 18 / 11 / 167 |
| davon Revisionen ohne künstlichen Anstoß | 1 (Cue „März 20“, gespeichert 1 gegen Konkurrent 6; keine sofortige Wieder-Graduierung) |
| Steuerwerte in den Experiment-Ergebnissen | echte Werte, z. B. Lernrate 0,78, Fehlergewicht 0,81, Dopamin 0,31 |
| Fragen-Gruppen aus echten Fragen (5b) und deren Bewertung (5c) | 3 Gruppen, 490 Bewertungen |
| 300 Zyklen mit Rückkopplung (frische DB) | 0 Fehler; Exploration 0,31 auf 0,75 (Obergrenze von 5b) in ca. 50 Zyklen, Hemmung pendelt bei 0,67 bis 0,70; 190 Graduierungen, 70 Fakten |
| 15 Zyklen auf einer Kopie der Produktionsdatenbank | 0 Fehler, 1,49 s pro Zyklus; Exploration 0,50 auf 0,74, Hemmung 0,20 auf 0,31 |
| Korrekturtest (eindeutig / knapp / echter Zyklus) | korrigiert / unverändert / im ersten Zyklus korrigiert |
| Inkrementelle Aggregate gegen vollständige Neuberechnung | Abweichung 0, auch nach Einfügen, Upsert, Ändern, Löschen |
| Lern-Reset über Kommandozeile und GUI | erfolgreich, Korpus und Volltextsuche erhalten |
| Admin-GUI (alle Reiter, Schließen) und Lese-GUI (Suche, Antwort, Chat) | 0 Fehler |

---

## 7. Performance

| Messung | Zeit pro Zyklus |
|---|---|
| Produktionsgröße, Stand vor den Optimierungen | 22,5 s |
| Produktionsgröße, aktueller Stand | etwa 1,0 s zu Beginn eines Laufs, etwa 1,25 s nach 1.000 Lernzyklen (vor der Behebung der Zykluszeit: 1,56 s steigend auf 2,89 s) |
| Kleiner Korpus (300 Abschnitte), aktueller Stand | 0,9 s |
| Produktionslauf, 20-GB-Datenbank (13.11.2026) | etwa 3,5 s zu Beginn, etwa 11 s ab Zyklus 2.000; Rechenanteil etwa 2,7 s, Abschluss der Transaktion etwa 10 s |
| Verdichtete Kopie (5,8 GB), allein auf dem Pool, nach den Paketen A und B | Median 2,49 s, Mittel 3,75 s (alter Code: 5,95 s / 5,14 s) |
| Abschlusslauf über 1.000 Zyklen, alle Pakete | 2,5 s in den ersten 10 % bis 5,5 s in den letzten 10 %; Profil am Ende: 6,4 s, davon 5,2 s Abschluss der Transaktion und 1,2 s Rechenarbeit |

Wirksame Maßnahmen:
- Schema-Prüfung einmal pro Datenbankverbindung statt pro beobachtetem Satz
- laufend gepflegte Summen für die Auswertungen von 5h und 5i (Trigger) statt Neuberechnung über 0,9 Mio. Zeilen
- gezielte Indizes auf häufig abgefragten Spalten, Ausdrucks-Indizes für die Replay-Kandidatenwahl in Phase 6a
- genau ein eindeutiger Index pro Tabellenspalte
- zwischengespeicherte Volltextsuchen der Lese-Rückkopplung, gültig bis zum nächsten Import
- fehlende Oberflächenbelege von Relationen werden bis zur nächsten Korpusänderung gemerkt statt in jedem Zyklus neu gesucht
- reine Rückschreibungen ohne Leser in 5h entfernt, 5g trägt nur fehlende Lückenprioritäten nach, indexfreundliche Abfrageformen in 7d und 5d, keine Schema-Abfragen pro Experiment
- zeitbasierte Habituation der Lücken und eine Kontrastsuche mit den seltensten Wörtern senkten den verbleibenden Zuwachs auf +0,22 s je 1.000 Zyklen; siehe `Audits/Cycle_Time_Investigation_2026-11-12_2121.md` und `Audits/Gap_Habituation_2026-11-12_2208.md`
- Aufbewahrung der Ereignisprotokolle (letzte 1.000 Zyklen) und einmalige Verdichtung (20,5 GB auf 5,8 GB); 5h schreibt nur geänderte Bewertungen; gebündelter globaler Zerfall; siehe `Audits/Pakete_A-D_C5_2026-11-13_2320.md`
- der Abschluss der Transaktion auf dem Speicherpool (SSDs unterschiedlicher Geschwindigkeit) bestimmt die Zykluszeit und schwankt ohne Codeänderung zwischen etwa 2,4 und 7 s; ein größerer Seitencache hilft nicht

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
| Die Zykluszeit steigt weiter mit den gelernten Tabellen | seit 16.11.2026: CPU-Zeit 2,6 s pro Zyklus, ein Commit pro Zyklus statt etwa 74, etwa ein Fünftel weniger geschrieben; ein Zyklus schreibt aber noch etwa 50 MB, und die Wandzeit schwankt mit dem Speicherpool | messen, welche Tabellen und Indizes die Schreiblast verursachen |
| Ontologie auf dem Produktionsstand | gelöst am 16.11.2026: Kategorien entstehen nur aus Worteinheiten; Silben-Cluster werden beobachtet, aber nie befördert; die Ontologie ist jetzt leer, der erwartete Stand, solange keine Worteinheit bestätigt ist | beobachten, sobald Wörter entstehen |
| Streuung der Lernrate | 0,010 bis 0,012 in den Prüfläufen vom 16.11.2026, knapp an der Grenze von K7 (0,01) | beobachten |
| Fangquote (K5) wird am Laufende zensiert | gelöst am 16.11.2026: K5 zählt nur Spuren, die mindestens 250 Zyklen vor Laufende markiert wurden (Einfangen dauert im Median 62 Zyklen, 99. Perzentil 238); 0,886 im Prüflauf R7 | keine |
| Schreiblast auf dem Speicherpool | die Zykluszeit schwankt zwischen etwa 2 und 10 s; ein Commit pro Zyklus hat die Wandzeit nicht messbar verändert | der Pool lässt sich derzeit nicht ändern; die Schreibmenge selbst senken |
| Die Replay-Wirksamkeit zeigt keinen messbaren Nutzen der Reaktivierung (leicht negativ, nicht gesichert) | 6b passt die Plastizität nur bei schwachen Belegen an | mögliche Zensierung: reaktivierte Spuren graduieren früher und überleben danach nicht mehr; nächste Prüfung: Graduierung innerhalb des Horizonts als Erfolg zählen |
| Die Reifezahl zählt stabile Hypothesen, die überwiegend Textstücke sind | das System verlässt seinen Säuglingsrhythmus früher, als es seinem Entwicklungsstand entspricht | Reife an die Art des Gelernten koppeln, sobald Satzbezüge entstehen |
| Fakten sind beobachtete Textstücke mit der Relation `observed_as`; 27 % stammen aus Literaturangaben | noch keine Aussagen über Inhalte | zurückgestellt: früher Entwicklungsstand, das System lernt noch Wörter und Satzzusammenhänge |
| Relationen (`associated_with`) und Kategorien verbinden oft einzelne Zeichen oder Silben | frühe Relationen und Kategorien sind Rauschen; die Kategorien sind jetzt stabil, bestehen aber weiter aus Zeichen und Silben | zurückgestellt: verbessert sich mit gelernten Wortgrenzen |
| Ungeprüfte Textkontraste werden nie automatisch aufgelöst | seit 16.11.2026 entstehen sie nur nach den Rahmenregeln (36 Rahmen-Lücken in 1.000 Zyklen statt 27.032 Lücken pro Paar); die 274.644 alten bleiben in der Tabelle, ihre Lücken sind habituiert | gewollt (Wiederholung ist keine Wahrheit); alte Zeilen über `semantic_frame_gap_log` umkehrbar |
| Pro Zyklus höchstens eine Graduierung | begrenzt die Lerngeschwindigkeit | gewolltes Budget |
| Im Schlaf wird weitergelesen | Schlaf kostet keine Lesezeit | biologisch wird der Sinneseingang im Schlaf gedrosselt; Entscheidung offen |
| `Audits/System_Audit_2026-09-28.md` | beschreibt den Stand vom 28.09.2026 | historisches Dokument |
