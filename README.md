# brainstem
A biologically-inspired neuromodulated context learning and memory consolidation core. Simulates neurotransmitter dynamics (Dopamine, Serotonin, Noradrenaline) to manage data prioritization, hypothesis tracking, and database optimization via SQLite.


# brainstem 

**brainstem** is a biologically-inspired context learning and data prioritization framework. Instead of storing data statically, this system simulates the dynamics of a biological brainstem: digital **neuromodulators** regulate data processing rates, evaluate information uncertainty, and consolidate data structures during simulated "sleep" cycles.

The system operates as a modular data pipeline, managing a probabilistic knowledge base purely via an SQLite backend.


# brainstem (TestVersion 8) – Neuromorphic Cognitive Architecture

AI-System V8 is a biologically-inspired, neuro-symbolic cognitive architecture designed for lifelong learning. The system extracts logical relations from unstructured texts and constructs a consistent world model within a relational SQLite database. The control of learning rates, exploration, and consolidation is managed autonomously via a homeostatic network of digital neurotransmitters and simulated sleep cycles.

---

## Data Pipeline & System Architecture

The system eliminates I/O latencies during cognitive processing through a strictly separated, **two-stage pipeline**:

* **Stage 1: Inference-Free Pre-Parsing:** The raw data (e.g., Wikipedia from a `.zim` database) is completely read, structured, and partitioned into a high-performance staging structure in memory before autonomous learning begins.
* **Stage 2: Autonomous Learning:** The `AutonomousLoop` processes the prepared text chunks in bite-sized portions. As a result, the neuromodulatory processes react purely to the inherent semantics of the data, undisturbed by disk read/write latencies.

---

## The Digital Neurotransmitter Cockpit

In each cycle of the `AutonomousLoop`, the system computes the state of six digital chemical messengers. These neuromodulators directly control the metaplasticity and behavior of the system. All values are strictly normalized to the interval `[0.0, 1.0]`.

### 1. Dopamine (DA) – The Success and Reward Metric
* **System Role:** Signals success in closing knowledge gaps (*Gap Closure*). A high dopamine value stabilizes current cognitive pathways and validates proposed context hypotheses.

### 2. Serotonin (5-HT) – The Consolidation and Stability Regulator
* **System Role:** Controls the focus on permanently securing learned structures (*Consolidation Bias*). It protects established knowledge from being overwritten by subsequent informational noise.

### 3. Glutamate (Glu) – The Excitatory Exploration Accelerator
* **System Role:** Drives cognitive arousal and the urge to generate new hypotheses (*Exploration Bias*). It increases synaptic plasticity to enable radical cross-connections.

### 4. GABA – The Inhibitory Noise Filter
* **System Role:** Acts as a functional counterpart to glutamate. It dampens irrelevant or redundant pathways (*Inhibition Bias*), protects the system from mathematical oversteering (saturation), and filters out informational noise.

### 5. Acetylcholine (ACh) – Unexpected Novelty (Novelty Detector)
* **System Role:** Controls attention and the urge for structural revision (*Revision Bias*). High ACh levels break up rigid system states when incoming data deviates significantly from the existing knowledge base, allowing for error corrections.

### 6. Noradrenaline (NA) – The Stress and Error Signal
* **System Role:** Responds to chronic cognitive blockages (`persistent_pressure`). If the system stagnates over multiple cycles or cannot resolve errors, noradrenaline forces a hard switch in the cognitive search strategy or temporarily freezes blocked chunks.

---

## Homeostasis, Sleep Pressure & Critic Gate

### Adenosine Homeostat (`phase7a`)
During the active waking phase, the system accumulates sleep pressure (`adenosine_level`) through the continuous processing of texts and the generation of context hypotheses. Acetylcholine acts as a temporary dampener of this buildup. When the adenosine level reaches the critical maximum (`1.0`), the architecture forces the **`neuromodulated_sleep_replay`**.

### Sleep Replay & Critic Gate (`phase6a` & `phase6b`)
In the artificial sleep mode, the neurochemical balance shifts: excitatory processes (glutamate) are throttled, while inhibitory filtering (GABA) and consolidation (serotonin) dominate. 

Before temporary hypotheses are permanently transferred to long-term memory, they must pass through the **`_critic_gate`**:
1. The system computes the **`anchor_consistency`** of the new relations against immutable core facts (anchor data).
2. If the system detects logical contradictions or instabilities, the gate intervenes (`critic_rejected`), applies mathematical penalties to the affected pathways, and prevents database contamination (hallucination protection).
3. After a successful replay cycle, the `adenosine_level` is completely depleted.

---

## Current Development & Testing Status

* **Test Corpus:** Wikipedia category "Computer" (fully pre-parsed).
* **Safety Mode:** During the ongoing calibration of phases 6 and 7, permanent write operations at the database level (`fact_promotion`, `direct_fact_writes`, `direct_relation_writes`) are explicitly set to **`disabled`**.
* **Objective:** Learning currently takes place exclusively within the transient metaplasticity states in RAM to mathematically verify system stability and ensure the error-free convergence of all homeostatic control loops over hundreds of test cycles.
