# Secondary task: AD vs FTD vs HC (5-fold subject-wise CV x 3 repeats)

Research use only: this classifies groups in a public dataset; it is not a diagnostic test.

Subjects: 87 (sub-086 excluded). Settings fixed in advance (task 05 defaults, not chosen from any test fold). Maps and early-stopping subjects come from each training fold only. Chance balanced accuracy = 0.333. `eegnet`, `hybrid` = network seed offset 0; `*_ens5` = mean probability vector over 5 seeds. Splits differ from the AD vs HC runs (they stratify over 3 groups), so numbers are not paired with those runs.

## Results

| Model | Balanced acc. (mean ± SD) | Macro-F1 | Macro AUC (one-vs-rest) |
|---|---|---|---|
| baseline_logreg | 0.594 ± 0.093 | 0.579 ± 0.099 | 0.755 ± 0.058 |
| baseline_rf | 0.576 ± 0.070 | 0.562 ± 0.065 | 0.749 ± 0.050 |
| eegnet | 0.554 ± 0.096 | 0.528 ± 0.100 | 0.760 ± 0.068 |
| hybrid | 0.522 ± 0.098 | 0.480 ± 0.097 | 0.763 ± 0.066 |
| eegnet_ens5 | 0.572 ± 0.070 | 0.546 ± 0.069 | 0.769 ± 0.075 |
| hybrid_ens5 | 0.580 ± 0.116 | 0.557 ± 0.119 | 0.770 ± 0.075 |

## Single seeds (fold mean)

| Run | EEGNet bal. acc. | Hybrid bal. acc. | Hybrid − EEGNet |
|---|---|---|---|
| improve_3class_no086_seed0 | 0.554 | 0.522 | -0.032 |
| improve_3class_no086_seed1 | 0.534 | 0.522 | -0.011 |
| improve_3class_no086_seed2 | 0.543 | 0.519 | -0.024 |
| improve_3class_no086_seed3 | 0.545 | 0.595 | +0.050 |
| improve_3class_no086_seed4 | 0.536 | 0.551 | +0.014 |
| **mean ± SD** | 0.542 ± 0.008 | 0.542 ± 0.032 | -0.001 ± 0.033 |

## Paired comparisons over the folds

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| hybrid_ens5 | eegnet_ens5 | balanced_accuracy | +0.008 (0.120) | 6 / 2 / 7 | 0.986 | 0.904 |
| hybrid_ens5 | eegnet_ens5 | f1 | +0.011 (0.127) | 7 / 1 / 7 | 1 | 0.875 |
| hybrid_ens5 | eegnet_ens5 | auc | +0.001 (0.058) | 7 / 0 / 8 | 0.89 | 0.976 |
| hybrid_ens5 | baseline_logreg | balanced_accuracy | -0.014 (0.173) | 7 / 0 / 8 | 0.679 | 0.889 |
| hybrid_ens5 | baseline_logreg | f1 | -0.022 (0.184) | 7 / 0 / 8 | 0.639 | 0.835 |
| hybrid_ens5 | baseline_logreg | auc | +0.015 (0.086) | 8 / 0 / 7 | 0.847 | 0.759 |
| eegnet_ens5 | baseline_logreg | balanced_accuracy | -0.022 (0.122) | 8 / 0 / 7 | 0.934 | 0.752 |
| eegnet_ens5 | baseline_logreg | f1 | -0.033 (0.120) | 8 / 0 / 7 | 0.599 | 0.629 |
| eegnet_ens5 | baseline_logreg | auc | +0.014 (0.090) | 11 / 0 / 4 | 0.454 | 0.783 |

Corrected t-test: Nadeau & Bengio (2003), test/train ratio 17.4/69.6.

## Per-class recall and confusion (all repeats pooled)

| Model | AD recall | FTD recall | HC recall |
|---|---|---|---|
| baseline_logreg | 0.602 | 0.394 | 0.793 |
| eegnet_ens5 | 0.565 | 0.348 | 0.805 |
| hybrid_ens5 | 0.574 | 0.424 | 0.759 |

`baseline_logreg`, rows = true, columns = predicted (counts over repeats):

| | AD | FTD | HC |
|---|---|---|---|
| AD | 65 | 23 | 20 |
| FTD | 25 | 26 | 15 |
| HC | 8 | 10 | 69 |

`eegnet_ens5`, rows = true, columns = predicted (counts over repeats):

| | AD | FTD | HC |
|---|---|---|---|
| AD | 61 | 25 | 22 |
| FTD | 29 | 23 | 14 |
| HC | 4 | 13 | 70 |

`hybrid_ens5`, rows = true, columns = predicted (counts over repeats):

| | AD | FTD | HC |
|---|---|---|---|
| AD | 62 | 26 | 20 |
| FTD | 26 | 28 | 12 |
| HC | 5 | 16 | 66 |

## Effect of removing sub-086 from training

`sub-086` (FTD, about 4x median amplitude) was removed from training, early stopping, map fitting and test. The outer folds are those of the full cohort, so test subjects are identical in both columns of this comparison: `with086_*` are the full-cohort runs scored without sub-086. Early-stopping subjects differ in folds where sub-086 was a training subject, because the split is drawn from one fewer subject.

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

Per-class recall on the same test subjects (all repeats pooled), with sub-086 in training → without:

| Model | AD recall | FTD recall | HC recall | Predictions changed |
|---|---|---|---|---|
| baseline_logreg | 0.500 → 0.602 | 0.409 → 0.394 | 0.770 → 0.793 | 24 of 261 |
| baseline_rf | 0.537 → 0.537 | 0.439 → 0.439 | 0.782 → 0.759 | 29 of 261 |
| eegnet_ens5 | 0.639 → 0.565 | 0.212 → 0.348 | 0.839 → 0.805 | 37 of 261 |
| hybrid_ens5 | 0.546 → 0.574 | 0.288 → 0.424 | 0.874 → 0.759 | 40 of 261 |

In the 3 folds where sub-086 was a test subject its removal leaves training unchanged: max probability difference 0 over all models. These folds count as ties above, so at most 12 folds can differ. There is no control run: removing any training subject also changes the early-stopping split and the batches, so these differences cannot all be attributed to sub-086's signal.
