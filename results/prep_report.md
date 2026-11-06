# Preprocessing report (task 03)

**Result: PASS** - 88/88 subjects prepared, 0 excluded, 1 amplitude flag(s), 0 flat-channel flag(s).

## Settings

- Command: `.venv/bin/python prep.py --bids ../ds004504 --out ../prepared` (log: `results/prep_log.txt`)
- Source: derivatives 88 (dataset authors' preprocessing: 0.5-45 Hz band-pass, ASR, ICA)
- 19 channels in fixed order, average reference, resampled to 128 Hz; `dl` = 1-40 Hz (EEGNet), `ms` = 2-20 Hz (microstates); FIR zero-phase; float32 µV
- Checked 2026-11-03 23:01; Python 3.12.16, mne 1.13.2, numpy 2.5.4, scipy 1.18.1

## Checks

| Check | Result |
|---|---|
| `.npz` files in prepared/ | 88 |
| Subjects in `subjects.csv` | 88 of 88 in participants.tsv |
| Excluded / missing subjects | none |
| Skip messages in prep log | none |
| Channel order identical to `Fp1,Fp2,F7,F3,Fz,F4,F8,T3,C3,Cz,C4,T4,T5,P3,Pz,P4,T6,O1,O2` | yes, all |
| Sampling rate 128 Hz | yes, all |
| `dl` and `ms` same shape, 19 rows | yes, all |
| NaN / Inf values (dl + ms) | 0 |
| Duration matches source recording (max difference) | 0.00 s |
| Subjects with std > 3x median (6.72 µV) | sub-086 |
| Subjects with a flat channel (std < 0.5 µV) | none |

## Issues found (no subject excluded)

- **sub-086 (FTD)**: overall std 27.0 µV = 4.0x the median, high on all channels for the whole recording (90% of 4-s windows exceed 100 µV; loudest F4 50 µV). Kept. FTD is not in the main AD vs HC comparison; if FTD is analysed, report results with and without it.
- Isolated large transients (> 500 µV) remain in 8 subjects (sub-012, sub-016, sub-022, sub-040, sub-047, sub-048, sub-074, sub-080); the worst is sub-040 (1466 µV). They are short (median subject: 2.7% of 4-s windows > 100 µV). Kept. Decision (2026-11-03, before task 05): no window rejection; all windows of all subjects are used, since the derivatives are already ASR/ICA-cleaned.
- Short recordings (< 6 min): sub-003 (AD, 306 s). Kept; these subjects contribute fewer 4-s windows, which matters if windows are pooled.

## Durations (s, after prep)

| Group | n | min | median | max | total (min) |
|---|---|---|---|---|---|
| AD (A) | 36 | 306.1 | 820.0 | 1281.7 | 486 |
| HC (C) | 29 | 748.5 | 814.6 | 989.9 | 402 |
| FTD (F) | 23 | 479.1 | 699.1 | 1014.5 | 276 |

## Amplitude (1-40 Hz copy, µV)

| Group | std median | std min | std max | max std/median ratio | max abs value |
|---|---|---|---|---|---|
| AD | 6.62 | 3.96 | 18.36 | 2.73 | 743 |
| HC | 7.04 | 3.69 | 11.63 | 1.73 | 1466 |
| FTD | 6.14 | 3.78 | 26.98 | 4.01 | 735 |

Five highest-amplitude subjects (none are excluded; listed for transparency):

| Subject | Group | std (µV) | ratio to median | loudest channel (std) | max abs (µV) |
|---|---|---|---|---|---|
| sub-086 | FTD | 26.98 | 4.01 | F4 (50.0) | 368 |
| sub-030 | AD | 18.36 | 2.73 | Fp2 (25.4) | 411 |
| sub-027 | AD | 12.65 | 1.88 | F8 (16.0) | 491 |
| sub-069 | FTD | 11.80 | 1.76 | T5 (14.4) | 178 |
| sub-064 | HC | 11.63 | 1.73 | T5 (20.2) | 179 |

Large transients (largest absolute value per subject; share of non-overlapping 4-s windows with any channel > 100 µV). Not removed: the data are the authors' ASR/ICA-cleaned derivatives.

| Subject | Group | max abs (µV) | channel | at t (s) | windows > 100 µV |
|---|---|---|---|---|---|
| sub-040 | HC | 1466 | T3 | 872.4 | 5.4% |
| sub-016 | AD | 743 | T4 | 533.1 | 7.4% |
| sub-074 | FTD | 735 | O2 | 209.4 | 6.7% |
| sub-080 | FTD | 695 | F7 | 310.8 | 3.9% |
| sub-022 | AD | 649 | Pz | 130.0 | 12.7% |
| sub-086 | FTD | 368 | F4 | 10.9 | 89.6% |
| sub-026 | AD | 238 | F4 | 562.1 | 24.6% |
| sub-067 | FTD | 210 | Fp2 | 348.5 | 22.5% |
| sub-030 | AD | 411 | Fz | 504.6 | 21.0% |
| sub-048 | HC | 557 | O2 | 905.4 | 18.6% |
| median, all subjects | | 185 | | | 2.7% |

## Spectral check: AD vs HC

Relative band power (fraction of 1-30 Hz power, mean of 19 channels), group mean ± SD. p = two-sided Mann-Whitney U, AD vs HC, uncorrected. Descriptive only: not used for model selection.

| Band | AD | HC | FTD | AD vs HC p |
|---|---|---|---|---|
| delta 1-4 Hz | 0.409 ± 0.187 | 0.283 ± 0.154 | 0.377 ± 0.173 | 0.00696 |
| theta 4-8 Hz | 0.214 ± 0.101 | 0.095 ± 0.034 | 0.156 ± 0.092 | 3.39e-07 |
| alpha 8-13 Hz | 0.225 ± 0.178 | 0.438 ± 0.171 | 0.254 ± 0.165 | 1.08e-05 |
| beta 13-30 Hz | 0.153 ± 0.087 | 0.184 ± 0.086 | 0.214 ± 0.137 | 0.121 |
| peak alpha freq (Hz, 6-14) | 7.81 ± 1.80 | 9.80 ± 0.99 | 9.07 ± 1.66 | 1.27e-05 |

Expected pattern (AD more slow-wave, less alpha than HC): slow-wave (delta+theta) higher in AD: **yes**; alpha lower in AD: **yes**.

## Figures

- `figures/prep/raw_eeg_AD_vs_HC.png` - 10 s (t = 60-70 s) of the 1-40 Hz copy, sub-001 (AD) and sub-037 (HC): the first subject of each group in participants.tsv.
- `figures/prep/psd_per_group.png` - Welch PSD (4-s windows), mean of 19 channels, group mean ± SEM of log10 power.

## Per-subject table

| Subject | Group | Duration (s) | std (µV) | ratio | min ch std | rel. alpha | flags |
|---|---|---|---|---|---|---|---|
| sub-001 | A | 599.8 | 4.82 | 0.72 | C3 3.28 | 0.097 | - |
| sub-002 | A | 793.1 | 6.54 | 0.97 | C3 4.24 | 0.542 | - |
| sub-003 | A | 306.1 | 7.67 | 1.14 | T4 4.97 | 0.464 | - |
| sub-004 | A | 706.1 | 6.50 | 0.97 | C4 4.51 | 0.065 | - |
| sub-005 | A | 804.1 | 5.51 | 0.82 | Fp2 1.81 | 0.125 | - |
| sub-006 | A | 632.4 | 7.65 | 1.14 | Cz 5.29 | 0.668 | - |
| sub-007 | A | 766.4 | 5.90 | 0.88 | F4 4.90 | 0.100 | - |
| sub-008 | A | 793.4 | 11.12 | 1.65 | C4 7.04 | 0.040 | - |
| sub-009 | A | 612.6 | 6.62 | 0.98 | C3 4.71 | 0.481 | - |
| sub-010 | A | 1281.7 | 3.96 | 0.59 | Fp1 2.63 | 0.379 | - |
| sub-011 | A | 769.9 | 9.01 | 1.34 | Fz 5.53 | 0.230 | - |
| sub-012 | A | 883.5 | 7.70 | 1.14 | Fp1 4.97 | 0.177 | - |
| sub-013 | A | 838.1 | 7.07 | 1.05 | C3 3.87 | 0.098 | - |
| sub-014 | A | 934.4 | 9.05 | 1.35 | Cz 4.51 | 0.055 | - |
| sub-015 | A | 901.4 | 5.29 | 0.79 | C3 3.43 | 0.558 | - |
| sub-016 | A | 972.4 | 6.11 | 0.91 | C3 3.75 | 0.062 | - |
| sub-017 | A | 843.4 | 7.99 | 1.19 | C3 5.60 | 0.090 | - |
| sub-018 | A | 845.1 | 8.84 | 1.32 | C3 7.12 | 0.220 | - |
| sub-019 | A | 918.6 | 4.58 | 0.68 | C3 2.95 | 0.242 | - |
| sub-020 | A | 869.3 | 5.20 | 0.77 | Fp2 2.76 | 0.138 | - |
| sub-021 | A | 920.3 | 4.87 | 0.72 | Fp2 3.09 | 0.208 | - |
| sub-022 | A | 821.9 | 11.18 | 1.66 | C4 7.51 | 0.112 | - |
| sub-023 | A | 834.7 | 6.60 | 0.98 | Cz 4.39 | 0.227 | - |
| sub-024 | A | 759.8 | 6.97 | 1.04 | Cz 5.13 | 0.141 | - |
| sub-025 | A | 684.4 | 7.68 | 1.14 | C4 4.28 | 0.589 | - |
| sub-026 | A | 898.6 | 9.05 | 1.35 | Cz 4.84 | 0.089 | - |
| sub-027 | A | 826.2 | 12.65 | 1.88 | C3 8.78 | 0.040 | - |
| sub-028 | A | 818.1 | 5.80 | 0.86 | C3 4.08 | 0.128 | - |
| sub-029 | A | 736.7 | 7.34 | 1.09 | Cz 5.21 | 0.100 | - |
| sub-030 | A | 554.1 | 18.36 | 2.73 | Pz 13.16 | 0.049 | - |
| sub-031 | A | 1150.8 | 6.09 | 0.91 | Fp2 3.69 | 0.380 | - |
| sub-032 | A | 797.8 | 5.86 | 0.87 | Pz 4.52 | 0.235 | - |
| sub-033 | A | 705.4 | 6.37 | 0.95 | C3 4.59 | 0.292 | - |
| sub-034 | A | 969.9 | 4.26 | 0.63 | Fp2 2.16 | 0.131 | - |
| sub-035 | A | 741.0 | 6.63 | 0.99 | Cz 4.25 | 0.101 | - |
| sub-036 | A | 841.4 | 8.24 | 1.23 | Fp1 5.66 | 0.433 | - |
| sub-037 | C | 777.1 | 8.19 | 1.22 | C4 4.63 | 0.603 | - |
| sub-038 | C | 891.4 | 5.61 | 0.84 | Fp1 3.00 | 0.303 | - |
| sub-039 | C | 850.1 | 9.50 | 1.41 | T3 6.62 | 0.708 | - |
| sub-040 | C | 965.7 | 9.38 | 1.40 | Fp1 7.06 | 0.380 | - |
| sub-041 | C | 886.1 | 5.55 | 0.83 | C4 3.45 | 0.445 | - |
| sub-042 | C | 963.0 | 8.65 | 1.29 | C4 5.70 | 0.333 | - |
| sub-043 | C | 829.1 | 4.89 | 0.73 | Fp1 2.53 | 0.195 | - |
| sub-044 | C | 881.6 | 7.51 | 1.12 | C3 4.56 | 0.645 | - |
| sub-045 | C | 851.6 | 5.67 | 0.84 | Fp2 3.26 | 0.242 | - |
| sub-046 | C | 753.0 | 9.29 | 1.38 | C4 7.23 | 0.444 | - |
| sub-047 | C | 807.0 | 6.78 | 1.01 | C3 4.18 | 0.546 | - |
| sub-048 | C | 989.9 | 9.30 | 1.38 | Cz 4.79 | 0.294 | - |
| sub-049 | C | 780.2 | 6.95 | 1.03 | F7 3.59 | 0.625 | - |
| sub-050 | C | 817.6 | 7.42 | 1.10 | C4 4.85 | 0.311 | - |
| sub-051 | C | 753.3 | 7.54 | 1.12 | T3 4.91 | 0.237 | - |
| sub-052 | C | 760.1 | 7.04 | 1.05 | C3 5.69 | 0.422 | - |
| sub-053 | C | 780.5 | 9.14 | 1.36 | P4 5.79 | 0.464 | - |
| sub-054 | C | 837.6 | 8.03 | 1.19 | O1 4.57 | 0.603 | - |
| sub-055 | C | 814.6 | 7.03 | 1.05 | Cz 5.23 | 0.453 | - |
| sub-056 | C | 791.3 | 7.18 | 1.07 | C3 5.01 | 0.730 | - |
| sub-057 | C | 796.5 | 6.09 | 0.91 | C3 3.82 | 0.492 | - |
| sub-058 | C | 756.8 | 6.66 | 0.99 | Pz 4.70 | 0.539 | - |
| sub-059 | C | 787.1 | 3.69 | 0.55 | Fp2 2.46 | 0.281 | - |
| sub-060 | C | 748.5 | 5.24 | 0.78 | T4 3.34 | 0.110 | - |
| sub-061 | C | 803.3 | 6.51 | 0.97 | T4 3.18 | 0.311 | - |
| sub-062 | C | 898.7 | 8.42 | 1.25 | C4 4.91 | 0.653 | - |
| sub-063 | C | 804.9 | 4.51 | 0.67 | Fp2 3.28 | 0.330 | - |
| sub-064 | C | 848.1 | 11.63 | 1.73 | T4 8.11 | 0.711 | - |
| sub-065 | C | 884.1 | 4.78 | 0.71 | Pz 3.01 | 0.306 | - |
| sub-066 | F | 549.8 | 8.90 | 1.32 | F7 6.50 | 0.159 | - |
| sub-067 | F | 643.1 | 11.49 | 1.71 | Cz 4.82 | 0.160 | - |
| sub-068 | F | 573.1 | 4.88 | 0.73 | Fp2 3.18 | 0.424 | - |
| sub-069 | F | 636.1 | 11.80 | 1.76 | Fp2 8.72 | 0.222 | - |
| sub-070 | F | 479.1 | 4.08 | 0.61 | Fp2 1.50 | 0.221 | - |
| sub-071 | F | 618.9 | 5.45 | 0.81 | Cz 4.42 | 0.484 | - |
| sub-072 | F | 657.4 | 8.95 | 1.33 | C4 6.12 | 0.073 | - |
| sub-073 | F | 854.6 | 4.24 | 0.63 | C3 2.86 | 0.417 | - |
| sub-074 | F | 1014.5 | 6.14 | 0.91 | C3 3.85 | 0.245 | - |
| sub-075 | F | 748.2 | 8.40 | 1.25 | Fz 5.25 | 0.417 | - |
| sub-076 | F | 818.8 | 6.30 | 0.94 | Fp2 3.91 | 0.139 | - |
| sub-077 | F | 699.1 | 4.30 | 0.64 | C3 2.66 | 0.147 | - |
| sub-078 | F | 870.9 | 5.62 | 0.84 | Cz 3.38 | 0.113 | - |
| sub-079 | F | 816.7 | 7.72 | 1.15 | Cz 3.61 | 0.276 | - |
| sub-080 | F | 915.1 | 8.42 | 1.25 | C4 3.96 | 0.673 | - |
| sub-081 | F | 824.5 | 3.86 | 0.57 | C3 2.59 | 0.242 | - |
| sub-082 | F | 777.6 | 5.40 | 0.80 | Pz 3.84 | 0.430 | - |
| sub-083 | F | 913.2 | 3.78 | 0.56 | Pz 1.84 | 0.127 | - |
| sub-084 | F | 652.1 | 6.14 | 0.91 | Fp2 4.04 | 0.095 | - |
| sub-085 | F | 560.1 | 8.82 | 1.31 | Cz 4.07 | 0.061 | - |
| sub-086 | F | 578.8 | 26.98 | 4.01 | P4 15.27 | 0.045 | amp>3x |
| sub-087 | F | 602.8 | 6.05 | 0.90 | C3 3.59 | 0.223 | - |
| sub-088 | F | 784.7 | 6.57 | 0.98 | C3 4.90 | 0.446 | - |

_Runtime: 11 s._
