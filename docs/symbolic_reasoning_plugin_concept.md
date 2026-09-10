# Symbolic Reasoning Plugin — Future-Stage Concept

> **Status:** Concept only. Not scheduled, not started, not part of the
> current runtime. This document exists to preserve the design intent for
> a later development stage, well beyond Stage B graduation and the
> opening of any productive write locks (see `README.md` Roadmap).
>
> **Explicitly out of scope for now:** no code in this repository
> currently implements any part of this concept. Nothing described here
> may be built, wired into `phase_registry.py`, or given any productive
> write path before the gating conditions in the Roadmap section below
> are met.

## 1. Motivation

BrainStem's core learning path is entirely LLM-free and statistics-driven
in the classical machine-learning sense: context hypotheses are formed,
weighted, revised, and consolidated using neuromodulator-driven scalar
signals (confidence, uncertainty, stability, replay weight, etc.). This
works well for the kind of graded, probabilistic knowledge that language
and text understanding inherently produce.

There is a complementary class of problems this approach is not designed
for: **discrete, exact, rule-based inference** — the kind of reasoning
where the answer is either provably correct or not, and where the
*justification* for the answer must be a finite, inspectable chain of
symbolic transformation steps, not a confidence score.

The explicit goal of this plugin concept is to give BrainStem, at some
future stage, a second reasoning mode alongside its existing hypothesis
engine: a **deterministic, non-statistical, symbolic computation and
inference component**, whose every step is a discrete, 100% traceable
transformation with a complete proof chain — in direct contrast to
LLM-style statistical inference.

This is explicitly a **plugin**, not a replacement or modification of the
existing hypothesis-centered learning architecture. The two systems are
intended to coexist: the hypothesis engine continues to handle graded,
uncertain, revisable language understanding; the symbolic engine would
handle exact, provable, rule-based derivations, operating over facts and
relations that the hypothesis engine has already produced and stabilized.

## 2. Core Components

The concept combines five classical symbolic-AI techniques, chosen
specifically because each one produces fully inspectable, deterministic
intermediate state rather than opaque numerical weights.

### 2.1 Unification Engine (variable-based pattern matching)

Rules are stored not as fixed text but as abstract syntax trees (ASTs)
containing variables/placeholders, e.g.:

```
X → Y  ∧  Y → Z  ⟹  X → Z
```

When the system encounters concrete fact anchors, a unification algorithm
(in the classical theorem-proving / Prolog sense) substitutes the
variables `X`, `Y`, `Z` with the actual data points and computes the
result exactly. This is the foundational mechanism: every other component
below either produces candidate rules for this engine to apply, or
consumes its output.

### 2.2 Graph Rewriting (subgraph transformation)

Since BrainStem's relational structures are already graph-shaped, logical
inference corresponds naturally to subgraph replacement: the system
searches the existing knowledge graph for a pattern matching a rule's
premise. When the pattern is found, a graph-rewriting operator applies the
rule and adds the resulting edge as a conclusion.

This maps directly onto BrainStem's existing graph-like relational data
(facts, relations, ontology edges) rather than requiring a separate data
representation.

### 2.3 Inductive Logic Programming (ILP) for self-learned rules

Rather than hand-coding abstract rules, the system should be able to
*learn* them: by comparing many concrete observations, if the hypothesis
core recognizes that hundreds of concrete relations follow the same
structural geometry, it abstracts the concrete values into variables and
proposes a general rule pattern as a new hypothesis.

This is the component that connects the symbolic engine back to
BrainStem's existing hypothesis-centered learning: a candidate symbolic
rule is itself a hypothesis, subject to the same evidence-based validation
philosophy as every other hypothesis in the system, not an externally
injected fixed rule.

### 2.4 Sleep-Consolidation for Rule Validation

In the existing offline-replay phases, the system would tentatively apply
a proposed rule hypothesis against the entire existing data population. If
the rule produces no contradictions with existing stable anchors, it is
considered verified and unlocked as a productive derivation operator.

This deliberately reuses BrainStem's existing consolidation philosophy
(survive repeated offline validation before becoming productive) rather
than introducing a separate, weaker validation pathway for symbolic rules.

### 2.5 Production System (condition-action rules)

Following the model of established cognitive architectures such as ACT-R
or Soar, the system executes derivations in a fixed loop:

```
check condition → select matching rule → apply transformation → update state
```

This provides the deterministic runtime control loop within which the
unification engine, graph rewriting, and validated rule set actually
operate cycle by cycle.

## 3. Core Advantage Over Statistical/LLM Inference

Every computational and logical step is a discrete, 100% traceable
transformation step with a complete proof chain. This is fully consistent
with — and a natural extension of — BrainStem's existing, non-negotiable
architectural principle (see `README.md`):

> *"Every answer the system produces is retrieved from proof, not
> generated... There is no black box. If the system states something, it
> can show why it states it."*

A symbolic reasoning plugin built this way would not weaken that
guarantee; it would extend it into a domain (exact rule-based inference)
where the existing hypothesis-confidence framework is not the most
natural fit, while preserving the same non-negotiable provenance
requirement.

## 4. Explicit Non-Goals / Guardrails

Consistent with the project's established "measure before changing" and
"no unearned productive writes" discipline, the following are explicitly
**not** part of this concept and must not be inferred from it:

- This is **not** a plan to introduce any LLM, transformer, or statistical
  black-box component. The entire point is to remain non-statistical.
- This is **not** a plan to replace SQLite as the canonical relational
  source. Any graph-rewriting representation would need to be evaluated
  against the same read-only/shadow-preflight discipline already
  established for the (separately deferred) vector-database question.
- This is **not** a plan to open any new productive write path ahead of,
  or independently from, the existing Stage-B / hypothesis-graduation /
  write-lock-opening sequence documented in the project Roadmap. A
  validated symbolic rule becoming a "productive derivation operator"
  (section 2.4) is itself a new class of productive write and must be
  gated at least as strictly as Fact promotion — arguably more strictly,
  since an incorrect symbolic rule can produce many incorrect derived
  facts in a single application, whereas a single incorrect hypothesis
  graduation affects only one fact.
- No word blacklists, hard-coded linguistic filters, or externally
  authored rule sets are to be seeded into the rule population. Candidate
  rules must arise from ILP over the system's own observed data (section
  2.3), matching the project's "learning before rules" principle.

## 5. Relationship to Existing Architecture (for future implementers)

When this concept is eventually scheduled, the following existing
BrainStem conventions should be treated as binding constraints, not
suggestions:

- **Schema discipline:** any new tables this plugin requires (e.g. for
  storing candidate/validated symbolic rules, unification traces, or
  graph-rewrite provenance) must be declared in the central schema
  authority (`db_bootstrap.py`'s `SCHEMA_TABLES`) before any write path is
  opened, following the idempotent `ensure_schema()` / `_self_check_schema()`
  pattern already used throughout the codebase.
- **Shadow-first activation:** exactly like the Modern Gap Candidate
  Bridge and every other new subsystem introduced into this project, this
  plugin must start in an `observed_only` / shadow mode with zero
  productive writes, and only graduate to productive status after a
  dedicated, explicit validation pass — never by default.
- **Full backup before any structural change**, per the project's
  unconditional rule.
- **No silent legacy accumulation:** if an earlier iteration of the rule
  engine, unification strategy, or graph-rewrite operator is superseded
  during development, it must be actively removed (or explicitly flagged
  as a retained-but-marked exception with a stated reason), not left as
  dead code, per the repository-wide Legacy Cleanup contract.

## 6. Suggested Reading / Prior Art

Implementers should review classical literature on:

- Unification and resolution-based theorem proving (as used in Prolog
  and classical automated theorem provers).
- Graph rewriting / graph transformation systems (e.g. double-pushout
  approaches).
- Inductive Logic Programming (ILP), particularly approaches that induce
  rules from relational/graph-structured observations rather than
  attribute-value tables.
- Production-system cognitive architectures, specifically ACT-R and Soar,
  for the condition-action control-loop design.

This document intentionally does not commit to specific algorithms,
libraries, or implementations for any of the five components — that
selection is deferred to whenever this stage is actually scheduled, so
that the choice can be informed by the state of the codebase and
available tooling at that time.
