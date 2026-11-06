**Exploratory variants from Task 06 (repeat seeds 0-2, the Task 05 splits). No row was selected on test folds and none is the headline result; the variants share these splits, so the best row is expected to look better by chance. p = corrected resampled t-test.**

| Change | Balanced accuracy (mean ± SD, 15 folds) | AUC (mean ± SD) | vs comparator: Δ bal. acc. (corrected p) | Δ AUC (corrected p) |
|---|---|---|---|---|
| Task 05 hybrid (CPU, 1 seed) | 0.813 ± 0.117 | 0.908 ± 0.103 | reference | reference |
| Task 05 EEGNet (CPU, 1 seed) | 0.852 ± 0.099 | 0.922 ± 0.078 | +0.039 (0.60) vs hybrid (1 seed) | +0.014 (0.74) |
| Late fusion 0.5 EEGNet + 0.5 logreg (CPU predictions) | 0.880 ± 0.078 | 0.921 ± 0.076 | +0.067 (0.22) vs hybrid (1 seed) | +0.013 (0.77) |
| Hybrid, MPS rerun (1 seed) - reference for MPS rows | 0.805 ± 0.099 | 0.911 ± 0.085 | reference | reference |
| EEGNet, MPS rerun (1 seed) | 0.790 ± 0.125 | 0.899 ± 0.084 | -0.015 (0.86) vs hybrid (1 seed) | -0.012 (0.76) |
| Late fusion 0.5 EEGNet + 0.5 logreg (MPS predictions) | 0.875 ± 0.095 | 0.915 ± 0.087 | +0.070 (0.31) vs hybrid (1 seed) | +0.004 (0.93) |
| EEGNet, threshold from inner-validation subjects | 0.783 ± 0.126 | 0.899 ± 0.084 | -0.022 (0.80) vs hybrid (1 seed) | unchanged (same scores) |
| Hybrid, threshold from inner-validation subjects | 0.795 ± 0.126 | 0.911 ± 0.085 | -0.010 (0.85) vs hybrid (1 seed) | unchanged (same scores) |
| EEGNet, 5-seed ensemble | 0.800 ± 0.091 | 0.916 ± 0.087 | -0.031 (0.58) vs hybrid ens. | +0.008 (0.73) |
| Hybrid, 5-seed ensemble - reference for ensemble rows | 0.831 ± 0.114 | 0.908 ± 0.096 | +0.027 (0.61) vs hybrid (1 seed) | -0.003 (0.82) |
| Hybrid, 5-seed ensemble + inner-validation threshold | 0.808 ± 0.131 | 0.908 ± 0.096 | -0.023 (0.52) vs hybrid ens. | unchanged (same scores) |
| EEGNet, 8-s windows, 5-seed ensemble | 0.817 ± 0.100 | 0.914 ± 0.090 | -0.014 (0.83) vs hybrid ens. | +0.006 (0.75) |
| Hybrid, 8-s windows, 5-seed ensemble | 0.828 ± 0.112 | 0.920 ± 0.075 | -0.003 (0.92) vs hybrid ens. | +0.012 (0.60) |
| Hybrid, one-hot microstate labels, 5-seed ensemble | 0.841 ± 0.098 | 0.922 ± 0.087 | +0.010 (0.87) vs hybrid ens. | +0.014 (0.48) |
| Hybrid, abs. correlation + 24 window features (MLP), 5-seed ensemble | 0.808 ± 0.117 | 0.913 ± 0.091 | -0.023 (0.53) vs hybrid ens. | +0.005 (0.76) |
| EEGNet, nested-CV regularisation, 5-seed ensemble | 0.829 ± 0.081 | 0.917 ± 0.087 | -0.002 (0.97) vs hybrid ens. | +0.009 (0.73) |
| Hybrid, nested-CV regularisation, 5-seed ensemble | 0.851 ± 0.122 | 0.919 ± 0.093 | +0.019 (0.68) vs hybrid ens. | +0.011 (0.34) |
