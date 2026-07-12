# Brainstem

> A biologically-inspired, neuro-symbolic cognitive architecture for lifelong learning.  
> Digital **neuromodulators** regulate learning, hypothesis tracking, and memory consolidation over an SQLite backend.
>An autonomous, biologically inspired AI system designed to understand the underlying mechanics, structures, and rules of language and text—rather than just memorizing facts.
>
>## The Core Philosophy
>Traditional AI models and semantic databases often focus on memorizing and reproducing content (the "what"). **Brainstem takes a fundamentally different approach (the "how").**
>The system treats incoming data (such as massive text corpora or Wikipedia dumps) not as a static knowledge base to be memorized, but as a training substrate. Its goal is to analyze, comprehend, and master the **structural and semantic grammar of language**. 
> **Structural Learning:** Brainstem learns how subjects, relations, and objects interact, mapping how meaning is built dynamically.
> **Noise Filtering via Sleep Cycles:** By mimicking biological sleep phases (such as slow-wave sleep and consolidation), the system constantly prunes weak or chaotic connections to crystalize the core rules of language.


![status](https://img.shields.io/badge/status-experimental-orange)
![python](https://img.shields.io/badge/python-3.11-blue)
![backend](https://img.shields.io/badge/backend-SQLite-lightgrey)
![stage](https://img.shields.io/badge/roadmap-Stage%20A%20complete-green)

---

## Overview

**brainstem** (Test Version 8) does not store data statically. Instead it simulates the dynamics of a biological brainstem: a homeostatic network of **12 digital neurotransmitters** regulates data-processing rates, evaluates uncertainty, forms context hypotheses, and consolidates knowledge during simulated **sleep cycles**.

The system extracts logical relations from unstructured text and incrementally builds a probabilistic world model in a relational **SQLite** database. Learning rate, exploration, error weighting, consolidation, and sleep–wake regulation are controlled autonomously — the system is designed to *learn how to learn*, not to be told the rules.

---

## Architecture

### Two-Stage Data Pipeline

| Stage | Name | Description |
|-------|------|-------------|
| **1** | Inference-Free Pre-Parsing | The raw corpus (e.g. Wikipedia `.zim`) is fully read, structured, and partitioned into a high-performance chunk store **before** learning begins (GUI: *"ZIM Einlesen"*). |
| **2** | Autonomous Learning | The `AutonomousLoop` processes prepared chunks in bite-sized portions, so neuromodulation reacts purely to data semantics — undisturbed by disk I/O latency. |

### Central Phase Registry

Phases are layered sequentially (`4x → 5x → 6a–6d → 7a–7g`). Loading is handled by a single **declarative registry** (`ki_system/phase_registry.py`) :

- Defines the **exact load order** in one place
- Isolates each entry with its own error handling + machine-readable load report
- Runs a **post-load self-check** (verifies the cycle chain terminates at the correct top phase and that all safety flags are set)

**Processing chain (top → down):**

```text
7g BDNF → 7f Orexin → 7e Histamine → 7d Slow-Wave → 7c → 7b1 → 7b → 7a → 6d → 6c → 6b → 6a
```

---

## The Digital Neurotransmitter Cockpit

Each cycle computes **12** self-regulating chemical messengers. Every level is derived from the system's *own* internal state (progress, uncertainty, sleep pressure, consolidation consistency, reading coverage) — not from fixed rules. All values are normalized to `[0.0, 1.0]`.

### Core Learning Modulators

| # | Neurotransmitter | System Role |
|---|------------------|-------------|
| 1 | **Dopamine (DA)** | Success & reward metric — signals *gap closure*, stabilizes validated pathways. |
| 2 | **Serotonin (5-HT)** | Consolidation & stability — protects established knowledge from being overwritten (*consolidation bias*). |
| 3 | **Glutamate (Glu)** | Excitatory exploration — drives new-hypothesis generation, raises plasticity (*exploration bias*). |
| 4 | **GABA** | Inhibitory noise filter — dampens redundant pathways, prevents saturation; reciprocal Glu–GABA E/I balance. |
| 5 | **Acetylcholine (ACh)** | Novelty detector — controls attention & structural revision when data deviates from the model (*revision bias*). |
| 6 | **Noradrenaline (NA)** | Stress & error signal — reacts to chronic blockage (`persistent_pressure`), forces strategy switches. |

### Homeostatic & Gain-Control Modulators

| # | Neurotransmitter | System Role |
|---|------------------|-------------|
| 7 | **Adenosine** `phase7a` | Sleep-pressure homeostat — accumulates while awake, forces sleep-replay at max, depletes after replay. |
| 8 | **Endocannabinoids** `phase7b` | Retrograde gain control — 2-AG / Anandamide dampening & LTD of over-excited pathways. |

### Regulatory & Growth Modulators 

| # | Neurotransmitter | System Role |
|---|------------------|-------------|
| 9 | **Cortisol / HPA** `phase7cort` | Global **stability watcher**. Measures *allostatic load* (threshold drift, survivor collapse, effectiveness depression, oscillation, E/I saturation) and **recommends** neuromodulator nudges. Currently a **Stage-1 pure observer** (recommend-only, never applied). |
| 10 | **Histamine** `phase7e` | Wake / arousal — reciprocal antagonist of adenosine; together they form the emergent **sleep–wake switch**. |
| 11 | **Orexin** `phase7f` | Reading-endurance & **curiosity drive** — motivates continued reading while unread corpus *and* progress remain; self-attenuates when satiated (`curious_drive` / `balanced` / `satiated`). |
| 12 | **BDNF** `phase7g` | Activity-dependent **growth & consolidation** substrate — rises on consistent, progressing consolidation (`growth`), else `maintenance` / `low_plasticity`. |

---

## Sleep, Consolidation & Slow-Wave Substructure

### Sleep Replay & Critic Gate — `phase6a` & `phase6b`

In artificial sleep, excitation (glutamate) is throttled while inhibition (GABA) and consolidation (serotonin) dominate. Before hypotheses are strengthened, they pass the **`_critic_gate`**:

1. Computes `anchor_consistency` of new relations against stable anchor data.
2. On contradiction/instability → `critic_rejected` + mathematical penalties (**hallucination protection**).
3. After a successful replay cycle, `adenosine_level` is fully depleted.

### Slow-Wave Sleep Substructure — `phase7d`

Adds a true `<1 Hz` up/down-state substructure with **self-regulating down-selection**:

- **Stochastic reactivation** (weighted sampling without replacement) — participation varies across oscillations, so *consistency* can be measured; only repeatedly, robustly active hypotheses survive.
- **Adaptive selection threshold** derived from the system's own activity distribution and its GABA/Glutamate-derived *selection pressure* — **no hard-coded cut-off**.
- **Anchor interleaving** as an anti-hallucination reality check.

This replaces the earlier "reinforce-everything" no-op with genuine, biologically-plausible consolidation (a small survivor fraction is reinforced, the majority weakened).

---

## Learning Dynamics & Progress Measurement

Because the knowledge base grows continuously, a **marginal progress metric** assesses learning honestly (the raw global average is diluted by accumulated mass). Comparing newest-vs-oldest cohorts reveals the true learning curve:

- Uncertainty falls from **~0.99** (earliest hypotheses) toward **~0.68** (most recent)
- The share of undifferentiated `uncertain_hypothesis` roles **decreases over time**

Old, unresolved hypotheses are **never discarded** — they form a growing *review pool*, re-examined as more context is read.

> **Core principle:** nothing is thrown away — everything stays open for re-evaluation as knowledge grows.

---

## Current Development & Testing Status

- **Own Test corpus:** Wikipedia category *"Computer"* (German) (~102k chunks, fully pre-parsed as a ZIM import). You must bring our own ZIM file.
- **Reading coverage:** Learning is corpus-bounded; observed plateaus correspond to *not-yet-read* material rather than true stagnation. Coverage is tracked explicitly and rises as cycles run.
- **Safety mode (Stage A lock):** During calibration of phases 6 & 7, permanent writes (`fact_promotion`, `direct_fact_writes`, `direct_relation_writes`) are explicitly **`disabled`**, and **no word blacklists** are used. Learning happens purely in transient metaplasticity/hypothesis states to verify stability and convergence over hundreds of cycles.
- **Roadmap:** Stage A (stabilize the learning core) is **complete** and its stability has been empirically verified via the sensory-deprivation drift test (no harmful drift under input removal). **Stage B** — controlled, consolidation-gated opening of the write locks (with a warm-up dampening of the first promotions to avoid overfitting on the earliest references) — is the next major milestone.
- **Future:** switch to vector database
---

## Database Initialization

The system uses a single **SQLite** database (`ki_memory.sqlite3`) in the project root.

**No manual setup is required.** If the database file does not exist on startup, it is **created automatically**:

- The core schema (documents, chunks, hypotheses, settings, etc.) is initialized on first launch.
- Every phase module carries its own schema and applies it idempotently via `ensure_schema()` at the start of each cycle — missing tables are created and missing columns are added automatically (self-healing schema).
- A built-in `_self_check_schema()` verifies all required columns exist before any writes occur.

As a result, you can simply run the GUI on a clean checkout; the database and all required tables/columns are provisioned on demand.

---

### Learning Reset (Corpus-Preserving)

For calibration and repeatable experiments, the learning state can be reset **without** re-importing the corpus. Available as a GUI button in **Export/Konfig** ("Lernsystem zuruecksetzen (Korpus bleibt)") and as a standalone script (reset_learning.py).

- **KEEP (preserved):** chunks, chunks_fts*, documents, settings/config, import_state, sqlite internals — i.e. the full imported ZIM corpus stays intact.
- **WIPE (cleared):** all learning-generated tables (context_hypotheses, chunk_attention_scores, all phase* state/event/cycle tables, cortisol/neuromodulator states, reading queue, gaps, etc.).
- **Safety:** dry-run by default (python reset_learning.py shows the plan, changes nothing); the real reset (--apply or the GUI button) makes an automatic timestamped DB backup first, then DELETEs rows (tables/schema are never dropped) and VACUUMs.
- **GUI guard:** the reset button is only active while autonomous learning is stopped, and asks for confirmation.

This lets the system be returned to a clean "just-imported" state in seconds, after which it re-seeds all neurotransmitters to their baselines on the first cycle and starts learning from zero.

---

### Sensory Deprivation & Drift Report

A GUI-controlled **sensory-deprivation mode** (tab "Drift-Report") for homeostatic calibration: the wake/read step is skipped (no new chunks, no new hypotheses) while the inner dynamics — sleep replay, consolidation and all 12 neuromodulators — keep running. This isolates the system's **self-regulation** from input noise and answers a single question: *does anything drift when no input arrives?*

- **Controls:** Start/Stop, plus an optional cycle-limit field (up to 9999). With the limit checkbox off, the run continues until Stop; with it on, it stops after N cycles — Stop always remains effective.
- **Per-cycle CSV log:** every deprivation cycle is written to drift_log_<timestamp>.csv in the project root (all 12 neurotransmitters + exploration_bias, plasticity, adaptive_threshold, survivors/participated/weakened, effectiveness, reciprocal_gate, allostatic_load).
- **Live graphs:** key signals (exploration_bias, adenosine, plasticity, effectiveness, histamine) are plotted live on a canvas.
- **Drift report:** for each signal — first/last/delta/span and a verdict (stabil / konvergiert / DIVERGIERT); count-signals (survivors etc.) are judged relative to their mean, normalized signals by absolute thresholds. Overall verdict: kein_drift / konvergenz / DIVERGENZ-WARNUNG. Appended to the CSV as a comment block.
- **Fail-safe:** the deprivation flag is always cleared on stop/finish (finally), so the system can never remain stuck in deprivation.

Result so far: over 1000 input-free cycles the regulated signals (neuromodulators, exploration_bias, plasticity) stay within a very tight band — the system is homeostatically stable and does not drift under input removal.

---

## Running the System

The GUI is launched from the project root:

```bash
python main.py --gui
```

### Workflow

| Step | GUI Action | Purpose |
|------|-----------|---------|
| 1 | **Export/Konfig** | Set the **maximum number of articles** for the ZIM import (**must** be configured before importing). |
| 2 | **Import & Jobs → ZIM Einlesen** | Stage 1 — pre-parse & import the corpus into the chunk store (run once). |
| 3 | **Import & Jobs → Autonom dauerhaft starten** | Stage 2 — start the autonomous learning loop; each GUI cycle runs several internal chain passes. |
| 4 | **Import & Jobs → Autonom stoppen** | Stop the loop cleanly. |
| 5 | **DON'T** close GUI while running Cycle, possible database damage |

> **Note on the GUI:** This is an experimental testing interface. Currently the **Import & Jobs**, **Export/Konfig** and **Drift-Report** tabs are functional — the remaining tabs are placeholders. Import & Jobs >shows a live 12-neurotransmitter dashboard (with tooltips and legend), two progress bars (total corpus coverage + current GUI-cycle step), and a small floating "mood head" window that mirrors the system state >(curious / growing / sleeping / stressed) and auto-closes with the GUI.
>
> The **maximum article count** for the ZIM import is configured in **`Export/Konfig`** and must be set before running *ZIM Einlesen*.

---

### Prerequisites for ZIM Import

>  **Required:** `zimdump` for Windows (the **`.exe`** together with its required **`.dll`** files) must be placed in the **project root directory**. Without it, the *ZIM Einlesen* function will not work.

The ZIM import relies on `zimdump` to extract articles from the `.zim` archive. Make sure the executable and all accompanying DLLs sit next to `main.py` in the root folder before running Stage 1.

---

## Development Notes & Technical Context

- **Codebase language:** Documentation is English; the source code (comments & internal naming) is **written in German**.
- **AI-assisted engineering:** Developed with the collaborative assistance of advanced language models (**Claude 3.5/4 Opus, ChatGPT, Gemini**).
- **Delivery & verification workflow:** Every module ships with idempotent schema management, self-checks, and a smoke test before integration; patches are validated with compile checks, backups, and automatic rollback.
- **Project scale & status:** A massive, highly experimental testing system. Due to its scale and ongoing calibration of complex homeostatic loops, the architecture **has not yet been consolidated** — it remains a playground for heavy benchmarking and mathematical verification of neuromorphic concepts.
