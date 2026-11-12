# BrainStem: Project and Function Status

**As of:** 12 November 2026, 09:49
**Scope:** code (`ki_system/`, `main.py`), production database `ki_memory.sqlite3`, test results from 12 November 2026

---

## 1. Summary

| Area | Status |
|---|---|
| Learning chain | 36 phases, all load without errors, chain top: Stage-B question-chunk feedback |
| Learning on all layers | active: sentences, word boundaries and relations consolidate and graduate |
| Self-correction | active and demonstrated: cue competition, revision, fact retraction, reconsolidation |
| Emergence of relations, categories, questions | active and productive |
| Neuromodulators | 12 neuromodulators active, 19 neuromodulated thresholds and budgets |
| System test | all 7 checks OK |
| Speed | about 1.3 to 1.6 s per cycle at production scale, about 0.9 s on a small corpus |
| Production database | 5.57 GB, integrity check OK; the new mechanisms have not yet run on it |

---

## 2. Code Status

- **Package:** `ki_system`, 59 Python modules, 19,022 lines including `main.py`
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
| 3 | Phase 5b | refines reading strategies from outcomes, persistent gaps and clusters; diversifies chunk selection | active, fixed control values (see 9) |
| 4 | Phase 5c | evaluates learning outcomes and clusters internal learning questions | active |
| 5 | Phase 5d | observation and strategy memory | active, partly fixed fallback values (see 9) |
| 6 | Stage-B Gap Detection | detects gaps: "stalled" (seen often, never consolidated) and "contested" (cue competition); habituation and dishabituation | active |
| 7 | Phase 5e | plans context expansions around gaps and raises the priority of neighbouring chunks | active |
| 8 | Phase 5f | measures the effectiveness of context windows and adapts them | active, fixed control values (see 9) |
| 9 | Phase 5g | selects context strategies and keeps the experiment memory | active, partly fixed fallback values (see 9) |
| 10 | Phase 5h | evaluates strategy experiments and learns from them (strategy memory) | active, fixed control values (see 9) |
| 11 | Phase 5i | diversifies strategies based on outcomes | active |
| 12 | Phase 6a | sleep replay and meta-plasticity; computes dopamine, serotonin, noradrenaline and acetylcholine from replay (phasic) and blends in the tonic target | active |
| 13 | Phase 6b | measures replay effectiveness, adjusts plasticity, critic gate | active |
| 14 | Phase 6c | keeps bias values across cycles, self-regulates meta-parameters | active |
| 15 | Phase 6d | saturation homeostasis (sliding threshold) and meta-metaplasticity | active |
| 16 | Phase 7a | adenosine: sleep pressure with gated discharge during sleep | active |
| 17 | Phase 7b | endocannabinoids: 2-AG as a fast brake, anandamide as a slow pull of saturated values back to mid-range | active |
| 18 | Phase 7b1 | wake-chain bridge: runs 6a to 7b in a fixed order | active |
| 19 | Phase 7c | adaptive boundaries, soft clipping at the edges, glutamate-GABA balance | active |
| 20 | Connection Accelerator | applies fast SQLite settings to every new connection | active |
| 21 | Phase 7d | slow-wave consolidation with prioritized replay (see 4.1) | active |
| 22 | Phase 7e | histamine: wakefulness, antagonist of adenosine | active |
| 23 | Phase 7f | orexin: reading endurance and curiosity | active |
| 24 | Phase 7g | BDNF: activity-dependent growth and consolidation | active |
| 25 | Phase 7cort | cortisol: stability watcher, Stage 2 (guarded soft regulator) | active, calm in operation |
| 26 | Cooperative Core | joint dynamics of the six core neuromodulators, sleep/wake control | active |
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

19 couplings; at the neutral value 0.5 each one yields exactly its calibrated base value.

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

### 4.5 Other modules

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
| `v8_outcome_aggregates.py` | trigger-maintained sums over the experiment outcomes for 5h and 5i | active |
| `fractional_control.py` | bounded error diffusion for discrete budgets (ontology) | active |
| `v8_cycle_diagnostics_release.py` | recursively evaluates cycle results for errors | active |
| `v8_sensory_deprivation.py`, `v8_deprivation_runner.py` | learning without new input, CSV log, drift report | active (GUI) |
| `v8_wal_maintenance_release.py` | maintenance of the write-ahead log | active |
| `reset_learning.py` | corpus-preserving learning reset, dry run, full backup, checks | active, tested |
| `systemtest.py` | system check on a copy of the database | active |
| `gui_app.py`, `user_gui.py` | admin GUI and read-only dialogue GUI | active, tested |

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

| Test | Result |
|---|---|
| System test on a copy of the production database | 7 of 7 checks OK |
| 150 cycles on a fresh DB with 300 real Wikipedia chunks | 0 errors, 0 hidden error states, integrity OK |
| of which graduations sentence / word boundary / relation | 35 / 15 / 35 |
| of which facts / relations / categories / questions | 33 / 12 / 11 / 117 |
| of which revisions without artificial trigger | 2 (no immediate re-graduation) |
| 10 and 20 cycles on a copy of the production database | 0 errors, 1.3 to 1.6 s per cycle |
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
| Phases 5f and 5h use fixed control values (learning rate, error weight, neuromodulator values) instead of the real neuromodulator state | strategy learning there is not neuromodulated | open, next step |
| Phases 5b, 5d and 5g query tables that are not created in the current system and then fall back to fixed values | parts of their evaluation are constant | open |
| Neuromodulators sit at high noradrenaline / low serotonin | couplings operate permanently in the "alarm" range | observe whether this changes as more gaps are closed |
| New mechanisms have not yet run on the production database | long-term behavior on the full corpus is unknown | next step |
| Facts are observed sentences with the relation `observed_as` | no statements about content yet | intended in the tabula rasa approach |
| Relation elements are often single characters or word fragments early on | early relations and categories are noise | intended, improves with learned word boundaries |
| Unverified text contrasts are never resolved automatically | many open contrasts in the table | intended (repetition is not truth) |
| At most one graduation per cycle | limits learning speed | intended budget |
| `assets/Project-Structure.png` is missing from the project folder | the README image is not shown locally | open |
| `Audits/System_Audit_2026-09-28.md` | describes the state of 28 September 2026 | historical document |
