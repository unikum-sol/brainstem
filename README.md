# BrainStem Update 24.09.26

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](#current-development-and-testing-status)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](#running-the-system)
[![Backend: SQLite](https://img.shields.io/badge/backend-SQLite-lightgrey)](#database-initialization)
[![Roadmap: Stage B write locks open (experiment)](https://img.shields.io/badge/roadmap-Stage%20B%20write%20locks%20open-brightgreen)](#current-development-and-testing-status)

BrainStem is a biologically inspired, Real Neuro-Symbolic (RNS-AI) cognitive architecture for lifelong learning. It is designed to learn models of the structures and dynamics of language and text through context hypotheses, uncertainty, contradiction, revision, neuromodulation, replay, and consolidation rather than by merely storing isolated facts. A second, character-level observation layer additionally attempts to discover word boundaries directly from unsegmented text, without any predefined notion of "word."

>One CPU Core / No GPU

> [!IMPORTANT]
> BrainStem is a research and calibration system, not a production-ready assistant. As of the current project stage, all previously closed productive write paths (facts, relations, questions, fact promotion, gap/contradiction/revision writes) have been deliberately opened as an explicitly framed, ongoing experiment, with a full project backup taken beforehand as a fallback point.

---

[![BrainStem Project AI conversation](https://img.youtube.com/vi/4nN7zELSAMo/mqdefault.jpg)](https://www.youtube.com/watch?v=4nN7zELSAMo)
YouTube - AI conversation about BrainStem Project

---

[NotebookLM codebase exploration](https://notebook.google.com/notebook/34b994eb-9f62-4fd7-a04d-facbd6041654) 24.09.2026

---

## 📍 Navigation
* [Core Philosophy](#core-philosophy)
* [What is BrainStem really](#what-is-brainstem-really)
* [Roadmap](#Roadmap)
* [Architecture](#architecture)
* [Autonomous Lexical Emergence Layer](#autonomous-lexical-emergence-layer)
* [Stage B Full Write-Path Chain](#stage-b-full-write-path-chain)
* [Running the System](#running-the-system)
* [ZIM Import](#zim-import)
* [Academic References](#Academic-References)
* [Development Notes](#development-notes)

---

## Current State

### Current Validation Status

The system has completed a full read-through of its current two-source corpus (German Wikipedia *Physics* and *Computer* categories, 167,661 chunks, 100%) and has since run well beyond 11,500 real learning cycles in both active-learning and replay/consolidation-only modes without data loss, corruption, or GUI failure. A dedicated 1,500-cycle Etappe-A drift validation (sensory-deprivation mode, input disabled, inner dynamics only) completed with an overall result of **"konvergiert"**: all 20 evaluated signals were classified either `stabil` or `konvergiert`, with zero signals flagged as divergent. This drift run supersedes the historical 1,344-cycle baseline, which applied only to a much earlier architectural state.

**Cortisol Stage 2 is active and functionally verified.** `stage=2` is set in the production database. Under real production conditions it has not been triggered live (`allostatic_load` has stayed well below the 0.6 threshold — a sign of a consistently calm system, not a defect). Its guarded intervention logic (per-value cap 0.01, per-cycle budget 0.03, 3-cycle cooldown) has been independently confirmed correct under simulated stress.

**Hypothesis graduation (`uncertain_hypothesis` → `stable_hypothesis`) is active**, gated by the consolidation-survival criterion (≥3 confirmed Phase-7d survival cycles), an available critic-gate cross-check, warm-up dampening, and a budget of one graduation per cycle.

### Current Project Position — Experimental Write-Path Opening

As of the current project stage, the project owner has deliberately declared an ongoing internal experiment — in which every previously closed productive write path was opened at once — to be the new, valid project position rather than a temporary test. A full project backup was taken beforehand as an explicit fallback point. Concretely, direct Facts, Relations, and Questions writes, Fact promotion, Attention writes, and productive Phase-5f/5g/5i experiments are all currently active, alongside a newly registered four-module Stage-B chain described below.

### Autonomous Lexical Emergence Layer

A new Phase 0 module (`v8_phase0_lexical_boundary_observation_release`) is registered at the front of the runtime phase chain, running alongside the existing sentence-level `context_observation_learning` entry point. It reads the raw, unsegmented character stream of already-imported chunks, maintains a pure frequency table of "which character follows this preceding context of length *k*," and computes the local branching entropy at each character position:

H(context) = − Σ P(next_char | context) · log2 P(next_char | context)

A pronounced spike in this entropy at a given position is treated as a boundary candidate and creates or re-observes a `context_hypotheses` row using the project's existing `role='uncertain_lexical_boundary'` — reusing exactly the same insert-or-reobserve mechanism, consolidation path (Phase 7d), Stage-B graduation, and (under the current experimental write-path opening) fact promotion already used for every other hypothesis. No second learning pipeline and no new neuromodulator responsibility is introduced; the existing division of labor (exploration/glutamate governs new candidate generation, inhibition/GABA suppresses unstable candidates, consolidation/BDNF/serotonin governs stabilization, revision-bias governs re-opening an already-stable boundary) is reused as-is.

Once two adjacent, sufficiently confirmed boundary hypotheses bracket a character span, that span is intended to become a `lexical_units` row (schema already extended, `context_hypotheses.lexical_offset` column added). Once enough `status='stable'` lexical units exist, they are intended to populate the `relation_hint`/`object` fields of sentence-level hypotheses that are currently hard-coded to empty strings — closing the originally identified gap between raw sentence observation and any notion of word-to-word relation. Segmentation deliberately starts from the raw character stream itself, with no whitespace, punctuation, dictionary, or grammar used as a given boundary hint.

This mechanism is framed explicitly as a measurable experiment, not a guaranteed outcome, with a concrete measurement plan (stabilized unit-length distribution, cross-context recurrence of identical surface forms, a purely read-only comparison against simple whitespace segmentation as an external yardstick never fed back into learning, and a repeat of the existing drift/sensory-deprivation test once enough boundary hypotheses exist).

### Stage B Full Write-Path Chain

Four additional modules are now registered in the runtime phase chain, forming a single, ordered chain per cycle:

1. **Gap detection** (`stageb_gap_detection`) — productively populates `internal_learning_gaps` from observed learning gaps (previously observation-only).
2. **Contradiction detection** (`stageb_contradiction_detection`) — detects conflicting values between hypotheses and/or already-promoted facts and records them in the existing `contradictions` table.
3. **Hypothesis revision** (`stageb_hypothesis_revision`) — reverses a hypothesis's role when an independently stronger, contradicting hypothesis is detected, logging the change (old/new role, old/new confidence and uncertainty) in `hypothesis_role_revisions`.
4. **Fact promotion** (`stageb_fact_promotion`) — promotes a hypothesis into the `facts` table only after it has independently passed Stage-B graduation, linking each fact back to its source hypothesis via `source_hypothesis_id`. If the source hypothesis is later reversed by hypothesis revision, the corresponding fact is automatically retracted — facts remain correctable rather than permanently fixed.

The four modules are positioned so that gap detection runs early in the cycle, contradiction detection and hypothesis revision run immediately after the cooperative six-core authority (and therefore still ahead of graduation/promotion within the same cycle), and fact promotion runs last among the four — so that a revision detected within a cycle is already reflected before that same cycle's fact promotion.

### Corpus and Learning State

Current corpus baseline (two ZIM sources: German Wikipedia *Physics* and *Computer* categories, ~664 MB combined): 167,661 of 167,661 imported chunks read (100%), over 1.6 million active `uncertain_hypothesis` entries, a growing population of graduated `stable_hypothesis` entries, and — since the experimental write-path opening — a growing, non-zero population of promoted `facts`. Corpus completion does not stop autonomous learning; replay, consolidation, hypothesis evaluation, neuromodulator regulation, sleep/wake transitions, guarded graduation, gap detection, contradiction detection, hypothesis revision, and fact promotion all continue after all imported chunks have been read.

### Six-Core Neuromodulator State

The six core neuromodulators (dopamine, serotonin, glutamate, GABA, noradrenaline, acetylcholine) are governed by the common canonical runtime authority in `v8_cooperative_core_neuromodulator_sleep_authority_release.py`. The cooperative authority publishes a homeostatic ("tonic") pull target for the four non-E/I core values (dopamine, serotonin, noradrenaline, acetylcholine — glutamate/GABA remain the sole responsibility of Phase 7c); Phase 6a then blends its own from-scratch phasic (learning-evidence) computation with this tonic target using a self-regulating `tonic_weight` meta-parameter, written to `phase6a_neuromodulated_sleep_state` (the canonical source also read by the GUI), with values constrained to `[0.05, 0.95]`. The 1,500-cycle drift validation confirms all six core values remain tightly stable under stable input conditions.

#### Extended Neuromodulator State

All twelve neuromodulator/regulatory systems (six core + adenosine, endocannabinoids, cortisol, histamine, orexin, BDNF) are represented in code and runtime state and connected to the GUI. Adenosine and histamine show clear, reciprocal, bounded oscillation consistent with the Phase-7a sleep/wake cycle. Endocannabinoids remain at 0.000 at the current corpus scale (the postsynaptic-overload trigger mechanism has not yet fired). Cortisol remains low throughout (regime consistently "calm").

### Cooperative and Phase-7a Sleep/Wake Authority

BrainStem runs two independent, valid sleep-entry authorities:

- **Phase-7a adenosine homeostat**: a single-signal homeostat (threshold 0.65).
- **Cooperative six-core authority**: a combined, five-signal score —

sleep_score = 0.35 · adenosine pressure + 0.25 · arousal release + 0.20 · inhibitory readiness + 0.12 · consolidation readiness + 0.08 · (1 − cortisol-related stress block)

  with sleep-entry threshold 0.62, wake-entry threshold 0.42, and a minimum dwell time of 3 cycles for hysteresis.

Both authorities are independently valid; they are not required to enter sleep simultaneously. Phase 7d/7e admit real slow-wave consolidation whenever *either* authority reports sleep.

### Runtime Phase Structure

The effective runtime architecture, top to bottom:

1. Context observation and integrated hypothesis learning
2. Phase 0 — lexical boundary observation (new)
3. Strategy refinement, outcome closure, and observation memory
4. Context expansion and effectiveness evaluation
5. Strategy selection, experiment memory, and outcome learning
6. Outcome-driven strategy diversification
7. Stage-B gap detection (new, productive)
8. Context expansion and gap closure
9. Phase-5f context-expansion effectiveness and adaptive windowing
10. Phase-5g context strategy selection and experiment memory
11. Phase-5h strategy-experiment outcome learning
12. Phase-5i outcome-driven context strategy diversification
13. Phase-6a offline replay and meta-plasticity
14. Phase-6b replay effectiveness evaluation
15. Phase-6c bias persistence and self-regulating meta-control
16. Phase-6d saturation homeostasis and meta-metaplasticity
17. Phase-7a adenosine homeostasis
18. Phase-7b endocannabinoid regulation
19. Phase-7b1 wake-chain bridging
20. Runtime acceleration (perf0)
21. Phase-7c adaptive boundaries, E/I balance, and sigmoid soft clipping
22. Connection-layer acceleration (perf3)
23. Phase-7d slow-wave sleep and down-selection
24. Phase-7e histamine wake/arousal regulation
25. Phase-7f orexin wake-endurance regulation
26. Phase-7g BDNF growth and consolidation regulation
27. Phase-7cort stability observation and guarded Cortisol Stage 2
28. Cooperative six-core neuromodulator and sleep/wake authority
29. Guarded Stage-B hypothesis graduation
30. Stage-B contradiction detection (new, productive)
31. Stage-B hypothesis revision (new, productive)
32. Stage-B fact promotion (new, productive)
33. Non-productive shadow recheck runtime
34. Stage-B gapflow runtime contract (chain top)

### Efraimidis-Spirakis Sampling / Sigmoid Soft Clipping / E/I Balance

Both mechanisms are intact. The guarded kernel-comparison path used for E/I balance only enforces (and only raises) when explicitly running in opt-in `kernel_guarded` mode; default production cycles never crash from this path, including at neuromodulator boundary values near 0.05/0.95.

### GUI State

The GUI displays all twelve neuromodulators, corpus/hypothesis/fact counters, the Phase-7d survivor-reactivation queue, and — new — a per-parameter phasic/tonic/tonic-weight transparency line reflecting the fixed dual-writer architecture between the cooperative core authority and Phase 6a. A toggleable, continuous CSV value logger can record one row per GUI tick (all displayed values, filename stamped with date and time including seconds), and a separate, standalone CSV viewer (toggleable/overlayable curves, distributed as a standalone EXE as well as a plain Python package for Linux use) is available for offline graphical analysis, independent of the running BrainStem process.

## Next Major Step

1. Continue observing the newly opened Stage-B write chain (gap detection → contradiction detection → hypothesis revision → fact promotion) over further real cycles.
2. Clarify why `phase5g_experiment_outcomes` remains structurally empty even as facts are already being produced under the opened write paths, and whether this reflects an architectural gap in how the new chain and the pre-existing Phase-5g experiment population relate to each other.
3. Continue calibrating the Lexical Emergence layer's open parameters (context window *k*, entropy threshold) against the real, already-imported corpus before considering Step 3/4 of its implementation plan (calibration, consolidation integration).
4. Run the Tadros/Bazhenov-motivated catastrophic-forgetting protection test (import a second, topically distinct corpus and measure whether the first corpus's already-stabilized hypotheses/facts are protected, degraded, or reinforced).

## Roadmap

| Stage | Status | Gating condition to proceed |
|---|---|---|
| **Stage A — Core stability** | Complete: 100% corpus completion, 11,500+ real cycles, clean 1,500-cycle formal drift run ("konvergiert", zero divergent signals) | Complete |
| **Stage B — Guarded graduation** | Active: Cortisol Stage 2 applied, hypothesis graduation active | Ongoing observation |
| **Hypothesis graduation** (`uncertain_hypothesis` → `stable_hypothesis`) | Active, consolidation-gated | Ongoing |
| **Autonomous Lexical Emergence (Phase 0)** | Active in shadow/observe-and-consolidate mode, schema in place, open calibration parameters (*k*, entropy threshold) not yet finalized | Calibration against real corpus, then consolidation-integration decision |
| **Stage-B full write-path chain** (gap detection, contradiction detection, hypothesis revision, fact promotion) | Active — declared the new, valid project position as of the current experiment; full backup taken as fallback | Ongoing observation; open question on `phase5g_experiment_outcomes` interaction |
| **Opening the productive write locks** (Facts / Relations / Questions / Fact promotion) | Open (experimental project position) | Ongoing observation of the full chain; this project's "no black box, no unearned answers" guarantee continues to apply to every promoted fact via its source-hypothesis link and automatic retraction on revision |
| **Full corpus scaling** (complete German Wikipedia) | Deliberately deferred | Order-of-magnitude estimate only, not a commitment |
| **Vector database evaluation** | Deliberately deferred per project's own architecture-checkpoint rule | Only once stable hypothesis identities exist, a concrete semantic-retrieval use case is identified, requirements are measurable, and a read-only/shadow comparison against the SQLite baseline is performed |
| **Symbolic reasoning plugin** (deterministic, non-LLM rule engine) | Concept documented, not scheduled | Gated behind Stage-B graduation and the write-lock roadmap; a validated symbolic rule becoming productive is itself a new class of productive write and must be gated at least as strictly as fact promotion |
| **Multi-core / multi-process learning** | Explicitly out of scope for now | Not currently planned |

## Core Philosophy

Traditional semantic systems often focus on the **what**: storing and retrieving content. BrainStem focuses on the **how**: learning how context, uncertainty, evidence, contradiction, revision, and consolidation interact over time — now extended to a second, character-level layer that learns how recurring units and boundaries emerge from raw text itself. A corpus is treated as training substrate rather than as a static knowledge base.

Core principles:
- **Learning before rules:** no fixed lexical blacklists or hand-authored word-role mappings in the active learning path — including at the character level.
- **Errors remain evidence:** unresolved and contradicted hypotheses remain available for later revision; a fact promoted from a hypothesis is retracted, not silently overwritten, if that hypothesis is later reversed.
- **Consolidation before promotion:** every fact traces back to a specific source hypothesis that has independently survived the project's own consolidation and graduation gates.
- **Neuromodulation governs learning:** learning rate, error weighting, revision, confidence, exploration, inhibition, attention, stabilization, and consolidation are state-dependent, and the same division of labor is reused rather than duplicated for new hypothesis types.
- **Measure before changing:** diagnostics, audits, drift tests, and shadow experiments precede active-control changes.
- **No hidden legacy paths:** obsolete modules and duplicate learning paths are removed rather than retained as inactive code.

## What is BrainStem really

**BrainStem** is an autonomous software architecture designed for continuous, self-improving data processing and knowledge management. At its core, the system operates through an Autonomous Loop that orchestrates a chain of learning phases to ingest, analyze, and refine information without manual intervention.

The biological terminology used throughout the project's technical documentation, including terms such as "neuromodulators," "sleep," or "homeostasis," is not decorative. These labels are functional designators for mathematical state variables and algorithmic control mechanisms. The values are floats, not molecules. The behavior is biologically inspired, but the implementation is strictly mathematical.

**The system's primary mechanics include:**

**Dynamic Steering Variables:** Digital messenger substances are dynamic meta-parameters that adjust the system's learning rate, error weighting, and exploration strategies in real time.

**Active versus Offline Processing:** The system cycles between active ingestion and an offline optimization phase ("sleep") in which recorded hypotheses are re-evaluated through batch replay and consolidation.

**Character-Level Emergence:** Alongside sentence-level hypotheses, a branching-entropy-driven process observes the raw character stream to propose, and — through the same consolidation/graduation machinery — stabilize, candidate word-boundary units.

**Knowledge Distillation:** By comparing new data against existing stable records, the system filters out inconsistencies and, in the current experimental write-path stage, promotes reliable information into its long-term fact store — while retaining the ability to retract a fact if the underlying hypothesis is revised.

**Equilibrium Control:** Stability monitoring routines act as a feedback mechanism that pulls meta-parameters back into a functional range when the system detects a performance plateau or excessive variance.

**Adaptive Boundaries:** The limits within which the system operates are not hardcoded but self-regulating, expanding or contracting processing thresholds based on the complexity of the data encountered.

In summary, the project is a recursive learning engine that uses biologically derived control logic to implement a highly flexible, self-governing system for automated knowledge acquisition, now including an emerging capacity to discover the very units of language it reasons about.

---

Every promoted fact carries a complete provenance chain, from the final fact through its source hypothesis, its consolidation cycles, and down to the exact source chunks and documents that justified its creation — and can be automatically retracted if that source hypothesis is later revised. There is no black box. If the system states something, it can show why it states it, and it can take it back if the evidence changes.

---

## Architecture

<a href="assets/Project-Structure.png" target="_blank">
  <img src="assets/Project-Structure.png" alt="Project-Structure" width="200" />
</a>

---

BrainStem does not operate as a continuously coupled system of differential equations. Instead, it traverses a cyclic state graph: each phase activates at most 2–3 dominant neuromodulators, while the remainder are kept inactive or passive. This sequential architecture prevents interaction cascades and enables deterministic debugging.

### Two-Stage Data Pipeline

| Stage | Name | Description |
|---:|---|---|
| 1 | Inference-free pre-parsing | A raw corpus such as a Wikipedia ZIM file is extracted, structured, and partitioned into the chunk store before autonomous learning begins. |
| 2 | Autonomous learning | `AutonomousLoop` processes prepared chunks while the neuromodulatory, consolidation, and — since the experimental opening — full write-path chain reacts to the evolving internal state. |

### Runtime Chain

Runtime phases are loaded through `ki_system/phase_registry.py`. The registry defines load order, isolates module-loading failures, and verifies the managed-cycle top phase (chain top: Stage-B gapflow runtime contract).

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
| Cortisol | top-level stability watcher and guarded soft regulator (Stage 2 active) |
| Histamine | wake and arousal signal |
| Orexin | reading-endurance and curiosity-related drive |
| BDNF | activity-dependent growth and consolidation substrate |

GABA currently regulates **system-level inhibition**. It does not identify or suppress individual words, relations, or extraction errors. All 12 displays are connected both statically and at runtime in the GUI.

## Sleep, Consolidation, and Selection

### Sleep Replay and Critic Gate

Phase 6a performs offline-style replay after the wake path. Phase 6b evaluates replay effectiveness and plasticity adjustments. The critic gate checks whether proposed changes remain consistent enough to be retained; rejected or unstable material remains available as error and revision evidence.

### Slow-Wave Substructure

Phase 7d adds sub-1-Hz up/down-state processing with stochastic reactivation, adaptive thresholds, activity-dependent participation, survivor and weakening statistics, anchor interleaving, and self-regulating down-selection. Both sentence-level and lexical-boundary hypotheses share this same candidate pool, distinguished only by their `role` value.

### E/I State Separation

The E/I path distinguishes Phase-6a drive (`glutamate_drive`/`gaba_drive`), active Phase-7c state (`glutamate_state`/`gaba_state`), a compatibility mirror for existing readers/GUI components, and a non-applying shadow state for recurrent candidates. This separation prevents Phase 6a from overwriting the active Phase-7c state on the next cycle.

## Safety Locks

As of the current experimental project position, the following paths — previously listed here as disabled — are now open:

- Direct fact, relation, and question writes.
- Permanent fact promotion, gated through Stage-B graduation and reversible via hypothesis revision.
- Direct Phase-5f/5g/5i experimental writes.
- Direct attention and internal-gap writes.

This reflects a deliberate, explicitly framed experiment declared as the current project position, undertaken with a full backup as a fallback point — not a relaxation of the project's underlying provenance guarantee, since every fact remains traceable to, and retractable from, its source hypothesis. The active architecture continues to use no word blacklists or hard-coded linguistic filters.

## Database and Schema Discipline

BrainStem uses `ki_memory.sqlite3` in the project root. The database is created automatically when absent. Schema rules: schema changes must be reflected in the bootstrap in the same delivery; `ensure_schema` must be idempotent; `_self_check_schema` must run before writes; every written column must already be declared in `SCHEMA_TABLES`; compile checks, smoke tests, and intermediate checks are required before delivery; structural changes require a full backup first.

### Corpus-Preserving Learning Reset

Learning state can be reset without re-importing the corpus. Preserved content includes documents, chunks, FTS data, import state, and configuration. The reset workflow performs a dry run and creates a timestamped database backup before applying changes.

### Performance Maintenance

Performance indexes are ensured during bootstrap. Bounded pruning is limited to explicitly approved history tables. Active state, Phase-5f/5g/5i data, and other protected tables are excluded from generic pruning.

## Sensory Deprivation and Drift Report

The GUI includes a sensory-deprivation mode that skips new wake/read input while replay, consolidation, and neuromodulatory dynamics continue. It provides start/stop controls, optional cycle limits, per-cycle CSV diagnostics, bounded/downsampled live graphs, signal-level and overall drift verdicts, and fail-safe cleanup when the run completes or is interrupted. The completed 1,500-cycle no-input test supersedes the historical 1,344-cycle baseline for the Stage-A stability decision.

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

- Import and Jobs (including the toggleable CSV value logger)
- Export and Configuration
- Drift Report
- Live 12-neuromodulator display, corpus-coverage and cycle-progress indicators, bounded diagnostic logs and graphs, cooperative worker shutdown

The GUI remains an experimental testing interface; individual areas may still be incomplete. A separate, standalone CSV viewer application (toggleable/overlayable curves) is available for offline analysis of logged sessions.

## ZIM Import

A Windows `zimdump.exe` build and its required DLL files must be placed in the project root next to `main.py`. Users must provide their own ZIM corpus. The current development corpus is the German Wikipedia categories *Physics* and *Computer*.

## Academic References

This project builds upon concepts, algorithms, and theoretical frameworks established in the following academic literature:

1. **Saffran, Jenny R.; Aslin, Richard N.; Newport, Elissa L.** (1996) *Statistical Learning by 8-Month-Old Infants*. Science.
2. **Aslin, Richard N.; Saffran, Jenny R.; Newport, Elissa L.** (1998) *Computation of Conditional Probability Statistics by 8-Month-Old Infants*. Psychological Science.
3. **Fló, Ana; Benjamin, Lucas; Palu, Marisa; Dehaene-Lambertz, Ghislaine** (2022) *Sleeping neonates track transitional probabilities in speech but only retain the first syllable of words*. Scientific Reports.
4. **Zhikov, Valentin; Takamura, Hiroya; Okumura, Manabu** *An Efficient Algorithm for Unsupervised Word Segmentation with Branching Entropy and MDL*.
5. **Hamilton, William L.** (2020) *Graph Representation Learning*. Morgan & Claypool Publishers (McGill University).
6. **Watkins, Yijing; Kim, Edward; Sornborger, Andrew; Kenyon, Garrett T.** (2020) *Using Sinusoidally-Modulated Noise as a Surrogate for Slow-Wave Sleep to Accomplish Stable Unsupervised Dictionary Learning in a Spike-Based Sparse Coding Model*.
7. **Tadros, Timothy; Krishnan, Giri P.; Ramyaa, Ramyaa; Bazhenov, Maxim** (2022) *Biologically Inspired Sleep Algorithm for Reducing Catastrophic Forgetting in Neural Networks*.
8. **Fischbacher, Thomas; Comsa, Iulia M.; Potempa, Krzysztof; Firsching, Moritz; Versari, Luca; Alakuijala, Jyrki** (2020) *Intelligent Matrix Exponentiation*. arXiv preprint arXiv:2008.03926. (Evaluated; assessed as not relevant to this project's architecture and not adopted.)
9. **Butz, Markus; van Ooyen, Arjen** (2013/2014) *Homeostatic structural plasticity – a key to neuronal network formation and repair*. BMC Neuroscience / PLoS Computational Biology.
10. **Parker, Paul A.; Holan, Scott H.; Ravishanker, Nalini** (2020) *Nonlinear Time Series Classification Using Bispectrum-based Deep Convolutional Neural Networks*. arXiv preprint arXiv:2003.02353.
11. **Rončević, Igor; et al.** *A molecule with half-Möbius topology*. Science (Supplementary Materials, SqDRIFT sampling).

---

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
- **Status:** highly experimental and under mathematical and architectural validation, currently in an explicitly declared full-write-path-open experimental stage
- **Engineering discipline:** backup, compile check, schema self-check, smoke test, and rollback planning for structural changes
- **AI-assisted engineering:** development has included collaborative AI assistance. Concept elaboration with ChatGPT, code generation Claude Opus/Sonnet and ChatGPT Deep Thinking, code review NotebookLM, Gemini and Copilot as critics (no sugarcoat mode)

## Claims and Limitations

BrainStem does not claim that every current hypothesis is meaningful or that the system understands language at a human level. The current objective is to establish and validate the mechanisms by which hypotheses are formed, challenged, revised, inhibited, replayed, consolidated, and — now — promoted into and retracted from a fact store, as well as the mechanisms by which word-like units might emerge from raw character statistics.

## Disclaimer

BrainStem is an experimental cognitive-architecture research project. Biological terminology is used as an engineering analogy and design inspiration. The software is not a biological simulation and does not claim neuroscientific equivalence.
