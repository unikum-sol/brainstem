# Data for "Learning on an Experience Clock"

Unchanged copies of the measured BrainStem data that the paper and its figures use. `../figures/make_figures.py` reads only this folder.

| Path | Content | Origin |
|---|---|---|
| `seed_baseline/seed_0` to `seed_4` | `learn_metrics.csv` (one row per learning cycle, 24 logged signals plus wall seconds) and `learn_summary.json` (counts at the end of the run) for the five-seed baseline, code 283091a, 1,000 cycles each | `benchmarks/2026-11-16_seed_baseline/baseline_283091a/` |
| `seed_baseline/manifest.json` | code hash, snapshot size and hash, Python and SQLite version, machine, start and end time of the baseline | same folder |
| `det_1000` | the same two files for the 1,000-cycle quality run of 16 November 2026 (code of the learning-clock change, run alone) | `Brainstem/Audits/reproduzierbarkeit_2026-11-16/det_1000/` |
| `table_comparisons/aa_baseline.txt` | table-by-table comparison of two 100-cycle runs before the fix (time columns excluded) | `Brainstem/Audits/reproduzierbarkeit_2026-11-16/` |
| `table_comparisons/aa_v4.txt` | the same after the fix, all columns including timestamps | same folder |
| `table_comparisons/aa_resume.txt` | 50 cycles, restart, 50 cycles against 100 cycles in one process | same folder |
| `table_comparisons/aa_seed1.txt` | run seed 1 against run seed 0, 100 cycles | same folder |

The first line of each comparison file gives the number of identical and differing tables; the following lines list the differing tables with their row counts in both runs.

Column `seconds` in `learn_metrics.csv` is wall-clock time per cycle and is the only column that is expected to differ between repeated runs. The production database itself (8.09 GB, derived from German Wikipedia) is not included.
