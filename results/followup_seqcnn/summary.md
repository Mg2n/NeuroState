# Follow-up: microstate sequence CNN vs summary features

Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.

Fixed in `PREREGISTERED.md` before the run. 65 subjects, 15 test folds (repeats [np.int64(3), np.int64(4), np.int64(5)]), threshold 0.5. Same subjects and splits as the confirmation run: not independent, and logistic regression and EEGNet were already known on them.

**Sanity check.** Logistic regression vs confirmation run: same test subjects True; largest probability difference 0.0. Mean balanced accuracy 0.831.

## Results

Mean ± SD over folds. Sensitivity and specificity: AD = positive.

| Model | Balanced acc. | AUC | F1 | Sensitivity | Specificity | Sens. (pooled) | Spec. (pooled) |
|---|---|---|---|---|---|---|---|
| seq-CNN one-hot, primary labels | 0.840 ± 0.056 | 0.901 ± 0.086 | 0.812 ± 0.086 | 0.713 ± 0.135 | 0.967 ± 0.069 | 0.713 | 0.966 |
| Logistic regression, primary labels | 0.831 ± 0.094 | 0.917 ± 0.066 | 0.828 ± 0.102 | 0.787 ± 0.150 | 0.876 ± 0.134 | 0.787 | 0.874 |
| seq-CNN one-hot, smoothed labels | 0.769 ± 0.083 | 0.850 ± 0.082 | 0.749 ± 0.104 | 0.685 ± 0.170 | 0.853 ± 0.125 | 0.685 | 0.851 |
| Logistic regression, smoothed labels | 0.755 ± 0.097 | 0.835 ± 0.078 | 0.758 ± 0.115 | 0.731 ± 0.181 | 0.780 ± 0.169 | 0.731 | 0.782 |
| seq-CNN on absolute correlation | 0.779 ± 0.096 | 0.869 ± 0.108 | 0.742 ± 0.136 | 0.658 ± 0.198 | 0.900 ± 0.164 | 0.657 | 0.897 |
| EEGNet ensemble (reused) | 0.816 ± 0.104 | 0.920 ± 0.088 | 0.803 ± 0.127 | 0.757 ± 0.196 | 0.876 ± 0.148 | 0.759 | 0.874 |
| Random forest, primary labels (reference) | 0.812 ± 0.075 | 0.880 ± 0.086 | 0.812 ± 0.087 | 0.767 ± 0.141 | 0.858 ± 0.124 | 0.769 | 0.862 |
| Random forest, smoothed labels (reference) | 0.774 ± 0.101 | 0.837 ± 0.093 | 0.787 ± 0.098 | 0.768 ± 0.145 | 0.780 ± 0.174 | 0.769 | 0.782 |

## Preregistered tests

Paired over the folds. Nadeau-Bengio corrected resampled t-test (test/train 13/52), two-sided, unadjusted; 11 tests in total. A non-significant result does not show that the models are equal.

| # | Role | Comparison | Metric | Diff. mean (SD) | better / tied / worse | t | p |
|---|---|---|---|---|---|---|---|
| 1 | PRIMARY | seq-CNN one-hot, primary labels vs Logistic regression, primary labels | balanced_accuracy | +0.009 (0.074) | 7 / 4 / 4 | 0.21 | 0.839 |
| 2 | secondary | seq-CNN one-hot, primary labels vs Logistic regression, primary labels | auc | -0.016 (0.044) | 5 / 2 / 8 | -0.64 | 0.535 |
| 3 | secondary | seq-CNN one-hot, primary labels vs Logistic regression, primary labels | f1 | -0.016 (0.087) | 4 / 4 / 7 | -0.33 | 0.747 |
| 4 | secondary | seq-CNN one-hot, smoothed labels vs Logistic regression, smoothed labels | balanced_accuracy | +0.013 (0.103) | 8 / 3 / 4 | 0.23 | 0.821 |
| 5 | secondary | seq-CNN one-hot, smoothed labels vs Logistic regression, smoothed labels | auc | +0.015 (0.068) | 7 / 3 / 5 | 0.39 | 0.701 |
| 6 | secondary | seq-CNN one-hot, smoothed labels vs seq-CNN one-hot, primary labels | balanced_accuracy | -0.071 (0.095) | 2 / 1 / 12 | -1.33 | 0.205 |
| 7 | secondary | Logistic regression, smoothed labels vs Logistic regression, primary labels | balanced_accuracy | -0.076 (0.105) | 2 / 3 / 10 | -1.28 | 0.22 |
| 8 | secondary | seq-CNN on absolute correlation vs seq-CNN one-hot, primary labels | balanced_accuracy | -0.061 (0.068) | 0 / 5 / 10 | -1.59 | 0.134 |
| 9 | secondary | seq-CNN on absolute correlation vs Logistic regression, primary labels | balanced_accuracy | -0.052 (0.083) | 4 / 2 / 9 | -1.11 | 0.284 |
| 10 | secondary | seq-CNN one-hot, primary labels vs EEGNet ensemble (reused) | balanced_accuracy | +0.024 (0.114) | 9 / 1 / 5 | 0.37 | 0.718 |
| 11 | secondary | Logistic regression, primary labels vs EEGNet ensemble (reused) | balanced_accuracy | +0.015 (0.117) | 7 / 4 / 4 | 0.23 | 0.825 |

Significant at p < 0.05: none. The seq-CNN wins on the primary test (positive difference and p < 0.05): no.

## Learning curve (descriptive, primary labels)

Metrics averaged over 5 draws within each fold, then mean ± SD over folds. seq-CNN = 5-seed ensemble per draw. The full fold has one possible subset, so no draws. There are no tests, and the curve cannot show what happens beyond 52 subjects.

**balanced_accuracy**

| Training size | seq-CNN | Logistic regression | Difference (seq-CNN − logreg) | SD across draws, seq-CNN | SD across draws, logreg |
|---|---|---|---|---|---|
| 20 | 0.752 ± 0.045 | 0.788 ± 0.062 | -0.036 ± 0.049 | 0.083 | 0.075 |
| 35 | 0.800 ± 0.060 | 0.814 ± 0.078 | -0.014 ± 0.069 | 0.058 | 0.052 |
| 52 (full) | 0.840 ± 0.056 | 0.831 ± 0.094 | +0.009 ± 0.074 | - | - |

**auc**

| Training size | seq-CNN | Logistic regression | Difference (seq-CNN − logreg) | SD across draws, seq-CNN | SD across draws, logreg |
|---|---|---|---|---|---|
| 20 | 0.828 ± 0.088 | 0.873 ± 0.058 | -0.045 ± 0.061 | 0.059 | 0.058 |
| 35 | 0.875 ± 0.073 | 0.904 ± 0.062 | -0.029 ± 0.046 | 0.047 | 0.035 |
| 52 (full) | 0.901 ± 0.086 | 0.917 ± 0.066 | -0.016 ± 0.044 | - | - |

Figure: `learning_curve.png`.

## Settings

Runtime: 1.02 h in total.
Device: mps.
