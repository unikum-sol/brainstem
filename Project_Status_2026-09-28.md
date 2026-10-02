# BrainStem RNS-AI — Project Status Report

**Date:** 28 September 2026
**Document type:** Full architectural and functional status description
**Scope:** Every active function, workflow, procedure, scientific reference, and formula currently implemented in the system

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Runtime Architecture](#2-runtime-architecture)
3. [Core Data Model](#3-core-data-model)
4. [Corpus Ingestion and Chunking](#4-corpus-ingestion-and-chunking)
5. [Foundational Observation Layer](#5-foundational-observation-layer)
   - 5.1 [Sentence-Level Raw Observation](#51-sentence-level-raw-observation)
   - 5.2 [Lexical Boundary Observation](#52-lexical-boundary-observation)
   - 5.3 [Relational Binding Observation](#53-relational-binding-observation)
6. [Context Expansion and Strategy Refinement Chain](#6-context-expansion-and-strategy-refinement-chain)
7. [The Digital Neuromodulator System](#7-the-digital-neuromodulator-system)
   - 7.1 [The Six Core Messengers](#71-the-six-core-messengers)
   - 7.2 [Sleep Replay and Meta-Plasticity](#72-sleep-replay-and-meta-plasticity)
   - 7.3 [Effectiveness Measurement and Plasticity Adjustment](#73-effectiveness-measurement-and-plasticity-adjustment)
   - 7.4 [Bias Persistence and Self-Regulating Meta-Parameters](#74-bias-persistence-and-self-regulating-meta-parameters)
   - 7.5 [Saturation Homeostasis and Meta-Metaplasticity](#75-saturation-homeostasis-and-meta-metaplasticity)
   - 7.6 [Adenosine Homeostat](#76-adenosine-homeostat)
   - 7.7 [Endocannabinoid Retrograde Gain Control](#77-endocannabinoid-retrograde-gain-control)
   - 7.8 [Adaptive Boundaries and Excitation/Inhibition Balance](#78-adaptive-boundaries-and-excitationinhibition-balance)
   - 7.9 [Slow-Wave Sleep Substructure](#79-slow-wave-sleep-substructure)
   - 7.10 [Histamine, Orexin, and BDNF](#710-histamine-orexin-and-bdnf)
   - 7.11 [Cortisol Stability Watch](#711-cortisol-stability-watch)
   - 7.12 [Cooperative Core and Sleep/Wake Authority](#712-cooperative-core-and-sleepwake-authority)
8. [The Stage-B Emergence Pipeline](#8-the-stage-b-emergence-pipeline)
   - 8.1 [Gap Detection](#81-gap-detection)
   - 8.2 [Contradiction Detection](#82-contradiction-detection)
   - 8.3 [Hypothesis Revision](#83-hypothesis-revision)
   - 8.4 [Guarded Hypothesis Graduation](#84-guarded-hypothesis-graduation)
   - 8.5 [Fact Promotion](#85-fact-promotion)
   - 8.6 [Relation Promotion](#86-relation-promotion)
   - 8.7 [Ontology Emergence](#87-ontology-emergence)
   - 8.8 [Question Emergence](#88-question-emergence)
   - 8.9 [Question-Chunk Feedback](#89-question-chunk-feedback)
9. [Neuromodulator Couplings Across the Pipeline](#9-neuromodulator-couplings-across-the-pipeline)
10. [Retrieval and Dialogue](#10-retrieval-and-dialogue)
11. [Scientific Literature Index](#11-scientific-literature-index)
12. [Formula Index](#12-formula-index)
13. [Appendix: Full Runtime Load Order](#13-appendix-full-runtime-load-order)

---

## 1. System Overview

BrainStem is a self-learning language-understanding system designed to acquire sentence-, word-, and relation-level structure from an unsegmented text corpus purely through statistical observation, without word lists, grammars, or filters. The system's stated design principle is that every unit of knowledge — a sentence-level hypothesis, a word boundary, a relation between two entities, a category, or a question — begins as a **low-confidence, fully correctable hypothesis**, and only becomes a durable fact, relation, category, or question after surviving a multi-cycle, neuromodulator-gated consolidation process modeled on biological sleep-dependent memory consolidation.

The system is organized as a single, ordered chain of independent Python modules ("phases"), each of which is loaded once at startup and installed into a shared `AutonomousLoop.cycle()` method. Every real learning cycle therefore executes the entire chain, in a fixed order, once. Thirty-nine such phase modules are currently registered and loaded on every startup.

Six "core" digital neuromodulators (dopamine, serotonin, glutamate, GABA, noradrenaline, acetylcholine) plus seven additional signals (adenosine, two endocannabinoids — 2-AG and anandamide —, histamine, orexin, BDNF, and cortisol) are computed every cycle from the system's own real, observed learning statistics, and in turn continuously modulate the thresholds, budgets, and decision criteria used throughout the rest of the pipeline — this is the literal implementation of the project's own design mandate that "digital neuromodulators steer the whole learning process."

---

## 2. Runtime Architecture

### 2.1 The AutonomousLoop chain-of-responsibility pattern

At startup, `phase_registry.py`'s `load_all()` function imports each of the 39 registered phase modules in a fixed order and calls each module's own `autoload()` (or, for a smaller number of legacy modules, `patch_autonomous_loop()`) function. Each such function captures whatever `AutonomousLoop.cycle` currently points to (i.e. the *previous* module's own cycle function, or `None` for the very first module in the chain) into a module-level `_PREV_CYCLE` variable, and then replaces `AutonomousLoop.cycle` with its own `managed_cycle()` function. `managed_cycle()` always calls `_PREV_CYCLE()` first (running every module registered *before* it in the chain), then performs its own module's real work, and returns a nested dictionary combining both results.

The practical consequence is that a single call to `AutonomousLoop.cycle()` — one "real learning cycle" — transitively executes all 39 modules in their registered order, each seeing the fully up-to-date database state left behind by every module that ran immediately before it in the same cycle. `phase_registry.py` records the full load order explicitly and exposes `EXPECTED_TOP_MODULE`, the name of the last-registered module (currently `v8_stageb_gapflow_runtime_contract_release`), which a self-check (`_self_check`) uses to confirm the chain assembled correctly (i.e. `AutonomousLoop.cycle.__module__` really does end on the expected top module, not on some earlier module due to a load failure further up the chain).

### 2.2 Persistence

All state — the corpus, every hypothesis, every neuromodulator value, every promoted fact/relation/category/question, and every phase module's own internal parameters — is stored in a single SQLite database (`ki_memory.sqlite3`), accessed through a shared `Memory` class (`memory.py`) or, in most phase modules, through a direct `sqlite3.Connection`. Every phase module owns a small, explicit `SCHEMA_TABLES`/`DEFAULTS` declaration and an idempotent `ensure_schema()` function that creates any of its own tables/columns that do not yet exist, and adds default configuration values via `INSERT OR IGNORE`. This means every tunable threshold in the system (search radii, budgets, neuromodulator gains, calibration constants) lives as a plain key/value row in the database, not as a hardcoded constant, and can be changed at runtime without a code change.

### 2.3 Write discipline

Every module that can create a durable, user-visible artifact (a fact, relation, category, or question) performs its write inside a SQLite `SAVEPOINT`, re-checks a small set of "protected" table row-counts before and after its own work, and automatically rolls back the entire savepoint if any protected count changed unexpectedly (a defensive invariant against a module accidentally writing to a table it does not own). Every retraction (a fact, relation, or ontology row being withdrawn because its source hypothesis was later reversed, or a cluster dissolved) is a real `DELETE`, but the retraction *event* itself is always additionally recorded in a dedicated, append-only events table, so the full history remains reconstructable even though the live table only ever reflects the current, correct state.

---

## 3. Core Data Model

### 3.1 `context_hypotheses` — the central hypothesis table

Every unit of knowledge the system ever considers — a whole sentence excerpt, a candidate word boundary, or a candidate relation between two already-observed elements — is stored as one row in `context_hypotheses`, sharing exactly the same schema regardless of which of the three observation layers produced it. Each row carries:

- `role` — the current lifecycle stage of this hypothesis (see table below)
- `subject` / `relation_hint` / `object` / `text_excerpt` — the actual observed content
- `confidence` / `uncertainty` — a Bayesian pseudo-count-based pair (see §3.2)
- `evidence_count` — how many times this exact hypothesis has been independently re-observed
- `dopamine`, `serotonin`, `glutamate`, `gaba`, `noradrenaline`, `acetylcholine` — a snapshot of the six core neuromodulator values at the moment this hypothesis was first created
- `signature` — a SHA-1 hash of the hypothesis's own defining content, used to detect "is this the exact same thing being observed again" without a second, separate deduplication mechanism

| Role | Meaning |
|---|---|
| `uncertain_hypothesis` | A newly observed, whole-sentence excerpt, not yet consolidated |
| `stable_hypothesis` | A sentence-level hypothesis that has survived Stage-B graduation |
| `uncertain_lexical_boundary` | A candidate word-boundary position, not yet consolidated |
| `stable_lexical_boundary` | A word-boundary hypothesis that has survived Stage-B graduation |
| `uncertain_relation_hypothesis` | A candidate directed-or-undirected relation between two already-stable elements |
| `stable_relation_hypothesis` | A relation hypothesis that has survived Stage-B graduation |

### 3.2 The Bayesian pseudo-count confidence update

Every time an already-known hypothesis (identified by its own `signature`) is re-observed, its `confidence` and `uncertainty` are recomputed from its own accumulated `evidence_count` using:

```
confidence   = 1 - 1 / (1 + evidence_count)
uncertainty  = 1 / (1 + evidence_count)
```

This asymptotically approaches (but never exactly reaches) `confidence → 1` / `uncertainty → 0` as a hypothesis is repeatedly confirmed, giving every hypothesis a real, continuously informative confidence value rather than a fixed placeholder. This same formula is applied uniformly across all three observation layers (sentence, lexical, relational) and is also reused, in the same functional form, for cluster-stability confidence in the ontology layer (§8.7).

### 3.3 Downstream durable tables

Once a hypothesis survives Stage-B graduation (§8.4), it can be promoted into one of four durable, user-facing tables, each retaining a `source_hypothesis_id` (or equivalent) back-reference to the originating `context_hypotheses` row:

| Table | Populated by | Meaning |
|---|---|---|
| `facts` | Fact Promotion (§8.5) | A graduated sentence-level or lexical-boundary observation |
| `relations` | Relation Promotion (§8.6) | A graduated, directed-or-undirected relation between two elements |
| `ontology` | Ontology Promotion (§8.7) | A `child → parent` category-membership row derived from graph clustering over `relations` |
| `questions` | Question Promotion (§8.8) | A durable, human-readable restatement of a persistent, unresolved information gap |

---

## 4. Corpus Ingestion and Chunking

`ingest.py` supports three source formats: plain text (`.txt`), PDF (`.pdf`, via PyPDF2), and Wikipedia ZIM archives (`.zim`, via the external `zimdump` tool, with per-article extraction and HTML stripping). Regardless of source format, raw text is split into overlapping word-count windows via `chunk_text()`:

```
max_words = 220, overlap = 40
```

i.e. each chunk contains 220 words, and each successive chunk starts 180 words after the previous one's start, so a 40-word tail is shared between consecutive chunks. Every chunk is stored with a unique `import_key` (derived from source path, article title, and chunk index) so re-importing the same source never creates duplicate chunk rows. For ZIM imports specifically, the system persists its own article/chunk cursor position (`get_import_state`/`set_import_state`) so an interrupted import can resume from exactly where it left off, at whole-article granularity, rather than restarting from the beginning.

---

## 5. Foundational Observation Layer

### 5.1 Sentence-Level Raw Observation

**Module:** `v8_context_observation_learning_release.py`

This is the system's primary input funnel. Each real cycle, it seeds `reading_queue` with any not-yet-queued chunk (target: 2000 pending rows), then reads up to 32 pending chunks ordered by attention score and priority, splits each chunk's text into sentences via a simple sentence-boundary regular expression (`(?<=[.!?])\s+|\n+`), and calls `insert_observation()` once per sentence. Each sentence becomes (or re-observes) exactly one `context_hypotheses` row with role `uncertain_hypothesis`, `subject` set to the sentence's own (truncated) text, and `relation_hint`/`object` left empty (populated only much later, by the relational binding layer, §5.3). A companion `context_learning_events` row records every creation/re-observation event together with the full six-core neuromodulator snapshot active at that moment. If a global "sensory deprivation" flag is active (`deprivation_state`), this entire module suspends queue-seeding and new-hypothesis creation for the cycle, allowing the rest of the system (consolidation, promotion) to continue operating on already-observed material without any new sensory input — the computational analogue of sensory deprivation experiments.

### 5.2 Lexical Boundary Observation

**Module:** `v8_phase0_lexical_boundary_observation_release.py`

This module discovers word boundaries directly from the raw, unsegmented character stream, with no dictionary, whitespace-splitting, or grammar of any kind — every character, including spaces, is treated as an undifferentiated symbol in the stream. For a short preceding character context (default length `k=3`), the module maintains a running count, per distinct context, of which character has historically followed it anywhere in the corpus already read (`lexical_context_transitions`). The **local branching entropy** of that per-context distribution is computed via the standard Shannon entropy formula:

```
H(context) = − Σ p(next_char | context) · log2 p(next_char | context)
```

A position in the text is proposed as a word-boundary candidate whenever (a) its own preceding context has already been observed at least `min_observations=8` times (avoiding conclusions from noisy, barely-seen contexts) and (b) its branching entropy clears `entropy_threshold_bits=1.0`. Each accepted boundary candidate becomes (or re-observes) a `context_hypotheses` row with role `uncertain_lexical_boundary`; its `signature` is built from a small, local character window around the boundary position (`k` characters before + `k` characters after, joined by a private separator character), so the *same* recurring local pattern is re-observable across many different chunks, exactly mirroring how the sentence layer re-observes an identical sentence.

The scientific grounding for using branching entropy as a rule-free segmentation signal: Saffran, Aslin & Newport (1996) demonstrated that human infants can segment a continuous artificial speech stream into recurring word-like units from transitional-probability statistics alone, within minutes of exposure; Aslin, Saffran & Newport (1998) confirmed the mechanism specifically responds to transitional probability, not raw co-occurrence frequency; Flo, Benjamin, Palu & Dehaene-Lambertz (2022) showed the same statistical mechanism is already active in sleeping, full-term neonates, i.e. prior to and independent of conscious attention. Zhikov, Takamura & Okumura's branching-entropy-plus-minimum-description-length algorithm is the directly analogous, already-published unsupervised computational method this module's own mechanism is modeled on.

By default, this layer's own hypotheses (`uncertain_lexical_boundary`) are excluded from Phase 7d's own consolidation candidate pool (a flag, `lexical_boundary_pool_isolated`, default `true`), so the lexical layer can accumulate observation statistics for an extended period with a verified zero behavioral change to the pre-existing sentence-hypothesis consolidation pathway, until a separate, deliberate activation step lifts that isolation.

### 5.3 Relational Binding Observation

**Module:** `v8_phase0b_relational_binding_observation_release.py`

This module binds pairs of already-observed, sufficiently well-supported elements (either a `stable_hypothesis` subject, or a word-like span derived from two adjacent lexical-boundary candidates whose own `evidence_count` clears `min_candidate_evidence_count=4`) that co-occur within the *same sentence* into a candidate relation. The mechanism is explicitly a two-stage, purely statistical process:

**Stage 1 — existence gate (symmetric Pointwise Mutual Information).** For every unordered pair of elements observed together at least `min_pair_count=3` times, a symmetric PMI is computed from the pair's own accumulated co-occurrence counters (`relational_cooccurrence_counts`):

```
PMI(A;B) = log2( P(A,B) / (P(A)·P(B)) )
```

Only pairs whose PMI clears `pmi_threshold_bits=1.0` become eligible for a relation hypothesis at all. PMI is used here specifically because it is symmetric by construction (`PMI(A;B) = PMI(B;A)`) and therefore mathematically answers only "is this association stronger than chance frequency alone would predict", never "which direction" — a deliberate methodological choice made after review found that a plain co-occurrence-frequency measure conflates true semantic association with pure collocation frequency (e.g. "Kaffee trinken").

**Stage 2 — direction signal (positional asymmetry).** Only textual position — which of the two elements occurred first within the sentence — is used to propose a direction, since it is the only genuinely asymmetric statistic available (`P(A before B) ≠ P(B before A)` are two distinct, mutually exclusive events). A direction is only committed to once the pair's own accumulated first-position observations exceed `min_direction_observations=6`, and only if the resulting positional skew clears a language-specific threshold: `direction_threshold_de=0.72` for German, `direction_threshold_en=0.62` for English (German's threshold is set higher to reflect its comparatively weaker, V2-topicalization-affected "position implies grammatical role" signal relative to English's more reliable SVO ordering). Below that threshold, the relation remains in an undirected `associated_with` form. The active corpus language is read from a GUI-set setting (`corpus_language`) fresh every cycle.

Both signals are themselves nothing more than additional observation-derived quantities; a generated relation is a low-initial-confidence hypothesis (role `uncertain_relation_hypothesis`), not a decision, and remains correctable through the same contradiction-detection/hypothesis-revision chain (§8.2–8.3) as every other hypothesis. A relation pair's own `signature` (and therefore its lifetime `context_hypotheses` identity) is always built from the canonical, sorted pair of surface forms — independent of the currently-assessed subject/object direction — so a pair whose direction assessment later resolves, or flips, from further evidence is treated as a continued re-observation of the same underlying pair, not a new, disconnected hypothesis.

The design choice to allow binding *before* a lexical-boundary candidate has fully graduated (rather than waiting for full Stage-B graduation of both sides first) is grounded in evidence that word segmentation and relational/referential learning are not sequential stages in human learners but run in parallel and mutually reinforce each other: Dal Ben, Toselli Prequero, de Hollanda Souza & Hay (2023) directly tested this, finding that adult learners who segment continuous speech and cross-situationally map words to referents *at the same time* perform better than learners doing either task alone; Räsänen & Rasilo's computational model further shows word segmentation emerging as a by-product of joint relational/meaning learning rather than needing to complete first; Yurovsky, Yu & Smith (2012) demonstrate the same parallel scaffolding effect directly on child-directed speech; Zhang, Yurovsky & Yu (2015) show statistical word learning is a continuous, cumulative process in which partial, still-uncertain knowledge from earlier observations carries forward and improves later learning.

---

## 6. Context Expansion and Strategy Refinement Chain

Between the raw observation layer and the neuromodulator engine, six modules (`v8_phase5a` through `v8_phase5i`, minus 5e which is documented in §8.1 as it now primarily serves gap closure) form an adaptive reading-strategy chain whose job is to decide, cycle by cycle, which chunks the sentence-observation layer should read next, and how strongly, based on the system's own recent learning outcomes.

- **Phase 5a** aggregates cross-system health metrics (hypothesis counts, gap counts, active-learning decisions, sleep decisions, current `learning_rate`/`error_weight`) into a single per-cycle health snapshot, primarily for diagnostic/monitoring purposes.
- **Phase 5b** refines `exploration_pressure`/`inhibition_level` based on recent average resolution/effectiveness scores, applies a persistent-gap strategy recommendation (`diversify_context_window` / `continue_targeted_learning` / `balanced_observe_and_reread`) per gap, and periodically re-diversifies the top of `reading_queue` (down-weighting repeatedly-read, high-priority "read_candidate" chunks slightly; lifting under-read "pending" chunks).
- **Phase 5c** clusters internal learning questions by type/role and evaluates whether each cluster's own resolution trend is improving, persistent, or regressing, recommending a corresponding follow-up strategy.
- **Phase 5d** performs cross-cutting observation bookkeeping and strategy-memory consolidation across the other Phase 5 modules.
- **Phase 5f** measures the actual effectiveness of a prior context-expansion attempt (did priority/attention actually go up, did the closure delta improve) and adapts the *window radius* used for subsequent expansions accordingly.
- **Phase 5g** selects among concrete context-expansion strategies for a gap — `contrastive_context_window`, `low_overlap_context_window`, `shift_away_from_no_candidate_context` — each defined as a specific pattern of chunk-offset choices around the gap's own anchor chunk, scored via `score = clamp(expected_gain + 0.10·exploration_pressure − 0.08·inhibition_level − 0.15·no_candidate_rate)`, and writes the resulting boosted priority into `reading_queue`/`chunk_attention_scores`.
- **Phase 5h** evaluates, after the fact, how well each previously-selected strategy actually performed, feeding that outcome back into future strategy selection.
- **Phase 5i** further diversifies strategy selection based on the accumulated outcome memory, avoiding repeatedly re-selecting a strategy whose own outcome memory shows it stagnating.

This chain, together with Phase 5e (§8.1's own gap-closure mechanism) and the Stage-B question-chunk feedback module (§8.9), is the complete set of mechanisms that ultimately determine `reading_queue.priority`/`chunk_attention_scores.attention_score`, which the sentence-observation layer (§5.1) consults every cycle to decide what to read next.

---

## 7. The Digital Neuromodulator System

Thirteen distinct digital chemical signals are computed and maintained every real cycle, each modeled functionally on a real biological messenger and each feeding back into the rest of the pipeline's own thresholds and budgets (documented comprehensively in §9). This section describes how each signal is itself computed.

### 7.1 The Six Core Messengers

**Module:** `v8_phase6a_neuromodulated_sleep_replay_and_meta_plasticity_release.py` (computation); read by every other module via the shared `phase6a_neuromodulated_sleep_state` table.

Dopamine, serotonin, glutamate, GABA, noradrenaline, and acetylcholine are together termed the "six core" messengers. Their values are derived from a weighted average of the system's own recent real learning outcomes (drawn from up to 180 replay candidates per cycle — see §7.2) via the following intermediate quantities:

```
persistent_pressure   = clamp(1.0 − avg_closure + avg_overlap·0.35 + (1.0 − avg_outcome)·0.25)
plasticity            = clamp(0.28 + persistent_pressure·0.35 + avg_overlap·0.18 + (1.0 − avg_outcome)·0.15)
exploration_bias       = clamp(0.30 + avg_overlap·0.35 + (1.0 − avg_outcome)·0.20 + avg_no_candidate·0.10)
consolidation_bias     = clamp(0.25 + avg_closure·0.45 + avg_outcome·0.25 − persistent_pressure·0.18)
inhibition_bias        = clamp(0.20 + avg_no_candidate·0.35 + avg_overlap·0.12)
revision_bias          = clamp(0.25 + persistent_pressure·0.40 + (1.0 − avg_outcome)·0.20)
```

and then into the six messengers themselves:

```
dopamine       = clamp(0.25 + avg_outcome·0.45   + avg_closure·0.25)
serotonin      = clamp(0.25 + consolidation_bias·0.55)
glutamate      = clamp(0.30 + exploration_bias·0.55)
gaba           = clamp(0.20 + inhibition_bias·0.60)
noradrenaline  = clamp(0.25 + persistent_pressure·0.45 + avg_overlap·0.15)
acetylcholine  = clamp(0.30 + (1.0 − avg_overlap)·0.25 + revision_bias·0.25)
```

**Tonic/phasic integration.** For four of the six messengers (dopamine, serotonin, noradrenaline, acetylcholine — glutamate/GABA are governed exclusively by Phase 7c's own excitation/inhibition balance, §7.8), the freshly computed value above (the "phasic" value) is blended with a slower-moving "tonic" target published separately by the cooperative sleep/wake authority (§7.12), using a self-regulating `tonic_weight` meta-parameter:

```
final_value = phasic_value + tonic_weight · (tonic_target − phasic_value)
```

This is the literal implementation of the classic tonic/phasic distinction in neuromodulator signaling: a fast-changing, cycle-fresh component and a slower, homeostatically-anchored component blended into one final value.

**Replay candidate selection.** Each cycle, up to 180 candidates are drawn from three sources — open `internal_learning_gaps` rows (ordered by priority, resolution score), recent `phase5g_experiment_outcomes` rows (weak-strategy experiments, ordered to prioritize low-outcome ones), and `context_hypotheses` rows ordered by uncertainty descending — mirroring the classic complementary-learning-systems principle of interleaving already-consolidated ("anchor") material with novel material during replay to avoid catastrophic forgetting of prior learning while still incorporating new information.

### 7.2 Sleep Replay and Meta-Plasticity

Beyond computing the six core values, this same module maintains a pool of "anchor" hypotheses promoted from Phase 7d's own multi-cycle consolidation survivors (`phase6b_anchor_pool`, populated by Phase 6b, §7.3) and mixes them into the replay batch alongside genuinely novel candidates, using a self-regulating novel/anchor ratio:

```
novel_ratio = clamp(0.6 − 0.3·gaba + 0.2·noradrenaline, 0.3, 0.9)
```

i.e. high GABA (inhibition) narrows the fraction of the replay batch spent on novel material (favoring re-consolidation of already-stable anchors), while high noradrenaline widens it (favoring exploration of new material).

### 7.3 Effectiveness Measurement and Plasticity Adjustment

**Module:** `v8_phase6b_sleep_replay_effectiveness_and_plasticity_adjustment_release.py`

This module measures whether a prior replay cycle actually improved outcome/closure/overlap scores (comparing a pre- and post-replay window), classifying the result as a genuine change, a plateau (both deltas within an epsilon band, default `0.005`), or historically unclassified (insufficient fresh data). On a detected plateau, a **plateau-break** adjustment is applied:

```
scale              = clamp(0.85 − 0.10·gaba, 0.55, 0.98)
post_plasticity    = clamp(pre_plasticity · scale)
post_exploration   = clamp(pre_exploration + 0.15·(1 − gaba) + 0.05·noradrenaline)
post_inhibition    = clamp(pre_inhibition  + 0.10·gaba        + 0.05·(1 − dopamine))
post_revision      = clamp(pre_revision    + 0.10·serotonin   + 0.05·acetylcholine)
post_consolidation = clamp(pre_consolidation − 0.05·(1 − effectiveness_score))
```

On a genuinely positive-effectiveness cycle (above a configurable threshold), a **stabilize-gains** adjustment is applied instead:

```
post_consolidation = clamp(pre_consolidation + 0.05·dopamine + 0.05·glutamate)
post_revision      = clamp(pre_revision − 0.03·serotonin)
post_plasticity    = clamp(pre_plasticity + 0.02·dopamine)
```

Every proposed adjustment passes through a **critic gate** before being applied: the proposed new bias values are compared against the most recent active `phase6b_critic_snapshot` baseline; if the largest single deviation (`max_dev`) exceeds a tolerance of `0.15`, a graded penalty is applied (`penalty = clamp((max_dev − 0.15)·2.0, 0, 0.8)`) that partially blends the proposal back toward the baseline rather than applying it outright, unless the underlying "anchor consistency" evidence is itself too weak (`< 0.3`), in which case the adjustment is refused entirely. This is the same critic gate reused, unmodified, by Stage-B hypothesis graduation (§8.4) to decide whether a specific hypothesis's own graduation is currently safe to apply.

This module additionally maintains an anchor pool (promoting any hypothesis that has survived at least 3 distinct Phase 7d consolidation cycles into `phase6b_anchor_pool`), a lightweight **knowledge distillation** step (any anchor whose own stability clears `0.7` and whose replay was measurably effective is recorded into `phase6b_distilled_knowledge` with a confidence blended from stability and effectiveness), and a small set of continual-learning-style metrics (`phase6b_l2m_metrics`: performance maintenance, forward transfer, backward transfer, sample efficiency), including an alert flag raised whenever backward transfer drops below `−0.05` (a proxy for measurable forgetting of previously-stable material).

### 7.4 Bias Persistence and Self-Regulating Meta-Parameters

**Module:** `v8_phase6c_bias_persistence_and_self_regulating_meta_release.py`

Two responsibilities: (1) a **bias persistence bridge** — a fixed set of "sticky" keys (`last_plasticity_level`, `last_exploration_bias`, `last_consolidation_bias`, `last_inhibition_bias`, `last_revision_bias`) that Phase 6b's own plasticity adjustments write into, and that Phase 6a's own next-cycle computation reads back from, so a plasticity adjustment made this cycle persists into the next cycle's own bias inputs rather than being silently recomputed from scratch every time; and (2) hosting every other meta-parameter used throughout the neuromodulator chain (learning rates, deltas, thresholds) as adaptively-regulated, database-backed values rather than hardcoded constants, so the whole chain's own tunable behavior lives in one place and can be inspected/adjusted without a code change.

### 7.5 Saturation Homeostasis and Meta-Metaplasticity

**Module:** `v8_phase6d_saturation_homeostasis_and_meta_metaplasticity_release.py`

This module is the explicit "counter-force" ensuring the self-regulating bias system above cannot drift into permanent, one-sided saturation. Three mechanisms:

**(1) Sliding-threshold homeostasis** (Lee & Kirkwood, 2019): for any tracked bias or meta-control parameter that has remained pinned at the same boundary (its own configured min or max) for a consecutive streak of cycles, once that streak reaches `SATURATION_STREAK_THRESHOLD`, the parameter's own learning rate is adjusted based on whether it has been saturating chronically on the *same* side episode after episode, or oscillating between sides:

```
agreement       = direction_bias · target_direction_bias
chronic_factor  = clamp(1.0 − 0.3·agreement, 0.8, 1.2)
new_learning_rate = clamp(current_lr · (0.7 + 0.2·serotonin) · chronic_factor, min_lr, max_lr)
```

Chronic, same-side saturation dampens the learning rate more aggressively (smaller `chronic_factor`); oscillating saturation dampens it less.

**(2) Controlled bias renormalization** (modeled on Bazhenov-style slow-wave downscaling): once a parameter has both saturated (streak above threshold) *and* the system's own recent replay effectiveness has been flat (zero) for at least 3 consecutive cycles, the saturated value is gently pulled back toward a defined mid-range target:

```
base_pull  = 0.15 + 0.05·min(5, effectiveness_zero_streak − 3)
pull       = clamp(base_pull · (0.6 + 0.6·glutamate) · (1.0 − 0.4·serotonin), 0.05, 0.35)
new_value  = clamp(old_value + (mid_target − old_value) · pull)
```

**(3) Critic-lock protection**: any `phase6b_critic_snapshot` whose own bias values are themselves found at a saturation boundary is refused/deactivated, so the critic gate (§7.3) never anchors its own tolerance check against an already-degenerate baseline.

### 7.6 Adenosine Homeostat

**Module:** `v8_phase7a_adenosine_homeostat_release.py`

Adenosine is modeled as a persistent, gated sleep-pressure signal accumulating during wakefulness and discharging over multiple consecutive sleep cycles (rather than a single-step threshold oscillator). During wake:

```
buildup_rate = 0.08 · (1 + 0.5·wake_activity) · (1.2 − 0.4·acetylcholine)
new_level    = clamp(old_level + buildup_rate)
```

Once the level clears `threshold_high=0.65`, the system enters a gated sleep state; every bias/meta-plasticity parameter currently pinned at its own saturation boundary is pulled toward its mid-range target with:

```
pull = clamp((0.05 + max(0, level−0.65)·(0.25−0.05)/(1−0.65)) · (0.7+0.6·glutamate) · (1−0.3·serotonin), 0.02, 0.4)
```

During sleep, the level discharges geometrically each cycle (`new = old · 0.85`), and the system only exits back to wake once *both* a minimum dwell of `minimum_sleep_cycles=3` cycles has elapsed *and* the level has fallen to or below `threshold_low=0.15` — a two-condition (level + dwell) exit gate that prevents an immediate flicker back to wake the moment the level merely dips below threshold.

### 7.7 Endocannabinoid Retrograde Gain Control

**Module:** `v8_phase7b_endocannabinoid_retrograde_gain_control_release.py`

Two endocannabinoid-style signals, modeled on real retrograde endocannabinoid signaling (release from a postsynaptic-analogue site that dampens presynaptic-analogue drive): **2-AG** is released in response to a detected "postsynaptic overload" condition (`new_2ag = clamp(current + release_gain·trigger_magnitude)`, `release_gain=5.0`) and decays geometrically each subsequent cycle (`decay_rate=0.6`), providing fast, short-lived retrograde dampening; **anandamide** responds instead to a *tonic*, sustained extreme-bias condition and applies a slower, LTD-style corrective pull (`ltd_pull_strength=0.10`) toward baseline. This module is also where the adenosine homeostat's own sleep-entry downscale can be overridden/restored if endocannabinoid state indicates the dampening is no longer warranted.

### 7.8 Adaptive Boundaries and Excitation/Inhibition Balance

**Module:** `v8_phase7c_adaptive_boundaries_and_ei_balance_release.py`

Three components:

**(A) Adaptive boundaries.** The min/max range of any self-regulating meta-control parameter is not fixed: a parameter that repeatedly sticks at its own boundary while the system's own signals indicate it needs more room causes that boundary to expand (bounded by hard outer limits); a parameter that idles well within its current range causes the boundary to contract.

**(B) Sigmoid soft-clipping.** Rather than a hard `[0,1]` clamp (which has zero gradient exactly at the boundary — "gradient death"), most internal regulator dynamics pass through a sigmoid-blended soft clamp that preserves differential sensitivity near the edges:

```
t = (x − lo) / (hi − lo)
soft_clamp(x) = sigmoid-blended interpolation between t and 1/(1+e^(−k(t−0.5))), k = 1/softness (default softness = 0.08),
                only active within `softness` of either edge; identity elsewhere
```

**(C) Reciprocal glutamate–GABA coupling (E/I balance).** This is the single, authoritative computation of the final glutamate/GABA values written back into the shared neuromodulator state, modeling bidirectional excitatory/inhibitory coupling (glutamate drives GABA via feedforward inhibition; GABA in turn dampens glutamate via feedback), the explicit purpose being prevention of runaway mutual excitation ("digital epilepsy"):

```
gaba_post      = soft_clamp(gaba_pre + alpha·glutamate_pre, 0, 1, softness),  alpha = 0.12
glutamate_post = soft_clamp(glutamate_pre − gamma·gaba_pre, 0, 1, softness),  gamma = 0.15
```

### 7.9 Slow-Wave Sleep Substructure

**Module:** `v8_phase7d_slow_wave_sleep_substructure_release.py`

This module implements the actual multi-oscillation consolidation mechanism that decides which hypotheses survive long enough to become eligible for Stage-B graduation (§8.4). Each real cycle in which the system is in a sleep state, a pool of reactivation candidates is assembled from three tracks — already-promoted anchors (Phase 6b's own `phase6b_anchor_pool`), previously-reinforced survivors, and genuinely novel `context_hypotheses` rows (with a guaranteed minimum novel-track quota, so a numerically dominant candidate source can never permanently starve a smaller one) — and then run through `n_oscillations=5` simulated up-state/down-state cycles. Within each oscillation, candidates are selected for reactivation via Efraimidis–Spirakis weighted sampling without replacement, and each reactivated candidate's own up-state activity is computed as:

```
activity = clamp( base_score · (0.6 + 0.5·glutamate) · (1.0 − 0.3·gaba) · (1.0 − ach_gain·(acetylcholine − 0.5)) + noise + anchor_bonus )
```

A candidate is judged "active" this oscillation if its activity clears an adaptive threshold derived from a percentile of the current oscillation's own activity distribution, gated by a self-regulating **selection pressure**:

```
selection_pressure = clamp(0.5 + 0.6·gaba − 0.4·glutamate)
```

After all `n_oscillations` complete, a candidate that both (a) participated in at least `min_participation_ratio=0.4` of oscillations and (b) was active in at least `survival_consistency_ratio=0.6` of the oscillations it participated in is **reinforced** — recorded as a `phase7d_consolidation_survivors` row for this cycle — and any candidate below that bar is **weakened**. A hypothesis must accumulate at least 3 such independent, distinct-cycle survivor rows before it becomes eligible for Stage-B graduation (§8.4).

The acetylcholine term above (`1.0 − ach_gain·(acetylcholine − 0.5)`) implements a specific, causally-demonstrated finding: Gais & Born (2004) showed, in a placebo-controlled human pharmacological study, that artificially raising cholinergic tone during slow-wave sleep completely blocked declarative memory consolidation, while leaving non-declarative learning and waking consolidation unaffected; Hasselmo & McGaughy (2004) supply the mechanism — high acetylcholine suppresses excitatory hippocampal/cortical feedback (favoring new encoding), while low acetylcholine releases that same feedback, permitting the replay this consolidation stage performs. At acetylcholine's own neutral value (0.5) this term is exactly 1.0 (no modulation); it rises toward higher activity as acetylcholine falls below neutral, and falls as acetylcholine rises above neutral.

The overall pool-composition safeguard (a guaranteed minimum quota for the novel/`context_hypotheses` track regardless of how numerous a competing candidate source is) is grounded in the general homeostatic-structural-plasticity principle that a dominant, highly available population must not be allowed to permanently crowd out a smaller one from a shared, limited consolidation resource (Butz & van Ooyen, 2014); the broader simulated-oscillation consolidation design draws on Watkins, Kim & Kenyon's sinusoidally-modulated-noise slow-wave-sleep surrogate and Tadros, Krishnan, Ramyaa & Bazhenov's (2022) biologically-inspired sleep-replay algorithm.

### 7.10 Histamine, Orexin, and BDNF

**Modules:** `v8_phase7e_histamine_wake_arousal_release.py`, `v8_phase7f_orexin_wake_endurance_release.py`, `v8_phase7g_bdnf_growth_consolidation_release.py`

All three signals use the same general pattern: a weighted target is computed from currently-relevant system state, then smoothed toward via an exponential moving average with a self-regulating blend factor `alpha`:

```
level = clamp((1 − alpha)·previous_level + alpha·target)
```

**Histamine** — modeled as the reciprocal wake-arousal antagonist to adenosine — targets a weighted combination of `(1 − adenosine)` and current wake activity:
```
histamine_target = clamp( w_adenosine·(1 − adenosine) + w_wake·wake_activity ) / (w_adenosine + w_wake)
```

**Orexin** — modeled as a wake-endurance / curiosity-sustaining drive — targets a weighted combination of the fraction of the corpus still unread, recent learning-progress, and the current histamine level:
```
orexin_target = clamp( w_unread·unread_fraction + w_progress·progress_norm + w_histamine·histamine ) / (w_unread + w_progress + w_histamine)
```

**BDNF** — modeled as an activity-dependent growth/consolidation-capacity signal — targets a weighted combination of consolidation strength, learning progress, and general activity, and gates a distinct "growth" regime (`bdnf_level ≥ growth_gate=0.6` and `progress_norm ≥ 0.58`) versus a "low" regime:
```
bdnf_target = clamp( w_consolidation·consolidation + w_progress·progress_norm + w_activity·activity ) / (w_consolidation + w_progress + w_activity)
```

### 7.11 Cortisol Stability Watch

**Module:** `v8_phase7cort_stability_watch_release.py`

Cortisol is modeled as an HPA-axis-style allostatic-load signal, computed from a weighted combination of the single largest currently-observed stress signal and a weighted sum of all tracked stress signals:

```
allostatic_load = clamp(0.6·max_stress_signal + 0.4·weighted_sum_of_stress_signals)
cortisol_level  = clamp((1 − alpha)·previous_level + alpha·allostatic_load)
```

The resulting `cortisol_level` classifies the system into a `calm` / `normal` / `elevated` regime against configured thresholds (`load_low`/`load_high`), each with an identified dominant stress signal. This module additionally implements a **guarded soft regulator** ("Stage 2"): once `allostatic_load` is classified as elevated, a small set of recommended corrective nudges are actually applied (not merely observed), each logged with its own reason, driver signal, and pre/post values.

### 7.12 Cooperative Core and Sleep/Wake Authority

**Module:** `v8_cooperative_core_neuromodulator_sleep_authority_release.py`

This module is the top-level integrator that decides the system's own overall sleep/wake state and publishes homeostatic pull targets for four of the six core messengers (dopamine, serotonin, noradrenaline, acetylcholine — glutamate/GABA remain Phase 7c's own exclusive responsibility, §7.8). Reading the current values of all other signals described above, it computes:

```
arousal                 = clamp(0.28·histamine + 0.25·orexin + 0.20·noradrenaline + 0.12·acetylcholine + 0.15·cortisol)
inhibitory_readiness    = clamp(0.55·gaba + 0.25·inhibition_bias + 0.20·(1 − glutamate))
consolidation_readiness = clamp(0.45·consolidation_bias + 0.30·bdnf + 0.25·serotonin)
arousal_release         = 1.0 − arousal
sleep_score             = clamp(0.35·adenosine_pressure + 0.25·arousal_release + 0.20·inhibitory_readiness
                                 + 0.12·consolidation_readiness + 0.08·(1.0 − cortisol))
```

The system transitions from wake to sleep once `sleep_score ≥ enter_threshold=0.62` (and a minimum dwell in the current state has elapsed), and from sleep back to wake once `sleep_score ≤ exit_threshold=0.42` (with the same minimum-dwell requirement) — a hysteresis band plus dwell requirement that prevents rapid oscillation between states. This module also publishes the four non-E/I messengers' own tonic pull targets (consumed by Phase 6a's tonic/phasic blend, §7.1):

```
dopamine_target      = clamp(0.20 + 0.34·outcome + 0.18·exploration_bias + 0.16·(1 − persistent_pressure) + 0.12·(1 − cortisol))
serotonin_target     = clamp(0.22 + 0.38·consolidation_bias + 0.20·(1 − cortisol) + 0.12·outcome + 0.08·inhibitory_readiness)
noradrenaline_target = clamp(0.12 + 0.30·persistent_pressure + 0.25·histamine + 0.18·orexin + 0.15·cortisol)
acetylcholine_target = clamp(0.18 + 0.33·revision_bias + 0.22·histamine + 0.17·orexin + 0.10·exploration_bias)
```

---

## 8. The Stage-B Emergence Pipeline

Stage-B is the collective name for the nine modules that take already-observed hypotheses through consolidation, contradiction resolution, graduation, and promotion into durable facts, relations, categories, and questions. All nine modules run in a fixed, same-cycle-visible order (gap detection → contradiction detection → hypothesis revision → graduation → fact promotion → relational binding observation → relation promotion → ontology cluster observation → ontology promotion → question promotion → question-chunk feedback), so that, for example, a contradiction resolved this cycle already causes its corresponding fact to be retracted within the very same cycle, not one cycle later.

### 8.1 Gap Detection

**Module:** `v8_stageb_gap_detection_release.py`

This module surfaces two independent kinds of information gap directly from the existing `context_hypotheses` population, reusing already-observed signals rather than inventing a new scoring mechanism:

**Heuristic A — stalled hypotheses.** A hypothesis (sentence-level or lexical-boundary, role `uncertain_hypothesis`/`uncertain_lexical_boundary`) that has accumulated at least `stalled_min_evidence_count=20` observations without ever graduating is surfaced as a `stalled_uncertain_hypothesis` gap — something the system keeps re-encountering without ever resolving further.

**Heuristic B — contested pairs.** Two *different*, already-stable hypotheses that share the exact same normalized subject but carry different text excerpts are surfaced as a `contested_subject_multiple_excerpts` gap — a plausible sign of tension between two competing, already-consolidated observations about "the same thing", deliberately restricted to already-stable material (comparing two barely-observed, still-uncertain hypotheses would be noise, not signal). This heuristic supplies contradiction detection (§8.2) with the pairs it needs to examine.

Every gap's own `evidence_count` grows by exactly 1 each time it is independently reconfirmed present in a later, separate gap-detection cycle — this reconfirmation counter, not the mere existence of a gap, is the persistence signal question promotion (§8.8) requires before treating a gap as durable enough to motivate a question.

**Habituation.** A gap that has gone `habituation_max_stagnant_cycles=64` consecutive reconfirmation cycles without any genuine growth in its own underlying `evidence_count` (i.e. the same stalled hypothesis or contested pair keeps being re-observed, but never actually gains new supporting evidence) is retired into a terminal `habituated` status — implementing the empirically well-established inverted-U relationship between resolvability and curiosity (Kang, Hsu, Krajbich, Loewenstein, McClure, Wang & Camerer, 2009; synthesized further by Ten, Oudeyer, Sakaki & Murayama, 2025) and habituation as a process driven specifically by absence of new information gain, not by elapsed time alone (Ueda, Sekoguchi & Yanagisawa, 2021). Habituation is fully reversible: should a habituated gap later show genuine evidence growth again, it dishabituates back to `open` — the same reversible "renewed salience" property real habituation exhibits (Smart, Shvartsman & Mönnigmann, 2026, formalize this as fading-memory dynamics composed with a static nonlinearity). A gap whose underlying hypothesis has since positively graduated is instead marked `closed` (see §8.4/8.5/8.6), which takes precedence over habituation.

### 8.2 Contradiction Detection

**Module:** `v8_stageb_contradiction_detection_release.py`

For every open `contested_subject_multiple_excerpts` gap surfaced by gap detection, this module determines which of the two (or more) competing, already-stable hypotheses is currently better supported, using only already-existing signals (`evidence_count`, `uncertainty`) — no new scoring mechanism. A pair is judged **decisively** resolvable whenever one side's `evidence_count` is at least `decisive_evidence_ratio=3.0` times the other's, in which case evidence-count dominance alone is treated as sufficient regardless of what `uncertainty` might separately suggest (since repeated, independent reconfirmation is this project's own most directly meaningful "how often has this actually been confirmed" signal). For genuinely close cases (below that ratio), the pair falls back to requiring `uncertainty` to independently agree with the same ordering before being judged resolvable at all; otherwise it remains `ambiguous`. Each contested pair is recorded as one row in `contradictions` (subject, both competing values, resolution status), and both sides' `hypothesis_stability_scores.conflict_count` are incremented — the "losing" side is never silently discarded, only re-scored, since a hypothesis is never deleted and remains open to future re-evaluation if new evidence later reverses which side is better supported.

### 8.3 Hypothesis Revision

**Module:** `v8_stageb_hypothesis_revision_release.py`

This module consumes contradictions already marked `resolvable` by contradiction detection (it does not re-derive which side is weaker) and reverses the *losing* hypothesis's own role back to its pre-graduation uncertain form (`stable_hypothesis → uncertain_hypothesis`, `stable_lexical_boundary → uncertain_lexical_boundary`, `stable_relation_hypothesis → uncertain_relation_hypothesis`), resetting its confidence/uncertainty to the same fresh-observation baseline (`0.0`/`1.0`) used at initial creation. A `hypothesis_revisions` row records the reversal (old/new role, old/new confidence/uncertainty, and the triggering contradiction), giving this decision the same durable, inspectable audit trail already required for graduation itself. This is the mechanism that gives the whole system its "no knowledge is permanently fixed" guarantee: any fact, relation, or category ultimately derived from a hypothesis remains correctable for as long as that hypothesis could, in principle, be contradicted again by future evidence. This module's own revision budget (how many reversals may be applied per real cycle) is a small, deliberately conservative constant, mirroring the graduation module's own promotion-budget convention.

### 8.4 Guarded Hypothesis Graduation

**Module:** `v8_stageb_guarded_hypothesis_graduation_release.py`

This module graduates at most one uncertain hypothesis per real cycle into its corresponding stable role, gated by three independent, layered safeguards:

1. **Consolidation survival** — the hypothesis must already have accumulated at least `minimum_7d_survivals=3` distinct Phase 7d consolidation-survivor rows (§7.9).
2. **Warm-up** — no graduation is attempted at all before `warmup_cycles=50` real cycles have elapsed since startup.
3. **The critic gate** — the same gate described in §7.3: a proposed graduation is compared against the most recent critic baseline and refused or penalized if it would represent too large a jump in the system's own bias state, or if anchor consistency evidence is too weak.

**Role selection via divisive normalization.** Three eligible roles (`uncertain_hypothesis`, `uncertain_lexical_boundary`, `uncertain_relation_hypothesis`) compete for the single graduation slot available each cycle. Each role's raw "pressure" is the count of its own currently-eligible candidates. Two neuromodulator-driven adjustments are applied before the final selection (see §9 for the full derivation of both):

```
effective_pressure(role) = raw_pressure(role) · max(0, 1 + ach_gain·(acetylcholine − 0.5)·novelty(role))
share(role)  = effective_pressure(role)^temperature / (Σ effective_pressure^temperature + sigma)
temperature  = 1.0 + gaba_gain·(gaba − 0.5)
```

where `novelty(role) = 1 − (role's own historical graduation count / total historical graduations across all roles)`. One role is then drawn via Efraimidis–Spirakis weighted sampling using these shares, and that role's own single top-ranked eligible candidate (by survived-cycles, then consistency) receives the graduation attempt this cycle. This entire mechanism is a direct application of divisive normalization (Carandini & Heeger, 2011/2012) — described in the neuroscience literature as "the canonical neural computation" for fairly allocating a single, scarce resource across competing populations in proportion to each population's own current demand.

### 8.5 Fact Promotion

**Module:** `v8_stageb_fact_promotion_release.py`

This is the sole module that ever writes to the `facts` table. It reads graduation events restricted to `new_role='stable_hypothesis'` (sentence-level and lexical-boundary graduations only — relation graduations are exclusively Relation Promotion's own responsibility, §8.6) that have not yet been turned into a fact, and creates exactly one fact per graduated hypothesis, reusing the hypothesis's own already-observed `subject`/`text_excerpt`/`confidence` verbatim. The fact's `relation` column is always written as the fixed, explicit placeholder literal `"observed_as"` — an intentionally honest label: the system has recorded that this subject was observed with this content, not asserted any specific linguistic relation type. On the reverse path, this module also reads `hypothesis_revisions` events (§8.3) and deletes the corresponding fact whenever its own source hypothesis is reversed — the concrete mechanism by which a promoted fact remains fully correctable rather than permanently fixed. It additionally closes the corresponding `internal_learning_gaps` row (marking it `closed`) the moment its own hypothesis graduates into a durable fact, and reopens that same gap (`status → open`) if the fact is later retracted.

### 8.6 Relation Promotion

**Module:** `v8_stageb_relation_promotion_release.py`

Structurally identical to Fact Promotion, but restricted to `new_role='stable_relation_hypothesis'` graduation events, writing into the `relations` table (`source`, `relation`, `target`, `confidence`) using the hypothesis's own already-resolved `subject`/`relation_hint`/`object` fields (populated by Relational Binding Observation, §5.3). A relation whose own direction never resolved (empty `object`, still in the undirected `associated_with` form) is deliberately skipped rather than promoted with a fabricated target — it remains visible via `context_hypotheses` itself and can still be promoted on a later cycle once further evidence resolves a direction. The same retraction-on-reversal and gap-closure/reopen mechanism described for Fact Promotion applies here identically.

### 8.7 Ontology Emergence

**Modules:** `v8_stageb_ontology_cluster_observation_release.py` (observation) and `v8_stageb_ontology_promotion_release.py` (promotion)

This is the mechanism by which categories emerge purely from graph connectivity structure over the already-promoted `relations` table, with no word lists or grammar involved at any point.

**Observation.** An undirected graph is built with one node per distinct `relations.source`/`.target` surface form and one edge per `relations` row. This graph is clustered via standard asynchronous **Label Propagation** (each node iteratively adopts the label held by the plurality of its own neighbors, ties broken deterministically, for up to `lp_max_iterations=20` iterations or until convergence). Clustering over already-promoted relations, rather than over raw facts (whose own `relation` column is always the placeholder `"observed_as"`), is grounded in Complementary Learning Systems theory: Sun, Advani, Spruston, Saxe & Fitzgerald (2023) show that neocortical structure-extraction only benefits generalization when it consolidates over *already* hippocampally-extracted regularities, not raw episodic traces directly; Singh & Schapiro (2026) similarly describe structure learning as operating on a slower pathway that extracts regularities across already-consolidated experiences, distinct from and downstream of fast individual-episode encoding.

Because Label Propagation's own tie-breaking order is non-deterministic cycle to cycle, cluster identity across cycles is anchored not to LP's own arbitrary per-cycle label but to each cluster's own **prototype** — the member with the highest in-cluster degree (the Rosch, 1971/1973, prototype-theory analogue: categories have a graded structure around a typical, central member, not a sharp defining boundary). A cluster's membership this cycle is compared against that same prototype's last-recorded membership via Jaccard overlap; overlap at or above `overlap_threshold=0.4` counts as "the same cluster reappeared" (streak increments); otherwise the streak resets to 1. A prototype that does not reappear as a prototype at all this cycle has its streak explicitly reset to 0, the signal ontology promotion uses to trigger retraction of anything already promoted under that prototype.

**Promotion.** Once a cluster's own reconfirmation streak reaches `stability_streak_required=3`, every non-prototype member is promoted into the `ontology` table as one `child → parent` row, with the prototype as parent, confidence computed via the same Bayesian pseudo-count formula used throughout the system (`confidence = 1 − 1/(1+streak)`), and `relation` written as the fixed, explicit placeholder literal `"is_a"` — mirroring fact promotion's own honest placeholder convention: the system has structurally identified a graded group-membership relationship via connectivity and centrality, but has not parsed or inferred any actual linguistic category name. A cluster whose streak later resets to 0 (dissolved) has every one of its previously-promoted `ontology` rows retracted, mirroring the retraction-on-reversal guarantee already implemented for facts and relations.

### 8.8 Question Emergence

**Module:** `v8_stageb_question_promotion_release.py`

This module is the sole consumer of `internal_learning_gaps`: it promotes a persistent, repeatedly-reconfirmed gap into the existing `questions` table, without needing any new kind of observation of its own. This directly implements Loewenstein's (1994) Information-Gap Theory of curiosity — curiosity is a form of cognitively-induced deprivation arising from the perception of a *specific, already-recognized* gap in knowledge, not diffuse ignorance — and Golman & Loewenstein's (2016) elaboration of the same theory. A gap becomes eligible for promotion once its own `resolution_attempts` (the reconfirmation counter maintained by gap detection, §8.1) clears `min_resolution_attempts_for_question=15`, a value calibrated to correspond to roughly one full measured sleep/wake rhythm period rather than an arbitrary constant.

**Question text.** Per the project's own "no pre-given sentence template, no grammar" principle, question text is never a generated natural-language sentence. Instead it is a fixed, explicit, non-linguistic marker prefix (`unresolved_hypothesis::` or `unresolved_contradiction::...::vs::...`) followed only by the referenced hypothesis's own already-observed, verbatim surface text — mirroring the same honest-placeholder convention already used for fact promotion's `"observed_as"` and ontology promotion's `"is_a"`.

**Resolution.** A promoted question is automatically retracted (`status → resolved`, never deleted) the moment its own source gap either closes (the underlying hypothesis positively graduates into a fact/relation, §8.5/8.6) or habituates (§8.1) — both real, independently-verifiable state transitions on the gap itself, polled every cycle.

### 8.9 Question-Chunk Feedback

**Module:** `v8_stageb_question_chunk_feedback_release.py`

This module is the mechanism by which a promoted question's own salience actually influences what the system reads next — closing the loop from "the system has noticed a specific gap" to "the system's own reading behavior responds to that gap". For every still-open question, two complementary boosts are applied to `reading_queue.priority`/`chunk_attention_scores.attention_score`, both written exclusively via `MAX(existing, new)` so this module can only ever raise a chunk's priority relative to what it already was, never override another module's own judgment:

**(1) Source-chunk boost.** The exact chunk where the question's underlying, still-unresolved hypothesis was first observed receives a boost toward a calibrated ceiling — the direct, literature-supported hypothesis that rereading the source text is the most immediate way to gather disambiguating evidence.

**(2) Full-corpus search boost.** The gap's own verbatim surface text (the same text used for the question itself) is used to search the *entire* corpus via SQLite FTS5, so a genuinely unread document elsewhere in the corpus that may hold the disambiguating answer can also be found and modestly boosted — addressing the specific limitation that source-chunk-only rereading is blind whenever the answer lies elsewhere. Candidate target chunks are pre-selected via FTS5's own `bm25()` ranking (a cheap index-based narrowing step), then finally accepted only if they share at least `fts_min_matched_terms=2` distinct real tokens with the query (a corpus-size-independent precision safeguard, since raw `bm25()` magnitude alone was found to behave unreliably as a sole acceptance criterion at small corpus sizes).

**Boost magnitude scaling.** Both boosts' own target magnitude are themselves scaled by the specific question's own already-neuromodulator-modulated `priority` value (see §9), interpolating between a non-zero floor (`priority_scaling_floor=0.30`) and the calibrated ceiling — so a highly salient question receives close to the full boost, while a barely-salient, near-habituation question receives a correspondingly weaker one.

**Global decay.** At the end of every cycle, every `reading_queue`/`chunk_attention_scores` row not freshly touched in that same cycle has its priority/attention multiplied by a small decay factor (`global_decay_factor=0.985`, i.e. 1.5% per cycle), floored at `global_decay_floor=0.05` so it shrinks toward, but never fully to, zero — a general anti-starvation mechanism ensuring a chunk boosted once cannot dominate reading priority indefinitely without ongoing, fresh confirmation.

The overall safety of coupling attention allocation to a curiosity/information-gap signal at all — rather than risking the well-documented "noisy-TV problem" (an agent that becomes stuck on unpredictable but worthless novelty; Modirshanechi, Kondrakiewicz, Gerstner & Haesler, 2023) — rests specifically on this module only ever reading `status='open'` questions: a question whose underlying signal turns out to be persistent, unresolvable noise stops receiving any further boost the moment gap detection's own habituation mechanism (§8.1) retires it.

---

## 9. Neuromodulator Couplings Across the Pipeline

Beyond the neuromodulator engine's own internal computation (§7), eleven of the pipeline's own calibrated thresholds and budgets (spread across seven modules in Slices 1–3 of the Stage-B pipeline) are themselves directly modulated by one or more of the six core messengers. Every such coupling shares the same design convention: a symmetric, self-regulating gain of the form

```
effective_value = base_value · (1 + gain · (0.5 − messenger_value))     [lowering couplings]
effective_value = base_value · (1 + gain · (messenger_value − 0.5))     [raising couplings]
```

which is, by construction, *exactly* equal to the unmodulated `base_value` whenever the driving messenger sits at its own neutral value of 0.5, and only deviates from that calibrated base value in proportion to how far the real, currently-observed messenger value has moved away from neutral.

| Module | Parameter | Messenger | Direction at elevated messenger level | Scientific grounding |
|---|---|---|---|---|
| Gap Detection (§8.1) | `stalled_min_evidence_count` (existence gate) | Noradrenaline | Lower (more receptive to weaker candidates) | Aston-Jones & Cohen (2005) — tonic locus-coeruleus noradrenaline signals disengagement from the current task and exploratory search for alternatives |
| Gap Detection (§8.1) | `habituation_max_stagnant_cycles` | Serotonin | Higher (more resistant to habituating) | Grossman, Bari & Cohen (2022) — dorsal raphe serotonin neurons track environmental uncertainty and directly control adaptation rate; Hochner, Klein, Schacher & Kandel (1986) and Cohen, Kaplan, Kandel & Hawkins (1997) — serotonin drives a facilitatory process that specifically counteracts synaptic-depression-based habituation |
| Relational Binding (§5.3) | `min_pair_count`, `pmi_threshold_bits` (existence gate) | Noradrenaline | Lower | Aston-Jones & Cohen (2005), same mechanism as above |
| Relational Binding (§5.3) | `direction_threshold_de`/`_en` | Acetylcholine | Lower (commits to a direction more readily) | This project's own internally-established role for acetylcholine as the structural-revision/structural-encoding signal (§7.1's own `revision_bias → acetylcholine` term) — assigning a directional interpretation to a pair is itself a structural-encoding decision |
| Hypothesis Revision (§8.3) | `revision_budget` | Acetylcholine | Higher (more revisions permitted per cycle) | Same internally-established acetylcholine role as above — this module is the literal structural-revision mechanism that role was designed to describe |
| Contradiction Detection (§8.2) | `decisive_evidence_ratio` | Noradrenaline | Lower (resolves contested pairs more readily) | Aston-Jones & Cohen (2005), same mechanism |
| Guarded Graduation (§8.4) | Per-role pressure (novelty bias) | Acetylcholine | Roles historically graduated less often receive a proportionally larger boost | Douchamps, Jeewajee, Blundell, Burgess & Lever (2013) and Gómez-Ocádiz, Trippa, Zhang, Posani, Cocco, Monasson & Schmidt-Hieber (2022) — acetylcholine shifts hippocampal circuit dynamics toward encoding genuinely novel information |
| Guarded Graduation (§8.4) | Divisive-normalization temperature | GABA | Higher GABA sharpens competition (favors the already-dominant role more strongly); lower GABA flattens it | Katzner, Busse & Carandini (2011) — intact GABA_A inhibition sharpens neural stimulus selectivity; blocking it broadens/flattens the response profile |
| Question Promotion (§8.8) | `min_resolution_attempts_for_question` | Noradrenaline | Lower | Aston-Jones & Cohen (2005), same mechanism |
| Question Promotion (§8.8) | `priority` of the promoted question itself | Dopamine, Acetylcholine | `priority *= 1 + 0.3·(dopamine−0.5) + 0.3·(acetylcholine−0.5)`, bounded so neither messenger alone can dominate or invert the underlying, evidence-derived priority | Dopamine's already-established project-wide role as a gap-closure/reward-prediction-adjacent signal; acetylcholine's established curiosity/attention role |
| Question-Chunk Feedback (§8.9) | Boost magnitude (source-chunk and full-corpus) | *(inherits the already-dopamine/acetylcholine-modulated question priority above)* | Scales continuously between a floor and the calibrated ceiling in proportion to the specific question's own priority | Ensures the upstream dopamine/acetylcholine signal that already determines *which* question is processed first is not discarded when determining *how strongly* that question's own source/target chunks are boosted |
| Ontology Cluster Observation (§8.7) | `stability_streak_required` | Serotonin | Lower (less reconfirmation required to trust stability) | Grossman, Bari & Cohen (2022), same mechanism as the gap-detection habituation coupling above |
| Ontology Cluster Observation (§8.7) | `overlap_threshold` | Dopamine | Lower (more cross-cycle member churn still counts as "the same cluster") | Kahnt & Tobler (2016) — a causal, pharmacological human study: D2-receptor blockade measurably narrowed the brain's own stimulus-generalization gradient; dopamine directly controls how much deviation from an already-learned pattern is still tolerated as "the same thing" — near-literally the question `overlap_threshold` answers. Independently, convergently modeled by Novicky, Parr, Friston, Mirza & Sajid (2023) as one of three precision parameters (alongside acetylcholine and noradrenaline) governing same-vs-different perceptual/categorical stability judgments |
| Ontology Promotion (§8.7) | `ontology_promotion_budget` | Acetylcholine | Higher | Same internally-established acetylcholine role as Hypothesis Revision's own budget above — promoting a cluster into a durable ontology row is itself a structural-encoding decision |

### 9.1 Self-Regulating Direction: Noradrenaline and `min_cluster_size`

One coupling is deliberately built differently from the pattern above. Two independent, competing neuroscience findings speak to whether *elevated* noradrenaline should lower or raise the minimum size a candidate cluster must reach before being trusted:

- Aston-Jones & Cohen's (2005) generic exploration/exploitation account would predict elevated noradrenaline lowers the bar (more receptive to smaller candidate clusters), matching the direction used for every other noradrenaline-coupled existence gate in this system.
- Shine, Aburn, Breakspear & Poldrack (2018) and Zerbi, Jones, Hall, Nagtegaal & Herzog (Zerbi et al., 2019) instead describe elevated neural gain (the level at which noradrenaline acts) as driving neural networks from a segregated topology (many small, specialized modules) toward an integrated one (fewer, larger, densely-interconnected modules) — implying elevated noradrenaline should instead *raise* the bar, since small clusters become comparatively more likely to be spurious in a more densely-merged regime.

Rather than assuming either direction, this specific coupling's own sign is **learned from the system's own real, already-recorded promotion/retraction outcomes**: the average noradrenaline value recorded at the moment of promotion is tracked separately for clusters later retracted ("failed") versus clusters that have survived at least `na_direction_min_survival_window=10` cycles without retraction ("survived"). Only once each group has independently accumulated at least `na_direction_min_evidence_per_group=5` real outcomes, and the two groups' average noradrenaline values differ by more than `na_direction_margin=0.05`, does the coupling commit to a direction (whichever group's own average noradrenaline is higher determines which theory's prediction the system's own real data currently supports); otherwise the coupling remains at its safe, no-modulation default. This mirrors the same sliding-threshold-homeostasis philosophy already implemented for meta-parameter learning rates (§7.5), applied here to let real outcome data — not either paper alone — decide a genuinely disputed empirical direction.

---

## 10. Retrieval and Dialogue

**Modules:** `search.py`, `dialogue.py`, `memory.py`, `gui_app.py`/`user_gui.py`

Independent of the learning pipeline described above, the system exposes a hybrid retrieval interface over the same corpus and durable knowledge tables. `semantic_search()` combines three complementary retrieval methods and merges their results:

1. **Full-text search** via SQLite's FTS5 extension, querying an OR-join of the query's own tokenized terms, ranked by the standard `bm25()` relevance score.
2. **Phrase matching** — a direct substring search for the query's own normalized phrase against chunk text and metadata, with a relevance boost when the phrase appears within a chunk's own source-article title.
3. **Bag-of-words cosine similarity** — a fallback pass computing cosine similarity between the query's own term-frequency vector and every not-yet-matched chunk's own term-frequency vector, used to fill out the result set once the first two methods are exhausted.

`answer()` builds on this by running `semantic_search()`, extracting and scoring individual sentences from the top hits (a sentence's score is the count of query terms it contains, plus a bonus if it contains the query's own full phrase), and composing a short extractive answer from the top-scoring sentences, together with the underlying source chunks for full provenance.

`DialogueManager` wraps `answer()` into a simple conversational interface: each question is answered, its topic is normalized (`normalize_topic_from_question()`), and — for a writable `Memory` instance — the conversation turn and its topic context are persisted via `memory.add_conversation()`/`memory.set_topic_context()`, so a later turn can retrieve the most recent topic context if needed. Against a read-only `Memory` (as used by the standalone viewer GUI, `user_gui.py`), persistence is skipped entirely as an explicit, expected branch.

The GUI (`gui_app.py`) additionally exposes: real-time messenger/regime displays for all thirteen digital neuromodulators; a continuously-updating CSV value logger and a companion standalone CSV viewer executable for offline graphical analysis of any tracked metric over time; corpus import controls (plain text, PDF, ZIM) with resumable, cancelable progress reporting; and direct read access to every durable table (facts, relations, ontology, questions) for manual inspection and export.

---

## 11. Scientific Literature Index

The following peer-reviewed and otherwise published sources are directly cited as the grounding for specific mechanisms described in this document.

**Word segmentation and statistical language acquisition**
- Saffran, J. R., Aslin, R. N., & Newport, E. L. (1996). Statistical learning by 8-month-old infants. *Science*, 274(5294), 1926–1928.
- Aslin, R. N., Saffran, J. R., & Newport, E. L. (1998). Computation of conditional probability statistics by 8-month-old infants. *Psychological Science*, 9(4), 321–324.
- Flo, A., Benjamin, L., Palu, M., & Dehaene-Lambertz, G. (2022). Sleeping neonates track transitional probabilities in speech but only retain the first syllable of words. *Scientific Reports*, 12, 4391.
- Zhikov, V., Takamura, H., & Okumura, M. Unsupervised word segmentation using branching entropy and MDL (referenced computational method).
- Dal Ben, R., Toselli Prequero, L., de Hollanda Souza, D., & Hay, J. F. (2023). Simultaneous word segmentation and word-referent mapping. *Open Mind*, 7.
- Räsänen, O., & Rasilo, H. Joint word segmentation and referential learning (referenced computational model).
- Yurovsky, D., Yu, C., & Smith, L. B. (2012). Statistical speech segmentation and word learning in parallel: Scaffolding from child-directed speech. *Frontiers in Psychology*, 3, 374.
- Zhang, Y., Yurovsky, D., & Yu, C. (2015). Statistical word learning as a continuous, cumulative process.

**Curiosity, information gaps, and question formation**
- Loewenstein, G. (1994). The psychology of curiosity: A review and reinterpretation. *Psychological Bulletin*, 116(1), 75–98.
- Golman, R., & Loewenstein, G. (2016). An information-gap theory of feelings about uncertainty. Carnegie Mellon University working paper.
- Kang, M. J., Hsu, M., Krajbich, I. M., Loewenstein, G., McClure, S. M., Wang, J. T., & Camerer, C. F. (2009). The wick in the candle of learning: Epistemic curiosity activates reward circuitry and enhances memory. *Psychological Science*, 20(8), 963–973.
- Ten, A., Oudeyer, P.-Y., Sakaki, M., & Murayama, K. (2025). The Curious U: Integrating theories linking knowledge and information-seeking behavior. *Open Mind*, 9, 1763–1785.
- Modirshanechi, A., Kondrakiewicz, K., Gerstner, W., & Haesler, S. (2023). Curiosity-driven exploration: Foundations in neuroscience and computational modeling. *Trends in Neurosciences*, 46(12), 1054–1066.

**Habituation, dishabituation, and information-gain-driven decay**
- Ueda, K., Sekoguchi, T., & Yanagisawa, H. (2021). How predictability affects habituation to novelty. *PLoS One*, 16(6), e0237278.
- Smart, M., Shvartsman, S. Y., & Mönnigmann, M. (2026). Dynamical principles of habituation across substrates and scales. *Annual Review of Control, Robotics, and Autonomous Systems*.
- Hochner, B., Klein, M., Schacher, S., & Kandel, E. R. (1986). Additional component in the cellular mechanism of presynaptic facilitation contributes to behavioral dishabituation in Aplysia. *Proceedings of the National Academy of Sciences*, 83(22), 8794–8798.
- Cohen, T. E., Kaplan, S. W., Kandel, E. R., & Hawkins, R. D. (1997). A simplified preparation for relating cellular events to behavior: Mechanisms contributing to habituation, dishabituation, and sensitization of the Aplysia gill-withdrawal reflex. *Journal of Neuroscience*, 17(8), 2886–2899.

**Noradrenaline, arousal, and network topology**
- Aston-Jones, G., & Cohen, J. D. (2005). An integrative theory of locus coeruleus-norepinephrine function: Adaptive gain and optimal performance. *Annual Review of Neuroscience*, 28, 403–450.
- Shine, J. M., Aburn, M. J., Breakspear, M., & Poldrack, R. A. (2018). The modulation of neural gain facilitates a transition between functional segregation and integration in the brain. *eLife*, 7, e31130.
- Zerbi, V., et al. (2019). Rapid reconfiguration of the functional connectome after chemogenetic locus coeruleus activation. *Neuron*, 103(4), 702–718.

**Dopamine, generalization, and precision**
- Kahnt, T., & Tobler, P. N. (2016). Dopamine regulates stimulus generalization in the human hippocampus. *eLife*, 5, e19700.
- Novicky, F., Parr, T., Friston, K., Mirza, M. B., & Sajid, N. (2023). Bistable perception, precision and neuromodulation. *Cerebral Cortex*.

**Acetylcholine, novelty, and encoding-versus-retrieval balance**
- Douchamps, V., Jeewajee, A., Blundell, P., Burgess, N., & Lever, C. (2013). Evidence for encoding versus retrieval scheduling in the hippocampus by theta phase and acetylcholine. *Journal of Neuroscience*, 33(20), 8689–8704.
- Gómez-Ocádiz, R., Trippa, M., Zhang, C.-L., Posani, L., Cocco, S., Monasson, R., & Schmidt-Hieber, C. (2022). A synaptic signal for novelty processing in the hippocampus. *Nature Communications*, 13, 4122.
- Hasselmo, M. E., & McGaughy, J. (2004). High acetylcholine levels set circuit dynamics for attention and encoding and low acetylcholine levels set dynamics for consolidation. *Progress in Brain Research*, 145, 207–231.
- Gais, S., & Born, J. (2004). Low acetylcholine during slow-wave sleep is critical for declarative memory consolidation. *Proceedings of the National Academy of Sciences*, 101(7), 2140–2144.

**Serotonin and meta-learning under uncertainty**
- Grossman, C. D., Bari, B. A., & Cohen, J. Y. (2022). Serotonin neurons modulate learning rate through uncertainty. *Current Biology*, 32(6), 1339–1349.

**GABA, gain, and stimulus selectivity**
- Katzner, S., Busse, L., & Carandini, M. (2011). GABA_A inhibition controls response gain in visual cortex. *Journal of Neuroscience*, 31(16), 5931–5941.

**Divisive normalization**
- Carandini, M., & Heeger, D. J. (2011/2012). Normalization as a canonical neural computation. *Nature Reviews Neuroscience*, 13, 51–62.

**Category and prototype formation**
- Rosch, E. (1973). Natural categories. *Cognitive Psychology*, 4(3), 328–350.

**Complementary learning systems and structure extraction**
- Sun, W., Advani, M., Spruston, N., Saxe, A., & Fitzgerald, J. E. (2023). Organizing memories for generalization in complementary learning systems. *Nature Neuroscience*, 26(8), 1438–1448.
- Singh, D., & Schapiro, A. C. (2026). A computational account of complementary learning systems. *Philosophical Transactions of the Royal Society B*, 381(1954), 20250243.

**Sleep-dependent consolidation and homeostatic plasticity**
- Butz, M., & van Ooyen, A. (2014). A simple rule for dendritic spine and axonal bouton formation can account for cortical reorganization after focal retinal lesions. *PLoS Computational Biology* (homeostatic structural plasticity, referenced principle).
- Tadros, T., Krishnan, G. P., Ramyaa, R., & Bazhenov, M. (2022). Biologically inspired sleep algorithm for artificial neural networks. *Journal of Neuroscience Methods* (referenced sleep-replay algorithm).
- Watkins, P. K., Kim, J., & Kenyon, G. T. Sinusoidally-modulated noise as a slow-wave-sleep surrogate (referenced computational method).
- Lee, K.-F. K., & Kirkwood, A. (2019). Mechanisms of homeostatic synaptic plasticity in vivo. *Frontiers in Cellular Neuroscience*, 13, 520 (sliding-threshold homeostasis).

---

## 12. Formula Index

A consolidated reference of every named formula appearing in this document, grouped by originating module.

**Confidence/uncertainty (system-wide, §3.2)**
```
confidence = 1 − 1/(1 + evidence_count)
uncertainty = 1/(1 + evidence_count)
```

**Branching entropy (Phase 0, §5.2)**
```
H(context) = − Σ p(next_char|context) · log2 p(next_char|context)
```

**Symmetric PMI (Phase 0b, §5.3)**
```
PMI(A;B) = log2( P(A,B) / (P(A)·P(B)) )
```

**Six-core neuromodulator computation (Phase 6a, §7.1)**
```
persistent_pressure = clamp(1 − avg_closure + 0.35·avg_overlap + 0.25·(1 − avg_outcome))
plasticity = clamp(0.28 + 0.35·persistent_pressure + 0.18·avg_overlap + 0.15·(1 − avg_outcome))
exploration_bias = clamp(0.30 + 0.35·avg_overlap + 0.20·(1 − avg_outcome) + 0.10·avg_no_candidate)
consolidation_bias = clamp(0.25 + 0.45·avg_closure + 0.25·avg_outcome − 0.18·persistent_pressure)
inhibition_bias = clamp(0.20 + 0.35·avg_no_candidate + 0.12·avg_overlap)
revision_bias = clamp(0.25 + 0.40·persistent_pressure + 0.20·(1 − avg_outcome))

dopamine      = clamp(0.25 + 0.45·avg_outcome + 0.25·avg_closure)
serotonin     = clamp(0.25 + 0.55·consolidation_bias)
glutamate     = clamp(0.30 + 0.55·exploration_bias)
gaba          = clamp(0.20 + 0.60·inhibition_bias)
noradrenaline = clamp(0.25 + 0.45·persistent_pressure + 0.15·avg_overlap)
acetylcholine = clamp(0.30 + 0.25·(1 − avg_overlap) + 0.25·revision_bias)

final_value = phasic_value + tonic_weight·(tonic_target − phasic_value)
novel_ratio = clamp(0.6 − 0.3·gaba + 0.2·noradrenaline, 0.3, 0.9)
```

**Plateau-break / stabilize-gains adjustment (Phase 6b, §7.3)**
```
scale = clamp(0.85 − 0.10·gaba, 0.55, 0.98)
post_plasticity    = clamp(pre_plasticity · scale)
post_exploration   = clamp(pre_exploration + 0.15·(1−gaba) + 0.05·noradrenaline)
post_inhibition    = clamp(pre_inhibition  + 0.10·gaba + 0.05·(1−dopamine))
post_revision      = clamp(pre_revision    + 0.10·serotonin + 0.05·acetylcholine)
post_consolidation = clamp(pre_consolidation − 0.05·(1−effectiveness_score))    [plateau-break]

post_consolidation = clamp(pre_consolidation + 0.05·dopamine + 0.05·glutamate)
post_revision      = clamp(pre_revision − 0.03·serotonin)
post_plasticity    = clamp(pre_plasticity + 0.02·dopamine)                      [stabilize-gains]

critic_penalty = clamp((max_deviation − 0.15)·2.0, 0, 0.8)
```

**Sliding-threshold homeostasis and bias renormalization (Phase 6d, §7.5)**
```
agreement = direction_bias · target_direction_bias
chronic_factor = clamp(1 − 0.3·agreement, 0.8, 1.2)
new_learning_rate = clamp(current_lr · (0.7 + 0.2·serotonin) · chronic_factor, min_lr, max_lr)

pull = clamp((0.15 + 0.05·min(5, eff_zero_streak−3)) · (0.6+0.6·glutamate) · (1−0.4·serotonin), 0.05, 0.35)
new_value = clamp(old_value + (mid_target − old_value)·pull)
```

**Adenosine homeostat (Phase 7a, §7.6)**
```
buildup_rate = 0.08 · (1 + 0.5·wake_activity) · (1.2 − 0.4·acetylcholine)
new_level = clamp(old_level + buildup_rate)
sleep_entry_pull = clamp((0.05 + max(0,level−0.65)·(0.25−0.05)/(1−0.65)) · (0.7+0.6·glutamate) · (1−0.3·serotonin), 0.02, 0.4)
sleep_discharge: new_level = old_level · 0.85
```

**Sigmoid soft-clamp and E/I balance (Phase 7c, §7.8)**
```
t = (x − lo)/(hi − lo)
soft_clamp blends t with 1/(1+e^(−k(t−0.5))), k = 1/softness, near either edge only

gaba_post      = soft_clamp(gaba_pre + 0.12·glutamate_pre)
glutamate_post = soft_clamp(glutamate_pre − 0.15·gaba_pre)
```

**Up-state activity and selection pressure (Phase 7d, §7.9)**
```
activity = clamp(base_score · (0.6+0.5·glutamate) · (1.0−0.3·gaba) · (1.0 − ach_gain·(acetylcholine−0.5)) + noise + anchor_bonus)
selection_pressure = clamp(0.5 + 0.6·gaba − 0.4·glutamate)
```

**Histamine / orexin / BDNF (Phase 7e/f/g, §7.10)**
```
level = clamp((1−alpha)·previous_level + alpha·target)
histamine_target ∝ w₁·(1−adenosine) + w₂·wake_activity
orexin_target    ∝ w₁·unread_fraction + w₂·progress_norm + w₃·histamine
bdnf_target      ∝ w₁·consolidation + w₂·progress_norm + w₃·activity
```

**Cortisol (Phase 7cort, §7.11)**
```
allostatic_load = clamp(0.6·max_stress_signal + 0.4·weighted_sum_of_stress_signals)
cortisol_level = clamp((1−alpha)·previous_level + alpha·allostatic_load)
```

**Cooperative sleep/wake authority (§7.12)**
```
arousal = clamp(0.28·histamine + 0.25·orexin + 0.20·noradrenaline + 0.12·acetylcholine + 0.15·cortisol)
inhibitory_readiness = clamp(0.55·gaba + 0.25·inhibition_bias + 0.20·(1−glutamate))
consolidation_readiness = clamp(0.45·consolidation_bias + 0.30·bdnf + 0.25·serotonin)
sleep_score = clamp(0.35·adenosine + 0.25·(1−arousal) + 0.20·inhibitory_readiness + 0.12·consolidation_readiness + 0.08·(1−cortisol))

dopamine_target      = clamp(0.20 + 0.34·outcome + 0.18·exploration_bias + 0.16·(1−persistent_pressure) + 0.12·(1−cortisol))
serotonin_target     = clamp(0.22 + 0.38·consolidation_bias + 0.20·(1−cortisol) + 0.12·outcome + 0.08·inhibitory_readiness)
noradrenaline_target = clamp(0.12 + 0.30·persistent_pressure + 0.25·histamine + 0.18·orexin + 0.15·cortisol)
acetylcholine_target = clamp(0.18 + 0.33·revision_bias + 0.22·histamine + 0.17·orexin + 0.10·exploration_bias)
```

**Divisive-normalization role selection (Guarded Graduation, §8.4)**
```
effective_pressure(role) = raw_pressure(role) · max(0, 1 + ach_gain·(acetylcholine−0.5)·novelty(role))
share(role) = effective_pressure(role)^temperature / (Σ effective_pressure^temperature + sigma)
temperature = 1.0 + gaba_gain·(gaba − 0.5)
novelty(role) = 1 − (role's historical graduation count / total historical graduations)
```

**Question priority modulation (Question Promotion, §8.8)**
```
priority = base_priority · clamp(1 + 0.3·(dopamine−0.5) + 0.3·(acetylcholine−0.5))
```

**Symmetric self-regulating neuromodulator gain (general pattern, §9)**
```
effective_value = base_value · (1 + gain·(0.5 − messenger_value))   [lowering coupling]
effective_value = base_value · (1 + gain·(messenger_value − 0.5))   [raising coupling]
```

---

## 13. Appendix: Full Runtime Load Order

The following 39 phase modules are loaded, in this exact order, on every system startup, forming the complete chain executed once per real learning cycle:

1. Context Observation Learning (§5.1)
2. Phase 0 — Lexical Boundary Observation (§5.2)
3. Phase 5a — Integrated Self-Improving Learning (health aggregation)
4. Phase 5b — Integrated Strategy Refinement
5. Phase 5c — Learning Outcome Closure and Question Cluster Resolution
6. Phase 5d — Integrated Observation and Strategy Memory
7. Stage-B Gap Detection (§8.1)
8. Phase 5e — Context Expansion and Gap Closure
9. Phase 5f — Context Expansion Effectiveness and Adaptive Windowing
10. Phase 5g — Context Strategy Selection and Experiment Memory
11. Phase 5h — Strategy Experiment Outcome Learning
12. Phase 5i — Outcome-Driven Context Strategy Diversification
13. Phase 6a — Neuromodulated Sleep Replay and Meta-Plasticity (§7.1–7.2)
14. Phase 6b — Sleep Replay Effectiveness and Plasticity Adjustment (§7.3)
15. Phase 6c — Bias Persistence and Self-Regulating Meta (§7.4)
16. Phase 6d — Saturation Homeostasis and Meta-Metaplasticity (§7.5)
17. Phase 7a — Adenosine Homeostat (§7.6)
18. Phase 7b — Endocannabinoid Retrograde Gain Control (§7.7)
19. Phase 7b1 — Wake-Chain Bridge
20. Perf0 — Runtime Acceleration
21. Phase 7c — Adaptive Boundaries and E/I Balance (§7.8)
22. Perf3 — Connection Accelerator
23. Phase 7d — Slow-Wave Sleep Substructure (§7.9)
24. Phase 7e — Histamine / Wake-Arousal (§7.10)
25. Phase 7f — Orexin / Wake-Endurance (§7.10)
26. Phase 7g — BDNF / Growth Consolidation (§7.10)
27. Phase 7cort — Cortisol Stability Watch (§7.11)
28. Cooperative Core / Neuromodulator Sleep Authority (§7.12)
29. Stage-B Guarded Hypothesis Graduation (§8.4)
30. Stage-B Contradiction Detection (§8.2)
31. Stage-B Hypothesis Revision (§8.3)
32. Stage-B Fact Promotion (§8.5)
33. Phase 0b — Relational Binding Observation (§5.3)
34. Stage-B Relation Promotion (§8.6)
35. Stage-B Ontology Cluster Observation (§8.7)
36. Stage-B Ontology Promotion (§8.7)
37. Stage-B Question Promotion (§8.8)
38. Stage-B Question-Chunk Feedback (§8.9)
39. Stage-B Gapflow Runtime Contract (chain-top integrity contract; `AutonomousLoop.cycle.__module__` is expected to resolve here)

---

*End of report.*
