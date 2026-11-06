# Task 06: improvements (AD vs HC, ds004504)

Research use only: this classifies AD vs healthy controls; it is not a diagnostic test.

## Confirmation run: headline results (new splits, preregistered)

Models, settings and analysis were fixed in `results/confirmation/PREREGISTERED.md` before the run: repeat seeds 3, 4 and 5 (5 folds each), which no earlier result used; Task 05 defaults; MPS; 5 network seeds; threshold 0.5. Details in `results/confirmation/summary.md`.

| Model | Balanced acc. | AUC | F1 | Pooled AUC [95% CI] |
|---|---|---|---|---|
| fusion_eegnet_ens5_logreg | 0.869 ± 0.083 | 0.928 ± 0.077 | 0.853 ± 0.110 | 0.906 [0.833, 0.968] |
| hybrid_ens5 | 0.791 ± 0.082 | 0.901 ± 0.105 | 0.761 ± 0.124 | 0.863 [0.776, 0.936] |
| eegnet_ens5 | 0.816 ± 0.104 | 0.920 ± 0.088 | 0.803 ± 0.127 | 0.877 [0.793, 0.944] |
| baseline_logreg | 0.831 ± 0.094 | 0.917 ± 0.066 | 0.828 ± 0.102 | 0.904 [0.831, 0.962] |
| baseline_rf | 0.812 ± 0.075 | 0.880 ± 0.086 | 0.812 ± 0.087 | 0.868 [0.769, 0.946] |

Sensitivity and specificity (threshold 0.5, AD = positive):

| Model | Sensitivity (fold mean ± SD) | Specificity (fold mean ± SD) | Sensitivity (pooled) | Specificity (pooled) |
|---|---|---|---|---|
| fusion_eegnet_ens5_logreg | 0.794 ± 0.178 | 0.944 ± 0.103 | 0.796 | 0.943 |
| hybrid_ens5 | 0.694 ± 0.215 | 0.889 ± 0.163 | 0.694 | 0.885 |
| eegnet_ens5 | 0.757 ± 0.196 | 0.876 ± 0.148 | 0.759 | 0.874 |
| baseline_logreg | 0.787 ± 0.150 | 0.876 ± 0.134 | 0.787 | 0.874 |
| baseline_rf | 0.767 ± 0.141 | 0.858 ± 0.124 | 0.769 | 0.862 |

Preregistered comparisons (corrected t-test, unadjusted; balanced accuracy = primary):

| Comparison | Metric | Diff. mean (SD) | better / tied / worse | t | p |
|---|---|---|---|---|---|
| fusion_eegnet_ens5_logreg vs eegnet_ens5 | balanced_accuracy | +0.053 (0.091) | 10 / 2 / 3 | 1.03 | 0.32 |
| fusion_eegnet_ens5_logreg vs eegnet_ens5 | auc | +0.008 (0.048) | 5 / 5 / 5 | 0.30 | 0.768 |
| fusion_eegnet_ens5_logreg vs eegnet_ens5 | f1 | +0.050 (0.095) | 9 / 2 / 4 | 0.93 | 0.37 |
| hybrid_ens5 vs eegnet_ens5 | balanced_accuracy | -0.025 (0.080) | 3 / 5 / 7 | -0.55 | 0.591 |
| hybrid_ens5 vs eegnet_ens5 | auc | -0.019 (0.041) | 3 / 4 / 8 | -0.82 | 0.425 |
| hybrid_ens5 vs eegnet_ens5 | f1 | -0.042 (0.102) | 2 / 5 / 8 | -0.74 | 0.474 |
| fusion_eegnet_ens5_logreg vs hybrid_ens5 | balanced_accuracy | +0.078 (0.083) | 10 / 5 / 0 | 1.68 | 0.116 |
| fusion_eegnet_ens5_logreg vs hybrid_ens5 | auc | +0.027 (0.052) | 7 / 5 / 3 | 0.92 | 0.374 |
| fusion_eegnet_ens5_logreg vs hybrid_ens5 | f1 | +0.092 (0.110) | 10 / 5 / 0 | 1.49 | 0.159 |

None of the 3 primary comparisons is significant on the corrected test: fusion vs EEGNet ensemble +0.053 (p = 0.32), hybrid vs EEGNet ensemble -0.025 (p = 0.59), fusion vs hybrid ensemble +0.078 (p = 0.12). None of the 6 secondary AUC and F1 tests is significant either. Fusion has the highest mean balanced accuracy (0.869 ± 0.083), but this run does not show that it is better than either network ensemble. The hybrid does not beat EEGNet: its earlier +0.031 (p = 0.58, repeats 0-2) became -0.025 here, and it has the lowest mean balanced accuracy of the 5 rows. Fusion vs logistic regression was not preregistered, so it has no test: balanced accuracy 0.869 vs 0.831, pooled AUC 0.906 vs 0.904. From repeats 0-2 to 3-5, balanced accuracy moved +0.006 (fusion), -0.040 (hybrid), +0.016 (EEGNet), +0.014 (logistic regression) and +0.012 (random forest). The 65 subjects are the same as in all earlier comparisons, so this is not an independent test set.

## Exploratory comparisons (5-fold subject-wise CV x 3 repeats, same splits as Task 05)

Every setting was fixed in advance or chosen on training-fold subjects only. **No row was selected because it scored best on the test folds, and none should be read as 'the improved model'**: with this many variants compared on the same 65 subjects, the best row is expected to look better by chance. Differences are paired over the 15 outer folds; p = Nadeau-Bengio corrected resampled t-test (test/train 13/52), which accounts for overlapping training sets across repeats.

Comparator: single-seed rows are compared with the single-seed hybrid of the same run and device; 5-seed ensemble rows with the 5-seed hybrid ensemble (MPS). Task 05 hybrid (CPU, 1 seed) = 0.813 balanced accuracy.

| Change | Balanced accuracy (mean ± SD, 15 folds) | AUC (mean ± SD) | vs comparator: Δ bal. acc. (corrected p) | Δ AUC (corrected p) |
|---|---|---|---|---|
| Task 05 hybrid (CPU, 1 seed) | 0.813 ± 0.117 | 0.908 ± 0.103 | reference | reference |
| Task 05 EEGNet (CPU, 1 seed) | 0.852 ± 0.099 | 0.922 ± 0.078 | +0.039 (0.60) vs hybrid (1 seed) | +0.014 (0.74) |
| Late fusion 0.5 EEGNet + 0.5 logreg (CPU predictions) | 0.880 ± 0.078 | 0.921 ± 0.076 | +0.067 (0.22) vs hybrid (1 seed) | +0.013 (0.77) |
| Hybrid, MPS rerun (1 seed) - reference for MPS rows | 0.805 ± 0.099 | 0.911 ± 0.085 | reference | reference |
| EEGNet, MPS rerun (1 seed) | 0.790 ± 0.125 | 0.899 ± 0.084 | -0.015 (0.86) vs hybrid (1 seed) | -0.012 (0.76) |
| Late fusion 0.5 EEGNet + 0.5 logreg (MPS predictions) | 0.875 ± 0.095 | 0.915 ± 0.087 | +0.070 (0.31) vs hybrid (1 seed) | +0.004 (0.93) |
| EEGNet, threshold from inner-validation subjects | 0.783 ± 0.126 | 0.899 ± 0.084 | -0.022 (0.80) vs hybrid (1 seed) | unchanged (same scores) |
| Hybrid, threshold from inner-validation subjects | 0.795 ± 0.126 | 0.911 ± 0.085 | -0.010 (0.85) vs hybrid (1 seed) | unchanged (same scores) |
| EEGNet, 5-seed ensemble | 0.800 ± 0.091 | 0.916 ± 0.087 | -0.031 (0.58) vs hybrid ens. | +0.008 (0.73) |
| Hybrid, 5-seed ensemble - reference for ensemble rows | 0.831 ± 0.114 | 0.908 ± 0.096 | +0.027 (0.61) vs hybrid (1 seed) | -0.003 (0.82) |
| Hybrid, 5-seed ensemble + inner-validation threshold | 0.808 ± 0.131 | 0.908 ± 0.096 | -0.023 (0.52) vs hybrid ens. | unchanged (same scores) |
| EEGNet, 8-s windows, 5-seed ensemble | 0.817 ± 0.100 | 0.914 ± 0.090 | -0.014 (0.83) vs hybrid ens. | +0.006 (0.75) |
| Hybrid, 8-s windows, 5-seed ensemble | 0.828 ± 0.112 | 0.920 ± 0.075 | -0.003 (0.92) vs hybrid ens. | +0.012 (0.60) |
| Hybrid, one-hot microstate labels, 5-seed ensemble | 0.841 ± 0.098 | 0.922 ± 0.087 | +0.010 (0.87) vs hybrid ens. | +0.014 (0.48) |
| Hybrid, abs. correlation + 24 window features (MLP), 5-seed ensemble | 0.808 ± 0.117 | 0.913 ± 0.091 | -0.023 (0.53) vs hybrid ens. | +0.005 (0.76) |
| EEGNet, nested-CV regularisation, 5-seed ensemble | 0.829 ± 0.081 | 0.917 ± 0.087 | -0.002 (0.97) vs hybrid ens. | +0.009 (0.73) |
| Hybrid, nested-CV regularisation, 5-seed ensemble | 0.851 ± 0.122 | 0.919 ± 0.093 | +0.019 (0.68) vs hybrid ens. | +0.011 (0.34) |

## What each experiment tells us

- **fusion** (`results/improve_fusion/summary.md`): Weights fixed in advance. Highest balanced accuracy on both devices (0.880 CPU, 0.875 MPS), but corrected p = 0.22-0.31 vs the hybrid; AUC barely changes, so the gain is in where subjects fall relative to 0.5 (specificity up, sensitivity kept).
- **threshold** (`results/improve_threshold/summary.md`): No gain: with 8 validation subjects per fold the rule kept 0.5 in 8/15 (EEGNet) and 11/15 (hybrid) folds. Balanced accuracy changed in few folds (EEGNet 1 better / 3 worse, hybrid 2 better / 1 worse) and the means fell slightly (-0.007, p = 0.82; -0.010, p = 0.85).
- **ensemble** (`results/improve_ensemble/summary.md`): Averaging 5 seeds raises the hybrid by +0.027 (n.s.) and reduces seed noise; the hybrid ensemble is +0.031 over the EEGNet ensemble in balanced accuracy (p = 0.58); AUC difference -0.008 (p = 0.73).
- **win8** (`results/improve_win8/summary.md`): 8-s windows help EEGNet slightly (+0.017 ensemble, p = 0.42; +0.018 single-seed mean) and not the hybrid; no difference is significant.
- **onehot** (`results/improve_onehot/summary.md`): Highest of the three microstate-input variants (0.841), +0.010 over the |corr| hybrid ensemble (p = 0.87); within seed noise.
- **feats** (`results/improve_feats/summary.md`): Adding window-level features via an MLP did not help (-0.023, p = 0.53).
- **reg** (`results/improve_reg/summary.md`): Chosen per outer fold by inner 3-fold CV on training subjects only (mean inner-test AUC, grid dropout {0.5, 0.25} x weight decay {1e-3, 1e-4}); seed 0's choices were reused for seeds 1-4, so the ensemble does not capture selection noise. Channel dropout was not run. The default was kept in 6/15 (EEGNet) and 7/15 (hybrid) folds, and mean inner AUC was nearly flat across the grid (0.856-0.859 EEGNet, 0.861-0.863 hybrid). Against the matching reference ensemble: hybrid 0.851, +0.019 (p = 0.68; AUC +0.011, p = 0.34; 2 better / 12 tied / 1 worse); EEGNet 0.829, +0.029 (p = 0.29; AUC +0.002, p = 0.85; 5 / 10 / 0). Fold differences come only from folds whose setting changed, and single-seed means barely move (hybrid +0.004, EEGNet +0.001), so this is not evidence that regularisation helps. Hybrid vs EEGNet with these settings: +0.021 (p = 0.68), AUC +0.002 (p = 0.94).
- **seed noise**: single-seed balanced accuracy varies by SD 0.010 (EEGNet) to 0.020 (hybrid) across 5 seeds on MPS, and the single task-05 CPU EEGNet run (0.852) lies above all 5 MPS seeds (see `results/improve_mps_rerun/device_check.md`). Single-run differences of a few points are not evidence either way.
- **not run**: channel-dropout augmentation (no such option exists; left out of the reduced grid).

## Secondary task: AD vs FTD vs HC (88 subjects, 87 without sub-086, chance = 0.333)

Separate from the table above: these splits stratify over 3 groups, so a difference against the AD vs HC hybrid would not be valid. `eegnet`, `hybrid` = seed offset 0; `*_ens5` = 5-seed ensemble. Details in `results/improve_3class/summary.md` and `results/improve_3class_no086/summary.md`.

| Model | Balanced acc. (mean ± SD) | Macro-F1 | Macro AUC (one-vs-rest) |
|---|---|---|---|
| baseline_logreg | 0.554 ± 0.102 | 0.534 ± 0.099 | 0.745 ± 0.052 |
| baseline_rf | 0.579 ± 0.087 | 0.565 ± 0.090 | 0.746 ± 0.055 |
| eegnet | 0.568 ± 0.086 | 0.536 ± 0.097 | 0.758 ± 0.067 |
| hybrid | 0.539 ± 0.116 | 0.510 ± 0.124 | 0.760 ± 0.085 |
| eegnet_ens5 | 0.572 ± 0.084 | 0.542 ± 0.097 | 0.763 ± 0.065 |
| hybrid_ens5 | 0.569 ± 0.100 | 0.540 ± 0.099 | 0.763 ± 0.084 |

With sub-086 removed from the evaluation only:

| Model | Balanced acc. (mean ± SD) | Macro-F1 | Macro AUC (one-vs-rest) |
|---|---|---|---|
| baseline_logreg | 0.557 ± 0.101 | 0.538 ± 0.099 | 0.754 ± 0.052 |
| baseline_rf | 0.584 ± 0.083 | 0.570 ± 0.089 | 0.753 ± 0.049 |
| eegnet | 0.561 ± 0.075 | 0.526 ± 0.084 | 0.754 ± 0.062 |
| hybrid | 0.541 ± 0.110 | 0.507 ± 0.116 | 0.765 ± 0.087 |
| eegnet_ens5 | 0.566 ± 0.079 | 0.533 ± 0.090 | 0.763 ± 0.064 |
| hybrid_ens5 | 0.567 ± 0.092 | 0.535 ± 0.089 | 0.764 ± 0.083 |

With sub-086 removed from training, early stopping, map fitting and test (87 subjects, same outer folds):

| Model | Balanced acc. (mean ± SD) | Macro-F1 | Macro AUC (one-vs-rest) |
|---|---|---|---|
| baseline_logreg | 0.594 ± 0.093 | 0.579 ± 0.099 | 0.755 ± 0.058 |
| baseline_rf | 0.576 ± 0.070 | 0.562 ± 0.065 | 0.749 ± 0.050 |
| eegnet | 0.554 ± 0.096 | 0.528 ± 0.100 | 0.760 ± 0.068 |
| hybrid | 0.522 ± 0.098 | 0.480 ± 0.097 | 0.763 ± 0.066 |
| eegnet_ens5 | 0.572 ± 0.070 | 0.546 ± 0.069 | 0.769 ± 0.075 |
| hybrid_ens5 | 0.580 ± 0.116 | 0.557 ± 0.119 | 0.770 ± 0.075 |

Effect of that removal on identical test subjects (this run minus the full-cohort run scored without sub-086):

| Model | Metric | This run − with086 (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|
| baseline_logreg | balanced_accuracy | +0.037 (0.048) | 8 / 5 / 2 | 0.00977 | 0.188 |
| baseline_logreg | f1 | +0.041 (0.058) | 10 / 4 / 1 | 0.0137 | 0.227 |
| baseline_logreg | auc | +0.000 (0.031) | 6 / 3 / 6 | 0.97 | 0.986 |
| baseline_rf | balanced_accuracy | -0.008 (0.085) | 5 / 5 / 5 | 0.846 | 0.874 |
| baseline_rf | f1 | -0.008 (0.088) | 5 / 4 / 6 | 0.765 | 0.881 |
| baseline_rf | auc | -0.003 (0.042) | 7 / 3 / 5 | 0.91 | 0.889 |
| eegnet_ens5 | balanced_accuracy | +0.006 (0.081) | 6 / 6 / 3 | 0.715 | 0.896 |
| eegnet_ens5 | f1 | +0.013 (0.100) | 6 / 6 / 3 | 0.57 | 0.821 |
| eegnet_ens5 | auc | +0.006 (0.037) | 5 / 3 / 7 | 0.97 | 0.787 |
| hybrid_ens5 | balanced_accuracy | +0.013 (0.072) | 7 / 6 / 2 | 0.57 | 0.75 |
| hybrid_ens5 | f1 | +0.022 (0.094) | 7 / 4 / 4 | 0.365 | 0.68 |
| hybrid_ens5 | auc | +0.006 (0.030) | 8 / 3 / 4 | 0.569 | 0.736 |

Settings were fixed in advance (Task 05 defaults) instead of the task's 'best setting', because picking the best table row would select on test folds. All models are above chance (0.333) and within noise of each other: hybrid ensemble 0.569 vs EEGNet ensemble 0.572 (-0.002, p = 0.97), so microstate input adds nothing measurable here. FTD is the weak class: recall 0.232 (EEGNet ensemble), 0.290 (hybrid ensemble), 0.391 (logistic regression), and both network ensembles label FTD subjects as AD more often than as FTD. Leaving sub-086 out of the evaluation only moves balanced accuracy by at most 0.007.

Removing sub-086 from training, map fitting and test as well (same outer folds, so identical test subjects) changes balanced accuracy by +0.037 for logistic regression (p = 0.19; Wilcoxon 0.0098, not corrected for the 12 tests in this comparison), -0.008 for random forest (p = 0.87), +0.006 for the EEGNet ensemble (p = 0.90) and +0.013 for the hybrid ensemble (p = 0.75). None is significant on the corrected test. Among the 4 models above, logistic regression moves from lowest to highest, so their order depends on one subject and should not be read as a ranking. Hybrid vs EEGNet ensemble stays null (+0.008, p = 0.90). On the same subjects, FTD recall rises for both network ensembles (EEGNet 0.212 → 0.348, hybrid 0.288 → 0.424) but not for the baselines, and HC recall falls for both ensembles, so this is partly a trade between classes. There is no control run, so this cannot all be attributed to sub-086: removing any training subject also changes the early-stopping split and the batches.

Generated 2026-11-06 22:22 by `experiments/make_improvements.py`.
