**Preregistered confirmation run: AD vs HC, 65 subjects, 5-fold subject-wise CV with repeat seeds 3-5 (15 folds), threshold 0.5. Mean ± SD over folds. The subjects are those of all earlier comparisons, on new splits: not an independent test set.**

| Model | Balanced acc. | AUC | F1 | Pooled AUC [95% CI] | Sens. (pooled) | Spec. (pooled) |
|---|---|---|---|---|---|---|
| Late fusion (EEGNet ens. + LR) | 0.869 ± 0.083 | 0.928 ± 0.077 | 0.853 ± 0.110 | 0.906 [0.833, 0.968] | 0.796 | 0.943 |
| Hybrid ensemble | 0.791 ± 0.082 | 0.901 ± 0.105 | 0.761 ± 0.124 | 0.863 [0.776, 0.936] | 0.694 | 0.885 |
| EEGNet ensemble | 0.816 ± 0.104 | 0.920 ± 0.088 | 0.803 ± 0.127 | 0.877 [0.793, 0.944] | 0.759 | 0.874 |
| Logistic regression (baseline) | 0.831 ± 0.094 | 0.917 ± 0.066 | 0.828 ± 0.102 | 0.904 [0.831, 0.962] | 0.787 | 0.874 |
| Random forest (baseline) | 0.812 ± 0.075 | 0.880 ± 0.086 | 0.812 ± 0.087 | 0.868 [0.769, 0.946] | 0.769 | 0.862 |
