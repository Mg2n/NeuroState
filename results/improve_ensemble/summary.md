# Seed ensemble: 5 network seeds per fold, probabilities averaged

  fusion    : 0.5 * EEGNet + 0.5 * baseline logistic regression probability (weights fixed in advance), threshold 0.5
  threshold : per outer fold, a decision threshold chosen on that fold's inner-validation subjects only
              (val_predictions.csv; they are training-fold subjects held out for early stopping), then applied
              unchanged to the test subjects. Rule fixed in advance: candidates = 0.5 and the midpoints between
              the sorted validation scores; keep the highest validation balanced accuracy; ties -> closest to 0.5.
  ensemble  : mean subject probability of 5 network seeds per fold (ensemble size fixed in advance); seed k adds
              1000*k to the network training seed only, so microstate maps and inner splits are unchanged; the
              threshold rule above is also applied to the averaged validation-subject probabilities.
  variant   : a changed setting (window length, microstate branch input, ...) run with the same 5 seed offsets;
              its 5-seed ensemble is compared with the reference 5-seed ensemble (threshold 0.5, nothing tuned).

AUC CI: subject bootstrap (2000 resamples, seed 12345). Corrected t-test: Nadeau & Bengio (2003), test/train ratio 13/52. Research use only: classification, not diagnosis.

## Single seeds: 5 network seeds (each run alone, fold mean of 15 folds)

| Run | Network seed offset | EEGNet bal. acc. | Hybrid bal. acc. | EEGNet AUC | Hybrid AUC | Hybrid − EEGNet bal. acc. | Corrected t-test p |
|---|---|---|---|---|---|---|---|
| improve_mps_rerun | 0 | 0.790 | 0.805 | 0.899 | 0.911 | +0.015 | 0.86 |
| improve_seed1 | 1000 | 0.791 | 0.820 | 0.871 | 0.922 | +0.030 | 0.704 |
| improve_seed2 | 2000 | 0.800 | 0.771 | 0.901 | 0.898 | -0.029 | 0.693 |
| improve_seed3 | 3000 | 0.786 | 0.810 | 0.901 | 0.895 | +0.024 | 0.589 |
| improve_seed4 | 4000 | 0.810 | 0.820 | 0.906 | 0.901 | +0.010 | 0.861 |
| **mean ± SD over seeds** | | 0.795 ± 0.010 | 0.805 ± 0.020 | 0.896 ± 0.014 | 0.905 ± 0.011 | +0.010 ± 0.023 | |

Reference single-seed models below (`eegnet`, `hybrid`, `baseline_logreg`) are the seed-offset-0 run; every comparison uses the same splits.

## Source run: `improve_mps_rerun` (device: mps)

| Model | Balanced acc. (mean ± SD, 15 folds) | AUC | F1 | Sensitivity (fold mean) | Specificity (fold mean) | Pooled AUC [95% CI] |
|---|---|---|---|---|---|---|
| baseline_logreg | 0.817 ± 0.105 | 0.907 ± 0.091 | 0.812 ± 0.119 | 0.765 | 0.869 | 0.898 [0.820, 0.960] |
| eegnet | 0.790 ± 0.125 | 0.899 ± 0.084 | 0.790 ± 0.122 | 0.744 | 0.836 | 0.875 [0.795, 0.937] |
| hybrid | 0.805 ± 0.099 | 0.911 ± 0.085 | 0.755 ± 0.183 | 0.669 | 0.940 | 0.885 [0.815, 0.943] |
| eegnet_ens5 | 0.800 ± 0.091 | 0.916 ± 0.087 | 0.795 ± 0.095 | 0.738 | 0.862 | 0.892 [0.814, 0.954] |
| hybrid_ens5 | 0.831 ± 0.114 | 0.908 ± 0.096 | 0.807 ± 0.153 | 0.736 | 0.927 | 0.886 [0.811, 0.946] |
| eegnet_ens5_valthr | 0.800 ± 0.094 | 0.916 ± 0.087 | 0.797 ± 0.094 | 0.748 | 0.853 | 0.892 [0.814, 0.954] |
| hybrid_ens5_valthr | 0.808 ± 0.131 | 0.908 ± 0.096 | 0.791 ± 0.143 | 0.717 | 0.900 | 0.886 [0.811, 0.946] |

Paired comparison over the 15 folds (difference = variant − reference; same run, same splits):

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| hybrid_ens5 | eegnet_ens5 | balanced_accuracy | +0.031 (0.098) | 7 / 4 / 4 | 0.149 | 0.582 |
| hybrid_ens5 | eegnet_ens5 | auc | -0.008 (0.039) | 6 / 2 / 7 | 0.462 | 0.73 |
| hybrid_ens5 | eegnet_ens5 | f1 | +0.013 (0.108) | 8 / 4 / 3 | 0.478 | 0.838 |
| eegnet_ens5 | eegnet | balanced_accuracy | +0.010 (0.095) | 6 / 6 / 3 | 0.547 | 0.849 |
| eegnet_ens5 | eegnet | auc | +0.016 (0.041) | 8 / 5 / 2 | 0.193 | 0.491 |
| eegnet_ens5 | eegnet | f1 | +0.005 (0.078) | 5 / 6 / 4 | 0.57 | 0.919 |
| hybrid_ens5 | hybrid | balanced_accuracy | +0.027 (0.090) | 7 / 4 / 4 | 0.356 | 0.607 |
| hybrid_ens5 | hybrid | auc | -0.003 (0.024) | 3 / 7 / 5 | 0.773 | 0.82 |
| hybrid_ens5 | hybrid | f1 | +0.053 (0.114) | 8 / 4 / 3 | 0.123 | 0.425 |
| eegnet_ens5_valthr | eegnet_ens5 | balanced_accuracy | +0.000 (0.057) | 2 / 11 / 2 | 1 | 0.992 |
| eegnet_ens5_valthr | eegnet_ens5 | f1 | +0.002 (0.038) | 3 / 11 / 1 | 0.875 | 0.925 |
| hybrid_ens5_valthr | hybrid_ens5 | balanced_accuracy | -0.023 (0.061) | 0 / 13 / 2 | 0.5 | 0.518 |
| hybrid_ens5_valthr | hybrid_ens5 | f1 | -0.016 (0.046) | 0 / 13 / 2 | 0.5 | 0.539 |

Chosen ensemble thresholds: eegnet_ens5_valthr: median 0.500, range 0.436-0.648, left at 0.5 in 9/15 folds; hybrid_ens5_valthr: median 0.500, range 0.283-0.594, left at 0.5 in 13/15 folds

