**Secondary task: AD vs FTD vs HC, 5-fold subject-wise CV × 3 (repeat seeds 0-2), chance = 0.333. The full cohort is the main result and the sub-086 exclusion is a sensitivity analysis. Effect = same test subjects, sub-086 removed from training and map fitting minus kept; p = corrected resampled t-test.**

| Model | Bal. acc. (n = 88) | Macro-F1 | Macro AUC | Bal. acc. without sub-086 (n = 87) | Effect of removal (p) |
|---|---|---|---|---|---|
| Logistic regression (baseline) | 0.554 ± 0.102 | 0.534 ± 0.099 | 0.745 ± 0.052 | 0.594 ± 0.093 | +0.037 (0.19) |
| Random forest (baseline) | 0.579 ± 0.087 | 0.565 ± 0.090 | 0.746 ± 0.055 | 0.576 ± 0.070 | -0.008 (0.87) |
| EEGNet ensemble | 0.572 ± 0.084 | 0.542 ± 0.097 | 0.763 ± 0.065 | 0.572 ± 0.070 | +0.006 (0.90) |
| Hybrid ensemble | 0.569 ± 0.100 | 0.540 ± 0.099 | 0.763 ± 0.084 | 0.580 ± 0.116 | +0.013 (0.75) |
