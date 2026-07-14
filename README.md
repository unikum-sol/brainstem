# BrainStem

update 13.07.2026

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](#current-development-and-testing-status)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](#running-the-system)
[![Backend: SQLite](https://img.shields.io/badge/backend-SQLite-lightgrey)](#database-initialization)
[![Roadmap: Stage A complete](https://img.shields.io/badge/roadmap-Stage%20A%20complete-green)](#current-development-and-testing-status)

A biologically inspired, neuro-symbolic cognitive architecture for lifelong learning.

BrainStem is an autonomous experimental system designed to learn models of the structures and dynamics of language and text rather than merely storing isolated facts. Digital neuromodulators regulate hypothesis formation, uncertainty, revision, exploration, inhibition, memory consolidation, sleep pressure, and system stability over an SQLite backend.

[Open the code export in NotebookLM for review](https://notebooklm.google.com/notebook/22f86efd-8cd6-447b-a43f-65f252259ab4?utm_source=nlmm_share)

> [!IMPORTANT]
> BrainStem is a research and calibration system, not a production-ready assistant. Permanent fact, relation, and question writes remain locked while the learning core is being validated.

## Core Philosophy

Traditional semantic systems often focus on the **what**: storing and retrieving content. BrainStem focuses on the **how**: learning how context, uncertainty, evidence, contradiction, revision, and consolidation interact over time.

A corpus is treated as training substrate rather than as a static knowledge base. The current learning path creates and revises context hypotheses, preserves errors as learning material, and delays permanent knowledge promotion until consolidation and safety gates are ready.

Core principles:

- **Learning before rules:** fixed lexical blacklists and hand-authored word-role mappings are not part of the active learning path.
- **Errors remain evidence:** unresolved and contradicted hypotheses stay available for later revision.
- **Consolidation before promotion:** permanent fact promotion remains closed until the staged write-gating design is validated.
- **Neuromodulation governs the whole process:** learning rate, confidence, error weighting, exploration, inhibition, revision, attention, stabilization, and consolidation are state-dependent.
- **Measure before changing:** long runs, drift tests, call-stack audits, database diagnostics, and shadow-mode experiments precede active control changes.

## Overview

BrainStem Test Version 8 operates as a layered autonomous cycle over a relational SQLite database. The current system uses **12 digital neuromodulators**:

1. Dopamine
2. Serotonin
3. Glutamate
4. GABA
5. Noradrenaline
6. Acetylcholine
7. Adenosine
8. Endocannabinoids
9. Cortisol
10. Histamine
11. Orexin
12. BDNF

The system pre-parses a text corpus into chunks before autonomous learning begins. During learning, it forms context hypotheses, tracks uncertainty and outcomes, revisits unresolved material, performs sleep replay, and applies slow-wave down-selection. Permanent facts and relations are intentionally not generated during the current calibration stage.

## Architecture

### Two-Stage Data Pipeline

| Stage | Name | Description |
|---|---|---|
| 1 | Inference-Free Pre-Parsing | A raw corpus such as a Wikipedia ZIM file is extracted, structured, and partitioned into the chunk store before learning begins. |
| 2 | Autonomous Learning | `AutonomousLoop` processes prepared chunks while the neuromodulatory and consolidation chain reacts to the system's evolving internal state. |

### Central Phase Registry

Runtime phases are loaded through `ki_system/phase_registry.py`. The registry defines load order, isolates module-loading failures, and verifies that the managed cycle terminates at the expected top phase.

Current processing chain, top to bottom:

`7cort Cortisol → 7g BDNF → 7f Orexin → 7e Histamine → 7d Slow-Wave → 7c E/I → 7b1 Wake-Chain Bridge → 7b Endocannabinoids → 7a Adenosine → 6d → 6c → 6b → 6a`

A recent call-stack audit found nested predecessor calls that caused the complete Phase-6a sleep-replay path to run three times per global cycle. The chain was cleaned so that Phase 7b1 is the orchestrator and each normal global cycle now produces exactly one Phase-6a replay cycle, one Phase-7c E/I event, one Phase-7d cycle, and one workpoint-observer event.

## Digital Neuromodulator Cockpit

All levels are normalized to `[0.0, 1.0]`. Values are derived from internal system state on top of bounded biological-style dynamics and homeostatic constraints.

### Core Learning Modulators

| Neuromodulator | Current system role |
|---|---|
| **Dopamine (DA)** | Outcome and gap-closure signal; contributes to stabilization of useful pathways. |
| **Serotonin (5-HT)** | Consolidation and stability signal; contributes to protection against uncontrolled revision. |
| **Glutamate (Glu)** | Excitatory drive associated with exploration and learning activity. |
| **GABA** | **Global inhibition and E/I-balance signal.** GABA currently regulates system-level inhibition; it does **not** identify or suppress individual words, relations, or extraction errors. |
| **Acetylcholine (ACh)** | Novelty, attention, and structural-revision signal. |
| **Noradrenaline (NA)** | Error, alarm, and persistent-pressure signal. |

### Homeostatic and Gain-Control Modulators

| Neuromodulator | Phase | Current system role |
|---|---:|---|
| **Adenosine** | 7a | Sleep-pressure homeostat. |
| **Endocannabinoids** | 7b | Retrograde gain control using 2-AG and anandamide dynamics. |

### Regulatory and Growth Modulators

| Neuromodulator | Phase | Current system role |
|---|---:|---|
| **Cortisol / HPA** | 7cort | Top-level stability watcher. The current database calibration remains in **Stage 1 observer mode**; it measures allostatic load and recommendations but does not apply Stage-2 nudges. |
| **Histamine** | 7e | Wake and arousal signal interacting with sleep pressure. |
| **Orexin** | 7f | Reading-endurance and curiosity-related drive. |
| **BDNF** | 7g | Activity-dependent growth and consolidation substrate. |

## Sleep, Consolidation, and Slow-Wave Selection

### Sleep Replay and Critic Gate — Phases 6a and 6b

Phase 6a performs offline-style replay after the wake path. Phase 6b evaluates replay effectiveness and plasticity adjustments. The critic gate evaluates whether a hypothesis has sufficient consistency to be strengthened; rejected or unstable material remains available as error and revision evidence.

The chain-cleanup audit now enforces one complete Phase-6a replay per global cycle. Existing historical replay rows are retained because they represent real executions, although older history must not be interpreted as one replay row per global cycle.

### Slow-Wave Substructure — Phase 7d

Phase 7d adds sub-1-Hz up/down-state processing with:

- stochastic reactivation
- adaptive thresholds
- activity-dependent participation
- survivor and weakening statistics
- anchor interleaving
- self-regulating down-selection

A passive **Phase-7d Workpoint Observer** now records longitudinal E/I state, activity, survivor ratios, reference movement, and virtual adjustment proposals. The observer remains non-applying: `applied = false`.

## E/I Drive, Active State, and Shadow Recurrence

The E/I path was recently separated into distinct semantic roles:

- **Phase-6a drive:** `glutamate_drive` and `gaba_drive`
- **Active Phase-7c state:** `glutamate_state` and `gaba_state`
- **Shared compatibility mirror:** the active state remains mirrored to the legacy `glutamate` and `gaba` keys for existing readers and GUI components
- **Shadow recurrence:** a non-applying recurrent candidate is evaluated in `phase7c_ei_shadow_events`

This separation prevents Phase 6a from overwriting the Phase-7c state on the next cycle.

### Shadow-Recurrent Candidate Result

The first recurrent candidate was evaluated passively. During a 20-cycle constant-drive run:

- the active path remained stable at `Glu = 0.527` and `GABA = 0.389`
- the Shadow path never applied any value
- Shadow Glutamate reached the lower boundary at cycle 12 of the test window and remained there
- the candidate was therefore rejected for active use

The failed candidate remains valuable negative learning material. It is not promoted into Phase 7d or the Cortisol watcher.

## Learning Dynamics and Progress Measurement

BrainStem tracks marginal rather than purely global progress because a growing hypothesis population can dilute global averages. Older unresolved hypotheses remain in a review pool and can be re-evaluated when later context becomes available.

The project does not claim that every current hypothesis is meaningful or that the system already understands language at human level. The current objective is to stabilize the mechanisms by which hypotheses are formed, challenged, revised, inhibited, and consolidated.

## Current Development and Testing Status

### Completed

- **Stage A — learning-core stabilization**
- sensory-deprivation drift test over **1,344 cycles**
- removal of legacy CorpusReader / Phase-3d word-role and filter paths
- removal of the obsolete `nlp.py` path; the modern Phase-7cort chain is the only learning path
- repository audit showing no active word-blacklist/filter implementation in the learning path
- graceful GUI shutdown that waits cooperatively for workers
- performance indexes and bounded pruning for approved history tables
- Phase-7d passive workpoint observer
- Phase-6a/6c/6d chain cleanup: one replay per global cycle
- separation of E/I drive, active state, and Shadow state
- safe rejection of the first recurrent E/I candidate through a non-applying 20-cycle Shadow run

### Safety Locks

The following remain disabled during the transition to Stage B:

- direct fact writes
- direct relation writes
- permanent fact promotion

The active learning path forms and revises hypotheses only. There are no word blacklists in the active learning architecture.

### Next Major Milestone — Stage B

Stage B will open write capabilities gradually, not all at once. The planned sequence is:

1. retain the Cortisol stability watcher as a safety layer
2. validate the controlled regulator path before enabling it
3. graduate `uncertain_hypothesis` to `stable_hypothesis` only through consolidation and critic gates
4. require at least **three survived Phase-7d consolidations** before a hypothesis is eligible
5. begin with a promotion budget of **one per cycle** and warm-up dampening
6. keep the permanent `facts` table closed during the first hypothesis-graduation stage
7. enable true fact promotion only after the graduation path is stable

### Open Engineering Items

- mark and stop the rejected recurrent Shadow candidate while preserving its history
- introduce separately identified Shadow candidates with independently tracked parameters
- do not reuse a single parameter for both drive integration and reciprocal E/I coupling
- integrate approved history pruning as a periodic autonomous maintenance job
- preserve the distinction between global GABA inhibition and any future hypothesis-specific error-damping mechanism

## Database Initialization

BrainStem uses `ki_memory.sqlite3` in the project root.

The database is created automatically when absent. Phase modules carry idempotent schema setup and schema self-checks. Performance indexes are ensured during bootstrap.

### Corpus-Preserving Learning Reset

The learning state can be reset without re-importing the corpus.

Preserved content includes:

- documents
- chunks and FTS data
- import state
- configuration

Learning-generated state can be cleared after a dry run. The reset workflow creates a timestamped database backup before applying changes and does not drop the schema.

## Sensory Deprivation and Drift Report

The GUI includes a sensory-deprivation mode that skips new wake/read input while internal replay, consolidation, and neuromodulatory dynamics continue.

The mode provides:

- start and stop controls
- optional cycle limits
- per-cycle CSV diagnostics
- live bounded/downsampled graphs
- signal-level and overall drift verdicts
- a fail-safe that clears deprivation mode on completion or interruption

The completed 1,344-cycle test supported the Stage-A stability decision under no-input conditions.

## Running the System

From the project root:

```cmd
python main.py --gui
```

### Workflow

| Step | GUI action | Purpose |
|---:|---|---|
| 1 | **Export/Konfig** | Configure the maximum number of articles before import. |
| 2 | **Import & Jobs → ZIM Einlesen** | Extract and pre-parse the corpus. |
| 3 | **Import & Jobs → Autonom dauerhaft starten** | Start autonomous learning. |
| 4 | **Import & Jobs → Autonom stoppen** | Stop autonomous learning cooperatively. |
| 5 | Close the GUI normally | The GUI now waits for active workers instead of terminating daemon workers abruptly. |

### GUI Status

The GUI is an experimental testing interface. Current functional areas include:

- Import and Jobs
- Export and Configuration
- Drift Report
- live 12-neuromodulator display
- corpus-coverage and cycle-progress indicators
- bounded diagnostic logs and graphs
- graceful worker shutdown

Other areas may remain experimental or incomplete.

## Prerequisites for ZIM Import

A Windows `zimdump.exe` build and all required DLL files must be placed in the project root next to `main.py`. Users must provide their own ZIM corpus.

The current development corpus is the German Wikipedia category **Computer**, imported into roughly 102,000 chunks.

## Development Notes

- **Package name:** the Python package remains `ki_system`.
- **Project folder:** the current local development folder is `BrainStem`.
- **Documentation language:** English.
- **Primary runtime:** Python 3.11 on Windows with SQLite.
- **Patch discipline:** backups, compile checks, schema self-checks, smoke tests, and automatic rollback are used for structural changes.
- **Database discipline:** full backups are taken before major changes and experiments.
- **Project status:** highly experimental and undergoing mathematical and architectural validation.
- **AI-assisted engineering:** development has included collaborative assistance from Claude, ChatGPT, Gemini, and NotebookLM.

## Disclaimer

BrainStem is an experimental cognitive-architecture research project. Biological terminology is used as an engineering analogy and design inspiration; the software is not a biological simulation and does not claim neuroscientific equivalence.
