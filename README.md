# BrainStem

Update 10.09.26

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](#current-development-and-testing-status)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](#running-the-system)
[![Backend: SQLite](https://img.shields.io/badge/backend-SQLite-lightgrey)](#database-initialization)
[![Roadmap: Stage A historical validation passed, current build revalidation pending](https://img.shields.io/badge/roadmap-revalidation%20pending-yellow)](#current-development-and-testing-status)


BrainStem is a biologically inspired, Real Neuro-Symbolic (RNS-AI) cognitive architecture for lifelong learning. It is designed to learn models of the structures and dynamics of language and text through context hypotheses, uncertainty, contradiction, revision, neuromodulation, replay, and consolidation rather than by merely storing isolated facts.

>One CPU Core /
>No GPU

> [!IMPORTANT]
> BrainStem is a research and calibration system, not a production-ready assistant. Permanent fact, relation, and question writes remain locked while the learning core and its candidate flow are being validated.

---

[![BrainStem Project AI conversation](https://img.youtube.com/vi/4nN7zELSAMo/mqdefault.jpg)](https://www.youtube.com/watch?v=4nN7zELSAMo)

YouTube - AI conversation about BrainStem Project

---

[NotebookLM codebase exploration](https://notebook.google.com/notebook/34b994eb-9f62-4fd7-a04d-facbd6041654) 08.09.2026

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

## Current State

### Project-Structure

<a href="assets/Project-Structure.png" target="_blank">
  <img src="assets/Project-Structure.png" alt="Project-Structure" width="250" />
</a>

## Current State

> [!NOTE]
> Update (10 September 2026): Following the 08 September 2026 static/synthetic
> audit (14 defects found and fixed), the system underwent its first real,
> large-scale, multi-day production run (two ZIM sources, ~664 MB combined,
> 167,661 chunks) and surfaced a further set of real defects that only
> appear under genuine long-duration load — none of which were reachable by
> short synthetic testing alone:
> - `db_bootstrap.ensure_database_exists()` was never actually invoked by the
>   real `main.py`/`gui_app.py` entrypoint (only by `systemtest.py`), causing
>   two schema-dependent shadow modules to fail on every cycle even on a
>   correctly bootstrapped database. Fixed both at the entrypoint (automatic
>   bootstrap call in `main.py`) and at the two affected modules themselves
>   (now self-healing via their own `ensure_schema()`).
> - An uncaught `sqlite3.OperationalError: database is locked` inside a
>   non-productive audit-log write could silently kill the autonomous-
>   learning background thread with no GUI-visible explanation. Contained
>   at the source and given defense-in-depth exception handling around the
>   cycle call itself.
> - No module anywhere ever explicitly checkpointed the WAL journal, while
>   the GUI's own periodic reads could prevent automatic passive
>   checkpointing from ever fully shrinking the on-disk `-wal` file. A
>   guarded, non-blocking `PRAGMA wal_checkpoint(TRUNCATE)` now runs once
>   per outer GUI cycle.
> - The GUI itself froze ("Not Responding") at large scale (2,871 cycles /
>   327,637 hypotheses / 9.2 GB) while the backend kept learning correctly
>   the entire time (confirmed via Process Explorer thread-stack
>   inspection: the GUI main thread was busy, not blocked, deep inside
>   Tk canvas/font-metric calls and unindexed `ORDER BY` Treeview queries).
>   Fixed via lazy tab-aware refresh for the two expensive Treeview tabs,
>   added indexes on `documents(created_at)`/`facts(created_at)`, and a
>   full rewrite of the neuromodulator dashboard to reuse existing Tk
>   canvas items (`coords()`/`itemconfig()`) instead of repeated
>   `delete()` + full recreation on every tick — the latter is the most
>   likely explanation for why a simple GUI restart (with the identical,
>   unchanged database) always restored full responsiveness immediately.
> - The GUI mood/sleep indicator relied exclusively on the cooperative
>   six-core sleep authority, which — measured over a real 467-cycle
>   window — never once crossed its 0.62 combined threshold (peak 0.5403
>   at cycle 8, then oscillating 0.31–0.54, i.e. not a data-maturity
>   effect). The independent, older Phase-7a adenosine homeostat was
>   confirmed working correctly the entire time (290 of 467 cycles
>   asleep, 58 real transitions) but was never reflected in the GUI. Fixed
>   by mirroring the same "either authority" OR-pattern already used
>   internally by Phase 7d/7e for real slow-wave admission.
>
> All fixes were independently verified: full `compileall` across the
> package, targeted reproduction tests for each defect (including real
> multi-thread lock-contention simulation and mock-canvas item-count
> verification across 1,000 simulated cycles), and confirmed in the live
> production run itself, which reached 93.0% corpus completion
> (155,861 / 167,661 chunks) without a recurrence of the freeze.
>
> The 08 September 2026 findings (schema-column gaps, facts/relations/
> ontology naming conflict, E/I kernel-guard crash at neuromodulator
> boundary values, dialogue/read-only persistence conflict, silent
> diagnostic blindness, swallowed phase-registry load failures, an
> untested `systemtest.py`, an unused `--gui` flag, duplicate index
> definitions) remain fixed and were re-confirmed present in this build.

### Current Architecture

- BrainStem remains a phase-based, hypothesis-centered language and text understanding system.
- The Python package remains `ki_system`.
- `autonomous.py` remains the minimal autonomous loop kernel.
- `phase_registry.py` remains the central installer and ordering authority for the runtime phase chain; a real load failure now also sets an explicit `report["fatal"]` flag instead of being silently absorbed.
- SQLite remains the canonical relational source. All connections (main GUI, dedicated background-worker, diagnostic) now use a consistent 60-second busy-timeout instead of SQLite's 5-second default.
- The learning mode remains `context_hypotheses_with_neuromodulators`.
- The Modern Gap Candidate Bridge remains checkpoint-based, bounded to at most 512 hypotheses per cycle, `observed_only`, shadow-only, and non-productive.
- Stage-B gap flow continues to distinguish real shadow-observed candidates from measured zero-source intervals without opening productive downstream writes.
- No unvalidated replacement of the canonical runtime kernel or relational data source is authorized.
- The admin GUI's autonomous-learning and drift/sensory-deprivation background threads now use their own dedicated `Memory`/SQLite connection, separate from the GUI's own connection, eliminating unsynchronized concurrent access to a single shared connection object across threads.

### Runtime Phase Structure

The effective runtime architecture includes:
1. context observation and integrated hypothesis learning
2. strategy refinement, outcome closure, and observation memory
3. context expansion and effectiveness evaluation
4. strategy selection, experiment memory, and outcome learning
5. outcome-driven strategy diversification
6. Phase-6a offline replay and meta-plasticity
7. Phase-6b replay effectiveness evaluation
8. Phase-6c bias persistence and self-regulating meta-control
9. Phase-6d saturation homeostasis and meta-metaplasticity
10. Phase-7a adenosine homeostasis
11. Phase-7b endocannabinoid regulation
12. Phase-7b1 wake-chain bridging
13. Phase-7c adaptive boundaries, E/I balance, and sigmoid soft clipping
14. Phase-7d slow-wave sleep and down-selection
15. Phase-7e histamine wake/arousal regulation
16. Phase-7f orexin wake-endurance regulation
17. Phase-7g BDNF growth and consolidation regulation
18. Phase-7cort stability observation and guarded Cortisol Stage 2 regulation
19. cooperative six-core neuromodulator and sleep/wake authority
20. guarded Stage-B hypothesis graduation
21. non-productive shadow recheck runtime
22. Stage-B gapflow runtime contract

### Corpus and Learning State

The current, live production baseline (two ZIM sources: German Wikipedia
*Physics* and *Computer* categories, ~664 MB combined) as of the latest
observed run:
- 155,861 of 167,661 imported chunks read (93.0%)
- over 1.4 million context hypotheses recorded (last confirmed count:
  1,396,802 at 87.8% progress; growing continuously)
- observed throughput: on the order of 100,000–125,000 chunks processed per
  24-hour period of active autonomous learning (single CPU core, no GPU, as
  per project design)

These are live, observed values from an active run, not a frozen baseline —
they are expected to change (and the corpus percentage to reach 100%) as
autonomous learning continues.

Corpus completion does not stop autonomous learning. Replay, consolidation,
hypothesis evaluation, neuromodulator regulation, sleep/wake transitions,
and guarded Stage-B preparation continue after all imported chunks have
been read.

Replay activity alone does not prove replay-caused semantic improvement.
Independent outcome evidence and real-user dialogue measurements remain
necessary for semantic-effectiveness claims.

### Six-Core Neuromodulator State

The six core neuromodulators (dopamine, serotonin, glutamate, GABA,
noradrenaline, acetylcholine) continue to be governed by the common
canonical runtime authority in
`v8_cooperative_core_neuromodulator_sleep_authority_release.py`, writing to
`phase6a_neuromodulated_sleep_state` (the canonical source also read by the
GUI), with bounded smoothing (`new = old + 0.18 * (target - old)`) and
values constrained to `[0.05, 0.95]`.

Real production data (467-cycle window) confirms the regulator behaves as
designed: dopamine and serotonin remained essentially flat over hundreds of
consecutive cycles under stable input conditions, while adenosine showed a
clear, repeating sawtooth pattern consistent with the Phase-7a decay
formula (`new = old * 0.85`), verified to match observed values to within
three decimal places across nine consecutive cycles.

#### Extended Neuromodulator State

All twelve neuromodulator/regulatory systems (six core + adenosine,
endocannabinoids, cortisol, histamine, orexin, BDNF) remain represented in
code and runtime state and connected to the GUI. Endocannabinoids were
observed to remain at exactly 0.000 throughout the current run (plausible
at this corpus stage — the postsynaptic-overload trigger mechanism has
apparently not yet fired — but worth monitoring at larger scale).

### Cooperative Sleep/Wake Authority — Dual-Authority Finding

> [!IMPORTANT]
> Real production measurement (10 September 2026, `diagnose_sleep_authority.py`
> against a live 467-cycle database) found that the cooperative sleep score
> **never crossed its 0.62 entry threshold** over the observed window (peak
> 0.5403 at cycle 8, then oscillating 0.31–0.54 with no upward trend). The
> independent, older Phase-7a adenosine homeostat, however, was confirmed
> working correctly and extensively the entire time (290 of 467 cycles in
> `sleep` mode, 58 real transitions, full event history). The two
> authorities structurally interfere: Phase-7a enters sleep and begins
> discharging adenosine at its own 0.65 single-signal threshold, before the
> cooperative authority's own, later, five-signal combined threshold can
> ever be reached from the same adenosine input.
>
> This is not a new defect in the cooperative scoring formula itself — it is
> an interaction between two independently valid, previously-uncoordinated
> sleep authorities. The GUI now surfaces both authorities explicitly
> (mood label distinguishes "Schläft" [cooperative] from "Konsolidiert
> (Phase7a)"), mirroring the same "either authority" OR-pattern Phase 7d/7e
> already use internally for real slow-wave admission — so real
> consolidation was occurring the entire time even when the GUI previously
> showed no sleep state at all.

The cooperative sleep score formula itself is unchanged: 35% adenosine
pressure, 25% arousal release, 20% inhibitory readiness, 12% consolidation
readiness, 8% absence of cortisol-related stress blocking, with
sleep-entry threshold 0.62, wake-entry threshold 0.42, and minimum dwell
time 3 cycles for hysteresis. State remains stored in
`cooperative_sleep_wake_state` / `cooperative_sleep_wake_cycles`.

### Adenosine and Slow-Wave Sleep

The Phase-7a adenosine homeostat remains active and independently
confirmed correct via real production data (see above). Phase 7d continues
to accept either the Phase-7a homeostat or the cooperative sleep/wake
state as a valid sleep-entry authority, recording which one authorized
entry per cycle.

### Efraimidis-Spirakis Sampling / Sigmoid Soft Clipping / E/I Balance

Both mechanisms remain intact and unchanged. The previously-found E/I
kernel-guard crash (an unconditional shadow-kernel comparison that raised
`database is locked`-unrelated `RuntimeError`s at neuromodulator boundary
values near 0.05/0.95) is fixed: the guard now only enforces (and only
raises) when explicitly running in opt-in `kernel_guarded` mode; default
production cycles never crash from this path. Verified with 25 real
cycles including two rounds of deliberately forced boundary values.

### Histamine, Orexin, BDNF, and Cortisol

Unchanged in mechanism. Real production data shows histamine oscillating
cleanly between 0.50–0.68 with correct regime transitions at ~0.6; orexin
and BDNF growing slowly and monotonically in step with reading progress;
cortisol remaining low ("calm") throughout, consistent with Stage-2
warm-up not yet being reached.

### GUI State

The GUI displays all twelve neuromodulators via a dashboard that now
reuses its Tk canvas items across the entire run instead of deleting and
recreating them on every tick (see Validation Status above) — verified to
create zero additional canvas items and zero `delete()` calls even after
1,000 simulated update cycles. Per-neuromodulator canvas updates are
additionally skipped when the value has not changed beyond display
precision (±0.005), without any dependency on which tab is currently
visible (the dashboard is expected to update on every real learning cycle
regardless of tab).

The "Datenbank" and "Fakten/Relationen" tabs — whose Treeview
repopulation queries scale with total database size — now only refresh
while actually visible, with an immediate one-off refresh on tab switch
so the data never appears stale.

The mood/mission-control indicator now reflects both sleep authorities
(cooperative and Phase-7a) rather than only the cooperative one (see Dual-
Authority Finding above). The per-cycle diagnostic log line now reuses the
existing 10-second corpus-stats cache instead of running a redundant,
increasingly expensive `COUNT(*)` against `context_hypotheses` on every
single real cycle (measured 92% reduction in query overhead for this
specific path at 200,000-row scale).

One visible autonomous GUI cycle still contains five real backend cycles,
each with its own diagnostic evaluation and progress reporting.

### Stage-B Functional State

Unchanged and not yet activated: guarded Cortisol Stage 2 regulation
remains in observer mode, the three-survived-consolidation graduation
gate, `_critic_gate`, warm-up damping, and the one-graduation-per-cycle
budget all remain in place with Facts promotion disabled. The cooperative
neuromodulator/sleep-wake phase remains positioned after Cortisol and
before guarded Stage-B graduation in the wrapper chain.

### Current Safety Boundary

Unchanged and re-confirmed intact throughout the entire real production
run (facts/relations/questions counts observed at `[0, 0, 0]` at every
logged checkpoint): all productive writes (Facts, Relations, Questions,
Attention, Phase-5f/5g/5i experiments, Fact promotion) remain closed. The
cooperative authority continues to write only the six canonical
neuromodulator values, cooperative sleep/wake state, and bounded cycle
provenance.

A vector database remains explicitly deferred (see Roadmap below).

### Schema and Bootstrap Discipline

All schema-related fixes from the live-incident findings above are
additive only (`CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ADD COLUMN`),
verified safe to apply directly against an existing, populated production
database with no risk to already-recorded chunks or hypotheses. The
central bootstrap (`db_bootstrap.ensure_database_exists()`) is now
guaranteed to run automatically on every real program start
(`main.py --gui` / `--user-gui`), in addition to two previously-vulnerable
shadow modules now being self-healing regardless of how or whether the
database was bootstrapped beforehand.

Key/value reads continue to follow the repository contract:
`return dict(con.execute("SELECT key,value FROM " + table).fetchall())`

### Current Evidence Boundary

Proven via the real production run described above: multi-day autonomous
learning stability at real scale (93% of a 167,661-chunk corpus, 1.4M+
hypotheses, no data loss or corruption across two crash-recovery events),
correct independent operation of the Phase-7a sleep authority, correct
E/I regulation at neuromodulator boundary values, and full GUI
responsiveness recovery after the tab-refresh and canvas-reuse fixes.

Still not proven:
- a full, formal drift validation of the *current* build (the historical
  1,344-cycle result applies only to a much earlier architectural state)
- natural cooperative-authority Sleep entries under real conditions (the
  cooperative score has not yet been observed crossing its own threshold;
  whether it ever should, or whether the threshold/weighting needs
  revisiting, remains an open, deliberately low-priority question)
- semantic learning effectiveness / real-user dialogue usefulness
- behavior at corpus/database scales significantly beyond the current
  ~9+ GB (see Roadmap: full German Wikipedia scaling)
- readiness for productive Fact promotion

## Next Major Step

1. **Reach 100% completion of the current two-source corpus** (German
   Wikipedia *Physics* + *Computer* categories, 167,661 chunks; currently
   at 93.0%) under the fixed build, to confirm continued stability through
   full corpus completion and into the subsequent replay/consolidation-only
   regime.
2. **Etappe-A long-duration stress validation**: run autonomous learning
   substantially beyond the highest cycle count reached so far, using the
   built-in Drift-Report / sensory-deprivation tab, to obtain a new,
   current-build drift baseline (the historical 1,344-cycle result is
   explicitly superseded by all changes since).
3. Only after (1) and (2) are complete and clean: revisit whether to begin
   activating guarded Cortisol Stage 2 (moving it from observer to applied
   mode) as the first real Stage-B step.

## Roadmap

| Stage | Status | Gating condition to proceed |
|---|---|---|
| **Stage A — Core stability** | Substantially re-validated via real multi-day production use (93% corpus, 1.4M+ hypotheses, multiple real-world defects found and fixed under genuine load) | Formal long-duration drift run on the current build (see Next Major Step) |
| **Stage B — Guarded graduation** | Prepared, not yet activated (Cortisol Stage 2 remains observer-only) | Stage-A drift validation clean; Cortisol Stage 2 promoted from observer to applied mode first, under its existing warm-up/budget/cooldown gates |
| **Full corpus scaling (complete German Wikipedia)** | Deliberately deferred | Current two-source corpus reaches 100% and Stage-A validation is clean. Rough estimate from current throughput: ~13.5 GB of text-only content, ~3.4M chunks, ~33M hypotheses, ~0.9 TB resulting database, ~27–28 days of continuous processing at observed throughput — order-of-magnitude only, not a commitment |
| **Vector database evaluation** | Deliberately deferred per project's own architecture-checkpoint rule | Only once stable hypothesis identities exist (post-Stage-B graduation), a concrete semantic-retrieval use case is identified, requirements are measurable, and a read-only/shadow comparison against the SQLite baseline is performed. Must never replace the canonical relational source or open productive gates — the project's provenance-first, no-black-box guarantee takes priority over retrieval convenience |
| **Multi-core / multi-process learning** | Explicitly out of scope for now | Acknowledged as a real, non-trivial architectural undertaking (Python's GIL requires `multiprocessing`, not `threading`, for genuine parallel compute; SQLite's single-writer model would require careful cross-process coordination). Not currently planned; current single-core throughput is considered acceptable |


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

---

Every answer the system produces is retrieved from proof, not generated. Each fact in the knowledge base carries a complete provenance chain, from the final anchor back through its consolidation cycles, its originating hypotheses, and down to the exact source chunks and documents that justified its creation. There is no black box. If the system states something, it can show why it states it. Knowledge enters the system as raw observation, but it is never exposed to a user until it has passed through a multi-phase verification pipeline: hypothesis generation, strategic outcome testing, sleep-replay reinforcement, and guarded graduation. Only then does it become an anchor, a deductively usable fact. Until that point, it remains in the shadow layer, unable to influence any user-facing output. This creates a hard epistemic boundary. The system cannot hallucinate an answer it has not earned. When no verified anchor exists for a query, it does not invent a plausible response, and it reports the gap. The safety is architectural, not statistical. Trust is not placed in a model's weights, but in a transparent, auditable process that can be inspected, challenged, and verified, just like an engineering safety circuit.

---

## Architecture

---

<a href="assets/Autonomous_Learning_Architecture_Diagram.png" target="_blank">
  <img src="assets/Autonomous_Learning_Architecture_Diagram.png" alt="Project-Structure" width="250" />
</a>

---

BrainStem does not operate as a continuously coupled system of differential equations. Instead, it traverses a cyclic state graph: each phase activates at most 2–3 dominant neuromodulators, while the remainder are kept inactive or passive. This sequential architecture prevents interaction cascades and enables deterministic debugging.

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
```
</details>


---

## Development Notes

- **Python package:** `ki_system`
- **Local project folder:** `BrainStem`
- **Primary runtime:** Python 3.11 on Windows with SQLite
- **Documentation language:** English, German
- **Status:** highly experimental and under mathematical and architectural validation
- **Engineering discipline:** backup, compile check, schema self-check, smoke test, and rollback planning for structural changes
- **AI-assisted engineering:** development has included collaborative AI assistance. Concept elaboration with ChatGPT, Code generation Claude Opus/Sonnet and ChatGPT 5.6 Depp Thinking, Code review NotebookLM, Gemini and Copilot as critics (no sugarcoat mode)


## Claims and Limitations

BrainStem does not claim that every current hypothesis is meaningful or that the system understands language at a human level. The current objective is to establish and validate the mechanisms by which hypotheses are formed, challenged, revised, inhibited, replayed, and consolidated.

Current zero-result Shadow measurements do not prove a defect and do not prove successful candidate processing. Candidate-flow evidence is the next required result.

## Disclaimer

BrainStem is an experimental cognitive-architecture research project. Biological terminology is used as an engineering analogy and design inspiration. The software is not a biological simulation and does not claim neuroscientific equivalence.
