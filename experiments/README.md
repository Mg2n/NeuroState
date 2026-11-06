# Hybrid EEGNet + Microstate CNN experiments (ds004504)

Compares three models for Alzheimer's (A) vs healthy (C), with subject-wise cross-validation:
- **baseline**: 24 microstate features per subject -> logistic regression / random forest
- **eegnet**: EEGNet-style CNN on raw 4-s EEG windows
- **hybrid**: EEGNet branch + small microstate CNN branch (our model)

Plus a leakage demo (EEGNet with windows split at random, people mixed across train/test).

## Run
```bash
pip install torch mne pycrostates scikit-learn eeglabio pandas
python prep.py --bids ../ds004504 --out ../prepared
python run_experiment.py --prep ../prepared --out ../results --groups A C
```
Results: `results/results.json`, `fold_metrics.csv`, `oof_predictions.csv`.

Test without real data: `python make_fake.py fake_bids && python prep.py --bids fake_bids --out fake_prep`.
