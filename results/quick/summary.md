# Main experiment: AD vs HC (5-fold subject-wise CV x 1 repeats)

Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.

Subjects: 65 (36 AD, 29 HC), ds004504 derivatives, prepared as in `results/prep_report.md` (no window rejection). Every subject is in exactly one test fold per repeat; early-stopping subjects (15%) and microstate maps come from the training fold only. Subject score = mean of its 4-s window probabilities; threshold 0.5.

## Results

Mean ± SD over the 5 test folds; *pooled* = all out-of-fold subject predictions of a repeat scored together, averaged over repeats. AUC 95% CI: subject bootstrap (2000 resamples, stratified, seed 12345).

| Model | Balanced accuracy (fold mean ± SD) | AUC (fold mean ± SD) | F1 (fold mean ± SD) | Pooled bal. acc. | Pooled AUC [95% CI] | Pooled F1 |
|---|---|---|---|---|---|---|
| A. Baseline: microstate features + logistic regression | 0.839 ± 0.060 | 0.917 ± 0.078 | 0.829 ± 0.081 | 0.837 | 0.900 [0.821, 0.963] | 0.836 |
| A. Baseline: microstate features + random forest | 0.803 ± 0.045 | 0.860 ± 0.109 | 0.812 ± 0.034 | 0.803 | 0.839 [0.737, 0.931] | 0.812 |
| B. EEGNet alone | 0.766 ± 0.121 | 0.856 ± 0.102 | 0.742 ± 0.191 | 0.778 | 0.817 [0.705, 0.911] | 0.769 |
| C. Hybrid (EEGNet + microstate CNN) | 0.842 ± 0.139 | 0.905 ± 0.094 | 0.792 ± 0.219 | 0.844 | 0.873 [0.778, 0.953] | 0.825 |

Pooled balanced accuracy per repeat (shows split-to-split variation):

| Model | repeat 0 |
|---|---|
| baseline_logreg | 0.837 |
| baseline_rf | 0.803 |
| eegnet | 0.778 |
| hybrid | 0.844 |

## Hybrid vs EEGNet (paired)

| Metric | Hybrid − EEGNet, mean (SD) | folds hybrid better / tied / worse | Wilcoxon signed-rank p | Corrected resampled t-test p |
|---|---|---|---|---|
| balanced accuracy | +0.076 (0.100) | 3 / 1 / 1 | 0.25 | 0.318 (t = 1.14) |
| auc | +0.048 (0.038) | 4 / 1 / 0 | 0.125 | 0.133 (t = 1.88) |
| f1 | +0.051 (0.038) | 4 / 1 / 0 | 0.125 | 0.117 (t = 1.99) |

Pooled AUC difference hybrid − EEGNet: +0.056, paired subject-bootstrap 95% CI [+0.014, +0.109]; share of resamples with hybrid > EEGNet: 99.7%.

Wilcoxon uses the 5 fold scores (zero differences dropped, two-sided). Folds from different repeats share subjects, so they are not independent and the plain Wilcoxon p is optimistic; the corrected resampled t-test (Nadeau & Bengio 2003, test/train ratio 13/52) accounts for this and is the more conservative number.

Secondary (not pre-specified in the task): hybrid − logistic-regression baseline, balanced accuracy +0.003; Wilcoxon p 0.875; corrected t-test p 0.962.

## Leakage demo vs honest subject-wise evaluation

Not run (`--skip-leak`).

## Comparison with published results on ds004504

| Study | Reported | Task / protocol | Why not directly comparable |
|---|---|---|---|
| Two-Stage Microstate Fusion (Biosensors 2026) | 74.3% balanced acc. | dementia vs HC, LOSO | different class definition ('dementia'; check whether FTD is included) and leave-one-subject-out |
| DICE-Net (Miltiadous et al. 2023) | 83.28% acc. | AD vs HC, LOSO | plain accuracy, not balanced accuracy; LOSO trains on 64 subjects per fold vs about 52 here |
| ADformer (2024) | 92.82% F1 | AD vs HC, subject-independent | different metric (F1) and split; check the paper's evaluation unit (subject or sample) before comparing |
| Brookshire et al. 2024 | 53% -> 99.8% acc. | AD, subject-wise vs leaky split | methodological reference: shows how leakage inflates accuracy; compare with our leakage demo |
| **This study (highest mean: hybrid)** | 84.2% balanced acc. | AD vs HC, 5-fold subject-wise × 1 | - |

Our protocol differs from all of them: 5-fold (about 52 training subjects per fold) instead of LOSO (64), balanced accuracy over subjects instead of accuracy or window-level F1, early-stopping subjects taken from the training fold, and no tuning on test folds. Numbers across protocols should be read as context, not a ranking.

## Training details

Epochs actually trained (max 5, early stopping patience 8 on validation-subject loss; the best epoch's weights are kept):

| Repeat | Fold | Microstate GEV | EEGNet epochs | Hybrid epochs |
|---|---|---|---|---|
| 0 | 0 | 0.647 | 5 | 5 |
| 0 | 1 | 0.658 | 5 | 5 |
| 0 | 2 | 0.640 | 5 | 5 |
| 0 | 3 | 0.662 | 5 | 5 |
| 0 | 4 | 0.646 | 5 | 5 |
| mean | | 0.651 | 5.0 | 5.0 |

Runs that reached the 5-epoch cap without early stopping: 10 of 10.

| Setting | Value |
|---|---|
| folds | 5 |
| repeats | 1 |
| epochs | 5 |
| patience | 8 |
| crops | 64 |
| batch | 64 |
| lr | 0.001 |
| wd | 0.001 |
| dropout | 0.5 |
| leak_epochs | 15 |
| models | ['baseline', 'eegnet', 'hybrid'] |
| seeds | outer split StratifiedKFold random_state=repeat; per-fold seed=100*repeat+fold (microstate fit, RF, inner early-stopping split, torch/numpy in training); leakage demo seed=0 |
| fold seeds | [0, 1, 2, 3, 4] |
| bootstrap | 2000 resamples, seed 12345 |
| runtime | 0.66 h total; 8.0 min per fold on average (range 7.8-8.2) |
| environment | Python 3.12.16, macOS-26.6.2-arm64-arm-64bit, CPU only |
| libraries | numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, scikit-learn 1.9.1, torch 2.15.0, mne 1.13.2, pycrostates 0.6.1 |

Files: `results.json`, `fold_metrics.csv`, `oof_predictions.csv`, `log.txt` in this folder.
