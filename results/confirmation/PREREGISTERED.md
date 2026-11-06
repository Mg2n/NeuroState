# Confirmation run (Phase 4): preregistration

Written: Friday 6 November 2026, 00:16 +0300, before any confirmation run was started and before any prediction on these splits existed.
Project: Neurostate, AD vs HC classification on ds004504. Research use only: this is classification, not diagnosis.

## Why this run exists

The paper's headline numbers should not be chosen from the 17 variants already compared on splits 0, 1 and 2. These models and this analysis are fixed first. Whatever comes out is the headline result. It is reported as it comes out, and nothing is changed after seeing it.

## Models (fixed)

1. **Late fusion:** EEGNet 5-seed ensemble + baseline logistic regression, weights 0.5 / 0.5.
2. **Hybrid 5-seed ensemble.**
3. **EEGNet 5-seed ensemble.**

For reference only, not headline models: baseline logistic regression and baseline random forest.

## Settings (fixed)

- Task 05 defaults: 4-s windows, |correlation| microstate input, dropout 0.5, weight decay 1e-3, learning rate 1e-3, 40 epochs maximum, early-stopping patience 8, 64 crops per subject per epoch, batch size 64.
- Device: MPS.
- Decision threshold: 0.5, not tuned.
- Task: AD vs HC, all 65 subjects (36 AD, 29 HC). All windows kept. No subject excluded.
- Nothing is tuned: no regularisation search, threshold selection, or weight selection.

## Splits (fixed)

- 5-fold subject-wise stratified CV with repeat seeds 3, 4 and 5 (`StratifiedKFold(5, shuffle=True, random_state=repeat)`): 15 test folds.
- Checked before writing this file: every earlier result folder uses repeats 0-2 only (0 alone for the `fake` and `quick` runs).
- Microstate maps and early-stopping subjects come from each training fold only.
- Fold seed = 100 x repeat + fold. Network seed = fold seed + seed offset, with offsets 0, 1000, 2000, 3000, 4000.

## Outcomes (fixed)

For each of the 5 rows:
- balanced accuracy, AUC and F1: mean ± SD over the 15 folds
- pooled AUC with 95% bootstrap CI: 2000 subject resamples stratified by class, seed 12345, AUC computed per repeat and then averaged (same method as Task 05)
- sensitivity and specificity at threshold 0.5, AD = positive: mean ± SD over folds, and pooled over all out-of-fold predictions

Comparisons, paired over the 15 folds with the Nadeau-Bengio corrected resampled t-test (test/train 13/52, two-sided):
1. fusion vs EEGNet ensemble
2. hybrid ensemble vs EEGNet ensemble
3. fusion vs hybrid ensemble

## Details the request left open, fixed here before running

These were decided by the assistant, not specified in the user's request:
- **Ensemble:** mean subject probability over the 5 seeds, per fold. **Fusion:** 0.5 x that EEGNet mean + 0.5 x logistic-regression probability, per subject.
- **Primary metric:** balanced accuracy, so the 3 comparisons above on balanced accuracy are the primary tests. AUC and F1 are reported for the same comparisons as secondary.
- **p values:** reported unadjusted, with the number of tests stated (3 primary, 9 in total). A comparison is called significant only if p < 0.05 on the corrected test.
- **Earlier splits:** the same 5 rows computed from the existing runs on splits 0-2 are listed as context, to show how much the numbers move. They are not headline results.
- **Technical failure:** if a run crashes or the machine fails, it may be restarted with identical settings, and the restart is reported. A finished run is never rerun.
- **Code:** the training code and analysis script are frozen before launch (hashes below). The code change for this run only selects the repeat seeds. It is regression-tested on fake data first.

## Known limits, stated in advance

- **Same subjects.** The splits are new but the 65 subjects are the same ones used for all earlier comparisons. This removes selection on split noise, but it is not an independent test set. Choices made from earlier results (including the decision to test fusion) saw these subjects.
- **Fusion was picked after seeing it score highest** on splits 0-2. Regression towards the mean is expected and is what this run measures.
- **Training sets overlap** across folds and repeats. The corrected t-test allows for this but is approximate.
- **Small sample:** 13 test subjects per fold.

## Frozen code (added 6 November 2026, 00:24 +0300, before launch)

Snapshot: `results/_code_snapshots/step7_confirmation_2026-11-06/`. Regression on fake data (CPU): without the new `--first-repeat` option, predictions match the previous snapshot byte for byte. On the real labels, no test fold of repeats 3-5 equals one of repeats 0-2. The analysis script was tested on fake runs only.

```
aee1efe584440f6e2ff704904a3349ab29f941117bb0ae8deab8efe09d0ba630  run_experiment.py
76dde69ada4305f4806190ca36f6ea63b3a7aa36f30b0dbbf66bc42aeac71f97  models.py
b10c6c78925b69cd4c685f46e914fa5ddef979fcf01e9cf3f17b84f7a9908085  microstates.py
8afe2967e34a86c248845acb0a8da286c63d30e52e0cf1f4eaf84408d7ec61ac  confirmation.py
0f2d89eb377e05152a337ad1e65255f55080f5631bf54267236a768295a0195c  improve_analysis.py
6ab7bde4de1130ed7264e18fc8669f4dba53f4b3197a880856f2b4b50d16b667  summarize_main.py
142304ce874bed220f2c0ff648debf35df7585053df2dd3403481943365eca69  queue.sh
f1536c244b72dc947abffda38b940532ad13048b9d6fb95a12ee482ab3ea0b33  prepared/subjects.csv
```
