# Variant `win8` vs reference, both as 5-seed ensembles

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

## Single seeds: variant `win8` (each run alone, fold mean of 15 folds)

| Run | Network seed offset | EEGNet bal. acc. | Hybrid bal. acc. | EEGNet AUC | Hybrid AUC | Hybrid − EEGNet bal. acc. | Corrected t-test p |
|---|---|---|---|---|---|---|---|
| improve_win8_seed0 | 0 | 0.813 | 0.806 | 0.901 | 0.900 | -0.007 | 0.925 |
| improve_win8_seed1 | 1000 | 0.801 | 0.826 | 0.901 | 0.909 | +0.025 | 0.715 |
| improve_win8_seed2 | 2000 | 0.808 | 0.764 | 0.895 | 0.903 | -0.043 | 0.475 |
| improve_win8_seed3 | 3000 | 0.825 | 0.805 | 0.900 | 0.915 | -0.020 | 0.812 |
| improve_win8_seed4 | 4000 | 0.819 | 0.762 | 0.901 | 0.911 | -0.056 | 0.585 |
| **mean ± SD over seeds** | | 0.813 ± 0.009 | 0.793 ± 0.028 | 0.900 ± 0.003 | 0.907 ± 0.006 | -0.020 ± 0.032 | |

## Single seeds: reference (4-s windows, |correlation| input) (each run alone, fold mean of 15 folds)

| Run | Network seed offset | EEGNet bal. acc. | Hybrid bal. acc. | EEGNet AUC | Hybrid AUC | Hybrid − EEGNet bal. acc. | Corrected t-test p |
|---|---|---|---|---|---|---|---|
| improve_mps_rerun | 0 | 0.790 | 0.805 | 0.899 | 0.911 | +0.015 | 0.86 |
| improve_seed1 | 1000 | 0.791 | 0.820 | 0.871 | 0.922 | +0.030 | 0.704 |
| improve_seed2 | 2000 | 0.800 | 0.771 | 0.901 | 0.898 | -0.029 | 0.693 |
| improve_seed3 | 3000 | 0.786 | 0.810 | 0.901 | 0.895 | +0.024 | 0.589 |
| improve_seed4 | 4000 | 0.810 | 0.820 | 0.906 | 0.901 | +0.010 | 0.861 |
| **mean ± SD over seeds** | | 0.795 ± 0.010 | 0.805 ± 0.020 | 0.896 ± 0.014 | 0.905 ± 0.011 | +0.010 ± 0.023 | |

Reference single-seed models below (`eegnet`, `hybrid`, `baseline_logreg`) are the seed-offset-0 reference run. `*_ens5` = mean probability over the 5 seeds; variant and reference use the same outer splits, fold seeds, inner early-stopping subjects and network seed offsets (checked: identical baseline probabilities).

## Source run: `improve_mps_rerun` (device: mps)

| Model | Balanced acc. (mean ± SD, 15 folds) | AUC | F1 | Sensitivity (fold mean) | Specificity (fold mean) | Pooled AUC [95% CI] |
|---|---|---|---|---|---|---|
| baseline_logreg | 0.817 ± 0.105 | 0.907 ± 0.091 | 0.812 ± 0.119 | 0.765 | 0.869 | 0.898 [0.820, 0.960] |
| eegnet | 0.790 ± 0.125 | 0.899 ± 0.084 | 0.790 ± 0.122 | 0.744 | 0.836 | 0.875 [0.795, 0.937] |
| hybrid | 0.805 ± 0.099 | 0.911 ± 0.085 | 0.755 ± 0.183 | 0.669 | 0.940 | 0.885 [0.815, 0.943] |
| eegnet_ens5 | 0.800 ± 0.091 | 0.916 ± 0.087 | 0.795 ± 0.095 | 0.738 | 0.862 | 0.892 [0.814, 0.954] |
| hybrid_ens5 | 0.831 ± 0.114 | 0.908 ± 0.096 | 0.807 ± 0.153 | 0.736 | 0.927 | 0.886 [0.811, 0.946] |
| win8_eegnet_ens5 | 0.817 ± 0.100 | 0.914 ± 0.090 | 0.818 ± 0.104 | 0.774 | 0.860 | 0.895 [0.819, 0.957] |
| win8_hybrid_ens5 | 0.828 ± 0.112 | 0.920 ± 0.075 | 0.789 ± 0.190 | 0.717 | 0.940 | 0.890 [0.820, 0.948] |

Paired comparison over the 15 folds (difference = variant − reference; same run, same splits):

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| win8_hybrid_ens5 | hybrid_ens5 | balanced_accuracy | -0.003 (0.049) | 2 / 10 / 3 | 0.75 | 0.919 |
| win8_hybrid_ens5 | hybrid_ens5 | auc | +0.012 (0.042) | 6 / 7 / 2 | 0.305 | 0.603 |
| win8_hybrid_ens5 | hybrid_ens5 | f1 | -0.019 (0.065) | 2 / 10 / 3 | 0.312 | 0.616 |
| win8_hybrid_ens5 | eegnet_ens5 | balanced_accuracy | +0.028 (0.108) | 8 / 3 / 4 | 0.246 | 0.651 |
| win8_hybrid_ens5 | eegnet_ens5 | auc | +0.005 (0.042) | 6 / 2 / 7 | 0.699 | 0.844 |
| win8_hybrid_ens5 | eegnet_ens5 | f1 | -0.006 (0.154) | 8 / 3 / 4 | 0.801 | 0.945 |
| win8_eegnet_ens5 | eegnet_ens5 | balanced_accuracy | +0.017 (0.036) | 4 / 10 / 1 | 0.125 | 0.424 |
| win8_eegnet_ens5 | eegnet_ens5 | auc | -0.001 (0.017) | 3 / 8 / 4 | 0.859 | 0.884 |
| win8_eegnet_ens5 | eegnet_ens5 | f1 | +0.023 (0.039) | 5 / 10 / 0 | 0.0625 | 0.304 |
| win8_hybrid_ens5 | win8_eegnet_ens5 | balanced_accuracy | +0.011 (0.119) | 6 / 3 / 6 | 0.584 | 0.867 |
| win8_hybrid_ens5 | win8_eegnet_ens5 | auc | +0.006 (0.045) | 6 / 3 / 6 | 0.832 | 0.812 |
| win8_hybrid_ens5 | win8_eegnet_ens5 | f1 | -0.029 (0.158) | 7 / 3 / 5 | 0.801 | 0.746 |

