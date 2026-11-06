# Decision threshold chosen on inner-validation subjects of each training fold

  fusion    : 0.5 * EEGNet + 0.5 * baseline logistic regression probability (weights fixed in advance), threshold 0.5
  threshold : per outer fold, a decision threshold chosen on that fold's inner-validation subjects only
              (val_predictions.csv; they are training-fold subjects held out for early stopping), then applied
              unchanged to the test subjects. Rule fixed in advance: candidates = 0.5 and the midpoints between
              the sorted validation scores; keep the highest validation balanced accuracy; ties -> closest to 0.5.
  ensemble  : mean subject probability of 5 network seeds per fold (ensemble size fixed in advance); seed k adds
              1000*k to the network training seed only, so microstate maps and inner splits are unchanged; the
              threshold rule above is also applied to the averaged validation-subject probabilities.

AUC CI: subject bootstrap (2000 resamples, seed 12345). Corrected t-test: Nadeau & Bengio (2003), test/train ratio 13/52. Research use only: classification, not diagnosis.

## Source run: `improve_mps_rerun` (device: mps)

| Model | Balanced acc. (mean ± SD, 15 folds) | AUC | F1 | Sensitivity (fold mean) | Specificity (fold mean) | Pooled AUC [95% CI] |
|---|---|---|---|---|---|---|
| baseline_logreg | 0.817 ± 0.105 | 0.907 ± 0.091 | 0.812 ± 0.119 | 0.765 | 0.869 | 0.898 [0.820, 0.960] |
| eegnet | 0.790 ± 0.125 | 0.899 ± 0.084 | 0.790 ± 0.122 | 0.744 | 0.836 | 0.875 [0.795, 0.937] |
| hybrid | 0.805 ± 0.099 | 0.911 ± 0.085 | 0.755 ± 0.183 | 0.669 | 0.940 | 0.885 [0.815, 0.943] |
| eegnet_valthr | 0.783 ± 0.126 | 0.899 ± 0.084 | 0.791 ± 0.119 | 0.763 | 0.802 | 0.875 [0.795, 0.937] |
| hybrid_valthr | 0.795 ± 0.126 | 0.911 ± 0.085 | 0.759 ± 0.176 | 0.679 | 0.911 | 0.885 [0.815, 0.943] |

Paired comparison over the 15 folds (difference = variant − reference; same run, same splits):

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| eegnet_valthr | hybrid | balanced_accuracy | -0.022 (0.151) | 7 / 2 / 6 | 0.723 | 0.801 |
| eegnet_valthr | hybrid | f1 | +0.036 (0.175) | 7 / 2 / 6 | 0.497 | 0.721 |
| eegnet_valthr | eegnet | balanced_accuracy | -0.007 (0.054) | 1 / 11 / 3 | 0.625 | 0.817 |
| eegnet_valthr | eegnet | f1 | +0.000 (0.026) | 3 / 11 / 1 | 0.875 | 0.977 |
| hybrid_valthr | hybrid | balanced_accuracy | -0.010 (0.088) | 2 / 12 / 1 | 1 | 0.848 |
| hybrid_valthr | hybrid | f1 | +0.004 (0.072) | 1 / 12 / 2 | 1 | 0.917 |
| hybrid_valthr | eegnet | balanced_accuracy | +0.005 (0.153) | 7 / 2 / 6 | 0.961 | 0.954 |
| hybrid_valthr | eegnet | f1 | -0.031 (0.173) | 5 / 2 / 8 | 0.553 | 0.754 |

Chosen thresholds (improve_mps_rerun): eegnet_valthr: median 0.500, range 0.334-0.782, left at 0.5 in 8/15 folds; hybrid_valthr: median 0.500, range 0.252-0.630, left at 0.5 in 11/15 folds. Validation subjects per fold: 8-8 (4-4 AD).

