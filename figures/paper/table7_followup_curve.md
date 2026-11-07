**Follow-up learning curve, primary labels (descriptive, no tests). Mean ± SD over 15 folds; diff. = seq-CNN minus logistic regression (LR), paired by fold; SD across draws = SD over the 5 draws within a fold, averaged over folds; 52 is the full fold, with one possible subset and so no draws.**

| Training subjects | Bal. acc. seq-CNN | Bal. acc. LR | Bal. acc. diff. | Bal. acc. SD across draws (seq-CNN / LR) | AUC seq-CNN | AUC LR | AUC diff. | AUC SD across draws (seq-CNN / LR) |
|---|---|---|---|---|---|---|---|---|
| 20 | 0.752 ± 0.045 | 0.788 ± 0.062 | -0.036 ± 0.049 | 0.083 / 0.075 | 0.828 ± 0.088 | 0.873 ± 0.058 | -0.045 ± 0.061 | 0.059 / 0.058 |
| 35 | 0.800 ± 0.060 | 0.814 ± 0.078 | -0.014 ± 0.069 | 0.058 / 0.052 | 0.875 ± 0.073 | 0.904 ± 0.062 | -0.029 ± 0.046 | 0.047 / 0.035 |
| 52 (full) | 0.840 ± 0.056 | 0.831 ± 0.094 | +0.009 ± 0.074 | - | 0.901 ± 0.086 | 0.917 ± 0.066 | -0.016 ± 0.044 | - |
