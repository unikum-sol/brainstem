# BrainStem — Evaluation of Three Scientific Papers for Project Relevance

**Working document**
**Project:** BrainStem
**Subject:** Assessment of three scientific documents for biologically,
mathematically, or methodologically usable content
**Project state at time of writing:** Modern Gap Candidate Bridge +
Bootstrap Shadow V1 installed and accepted on the real runtime path
**Next technical step following this paper evaluation:** read-only Modern
Gap Candidate Signal Distribution Audit V1
**Still locked:** productive gap creation, Attention writes, Phase-5f/5g/5i
experiments, Facts/Relations/Questions writes

> **Note on this document:** this is an English adaptation of an internal
> working note for GitHub publication. All technical content, structure,
> and — critically — all explicit safety/non-goal statements from the
> original are preserved. Nothing in this document authorizes any change
> to the current, still-closed productive write locks.

## 1. Documents Reviewed

1. **Homeostatic structural plasticity — a key to neuronal network
   formation and repair.** Markus Butz and Arjen van Ooyen, *BMC
   Neuroscience*, 2014.
2. **Nonlinear Time Series Classification Using Bispectrum-based Deep
   Convolutional Neural Networks.** Paul A. Parker, Scott H. Holan, and
   Nalini Ravishanker, *arXiv*, 2020.
3. **Supplementary Materials for "A molecule with half-Möbius topology."**
   Igor Rončević et al.; supplementary materials with experimental,
   quantum-chemical, and quantum-algorithmic detail.

## 2. Overall Verdict

Of the three papers, the work on homeostatic structural plasticity is the
most directly relevant to BrainStem. It provides a biologically plausible
model for how a system can develop structural demand from local imbalance
without any central authority prescribing specific connections. Especially
valuable is its separation between a locally arising demand, free
structural elements, and an actual connection that only forms later.

The bispectral nonlinear time-series paper is primarily methodologically
relevant. It shows that ordinary means, autocorrelations, and second-order
spectra can be insufficient for nonlinear time series; higher-order
spectra can reveal additional interactions. For BrainStem this concerns in
particular temporal couplings between neuromodulators, replay, stability,
confidence, exploration, and inhibition.

The half-Möbius-molecule paper has little direct use for language and
context learning. Three points are methodologically relevant, however:
randomized sampling of very large state spaces, subsequent extension of a
selected subspace, and the observation that fast state switching can
appear as a smoothed state under limited measurement bandwidth.

None of the three papers justifies immediately opening the productive gap
lock. They do, however, provide strong suggestions for which trajectories
and interactions BrainStem should first measure in shadow mode.

## 3. Document 1: Homeostatic Structural Plasticity

### 3.1 Core Claim

The paper extends the classical notion of homeostatic plasticity.
Homeostasis is understood not only as adaptation of existing synaptic
weights — a neural network's connectivity structure itself can change:
connections can form, disappear, or be reorganized.

In the described model, a synapse is not simply a weighted edge. It is
composed of two separately arising structural elements:

- an axonal element,
- a dendritic element.

Both elements develop locally, depending on the average electrical
activity of their respective neuron. Free axonal and dendritic elements
can subsequently connect. In the model this connection occurs randomly,
but with a distance-dependent probability. If one of the participating
elements is later removed, the connection can decay again.

The model therefore separates three distinct processes:

1. A local state deviates from the homeostatic range.
2. A local structural offer or structural demand arises from this.
3. Only later does an actual connection possibly form from this.

This separation is particularly important for BrainStem.

### 3.2 Local Rules Can Produce Global Repair

The model was applied to a scenario of local input loss. Initially,
neurons at the edge of the affected region generated demand for additional
horizontal inputs. Neurons from the intact surrounding area provided new
axonal elements. After the border region restored its activity level, the
boundary between normal and low activity moved further into the damaged
area. This produced an ordered repair from outside to inside.

The authors emphasize that this spatially and temporally ordered
reorganization emerged from local rules. No central authority was required
to prescribe a repair order. In the described model, this reorganization
also required neither STDP nor any other Hebbian-style plasticity.

**Transfer to BrainStem**

BrainStem should, in the future, ideally avoid centrally deciding:

- which hypothesis constitutes a learning gap,
- which context must resolve it,
- which connection remains permanent,
- or which strategy is generally correct.

Instead, each hypothesis should be able to develop a local demand from its
own trajectory. Suitable context offers should likewise emerge locally
from observed usage, re-observation, replay, and consolidation.

Overall learning progress should then emerge from many local
demand-offer pairings.

### 3.3 Demand Is Not Yet a Connection

The most important transferable idea:

> **A detected demand is not yet a new structure.**

For BrainStem, a future processing chain should therefore not directly
read:

```
uncertain hypothesis → internal_learning_gaps
```

A biologically cleaner architecture would be:

```
raw hypothesis → observed trajectory → local structural demand →
free gap-demand element → consolidation check → context offer →
connection or rejection
```

Possible later conceptual states could be:

- `observed_only`
- `homeostatic_deviation_observed`
- `structural_demand_pending`
- `context_offer_pending`
- `pairing_under_observation`
- `consolidation_candidate`
- `stable_connection`
- `connection_released`

These states are, for now, purely architectural terminology. They should
not be built as a productive state machine before the underlying
trajectories have been empirically measured.

The current `modern_gap_candidate_shadow` table already satisfies the
first part of this separation: it stores observable signals but
explicitly does not yet declare any record to be a learning gap.

### 3.4 Homeostasis Should Be Self-Referential, Not Global

The biological model regulates activity toward a homeostatic range. For
BrainStem, this should not be hastily translated into a global, fixed
setpoint rule.

A global rule such as:

- stability must be greater than 0.2,
- uncertainty must be less than 0.5,
- replay count must be at least 3,

would ignore individual hypothesis trajectories.

A more fitting future BrainStem idea would be an individual homeostatic
expectation range per hypothesis or hypothesis group, arising from its
own history:

- typical stability development after first observation,
- typical confidence change after re-observation,
- usual replay count until a measurable change occurs,
- usual fluctuation range of neuromodulator values,
- expected change given additional evidence,
- normal duration until stabilization or revision.

A structural demand would then arise not from an absolute value, but from
a sustained deviation from the hypothesis's own learned trajectory.

**Example:** A hypothesis repeatedly receives new evidence and replay, but
repeatedly shows no change in stability, confidence, revision, or context
support. This would be a stronger demand signal than a single instance of
high uncertainty.

### 3.5 Structural Change Is More Than Weight Adjustment

BrainStem already changes or observes numerous scalar quantities:
confidence, uncertainty, stability, attention, priority, replay weight,
meta-plasticity, exploration pressure, inhibition level, revision
pressure, consolidation gain, strategy score.

The paper makes clear that plasticity need not consist only of changing
such weights. A future structural plasticity in BrainStem could
additionally include:

- creating new context connections,
- allowing alternative context offers,
- releasing unproductive connections again,
- decaying permanently unused connections,
- extending local context neighborhoods,
- temporarily inhibiting repeatedly unsuccessful context regions,
- observing several context routes in parallel,
- stabilizing a proven connection only after consolidation.

This fits the existing Stage-B principle: productive changes should only
become possible after repeated, consolidated survival and further gates.

### 3.6 Separating Fast and Slow Plasticity

The authors assign structural plasticity to longer timescales, relevant
for development and repair.

For BrainStem this yields a clear separation:

**Fast processes**
- raw observation,
- short-term attention,
- current neuromodulator response,
- one-off uncertainty,
- queue selection,
- short-term exploration,
- momentary read outcome.

**Medium processes**
- re-observation,
- evidence growth,
- stability change,
- replay selection,
- strategy variation,
- context comparison,
- revision tendency.

**Slow structural processes**
- emergence of a structural learning demand,
- pairing of a demand with a context offer,
- stabilization of a repeatedly helpful connection,
- decay of a permanently useless connection,
- gradual transition into productive knowledge structures.

Productive gap creation should therefore not occur during the fast
observation phase.

### 3.7 Caution Regarding the Distance Function

The model uses a Gaussian-shaped kernel function, making spatially
neighboring neurons more likely to connect than more distant ones.
Interestingly, longer connections also arose while approaching
homeostatic equilibrium.

For BrainStem, this concrete distance rule should not be adopted directly.
A hard-coded linguistic or semantic distance would reintroduce a
predetermined language model. Context proximity should instead ideally
arise from actual usage, for example from:

- shared observation,
- repeated occurrence in the same context,
- successful mutual stabilization,
- measured closure improvement,
- consistent replay coupling,
- actual dialogue usefulness.

## 4. Document 2: Bispectrum and Nonlinear Time Series

### 4.1 Core Claim

The paper addresses classification of nonlinear time series. The authors
argue that many methods predominantly use first- and second-order
properties and therefore cannot sufficiently distinguish certain
nonlinear processes. As an additional representation, they use
higher-order spectral analysis, specifically the bispectrum, based on
third-order moments.

The bispectrum describes not just the strength of individual frequencies
but interactions between frequency pairs, revealing nonlinear couplings
not contained in the ordinary power spectrum.

The bispectral representations are used as two-dimensional inputs for a
convolutional neural network, which simultaneously performs feature
extraction, dimensionality reduction, and classification.

### 4.2 Relevance to the Digital Neuromodulators

BrainStem has twelve active digital neuromodulators: dopamine, serotonin,
noradrenaline, acetylcholine, glutamate, GABA, adenosine,
endocannabinoids, cortisol, histamine, orexin, BDNF.

The effect of these regulators should not be considered only via
individual means. Relevant system states can arise from temporal
interactions, for example:

- glutamate rises and GABA follows with a delay,
- adenosine rises while orexin and histamine fall,
- cortisol briefly increases inhibition or reduces exploration,
- BDNF rises only after successful replay,
- endocannabinoids act with a delay on prior activity,
- replay weight and meta-plasticity change together,
- confidence rises only after several evidence-replay cycles.

The paper provides no evidence that any specific one of these BrainStem
couplings exists. It does, however, provide a method by which nonlinear
frequency couplings can in principle be investigated.

### 4.3 Possible Future Analysis Fields

A later, purely analytical BrainStem tool could examine time series of:

neuromodulator values per cycle, stability trajectories, confidence
trajectories, uncertainty trajectories, replay count, replay weight,
meta-plasticity, exploration pressure, inhibition level, revision
pressure, consolidation gain, gap-candidate signal frequency, drift
metrics, sleep/wake states.

Possible questions:

- Do recurring oscillations exist?
- Are there phase shifts between activating and inhibiting regulators?
- Does GABA respond to rising glutamate with appropriate timing?
- Do adenosine, histamine, and orexin couple differently in wake and
  sleep phases?
- Does a drift phase precede a changed frequency coupling?
- Do successful and unsuccessful replay phases differ in their nonlinear
  coupling patterns?
- Is an apparently stable mean actually the result of strong, opposing
  oscillations?

### 4.4 No Immediate CNN Integration

The paper works with supervised classes. For BrainStem, no sufficiently
validated labels currently exist for: a genuine learning gap, productive
uncertainty, a false hypothesis, helpful replay, a successful context
connection, an unsuccessful context strategy.

A CNN could therefore currently only learn artificially generated labels,
heuristically fixed classes, or self-referential results — none of which
would be compatible with the project's core principle.

The sensible order is:

1. Fully capture raw time series.
2. Check distributions and simple relationships.
3. Check time-lagged relationships.
4. Compare linear and nonlinear baselines.
5. Optionally test spectral/bispectral analysis as an external diagnostic
   tool.
6. Only consider a learning model once real outcomes exist.

### 4.5 Dropout as an Uncertainty Distribution

The paper uses dropout during both training and prediction. Repeated
predictions thereby yield a distribution rather than a single
classification value, which the authors use for uncertainty
quantification.

The transferable idea for BrainStem is not necessarily "add dropout," but:

> A decision should, where possible, arise from a distribution of
> repeated, slightly varied observations or evaluations.

Possible future BrainStem application:

- test the same hypothesis under several replay configurations,
- compare different context windows,
- consider different neuromodulator states,
- store not only the mean but the spread and stability of results,
- only solidify a decision if it remains robust across several variants.

This fits conceptually with `_critic_gate`, consolidation gates, warm-up
damping, repeated survival, confidence distributions, and exploration
before stabilization.

### 4.6 Explainability via Activation Maps

The paper uses class activation maps to reveal which regions of the
bispectral representation were particularly relevant for a
classification.

A transferable requirement for BrainStem: any future nonlinear analysis
should not only produce a result, but also show:

- which time windows were relevant,
- which neuromodulator pairs were involved,
- which frequency ranges were conspicuous,
- which replay or sleep phases shaped the result,
- whether the result is carried by a few extreme events or a stable
  trajectory.

A non-explainable classifier should not directly steer productive
learning decisions.

### 4.7 Stationarity as a Risk

The authors note that their current approach assumes a form of
stationarity and mention time-varying bispectra or recurrent structures
as possible extensions.

BrainStem is likely strongly non-stationary: new chunks change the data
population; sleep and wake phases differ; neuromodulators change their
regulatory effect; warm-up and long runs differ; Stage B changes system
dynamics; Cortisol Stage 2 would change the control loop.

A future spectral analysis should therefore not simply treat a complete
long run as one homogeneous time series. Sensible separate windows would
be: warm-up, stable wake operation, sleep transition, slow-wave phase,
wake-up phase, sensory deprivation, drift test, normal corpus run.

## 5. Document 3: Half-Möbius Topology and SqDRIFT

### 5.1 Direct Project Relevance

The main subject is a molecular system with half-Möbius topology,
covering STM/AFM measurements, tight-binding calculations,
multireference calculations, DFT calculations, aromaticity, electronic
states, state switching, and quantum-chemical sampling methods.

The molecular topology itself should not be adopted as a model for
BrainStem. A direct analogy between Möbius topology and language
understanding would not be scientifically justified.

### 5.2 Randomized Sampling of a Large State Space

The document describes SqDRIFT. The electronic Hamiltonian is decomposed
into elementary terms. For each randomized approximation, only a sample
of these terms is used, with selection probability depending on the
terms' coefficients. Relevant determinants are collected from many
randomized circuits, and the Hamiltonian is then classically
diagonalized in the selected subspace.

The core methodological idea: a huge state space is not searched
exhaustively. Instead, repeated weighted sampling identifies relevant
states, which are then evaluated more precisely in a bounded subspace.

**Possible BrainStem Relevance**

The current 512-item checkpoint is appropriate for the first complete
shadow pass because it is reproducible, bounded, fully progressive, and
GUI-friendly.

Later, a small exploratory sampling path could additionally be
investigated for: new hypotheses, old but recently changed hypotheses,
frequently re-observed hypotheses, replayed hypotheses, rarely selected
hypotheses, hypotheses from underrepresented context groups, hypotheses
with unusual neuromodulator development.

This sampling path should not replace the checkpoint. It would be an
additional exploration component against chronological sampling bias.

### 5.3 Extending a Selected Subspace

Ext-SqDRIFT first adopts a selected determinant space and then extends it
with related single and double excitations before re-diagonalizing.

The transferable idea for BrainStem:

> Do not immediately productively change a conspicuous candidate. First
> capture its local context neighborhood. Collect nearby alternatives and
> contrasting contexts. Check several possible connections in parallel.
> Re-evaluate the extended local subspace. Only stabilize a structure
> after repeated consolidation.

This fits the existing architecture of context expansion, window
strategies, gap-driven rereading, exploration pressure, inhibition,
replay, and consolidation. The extension must not, however, occur via
fixed linguistic neighborhood rules — it should arise from observed usage
and measured outcomes.

### 5.4 Cross-Checking Multiple Model Levels

The document compares and combines several computational levels: a
simple tight-binding model, multireference methods, DFT, classical
diagonalization, quantum-based sampling, and experimental AFM/STM
observations.

For BrainStem, the validation strategy — not the concrete physics — is
what matters. A future learning decision could have several separate
evidence pathways: raw observation, re-observation, stability, replay
behavior, neuromodulator response, error events, user feedback, dialogue
usefulness.

A productive structural decision should become stronger when multiple
independent pathways agree. A single score should not carry the entire
decision.

### 5.5 Measurement Bandwidth and Hidden State Switching

The document describes experimental situations in which molecules switch
between states. At higher switching rates, individual transitions can be
faster than the measurement bandwidth, causing the resulting picture to
appear smoothed or to overlay multiple states.

This point is directly relevant to BrainStem as a measurement warning. A
stable mean can have two very different causes:

- **Genuinely stable:** the value stays within a narrow range and changes
  only slightly.
- **Apparently stable:** the value switches rapidly between high and low
  states whose mean appears stable.

For BrainStem, the following should therefore be captured alongside
means: minimum and maximum, variance, quantiles, number of direction
reversals, number of threshold crossings, mean state duration, maximum
rate of change, frequency of short peaks, autocorrelation, switching rate
between discrete state ranges.

This particularly concerns: cortisol, glutamate/GABA, adenosine/
orexin/histamine, exploration/inhibition, replay weight, meta-plasticity,
stability, confidence, gap-candidate trajectories.

The GUI may continue to be bounded and downsampled. The underlying raw
data, however, should retain enough information to later detect fast
switching.

### 5.6 State Lifetime Instead of Just State Value

The supplementary materials analyze state lifetimes and switching rates
under different experimental conditions.

The resulting measurement idea for BrainStem: do not only ask "how high
is cortisol / stability / replay weight?" but additionally:

- How long does the state persist?
- How quickly does it return to the baseline range?
- How often does it switch?
- Which preceding signals increase dwell time?
- Which states are metastable?
- Which states occur only as brief transitions?
- Does sleep change state lifetime?
- Does re-observation change the lifetime of an uncertainty state?

## 6. Shared Architectural Principles From All Three Papers

### 6.1 Observation Before Intervention

All productive decisions should first be prepared as shadow observation.
Current BrainStem status: `modern_gap_candidate_shadow` observes candidate
signals; candidates remain `observed_only`; there is no gap
classification; there is no productive gap creation. This approach
remains correct.

### 6.2 Separate Demand From Connection

A hypothesis can show structural demand without it yet being clear
whether a gap actually exists, which context is suitable, whether a
connection should be stabilized, or whether revision or additional
evidence is more sensible. Possible future structures should therefore, at
minimum, separate: demand, offer, provisional pairing, observation of the
pairing, consolidation, stabilization, decay.

### 6.3 Local Self-Regulation Before Global Rules

Global fixed thresholds are to be avoided. Preferred instead: individual
trajectory, group-specific baseline, self-referential deviation, response
to new evidence, effect of replay, effect of neuromodulator state,
long-term direction of change.

### 6.4 Multiple Timescales

BrainStem should treat fast, medium, and slow changes separately (see
section 3.6 for the full breakdown: fast = current read/neuromodulator
state/attention/exploration; medium = re-observation/evidence
growth/replay results/stability development/strategy comparison; slow =
structural demand/consolidated connection/repeated repair/decay of
unproductive structures/long-term homeostasis).

### 6.5 Multiple Independent Evidence Pathways

Future decisions should ideally not depend on a single measured value.
Possible independent signals: re-observation, evidence count, stability
trajectory, replay trajectory, confidence trajectory, uncertainty
trajectory, error events, feedback, conflict count, context support,
dialogue success, neuromodulator response.

### 6.6 State Distribution Instead of a Single Value

For important decisions, not only means should be stored later, but
spread, distribution, persistence, state duration, switching frequency,
reproducibility across replay, sensitivity to context variation.

### 6.7 Bounded Sampling With an Exploration Component

The current checkpoint remains suitable for ordered corpus processing.
Later it can additionally be checked whether chronological processing
biases populations, whether old hypotheses are re-examined too rarely,
whether rare signal groups are underrepresented, or whether a small
weighted exploration component yields additional insight. No change to
the current 512-item checkpoint before a sampling bias has been measured.

## 7. Concrete Extensions for the Next Audit

The next technical step remains: **Modern Gap Candidate Signal
Distribution Audit V1**. The audit remains fully read-only and produces
no productive writes.

### 7.1 Base Distributions

To capture: number of shadow candidates, evidence count, re-observation
count, stability, hypothesis confidence, hypothesis uncertainty,
stability-confidence, stability-uncertainty, feedback count, error count,
conflict count, replay count, replay weight, meta-plasticity, hypothesis
age, time since last observation, time span between first and last
observation.

### 7.2 Group Comparisons

At minimum the following groups: no re-observation & no replay;
re-observation & no replay; replay & no re-observation; re-observation &
replay; high evidence count relative to population; long time without new
observation; repeatedly replayed but low stability change; repeatedly
observed but unchanged confidence; candidates with feedback; candidates
with error events; candidates with conflicts; candidates with extreme
neuromodulator profiles.

Groups 9–11 are presumably currently empty. The audit should still
structurally support them.

### 7.3 Homeostatic Trajectory Metrics

As far as data history is available: stability change per replay,
confidence change per additional evidence, uncertainty change per
re-observation, replay count without measurable progress, evidence growth
without stability growth, age without new evidence, timestamp of last
positive change, individual fluctuation range.

**Important:** if historical individual values are missing and only the
current state is available, the audit must not invent a trajectory
change. It must clearly disclose which metrics cannot be computed due to
missing history.

### 7.4 Neuromodulator Distributions

For each of the four main groups: dopamine, serotonin, glutamate, GABA,
noradrenaline, acetylcholine mean/median/quantiles; plus replay weight and
meta-plasticity. If further neuromodulators are not directly stored in
the shadow rows, they should not be simulated. A later extended shadow
version could add them if a reliable per-hypothesis mapping exists.

### 7.5 Multi-Scale Time Windows

If timestamps permit: newest candidates, older candidates, short
observation duration, long observation duration, recently updated, long
unchanged. No arbitrary content-based classes should arise from this —
the windows serve distribution analysis only.

### 7.6 Sampling Bias

To check: distribution of hypothesis ID across already-processed
candidates, distribution of `updated_at`, chunk-ID distribution, share of
different evidence counts along the checkpoint, share of replay/
re-observation per 512-item batch, stability per batch, differences
between early and later checkpoint batches. Goal: determine whether
chronological order processes certain populations first or last.

### 7.7 Switching and Smoothing Risk

Where cycle/history data is available: variance instead of just the mean,
rate of change, number of direction reversals, short peaks, state
duration, oscillation indicators. If this history is not available, the
audit should only document the gap — it must not construct a time series
from individual current values.

## 8. What Must Explicitly Not Be Built (From These Papers Alone)

The papers do not currently justify:

- a productive gap writer,
- a global stability threshold,
- a global uncertainty threshold,
- a rule "replay means gap,"
- a rule "re-observation means gap,"
- a fixed semantic distance function,
- a CNN for gap classification,
- a bispectrum as a productive learning regulator,
- a random replacement for the checkpoint,
- a direct transfer of chemical or quantum-mechanical topology onto
  language understanding,
- a productive structural connection without consolidation.

## 9. Long-Term Possible Roadmap

**Stage 1 — current shadow measurement:** capture signal distributions;
check sampling bias; identify homeostasis metrics; openly document
missing histories.

**Stage 2 — trajectory observation:** track candidates across multiple
re-observations; measure replay effect; capture stability and confidence
change; compare neuromodulator trajectories by group.

**Stage 3 — structural demand in shadow mode:** still no productive gap.
Possible shadow representation: local demand, missing context support,
persisting deviation, response to replay, possible context offers.

**Stage 4 — demand-offer pairing in shadow mode:** observe multiple
context offers; compare outcome differences; no productive connection; no
direct knowledge promotion.

**Stage 5 — consolidation gate:** only if empirically supported: repeated
survival of consolidation, `_critic_gate`, warm-up damping, controlled
budget, full traceability, automatic rollback on instability.

**Stage 6 — bounded productive gap opening:** only after successful
shadow validation. Productive scope: very small budget, initially at most
one transition per cycle, no fact promotion, no direct Relations or
Questions writes, full safety counting, full rollback, drift and
long-duration testing.

## 10. Key Findings in Short Form

- Structural demand is not the same as a learning gap.
- A learning gap is not the same as a new connection.
- A new connection is not the same as stabilized knowledge.
- Homeostatic demand should arise from a hypothesis's own trajectory, not
  from fixed global thresholds.
- Re-observation, replay, and stability are different signals and must
  not be equated.
- Nonlinear interactions between neuromodulators can matter more than
  individual means.
- Uncertainty should, where possible, be understood as a distribution
  over multiple observations or checks.
- Fast state switching can become invisible through means and GUI
  downsampling.
- Large state spaces can later be investigated through controlled
  sampling, without replacing ordered checkpoint processing.
- Multiple independent evidence pathways should precede any future
  structural decision.
- Structural changes belong on a slower, consolidation-gated timescale.
- None of the papers currently justifies a productive gap opening.

## 11. Binding Next Step

Following completion of this paper evaluation, the next technical step to
be built is: **Modern Gap Candidate Signal Distribution Audit V1**.

Properties:

- fully read-only,
- no database migration,
- no productive writes,
- no classification,
- no fixed gap threshold,
- no registry change,
- no checkpoint change,
- no change to `internal_learning_gaps`,
- no change to `chunk_attention_scores`,
- no Phase-5f/5g/5i experiments,
- `SAFETY [0,0,0]` remains a precondition.

The audit is extended with the measurement areas derived from the papers
above: homeostatic trajectories, group comparisons, multiple timescales,
neuromodulator couplings, state duration and switching rate, sampling
bias, replay effect, evidence growth without progress, and the difference
between actual stability and smoothed switching behavior.

**Until this audit has been evaluated, the productive gap lock remains
fully closed.**
