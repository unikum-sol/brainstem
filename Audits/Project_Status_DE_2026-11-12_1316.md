# BrainStem: Projekt- und Funktionsstatus

**Stand:** 12.11.2026, 13:16 Uhr
**Umfang:** Code (`ki_system/`, `main.py`), Produktionsdatenbank `ki_memory.sqlite3`, Testergebnisse vom 12.11.2026

---

## 1. Zusammenfassung

| Bereich | Status |
|---|---|
| Lernkette | 36 Phasen, alle laden fehlerfrei, Kettenspitze: Stage-B Question-Chunk-Feedback |
| Lernen auf allen Ebenen | aktiv: Sätze, Wortgrenzen und Relationen konsolidieren und graduieren |
| Selbstkorrektur | aktiv und nachgewiesen: Cue-Konkurrenz, Revision, Rücknahme von Fakten, Rekonsolidierung |
| Emergenz von Relationen, Kategorien, Fragen | aktiv und produktiv |
| Botenstoffe | 12 Botenstoffe aktiv, 22 neuromodulierte Schwellen, Raten und Budgets, Strategiephasen 5b bis 5i mit echten Steuerwerten |
| Schlafen und Wachen | ein gemeinsamer Auslöser: ein einziger Schlaf-Wach-Schalter mit Hysterese; Adenosin folgt der Lernlast; entwicklungsabhängiger Schlafanteil: etwa zwei Drittel Schlaf im unreifen Zustand, sinkt mit wachsendem konsolidiertem Wissen zum Erwachsenenrhythmus (etwa 55 Wach- und 22 Schlafzyklen) |
| Systemtest | alle 7 Prüfpunkte OK |
| Geschwindigkeit | ca. 1,3 bis 1,6 s pro Zyklus auf Produktionsgröße, ca. 0,9 s auf kleinem Korpus |
| Produktionsdatenbank | 5,57 GB, Integritätsprüfung OK; die neuen Mechanismen sind darauf noch nicht gelaufen |

---

## 2. Code-Stand

- **Paket:** `ki_system`, 60 Python-Module, zusammen mit `main.py` 19.173 Zeilen
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
| 3 | Phase 5b | verfeinert Lesestrategien aus Ergebnissen, hartnäckigen Lücken und Clustern; gruppiert die echten Fragen nach Lückentyp und Rolle; diversifiziert die Leseauswahl; wirkt mit gedämpftem Schritt auf Explorations- und Hemmungs-Bias zurück | aktiv, echte Steuerwerte, Rückkopplung aktiv |
| 4 | Phase 5c | bewertet die Fragen-Gruppen aus 5b (Größe, Priorität, Lösungsanteil) und straft unergiebige Leseziele ab | aktiv |
| 5 | Phase 5d | Beobachtungs- und Strategiegedächtnis aus echten Kennzahlen (Experiment-Ergebnisse, geschlossene Lücken, Graduierungen, offene Fragen, Steuerwerte) | aktiv |
| 6 | Stage-B Gap Detection | erkennt Lücken: „stalled“ (oft gesehen, nie gefestigt) und „contested“ (Cue-Konkurrenz); Habituation und Dishabituation; hält den Lösungswert jeder Lücke aktuell (geschlossen = 1, sonst 0) | aktiv |
| 7 | Phase 5e | plant Kontexterweiterungen rund um Lücken und erhöht die Priorität benachbarter Abschnitte | aktiv |
| 8 | Phase 5f | misst die Wirksamkeit der Kontextfenster und passt sie an (Fensterbreite abhängig von Hemmung und Exploration) | aktiv, echte Steuerwerte |
| 9 | Phase 5g | wählt Kontextstrategien aus und führt das Experimentgedächtnis | aktiv, echte Steuerwerte |
| 10 | Phase 5h | wertet Strategie-Experimente aus und lernt daraus; speichert zu jedem Ergebnis die echten Steuerwerte und Botenstoffe | aktiv, echte Steuerwerte |
| 11 | Phase 5i | diversifiziert Strategien anhand der Ergebnisse | aktiv, echte Steuerwerte |
| 12 | Phase 6a | Schlaf-Replay und Meta-Plastizität; berechnet Dopamin, Serotonin, Noradrenalin, Acetylcholin aus dem Replay (phasisch) und mischt den tonischen Zielwert bei | aktiv |
| 13 | Phase 6b | misst die Wirksamkeit des Replays, passt die Plastizität an, Critic-Gate; Anpassungen gehen in den dauerhaften Bias-Zielwert ein | aktiv |
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
| `semantic_evidence.py` | Oberflächen-Belege und ungeprüfte Textkontraste (werden nie automatisch aufgelöst) | aktiv |
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
| Exploration steht bei vielen ungelösten Lücken an der Obergrenze von 5b (0,75) | das System sucht dauerhaft breit | beobachten, sinkt mit mehr gelösten Lücken |
| Nur wenige Lücken schließen sich (im 200-Zyklen-Lauf 1 von 946) | Lösungswerte und damit Dopamin bleiben niedrig | beobachten |
| Botenstoffe stehen im Zustand hohes Noradrenalin / niedriges Serotonin | Kopplungen arbeiten dauerhaft im „Alarm“-Bereich | beobachten, ob sich das mit mehr geschlossenen Lücken ändert |
| Neue Mechanismen noch nicht auf der Produktionsdatenbank gelaufen | Langzeitverhalten auf dem vollen Korpus unbekannt | nächster Schritt |
| Fakten sind beobachtete Sätze mit der Relation `observed_as` | noch keine Aussagen über Inhalte | gewollt im Tabula-rasa-Ansatz |
| Relationselemente sind früh oft einzelne Zeichen oder Wortstücke | frühe Relationen und Kategorien sind Rauschen | gewollt, verbessert sich mit gelernten Wortgrenzen |
| Ungeprüfte Textkontraste werden nie automatisch aufgelöst | viele offene Kontraste in der Tabelle | gewollt (Wiederholung ist keine Wahrheit) |
| Pro Zyklus höchstens eine Graduierung | begrenzt die Lerngeschwindigkeit | gewolltes Budget |
| Das Reifungstempo hängt vom Kalibrierwert 1.000 stabile Hypothesen für halbe Reife ab | bestimmt, wie lange das System seinen Säuglingsrhythmus behält | auf dem Produktionskorpus beobachten, bei Bedarf nachkalibrieren |
| Ein reifes System graduiert weniger Hypothesen pro Zyklus (weniger Schlafzyklen, eine Graduierung pro Zyklus) | die Konsolidierung pro Schlafzyklus ist unverändert | gewollt: der entwicklungsabhängige Anteil hält die Konsolidierung hoch, solange wenig bekannt ist |
| Im Schlaf wird weitergelesen | Schlaf kostet keine Lesezeit, die Schlafdauer hat daher keine Lernkosten | biologisch wird der Sinneseingang im Schlaf gedrosselt; Entscheidung offen |
| Wird jeder Abschnitt nur einmal gelesen, entstehen keine Relationshypothesen (alter und neuer Code gleich) | die relationale Bindung braucht wiederholtes gemeinsames Auftreten | Eigenschaft des Korpus, kein Schlafeffekt |
| `assets/Project-Structure.png` fehlt im Projektordner | Bild im README wird lokal nicht angezeigt | offen |
| `Audits/System_Audit_2026-09-28.md` | beschreibt den Stand vom 28.09.2026 | historisches Dokument |
