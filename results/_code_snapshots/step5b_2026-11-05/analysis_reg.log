# Variant `reg` vs reference, both as 5-seed ensembles

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

## Single seeds: variant `reg` (each run alone, fold mean of 15 folds)

| Run | Network seed offset | EEGNet bal. acc. | Hybrid bal. acc. | EEGNet AUC | Hybrid AUC | Hybrid − EEGNet bal. acc. | Corrected t-test p |
|---|---|---|---|---|---|---|---|
| improve_reg_seed0 | 0 | 0.809 | 0.827 | 0.912 | 0.919 | +0.018 | 0.841 |
| improve_reg_seed1 | 1000 | 0.797 | 0.813 | 0.880 | 0.927 | +0.016 | 0.839 |
| improve_reg_seed2 | 2000 | 0.806 | 0.800 | 0.909 | 0.906 | -0.006 | 0.932 |
| improve_reg_seed3 | 3000 | 0.755 | 0.817 | 0.898 | 0.894 | +0.062 | 0.207 |
| improve_reg_seed4 | 4000 | 0.814 | 0.790 | 0.904 | 0.911 | -0.023 | 0.742 |
| **mean ± SD over seeds** | | 0.796 ± 0.024 | 0.809 ± 0.015 | 0.901 ± 0.013 | 0.911 ± 0.012 | +0.013 ± 0.032 | |

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
| reg_eegnet_ens5 | 0.829 ± 0.081 | 0.917 ± 0.087 | 0.823 ± 0.097 | 0.774 | 0.884 | 0.898 [0.823, 0.956] |
| reg_hybrid_ens5 | 0.851 ± 0.122 | 0.919 ± 0.093 | 0.815 ± 0.167 | 0.735 | 0.967 | 0.901 [0.830, 0.957] |

Paired comparison over the 15 folds (difference = variant − reference; same run, same splits):

| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |
|---|---|---|---|---|---|---|
| reg_hybrid_ens5 | hybrid_ens5 | balanced_accuracy | +0.019 (0.082) | 2 / 12 / 1 | 0.75 | 0.679 |
| reg_hybrid_ens5 | hybrid_ens5 | auc | +0.011 (0.020) | 4 / 11 / 0 | 0.125 | 0.337 |
| reg_hybrid_ens5 | hybrid_ens5 | f1 | +0.008 (0.053) | 2 / 12 / 1 | 0.75 | 0.796 |
| reg_hybrid_ens5 | eegnet_ens5 | balanced_accuracy | +0.050 (0.105) | 8 / 4 / 3 | 0.0713 | 0.406 |
| reg_hybrid_ens5 | eegnet_ens5 | auc | +0.003 (0.038) | 6 / 4 / 5 | 0.661 | 0.879 |
| reg_hybrid_ens5 | eegnet_ens5 | f1 | +0.021 (0.118) | 8 / 4 / 3 | 0.377 | 0.762 |
| reg_eegnet_ens5 | eegnet_ens5 | balanced_accuracy | +0.029 (0.047) | 5 / 10 / 0 | 0.0625 | 0.294 |
| reg_eegnet_ens5 | eegnet_ens5 | auc | +0.002 (0.014) | 1 / 13 / 1 | 1 | 0.854 |
| reg_eegnet_ens5 | eegnet_ens5 | f1 | +0.028 (0.046) | 5 / 10 / 0 | 0.0625 | 0.285 |
| reg_hybrid_ens5 | reg_eegnet_ens5 | balanced_accuracy | +0.021 (0.089) | 8 / 3 / 4 | 0.272 | 0.676 |
| reg_hybrid_ens5 | reg_eegnet_ens5 | auc | +0.002 (0.043) | 6 / 3 / 6 | 0.871 | 0.941 |
| reg_hybrid_ens5 | reg_eegnet_ens5 | f1 | -0.008 (0.107) | 6 / 3 / 6 | 0.987 | 0.897 |

