# Follow-up study: microstate sequence CNN vs summary features: preregistration

Written: Friday 6 November 2026, 20:10:47 +0300, before any code change for this study and before any prediction from these models existed.
Project: Neurostate, ds004504. Research use only: this is classification of AD vs healthy controls (HC), not diagnosis. It is separate from the submitted paper.

## Question

For AD vs HC, does a standalone CNN on the A-D microstate label sequence beat logistic regression on the 24 summary features computed from the same label sequence, and how does each change with training-set size?

## Data and splits (fixed)

- 65 subjects (36 AD, 29 HC), prepared as in `results/prep_report.md`: the 2-20 Hz `ms` copy at 128 Hz. All windows kept, no subject excluded.
- Outer split: `StratifiedKFold(5, shuffle=True, random_state=repeat)` over subjects, repeats 3, 4 and 5: 15 test folds, about 13 test subjects each. These are the confirmation splits.
- Maps: fitted on the training subjects of each fold only, with `fold_microstates` and fold seed = 100 x repeat + fold, as now.
- **Sanity check, not a result:** with primary labels, the logistic regression must reproduce the confirmation run: 0.831 mean balanced accuracy, and fold by fold the same probabilities as `results/confirmation/seed0`. If it does not, the analysis stops and this is reported before anything else is interpreted.

## Labels (fixed)

- **PRIMARY:** argmax of |spatial correlation| with the 4 maps at every sample at 128 Hz, with no smoothing, exactly as `microstates.corr_sequence(...).argmax(0)` does now. Because of this, visits are very short: about 2-3 samples, or about 20 ms, on average. This is known from Task 04 (mean durations of about 16-25 ms) and is stated here so that nobody reads these sequences as conventional smoothed microstates.
- **SECONDARY:** smoothed labels, from the primary labels of each subject's whole recording:
  - **Method:** minimum-segment rejection, as in Pycrostates (Férat et al., 2022, J. Open Source Softw. 7(78):4564, doi: 10.21105/joss.04564): the `min_segment_length` option of `ModKMeans.predict`, implemented in `_BaseCluster._reject_short_segments` (version 0.6.1). No Pascual-Marqui temporal smoothing is used (`factor = 0`).
  - **Minimum segment length:** 4 samples = 31.25 ms at 128 Hz. Any segment shorter than 4 samples is removed. This is the smallest whole number of samples of at least 30 ms. It was chosen before looking at visit lengths on these labels and will not be changed because of them.
  - **Merge rule:** the short segment's samples are reassigned one at a time from its ends to the neighbouring labels. At each step, the left end goes to the left neighbour if the |spatial correlation| between samples left-1 and left is larger than that between samples right and right+1; the right end goes to the right neighbour if that second correlation is larger; on a tie (difference <= 1e-8) both ends move, or only the left end if one sample remains. Segments are then listed again and the first remaining short segment is processed, until none is left. The first and last segments of a recording are exempt. No samples are set to unlabelled (`reject_edges` is not used).
  - **Implementation:** because the Pycrostates routine relists the whole recording after each fix, it is too slow for recordings of about 76,000 samples. We use a linear-time version that must give identical labels, tested against the Pycrostates function before launch.
  - The same smoothed labels feed both the seq-CNN and the logistic regression.

## Models (fixed)

**(a) seq-CNN.** The paper's microstate branch (`MSBranch` in `models.py`) trained alone, from scratch, with its own linear head (32 units to 2 classes). Input: one-hot 4 x 512 windows (4 s).
- Subject score: mean window probability. Threshold 0.5.
- 5-seed ensemble: mean subject probability over seed offsets 0, 1000, 2000, 3000, 4000. Network seed = fold seed + offset. Device MPS.
- Task 05 training defaults, with no tuning: Adam, learning rate 1e-3, weight decay 1e-3, cosine schedule, dropout 0.5, class-weighted cross-entropy, 40 epochs maximum, patience 8, 64 random crops per subject per epoch, batch size 64. Early stopping on 15% of the training subjects, as now.
- The amplitude jitter and Gaussian noise of Task 05 act on raw EEG only, so they do not apply here. The seq-CNN's augmentation is the random crops.

**(b) Logistic regression.** The 24 features from the same labels, per subject over the whole recording: coverage, mean duration and occurrence per state, plus 12 transition probabilities (`microstates.features`). The paper's fixed settings: `StandardScaler`, then `LogisticRegression(C=0.5, class_weight="balanced", max_iter=5000)`. Threshold 0.5.

**Secondary models.**
- seq-CNN on the 4 |correlation| traces (same training, same 5 seeds, no labels involved).
- EEGNet 5-seed ensemble, reused from `results/confirmation`, with no retraining.
- The random forest of `run_experiment.py` is produced in the same runs and is listed as a reference row only, with no test.

## Outcomes and tests (fixed)

- **Primary metric:** subject-level balanced accuracy at threshold 0.5.
- Also reported for every row: AUC, F1, sensitivity and specificity (AD = positive). Mean ± SD over the 15 folds; sensitivity and specificity also pooled over all out-of-fold predictions.
- **Test:** paired over the 15 folds, Nadeau-Bengio corrected resampled t-test (test/train 13/52), two-sided. p values are unadjusted. A comparison is called significant only if p < 0.05.
- **A non-significant result does not show that the models are equal.** There are about 13 test subjects per fold, so modest real differences can be missed.

| # | Comparison | Metric | Role |
|---|---|---|---|
| 1 | seq-CNN one-hot, primary labels vs logistic regression, primary labels | balanced accuracy | **PRIMARY** |
| 2 | same | AUC | secondary |
| 3 | same | F1 | secondary |
| 4 | seq-CNN one-hot, smoothed labels vs logistic regression, smoothed labels | balanced accuracy | secondary |
| 5 | same | AUC | secondary |
| 6 | seq-CNN one-hot, smoothed vs seq-CNN one-hot, primary | balanced accuracy | secondary |
| 7 | logistic regression, smoothed vs logistic regression, primary | balanced accuracy | secondary |
| 8 | seq-CNN on absolute correlation vs seq-CNN one-hot, primary | balanced accuracy | secondary |
| 9 | seq-CNN on absolute correlation vs logistic regression, primary | balanced accuracy | secondary |
| 10 | seq-CNN one-hot, primary vs EEGNet ensemble | balanced accuracy | secondary |
| 11 | logistic regression, primary vs EEGNet ensemble | balanced accuracy | secondary |

**Total: 11 tests: 1 primary and 10 secondary.** The learning curve adds no tests.

"The seq-CNN wins on the primary test" means comparison 1 has a positive difference and p < 0.05.

## Learning curve (fixed)

Primary labels only: seq-CNN one-hot vs logistic regression.
- **Training sizes:** 20, 35 and the full fold (52).
- **Stratified by class:** n_AD = round(size x AD share of that fold's training subjects), n_HC = size - n_AD.
- **Nested subsets:** for each draw, each class's training subjects are shuffled once, and each size takes the first n of that order, so 20 lies inside 35, which lies inside the full fold.
- **Draws:** 5 per size per outer fold, 150 subsets in all. Shuffle generator: `numpy.random.default_rng(910000 + 1000*repeat + 10*fold + draw)`, draw = 0-4; each class is shuffled in that order, AD first.
- **Test subjects:** unchanged, the fold's own test subjects.
- **Maps:** refitted on each subset only. Map seed s = fold seed + 100000*(draw+1) + 10000*size_index, with size_index 0 for 20 and 1 for 35.
- **Identical subsets:** logistic regression and seq-CNN get the same subset and the same maps. Logistic regression trains on the whole subset. The seq-CNN holds out its early-stopping subjects from that subset, as in the main runs.
- **Early stopping in subsets:** `train_test_split(test_size=0.15, stratify=y, random_state=s)` as in the main runs, which gives 3 of 20 and 6 of 35 subjects, with at least 1 per class.
- **Too few subjects in a class:** every outer training fold has more than 20 subjects in each class, so this cannot happen at these sizes. The script asserts at least 2 subjects per class in the subset and at least 1 per class in both the training and early-stopping parts. If an assertion fails, the run stops and this is reported; nothing is resized silently.
- **seq-CNN at sizes 20 and 35:** 5-seed ensemble per draw, offsets 0-4000, network seed = s + offset. Otherwise the same settings as model (a).
- **Full fold:** the main-run values. There is only one possible subset, so there are no draws at this size.
- **Reporting:** for each fold and size, metrics are averaged over draws, giving 15 fold values per size. We report mean ± SD over folds for both models, balanced accuracy and AUC, plus the per-size difference (seq-CNN - logistic regression) mean ± SD, and the SD across draws.
- **The curve is descriptive.** It has no significance tests, and it cannot show what happens beyond 52 subjects.

## Out of scope

Unless the seq-CNN wins on the primary test: the temporal-order shuffle control and any external cohort.

## Details the request left open, fixed here by the assistant

- The 4-sample minimum segment length, and the use of Pycrostates' rule.
- The list of secondary tests and the definition of "wins".
- All curve seed formulas, class rounding, and using primary labels only for the curve.
- Random forest as a reference row. A learning-curve plot is added to `summary.md` as a figure.
- **Technical failure:** a crashed run may be restarted with identical settings, and the restart is reported. A finished run is never rerun.
- **Curve cost:** if the runtime estimate is over about 5 h, a cheaper design is proposed and the user chooses. Any change is recorded as a dated amendment below, before launch.

## Known limits, stated in advance

- **Not blind and not independent.** The 65 subjects and these splits were used for the confirmation run, so logistic regression (0.831) and EEGNet (0.816) are already known on them, and the seq-CNN is new. A one-hot hybrid was also explored on repeats 0-2.
- **Unequal views of the data.** The seq-CNN sees 4-s windows, averaged over the recording at test time; logistic regression summarises the whole recording at once.
- **Primary labels are noisy by construction,** because they have no smoothing. Results may not carry over to conventional smoothed microstate sequences.
- **Small sample and overlapping training sets.** About 13 test subjects per fold; the corrected t-test is approximate; p values are unadjusted for the 11 tests.
- **Learning-curve subsets overlap,** because they are drawn from the same fold. The SD across draws understates uncertainty about new data.

## Amendments

- 6 November 2026, 20:13:25 +0300, before any code change: wording of the merge rule corrected to match the Pycrostates source ("larger", not "at least as large"). The rule itself did not change.

## Frozen code (added 6 November 2026, 20:21:45 +0300, before launch; nothing launched yet)

Snapshot: `results/followup_seqcnn/_code_snapshot/`. Regression on fake data (CPU): with no new options, predictions match `results/_code_snapshots/step7_confirmation_2026-11-06/run_experiment.py` byte for byte, in 4 configurations (2-class, one-hot with repeat 3, corr+feats, 3-class). The linear-time segment rejection gave the same labels as the Pycrostates routine in all 94 test cases. The analysis script was tested on fake runs only. If any file below changes before launch, this section is rewritten and the user is told.

```
cbec53539810420d66aef031d8c2c530d1f5d8eaf78df06d7e37ecc17f33ad0c  run_experiment.py
04dc6dce70d391777f0b1b6f67bd8d6650e27eecc6be33ff83d69a9b8eebb884  models.py
d6d82d02f8b3441684298c01e26bd54cb03e41fd7105e0e7f3fbaa1476ebfa12  microstates.py
fafbbb572f055da2f1ab76a8472127def9afeed88dbc8423a1d30b2160efdf48  seqcnn_curve.py
6101cabac34cfcc0ea214febab8900c5a515cb8cbd3b478059e18edeaec3725f  followup_analysis.py
0f2d89eb377e05152a337ad1e65255f55080f5631bf54267236a768295a0195c  improve_analysis.py
6ab7bde4de1130ed7264e18fc8669f4dba53f4b3197a880856f2b4b50d16b667  summarize_main.py
779a95ae1aaf1d8a6d931563ecb4e5e48d6b20bbc8f6518c77d03152525deb91  queue.sh
f1536c244b72dc947abffda38b940532ad13048b9d6fb95a12ee482ab3ea0b33  prepared/subjects.csv
```
