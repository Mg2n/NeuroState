# Secondary task: AD vs FTD vs HC (5-fold subject-wise CV x 3 repeats)

Research use only: this classifies groups in a public dataset; it is not a diagnostic test.

Subjects: 88. Settings fixed in advance (task 05 defaults, not chosen from any test fold). Maps and early-stopping subjects come from each training fold only. Chance balanced accuracy = 0.333. `eegnet`, `hybrid` = network seed offset 0; `*_ens5` = mean probability vector over 5 seeds. Splits differ from the AD vs HC runs (they stratify over 3 groups), so numbers are not paired with those runs.

## Results

| Model | Balanced acc. (mean ± SD) | Macro-F1 | Macro AUC (one-vs-rest) |
|---|---|---|---|
| baseline_logreg | 0.554 ± 0.102 | 0.534 ± 0.099 | 0.745 ± 0.052 |
| baseline_rf | 0.579 ± 0.087 | 0.565 ± 0.090 | 0.746 ± 0.055 |
| eegnet | 0.568 ± 0.086 | 0.536 ± 0.097 | 0.758 ± 0.067 |
| hybrid | 0.539 ± 0.116 | 0.510 ± 0.124 | 0.760 ± 0.085 |
| eegnet_ens5 | 0.572 ± 0.084 | 0.542 ± 0.097 | 0.763 ± 0.065 |
| hybrid_ens5 | 0.569 ± 0.100 | 0.540 ± 0.099 | 0.763 ± 0.084 |

## Single seeds (fold mean)

| Run | EEGNet bal. acc. | Hybrid bal. acc. | Hybrid − EEGNet |
|---|---|---|---|
| improve_3class_seed0 | 0.568 | 0.539 | -0.029 |
| improve_3class_seed1 | 0.510 | 0.542 | +0.032 |
| improve_3class_seed2 | 0.531 | 0.514 | -0.017 |
| improve_3class_seed3 | 0.549 | 0.549 | +0.000 |
| improve_3class_seed4 | 0.549 | 0.537 | -0.012 |
| **mean ± SD** | 0.541 ± 0.022 | 0.536 ± 0.013 | -0.005 ± 0.023 |

## Paired comparisons over the folds

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| hybrid_ens5 | eegnet_ens5 | balanced_accuracy | -0.002 (0.096) | 6 / 0 / 9 | 0.733 | 0.969 |
| hybrid_ens5 | eegnet_ens5 | f1 | -0.002 (0.115) | 6 / 0 / 9 | 0.934 | 0.972 |
| hybrid_ens5 | eegnet_ens5 | auc | -0.000 (0.061) | 7 / 0 / 8 | 0.934 | 0.992 |
| hybrid_ens5 | baseline_logreg | balanced_accuracy | +0.016 (0.159) | 8 / 0 / 7 | 0.798 | 0.863 |
| hybrid_ens5 | baseline_logreg | f1 | +0.006 (0.157) | 8 / 0 / 7 | 1 | 0.947 |
| hybrid_ens5 | baseline_logreg | auc | +0.018 (0.099) | 9 / 0 / 6 | 0.599 | 0.752 |
| eegnet_ens5 | baseline_logreg | balanced_accuracy | +0.018 (0.147) | 9 / 1 / 5 | 0.502 | 0.832 |
| eegnet_ens5 | baseline_logreg | f1 | +0.008 (0.147) | 11 / 0 / 4 | 0.489 | 0.921 |
| eegnet_ens5 | baseline_logreg | auc | +0.018 (0.085) | 7 / 0 / 8 | 0.599 | 0.707 |

Corrected t-test: Nadeau & Bengio (2003), test/train ratio 17.6/70.4.

## Per-class recall and confusion (all repeats pooled)

| Model | AD recall | FTD recall | HC recall |
|---|---|---|---|
| baseline_logreg | 0.500 | 0.391 | 0.770 |
| eegnet_ens5 | 0.639 | 0.232 | 0.839 |
| hybrid_ens5 | 0.546 | 0.290 | 0.874 |

`baseline_logreg`, rows = true, columns = predicted (counts over repeats):

| | AD | FTD | HC |
|---|---|---|---|
| AD | 54 | 32 | 22 |
| FTD | 26 | 27 | 16 |
| HC | 8 | 12 | 67 |

`eegnet_ens5`, rows = true, columns = predicted (counts over repeats):

| | AD | FTD | HC |
|---|---|---|---|
| AD | 69 | 16 | 23 |
| FTD | 37 | 16 | 16 |
| HC | 9 | 5 | 73 |

`hybrid_ens5`, rows = true, columns = predicted (counts over repeats):

| | AD | FTD | HC |
|---|---|---|---|
| AD | 59 | 23 | 26 |
| FTD | 29 | 20 | 20 |
| HC | 4 | 7 | 76 |

## Without sub-086 in the evaluation

`sub-086` (FTD, about 4x median amplitude) is removed from the test folds here but was still used for training when it was in a training fold, and in map fitting, so this is an evaluation-only sensitivity check, not a full exclusion.

| Model | Balanced acc. (mean ± SD) | Macro-F1 | Macro AUC (one-vs-rest) |
|---|---|---|---|
| baseline_logreg | 0.557 ± 0.101 | 0.538 ± 0.099 | 0.754 ± 0.052 |
| baseline_rf | 0.584 ± 0.083 | 0.570 ± 0.089 | 0.753 ± 0.049 |
| eegnet | 0.561 ± 0.075 | 0.526 ± 0.084 | 0.754 ± 0.062 |
| hybrid | 0.541 ± 0.110 | 0.507 ± 0.116 | 0.765 ± 0.087 |
| eegnet_ens5 | 0.566 ± 0.079 | 0.533 ± 0.090 | 0.763 ± 0.064 |
| hybrid_ens5 | 0.567 ± 0.092 | 0.535 ± 0.089 | 0.764 ± 0.083 |

`sub-086` prediction by model (fraction of repeats classified FTD): baseline_logreg 0.00, baseline_rf 0.00, eegnet 0.67, hybrid 0.33, eegnet_ens5 0.67, hybrid_ens5 0.33
