# BrainStem: Project and Function Status

**As of:** 12 November 2026, 13:16
**Scope:** code (`ki_system/`, `main.py`), production database `ki_memory.sqlite3`, test results from 12 November 2026

---

## 1. Summary

| Area | Status |
|---|---|
| Learning chain | 36 phases, all load without errors, chain top: Stage-B question-chunk feedback |
| Learning on all layers | active: sentences, word boundaries and relations consolidate and graduate |
| Self-correction | active and demonstrated: cue competition, revision, fact retraction, reconsolidation |
| Emergence of relations, categories, questions | active and productive |
| Neuromodulators | 12 neuromodulators active, 22 neuromodulated thresholds, rates and budgets, strategy phases 5b to 5i use live control values |
| Sleep and wake | one common trigger: a single sleep/wake switch with hysteresis; adenosine driven by encoding load; developmental sleep share: about two thirds sleep while immature, falling toward the adult rhythm (about 55 wake and 22 sleep cycles) as consolidated knowledge grows |
| System test | all 7 checks OK |
| Speed | about 1.3 to 1.6 s per cycle at production scale, about 0.9 s on a small corpus |
| Production database | 5.57 GB, integrity check OK; the new mechanisms have not yet run on it |

---

## 2. Code Status

- **Package:** `ki_system`, 60 Python modules, 19,173 lines including `main.py`
- **Entry points:** `python main.py --gui` (admin GUI), `python main.py --user-gui` (read-only dialogue GUI)
- **System check:** `python -m ki_system.systemtest` (runs on a copy of the database)
- **Corpus-preserving learning reset:** GUI button or `python -m ki_system.reset_learning --apply`
- All modules compile without errors.

---

## 3. Learning Chain (execution order)

Each phase first calls the phase registered before it and then does its own work. The execution order therefore equals the registration order in `phase_registry.py`.

| No. | Phase | Function | Status |
|---|---|---|---|
| 1 | Context Observation | reads text chunks, splits them into sentences, creates or re-observes sentence hypotheses (evidence count, confidence) | active |
| 2 | Phase 0 Lexical | word boundaries from the unsegmented character stream via branching entropy | active |
| 3 | Phase 5b | refines reading strategies from outcomes, persistent gaps and clusters; clusters the real questions by gap type and role; diversifies chunk selection; acts back on the exploration and inhibition biases with a damped step | active, live control values, feedback active |
| 4 | Phase 5c | evaluates the question clusters from 5b (size, priority, resolved share) and penalizes unproductive reading targets | active |
| 5 | Phase 5d | observation and strategy memory from real metrics (experiment outcomes, closed gaps, graduations, open questions, control values) | active |
| 6 | Stage-B Gap Detection | detects gaps: "stalled" (seen often, never consolidated) and "contested" (cue competition); habituation and dishabituation; keeps every gap's resolution value current (closed = 1, otherwise 0) | active |
| 7 | Phase 5e | plans context expansions around gaps and raises the priority of neighbouring chunks | active |
| 8 | Phase 5f | measures the effectiveness of context windows and adapts them (window width depends on inhibition and exploration) | active, live control values |
| 9 | Phase 5g | selects context strategies and keeps the experiment memory | active, live control values |
| 10 | Phase 5h | evaluates strategy experiments and learns from them; stores the live control values and neuromodulators with every outcome | active, live control values |
| 11 | Phase 5i | diversifies strategies based on outcomes | active, live control values |
| 12 | Phase 6a | sleep replay and meta-plasticity; computes dopamine, serotonin, noradrenaline and acetylcholine from replay (phasic) and blends in the tonic target | active |
| 13 | Phase 6b | measures replay effectiveness, adjusts plasticity, critic gate; adjustments enter the persistent bias target | active |
| 14 | Phase 6c | keeps bias values across cycles (persistent target fed by 5b, 6b, 6d, 7a, 7b), self-regulates meta-parameters | active |
| 15 | Phase 6d | saturation homeostasis (sliding threshold) and meta-metaplasticity | active |
| 16 | Phase 7a | adenosine as sleep pressure (Process S): saturating rise with encoding load during wake, faster while the system is immature, exponential decay during sleep; renormalizes saturated biases at sleep onset; does not decide sleep itself | active, reads the switch state |
| 17 | Phase 7b | endocannabinoids: 2-AG as a fast brake, anandamide as a slow pull of saturated values back to mid-range | active |
| 18 | Phase 7b1 | wake-chain bridge: runs 6a to 7b in a fixed order | active |
| 19 | Phase 7c | adaptive boundaries, soft clipping at the edges, glutamate-GABA balance | active |
| 20 | Connection Accelerator | applies fast SQLite settings to every new connection | active |
| 21 | Phase 7d | slow-wave consolidation with prioritized replay (see 4.1) | active |
| 22 | Phase 7e | histamine: wakefulness, antagonist of adenosine; suppressed during sleep by the switch (flip-flop) | active, reads the switch state |
| 23 | Phase 7f | orexin: reading endurance and curiosity | active |
| 24 | Phase 7g | BDNF: activity-dependent growth and consolidation | active |
| 25 | Phase 7cort | cortisol: stability watcher, Stage 2 (guarded soft regulator) | active, calm in operation |
| 26 | Cooperative Core | joint dynamics of the six core neuromodulators; the single sleep/wake switch (see 4.7) | active |
| 27 | Stage-B Graduation | at most one graduation per cycle, roles compete via divisive normalization | active |
| 28 | Stage-B Contradiction Detection | decides cue competitions from evidence; records unverified surface contrasts | active |
| 29 | Stage-B Hypothesis Revision | reverts consolidated hypotheses that lost a competition, closes the gap | active |
| 30 | Stage-B Fact Promotion | graduated sentence and word-boundary hypotheses become facts; retraction on revision | active |
| 31 | Phase 0b Relational Binding | binds co-occurring elements (PMI, direction from position) | active |
| 32 | Stage-B Relation Promotion | graduated relation hypotheses become relations | active |
| 33 | Stage-B Ontology Cluster Observation | Label Propagation over the relation graph, prototype anchor | active |
| 34 | Stage-B Ontology Promotion | stable clusters become ontology entries (membership) | active |
| 35 | Stage-B Question Promotion | persistent gaps become questions | active |
| 36 | Stage-B Question-Chunk Feedback | open questions steer reading (source chunk and full-text search) | active |

---

## 4. Core Mechanisms

### 4.1 Prioritized replay (Phase 7d)

| Element | Function | Coupling |
|---|---|---|
| Track "anchors" | consolidated knowledge is replayed interleaved and thus protected from interference | serotonin |
| Track "tagged survivors" | hypotheses with 1 to 2 consolidations; the tag decays after a time window | dopamine (share and tag lifetime) |
| Track "novel" | sampled per role: partly from recently seen material, partly at random over the whole population | noradrenaline (share), dopamine (share of recently seen material) |
| Initial activity | derived from the hypothesis's repetition history (frequently seen material consolidates more readily) | |
| Down-selection | threshold within each population (anchors, strategy experiments, hypotheses) | GABA, glutamate, acetylcholine |
| Role shares | sentences 50 %, relations 25 %, word boundaries 25 % of the novel slots; unused slots go to the other roles | |

**Status:** active. In the 150-cycle test, graduation reached the intended budget of one graduation per cycle.

### 4.2 Self-correction through cue competition

| Step | Module | Status |
|---|---|---|
| Learned cue: shortest prefix that ends at a learned word boundary and covers a minimum share of the pattern (share coupled to acetylcholine) | `v8_cue_competition.py` | active |
| Competitors: other observed completions of the same cue | Gap Detection | active |
| Decision from evidence only: "resolvable", "confirmed", "open"; threshold coupled to noradrenaline | Contradiction Detection | active |
| Reversion of the losing hypothesis, closing of the gap | Hypothesis Revision | active |
| Retraction of the fact | Fact Promotion | active |
| Reconsolidation: after a revision, only new consolidations count | Graduation | active |

**Evidence:** a test scenario with a clear-cut competitor is corrected, a close scenario stays unchanged. In learning runs on real Wikipedia chunks, corrections occurred without any artificial trigger, e.g. cue "August" (stored 1 observation, competitor 6) and cue "April 20" (1 vs. 3). Reverted hypotheses did not graduate again immediately.

### 4.3 Emergence layers

| Layer | Function | Status |
|---|---|---|
| Word boundaries | branching entropy over a context of length 3, minimum 8 observations, threshold 1.0 bit | active, takes part in consolidation with its own quota |
| Relations | PMI existence test, direction from positional asymmetry (threshold for German 0.72) | active |
| Categories | Label Propagation, prototype as anchor, placeholder relation `member_of_cluster` | active |
| Questions | promotion of persistent gaps, priority via dopamine and acetylcholine | active |
| Reading feedback | the question's source chunk and chunks found by full-text search get higher priority | active |
| Habituation | unproductive gaps become "habituated" (reversible) | active |

### 4.4 Neuromodulated thresholds and budgets

22 couplings; at the neutral value 0.5 each one yields exactly its calibrated base value.

| Coupling | Neuromodulator |
|---|---|
| Existence threshold of gap detection | noradrenaline |
| Habituation threshold | serotonin |
| Existence threshold of relational binding | noradrenaline |
| Direction threshold of relational binding | acetylcholine |
| Revision budget | acetylcholine |
| Decision ratio of cue competition | noradrenaline |
| Cue length | acetylcholine |
| Role pressure at graduation | acetylcholine |
| Temperature of divisive normalization | GABA |
| Replay shares anchors / tagged / novel | serotonin / dopamine / noradrenaline |
| Tag lifetime, share of recently seen samples | dopamine |
| Stability streak of categories | serotonin |
| Minimum category size (direction learned from outcomes) | noradrenaline |
| Overlap threshold of categories | dopamine |
| Budget of category promotion | acetylcholine |
| Existence threshold of questions | noradrenaline |
| Priority of questions | dopamine, acetylcholine |
| Strength of reading feedback | via the question's priority |
| Consolidation gate in Phase 7d | acetylcholine |
| Rise rate of adenosine during wake | glutamate |
| Decay rate of adenosine during sleep | GABA |
| Sleep and wake thresholds (shifted together, at most 0.1) | histamine, orexin, noradrenaline, acetylcholine, cortisol against GABA |

### 4.5 Control values of the strategy phases

Phases 5b, 5d, 5f, 5g, 5h and 5i take their control values from the live state via `v8_learning_controls.py`:

| Control value | Source |
|---|---|
| Learning rate | plasticity level from Phase 6a |
| Exploration pressure | exploration bias from Phase 6a |
| Consolidation | consolidation bias from Phase 6a |
| Inhibition | inhibition bias from Phase 6a |
| Revision pressure | revision bias from Phase 6a |
| Error weight | noradrenaline (arousal from unexpected outcomes weights new evidence and errors; Yu & Dayan 2005; Nassar et al. 2012) |
| Dopamine, serotonin, glutamate, GABA, noradrenaline, acetylcholine | shared neuromodulator state from Phases 6a and 7c |

The calibrated base values apply only while a value has not been written yet (fresh database before the first sleep cycle).

**Strategy feedback (Phase 5b):** many persistent, unresolved gaps push toward exploration, success toward exploitation (Cohen, McClure & Yu 2007). Phase 5b's recommendation moves the persistent bias target by a damped step (parameter `bias_feedback_gain`, base value 0.5). Counterforces: saturation homeostasis (6d) and the anandamide pull (7b).

### 4.6 Other modules

| Module | Function | Status |
|---|---|---|
| `autonomous.py` | core of the learning loop; the chain is attached by the registry | active |
| `phase_registry.py` | load order, error capture, self-check of the chain | active |
| `db_bootstrap.py` | central, idempotent schema: tables, columns, indexes, expression indexes | active |
| `db_runtime.py` | consistent database snapshots | active |
| `memory.py` | database access, documents and chunks, full-text index | active |
| `ingest.py` | import of ZIM, TXT, PDF, resume after interruption | active |
| `search.py`, `dialogue.py`, `text_utils.py`, `wiki_quality.py` | search, answers, dialogue, neutral text helpers without word filters | active |
| `semantic_evidence.py` | surface evidence and unverified text contrasts (never resolved automatically) | active |
| `v8_cue_competition.py` | learned cues and competing completions | active |
| `v8_outcome_aggregates.py` | trigger-maintained sums over the experiment outcomes for 5d, 5h and 5i | active |
| `v8_learning_controls.py` | control values and neuromodulators of the strategy phases from the live state | active |
| `fractional_control.py` | bounded error diffusion for discrete budgets (ontology) | active |
| `v8_cycle_diagnostics_release.py` | recursively evaluates cycle results for errors | active |
| `v8_sensory_deprivation.py`, `v8_deprivation_runner.py` | learning without new input, CSV log, drift report | active (GUI) |
| `v8_wal_maintenance_release.py` | maintenance of the write-ahead log | active |
| `reset_learning.py` | corpus-preserving learning reset, dry run, full backup, checks | active, tested |
| `systemtest.py` | system check on a copy of the database | active |
| `gui_app.py`, `user_gui.py` | admin GUI and read-only dialogue GUI; the admin GUI shows one sleep state with sleep pressure, both thresholds, dwell time, maturity and the reason of the last transition | active, tested |

### 4.7 Sleep and wake: one common trigger

Until now two independent mechanisms could start consolidation: the adenosine homeostat in Phase 7a (its own sleep mode) and a weighted sleep score in the cooperative core. Phase 7d slept when either of them said "sleep". In operation only Phase 7a ever triggered (production database: 259 transitions in 1,947 cycles, about 5 wake and 10 sleep cycles per episode, 66 % sleep); the cooperative score never reached its threshold.

Now exactly one switch decides: the sleep/wake switch in the cooperative core. Phase 7a, Phase 7d, Phase 7e and the GUI read its state.

| Element | Function | Basis |
|---|---|---|
| Sleep pressure S (adenosine, Phase 7a) | wake: `S = 1 - (1 - S) * exp(-k_wake)`, sleep: `S = S * exp(-k_sleep)` | two-process model (Borbély 1982; Daan, Beersma & Borbély 1984) |
| Time constants | ratio of rise to decay as in the human fits (18.2 h / 4.2 h); base rates 0.0154 and 0.0666 per cycle | Skeldon, Dijk & Derks 2014 |
| How much S rises | `k_wake = 0.0154 * (0.5 + load) * glutamate factor`; load = new hypotheses and experiment outcomes of the cycle relative to the system's own running novelty level, `n / (n + reference)` | adenosine accumulates with neural activity (Porkka-Heiskanen et al. 1997; Brambilla, Chapman & Greene 2005); sleep need grows with wake learning (Tononi & Cirelli 2006; Huber et al. 2004) |
| How fast S falls | `k_sleep = 0.0666 * GABA factor` | deeper slow-wave sleep with stronger GABAergic inhibition (Walsh et al. 2008) |
| When the system sleeps | S reaches the upper threshold 0.67 | upper threshold of the two-process model |
| When the system wakes | S has dissipated to the lower threshold 0.17 | lower threshold of the two-process model |
| Threshold shift | both thresholds shift together by `0.1 * (wake drive - sleep drive)`, at most 0.1; wake drive from histamine, orexin, noradrenaline, acetylcholine, cortisol; sleep drive from GABA, inhibition bias and low glutamate | flip-flop between VLPO and arousal system (Saper, Chou & Scammell 2001; Saper, Scammell & Lu 2005) |
| Mutual inhibition | during sleep the histamine target is halved; lower histamine lowers the wake drive and stabilizes sleep | VLPO inhibits the tuberomammillary nucleus (Sherin et al. 1998; Takahashi, Lin & Sakai 2006) |
| Sleep onset | saturated meta-plasticity biases are pulled toward their mid values | synaptic renormalization (Tononi & Cirelli 2006) |
| Developmental sleep share | `k_wake` is multiplied by `1 + 4 * (1 - maturity)`, `maturity = knowledge / (knowledge + 1000)`, knowledge = net number of hypotheses in a stable role (revisions count back down); a fresh system builds up pressure five times faster and sleeps about two thirds of the time | newborns sleep about two thirds of the day, the share falls with age (Roffwarg, Muzio & Dement 1966); sleep pressure builds up faster in younger children while its dissipation stays the same (Jenni, Achermann & Carskadon 2005; Tarokh, Carskadon & Achermann 2012); sleep need falls with brain maturation (Feinberg & Campbell 2010) |

**Not too early, not too late.** A wake episode lasts `0.92 / k_wake` cycles: about 11 to 13 cycles in a fresh system and about 55 to 65 cycles in a mature one at typical load, between roughly 7 (newborn, high load, high glutamate) and 150 cycles (mature, no new material). It therefore always ends inside the dopamine-modulated synaptic tag window of Phase 7d (225 to 375 cycles), so tagged traces are consolidated before they decay. A sleep episode lasts about 20 to 23 cycles. Each wake episode collects several thousand new hypotheses, more than one sleep episode can replay, so replay remains selective.

**Migration:** obsolete keys of the old mechanisms (sleep mode of Phase 7a, sleep score, fixed enter and exit thresholds, minimum dwell) are removed automatically on the first run. The stored adenosine value is kept.

---

## 5. Production Database

| Metric | Value |
|---|---|
| File size | 5.57 GB |
| Tables / indexes | 147 / 71 |
| Integrity check | OK |
| Documents / chunks | 2 / 167,661 |
| Chunks read since the last learning reset | 62,244 (37.1 %) |
| Learning cycles since the last learning reset | 1,947 (of which 1,294 slow-wave cycles) |
| Hypotheses in total | 937,552 |
| of which sentence uncertain / stable | 609,096 / 36 |
| of which word boundary uncertain | 320,032 |
| of which relation uncertain | 8,388 |
| Facts / relations / categories | 36 / 0 / 0 |
| Questions open / resolved | 202 / 11 |
| Knowledge gaps | 514 |
| Experiment outcomes | 901,852 |
| Word-boundary statistics (transitions) | 432,587 |
| Progress of word-boundary layer / relation layer | up to chunk 15,576 / up to chunk 5,872 |

**Neuromodulators (last state):** dopamine 0.31, serotonin 0.34, noradrenaline 0.80, acetylcholine 0.56, glutamate 0.68, GABA 0.47; cortisol Stage 2, regime "calm".

**Note:** the database was last operated with a version that did not yet contain prioritized replay and cue competition. Graduations have therefore been at a standstill since cycle 1,226, and there are no relations or categories in it yet. On the next start, the bootstrap creates the new indexes and the aggregate table once (seconds to a few minutes).

---

## 6. Test Results from 12 November 2026

### Developmental sleep share (13:16)

| Test | Result |
|---|---|
| 400 cycles on a fresh DB with 12,000 real chunks (source: corpus backup database), default maturation | 0 errors, integrity OK; wake episodes 12 to 16 cycles, sleep 21 to 23 cycles; sleep share 61.8 %; maturity 0 to 0.19 |
| Graduations | 231 (sentence 168, word boundary 63); 103 with the fixed adult rhythm in the same setup |
| Tagged survivors | 275 tagged, 242 captured, 3 expired before consolidation |
| Same run with fast maturation (half-maturity knowledge 50 instead of 1,000) | wake episodes grow from 13 to 30 cycles, sleep share falls from 68 % (cycles 51 to 100) to 44 to 46 % (cycles 151 to 400) at maturity 0.80; 199 graduations, 3 tags expired |
| 60 cycles on a copy of the production database | 0 errors, 1.35 s per cycle; wake 11 to 12, sleep 22 cycles (maturity about 0.05); 28 graduations |
| System test | 7 of 7 checks OK |
| Admin GUI (sleep display with maturity, status report, CSV export) | 0 errors |

### Sleep switch (12:50)

| Test | Result |
|---|---|
| 400 cycles on a fresh DB with 12,000 real Wikipedia chunks | 0 errors, integrity OK, 1.82 s per cycle |
| Sleep rhythm | wake episodes 66, 54, 55, 56, 57 cycles; sleep episodes 22, 22, 22, 22, 23 cycles; sleep share 27.8 % |
| Graduations | 103 (sentence 71, word boundary 32); 78 during sleep, 25 in the first wake cycles after it |
| Tagged survivors | 129 tagged, 108 reached three survivals, 3 expired before consolidation |
| Histamine | falls during sleep (about 0.42 to 0.26) and recovers after waking |
| 120 cycles on a copy of the production database (migration) | 0 errors, 1.25 s per cycle; old keys removed; wake 35 (started at adenosine 0.40) and 78 cycles, sleep 22 cycles; 6 sentence, 2 word-boundary and 4 relation graduations |
| System test | 7 of 7 checks OK |
| Admin GUI (headless check of the sleep display, status report and CSV export) | 0 errors |
| Comparison with the old trigger, 150 cycles, same setup | old: 97 graduations, about 66 % sleep cycles; new: 19 graduations after 150 cycles (first sleep at cycle 67), 103 after 400 cycles; graduations per sleep cycle almost equal (0.98 old, 0.93 new) |

### Earlier tests (12:16)

| Test | Result |
|---|---|
| System test on a copy of the production database | 7 of 7 checks OK |
| 200 cycles on a fresh DB with 300 real Wikipedia chunks | 0 errors, 0 hidden error states, integrity OK |
| of which graduations sentence / word boundary / relation | 49 / 28 / 52 |
| of which facts / relations / categories / questions | 48 / 18 / 11 / 167 |
| of which revisions without artificial trigger | 1 (cue "März 20", stored 1 vs. competitor 6; no immediate re-graduation) |
| Control values stored with experiment outcomes | live values, e.g. learning rate 0.78, error weight 0.81, dopamine 0.31 |
| Question clusters from real questions (5b) and their evaluation (5c) | 3 clusters, 490 evaluations |
| 300 cycles with feedback (fresh DB) | 0 errors; exploration 0.31 to 0.75 (Phase 5b's upper bound) within about 50 cycles, inhibition oscillates around 0.67 to 0.70; 190 graduations, 70 facts |
| 15 cycles on a copy of the production database | 0 errors, 1.49 s per cycle; exploration 0.50 to 0.74, inhibition 0.20 to 0.31 |
| Correction test (clear-cut / close / real cycle) | corrected / unchanged / corrected in the first cycle |
| Incremental aggregates vs. full recomputation | deviation 0, also after insert, upsert, update, delete |
| Learning reset via command line and GUI | successful, corpus and full-text search preserved |
| Admin GUI (all tabs, closing) and read-only GUI (search, answer, chat) | 0 errors |

---

## 7. Performance

| Measurement | Time per cycle |
|---|---|
| Production scale, before the optimizations | 22.5 s |
| Production scale, current version | 1.3 to 1.6 s |
| Small corpus (300 chunks), current version | 0.9 s |

Effective measures:
- schema check once per database connection instead of once per observed sentence
- continuously maintained sums for the evaluations of 5h and 5i (triggers) instead of recomputation over 0.9 million rows
- targeted indexes on frequently queried columns, expression indexes for the replay candidate selection in Phase 6a
- exactly one unique index per table column
- cached full-text searches for reading feedback, valid until the next import

---

## 8. Runtime Properties

- one process, one CPU core, no GPU
- SQLite in WAL mode, 60 s wait on locks
- deterministic phase order; randomness only in replay selection and noise, seeded per cycle
- every phase error is captured in the cycle result and evaluated by the diagnostics module

---

## 9. Known Limitations and Open Points

| Item | Effect | Assessment |
|---|---|---|
| With many unresolved gaps, exploration sits at Phase 5b's upper bound (0.75) | the system keeps searching broadly | observe; should drop as more gaps are resolved |
| Few gaps get closed (1 of 946 in the 200-cycle run) | resolution values and therefore dopamine stay low | observe |
| Neuromodulators sit at high noradrenaline / low serotonin | couplings operate permanently in the "alarm" range | observe whether this changes as more gaps are closed |
| New mechanisms have not yet run on the production database | long-term behavior on the full corpus is unknown | next step |
| Facts are observed sentences with the relation `observed_as` | no statements about content yet | intended in the tabula rasa approach |
| Relation elements are often single characters or word fragments early on | early relations and categories are noise | intended, improves with learned word boundaries |
| Unverified text contrasts are never resolved automatically | many open contrasts in the table | intended (repetition is not truth) |
| At most one graduation per cycle | limits learning speed | intended budget |
| The pace of maturation depends on the calibration value 1,000 stable hypotheses for half maturity | determines how long the system keeps its infant rhythm | observe on the production corpus and recalibrate if needed |
| A mature system graduates fewer hypotheses per cycle (fewer sleep cycles, one graduation per cycle) | consolidation per sleep cycle is unchanged | intended: the developmental share keeps consolidation high while little is known |
| Reading continues during sleep | sleep costs no reading time, so the length of sleep has no learning cost | biologically, sensory input is gated during sleep; open decision |
| In a run where every chunk is read only once, no relation hypotheses form (old and new code alike) | relational binding needs repeated co-occurrence | corpus property, not a sleep effect |
| `assets/Project-Structure.png` is missing from the project folder | the README image is not shown locally | open |
| `Audits/System_Audit_2026-09-28.md` | describes the state of 28 September 2026 | historical document |
