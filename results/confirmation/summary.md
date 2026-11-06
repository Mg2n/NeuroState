# Confirmation run: AD vs HC on new splits

Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.

Models, settings, splits and this analysis were fixed in `PREREGISTERED.md` before the run. 65 subjects (36 AD, 29 HC), repeat seeds [3, 4, 5], 15 test folds, 5 network seeds, threshold 0.5, nothing tuned. Same subjects as all earlier comparisons, on new splits: not an independent test set.

## Results

Mean ± SD over folds. Pooled AUC = per repeat, then averaged; 95% CI: subject bootstrap (2000 resamples, stratified, seed 12345).

| Model | Balanced acc. | AUC | F1 | Pooled AUC [95% CI] |
|---|---|---|---|---|
| fusion_eegnet_ens5_logreg | 0.869 ± 0.083 | 0.928 ± 0.077 | 0.853 ± 0.110 | 0.906 [0.833, 0.968] |
| hybrid_ens5 | 0.791 ± 0.082 | 0.901 ± 0.105 | 0.761 ± 0.124 | 0.863 [0.776, 0.936] |
| eegnet_ens5 | 0.816 ± 0.104 | 0.920 ± 0.088 | 0.803 ± 0.127 | 0.877 [0.793, 0.944] |
| baseline_logreg | 0.831 ± 0.094 | 0.917 ± 0.066 | 0.828 ± 0.102 | 0.904 [0.831, 0.962] |
| baseline_rf | 0.812 ± 0.075 | 0.880 ± 0.086 | 0.812 ± 0.087 | 0.868 [0.769, 0.946] |

## Sensitivity and specificity

Threshold 0.5, AD = positive.

| Model | Sensitivity (fold mean ± SD) | Specificity (fold mean ± SD) | Sensitivity (pooled) | Specificity (pooled) |
|---|---|---|---|---|
| fusion_eegnet_ens5_logreg | 0.794 ± 0.178 | 0.944 ± 0.103 | 0.796 | 0.943 |
| hybrid_ens5 | 0.694 ± 0.215 | 0.889 ± 0.163 | 0.694 | 0.885 |
| eegnet_ens5 | 0.757 ± 0.196 | 0.876 ± 0.148 | 0.759 | 0.874 |
| baseline_logreg | 0.787 ± 0.150 | 0.876 ± 0.134 | 0.787 | 0.874 |
| baseline_rf | 0.767 ± 0.141 | 0.858 ± 0.124 | 0.769 | 0.862 |

## Preregistered comparisons

Paired over the folds. p = Nadeau-Bengio corrected resampled t-test (test/train 13/52, two-sided), unadjusted. Balanced accuracy = 3 primary tests; AUC and F1 = 6 secondary tests.

| Comparison | Metric | Diff. mean (SD) | better / tied / worse | t | p |
|---|---|---|---|---|---|
| fusion_eegnet_ens5_logreg vs eegnet_ens5 | balanced_accuracy | +0.053 (0.091) | 10 / 2 / 3 | 1.03 | 0.32 |
| fusion_eegnet_ens5_logreg vs eegnet_ens5 | auc | +0.008 (0.048) | 5 / 5 / 5 | 0.30 | 0.768 |
| fusion_eegnet_ens5_logreg vs eegnet_ens5 | f1 | +0.050 (0.095) | 9 / 2 / 4 | 0.93 | 0.37 |
| hybrid_ens5 vs eegnet_ens5 | balanced_accuracy | -0.025 (0.080) | 3 / 5 / 7 | -0.55 | 0.591 |
| hybrid_ens5 vs eegnet_ens5 | auc | -0.019 (0.041) | 3 / 4 / 8 | -0.82 | 0.425 |
| hybrid_ens5 vs eegnet_ens5 | f1 | -0.042 (0.102) | 2 / 5 / 8 | -0.74 | 0.474 |
| fusion_eegnet_ens5_logreg vs hybrid_ens5 | balanced_accuracy | +0.078 (0.083) | 10 / 5 / 0 | 1.68 | 0.116 |
| fusion_eegnet_ens5_logreg vs hybrid_ens5 | auc | +0.027 (0.052) | 7 / 5 / 3 | 0.92 | 0.374 |
| fusion_eegnet_ens5_logreg vs hybrid_ens5 | f1 | +0.092 (0.110) | 10 / 5 / 0 | 1.49 | 0.159 |

Significant at p < 0.05: primary tests none; secondary tests none.

## Pooled balanced accuracy per repeat

| Model | repeat 3 | repeat 4 | repeat 5 |
|---|---|---|---|
| fusion_eegnet_ens5_logreg | 0.868 | 0.854 | 0.886 |
| hybrid_ens5 | 0.778 | 0.778 | 0.813 |
| eegnet_ens5 | 0.837 | 0.806 | 0.806 |
| baseline_logreg | 0.837 | 0.820 | 0.834 |
| baseline_rf | 0.820 | 0.834 | 0.792 |

## Single network seeds (fold mean balanced accuracy)

| Run | EEGNet | Hybrid |
|---|---|---|
| seed0 | 0.822 | 0.796 |
| seed1 | 0.793 | 0.791 |
| seed2 | 0.768 | 0.795 |
| seed3 | 0.777 | 0.798 |
| seed4 | 0.811 | 0.762 |
| **mean ± SD** | 0.794 ± 0.022 | 0.789 ± 0.015 |

## Context: same rows on the earlier splits (not headline results)

Repeats 0-2 are the splits on which the 17 variants were compared. The 3 models were fixed with their earlier scores known. The 5-seed fusion on those splits was first computed for this table.

| Model | Bal. acc., repeats 0-2 | Bal. acc., repeats 3-5 | Change | AUC, repeats 0-2 | AUC, repeats 3-5 | Change |
|---|---|---|---|---|---|---|
| fusion_eegnet_ens5_logreg | 0.863 ± 0.096 | 0.869 ± 0.083 | +0.006 | 0.915 | 0.928 | +0.013 |
| hybrid_ens5 | 0.831 ± 0.114 | 0.791 ± 0.082 | -0.040 | 0.908 | 0.901 | -0.007 |
| eegnet_ens5 | 0.800 ± 0.091 | 0.816 ± 0.104 | +0.016 | 0.916 | 0.920 | +0.005 |
| baseline_logreg | 0.817 ± 0.105 | 0.831 ± 0.094 | +0.014 | 0.907 | 0.917 | +0.010 |
| baseline_rf | 0.800 ± 0.075 | 0.812 ± 0.075 | +0.012 | 0.857 | 0.880 | +0.023 |

## Settings and environment

| Setting | Value |
|---|---|
| folds | 5 |
| repeats | 3 |
| first_repeat | 3 |
| epochs | 40 |
| patience | 8 |
| crops | 64 |
| batch | 64 |
| lr | 0.001 |
| wd | 0.001 |
| dropout | 0.5 |
| win_sec | 4.0 |
| ms_input | corr |
| device | mps |
| seed offsets | 0, 1000, 2000, 3000, 4000 |
| fold seeds | [300, 301, 302, 303, 304, 400, 401, 402, 403, 404, 500, 501, 502, 503, 504] |
| bootstrap | 2000 resamples, seed 12345 |
| runtime | 99.9 min total; per seed 19.7, 19.6, 18.7, 22.6, 19.4 |
| environment | Python 3.12.16, macOS-26.6.2-arm64-arm-64bit |
| libraries | numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, scikit-learn 1.9.1, torch 2.15.0, mne 1.13.2, pycrostates 0.6.1 |
