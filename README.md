# BrainStem

Update 27.07.26

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](#current-development-and-testing-status)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](#running-the-system)
[![Backend: SQLite](https://img.shields.io/badge/backend-SQLite-lightgrey)](#database-initialization)
[![Roadmap: Stage A complete -> validating](https://img.shields.io/badge/roadmap-Stage%20A%20complete-green)](#current-development-and-testing-status)


BrainStem is a biologically inspired, Real Neuro-Symbolic (RNS-AI) cognitive architecture for lifelong learning. It is designed to learn models of the structures and dynamics of language and text through context hypotheses, uncertainty, contradiction, revision, neuromodulation, replay, and consolidation rather than by merely storing isolated facts.

>One CPU Core /
>No GPU needed

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

[Revibe codebase analysis](https://app.revibe.codes/shared/1WMamYip9Amived6mf-OF6OF0VNhcMWrekHg3c5bqkY)

---

## Current State

### Project-Structure

<a href="assets/Project-Structure.png" target="_blank">
  <img src="assets/Project-Structure.png" alt="Project-Structure" width="250" />
</a>

### Current Validation Status

The current repository and local database completed the bundled Stage-B Readiness Freeze validation with the verdict `STAGE_B_READY_FREEZE_PASS`, zero failures, and zero warnings. The validated scope included 66 Python files, AST and compile checks, central import smoke tests, registry consistency, empty-database bootstrap and bootstrap idempotence, SQLite integrity checks, protected-table invariance, source-file invariance, and the five included Stage-B and neuromodulator integration tests.

A new full 1,344-cycle stability and drift validation is currently running against this exact frozen Stage-B state. The run is bounded and records all twelve neuromodulator signals, sleep/wake state, hypothesis and graduation counts, and Phase-7a event counts. Its final checks include cycle completion, runtime errors, database integrity, schema and source fingerprints, protected production tables, bounded finite signal values, per-signal drift, sleep ratio, Sleep entries, Wake exits, and sleep/wake dwell lengths.

The running validation must not be described as passed until all requested cycles complete and the final report returns `VALIDATION_OK_STAGE_B_FROZEN_FULL_STABILITY_BASELINE_ESTABLISHED`.

### Current Architecture

- Legacy Cleanup large slices A through C are complete. Obsolete NLP, CorpusReader / Phase-3d, and historical Phase-4def through Phase-4p paths were removed.
- The canonical outer runtime owner remains Phase 7cort.
- SQLite remains the canonical relational source.
- The central phase registry currently contains 27 validated module entries without duplicates.
- The Modern Gap Candidate Bridge remains checkpoint-based, bounded to at most 512 hypotheses per cycle, `observed_only`, shadow-only, and non-productive.
- Stage-B gap flow distinguishes `real_candidates_observed_shadow_only` from `measured_zero_no_new_sources` without opening downstream productive writes.
- Guarded computational kernels and adapters preserve wrapper-owned evidence, critic, transaction, logging, and persistence responsibilities. No unvalidated kernel runtime cutover is authorized.

### Corpus and Learning State

The latest explicitly documented corpus baseline remains:

- 102,275 of 102,275 imported chunks read
- 949,760 context hypotheses recorded

These are the latest documented values and are not a new live recount from the running validation. Replay, consolidation, and the extended neuromodulator phases can continue after corpus completion. Replay activity does not yet prove replay-caused semantic improvement or independent outcome-based effectiveness.

### Stage-B Functional State

The Stage-B implementation and readiness contracts are present and test-validated:

- guarded Cortisol Stage 2 regulation
- observer and safety gates
- at least three survived 7d consolidations before graduation eligibility
- `_critic_gate`
- warm-up damping
- an initial maximum budget of one graduation per cycle
- Facts promotion disabled
- productive protected tables unchanged during the readiness suite

The C/D integration test demonstrated warm-up blocking and bounded graduation behavior. The E/F integration test demonstrated both real shadow-only candidate observation and a correctly classified measured zero-source interval.

Stage B is therefore readiness-complete for the frozen pre-validation state. Full frozen-state runtime stability remains pending until the active 1,344-cycle validation finishes successfully.

### Neuromodulator and Sleep/Wake Status

All twelve intended neuromodulator systems are represented in code and runtime state: dopamine, serotonin, glutamate, GABA, noradrenaline, acetylcholine, adenosine, endocannabinoids, cortisol, histamine, orexin, and BDNF.

The all-neuromodulator cooperation test passed without opening Fact promotion. The targeted Phase-7a gated sleep-discharge test used 40 deliberately constructed cycles, including 20 simulated sleep cycles. That 50 percent test ratio is path coverage, not evidence of BrainStem's natural sleep frequency.

The running full validation measures natural sleep ratio, Sleep-entry and Wake-exit counts, minimum and mean sleep and wake dwell lengths, state runs of one or two cycles, and adenosine range and drift. No final claim about long-term adenosine stability or natural sleep frequency is made before that validation completes.

### Current Safety Boundary

The following remain closed:

- productive `internal_learning_gaps` writes
- productive Attention writes
- productive Phase-5f, Phase-5g, and Phase-5i experiments
- Phase-5g outcomes
- direct Facts, Relations, and Questions writes
- Fact promotion
- unvalidated kernel runtime cutover
- replacement of SQLite as the canonical relational source

The Stage-B readiness validation observed zero rows in all checked protected production areas before and after execution.

A vector database may only be evaluated at the dedicated architecture checkpoint after stable identities, a concrete semantic retrieval use case, measurable requirements, and a read-only or shadow comparison against the SQLite baseline exist. It must not replace the canonical relational source or open productive gates.

### Current Evidence Boundary

The successful Stage-B readiness result proves code, schema, bootstrap, registry, safety-gate, and included integration-test consistency for the frozen state. It does not prove semantic learning effectiveness, independent real outcomes, permanent freedom from drift, real-user dialogue usefulness, or readiness for productive Fact promotion.

Even a successful 1,344-cycle validation will establish a runtime stability baseline only for the exact tested state.

### Next Major Step

Keep the repository frozen until the active 1,344-cycle stability and drift validation completes. Then evaluate the final verdict, protected-table invariance, schema and source hashes, per-modulator drift, adenosine behavior, natural sleep ratio, Sleep/Wake transition counts, and dwell-duration metrics before authorizing any further Stage-B change.


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


## Architecture

---

<a href="assets/Autonomous_Learning_Architecture_Diagram.png" target="_blank">
  <img src="assets/Autonomous_Learning_Architecture_Diagram.png" alt="Project-Structure" width="250" />
</a>

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
