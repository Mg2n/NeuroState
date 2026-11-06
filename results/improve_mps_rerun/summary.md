# Main experiment: AD vs HC (5-fold subject-wise CV x 3 repeats)

Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.

Subjects: 65 (36 AD, 29 HC), ds004504 derivatives, prepared as in `results/prep_report.md` (no window rejection). Every subject is in exactly one test fold per repeat; early-stopping subjects (15%) and microstate maps come from the training fold only. Subject score = mean of its 4-s window probabilities; threshold 0.5.

## Results

Mean ± SD over the 15 test folds; *pooled* = all out-of-fold subject predictions of a repeat scored together, averaged over repeats. AUC 95% CI: subject bootstrap (2000 resamples, stratified, seed 12345).

| Model | Balanced accuracy (fold mean ± SD) | AUC (fold mean ± SD) | F1 (fold mean ± SD) | Pooled bal. acc. | Pooled AUC [95% CI] | Pooled F1 |
|---|---|---|---|---|---|---|
| A. Baseline: microstate features + logistic regression | 0.817 ± 0.105 | 0.907 ± 0.091 | 0.812 ± 0.119 | 0.821 | 0.898 [0.820, 0.960] | 0.822 |
| A. Baseline: microstate features + random forest | 0.800 ± 0.075 | 0.857 ± 0.080 | 0.802 ± 0.092 | 0.805 | 0.844 [0.745, 0.928] | 0.808 |
| B. EEGNet alone | 0.790 ± 0.125 | 0.899 ± 0.084 | 0.790 ± 0.122 | 0.795 | 0.875 [0.795, 0.937] | 0.799 |
| C. Hybrid (EEGNet + microstate CNN) | 0.805 ± 0.099 | 0.911 ± 0.085 | 0.755 ± 0.183 | 0.809 | 0.885 [0.815, 0.943] | 0.783 |

Pooled balanced accuracy per repeat (shows split-to-split variation):

| Model | repeat 0 | repeat 1 | repeat 2 |
|---|---|---|---|
| baseline_logreg | 0.837 | 0.789 | 0.837 |
| baseline_rf | 0.803 | 0.806 | 0.806 |
| eegnet | 0.720 | 0.827 | 0.837 |
| hybrid | 0.823 | 0.774 | 0.830 |

Sensitivity and specificity at threshold 0.5 (all out-of-fold subject predictions, 3 repeats pooled; AD = positive class):

| Model | Sensitivity (AD recall) | Specificity (HC recall) | Median score, AD | Median score, HC |
|---|---|---|---|---|
| baseline_logreg | 0.769 | 0.874 | 0.928 | 0.192 |
| baseline_rf | 0.759 | 0.851 | 0.795 | 0.286 |
| eegnet | 0.750 | 0.839 | 0.721 | 0.272 |
| hybrid | 0.676 | 0.943 | 0.749 | 0.209 |

The hybrid misses more AD subjects than EEGNet (sensitivity 0.676 vs 0.750) and fewer HC subjects; its AUC is close to EEGNet's, so most of the gap is in which side of the fixed 0.5 threshold subjects fall on, not in how they are ranked. Fewer AD subjects caught lowers F1 (AD = positive) more than balanced accuracy. The 0.5 threshold was fixed in advance and is not tuned here.

## Hybrid vs EEGNet (paired)

| Metric | Hybrid − EEGNet, mean (SD) | folds hybrid better / tied / worse | Wilcoxon signed-rank p | Corrected resampled t-test p |
|---|---|---|---|---|
| balanced accuracy | +0.015 (0.145) | 7 / 2 / 6 | 0.852 | 0.86 (t = 0.18) |
| auc | +0.012 (0.067) | 6 / 5 / 4 | 0.656 | 0.763 (t = 0.31) |
| f1 | -0.035 (0.173) | 5 / 2 / 8 | 0.444 | 0.721 (t = -0.36) |

Pooled AUC difference hybrid − EEGNet: +0.011, paired subject-bootstrap 95% CI [-0.022, +0.045]; share of resamples with hybrid > EEGNet: 73.7%.

Wilcoxon uses the 15 fold scores (zero differences dropped, two-sided). Folds from different repeats share subjects, so they are not independent and the plain Wilcoxon p is optimistic; the corrected resampled t-test (Nadeau & Bengio 2003, test/train ratio 13/52) accounts for this and is the more conservative number.

Secondary (not pre-specified in the task): hybrid − logistic-regression baseline, balanced accuracy -0.013; Wilcoxon p 0.608; corrected t-test p 0.876.

## Leakage demo vs honest subject-wise evaluation

Not run (`--skip-leak`).

## Comparison with published results on ds004504

| Study | Reported | Task / protocol | Why not directly comparable |
|---|---|---|---|
| Two-Stage Microstate Fusion (Biosensors 2026) | 74.3% balanced acc. | dementia vs HC, LOSO | different class definition ('dementia'; check whether FTD is included) and leave-one-subject-out |
| DICE-Net (Miltiadous et al. 2023) | 83.28% acc. | AD vs HC, LOSO | plain accuracy, not balanced accuracy; LOSO trains on 64 subjects per fold vs about 52 here |
| ADformer (2024) | 92.82% F1 | AD vs HC, subject-independent | different metric (F1) and split; check the paper's evaluation unit (subject or sample) before comparing |
| Brookshire et al. 2024 | 53% -> 99.8% acc. | AD, subject-wise vs leaky split | methodological reference: shows how leakage inflates accuracy; compare with our leakage demo |
| **This study (highest mean: baseline_logreg)** | 81.7% balanced acc. | AD vs HC, 5-fold subject-wise × 3 | - |

Our protocol differs from all of them: 5-fold (about 52 training subjects per fold) instead of LOSO (64), balanced accuracy over subjects instead of accuracy or window-level F1, early-stopping subjects taken from the training fold, and no tuning on test folds. Numbers across protocols should be read as context, not a ranking.

## Training details

Epochs actually trained (max 40, early stopping patience 8 on validation-subject loss; the best epoch's weights are kept):

| Repeat | Fold | Microstate GEV | EEGNet epochs | Hybrid epochs |
|---|---|---|---|---|
| 0 | 0 | 0.647 | 9 | 10 |
| 0 | 1 | 0.658 | 9 | 9 |
| 0 | 2 | 0.640 | 30 | 23 |
| 0 | 3 | 0.662 | 10 | 13 |
| 0 | 4 | 0.646 | 13 | 11 |
| 1 | 0 | 0.664 | 17 | 17 |
| 1 | 1 | 0.653 | 12 | 18 |
| 1 | 2 | 0.656 | 10 | 11 |
| 1 | 3 | 0.646 | 13 | 15 |
| 1 | 4 | 0.647 | 12 | 12 |
| 2 | 0 | 0.665 | 14 | 14 |
| 2 | 1 | 0.649 | 17 | 23 |
| 2 | 2 | 0.648 | 24 | 21 |
| 2 | 3 | 0.650 | 12 | 14 |
| 2 | 4 | 0.651 | 22 | 21 |
| mean | | 0.652 | 14.9 | 15.5 |

Runs that reached the 40-epoch cap without early stopping: 0 of 30.

| Setting | Value |
|---|---|
| folds | 5 |
| repeats | 3 |
| epochs | 40 |
| patience | 8 |
| crops | 64 |
| batch | 64 |
| lr | 0.001 |
| wd | 0.001 |
| dropout | 0.5 |
| leak_epochs | 15 |
| models | ['baseline', 'eegnet', 'hybrid'] |
| seeds | outer split StratifiedKFold random_state=repeat; per-fold seed=100*repeat+fold (microstate fit, RF, inner early-stopping split, torch/numpy in training); leakage demo seed=0 |
| fold seeds | [0, 1, 2, 3, 4, 100, 101, 102, 103, 104, 200, 201, 202, 203, 204] |
| bootstrap | 2000 resamples, seed 12345 |
| runtime | 0.34 h total; 1.3 min per fold on average (range 0.9-2.4) |
| environment | Python 3.12.16, macOS-26.6.2-arm64-arm-64bit, device: mps |
| libraries | numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, scikit-learn 1.9.1, torch 2.15.0, mne 1.13.2, pycrostates 0.6.1 |

Files: `results.json`, `fold_metrics.csv`, `oof_predictions.csv`, `log.txt` in this folder.
