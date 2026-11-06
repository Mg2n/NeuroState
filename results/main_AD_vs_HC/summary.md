# Main experiment: AD vs HC (5-fold subject-wise CV x 3 repeats)

Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.

Subjects: 65 (36 AD, 29 HC), ds004504 derivatives, prepared as in `results/prep_report.md` (no window rejection). Every subject is in exactly one test fold per repeat; early-stopping subjects (15%) and microstate maps come from the training fold only. Subject score = mean of its 4-s window probabilities; threshold 0.5.

## Results

Mean ± SD over the 15 test folds; *pooled* = all out-of-fold subject predictions of a repeat scored together, averaged over repeats. AUC 95% CI: subject bootstrap (2000 resamples, stratified, seed 12345).

| Model | Balanced accuracy (fold mean ± SD) | AUC (fold mean ± SD) | F1 (fold mean ± SD) | Pooled bal. acc. | Pooled AUC [95% CI] | Pooled F1 |
|---|---|---|---|---|---|---|
| A. Baseline: microstate features + logistic regression | 0.817 ± 0.105 | 0.907 ± 0.091 | 0.812 ± 0.119 | 0.821 | 0.898 [0.820, 0.960] | 0.822 |
| A. Baseline: microstate features + random forest | 0.800 ± 0.075 | 0.857 ± 0.080 | 0.802 ± 0.092 | 0.805 | 0.844 [0.745, 0.928] | 0.808 |
| B. EEGNet alone | 0.852 ± 0.099 | 0.922 ± 0.078 | 0.853 ± 0.097 | 0.857 | 0.905 [0.831, 0.962] | 0.857 |
| C. Hybrid (EEGNet + microstate CNN) | 0.813 ± 0.117 | 0.908 ± 0.103 | 0.751 ± 0.198 | 0.817 | 0.891 [0.818, 0.950] | 0.781 |

Pooled balanced accuracy per repeat (shows split-to-split variation):

| Model | repeat 0 | repeat 1 | repeat 2 |
|---|---|---|---|
| baseline_logreg | 0.837 | 0.789 | 0.837 |
| baseline_rf | 0.803 | 0.806 | 0.806 |
| eegnet | 0.817 | 0.872 | 0.882 |
| hybrid | 0.872 | 0.778 | 0.802 |

Sensitivity and specificity at threshold 0.5 (all out-of-fold subject predictions, 3 repeats pooled; AD = positive class):

| Model | Sensitivity (AD recall) | Specificity (HC recall) | Median score, AD | Median score, HC |
|---|---|---|---|---|
| baseline_logreg | 0.769 | 0.874 | 0.928 | 0.192 |
| baseline_rf | 0.759 | 0.851 | 0.795 | 0.286 |
| eegnet | 0.806 | 0.908 | 0.724 | 0.287 |
| hybrid | 0.657 | 0.977 | 0.729 | 0.191 |

The hybrid misses more AD subjects than EEGNet (sensitivity 0.657 vs 0.806) and fewer HC subjects; its AUC is close to EEGNet's, so most of the gap is in which side of the fixed 0.5 threshold subjects fall on, not in how they are ranked. Fewer AD subjects caught lowers F1 (AD = positive) more than balanced accuracy. The 0.5 threshold was fixed in advance and is not tuned here.

## Hybrid vs EEGNet (paired)

| Metric | Hybrid − EEGNet, mean (SD) | folds hybrid better / tied / worse | Wilcoxon signed-rank p | Corrected resampled t-test p |
|---|---|---|---|---|
| balanced accuracy | -0.039 (0.128) | 5 / 2 / 8 | 0.297 | 0.597 (t = -0.54) |
| auc | -0.014 (0.075) | 6 / 2 / 7 | 0.864 | 0.744 (t = -0.33) |
| f1 | -0.101 (0.179) | 3 / 2 / 10 | 0.0466 | 0.332 (t = -1.00) |

Pooled AUC difference hybrid − EEGNet: -0.014, paired subject-bootstrap 95% CI [-0.053, +0.021]; share of resamples with hybrid > EEGNet: 23.4%.

Wilcoxon uses the 15 fold scores (zero differences dropped, two-sided). Folds from different repeats share subjects, so they are not independent and the plain Wilcoxon p is optimistic; the corrected resampled t-test (Nadeau & Bengio 2003, test/train ratio 13/52) accounts for this and is the more conservative number.

Secondary (not pre-specified in the task): hybrid − logistic-regression baseline, balanced accuracy -0.004; Wilcoxon p 0.82; corrected t-test p 0.953.

## Leakage demo vs honest subject-wise evaluation

| Evaluation | Unit | Balanced acc. | AUC | F1 |
|---|---|---|---|---|
| EEGNet, windows split at random (same people in train and test) | 2,657 test windows | 0.956 | 0.993 | 0.955 |
| EEGNet, subject-wise CV (this study) | 65 subjects × 3 repeats | 0.852 ± 0.099 | 0.922 | 0.853 |

The random window split trains 15 epochs on 80% of all windows (seed 0, no early stopping) and tests on the remaining 20%, which come from the same people. The gap (+0.104 balanced accuracy) is what subject leakage adds; the subject-wise number is the honest estimate.

## Comparison with published results on ds004504

| Study | Reported | Task / protocol | Why not directly comparable |
|---|---|---|---|
| Two-Stage Microstate Fusion (Biosensors 2026) | 74.3% balanced acc. | dementia vs HC, LOSO | different class definition ('dementia'; check whether FTD is included) and leave-one-subject-out |
| DICE-Net (Miltiadous et al. 2023) | 83.28% acc. | AD vs HC, LOSO | plain accuracy, not balanced accuracy; LOSO trains on 64 subjects per fold vs about 52 here |
| ADformer (2024) | 92.82% F1 | AD vs HC, subject-independent | different metric (F1) and split; check the paper's evaluation unit (subject or sample) before comparing |
| **This study (highest mean: eegnet)** | 85.2% balanced acc. | AD vs HC, 5-fold subject-wise × 3 | - |

Different cohort, not ds004504: Brookshire et al. 2024, 53% -> 99.8% acc., subject-wise vs leaky split, 49 subjects with dementia due to Alzheimer's disease vs 49 with subjective cognitive impairment; methodological reference only.

Corrected on 6 Nov 2026: Brookshire et al. moved out of this ds004504 table.

Our protocol differs from all of them: 5-fold (about 52 training subjects per fold) instead of LOSO (64), balanced accuracy over subjects instead of accuracy or window-level F1, early-stopping subjects taken from the training fold, and no tuning on test folds. Numbers across protocols should be read as context, not a ranking.

## Training details

Epochs actually trained (max 40, early stopping patience 8 on validation-subject loss; the best epoch's weights are kept):

| Repeat | Fold | Microstate GEV | EEGNet epochs | Hybrid epochs |
|---|---|---|---|---|
| 0 | 0 | 0.647 | 9 | 10 |
| 0 | 1 | 0.658 | 9 | 12 |
| 0 | 2 | 0.640 | 30 | 29 |
| 0 | 3 | 0.662 | 10 | 14 |
| 0 | 4 | 0.646 | 13 | 13 |
| 1 | 0 | 0.664 | 17 | 23 |
| 1 | 1 | 0.653 | 12 | 17 |
| 1 | 2 | 0.656 | 14 | 15 |
| 1 | 3 | 0.646 | 14 | 14 |
| 1 | 4 | 0.647 | 12 | 12 |
| 2 | 0 | 0.665 | 14 | 14 |
| 2 | 1 | 0.649 | 22 | 13 |
| 2 | 2 | 0.648 | 19 | 40 |
| 2 | 3 | 0.650 | 14 | 15 |
| 2 | 4 | 0.651 | 23 | 23 |
| mean | | 0.652 | 15.5 | 17.6 |

Runs that reached the 40-epoch cap without early stopping: 1 of 30.

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
| runtime | 6.68 h total; 23.5 min per fold on average (range 14.0-43.5) |
| environment | Python 3.12.16, macOS-26.6.2-arm64-arm-64bit, device: cpu |
| libraries | numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, scikit-learn 1.9.1, torch 2.15.0, mne 1.13.2, pycrostates 0.6.1 |

Files: `results.json`, `fold_metrics.csv`, `oof_predictions.csv`, `log.txt` in this folder.
