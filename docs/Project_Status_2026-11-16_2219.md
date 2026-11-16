# BrainStem: Project and Function Status

**As of:** 16 November 2026, 22:19
**Cycle units:** All cycle counts are system cycles (one call of `AutonomousLoop.cycle()`, one pass through the whole phase chain). One autonomous-learning cycle in the GUI comprises 5 system cycles, so 1,000 cycles correspond to 200 GUI cycles. The GUI's drift tab counts system cycles.
**Scope:** code (`ki_system/`, `main.py`), production database `ki_memory.sqlite3`, test results from 12 and 13 November 2026, production run of 13 November 2026, packages A to D and C5 of the work plan

---

## 1. Summary

| Area | Status |
|---|---|
| Learning chain | 36 phases plus a log-retention maintenance step and the cycle transaction, all load without errors, chain top: cycle transaction (`v8_cycle_transaction`) |
| Learning on all layers | active: sentences, word boundaries and relations consolidate and graduate |
| Self-correction | active and demonstrated: cue competition, revision, fact retraction, reconsolidation |
| Emergence of relations, categories, questions | active and productive |
| Neuromodulators | 12 neuromodulators active, 22 neuromodulated thresholds, rates and budgets, strategy phases 5b to 5i use live control values; dopamine is a reward prediction error, noradrenaline includes surprise, noradrenaline, acetylcholine and serotonin drop during sleep |
| Plasticity, meta- and meta-meta-plasticity | fully active: replay effectiveness adjusts plasticity and biases, 16 meta parameters self-regulate with a homeostatic restoring force, no regulator saturates |
| Sleep and wake | one common trigger: a single sleep/wake switch with hysteresis; adenosine driven by encoding load; developmental sleep share: about two thirds sleep while immature, falling toward the adult rhythm (about 55 wake and 22 sleep cycles) as consolidated knowledge grows |
| System test | all 7 checks OK (also after packages A to D and C5) |
| Reproducibility | since 16 November 2026: two runs from the same state are identical in all tables including timestamps, also across a restart; a different run seed gives a replicate |
| Work plan packages A to D and C5 (13 November) | log retention and compaction, fewer writes, closure signal of experiments fixed (R1), replay effectiveness as cued-versus-uncued contrast (R5), exploration driven by learning progress, stable ontology; final 1,000-cycle run meets K1 to K9 |
| Production run | 5,000 cycles on the full corpus without exceptions or hidden errors; stable hypotheses 36 to 2,597, facts 36 to 819, relations 0 to 493; corpus fully read; no regulator at a boundary |
| Speed | computation about 2.4 s of CPU time per cycle on the current production state (2.76 s before the per-cycle reuse of lexical statistics), one commit per cycle; the wall time fluctuates between about 2 and 10 s with the storage pool |
| Production database | 8.09 GB after the second production run (5,000 cycles, 15 November 2026); size constant from cycle 1,750 on, 17.5 million old log rows removed by the retention; integrity check OK; every fact and relation traces back to its chunk |

---

## 2. Code Status

- **Package:** `ki_system`, 66 Python modules, 22,640 lines including `main.py`
- **Entry points:** `python main.py --gui` (admin GUI), `python main.py --user-gui` (read-only dialogue GUI)
- **System check:** `python -m ki_system.systemtest` (runs on a copy of the database)
- **One-time log compaction:** `python -m ki_system.compact_logs <db> [--cutoff-ts EPOCH] [--vacuum]`
- **Corpus-preserving learning reset:** GUI button or `python -m ki_system.reset_learning --apply`
- All modules compile without errors.

---

## 3. Learning Chain (execution order)

Each phase first calls the phase registered before it and then does its own work. The execution order therefore equals the registration order in `phase_registry.py`.

| No. | Phase | Function | Status |
|---|---|---|---|
| 1 | Context Observation | reads text chunks, splits them into sentences, creates or re-observes sentence hypotheses (evidence count, confidence) | active |
| 2 | Phase 0 Lexical | word boundaries from the unsegmented character stream via branching entropy | active |
| 3 | Phase 5b | refines reading strategies from outcomes, persistent gaps and clusters; clusters the real questions by gap type and role; diversifies chunk selection; acts back on the exploration and inhibition biases with a damped step; exploration rises when learning progress stalls and falls while learning succeeds | active, live control values, feedback active |
| 4 | Phase 5c | evaluates the question clusters from 5b (size, priority, resolved share) and penalizes unproductive reading targets | active |
| 5 | Phase 5d | observation and strategy memory from real metrics (experiment outcomes, closed gaps, graduations, open questions, control values) | active |
| 6 | Stage-B Gap Detection | detects gaps: "stalled" (seen often, never consolidated) and "contested" (cue competition); habituation and dishabituation; keeps every gap's resolution value current (closed = 1, otherwise 0) | active |
| 7 | Phase 5e | plans context expansions around gaps and raises the priority of neighbouring chunks | active |
| 8 | Phase 5f | measures the effectiveness of context windows and adapts them (window width depends on inhibition and exploration) | active, live control values |
| 9 | Phase 5g | selects context strategies and keeps the experiment memory | active, live control values |
| 10 | Phase 5h | evaluates strategy experiments and learns from them; stores the live control values and neuromodulators with every outcome; a closed gap gives the full closure gain; writes only changed evaluations | active, live control values |
| 11 | Phase 5i | diversifies strategies based on outcomes | active, live control values |
| 12 | Phase 6a | sleep replay and meta-plasticity; derives the learning state from representative recent windows, computes dopamine (reward prediction error), serotonin, noradrenaline (pressure and surprise) and acetylcholine, blends in the tonic target, applies the sleep tone and integrates the fresh biases into the shared bias state | active |
| 13 | Phase 6b | measures replay effectiveness as a cued-versus-uncued contrast of tagged traces (targeted memory reactivation), adjusts plasticity, critic gate; adjustments enter the persistent bias target | active |
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
| 28 | Stage-B Contradiction Detection | decides cue competitions from evidence; one-slot text alternatives are recorded as sentence frames, and only a specific, closed, cross-article frame with a stable side becomes an unverified contradiction | active |
| 29 | Stage-B Hypothesis Revision | reverts consolidated hypotheses that lost a competition, closes the gap | active |
| 30 | Stage-B Fact Promotion | graduated sentence and word-boundary hypotheses become facts; retraction on revision | active |
| 31 | Phase 0b Relational Binding | binds co-occurring elements (PMI, direction from position) | active |
| 32 | Stage-B Relation Promotion | graduated relation hypotheses become relations | active |
| 33 | Stage-B Ontology Cluster Observation | deterministic, warm-started Label Propagation over the relation graph, prototype anchor; counts sleep episodes per cluster; grace period of 60 cycles before a cluster dissolves | active |
| 34 | Stage-B Ontology Promotion | stable clusters with at least 3 members seen in at least 3 sleep episodes become ontology entries (membership) | active |
| 35 | Stage-B Question Promotion | persistent gaps become questions | active |
| 36 | Stage-B Question-Chunk Feedback | open questions steer reading (source chunk and full-text search); global decay batched every 10 cycles | active |
| + | Log Retention (maintenance) | keeps the raw experiment event logs of the last 1,000 cycles; prunes older rows during sleep with a row budget; lifetime summaries stay intact | active |
| + | Cycle Transaction (`v8_cycle_transaction`) | one durable commit per cycle: inside a cycle a commit of the Memory connection is a step boundary (savepoint), a rollback undoes the work since the last boundary; the cycle commits once at its end, also on an exception | active |

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
| `semantic_evidence.py` | surface evidence; sentence frames with fillers and sources (`semantic_text_frames`); unverified text contrasts only under the frame rules, never resolved automatically | active |
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

### 4.8 Neuromodulator signals and the plasticity chain

| Signal | Computation | Basis |
|---|---|---|
| Reward per cycle | 0.5 x outcome of new experiments + 0.3 x graduation + 0.2 x closed gap | |
| Dopamine (phasic) | 0.5 + 1.5 x reward prediction error; expectation learned per state (wake, sleep) with rate 0.1 | Schultz, Dayan & Montague 1997; Sutton & Barto 2018 |
| Tonic dopamine target, serotonin | long-run average reward (slow average, rate 0.02), consolidation, anchor stability | Niv et al. 2007 |
| Noradrenaline | persistent pressure plus surprise (absolute prediction error) plus overlap | Yu & Dayan 2005; Aston-Jones & Cohen 2005 |
| Persistent pressure | 0.5 x (1 - closure) + 0.3 x (1 - outcome) + 0.2 x overlap (weights sum to 1, no saturation) | |
| Learning progress (orexin, BDNF) | fast minus slow average of the reward | Oudeyer, Kaplan & Hafner 2007 |
| Sleep tone | noradrenaline x 0.3, acetylcholine x 0.4, serotonin x 0.5 | Yang & Eschenko 2025; Trulson & Jacobs 1979; Hasselmo & McGaughy 2004 |
| Shared bias state | fresh 6a values enter at rate 0.1 per cycle; 5b, 6b, 6d, 7a and 7b change it additively | |
| Meta parameters (6c) | steps relative to the range, restoring force 0.25 toward the default, 2-AG dampening factor | Turrigiano 2008 |
| Meta-meta-plasticity (6d) | learning rates of the meta parameters and of the five biases; the step away from a saturated boundary is made easier | Abraham & Bear 1996; Lee & Kirkwood 2019 |
| BDNF | lowers the survival threshold and strengthens reinforcement in slow-wave consolidation | Bramham & Messaoudi 2005 |
| Adaptive boundaries (7c) | ranges contract only while a parameter is actually regulated, never below half the calibrated width | |

The detailed report is `Audits/Neuromodulator_Plasticity_Fix_Calibration_2026-11-12_1722.md` (German).

---

## 5. Production Database

State after the production run of 13 November 2026 (5,000 cycles). On 14 November 2026 the event logs older than the last 1,000 cycles of the run were removed (about 27 million rows) and the file was compacted; learned content is unchanged.

| Metric | Value |
|---|---|
| File size | 5.82 GB after compaction (20.5 GB after the run, 5.57 GB before it) |
| Tables / indexes | 159 / 86 |
| Integrity check | OK |
| Documents / chunks | 2 / 167,661 |
| Chunks read since the last learning reset | 167,661 (100 %) |
| Learning cycles since the last learning reset | 6,947 |
| Hypotheses in total | 2,430,058 |
| of which sentence uncertain / stable | 1,590,914 / 819 |
| of which word boundary uncertain / stable | 829,109 / 553 |
| of which relation uncertain / stable | 7,438 / 1,225 |
| Facts / relations / categories | 819 / 493 / 4 |
| Questions open / resolved | 52 / 273 |
| Knowledge gaps open / habituated / closed | 950 / 146,921 / 101 |
| Experiment outcomes | 3,287,455 |
| Word-boundary statistics (transitions) | 846,782 |

**Neuromodulators (last state, sleep):** dopamine 0.58, serotonin 0.28, noradrenaline 0.18, acetylcholine 0.21, glutamate 0.64, GABA 0.46; cortisol Stage 2, regime "calm".

**Growth:** the experiment phases write several hundred event rows per cycle. Since 13 November 2026 the log retention keeps only the last 1,000 cycles of them, so the file grows by about 3 GB during the next 1,000 cycles and afterwards mainly with learned content.

**Compaction of 14 November 2026:** 27.0 million rows deleted in 843 s, VACUUM 232 s; lifetime summaries 3,287,455 observations before and after; facts 819, relations 493, ontology 4, stable hypotheses 2,597, chunks 167,661 before and after; all three summary triggers present.

**Traceability:** 30 facts from the first graduations of 23 and 24 September 2026 had no direct chunk reference (the promotion code of that time did not copy it); it was filled in from their source hypotheses. All 819 facts and 493 relations now point directly to an existing chunk.

Backups: before the run `A:\ClaudeCode\Brainstem_db_backup_20261113_vor_langzeitlauf`, after the run (before compaction) `A:\ClaudeCode\Brainstem_db_backup_20261113_nach_langzeitlauf`.

---

## 6. Test Results from 12 and 13 November 2026

### Faster lexical statistics, 16 November 2026

Details in `Audits/Beschleunigung_2026-11-16_2219.md` (German).

| Item | Result |
|---|---|
| Phase 0 | stored transition counts read once per cycle instead of once per chunk, decision once per context and chunk: 0.41 to 0.20 s per cycle |
| Cue competition | `learned_boundaries` keeps total and entropy per context for the cycle (invalidated when Phase 0 writes or on a rollback): 0.30 to 0.11 s |
| Reading queue | `seed_queue` skips the corpus scan once every chunk is queued (`reading_queue_seed_state`); partial index on pending rows: 0.05 s to below 0.001 s |
| Identical results | old and new code, 100 cycles from byte-identical copies: all 157 common tables identical |
| CPU time | 2.755 to 2.455 s per cycle, paired saving 0.30 s (95 % interval 0.26 to 0.34 s), 11 % |

### Reproducible learning, 16 November 2026

Details in `Audits/Reproduzierbarkeit_2026-11-16_2010.md` (German).

| Item | Result |
|---|---|
| Before | two 100-cycle runs from byte-identical copies differed in 101 of 156 tables (4,547 vs 4,541 stable hypotheses, 1,143 vs 1,140 facts): wall-clock seeds in phases 6b and 7d, an unseeded random call, decisions on wall-clock seconds, iteration over string sets |
| Advisory council | experience time (cycles) is the biologically better internal time (Jenkins & Dallenbach 1924; Wixted 2004; Howard & Kahana 2002; Tsao et al. 2018); seeded noise keeps its distribution (Faisal et al. 2008); counter-based seeds (Salmon et al. 2011); several run seeds for benchmarks (Henderson et al. 2018; Bouthillier et al. 2021) |
| Change | `learning_clock.py` (one tick per cycle, base one second after the newest timestamp), 35 phase modules and `semantic_evidence` read it, all random sources seeded, ties broken by id, string sets sorted; wall clock kept for GUI, import, logs, compaction and WAL maintenance |
| A/A test | different Python hash seeds and start times: all 157 tables identical, including timestamps |
| Restart test | 50 cycles, new process, 50 cycles equals 100 cycles in one process |
| Negative control | run seed 1 instead of 0 changes 96 tables |
| 1,000 cycles | all nine criteria met; stable hypotheses +323 (old code +319, frames +339), K5 0.899, 0 exceptions |

### Test run R8, 16 November 2026: sentence frames and one commit per cycle

Details in `Audits/Test_Run_R8_2026-11-16_1354.md` (German).

| Item | Result |
|---|---|
| Advisory council on text contrasts | aligned one-slot alternatives are frames with fillers, the evidence from which word classes form (Harris 1954, Mintz 2003, Gómez 2002), not contradictions; a contradiction only when one side is stable, the rarest shared word is specific (df at most sqrt(N)), the slot is closed (at most 3 fillers) and the sides come from different articles; one gap per frame, habituated when the slot opens, every change logged and reversible |
| Search | rarest cue terms only (prefix filtering), postings budget 2.5 % of the index, 64 best bm25 matches; 98.4 % of the specific pairs of the old method recovered offline |
| A/B over 1,000 cycles each on identical production copies | all nine criteria met in both; old code vs frames: stable hypotheses +319 vs +339, graduations 319 vs 339, K5 0.896 vs 0.898, questions 355 vs 355; unverified contradictions +27,032 vs 0; paired 50-cycle blocks: B minus A +1.0 per block, 95 % CI -1.4 to +3.4 (mean 16.0) |
| Frames | 50,742 frames from 319,469 pairs, 375 paradigmatic; top frames are citation templates; 1,728 old per-pair gaps reclassified and habituated (logged), backfill complete |
| One commit per cycle | 1 instead of about 74 commits; same CPU time; about 20 to 35 % fewer bytes written; wall time not measurably different on the storage pool |
| Verification with frames and bundling, 500 cycles | 0 exceptions, 0 diagnostic findings, K6 320, K7 0.011; K5 0.807, above old code (0.72 to 0.74) on windows of the same length; median 2.3 s per cycle |

### Test run R7, 16 November 2026

Details in `Audits/Test_Run_R7_2026-11-16_0830.md` (German).

| Item | Result |
|---|---|
| Partial gap indexes | of 276,246 gaps 274,623 are habituated; six partial indexes match the filters of phases 5e, 5f, 5g, 5i, 6a and gap detection exactly; eleven queries return identical results, 2.1 s to 0.03 s per cycle |
| Further indexes | covering index for the 5d averages and the 6a count, `contradictions(subject, relation)`; 5b and 5c skip the duplicate scan once the unique index exists |
| Calibration criteria | all nine met over 1,000 cycles, 0 exceptions, 0 diagnostic findings, K5 0.886 with the new window |
| Speed | process CPU time 2.6 s per cycle in fast and slow cycles alike (before about 5.1 s); wall time 2.4 s in 39 % of the cycles and 8.7 s in the rest, the difference is commit waiting on the storage pool |

### Test run R6, 16 November 2026

Advisory council of 15 November 2026 put into code; details in `Audits/Test_Run_R6_2026-11-16_0308.md` (German).

| Item | Result |
|---|---|
| Ontology from words | promotion only if the prototype and at least `min_promotion_size` members are word-level units (alphabetic, at least four letters, or confirmed lexical units); one promoted syllable cluster withdrawn with its own reason; no promotion since, ontology empty |
| Stable against stable | two consolidated sentences sharing a cue now coexist (status `coexisting`), revision skips a stable winner; no such case in 1,000 cycles, 59 revisions with an uncertain winner |
| Bug found and fixed | the ontology promotion failed in every cycle ("no such savepoint") because a schema check that commits ran inside the savepoint; the 200-cycle check after the fix had 0 exceptions and 0 diagnostic findings |
| Calibration criteria | K1 to K4 and K6 to K9 met after the fix; K5 lower only through censoring at the end of short runs |
| Speed | phase 5b 0.59 to 0.012 s, phase 5d 0.35 to 0.18 s, identical values |

### Second production run, 5,000 cycles (15 November, 06:45 to 13:57)

On the compacted production database with all changes of 14 November 2026 and full sensory gating in sleep; details in `Audits/Production_Run_2_2026-11-15_1357.md` (German).

| Metric | Result |
|---|---|
| Stability | 5,000 of 5,000 cycles, 0 exceptions, 0 hidden errors, integrity OK, no meta parameter at a boundary |
| Learning | stable hypotheses 2,597 to 4,505, facts 819 to 1,136, relations 493 to 1,067, capture 97.4 % |
| Database | 5.82 to 8.09 GB, constant from cycle 1,750; 17.5 million old log rows removed |
| Cycle time (median) | 2.7 s rising to 5.9 s |
| Ontology | 110 promoted, 112 retracted after the grace period (before: 1,013 and 1,010) |
| Replay cue effect | 463 cohorts, +0.028 (SE 0.088), no false alarms |
| Content-weighted maturity (shadow) | 0.081, against 0.82 for the item count |

### Work of 14 November 2026

| Item | Result |
|---|---|
| Replay effectiveness, version 2 | outcome is capture; one cohort per trace and horizon; flags only beyond 2.814 SE; plateau only with an equivalence test (council of three agents). 1,000-cycle run: K1 to K9 met, effect +0.135 (z 1.66), before -0.051 from censoring |
| Sensory gating in sleep | three-arm comparison after a learning reset and a pre-registered confirmation (two pairs, up to 3,000 cycles): full gating learns as much or slightly more with about 30 % less runtime; now the default |
| Content-weighted maturity | shadow mode in Phase 7a, not coupled to the sleep rhythm |
| Learning reset | was blocked by the summary triggers; fixed |
| Deprivation run, 1,500 cycles | verdict "konvergenz", all 21 signals stable or converging |
| GUI | learning, stop, CSV logger, drift tab and CSV viewer work on a copy of the compacted production database |

### Work plan packages A to D and C5 (13 November, 23:20)

Tests on copies of the production database; the production database is unchanged. Details in `Audits/Pakete_A-D_C5_2026-11-13_2320.md` (German).

| Item | Result |
|---|---|
| A: log retention, compaction | new maintenance step keeps 1,000 cycles of raw logs; compaction of a copy 20.5 GB to 5.8 GB, about 27 million rows removed, lifetime sums unchanged (3,287,455 observations), integrity OK, 24 min delete plus 5 min VACUUM |
| B: write load | 5h writes 479 instead of 1,200 evaluations per cycle; batched decay; new index on contradiction status; about 17,000 writes per cycle remain, mostly real learning |
| C1 / R1: closure signal | cause: 5h read a column that was never written; fixed, a closed gap gives the full closure gain (Schultz 1997); 24 % of evaluations now report closure (before 0 %) |
| C2 / R5: replay effectiveness | new measure: cued versus uncued tagged traces, stratified by strength, outcome read out 30 cycles later (targeted memory reactivation: Rudoy 2009, Rasch 2007, Hu 2020); 567 cohorts, effect -0.051 (SE 0.037, not significant); plateau signals 4 in 1,000 cycles instead of noise crossings in 335 of 6,947 cycles |
| C3: exploration | follows learning progress (Aston-Jones & Cohen 2005, Oudeyer 2007, Gottlieb 2013); moves between 0.54 and 0.81 instead of sitting at 0.75 |
| C5: ontology | deterministic warm-started Label Propagation, promotion after 3 sleep episodes (Gomez 2006, Friedrich 2015), grace period, minimum size 3; 10 clusters promoted and 1 retracted in 1,000 cycles (production run: about 203 and 202 per 1,000 cycles) |
| D: GUI on the 20 GB database | cold count queries took up to 5.8 s, index added; all dashboard queries at most 0.1 s on the compacted copy |
| Final run, 1,000 cycles | K1 to K9 met (graduations 633, capture 95.0 %, prediction error 0.008 / 0.000, no regulator at a boundary), 0 exceptions, 0 hidden errors, integrity OK; system test 7 of 7 OK |
| Not yet run | 1,500-cycle deprivation run against the stability reference; GUI steps D2 to D4 |

### Production run, 5,000 cycles (13 November, 06:17 to 19:00)

Learning run with input on the production database; details in `Audits/Production_Run_2026-11-13_1912.md` (German).

| Metric | Result |
|---|---|
| Stability | 5,000 of 5,000 cycles, 0 exceptions, 0 hidden errors, integrity OK |
| Learning | stable hypotheses 36 to 2,597, facts 36 to 819 (920 promoted, 101 retracted after lost competitions), relations 0 to 493, questions 213 to 325 (273 resolved) |
| Consolidation | 2,661 tagged traces, 2,629 captured (98.8 %) |
| Corpus | fully read from cycle 3,300; consolidation continues afterwards (+655 stable hypotheses) |
| Sleep | sleep share falls with maturity from 63 % to 45 %; wake episodes lengthen from 16 to 27 cycles, sleep episodes stay at 23 cycles |
| Neuromodulators | wake/sleep ratios constant over the run; orexin falls to 0.23 ("satiated") once the corpus is exhausted; BDNF stays at 0.63 ("growth") |
| Regulators | no meta parameter at a boundary in any cycle; 6d saturation homeostasis never needed; cortisol calm (mean 0.10) |
| Strategy | contrasts take 12 % of the strategy experiments (before 59 %) |
| Cycle time | rises from 3.5 s to about 11 s and stays there from cycle 2,000; cause: the commit of about 55 MB of scattered writes per cycle into a growing 20 GB file |
| Reviewed items R1 to R8 | R2, R3, R4, R6, R7, R8 settled; R1 (`closure_delta` of experiments still 0) and R5 (no measurable replay effect in 6b's window) remain open |

### Drift verdict on window means (13 November, 06:09)

| Test | Result |
|---|---|
| Runner self-test (`v8_deprivation_runner.py --selftest`) | 6 of 6 PASS, including two new cases: a resting signal with a late fluctuation and an oscillating signal without trend (both failed with the old first-vs-last verdict) |
| Stability reference re-evaluated | overall "konvergenz" unchanged; only noradrenaline (+0.054, maturation) and slow-wave survivors (better consolidation) reported, all other signals "stabil" |
| Habituation drift run re-evaluated | "DIVERGENZ-WARNUNG" before, "konvergenz" now; allostatic load "stabil" (0.114 to 0.112) |

### Calibration on learning runs with input (20:09)

Three runs with the current code and one control run with the code from before the neuromodulator fix, 1,000 cycles each with sensory input, each on its own fresh copy of the production database. The nine acceptance criteria were fixed before the runs (`Audits/learning_calibration_2026-11-12/criteria.md`).

| Test | Result |
|---|---|
| Acceptance criteria K1 to K9 | all met in all three runs; no recalibration needed |
| Reward prediction error, wake / sleep | +0.009 / 0.000 |
| Noradrenaline and acetylcholine, sleep relative to wake | 0.33 and 0.44 (control run: 0.99 and 0.99) |
| Graduations per 1,000 cycles | 634 ± 14 (control run 592) |
| Capture rate of tagged traces | 95 to 96 % (control run 84 %) |
| Meta parameters at a boundary, saturation interventions | 0 / 0 |
| Learning rate | standard deviation 0.04, range 0.45 to 0.85 (control run: frozen at 0.78) |
| Exceptions, hidden errors, integrity | 0 / 0 / ok |
| Cycle time | 1.55 s to 2.87 s over 1,000 cycles, equally in the control run (data growth, not the fix) |

The 1,500-cycle sensory-deprivation run is kept as a stability reference (`Audits/Stability_Reference_Drift_2026-11-12_1905.md`): verdict "konvergenz", no divergence, no regulator at a boundary. It serves as a regression check after changes, not as a calibration basis. Details: `Audits/Learning_Calibration_2026-11-12_2009.md` (German).

### Neuromodulators and plasticity after fix and calibration (17:22)

| Test | Result |
|---|---|
| 400 cycles on a fresh DB (12,000 chunks from the corpus backup) | 0 errors, integrity OK, 1.78 s per cycle |
| Dopamine | standard deviation 0.005 before, 0.162 now; range 0.12 to 0.93; wake 0.53, sleep 0.52 |
| Noradrenaline / acetylcholine / serotonin, wake vs. sleep | 0.61 / 0.22, 0.50 / 0.22, 0.50 / 0.27 (before: no difference) |
| Persistent pressure | 1.000 in every cycle before; now 0.64 to 0.93, falling with learning success |
| Learning rate | one frozen value before; now 0.51 to 0.85 |
| Plasticity adjustments (6b), critic snapshots, meta regulation events (6c) | 0 / 0 / 0 before; now 384 / 41 / 4,472 |
| Meta parameters at a boundary, saturation interventions (6d) | 0 / 0 |
| Response test (inject success and failure) | dopamine burst on unexpected reward, dip below baseline on omission, adapting response under sustained reward, deep dip on failure; noradrenaline rises with surprise |
| 80 cycles on a copy of the production database | 0 errors, 1.57 s per cycle, 61 graduations |
| End-to-end test with hidden-error scan, system test, admin GUI | 0 findings, 7 of 7 OK, 0 errors |

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
| Production scale, current version | about 1.0 s at the start of a run, about 1.25 s after 1,000 learning cycles (before the cycle-time fixes: 1.56 s rising to 2.89 s) |
| Small corpus (300 chunks), current version | 0.9 s |
| Production run, 20 GB database (13 November) | about 3.5 s at the start, about 11 s from cycle 2,000; computation about 2.7 s, commit about 10 s |
| Compacted copy (5.8 GB), alone on the pool, after packages A and B | median 2.49 s, mean 3.75 s (old code: 5.95 s / 5.14 s) |
| Final 1,000-cycle run, all packages | 2.5 s in the first 10 % to 5.5 s in the last 10 %; profile at the end: 6.4 s, of which commit 5.2 s and computation 1.2 s |

Effective measures:
- schema check once per database connection instead of once per observed sentence
- continuously maintained sums for the evaluations of 5h and 5i (triggers) instead of recomputation over 0.9 million rows
- targeted indexes on frequently queried columns, expression indexes for the replay candidate selection in Phase 6a
- exactly one unique index per table column
- cached full-text searches for reading feedback, valid until the next import
- missing surface corroboration of relations is remembered until the corpus changes instead of being searched again every cycle
- write-only back-propagation in 5h removed, 5g fills in only missing gap priorities, index-friendly query forms in 7d and 5d, no schema look-ups per experiment
- time-based habituation of gaps and a contrast search with the rarest words reduced the remaining growth to +0.22 s per 1,000 cycles; see `Audits/Cycle_Time_Investigation_2026-11-12_2121.md` and `Audits/Gap_Habituation_2026-11-12_2208.md` (German)
- retention of experiment event logs (last 1,000 cycles) and one-time compaction (20.5 GB to 5.8 GB); 5h writes only changed evaluations; batched global decay; see `Audits/Pakete_A-D_C5_2026-11-13_2320.md` (German)
- the commit on the storage pool (SSDs of different speed) dominates the cycle time and fluctuates between about 2.4 and 7 s without code changes; a larger page cache does not help

---

## 8. Runtime Properties

- one process, one CPU core, no GPU
- SQLite in WAL mode, 60 s wait on locks
- reproducible: learning reads a learning clock (one tick per cycle, `learning_clock.py`) instead of the wall clock, and every random choice comes from a generator seeded by run seed, cycle, phase and purpose; two runs from the same state end in the same state
- every phase error is captured in the cycle result and evaluated by the diagnostics module

---

## 9. Known Limitations and Open Points

| Item | Effect | Assessment |
|---|---|---|
| Cycle time still rises with the learned tables | since 16 November 2026: CPU time 2.6 s per cycle, one commit per cycle instead of about 74, about a fifth less written; a cycle still writes about 50 MB, and the wall time fluctuates with the storage pool | measure which tables and indexes cause the write load |
| Ontology on the production state | solved on 16 November 2026: categories form only from word-level units; syllable clusters are observed but never promoted; the ontology is now empty, which is the expected stage while no word unit is confirmed | watch once words emerge |
| Learning rate spread | 0.010 to 0.012 in the test runs of 16 November 2026, close to the K7 bound of 0.01 | watch |
| Capture rate (K5) is censored at the end of a run | solved on 16 November 2026: K5 counts only traces tagged at least 250 cycles before the end (capture takes a median of 62 cycles, 99th percentile 238); 0.886 in test run R7 | none |
| Write load on the storage pool | cycle time fluctuates between about 2 and 10 s; one commit per cycle did not change the wall time measurably | the pool cannot be changed at the moment; reduce the write volume itself |
| Replay effectiveness shows no measurable benefit of cued reactivation (slightly negative, not significant) | 6b adjusts plasticity only on weak evidence | possible censoring: cued traces graduate earlier and then stop surviving; next check: count graduation within the horizon as success |
| The maturity value counts stable hypotheses, which are mostly text fragments | the system leaves its infant rhythm earlier than its developmental stage suggests | couple maturity to the kind of learned content once sentence relations appear |
| Facts are observed text fragments with the relation `observed_as`; 27 % come from references | no statements about content yet | deferred: early developmental stage, the system is still learning words and sentence structure |
| Relations (`associated_with`) and categories often join single characters or syllables | early relations and categories are noise; categories are stable now, but still made of characters and syllables | deferred: improves with learned word boundaries |
| Unverified text contrasts are never resolved automatically | since 16 November 2026 they form only under the frame rules (36 frame gaps in 1,000 cycles instead of 27,032 per-pair gaps); the 274,644 old ones stay in the table, their gaps are habituated | intended (repetition is not truth); old rows reversible via `semantic_frame_gap_log` |
| At most one graduation per cycle | limits learning speed | intended budget |
| Reading continues during sleep | sleep costs no reading time | biologically, sensory input is gated during sleep; open decision |
| `Audits/System_Audit_2026-09-28.md` | describes the state of 28 September 2026 | historical document |
