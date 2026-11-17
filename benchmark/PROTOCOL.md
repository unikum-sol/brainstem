# BrainStem Benchmark Protocol

Since 16 November 2026 learning is reproducible: two runs from the same database with the same code and the same run seed end in the same state (see "Learning Clock and Reproducibility" in the README). One run seed is therefore one exact sample, and all variance between runs comes from the run seed. A single run says little about a change, because two seeds of identical code already differ (for example +42 against +36 stable hypotheses in 100 cycles). Comparisons use several seeds per variant (Henderson et al. 2018; Bouthillier et al. 2021).

## Rules

1. **Fixed before the runs:** the snapshot, the variants, the seeds, the cycle count, the criteria K1 to K9 below and the non-inferiority margin. Write them into the experiment report before starting (Pineau et al. 2021).
2. **Same start:** every run starts from a fresh copy of the same snapshot database.
3. **Seeds:** at least 5 run seeds per variant, the same seeds for both variants (common random numbers), so differences are paired by seed. Default seeds: 0, 1, 2, 3, 4.
4. **Length:** 1,000 system cycles per run. The capture rate K5 needs at least 1,000 cycles because it only counts traces tagged at least 250 cycles before the end.
5. **Report every seed,** then per variant the mean, standard deviation, minimum and maximum, and the paired difference with a bootstrap 95 % interval.
6. **Pass rule per variant:** a criterion passes when it holds in all seeds but at most one; K9 (no exceptions, no hidden errors, integrity check) must hold in every seed.
7. **Non-inferiority:** a variant is "not worse" in a measure when the lower bound of the paired interval lies above minus the margin (default 5 % of the reference mean, derived from the seed baseline below). With five seeds the interval is wide, so the verdict rests on the margin fixed in advance, not on p-values.
8. **Wall time** is reported but never used to decide: on the storage pool it fluctuates far more than the code changes it. Use CPU time for speed claims, measured separately and paired.
9. **Record** code hash, snapshot, Python and SQLite version (written to `manifest.json` by the tool).

## Criteria

| No. | Criterion | Target |
|---|---|---|
| K1 | mean reward prediction error, wake and sleep | magnitude below 0.02 |
| K2 | phasic dopamine at 0 or 1 | under 2 % of cycles |
| K3 | sleep/wake ratio of noradrenaline / acetylcholine | at most 0.5 / 0.6 |
| K4 | meta parameters at a bound | 0 |
| K5 | capture rate of tagged traces (traces tagged at least 250 cycles before the end) | at least 0.85 |
| K6 | graduations per 1,000 cycles | compared between variants |
| K7 | learning-rate spread and range | SD above 0.01, values in [0.05, 0.95] |
| K8 | neuromodulators at 0 or 1 | under 5 % of cycles |
| K9 | exceptions, diagnostic findings, integrity check | none, none, ok |

Measures compared between variants: gain of stable hypotheses, graduations per 1,000 cycles, capture rate, facts, relations.

## Tool

```
python benchmark/benchmark.py run --snapshot <db> --code <project folder with ki_system> --label A --out <dir>
python benchmark/benchmark.py run --snapshot <db> --code <other project folder> --label B --out <dir>
python benchmark/benchmark.py compare --out <dir> --a A --b B
```

Options: `--seeds 0,1,2,3,4`, `--cycles 1000`, `--parallel 2` (runs at the same time; each needs a full copy of the database), `--keep-db` (keep the database copies, otherwise they are deleted after each run). `report --out <dir> --a A` prints one variant alone.

A seed baseline (the current code alone, five seeds) shows how far identical code spreads between seeds; use it to judge whether a margin is reasonable.

## Seed baseline (16/17 November 2026)

Code 283091a, snapshot of the production database after the second production run, seeds 0 to 4, 1,000 cycles each, five runs at the same time (about 5.8 hours). All nine criteria held in every seed, with no exceptions and no diagnostic findings.

| Measure | Mean | SD between seeds | Expected 95 % half-width of a paired mean difference between two identical variants |
|---|---|---|---|
| Gain of stable hypotheses | 328.6 | 5.2 (1.6 %) | 9.1 (2.8 %) |
| Facts | 1,200.2 | 7.2 (0.6 %) | 12.7 (1.1 %) |
| Relations | 1,329.0 | 5.0 (0.4 %) | 8.7 (0.7 %) |
| Capture rate K5 | 0.897 | 0.006 | 0.010 (1.1 %) |

A margin must be wider than the interval two identical variants produce, otherwise equal code is often not confirmed; 5 % leaves room above the 2.8 % of the most variable measure while still detecting a real loss of a few percent. The learning-rate spread (K7) lies between 0.011 and 0.012, close to its bound of 0.01.

## References

- Henderson, P. et al. (2018) Deep Reinforcement Learning That Matters. AAAI.
- Bouthillier, X. et al. (2021) Accounting for Variance in Machine Learning Benchmarks. MLSys.
- Pineau, J. et al. (2021) Improving Reproducibility in Machine Learning Research. JMLR.
- Sandve, G. K. et al. (2013) Ten Simple Rules for Reproducible Computational Research. PLoS Computational Biology.
- Lakens, D. (2017) Equivalence Tests. Social Psychological and Personality Science.
