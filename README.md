## BrainStem Update 28.09.26

[Status: Experimental](#current-development-and-testing-status)[Python 3.11](#running-the-system)[Backend: SQLite](#database-initialization)[Roadmap: Full Relations/Ontology/Questions emergence chain active](#current-development-and-testing-status)

BrainStem is a biologically inspired, Real Neuro-Symbolic (RNS-AI) cognitive architecture for lifelong learning. It is designed to learn models of the structures and dynamics of language and text through context hypotheses, uncertainty, contradiction, revision, neuromodulation, replay, and consolidation rather than by merely storing isolated facts. A second, character-level observation layer discovers word boundaries directly from unsegmented text, without any predefined notion of "word." Since 25–28 September 2026, a third, fourth, and fifth observation layer additionally discover relations between already-observed elements, categories emerging from the resulting relation graph, and durable questions emerging from persistent, unresolved information gaps.

One CPU Core / No GPU

BrainStem is a research and calibration system, not a production-ready assistant. As of the current project stage, all previously closed productive write paths (facts, relations, ontology categories, questions, fact/relation/ontology/question promotion, gap/contradiction/revision writes) have been deliberately opened as an explicitly framed, ongoing experiment, with a full project backup taken beforehand as a fallback point.

[BrainStem Project AI conversation](https://www.youtube.com/watch?v=4nN7zELSAMo)YouTube - AI conversation about BrainStem Project
[NotebookLM codebase exploration](https://notebook.google.com/notebook/34b994eb-9f62-4fd7-a04d-facbd6041654) 28.09.2026

### 📍 Navigation
- [Core Philosophy](#core-philosophy)
- [What is BrainStem really](#what-is-brainstem-really)
- [Roadmap](#Roadmap)
- [Architecture](#architecture)
- [Autonomous Lexical Emergence Layer](#autonomous-lexical-emergence-layer)
- [Relations, Ontology, and Questions Emergence](#relations-ontology-and-questions-emergence)
- [Stage B Full Write-Path Chain](#stage-b-full-write-path-chain)
- [Neuromodulator-Coupled Thresholds](#neuromodulator-coupled-thresholds)
- [Running the System](#running-the-system)
- [ZIM Import](#zim-import)
- [Academic References](#Academic-References)
- [Development Notes](#development-notes)

### Current State

#### Current Validation Status

The system has completed a full read-through of its current two-source corpus (German Wikipedia _Physics_ and _Computer_ categories, 167,661 chunks, 100%) and has since run well beyond 11,500 real learning cycles in both active-learning and replay/consolidation-only modes without data loss, corruption, or GUI failure. A dedicated 1,500-cycle Etappe-A drift validation (sensory-deprivation mode, input disabled, inner dynamics only) completed with an overall result of **"konvergiert"**: all 20 evaluated signals were classified either stabil or konvergiert, with zero signals flagged as divergent.

**Cortisol Stage 2 is active and functionally verified.** stage=2 is set in the production database. Under real production conditions it has not been triggered live (allostatic_load has stayed well below the 0.6 threshold — a sign of a consistently calm system, not a defect). Its guarded intervention logic (per-value cap 0.01, per-cycle budget 0.03, 3-cycle cooldown) has been independently confirmed correct under simulated stress.

**Hypothesis graduation** (uncertain_hypothesis → stable_hypothesis, and — since the Relations/Ontology work below — uncertain_lexical_boundary → stable_lexical_boundary and uncertain_relation_hypothesis → stable_relation_hypothesis) is active, gated by the consolidation-survival criterion (≥3 confirmed Phase-7d survival cycles), an available critic-gate cross-check, warm-up dampening, a budget of one graduation per cycle, and — new — neuromodulator-coupled divisive-normalization role selection among the three competing roles (see below).

**As of 25–28 September 2026, the complete Relations/Ontology/Questions emergence chain (originally planned as three slices) is fully implemented, wired into the runtime phase chain, and verified through repeated real, multi-hundred-cycle end-to-end runs.** The runtime phase registry now holds 39 entries (previously 34). Additionally, eleven of the pipeline's own calibrated thresholds and budgets are now directly coupled to one or more of the six core digital neuromodulators, each grounded in a specific piece of neuroscience literature (see [Neuromodulator-Coupled Thresholds](#neuromodulator-coupled-thresholds)).

#### Current Project Position — Experimental Write-Path Opening

Direct Facts, Relations, Ontology, and Questions writes, Fact/Relation/Ontology/Question promotion, Attention writes, and productive Phase-5f/5g/5i experiments are all currently active, alongside the full nine-module Stage-B chain described below.

#### Autonomous Lexical Emergence Layer

A Phase 0 module (v8_phase0_lexical_boundary_observation_release) is registered at the front of the runtime phase chain, running alongside the existing sentence-level context_observation_learning entry point. It reads the raw, unsegmented character stream of already-imported chunks, maintains a pure frequency table of "which character follows this preceding context of length _k_," and computes the local branching entropy at each character position:

H(context) = − Σ P(next_char | context) · log2 P(next_char | context)

A pronounced spike in this entropy at a given position is treated as a boundary candidate and creates or re-observes a context_hypotheses row using role='uncertain_lexical_boundary' — reusing exactly the same insert-or-reobserve mechanism, consolidation path (Phase 7d), Stage-B graduation, and fact promotion already used for every other hypothesis. Once a lexical-boundary candidate's own evidence_count clears a small threshold, it additionally becomes eligible as an input element for the Relations emergence layer below — deliberately *before* full Stage-B graduation, a design decision grounded in evidence that word segmentation and relational learning proceed in parallel in human learners rather than sequentially (see Academic References).

#### Relations, Ontology, and Questions Emergence

Three additional observation/promotion layers, completed this session, extend the system beyond isolated sentence- and word-level hypotheses toward structured, relational, categorical, and curiosity-driven knowledge:

**Relations (Modul A).** `v8_phase0b_relational_binding_observation_release` binds pairs of already-stable elements that co-occur within the same sentence into a candidate relation, via a strict two-stage statistical process: a symmetric Pointwise Mutual Information existence gate (`PMI(A;B) = log2(P(A,B)/(P(A)·P(B)))`), followed — only once enough evidence exists — by a purely positional direction signal, calibrated separately per corpus language (German requires a stronger positional skew than English, reflecting German's weaker "position implies grammatical role" signal). `v8_stageb_relation_promotion_release` promotes graduated relation hypotheses into the `relations` table, fully retractable on later revision, exactly like fact promotion.

**Ontology (Modul B).** `v8_stageb_ontology_cluster_observation_release` builds an undirected graph over the `relations` table and clusters it via Label Propagation, anchoring cluster identity across cycles to each cluster's own centrality-based prototype (Rosch prototype theory) rather than to Label Propagation's own non-deterministic per-cycle label. `v8_stageb_ontology_promotion_release` promotes reconfirmed-stable clusters into the `ontology` table as `child → parent` rows, with the fixed, honest placeholder relation `"is_a"` — the system has structurally identified a graded group-membership relationship via connectivity and centrality, without parsing or inferring any actual linguistic category name.

**Questions (Modul C).** `v8_stageb_question_promotion_release` promotes a persistent, repeatedly reconfirmed entry from the existing `internal_learning_gaps` table into the `questions` table once it clears a calibrated persistence threshold — directly implementing Loewenstein's Information-Gap Theory of curiosity. Question text is never a generated sentence, only a fixed, non-linguistic marker followed by the underlying hypothesis's own verbatim, already-observed surface text. `v8_stageb_question_chunk_feedback_release` closes the loop back into reading behavior: for every still-open question, it boosts both the exact source chunk where the underlying gap was first observed *and* searches the full corpus via SQLite FTS5 for other, not-yet-read chunks that might resolve it — the first and only module in the codebase that reads `questions` to influence real system behavior.

**Habituation.** Gap detection now additionally retires a persistent-but-unproductive gap (no genuine evidence growth for 64 consecutive reconfirmation cycles) into a reversible `habituated` state, implementing the empirically established inverted-U relationship between resolvability and curiosity.

#### Stage B Full Write-Path Chain

Nine modules now form a single, ordered, same-cycle-visible chain per real learning cycle:

- **Gap detection** (stageb_gap_detection) — productively populates internal_learning_gaps from observed learning gaps, now including reversible habituation for persistently unresolvable ones.
- **Contradiction detection** (stageb_contradiction_detection) — detects conflicting values between hypotheses and/or already-promoted facts and records them in the existing contradictions table.
- **Hypothesis revision** (stageb_hypothesis_revision) — reverses a hypothesis's role when an independently stronger, contradicting hypothesis is detected.
- **Guarded hypothesis graduation** — promotes an uncertain hypothesis (sentence, lexical-boundary, or relation) into its stable role, with roles competing for a single per-cycle budget via neuromodulator-coupled divisive normalization.
- **Fact promotion** (stageb_fact_promotion) — promotes graduated sentence-/lexical-level hypotheses into `facts`, fully retractable on later revision.
- **Relational binding observation** (phase0b) and **relation promotion** (stageb_relation_promotion) — Modul A above.
- **Ontology cluster observation** and **ontology promotion** — Modul B above.
- **Question promotion** and **question-chunk feedback** — Modul C above.

The chain is ordered so that a contradiction resolved this cycle already causes its corresponding fact/relation to be retracted within the same cycle, and a relation/cluster/question promoted this cycle is already visible to the next module in the same chain.

#### Neuromodulator-Coupled Thresholds

Beyond the pre-existing six-core neuromodulator engine, eleven of the pipeline's own calibrated thresholds and budgets are now directly modulated by one or more of the six core messengers, each using the same symmetric, self-regulating gain (exactly the unmodulated calibrated value at the messenger's own neutral value of 0.5):

| Coupling | Messenger(s) | Grounding |
|---|---|---|
| Gap detection existence gate | Noradrenaline | Aston-Jones & Cohen (2005) adaptive gain theory |
| Gap habituation threshold | Serotonin | Grossman, Bari & Cohen (2022); Hochner et al. (1986) |
| Relational binding existence gate | Noradrenaline | Aston-Jones & Cohen (2005) |
| Relational binding direction threshold | Acetylcholine | Project-internal structural-revision role |
| Hypothesis revision budget | Acetylcholine | Project-internal structural-revision role |
| Contradiction resolution ratio | Noradrenaline | Aston-Jones & Cohen (2005) |
| Graduation role-selection pressure | Acetylcholine | Douchamps et al. (2013); Gómez-Ocádiz et al. (2022) |
| Graduation divisive-normalization temperature | GABA | Katzner, Busse & Carandini (2011) |
| Ontology stability streak | Serotonin | Grossman, Bari & Cohen (2022) |
| Ontology minimum cluster size | Noradrenaline (**self-regulating direction**) | Aston-Jones & Cohen (2005) vs. Shine et al. (2018) |
| Ontology overlap threshold | Dopamine | Kahnt & Tobler (2016); Novicky et al. (2023) |
| Ontology promotion budget | Acetylcholine | Project-internal structural-revision role |
| Question existence gate | Noradrenaline | Aston-Jones & Cohen (2005) |
| Question priority | Dopamine, Acetylcholine | Established gap-closure/curiosity roles |
| Question-chunk feedback boost magnitude | *(inherits question priority)* | Consistency with the upstream signal |
| Phase 7d consolidation gate | Acetylcholine | Gais & Born (2004); Hasselmo & McGaughy (2004) |

One coupling — noradrenaline's effect on the ontology layer's minimum cluster size — is deliberately **not** hardcoded in either theoretically predicted direction. Two competing, independently plausible neuroscience findings disagree on the correct sign for this specific parameter, so the system instead learns the sign from its own real, already-recorded promotion/retraction outcomes (requiring a minimum evidence count in each outcome group before committing to either direction), mirroring the same sliding-threshold-homeostasis philosophy already used elsewhere in the system for meta-parameter learning rates.

### Next Major Step
- Continue observing the full, now nine-module Stage-B write chain over further real cycles, at real production corpus scale.
- Re-measure the sleep/wake rhythm period and the ontology-layer's own self-regulating noradrenaline direction against the real, full production corpus rather than only the smaller synthetic corpora used for this session's own calibration and verification runs.
- Continue calibrating the Lexical Emergence layer's open parameters (context window _k_, entropy threshold) against the real, already-imported corpus.
- Run the Tadros/Bazhenov-motivated catastrophic-forgetting protection test (import a second, topically distinct corpus and measure whether the first corpus's already-stabilized hypotheses/facts/relations/categories are protected, degraded, or reinforced).

### Roadmap

<table>
<tr><th>Stage</th><th>Status</th><th>Gating condition to proceed</th></tr>
<tr><td>**Stage A — Core stability**</td><td>Complete: 100% corpus completion, 11,500+ real cycles, clean 1,500-cycle formal drift run ("konvergiert", zero divergent signals)</td><td>Complete</td></tr>
<tr><td>**Stage B — Guarded graduation**</td><td>Active: Cortisol Stage 2 applied, hypothesis graduation active for all three eligible roles, neuromodulator-coupled role selection</td><td>Ongoing observation</td></tr>
<tr><td>**Autonomous Lexical Emergence (Phase 0)**</td><td>Active, feeding both fact promotion and the Relations layer below once its own evidence threshold clears</td><td>Calibration against real corpus ongoing</td></tr>
<tr><td>**Relations Emergence (Modul A)**</td><td>Active and productive — Gate-and-Direction binding, promotion, retraction all verified over real multi-cycle runs</td><td>Ongoing observation at real production scale</td></tr>
<tr><td>**Ontology Emergence (Modul B)**</td><td>Active and productive — Label Propagation clustering, prototype-anchored stability, promotion/retraction, three neuromodulator couplings (one self-regulating) all verified</td><td>Ongoing observation at real production scale</td></tr>
<tr><td>**Questions Emergence (Modul C)**</td><td>Active and productive — persistence-gated promotion, habituation-aware retraction, full-corpus chunk feedback all verified</td><td>Ongoing observation at real production scale</td></tr>
<tr><td>**Neuromodulator coupling of pipeline thresholds**</td><td>Eleven couplings active across seven modules, each individually literature-grounded and baseline-invariance-verified</td><td>Ongoing; re-calibration against real production corpus pending</td></tr>
<tr><td>**Opening the productive write locks** (Facts / Relations / Ontology / Questions / all four Promotion paths)</td><td>Open (experimental project position)</td><td>Ongoing observation of the full chain; every promoted artifact remains traceable to, and retractable from, its source hypothesis/gap</td></tr>
<tr><td>**Full corpus scaling** (complete German Wikipedia)</td><td>Deliberately deferred</td><td>Order-of-magnitude estimate only, not a commitment</td></tr>
<tr><td>**Vector database evaluation**</td><td>Deliberately deferred per project's own architecture-checkpoint rule</td><td>Only once stable hypothesis identities exist, a concrete semantic-retrieval use case is identified, requirements are measurable, and a read-only/shadow comparison against the SQLite baseline is performed</td></tr>
<tr><td>**Symbolic reasoning plugin** (deterministic, non-LLM rule engine)</td><td>Concept documented, not scheduled</td><td>Gated behind Stage-B graduation and the write-lock roadmap; a validated symbolic rule becoming productive is itself a new class of productive write and must be gated at least as strictly as fact promotion</td></tr>
<tr><td>**Multi-core / multi-process learning**</td><td>Explicitly out of scope for now</td><td>Not currently planned</td></tr>
</table>

### Core Philosophy

Traditional semantic systems often focus on the **what**: storing and retrieving content. BrainStem focuses on the **how**: learning how context, uncertainty, evidence, contradiction, revision, and consolidation interact over time — extended to a character-level layer that learns how recurring units emerge from raw text, a relational layer that learns how those units connect to each other, a categorical layer that learns how connected units group into categories, and a curiosity layer that learns which of its own unresolved gaps are durable enough to motivate further reading. A corpus is treated as training substrate rather than as a static knowledge base.

Core principles:
- **Learning before rules:** no fixed lexical blacklists or hand-authored word-role mappings in the active learning path — including at the character, relational, and categorical level.
- **Errors remain evidence:** unresolved and contradicted hypotheses remain available for later revision; a fact, relation, or category promoted from a hypothesis is retracted, not silently overwritten, if that hypothesis is later reversed.
- **Consolidation before promotion:** every fact, relation, category, and question traces back to a specific source hypothesis or gap that has independently survived the project's own consolidation and graduation/persistence gates.
- **Neuromodulation governs learning:** learning rate, error weighting, revision, confidence, exploration, inhibition, attention, stabilization, and consolidation are state-dependent; the same division of labor is reused, and — new this session — extended with direct, literature-grounded couplings into the pipeline's own thresholds, rather than duplicated for new hypothesis types.
- **Measure before changing:** diagnostics, audits, drift tests, and shadow experiments precede active-control changes; where two neuroscience findings disagree on a specific coupling's direction, the system learns the direction from its own real outcomes rather than assuming either.
- **No hidden legacy paths:** obsolete modules and duplicate learning paths are removed rather than retained as inactive code.

### What is BrainStem really

**BrainStem** is an autonomous software architecture designed for continuous, self-improving data processing and knowledge management. At its core, the system operates through an Autonomous Loop that orchestrates a chain of 39 learning phases to ingest, analyze, and refine information without manual intervention.

The biological terminology used throughout the project's technical documentation, including terms such as "neuromodulators," "sleep," or "homeostasis," is not decorative. These labels are functional designators for mathematical state variables and algorithmic control mechanisms. The values are floats, not molecules. The behavior is biologically inspired, but the implementation is strictly mathematical.

**The system's primary mechanics include:**

**Dynamic Steering Variables:** Digital messenger substances are dynamic meta-parameters that adjust the system's learning rate, error weighting, and exploration strategies in real time, and — as of this session — directly gate eleven specific thresholds and budgets throughout the emergence pipeline.

**Active versus Offline Processing:** The system cycles between active ingestion and an offline optimization phase ("sleep") in which recorded hypotheses are re-evaluated through batch replay and consolidation.

**Character-Level Emergence:** Alongside sentence-level hypotheses, a branching-entropy-driven process observes the raw character stream to propose, and — through the same consolidation/graduation machinery — stabilize, candidate word-boundary units.

**Relational, Categorical, and Curiosity-Driven Emergence:** Beyond individual hypotheses, the system now binds pairs of stable elements into relations via a statistically principled existence-and-direction gate, clusters the resulting relation graph into emergent categories anchored by centrality rather than arbitrary labels, and promotes its own persistent, unresolved information gaps into durable questions that measurably redirect its own reading attention.

**Knowledge Distillation:** By comparing new data against existing stable records, the system filters out inconsistencies and promotes reliable information into its long-term fact/relation/ontology store — while retaining the ability to retract any of them if the underlying hypothesis is revised.

**Equilibrium Control:** Stability monitoring routines act as a feedback mechanism that pulls meta-parameters back into a functional range when the system detects a performance plateau or excessive variance.

**Adaptive Boundaries:** The limits within which the system operates are not hardcoded but self-regulating, expanding or contracting processing thresholds based on the complexity of the data encountered — and, for at least one specific coupling, self-regulating even in *which direction* a neuromodulator should push a threshold, learned from real outcomes rather than assumed.

In summary, the project is a recursive learning engine that uses biologically derived control logic to implement a highly flexible, self-governing system for automated knowledge acquisition, now spanning word-, relation-, category-, and question-level structure discovery.

Every promoted fact, relation, category, and question carries a complete provenance chain, from the final artifact through its source hypothesis or gap, its consolidation cycles, and down to the exact source chunks and documents that justified its creation — and can be automatically retracted if that source is later revised, dissolved, or habituated. There is no black box. If the system states something, it can show why it states it, and it can take it back if the evidence changes.

### Architecture

BrainStem does not operate as a continuously coupled system of differential equations. Instead, it traverses a cyclic state graph: each phase activates at most 2–3 dominant neuromodulators, while the remainder are kept inactive or passive. This sequential architecture prevents interaction cascades and enables deterministic debugging.

#### Two-Stage Data Pipeline

<table>
<tr><th>Stage</th><th>Name</th><th>Description</th></tr>
<tr><td>1</td><td>Inference-free pre-parsing</td><td>A raw corpus such as a Wikipedia ZIM file is extracted, structured, and partitioned into the chunk store before autonomous learning begins.</td></tr>
<tr><td>2</td><td>Autonomous learning</td><td>AutonomousLoop processes prepared chunks while the neuromodulatory, consolidation, and full write-path chain (facts, relations, ontology, questions) reacts to the evolving internal state.</td></tr>
</table>

#### Runtime Chain

Runtime phases are loaded through ki_system/phase_registry.py. The registry defines load order (39 entries), isolates module-loading failures, and verifies the managed-cycle top phase (chain top: Stage-B gapflow runtime contract).

### Digital Neuromodulator Cockpit

BrainStem currently uses **12 digital neuromodulators**. Their values are normalized to [0.0, 1.0] and derived from internal system state under bounded, biologically inspired dynamics and homeostatic constraints.

<table>
<tr><th>Neuromodulator</th><th>Current engineering role</th></tr>
<tr><td>Dopamine</td><td>outcome and gap-closure signal; now also couples question priority and the ontology layer's overlap tolerance</td></tr>
<tr><td>Serotonin</td><td>consolidation and stability signal; now also couples gap habituation resistance and ontology cluster-stability requirements</td></tr>
<tr><td>Glutamate</td><td>excitatory drive associated with exploration and learning activity</td></tr>
<tr><td>GABA</td><td>global inhibition and E/I-balance signal; now also couples the sharpness of divisive-normalization role competition at graduation</td></tr>
<tr><td>Noradrenaline</td><td>error, alarm, and persistent-pressure signal; now also couples five separate existence/resolution gates across the pipeline, one of them (ontology minimum cluster size) with a self-regulating, outcome-learned direction</td></tr>
<tr><td>Acetylcholine</td><td>novelty, attention, and structural-revision signal; now also couples relation direction commitment, hypothesis revision budget, graduation role-novelty pressure, ontology promotion budget, and Phase 7d consolidation gating</td></tr>
<tr><td>Adenosine</td><td>sleep-pressure homeostat</td></tr>
<tr><td>Endocannabinoids</td><td>retrograde gain control</td></tr>
<tr><td>Cortisol</td><td>top-level stability watcher and guarded soft regulator (Stage 2 active)</td></tr>
<tr><td>Histamine</td><td>wake and arousal signal</td></tr>
<tr><td>Orexin</td><td>reading-endurance and curiosity-related drive</td></tr>
<tr><td>BDNF</td><td>activity-dependent growth and consolidation substrate</td></tr>
</table>

GABA regulates **system-level inhibition and competitive sharpness**. It does not identify or suppress individual words, relations, or extraction errors via any word-level mechanism. All 12 displays are connected both statically and at runtime in the GUI.

### Sleep, Consolidation, and Selection

#### Sleep Replay and Critic Gate

Phase 6a performs offline-style replay after the wake path. Phase 6b evaluates replay effectiveness and plasticity adjustments. The critic gate checks whether proposed changes remain consistent enough to be retained; rejected or unstable material remains available as error and revision evidence. The same critic gate is reused, unmodified, by Stage-B hypothesis graduation.

#### Slow-Wave Substructure

Phase 7d adds sub-1-Hz up/down-state processing with stochastic reactivation, adaptive thresholds, activity-dependent participation, survivor and weakening statistics, anchor interleaving, and self-regulating down-selection. Sentence-level, lexical-boundary, and relation hypotheses all share this same candidate pool, distinguished only by their role value. Consolidation activity is now additionally gated by acetylcholine, reflecting the causal, pharmacologically demonstrated role of low cholinergic tone during slow-wave sleep in permitting declarative memory consolidation.

#### E/I State Separation

The E/I path distinguishes Phase-6a drive (glutamate_drive/gaba_drive), active Phase-7c state (glutamate_state/gaba_state), a compatibility mirror for existing readers/GUI components, and a non-applying shadow state for recurrent candidates. This separation prevents Phase 6a from overwriting the active Phase-7c state on the next cycle.

### Safety Locks

As of the current experimental project position, the following paths are open:
- Direct fact, relation, ontology, and question writes.
- Permanent fact/relation/ontology/question promotion, each gated through its own Stage-B graduation or persistence/stability criterion, and each reversible via hypothesis revision, cluster dissolution, or gap closure/habituation respectively.
- Direct Phase-5f/5g/5i experimental writes.
- Direct attention and internal-gap writes, including question-chunk feedback's own attention writes.

This reflects a deliberate, explicitly framed experiment declared as the current project position, undertaken with a full backup as a fallback point — not a relaxation of the project's underlying provenance guarantee, since every artifact remains traceable to, and retractable from, its source. The active architecture continues to use no word blacklists or hard-coded linguistic filters.

### Database and Schema Discipline

BrainStem uses ki_memory.sqlite3 in the project root. The database is created automatically when absent. Schema rules: schema changes must be reflected in the bootstrap in the same delivery; ensure_schema must be idempotent; _self_check_schema must run before writes; every written column must already be declared in SCHEMA_TABLES; compile checks, smoke tests, and intermediate checks are required before delivery; structural changes require a full backup first.

#### Corpus-Preserving Learning Reset

Learning state can be reset without re-importing the corpus. Preserved content includes documents, chunks, FTS data, import state, and configuration. The reset workflow performs a dry run and creates a timestamped database backup before applying changes.

#### Performance Maintenance

Performance indexes are ensured during bootstrap. Bounded pruning is limited to explicitly approved history tables. Active state, Phase-5f/5g/5i data, and other protected tables are excluded from generic pruning.

### Sensory Deprivation and Drift Report

The GUI includes a sensory-deprivation mode that skips new wake/read input while replay, consolidation, and neuromodulatory dynamics continue. It provides start/stop controls, optional cycle limits, per-cycle CSV diagnostics, bounded/downsampled live graphs, signal-level and overall drift verdicts, and fail-safe cleanup when the run completes or is interrupted. The completed 1,500-cycle no-input test remains the current Stage-A stability baseline.

### Running the System

From the project root: `python main.py --gui`

#### Basic Workflow

<table>
<tr><th>Step</th><th>GUI action</th><th>Purpose</th></tr>
<tr><td>1</td><td>Export / Configuration</td><td>Configure the maximum number of articles before import.</td></tr>
<tr><td>2</td><td>Import & Jobs → ZIM Einlesen</td><td>Extract and pre-parse the corpus.</td></tr>
<tr><td>3</td><td>Import & Jobs → Autonom dauerhaft starten</td><td>Start autonomous learning.</td></tr>
<tr><td>4</td><td>Import & Jobs → Autonom stoppen</td><td>Stop autonomous learning cooperatively.</td></tr>
<tr><td>5</td><td>Close the GUI normally</td><td>Wait for active workers instead of terminating them abruptly.</td></tr>
</table>

#### GUI Areas
- Import and Jobs (including the toggleable CSV value logger)
- Export and Configuration
- Drift Report
- Live 12-neuromodulator display, corpus-coverage and cycle-progress indicators, bounded diagnostic logs and graphs, cooperative worker shutdown

The GUI remains an experimental testing interface; individual areas may still be incomplete. A separate, standalone CSV viewer application (toggleable/overlayable curves) is available for offline analysis of logged sessions.

### ZIM Import

A Windows zimdump.exe build and its required DLL files must be placed in the project root next to main.py. Users must provide their own ZIM corpus. The current development corpus is the German Wikipedia categories _Physics_ and _Computer_.

### Academic References

This project builds upon concepts, algorithms, and theoretical frameworks established in the following academic literature:

**Word segmentation and statistical language acquisition**
- **Saffran, Jenny R.; Aslin, Richard N.; Newport, Elissa L.** (1996) _Statistical Learning by 8-Month-Old Infants_. Science.
- **Aslin, Richard N.; Saffran, Jenny R.; Newport, Elissa L.** (1998) _Computation of Conditional Probability Statistics by 8-Month-Old Infants_. Psychological Science.
- **Fló, Ana; Benjamin, Lucas; Palu, Marisa; Dehaene-Lambertz, Ghislaine** (2022) _Sleeping neonates track transitional probabilities in speech but only retain the first syllable of words_. Scientific Reports.
- **Zhikov, Valentin; Takamura, Hiroya; Okumura, Manabu** _An Efficient Algorithm for Unsupervised Word Segmentation with Branching Entropy and MDL_.
- **Dal Ben, Rafael; Toselli Prequero, Lilian; de Hollanda Souza, Débora; Hay, Jessica F.** (2023) _Simultaneous word segmentation and word-referent mapping_. Open Mind. (parallel, mutually reinforcing word-segmentation and relational learning)
- **Räsänen, Okko; Rasilo, Heikki** _Joint word segmentation and referential learning_ (computational model).
- **Yurovsky, Daniel; Yu, Chen; Smith, Linda B.** (2012) _Statistical speech segmentation and word learning in parallel: Scaffolding from child-directed speech_. Frontiers in Psychology.
- **Zhang, Yayun; Yurovsky, Daniel; Yu, Chen** (2015) _Statistical word learning as a continuous, cumulative process_.

**Curiosity, information gaps, and question formation**
- **Loewenstein, George** (1994) _The Psychology of Curiosity: A Review and Reinterpretation_. Psychological Bulletin.
- **Golman, Russell; Loewenstein, George** (2016) _An Information-Gap Theory of Feelings About Uncertainty_. Carnegie Mellon University working paper.
- **Kang, Min Jeong; Hsu, Ming; Krajbich, Ian M.; Loewenstein, George; McClure, Samuel M.; Wang, Joseph Tao-yi; Camerer, Colin F.** (2009) _The Wick in the Candle of Learning: Epistemic Curiosity Activates Reward Circuitry and Enhances Memory_. Psychological Science.
- **Ten, Alexandr; Oudeyer, Pierre-Yves; Sakaki, Michiko; Murayama, Kou** (2025) _The Curious U: Integrating Theories Linking Knowledge and Information-Seeking Behavior_. Open Mind.
- **Modirshanechi, Alireza; Kondrakiewicz, Kacper; Gerstner, Wulfram; Haesler, Sebastian** (2023) _Curiosity-driven exploration: foundations in neuroscience and computational modeling_. Trends in Neurosciences.

**Habituation, dishabituation, and information-gain-driven decay**
- **Ueda, Kazutaka; Sekoguchi, Takahiro; Yanagisawa, Hideyoshi** (2021) _How predictability affects habituation to novelty_. PLoS One.
- **Smart, Matthew; Shvartsman, Stanislav Y.; Mönnigmann, Martin** (2026) _Dynamical principles of habituation across substrates and scales_. Annual Review of Control, Robotics, and Autonomous Systems.
- **Hochner, Binyamin; Klein, Marc; Schacher, Samuel; Kandel, Eric R.** (1986) _Additional component in the cellular mechanism of presynaptic facilitation contributes to behavioral dishabituation in Aplysia_. Proceedings of the National Academy of Sciences.
- **Cohen, Thomas E.; Kaplan, Samuel W.; Kandel, Eric R.; Hawkins, Robert D.** (1997) _A simplified preparation for relating cellular events to behavior: mechanisms contributing to habituation, dishabituation, and sensitization of the Aplysia gill-withdrawal reflex_. Journal of Neuroscience.

**Noradrenaline, arousal, and network topology**
- **Aston-Jones, Gary; Cohen, Jonathan D.** (2005) _An Integrative Theory of Locus Coeruleus-Norepinephrine Function: Adaptive Gain and Optimal Performance_. Annual Review of Neuroscience.
- **Shine, James M.; Aburn, Matthew J.; Breakspear, Michael; Poldrack, Russell A.** (2018) _The modulation of neural gain facilitates a transition between functional segregation and integration in the brain_. eLife.
- **Zerbi, Valerio; et al.** (2019) _Rapid Reconfiguration of the Functional Connectome after Chemogenetic Locus Coeruleus Activation_. Neuron.

**Dopamine, generalization, and precision**
- **Kahnt, Thorsten; Tobler, Philippe N.** (2016) _Dopamine regulates stimulus generalization in the human hippocampus_. eLife.
- **Novicky, Filip; Parr, Thomas; Friston, Karl; Mirza, M. Berk; Sajid, Noor** (2023) _Bistable perception, precision and neuromodulation_. Cerebral Cortex.

**Acetylcholine, novelty, and encoding-versus-retrieval balance**
- **Douchamps, Vincent; Jeewajee, Ali; Blundell, Pam; Burgess, Neil; Lever, Colin** (2013) _Evidence for Encoding versus Retrieval Scheduling in the Hippocampus by Theta Phase and Acetylcholine_. Journal of Neuroscience.
- **Gómez-Ocádiz, Ruy; Trippa, Massimiliano; Zhang, Chun-Lei; Posani, Lorenzo; Cocco, Simona; Monasson, Rémi; Schmidt-Hieber, Christoph** (2022) _A synaptic signal for novelty processing in the hippocampus_. Nature Communications.
- **Hasselmo, Michael E.; McGaughy, Jill** (2004) _High acetylcholine levels set circuit dynamics for attention and encoding and low acetylcholine levels set dynamics for consolidation_. Progress in Brain Research.
- **Gais, Steffen; Born, Jan** (2004) _Low acetylcholine during slow-wave sleep is critical for declarative memory consolidation_. Proceedings of the National Academy of Sciences.

**Serotonin and meta-learning under uncertainty**
- **Grossman, Cooper D.; Bari, Bilal A.; Cohen, Jeremiah Y.** (2022) _Serotonin neurons modulate learning rate through uncertainty_. Current Biology.

**GABA, gain, and stimulus selectivity**
- **Katzner, Steffen; Busse, Laura; Carandini, Matteo** (2011) _GABA_A Inhibition Controls Response Gain in Visual Cortex_. Journal of Neuroscience.

**Divisive normalization**
- **Carandini, Matteo; Heeger, David J.** (2011/2012) _Normalization as a canonical neural computation_. Nature Reviews Neuroscience.

**Category and prototype formation**
- **Rosch, Eleanor** (1973) _Natural categories_. Cognitive Psychology.

**Complementary learning systems and structure extraction**
- **Sun, Weinan; Advani, Madhu; Spruston, Nelson; Saxe, Andrew; Fitzgerald, James E.** (2023) _Organizing memories for generalization in complementary learning systems_. Nature Neuroscience.
- **Singh, Dhairyya; Schapiro, Anna C.** (2026) _A computational account of complementary learning systems_. Philosophical Transactions of the Royal Society B.

**Sleep-dependent consolidation, homeostatic plasticity, and previously referenced principles (unchanged)**
- **Hamilton, William L.** (2020) _Graph Representation Learning_. Morgan & Claypool Publishers.
- **Watkins, Yijing; Kim, Edward; Kenyon, Garrett T.** (2020) _Using Sinusoidally-Modulated Noise as a Surrogate for Slow-Wave Sleep to Accomplish Stable Unsupervised Dictionary Learning in a Spike-Based Sparse Coding Model_. Frontiers in Computational Neuroscience.
- **Tadros, Timothy; Tran, Gia-Bao M.; Krishnan, Giri P.; Bazhenov, Maxim** (2022) _Biologically Inspired Sleep Algorithm for Reducing Catastrophic Forgetting in Neural Networks_.
- **Fischbacher, Thomas; Comsa, Iulia M.; Potempa, Krzysztof; Firsching, Moritz; Versari, Luca; Alakuijala, Jyrki** (2020) _Intelligent Matrix Exponentiation_. arXiv preprint arXiv:2008.03926. (Evaluated; assessed as not relevant to this project's architecture and not adopted.)
- **Butz, Markus; van Ooyen, Arjen** (2013/2014) _Homeostatic structural plasticity – a key to neuronal network formation and repair_. BMC Neuroscience / PLoS Computational Biology.
- **Lee, Kea-Joo K.; Kirkwood, Alfredo** (2019) _Mechanisms of Homeostatic Synaptic Plasticity In Vivo_. Frontiers in Cellular Neuroscience. (sliding-threshold homeostasis, now also underlying the ontology layer's self-regulating noradrenaline direction)
- **Parker, Paul A.; Holan, Scott H.; Ravishanker, Nalini** (2020) _Nonlinear Time Series Classification Using Bispectrum-based Deep Convolutional Neural Networks_. arXiv preprint arXiv:2003.02353.
- **Rončević, Igor; et al.** _A molecule with half-Möbius topology_. Nature Chemistry (Supplementary Materials, SqDRIFT sampling).

```bibtex
@article{aston-jones2005integrative,
  title={An Integrative Theory of Locus Coeruleus-Norepinephrine Function: Adaptive Gain and Optimal Performance},
  author={Aston-Jones, Gary and Cohen, Jonathan D.},
  journal={Annual Review of Neuroscience},
  year={2005}
}
@article{kahnt2016dopamine,
  title={Dopamine regulates stimulus generalization in the human hippocampus},
  author={Kahnt, Thorsten and Tobler, Philippe N.},
  journal={eLife},
  year={2016}
}
@article{grossman2022serotonin,
  title={Serotonin neurons modulate learning rate through uncertainty},
  author={Grossman, Cooper D. and Bari, Bilal A. and Cohen, Jeremiah Y.},
  journal={Current Biology},
  year={2022}
}
@article{katzner2011gaba,
  title={GABA\_A Inhibition Controls Response Gain in Visual Cortex},
  author={Katzner, Steffen and Busse, Laura and Carandini, Matteo},
  journal={Journal of Neuroscience},
  year={2011}
}
@article{carandini2012normalization,
  title={Normalization as a canonical neural computation},
  author={Carandini, Matteo and Heeger, David J.},
  journal={Nature Reviews Neuroscience},
  year={2012}
}
@article{loewenstein1994psychology,
  title={The Psychology of Curiosity: A Review and Reinterpretation},
  author={Loewenstein, George},
  journal={Psychological Bulletin},
  year={1994}
}
@article{shine2018modulation,
  title={The modulation of neural gain facilitates a transition between functional segregation and integration in the brain},
  author={Shine, James M. and Aburn, Matthew J. and Breakspear, Michael and Poldrack, Russell A.},
  journal={eLife},
  year={2018}
}
@article{hamilton2020graph,
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
@article{lee2019mechanisms,
  title={Mechanisms of Homeostatic Synaptic Plasticity In Vivo},
  author={Lee, Kea-Joo K. and Kirkwood, Alfredo},
  journal={Frontiers in Cellular Neuroscience},
  year={2019}
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

### Development Notes
- **Python package:** ki_system
- **Local project folder:** BrainStem
- **Primary runtime:** Python 3.11 on Windows with SQLite
- **Documentation language:** English, German
- **Status:** highly experimental and under mathematical and architectural validation, currently in an explicitly declared full-write-path-open experimental stage, now spanning facts, relations, ontology categories, and questions
- **Engineering discipline:** backup, compile check, schema self-check, smoke test, and rollback planning for structural changes
- **AI-assisted engineering:** development has included collaborative AI assistance. Concept elaboration with ChatGPT, code generation Claude Opus/Sonnet and ChatGPT Deep Thinking, code review NotebookLM, Gemini and Copilot as critics (no sugarcoat mode)

### Claims and Limitations

BrainStem does not claim that every current hypothesis is meaningful or that the system understands language at a human level. The current objective is to establish and validate the mechanisms by which hypotheses are formed, challenged, revised, inhibited, replayed, consolidated, and promoted into and retracted from fact, relation, ontology, and question stores, as well as the mechanisms by which word-like units, relations, categories, and durable questions might emerge from raw statistics and the system's own recorded outcomes.

### Disclaimer

BrainStem is an experimental cognitive-architecture research project. Biological terminology is used as an engineering analogy and design inspiration. The software is not a biological simulation and does not claim neuroscientific equivalence.
