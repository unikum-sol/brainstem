# BrainStem

Update 31.07.26

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](#current-development-and-testing-status)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](#running-the-system)
[![Backend: SQLite](https://img.shields.io/badge/backend-SQLite-lightgrey)](#database-initialization)
[![Roadmap: Stage A complete -> validating](https://img.shields.io/badge/roadmap-Stage%20A%20complete-green)](#current-development-and-testing-status)


BrainStem is a biologically inspired, Real Neuro-Symbolic (RNS-AI) cognitive architecture for lifelong learning. It is designed to learn models of the structures and dynamics of language and text through context hypotheses, uncertainty, contradiction, revision, neuromodulation, replay, and consolidation rather than by merely storing isolated facts.

>One CPU Core /
>No GPU

> [!IMPORTANT]
> BrainStem is a research and calibration system, not a production-ready assistant. Permanent fact, relation, and question writes remain locked while the learning core and its candidate flow are being validated.

---

[![BrainStem Project AI conversation](https://img.youtube.com/vi/4nN7zELSAMo/mqdefault.jpg)](https://www.youtube.com/watch?v=4nN7zELSAMo)

YouTube - BrainStem Project AI conversation 22.07.26

---

## 📍 Navigation

* [Core Philosophy](#core-philosophy)
* [What is BrainStem really](#what-is-brainstem-really)
* [Architecture](#architecture)
* [Running the System](#running-the-system)
* [ZIM Import](#zim-import)
* [Academic References](#Academic-References)
* [Development Notes](#development-notes)

    
---

[NotebookLM codebase exploration](https://notebooklm.google.com/notebook/22f86efd-8cd6-447b-a43f-65f252259ab4?utm_source=nlmm_share) 22.07.26

---

## Current State

### Project-Structure

<a href="assets/Project-Structure.png" target="_blank">
  <img src="assets/Project-Structure.png" alt="Project-Structure" width="250" />
</a>


### Current Validation Status

The current BrainStem source package contains 66 Python modules and represents the integrated cooperative neuromodulator and sleep/wake build as of 31 July 2026.

The current source package has completed the following checks:
- complete Base64 project extraction without decoding errors
- AST parsing and Python compilation across all 66 Python modules
- cooperative neuromodulator schema creation and schema self-check
- isolated SQLite execution of the six-core neuromodulator regulator
- before/after delta verification for all six core neuromodulators
- cooperative sleep-score calculation and state persistence
- phase-registry integration checks
- Stage-B wrapper-chain continuity checks
- Phase-7d cooperative sleep-entry integration checks
- GUI cooperative-state integration checks
- presence checks for Efraimidis-Spirakis weighted sampling and sigmoid soft clipping

The updated build is an integrated release candidate. It has not yet completed a new full live-database stability and drift validation after the cooperative neuromodulator and sleep/wake changes. The historical 1,344-cycle drift result applies only to the earlier state that was tested at that time.

The current build must therefore not be described as fully Stage-B validated until a new frozen-state validation completes successfully against the live database and exact current source fingerprints.

### Current Architecture

- BrainStem remains a phase-based, hypothesis-centered language and text understanding system.
- The Python package remains `ki_system`.
- The primary project path remains `Z:\Temp\Ki_System\BrainStem\`.
- `autonomous.py` remains the minimal autonomous loop kernel.
- `phase_registry.py` remains the central installer and ordering authority for the runtime phase chain.
- SQLite remains the canonical relational source.
- The learning mode remains `context_hypotheses_with_neuromodulators`.
- Legacy Cleanup large slices A through C remain incorporated.
- Obsolete NLP, CorpusReader / Phase-3d, and historical Phase-4def through Phase-4p paths remain removed.
- The Modern Gap Candidate Bridge remains checkpoint-based, bounded to at most 512 hypotheses per cycle, `observed_only`, shadow-only, and non-productive.
- Stage-B gap flow continues to distinguish real shadow-observed candidates from measured zero-source intervals without opening productive downstream writes.
- Guarded computational kernels and adapters continue to preserve wrapper-owned evidence, critic, transaction, logging, and persistence responsibilities.
- No unvalidated replacement of the canonical runtime kernel or relational data source is authorized.

### Runtime Phase Structure

The effective runtime architecture includes:
1. context observation and integrated hypothesis learning
2. strategy refinement, outcome closure, and observation memory
3. context expansion and effectiveness evaluation
4. strategy selection, experiment memory, and outcome learning
5. outcome-driven strategy diversification
6. Phase-6a offline replay and meta-plasticity
7. Phase-6b replay effectiveness evaluation
8. Phase-6c bias persistence and self-regulating meta-control
9. Phase-6d saturation homeostasis and meta-metaplasticity
10. Phase-7a adenosine homeostasis
11. Phase-7b endocannabinoid regulation
12. Phase-7b1 wake-chain bridging
13. Phase-7c adaptive boundaries, E/I balance, and sigmoid soft clipping
14. Phase-7d slow-wave sleep and down-selection
15. Phase-7e histamine wake/arousal regulation
16. Phase-7f orexin wake-endurance regulation
17. Phase-7g BDNF growth and consolidation regulation
18. Phase-7cort stability observation and guarded Cortisol Stage 2 regulation
19. cooperative six-core neuromodulator and sleep/wake authority
20. guarded Stage-B hypothesis graduation
21. non-productive shadow recheck runtime
22. Stage-B gapflow runtime contract

### Corpus and Learning State

The latest explicitly documented corpus baseline remains:
- 102,275 of 102,275 imported chunks read
- 949,760 context hypotheses recorded

These values are the latest documented baseline and are not presented as a new live recount.

Corpus completion does not stop autonomous learning. Replay, consolidation, hypothesis evaluation, neuromodulator regulation, sleep/wake transitions, and guarded Stage-B preparation can continue after all imported chunks have been read.

Replay activity alone does not prove replay-caused semantic improvement. Independent outcome evidence and real-user dialogue measurements remain necessary for semantic-effectiveness claims.

### Six-Core Neuromodulator State

The six core neuromodulators are:
- dopamine
- serotonin
- glutamate
- GABA
- noradrenaline
- acetylcholine

The current build adds a common canonical runtime authority for these six values in:

`v8_cooperative_core_neuromodulator_sleep_authority_release.py`

The regulator derives target values from existing BrainStem signals, including:
- observed learning outcome
- exploration bias
- consolidation bias
- inhibition bias
- revision bias
- persistent unresolved-gap pressure
- adenosine
- histamine
- orexin
- BDNF
- cortisol
- Phase-7c glutamate and GABA state

The final six-core values are written to:

`phase6a_neuromodulated_sleep_state`

This is also the canonical source read by the GUI.

The regulator does not introduce random fluctuations. Each value approaches its calculated target through bounded smoothing:

`new = old + 0.18 * (target - old)`

Core values are constrained to the interval from 0.05 to 0.95. A value may stabilize when its input signals and target stabilize. The intended behavior is responsive but bounded adaptation, not continuous artificial movement.

An isolated SQLite functional test produced measurable before/after changes in all six core values and confirmed that the regulator can update the canonical state without opening productive knowledge-write paths.

#### Extended Neuromodulator State

The extended neuromodulator and regulatory systems remain:
- adenosine
- endocannabinoids
- cortisol
- histamine
- orexin
- BDNF

All twelve intended systems are represented in code and runtime state and remain connected to the GUI.

Their current functional roles include:
- adenosine as homeostatic sleep pressure and downscaling input
- endocannabinoids as retrograde gain-control and stabilization signals
- cortisol as allostatic-load and stability regulation
- histamine as wake/arousal drive
- orexin as wake endurance and curiosity support
- BDNF as growth and consolidation readiness

### Cooperative Sleep/Wake Authority

The current build supplements the existing adenosine homeostat with a cooperative sleep/wake authority.

Adenosine remains an important sleep-pressure signal, but it is no longer the only available sleep-entry authority.

The cooperative sleep score combines:
- 35% adenosine pressure
- 25% release from wake and arousal drive
- 20% inhibitory readiness
- 12% consolidation readiness
- 8% absence of cortisol-related stress blocking

Wake and arousal drive includes:
- histamine
- orexin
- noradrenaline
- acetylcholine
- cortisol

Inhibitory readiness includes:
- Phase-7c GABA state
- inhibition bias
- reduced glutamate dominance

Consolidation readiness includes:
- consolidation bias
- BDNF
- serotonin

The cooperative state machine uses:
- sleep-entry threshold: 0.62
- wake-entry threshold: 0.42
- minimum dwell time: 3 cycles

The separate entry and exit thresholds provide hysteresis and reduce rapid state oscillation.

The canonical cooperative state is stored in:
- `cooperative_sleep_wake_state`
- `cooperative_sleep_wake_cycles`

Cycle-level provenance includes the previous and current state, transition reason, total sleep score, component scores, six-core values before regulation, calculated targets, and final values after regulation.

### Adenosine and Slow-Wave Sleep

The Phase-7a adenosine homeostat remains active and continues to provide:
- wake-related adenosine accumulation
- homeostatic sleep pressure
- sleep-related downscaling
- post-sleep recovery
- coordination with endocannabinoid regulation

Phase 7d now accepts either of two valid sleep-entry authorities:
- the existing Phase-7a adenosine homeostat
- the cooperative sleep/wake state

The Slow-Wave result records whether entry was authorized by `adenosine_homeostat` or `cooperative`.

The underlying Phase-7d slow-wave mechanism remains intact, including oscillations, candidate reactivation, adaptive thresholds, anchor interleaving, participation requirements, consistency-based survival, reinforcement, weakening, and GABA/glutamate-dependent selection pressure.

### Efraimidis-Spirakis Sampling

Efraimidis-Spirakis weighted sampling without replacement remains active in Phase 7d.

The algorithm continues to assign randomized weighted keys derived from candidate activity and selects the strongest keys for each slow-wave oscillation. The cooperative sleep/wake integration changes the admission authority for slow-wave processing but does not replace or modify the weighted sampling mechanism.

### Sigmoid Soft Clipping and E/I Balance

Phase 7c continues to provide:
- adaptive boundaries
- persistent glutamate/GABA E/I state
- sigmoid soft clipping
- bounded E/I regulation

The `_soft_clamp()` implementation, `sigmoid_softness` parameter, persistent state marker, and runtime flag remain present.

The cooperative six-core regulator consumes the Phase-7c glutamate and GABA state. It does not replace the Phase-7c E/I kernel.

### Histamine, Orexin, BDNF, and Cortisol

Phase 7e continues to calculate histamine from adenosine coupling, measured wake activity, and the previous smoothed histamine state. Histamine consumes the cooperative sleep/wake state when available and falls back to the Phase-7a mode before cooperative state initialization.

Phase 7f continues to calculate orexin from unread corpus fraction, marginal progress, and histamine. Orexin contributes to the cooperative arousal component.

Phase 7g continues to calculate BDNF from consolidation consistency, marginal progress, and activity. BDNF contributes to cooperative consolidation readiness.

Phase 7cort continues to calculate allostatic load and cortisol from threshold drift, survivor behavior, effectiveness, oscillation, and saturation. Guarded Stage-2 nudges remain constrained by stage, warm-up, load gates, cooldown, a per-value cap, a total cycle budget, savepoint protection, and postcondition checks.

### GUI State

The GUI continues to display all twelve neuromodulators.

The six core values are read from the same canonical state updated by the cooperative regulator:

`phase6a_neuromodulated_sleep_state`

The GUI first reads the cooperative sleep/wake state. If the cooperative state has not yet been initialized, the prior adenosine/histamine heuristic remains available as a startup fallback.

One visible autonomous GUI cycle contains five real backend cycles. The intended GUI contract includes:
- one outer autonomous-cycle heading
- five internal diagnostic evaluations
- progress based on completed backend subcycles
- visible progress from 0 through 20, 40, 60, 80, and 100 percent
- bounded log output
- main-thread widget updates through the GUI queue and pump

### Stage-B Functional State

The Stage-B implementation and guarded readiness contracts remain present:
- guarded Cortisol Stage 2 regulation
- observer and safety gates
- at least three survived Phase-7d consolidations before graduation eligibility
- `_critic_gate`
- warm-up damping
- an initial maximum budget of one graduation per cycle
- Facts promotion disabled

The cooperative neuromodulator and sleep/wake phase is positioned after the existing Cortisol phase and before guarded Stage-B graduation. The Stage-B wrapper chain explicitly includes the cooperative authority.

Because the cooperative authority changes the current runtime architecture, the exact updated build requires a new frozen-state live-database readiness, stability, and drift validation before final Stage-B readiness can be claimed.

### Current Safety Boundary

The following remain closed:
- productive `internal_learning_gaps` writes
- productive Attention writes
- productive Phase-5f experiments
- productive Phase-5g experiments
- productive Phase-5i experiments
- productive Phase-5g outcomes
- direct Facts writes
- direct Relations writes
- direct Questions writes
- Fact promotion
- unvalidated kernel runtime cutover
- replacement of SQLite as the canonical relational source

The cooperative authority writes only:
- the six canonical core-neuromodulator values
- cooperative sleep/wake state
- bounded sleep/wake cycle provenance

It does not write facts, relations, questions, attention entries, learning gaps, experiment outcomes, graduated facts, or promoted knowledge.

A vector database may only be evaluated at the dedicated architecture checkpoint after stable data identities, a concrete semantic retrieval use case, measurable requirements, and a read-only or shadow comparison against the SQLite baseline exist. It must not replace the canonical relational source or open productive gates.

### Schema and Bootstrap Discipline

The cooperative module defines all new columns in `SCHEMA_TABLES` and provides:
- idempotent `ensure_schema`
- `_self_check_schema`
- explicit state-table creation
- explicit cycle-table creation
- a cycle index
- validation before runtime state changes

Key/value reads continue to follow the repository contract:

`return dict(con.execute("SELECT key,value FROM " + table).fetchall())`

Any future schema change must be added to the central bootstrap at the same time as the runtime schema definition.

### Current Evidence Boundary

The current validation proves source extraction, compilation, local schema materialization, isolated six-core regulation, cooperative score calculation, state persistence, registry integration, wrapper-chain continuity, and preservation of the key safety boundaries in the tested package.

It does not yet prove:
- long-term stability against the live database
- a new drift baseline for the current build
- natural long-run sleep frequency
- repeated live cooperative Sleep entries and Wake exits
- semantic learning effectiveness
- replay-caused semantic improvement
- independent real-world outcomes
- real-user dialogue usefulness
- readiness for productive Fact promotion

A successful future long-duration validation will establish a runtime stability baseline only for the exact source and database state tested.

### Next Major Step

Treat the cooperative neuromodulator and sleep/wake build as the current integrated release candidate.

Before additional Stage-B changes, validate the exact current build against the live database and then freeze it for a new complete readiness, stability, and drift run. The validation should verify:
- database integrity
- schema and source fingerprints
- protected-table invariance
- six-core before/after behavior
- bounded and finite values for all twelve neuromodulators
- per-signal drift
- cooperative sleep score
- natural Sleep-entry and Wake-exit counts
- sleep and wake dwell lengths
- Stage-B graduation bounds
- absence of productive Fact promotion
- GUI/backend continuity during long-duration execution


## Core Philosophy

Traditional semantic systems often focus on the **what**: storing and retrieving content. BrainStem focuses on the **how**: learning how context, uncertainty, evidence, contradiction, revision, and consolidation interact over time.

A corpus is treated as training substrate rather than as a static knowledge base. The active learning architecture forms and revises context hypotheses, preserves errors as learning material, and delays permanent knowledge promotion until consolidation and safety gates are validated.

Core principles:

- **Learning before rules:** no fixed lexical blacklists or hand-authored word-role mappings in the active learning path.
- **Errors remain evidence:** unresolved and contradicted hypotheses remain available for later revision.
- **Consolidation before promotion:** permanent fact promotion stays closed until the staged write-gating design is validated.
- **Neuromodulation governs learning:** learning rate, error weighting, revision, confidence, exploration, inhibition, attention, stabilization, and consolidation are state-dependent.
- **Measure before changing:** diagnostics, audits, drift tests, and Shadow experiments precede active-control changes.
- **No hidden legacy paths:** obsolete modules and duplicate learning paths are removed rather than retained as inactive code.


## What is BrainStem really

**BrainStem** is an autonomous software architecture designed for continuous, self-improving data processing and knowledge management. At its core, the system operates through an Autonomous Loop that orchestrates a chain of learning phases to ingest, analyze, and refine information without manual intervention.

The biological terminology used throughout the project's technical documentation, including terms such as "neuromodulators," "sleep," or "homeostasis," is not decorative. These labels are functional designators for mathematical state variables and algorithmic control mechanisms. They describe real control functions, learning rates, error weightings, and consolidation thresholds, not simulated chemistry. The values are floats, not molecules. The behavior is biologically inspired, but the implementation is strictly mathematical.

**The system's primary mechanics include:**

**Dynamic Steering Variables:** The variables referred to as "digital messenger substances" are dynamic meta-parameters. These numerical equivalents, such as "dopamine" or "serotonin," adjust the system's learning rate, error weighting, and exploration strategies in real time.

**Active versus Offline Processing:** The system cycles between an active ingestion phase and an optimization phase. During active processing, the system extracts context hypotheses from new data inputs. During the optimization phase, referred to as "sleep," the system re-evaluates recorded hypotheses through batch replay and consolidation to improve overall accuracy and stability.

**Knowledge Distillation:** By comparing new data against existing stable records, the system filters out inconsistencies and promotes reliable information into its long-term memory structures.

**Equilibrium Control:** To prevent control variables from reaching unproductive extreme values, or saturation, the system uses stability monitoring routines. These routines act as a feedback mechanism that pulls meta-parameters back into a functional range when the system detects a performance plateau or excessive variance.

**Adaptive Boundaries:** The limits within which the system operates are not hardcoded but self-regulating. The software learns from its own performance metrics, referred to as L2M metrics, to expand or contract its processing thresholds based on the complexity of the data it encounters.

In summary, the project is a recursive learning engine that uses biologically derived control logic to implement a highly flexible, self-governing system for automated knowledge acquisition.

---

Every answer the system produces is retrieved from proof, not generated. Each fact in the knowledge base carries a complete provenance chain, from the final anchor back through its consolidation cycles, its originating hypotheses, and down to the exact source chunks and documents that justified its creation. There is no black box. If the system states something, it can show why it states it. Knowledge enters the system as raw observation, but it is never exposed to a user until it has passed through a multi-phase verification pipeline: hypothesis generation, strategic outcome testing, sleep-replay reinforcement, and guarded graduation. Only then does it become an anchor, a deductively usable fact. Until that point, it remains in the shadow layer, unable to influence any user-facing output. This creates a hard epistemic boundary. The system cannot hallucinate an answer it has not earned. When no verified anchor exists for a query, it does not invent a plausible response, and it reports the gap. The safety is architectural, not statistical. Trust is not placed in a model's weights, but in a transparent, auditable process that can be inspected, challenged, and verified, just like an engineering safety circuit.

---

## Architecture

---

<a href="assets/Autonomous_Learning_Architecture_Diagram.png" target="_blank">
  <img src="assets/Autonomous_Learning_Architecture_Diagram.png" alt="Project-Structure" width="250" />
</a>

---

BrainStem does not operate as a continuously coupled system of differential equations. Instead, it traverses a cyclic state graph: each phase activates at most 2–3 dominant neuromodulators, while the remainder are kept inactive or passive. This sequential architecture prevents interaction cascades and enables deterministic debugging.

---

### Two-Stage Data Pipeline

| Stage | Name | Description |
|---:|---|---|
| 1 | Inference-free pre-parsing | A raw corpus such as a Wikipedia ZIM file is extracted, structured, and partitioned into the chunk store before autonomous learning begins. |
| 2 | Autonomous learning | `AutonomousLoop` processes prepared chunks while the neuromodulatory and consolidation chain reacts to the evolving internal state. |

### Runtime Chain

Runtime phases are loaded through `ki_system/phase_registry.py`. The registry defines load order, isolates module-loading failures, and verifies the managed-cycle top phase.

Current chain, top to bottom:

`7cort Cortisol → 7g BDNF → 7f Orexin → 7e Histamine → 7d Slow-Wave → 7c E/I → 7b1 Wake-Chain Bridge → 7b Endocannabinoids → 7a Adenosine → 6d → 6c → 6b → 6a`

The cleaned chain uses Phase 7b1 as orchestrator so a normal global cycle produces one complete Phase-6a replay path, one Phase-7c E/I event, one Phase-7d cycle, and one workpoint-observer event.

## Digital Neuromodulator Cockpit

BrainStem currently uses **12 digital neuromodulators**. Their values are normalized to `[0.0, 1.0]` and derived from internal system state under bounded, biologically inspired dynamics and homeostatic constraints.

| Neuromodulator | Current engineering role |
|---|---|
| Dopamine | outcome and gap-closure signal |
| Serotonin | consolidation and stability signal |
| Glutamate | excitatory drive associated with exploration and learning activity |
| GABA | global inhibition and E/I-balance signal |
| Noradrenaline | error, alarm, and persistent-pressure signal |
| Acetylcholine | novelty, attention, and structural-revision signal |
| Adenosine | sleep-pressure homeostat |
| Endocannabinoids | retrograde gain control |
| Cortisol | top-level stability watcher and planned soft regulator |
| Histamine | wake and arousal signal |
| Orexin | reading-endurance and curiosity-related drive |
| BDNF | activity-dependent growth and consolidation substrate |

GABA currently regulates **system-level inhibition**. It does not identify or suppress individual words, relations, or extraction errors.

All 12 displays are connected both statically and at runtime in the GUI.

## Sleep, Consolidation, and Selection

### Sleep Replay and Critic Gate

Phase 6a performs offline-style replay after the wake path. Phase 6b evaluates replay effectiveness and plasticity adjustments. The critic gate checks whether proposed changes remain consistent enough to be retained; rejected or unstable material remains available as error and revision evidence.

### Slow-Wave Substructure

Phase 7d adds sub-1-Hz up/down-state processing with:

- stochastic reactivation
- adaptive thresholds
- activity-dependent participation
- survivor and weakening statistics
- anchor interleaving
- self-regulating down-selection

A passive Phase-7d workpoint observer records longitudinal E/I state, activity, survivor ratios, reference movement, and virtual adjustment proposals without applying them.

### E/I State Separation

The E/I path distinguishes:

- **Phase-6a drive:** `glutamate_drive` and `gaba_drive`
- **active Phase-7c state:** `glutamate_state` and `gaba_state`
- **compatibility mirror:** active values remain available to existing readers and GUI components
- **Shadow state:** non-applying recurrent candidates can be evaluated separately

This separation prevents Phase 6a from overwriting the active Phase-7c state on the next cycle.

## Stage B — Controlled Preparation

Stage B will not open all write capabilities at once. The controlled sequence is:

1. introduce Cortisol Stage 2 as a gentle regulator
2. validate it in observer operation before allowing applied control
3. allow only consolidation-gated graduation from `uncertain_hypothesis` to `stable_hypothesis`
4. require at least **three survived Phase-7d consolidations**
5. apply `_critic_gate`
6. use warm-up dampening
7. begin with a budget of **one promotion per cycle**
8. keep the facts table closed during the initial hypothesis-graduation stage
9. assess true fact promotion separately at a later milestone

Stage B remains blocked until the current Shadow bridge has demonstrably processed real candidates.

## Safety Locks

The following productive paths remain disabled:

- direct fact writes
- direct relation writes
- direct question writes
- permanent fact promotion
- direct Phase-5f / Phase-5g / Phase-5i experimental writes from the new bridge
- direct attention and internal-gap writes from the new bridge

The active architecture does not use word blacklists or hard-coded linguistic filters.

## Database and Schema Discipline

BrainStem uses `ki_memory.sqlite3` in the project root. The database is created automatically when absent.

Schema rules:

- schema changes must be reflected in the bootstrap in the same delivery
- `ensure_schema` must be idempotent
- `_self_check_schema` must run before writes
- every written column must already be declared in `SCHEMA_TABLES`
- compile checks, smoke tests, and intermediate checks are required before delivery
- structural changes require a full backup first

### Corpus-Preserving Learning Reset

Learning state can be reset without re-importing the corpus. Preserved content includes documents, chunks, FTS data, import state, and configuration. The reset workflow performs a dry run and creates a timestamped database backup before applying changes.

### Performance Maintenance

Performance indexes are ensured during bootstrap. Bounded pruning is limited to explicitly approved history tables. Active state, Phase-5f/5g/5i data, and other protected tables are excluded from generic pruning.

Periodic autonomous execution of the approved pruning routine remains an open maintenance item.

## Sensory Deprivation and Drift Report

The GUI includes a sensory-deprivation mode that skips new wake/read input while replay, consolidation, and neuromodulatory dynamics continue.

It provides:

- start and stop controls
- optional cycle limits
- per-cycle CSV diagnostics
- bounded/downsampled live graphs
- signal-level and overall drift verdicts
- fail-safe cleanup when the run completes or is interrupted

The completed **1,344-cycle** no-input test supported the Stage-A stability decision.

## Running the System

From the project root:

```cmd
python main.py --gui
```

### Basic Workflow

| Step | GUI action | Purpose |
|---:|---|---|
| 1 | Export / Configuration | Configure the maximum number of articles before import. |
| 2 | Import & Jobs → ZIM Einlesen | Extract and pre-parse the corpus. |
| 3 | Import & Jobs → Autonom dauerhaft starten | Start autonomous learning. |
| 4 | Import & Jobs → Autonom stoppen | Stop autonomous learning cooperatively. |
| 5 | Close the GUI normally | Wait for active workers instead of terminating them abruptly. |

### GUI Areas

- Import and Jobs
- Export and Configuration
- Drift Report
- live 12-neuromodulator display
- corpus-coverage and cycle-progress indicators
- bounded diagnostic logs and graphs
- cooperative worker shutdown

The GUI remains an experimental testing interface; individual areas may still be incomplete.

## ZIM Import

A Windows `zimdump.exe` build and its required DLL files must be placed in the project root next to `main.py`. Users must provide their own ZIM corpus.

The current development corpus is the German Wikipedia category **Computer**, imported into roughly 102,000 chunks.

## Academic References

This project builds upon concepts, algorithms, and theoretical frameworks established in the following academic literature:

1. **Hamilton, William L.** (2020)  
   *Graph Representation Learning*. Morgan & Claypool Publishers (McGill University).

2. **Watkins, Yijing; Kim, Edward; Kenyon, Garrett T.** (2020)  
   *Using Sinusoidally-Modulated Noise as a Surrogate for Slow-Wave Sleep to Accomplish Stable Unsupervised Dictionary Learning in a Spike-Based Sparse Coding Model*. Frontiers in Computational Neuroscience.

3. **Tadros, Timothy; Tran, Gia-Bao M.; Krishnan, Giri P.; Bazhenov, Maxim** (2022)  
   *Biologically Inspired Sleep Algorithm for Reducing Catastrophic Forgetting in Neural Networks*. eLife / bioRxiv.

4. **Fischbacher, Thomas; Comsa, Iulia M.; Potempa, Krzysztof; Firsching, Moritz; Versari, Luca; Alakuijala, Jyrki** (2020)  
   *Intelligent Matrix Exponentiation*. arXiv preprint arXiv:2008.03926.

5. **Butz, Markus; van Ooyen, Arjen** (2013)  
   *Homeostatic structural plasticity – a key to neuronal network formation and repair*. PLoS Computational Biology.

6. **Parker, Paul A.; Holan, Scott H.; Ravishanker, Nalini** (2020)  
   *Nonlinear Time Series Classification Using Bispectrum-based Deep Convolutional Neural Networks*. arXiv preprint arXiv:2003.02353.

7. **Rončević, Igor; et al.** (2023)  
   *Supplementary Materials for A molecule with half-Möbius topology*. Nature Chemistry.

<details>
<summary><b>Click to expand BibTeX citations</b></summary>

```bibtex
@book{hamilton2020graph,
  title={Graph Representation Learning},
  author={Hamilton, William L.},
  year={2020},
  publisher={Morgan \& Claypool Publishers}
}

@article{watkins2020using,
  title={Using Sinusoidally-Modulated Noise as a Surrogate for Slow-Wave Sleep to Accomplish Stable Unsupervised Dictionary Learning in a Spike-Based Sparse Coding Model},
  author={Watkins, Yijing and Kim, Edward and Kenyon, Garrett T.},
  journal={Frontiers in Computational Neuroscience},
  year={2020}
}

@article{tadros2022biologically,
  title={Biologically Inspired Sleep Algorithm for Reducing Catastrophic Forgetting in Neural Networks},
  author={Tadros, Timothy and Tran, Gia-Bao M. and Krishnan, Giri P. and Bazhenov, Maxim},
  year={2022}
}

@article{fischbacher2020intelligent,
  title={Intelligent Matrix Exponentiation},
  author={Fischbacher, Thomas and Comsa, Iulia M. and Potempa, Krzysztof and Firsching, Moritz and Versari, Luca and Alakuijala, Jyrki},
  journal={arXiv preprint arXiv:2008.03926},
  year={2020}
}

@article{butz2013homeostatic,
  title={Homeostatic structural plasticity--a key to neuronal network formation and repair},
  author={Butz, Markus and van Ooyen, Arjen},
  journal={PLoS Computational Biology},
  year={2013}
}

@article{parker2020nonlinear,
  title={Nonlinear Time Series Classification Using Bispectrum-based Deep Convolutional Neural Networks},
  author={Parker, Paul A. and Holan, Scott H. and Ravishanker, Nalini},
  journal={arXiv preprint arXiv:2003.02353},
  year={2020}
}

@article{roncevic2023molecule,
  title={Supplementary Materials for A molecule with half-M{\"o}bius topology},
  author={Ron{\v{c}}evi{\'c}, Igor and others},
  journal={Nature Chemistry},
  year={2023}
}
```
</details>


---

## Development Notes

- **Python package:** `ki_system`
- **Local project folder:** `BrainStem`
- **Primary runtime:** Python 3.11 on Windows with SQLite
- **Documentation language:** English, German
- **Status:** highly experimental and under mathematical and architectural validation
- **Engineering discipline:** backup, compile check, schema self-check, smoke test, and rollback planning for structural changes
- **AI-assisted engineering:** development has included collaborative AI assistance. Concept elaboration with ChatGPT, Code generation Claude Opus an ChatGPT 5.6 Depp Thinking, Code review NotebookLM, Gemini and Copilot as critics (no sugarcoat mode)


## Claims and Limitations

BrainStem does not claim that every current hypothesis is meaningful or that the system understands language at a human level. The current objective is to establish and validate the mechanisms by which hypotheses are formed, challenged, revised, inhibited, replayed, and consolidated.

Current zero-result Shadow measurements do not prove a defect and do not prove successful candidate processing. Candidate-flow evidence is the next required result.

## Disclaimer

BrainStem is an experimental cognitive-architecture research project. Biological terminology is used as an engineering analogy and design inspiration. The software is not a biological simulation and does not claim neuroscientific equivalence.
