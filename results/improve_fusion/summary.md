# Late fusion: 0.5 × EEGNet + 0.5 × logistic-regression baseline (fixed weights, threshold 0.5)

  fusion    : 0.5 * EEGNet + 0.5 * baseline logistic regression probability (weights fixed in advance), threshold 0.5
  threshold : per outer fold, a decision threshold chosen on that fold's inner-validation subjects only
              (val_predictions.csv; they are training-fold subjects held out for early stopping), then applied
              unchanged to the test subjects. Rule fixed in advance: candidates = 0.5 and the midpoints between
              the sorted validation scores; keep the highest validation balanced accuracy; ties -> closest to 0.5.
  ensemble  : mean subject probability of 5 network seeds per fold (ensemble size fixed in advance); seed k adds
              1000*k to the network training seed only, so microstate maps and inner splits are unchanged; the
              threshold rule above is also applied to the averaged validation-subject probabilities.

AUC CI: subject bootstrap (2000 resamples, seed 12345). Corrected t-test: Nadeau & Bengio (2003), test/train ratio 13/52. Research use only: classification, not diagnosis.

## Source run: `main_AD_vs_HC` (device: cpu)

| Model | Balanced acc. (mean ± SD, 15 folds) | AUC | F1 | Sensitivity (fold mean) | Specificity (fold mean) | Pooled AUC [95% CI] |
|---|---|---|---|---|---|---|
| baseline_logreg | 0.817 ± 0.105 | 0.907 ± 0.091 | 0.812 ± 0.119 | 0.765 | 0.869 | 0.898 [0.820, 0.960] |
| eegnet | 0.852 ± 0.099 | 0.922 ± 0.078 | 0.853 ± 0.097 | 0.801 | 0.902 | 0.905 [0.831, 0.962] |
| hybrid | 0.813 ± 0.117 | 0.908 ± 0.103 | 0.751 ± 0.198 | 0.650 | 0.976 | 0.891 [0.818, 0.950] |
| fusion_eegnet_logreg | 0.880 ± 0.078 | 0.921 ± 0.076 | 0.869 ± 0.087 | 0.804 | 0.956 | 0.916 [0.840, 0.972] |

Paired comparison over the 15 folds (difference = variant − reference; same run, same splits):

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| fusion_eegnet_logreg | hybrid | balanced_accuracy | +0.067 (0.093) | 10 / 2 / 3 | 0.0164 | 0.224 |
| fusion_eegnet_logreg | hybrid | auc | +0.013 (0.080) | 9 / 3 / 3 | 0.329 | 0.768 |
| fusion_eegnet_logreg | hybrid | f1 | +0.117 (0.165) | 11 / 2 / 2 | 0.00635 | 0.228 |
| fusion_eegnet_logreg | eegnet | balanced_accuracy | +0.028 (0.083) | 5 / 6 / 4 | 0.172 | 0.563 |
| fusion_eegnet_logreg | eegnet | auc | -0.001 (0.054) | 6 / 4 / 5 | 0.951 | 0.986 |
| fusion_eegnet_logreg | eegnet | f1 | +0.016 (0.080) | 6 / 6 / 3 | 0.586 | 0.727 |

## Source run: `improve_mps_rerun` (device: mps)

| Model | Balanced acc. (mean ± SD, 15 folds) | AUC | F1 | Sensitivity (fold mean) | Specificity (fold mean) | Pooled AUC [95% CI] |
|---|---|---|---|---|---|---|
| baseline_logreg | 0.817 ± 0.105 | 0.907 ± 0.091 | 0.812 ± 0.119 | 0.765 | 0.869 | 0.898 [0.819, 0.960] |
| eegnet | 0.790 ± 0.125 | 0.899 ± 0.084 | 0.790 ± 0.122 | 0.744 | 0.836 | 0.875 [0.793, 0.936] |
| hybrid | 0.805 ± 0.099 | 0.911 ± 0.085 | 0.755 ± 0.183 | 0.669 | 0.940 | 0.885 [0.811, 0.943] |
| fusion_eegnet_logreg | 0.875 ± 0.095 | 0.915 ± 0.087 | 0.861 ± 0.110 | 0.794 | 0.956 | 0.912 [0.838, 0.970] |

Paired comparison over the 15 folds (difference = variant − reference; same run, same splits):

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| fusion_eegnet_logreg | hybrid | balanced_accuracy | +0.070 (0.119) | 10 / 2 / 3 | 0.0652 | 0.313 |
| fusion_eegnet_logreg | hybrid | auc | +0.004 (0.084) | 9 / 1 / 5 | 0.508 | 0.933 |
| fusion_eegnet_logreg | hybrid | f1 | +0.106 (0.197) | 10 / 2 / 3 | 0.0222 | 0.355 |
| fusion_eegnet_logreg | eegnet | balanced_accuracy | +0.085 (0.110) | 9 / 4 / 2 | 0.00879 | 0.191 |
| fusion_eegnet_logreg | eegnet | auc | +0.016 (0.048) | 8 / 2 / 5 | 0.25 | 0.574 |
| fusion_eegnet_logreg | eegnet | f1 | +0.071 (0.101) | 9 / 4 / 2 | 0.0186 | 0.235 |

