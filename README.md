# BrainStem

Update 22.07.26

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](#current-development-and-testing-status)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](#running-the-system)
[![Backend: SQLite](https://img.shields.io/badge/backend-SQLite-lightgrey)](#database-initialization)
[![Roadmap: Stage A complete -> validating](https://img.shields.io/badge/roadmap-Stage%20A%20complete-green)](#current-development-and-testing-status)


BrainStem is a biologically inspired, neuro-symbolic cognitive architecture for lifelong learning. It is designed to learn models of the structures and dynamics of language and text through context hypotheses, uncertainty, contradiction, revision, neuromodulation, replay, and consolidation rather than by merely storing isolated facts.

>One CPU Core /
>No GPU needed

[![BrainStem Project AI conversation](https://img.youtube.com/vi/4nN7zELSAMo/mqdefault.jpg)](https://www.youtube.com/watch?v=4nN7zELSAMo)

YouTube - BrainStem Project AI conversation 22.07.26

<br>
---
## 📍 Navigation

* [Core Philosophy](#core-philosophy)
* [What is BrainStem really](#what-is-brainstem-really)
* [Architecture](#architecture)
* [Running the System](#running-the-system)
* [ZIM Import](#zim-import)
* [Development Notes](#development-notes)    
---
<br>

[NotebookLM codebase exploration](https://notebooklm.google.com/notebook/22f86efd-8cd6-447b-a43f-65f252259ab4?utm_source=nlmm_share) 22.07.26

[Revibe codebase analysis](https://app.revibe.codes/shared/1WMamYip9Amived6mf-OF6OF0VNhcMWrekHg3c5bqkY)

> [!IMPORTANT]
> BrainStem is a research and calibration system, not a production-ready assistant. Permanent fact, relation, and question writes remain locked while the learning core and its candidate flow are being validated.

## Current State

### Project-Structure

<a href="assets/Project-Structure.png" target="_blank">
  <img src="assets/Project-Structure.png" alt="Project-Structure" width="250" />
</a>

### Current Validation Status

BrainStem has completed the original Stage A foundation work and the Legacy Cleanup large slices A–C. Historical and unused learning paths were removed, including the obsolete `nlp.py` path, the legacy CorpusReader / Phase-3d word-role and filter path, and the historical Phase-4def–4p cluster. The current runtime uses the canonical Phase-7cort top path.

Important validation boundary:

- The historical 1,344-cycle drift and convergence validation applied only to the system state tested at that time.
- Major architectural changes were installed after that run.
- The current system must therefore complete a new full stability and drift validation before Stage B can be treated as ready.
- The earlier 1,344-cycle result remains historical evidence, not a current stability certificate.

Additional completed foundation work includes:

- centralized bootstrap and schema-contract consolidation
- idempotent schema setup and schema self-check contracts
- all 12 digital neuromodulators statically and at runtime connected to the GUI
- performance indexes for active learning-history tables
- bounded pruning only for explicitly approved history tables
- bounded and downsampled GUI diagnostics and graphs
- cooperative GUI worker shutdown logic, although long GUI runs can still become unresponsive while the autonomous worker continues
- modernized learning reset validated against the current database in read-only dry-run mode

### Current Corpus and Learning State

The current database contains:

- 102,275 of 102,275 chunks read by the GUI, representing 100% of the imported corpus
- 949,760 context hypotheses
- Candidate Bridge checkpoint at hypothesis 949,760
- Phase-5f Shadow Observation checkpoint at hypothesis 949,760
- no context-hypothesis or Candidate Shadow rows currently beyond the active observation checkpoint

The GUI chunk counter is the canonical corpus-read progress indicator. Counts of distinct `context_hypotheses.chunk_id` values are treated only as hypothesis-coverage proxies and not as an exact processed-chunk counter.

### Modern Gap Candidate and Observation Shadow Path

The Modern Gap Candidate Bridge and non-productive Phase-5f Shadow Observation path remain installed in the untouched canonical runtime.

Current restrictions:

- mode: `observed_only`
- automatic execution from Phase 5a
- checkpoint-based source selection
- maximum batch: 512 hypotheses per cycle
- canonical outer runtime owner: Phase 7cort
- no direct productive writes to `internal_learning_gaps`, attention targets, Phase-5f / Phase-5g / Phase-5i experiments, facts, relations or questions
- `observation_ready` remains false
- no direct fact promotion

Both Candidate and Observation frontiers reached the full current hypothesis population. Initial Shadow Observation generation completed without projection errors. The original V1 observation identity mixed stable identity with `source_updated_at`, causing repeated observations of the same hypothesis to appear as new keys instead of versions of one stable identity.

### Stable Observation Identity V2 Shadow

Stable Observation Identity V2 is installed as a parallel, non-productive dual-write path.

V2 contract:

- stable identity: `shadow_key + hypothesis_id`
- source version and projection version stored separately
- existing V1 writer preserved
- no backfill
- no migration
- no reader switch
- no V1 deletion
- no checkpoint reset
- all outcome and productive gates remain closed

The first production parity cycle proved exact V1/V2 input parity. During the subsequent natural long run, V2 recorded:

- 629,469 stable latest-state rows
- 766,459 history rows
- 28,166 stable keys with multiple versions
- 136,990 `source_state_change` versions
- zero input-parity failures
- zero duplicate fingerprint groups
- zero broken previous-version links
- zero gate violations

A dedicated driver audit proved that all 136,990 recorded source-state changes were caused only by `source_updated_at`. The stored source content and the projection fingerprint remained unchanged. This established that the timestamp-sensitive V2 source fingerprint was technically consistent but too sensitive for semantic versioning.

### Content-Stable Fingerprint Shadow Classifier

A parallel Content-Stable Fingerprint Shadow Classifier is installed without changing the existing V2 writer.

Contract:

- `source_updated_at` remains as provenance and checkpoint information
- `source_updated_at` is excluded from the content-stable source fingerprint
- same content plus a new timestamp is classified as `same_content_new_timestamp`
- real content changes and projection changes remain separate classifications
- no backfill
- no migration
- no writer switch
- no productive writes

The Classifier currently has no production events because the normal Observation checkpoint is fully caught up and no new `context_hypotheses` or Candidate Shadow source row exists beyond it. Fifty additional system cycles were verified as zero-input cycles for this path.

### Phase-6a Replay-Control Shadow Capture

Post-corpus replay activity continues after all corpus chunks have been read. Phase 6a creates replay candidates and replay events, but its existing `context_hypotheses` update writes only replay-control and replay-provenance fields. It does not update semantic hypothesis fields and does not update the canonical `context_hypotheses.updated_at` field.

A future-only, `context_hypotheses`-scoped Replay-Control Shadow Capture is installed.

Contract:

- stable identity: `source_table + source_id`
- scope: `context_hypotheses` only
- retry identity: immutable `phase6a_sleep_replay_events.id`
- canonical recursive JSON normalization for neuromodulator profiles
- no backfill of historical replay events
- no Candidate Bridge call
- no Observation Layer call
- no checkpoint change
- no semantic hypothesis version
- no productive write

After correction of the installer hook to use the actual SQLite connection receiver `db`, the natural production test recorded exactly:

- 300 new Phase-6a replay events
- 300 Replay-Control Shadow events
- 60 stable Replay-Control identities
- 60 `initial_replay_control_state` events
- 240 `same_control_state_new_replay_event` events
- zero `replay_control_state_change_candidate` events

Each of the 60 observed hypotheses received five replay events, with one initial state and four stable refreshes. This proves natural runtime reachability, exact event parity, retry-safe identity and stable replay-control classification. It does not prove semantic learning.

### Replay Learning Effect and Real-Outcome Status

Current evidence shows:

- all measured replay events have matching replay candidates
- Phase 6a updates replay priority, replay weight, meta-plasticity, replay count, last replay time and replay reason
- Phase 6a does not write semantic hypothesis content, confidence, uncertainty, evidence count, stability or canonical `updated_at`
- `hypothesis_learning_updates`, feedback, error, revision and self-evaluation tables are currently empty
- stability and consolidation data exist, but no direct replay-event causal key links replay events to those records
- replay-caused semantic learning is not proven
- replay effectiveness is not proven

Phase 6a currently computes `outcome_observation_available` from the global row count of `phase5g_experiment_outcomes`. It does not join by replay event, hypothesis identity or post-replay observation time. The table is currently empty, so all recorded Phase-6a cycles report no available outcome observation.

### Phase-5g Strategy Experiment and Outcome Status

The current legacy Phase-5g experiment producer exists in `v8_phase5g_context_strategy_selection_and_experiment_memory_release.py`, but it relies on `internal_learning_gaps` as its primary source. `internal_learning_gaps` remains intentionally empty and productively closed.

The producer is not statically connected to the current Registry or canonical Phase-7cort cycle. If activated, it would write operationally to Phase-5g experiments, reading queue, attention and gap-related structures. It is therefore not a safe read-only bridge for the modern Shadow architecture.

The Phase-5h outcome writer exists and can evaluate Phase-5g strategy experiments, but:

- `phase5g_strategy_experiments` is empty
- `phase5g_experiment_outcomes` is empty
- the writer evaluates internal strategy metrics
- the schema has no explicit external real-outcome observation contract
- no hypothesis-specific or replay-specific real-outcome lineage is present

The current Phase-5g and Phase-5h path is an internal strategy-projection and evaluation path, not a proven independent real-outcome path.

### Modern Non-Productive Phase-5g Candidate Contract

A read-only preflight proved that V2 Stable Observations contain all fields required for a future-only, non-productive Phase-5g Candidate contract.

The proposed contract would:

- use `stable_observation_key + projection fingerprint` as candidate identity
- classify initial candidates, identical retries, same-projection refreshes and projection changes
- avoid numeric eligibility thresholds
- keep `internal_learning_gaps`, reading queue and attention writes closed
- keep Phase-5g experiment and outcome writes closed
- make no Real Outcome claim

No installer has been authorized. The live V2 projection population currently shows almost no strategy diversity:

- `projected_action = increase_window` across the measured population
- `projected_window_strategy = wider_context_window` across the measured population
- expected gain, projected effectiveness, closure, overlap and no-candidate metrics are uniform in the current snapshot
- target count is six for all but one measured Stable Observation

The next pending read-only audit is the Modern V2 Projection Input Variance, Formula Drivers & Strategy Diversity Audit. It has been prepared but not yet executed.

### GUI Runtime Observation

During long autonomous runs, the GUI became unresponsive while the autonomous worker continued progressing. The worker was later stopped with `taskkill`, and SQLite `quick_check` and `integrity_check` both remained successful.

The GUI became responsive again after restarting with the same large database. Therefore:

- the earlier GUI freeze must not be attributed to database size without separate evidence
- database size is not an optimization trigger
- sufficient storage space is available
- no pruning, retention or history deletion is justified solely by database size

### Current Safety Boundary

The following remain closed:

- `internal_learning_gaps` productive writes
- attention writes
- productive Phase-5f experiments
- productive Phase-5g experiments and outcomes
- Phase-5i experiments
- `observation_ready`
- facts
- relations
- questions
- fact promotion
- reader switch to V2
- historical migration or backfill

### Immediate Next Steps

1. Run the prepared read-only Modern V2 Projection Input Variance, Formula Drivers & Strategy Diversity Audit.
2. Determine whether projection uniformity comes from constant inputs, default paths or a formula branch that collapses real source variance.
3. Do not install a modern Phase-5g Candidate writer until natural projection diversity or a justified projection-change contract is demonstrated.
4. Keep the Replay-Control Shadow Capture installed and continue treating its events as activity and control-state observations, not semantic learning.
5. Keep all productive gates closed until an independent, hypothesis-specific and temporally valid Real Outcome contract exists.
6. Perform a new full stability and drift validation of the current system before Stage B preparation.

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

It is important to understand that the biological terminology used throughout the project’s technical documentation, such as "neuromodulators," "sleep," or "homeostasis" serves as a set of metaphors to describe the underlying digital functions. These biological terms are mapped to mathematical variables and algorithmic states that steer the system's behavior.

#### **The system’s primary mechanics include:**

**Dynamic Steering Variables:** What the documentation calls "digital messenger substances" are actually dynamic meta-parameters. These variables, such as "dopamine" or "serotonin" equivalents, represent numerical values that adjust the system's learning rate, error weighting, and exploration strategies in real-time.

**Active vs. Offline Processing:** The system cycles between an active ingestion phase and an optimization phase. During active processing, the system extracts "context hypotheses" from new data inputs. During the optimization phase (metaphorically called "sleep"), the system re-evaluates these recorded hypotheses through batch replay and consolidation to improve overall accuracy and stability.

**Knowledge Distillation:** By comparing new data against existing stable records, the system filters out inconsistencies and promotes reliable information into its long-term memory structures.

**Equilibrium Control:** To prevent the control variables from reaching unproductive extreme values (saturation), the system uses stability monitoring routines. These routines act as a feedback mechanism that pulls meta-parameters back into a functional range when the system detects a performance plateau or excessive variance.

**Adaptive Boundaries:** The limits within which the system operates are not hardcoded but self-regulating. The software learns from its own performance metrics (L2M metrics) to expand or contract its processing thresholds based on the complexity of the data it encounters.

In summary, the project is a recursive learning engine that uses bio-inspired metaphors to implement a highly flexible, self-governing control logic for automated knowledge acquisition.


## Architecture

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

## Development Notes

- **Python package:** `ki_system`
- **Local project folder:** `BrainStem`
- **Primary runtime:** Python 3.11 on Windows with SQLite
- **Documentation language:** English, German
- **Status:** highly experimental and under mathematical and architectural validation
- **Engineering discipline:** backup, compile check, schema self-check, smoke test, and rollback planning for structural changes
- **AI-assisted engineering:** development has included collaborative AI assistance. Concept elaboration with ChatGPT, Code generation Claude Opus an ChatGPT 5.6 Depp Thinking, Code review NotebookLM, Gemini and Copilot as critics (no sugarcoat mode)

After major refactorings, project documentation includes a Legacy Report with:

- removed legacy elements
- retained but explicitly marked elements

## Claims and Limitations

BrainStem does not claim that every current hypothesis is meaningful or that the system understands language at a human level. The current objective is to establish and validate the mechanisms by which hypotheses are formed, challenged, revised, inhibited, replayed, and consolidated.

Current zero-result Shadow measurements do not prove a defect and do not prove successful candidate processing. Candidate-flow evidence is the next required result.

## Disclaimer

BrainStem is an experimental cognitive-architecture research project. Biological terminology is used as an engineering analogy and design inspiration. The software is not a biological simulation and does not claim neuroscientific equivalence.
