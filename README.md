# Brainstem

> A biologically-inspired, neuro-symbolic cognitive architecture for lifelong learning.  
> Digital **neuromodulators** regulate learning, hypothesis tracking, and memory consolidation over an SQLite backend.

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

Phases are layered sequentially (`4x → 5x → 6a–6d → 7a–7g`). Loading is handled by a single **declarative registry** (`ki_system/phase_registry.py`) instead of scattered monkey-patch blocks:

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

### Regulatory & Growth Modulators — *new in this stage*

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

### Slow-Wave Sleep Substructure — `phase7d` *(new)*

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

- **Test corpus:** Wikipedia category *"Computer"* (German) (~102k chunks, fully pre-parsed as a ZIM import).
- **Reading coverage:** Learning is corpus-bounded; observed plateaus correspond to *not-yet-read* material rather than true stagnation. Coverage is tracked explicitly and rises as cycles run.
- **Safety mode (Stage A lock):** During calibration of phases 6 & 7, permanent writes (`fact_promotion`, `direct_fact_writes`, `direct_relation_writes`) are explicitly **`disabled`**, and **no word blacklists** are used. Learning happens purely in transient metaplasticity/hypothesis states to verify stability and convergence over hundreds of cycles.
- **Roadmap:** Stage A (stabilize the learning core) is **complete**. **Stage B** — controlled, consolidation-gated opening of the write locks so repeatedly confirmed hypotheses may become first anchors — is the next major milestone.

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

> **Note on the GUI:** This is an experimental testing interface. Currently **only the `Import & Jobs` and `Export/Konfig` tabs are functional** — all other tabs are placeholders without real functionality yet.
>
> The **maximum article count** for the ZIM import is configured in **`Export/Konfig`** and must be set before running *ZIM Einlesen*.

---

### Prerequisites for ZIM Import

>  **Required:** `zimdump` (the **`.exe`** together with its required **`.dll`** files) must be placed in the **project root directory**. Without it, the *ZIM Einlesen* function will not work.

The ZIM import relies on `zimdump` to extract articles from the `.zim` archive. Make sure the executable and all accompanying DLLs sit next to `main.py` in the root folder before running Stage 1.

---

## Development Notes & Technical Context

- **Codebase language:** Documentation is English; the source code (comments & internal naming) is **written in German**.
- **AI-assisted engineering:** Developed with the collaborative assistance of advanced language models (**Claude 3.5/4 Opus, ChatGPT, Gemini**).
- **Delivery & verification workflow:** Every module ships with idempotent schema management, self-checks, and a smoke test before integration; patches are validated with compile checks, backups, and automatic rollback.
- **Project scale & status:** A massive, highly experimental testing system. Due to its scale and ongoing calibration of complex homeostatic loops, the architecture **has not yet been consolidated** — it remains a playground for heavy benchmarking and mathematical verification of neuromorphic concepts.
