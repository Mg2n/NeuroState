"""Task 06: write results/improvements.md, one table over all improvement experiments, from saved fold metrics.

Each row is compared with the hybrid it can fairly be compared with: same device, same splits, same number of seeds
(single-seed rows -> the single-seed hybrid of the same run; 5-seed ensemble rows -> the 5-seed hybrid ensemble).
Paired over the 15 outer folds; Nadeau-Bengio corrected resampled t-test.

  .venv/bin/python make_improvements.py
"""
import os
import time

import pandas as pd

from improve_analysis import paired

R = "../results"


def load(exp, source=None):
    f = pd.read_csv(os.path.join(R, exp, "fold_metrics.csv"))
    return f if source is None else f[f.source_run == source]


REF_LABEL = {"hybrid": "hybrid (1 seed)", "hybrid_ens5": "hybrid ens."}  # reference models, as printed in the table
# (label, experiment folder, source_run filter, model, reference model, one-line reading)
ROWS = [
    ("Task 05 hybrid (CPU, 1 seed)", "improve_fusion", "main_AD_vs_HC", "hybrid", None, None),
    ("Task 05 EEGNet (CPU, 1 seed)", "improve_fusion", "main_AD_vs_HC", "eegnet", "hybrid", None),
    ("Late fusion 0.5 EEGNet + 0.5 logreg (CPU predictions)", "improve_fusion", "main_AD_vs_HC",
     "fusion_eegnet_logreg", "hybrid", None),
    ("Hybrid, MPS rerun (1 seed) - reference for MPS rows", "improve_threshold", "improve_mps_rerun", "hybrid",
     None, None),
    ("EEGNet, MPS rerun (1 seed)", "improve_threshold", "improve_mps_rerun", "eegnet", "hybrid", None),
    ("Late fusion 0.5 EEGNet + 0.5 logreg (MPS predictions)", "improve_fusion", "improve_mps_rerun",
     "fusion_eegnet_logreg", "hybrid", None),
    ("EEGNet, threshold from inner-validation subjects", "improve_threshold", "improve_mps_rerun", "eegnet_valthr",
     "hybrid", None),
    ("Hybrid, threshold from inner-validation subjects", "improve_threshold", "improve_mps_rerun", "hybrid_valthr",
     "hybrid", None),
    ("EEGNet, 5-seed ensemble", "improve_ensemble", None, "eegnet_ens5", "hybrid_ens5", None),
    ("Hybrid, 5-seed ensemble - reference for ensemble rows", "improve_ensemble", None, "hybrid_ens5", "hybrid",
     None),
    ("Hybrid, 5-seed ensemble + inner-validation threshold", "improve_ensemble", None, "hybrid_ens5_valthr",
     "hybrid_ens5", None),
    ("EEGNet, 8-s windows, 5-seed ensemble", "improve_win8", None, "win8_eegnet_ens5", "hybrid_ens5", None),
    ("Hybrid, 8-s windows, 5-seed ensemble", "improve_win8", None, "win8_hybrid_ens5", "hybrid_ens5", None),
    ("Hybrid, one-hot microstate labels, 5-seed ensemble", "improve_onehot", None, "onehot_hybrid_ens5",
     "hybrid_ens5", None),
    ("Hybrid, abs. correlation + 24 window features (MLP), 5-seed ensemble", "improve_feats", None, "feats_hybrid_ens5",
     "hybrid_ens5", None),
    ("EEGNet, nested-CV regularisation, 5-seed ensemble", "improve_reg", None, "reg_eegnet_ens5", "hybrid_ens5", None),
    ("Hybrid, nested-CV regularisation, 5-seed ensemble", "improve_reg", None, "reg_hybrid_ens5", "hybrid_ens5", None),
]

READING = {
    "improve_fusion": "Weights fixed in advance. Highest balanced accuracy on both devices (0.880 CPU, 0.875 MPS), "
                      "but corrected p = 0.22-0.31 vs the hybrid; AUC barely changes, so the gain is in where "
                      "subjects fall relative to 0.5 (specificity up, sensitivity kept).",
    "improve_threshold": "No gain: with 8 validation subjects per fold the rule kept 0.5 in 8/15 (EEGNet) and "
                         "11/15 (hybrid) folds. Balanced accuracy changed in few folds (EEGNet 1 better / 3 worse, hybrid 2 better / "
                         "1 worse) and the means fell slightly (-0.007, p = 0.82; -0.010, p = 0.85).",
    "improve_ensemble": "Averaging 5 seeds raises the hybrid by +0.027 (n.s.) and reduces seed noise; the hybrid "
                        "ensemble is +0.031 over the EEGNet ensemble in balanced accuracy (p = 0.58); AUC difference -0.008 "
                        "(p = 0.73).",
    "improve_win8": "8-s windows help EEGNet slightly (+0.017 ensemble, p = 0.42; +0.018 single-seed mean) and not the "
                    "hybrid; no difference is significant.",
    "improve_onehot": "Highest of the three microstate-input variants (0.841), +0.010 over the |corr| hybrid ensemble "
                      "(p = 0.87); within seed noise.",
    "improve_feats": "Adding window-level features via an MLP did not help (-0.023, p = 0.53).",
    "improve_reg": "Chosen per outer fold by inner 3-fold CV on training subjects only (mean inner-test AUC, grid "
                   "dropout {0.5, 0.25} x weight decay {1e-3, 1e-4}); seed 0's choices were reused for seeds 1-4, so "
                   "the ensemble does not capture selection noise. Channel dropout was not run. The default was kept "
                   "in 6/15 (EEGNet) and 7/15 (hybrid) folds, and mean inner AUC was nearly flat across the grid "
                   "(0.856-0.859 EEGNet, 0.861-0.863 hybrid). Against the matching reference ensemble: hybrid 0.851, "
                   "+0.019 (p = 0.68; AUC +0.011, p = 0.34; 2 better / 12 tied / 1 worse); EEGNet 0.829, +0.029 "
                   "(p = 0.29; AUC +0.002, p = 0.85; 5 / 10 / 0). Fold differences come only from folds whose setting "
                   "changed, and single-seed means barely move (hybrid +0.004, EEGNet +0.001), so this is not "
                   "evidence that regularisation helps. Hybrid vs EEGNet with these settings: +0.021 (p = 0.68), AUC "
                   "+0.002 (p = 0.94).",
}

READING_3CLASS = (
    "Settings were fixed in advance (Task 05 defaults) instead of the task's 'best setting', because picking the best "
    "table row would select on test folds. All models are above chance (0.333) and within noise of each other: hybrid "
    "ensemble 0.569 vs EEGNet ensemble 0.572 (-0.002, p = 0.97), so microstate input adds nothing measurable here. "
    "FTD is the weak class: recall 0.232 (EEGNet ensemble), 0.290 (hybrid ensemble), 0.391 (logistic regression), and "
    "both network ensembles label FTD subjects as AD more often than as FTD. Leaving sub-086 out of the evaluation "
    "only moves balanced accuracy by at most 0.007.\n\n"
    "Removing sub-086 from training, map fitting and test as well (same outer folds, so identical test subjects) changes "
    "balanced accuracy by +0.037 for logistic regression (p = 0.19; Wilcoxon 0.0098, not corrected for the 12 tests in "
    "this comparison), -0.008 for random forest (p = 0.87), +0.006 for the EEGNet ensemble (p = 0.90) and +0.013 for the "
    "hybrid ensemble (p = 0.75). None is significant on the corrected test. Among the 4 models above, logistic regression "
    "moves from lowest to highest, so their order depends on one subject and should not be read as a ranking. Hybrid "
    "vs EEGNet ensemble stays null (+0.008, p = 0.90). On the same subjects, FTD recall rises for both network ensembles "
    "(EEGNet 0.212 → 0.348, hybrid 0.288 → 0.424) but not for the baselines, and HC recall falls for both ensembles, so "
    "this is partly a trade between classes. There is no control run, so this cannot all be attributed to sub-086: "
    "removing any training subject also changes the early-stopping split and the batches.")


READING_CONFIRMATION = (
    "None of the 3 primary comparisons is significant on the corrected test: fusion vs EEGNet ensemble +0.053 (p = 0.32), "
    "hybrid vs EEGNet ensemble -0.025 (p = 0.59), fusion vs hybrid ensemble +0.078 (p = 0.12). None of the 6 secondary "
    "AUC and F1 tests is significant either. Fusion has the highest mean balanced accuracy (0.869 ± 0.083), but this run "
    "does not show that it is better than either network ensemble. The hybrid does not beat EEGNet: its earlier +0.031 "
    "(p = 0.58, repeats 0-2) became -0.025 here, and it has the lowest mean balanced accuracy of the 5 rows. Fusion vs "
    "logistic regression was not preregistered, so it has no test: balanced accuracy 0.869 vs 0.831, pooled AUC 0.906 vs "
    "0.904. From repeats 0-2 to 3-5, balanced accuracy moved +0.006 (fusion), -0.040 (hybrid), +0.016 (EEGNet), +0.014 "
    "(logistic regression) and +0.012 (random forest). The 65 subjects are the same as in all earlier comparisons, so "
    "this is not an independent test set.")


def md_table(path, heading):
    """The first markdown table after a heading of a summary file, unchanged."""
    lines = open(path).read().split("\n")
    i = next(k for k, ln in enumerate(lines) if ln.startswith(heading))
    j = next(k for k in range(i, len(lines)) if lines[k].startswith("|"))
    k = next(n for n in range(j, len(lines)) if not lines[n].startswith("|"))
    return lines[j:k]


def main():
    C = os.path.join(R, "confirmation", "summary.md")
    L = ["# Task 06: improvements (AD vs HC, ds004504)",
         "", "Research use only: this classifies AD vs healthy controls; it is not a diagnostic test.", "",
         "## Confirmation run: headline results (new splits, preregistered)", "",
         "Models, settings and analysis were fixed in `results/confirmation/PREREGISTERED.md` before the run: repeat seeds "
         "3, 4 and 5 (5 folds each), which no earlier result used; Task 05 defaults; MPS; 5 network seeds; threshold 0.5. "
         "Details in `results/confirmation/summary.md`.", ""]
    L += md_table(C, "## Results")
    L += ["", "Sensitivity and specificity (threshold 0.5, AD = positive):", ""]
    L += md_table(C, "## Sensitivity")
    L += ["", "Preregistered comparisons (corrected t-test, unadjusted; balanced accuracy = primary):", ""]
    L += md_table(C, "## Preregistered comparisons")
    L += ["", READING_CONFIRMATION, "",
         "## Exploratory comparisons (5-fold subject-wise CV x 3 repeats, same splits as Task 05)", "",
         "Every setting was fixed in advance or chosen on training-fold subjects only. **No row was selected "
         "because it scored best on the test folds, and none should be read as 'the improved model'**: "
         "with this many variants compared on the same 65 subjects, the best row is expected to look better by "
         "chance. Differences are paired over the 15 outer folds; p = Nadeau-Bengio corrected resampled t-test "
         "(test/train 13/52), which accounts for overlapping training sets across repeats.", "",
         "Comparator: single-seed rows are compared with the single-seed hybrid of the same run and device; "
         "5-seed ensemble rows with the 5-seed hybrid ensemble (MPS). Task 05 hybrid (CPU, 1 seed) = 0.813 "
         "balanced accuracy.", "",
         "| Change | Balanced accuracy (mean ± SD, 15 folds) | AUC (mean ± SD) | vs comparator: Δ bal. acc. "
         "(corrected p) | Δ AUC (corrected p) |", "|---|---|---|---|---|"]
    for label, exp, src, m, ref, _ in ROWS:
        f = load(exp, src)
        g = f[f.model == m]
        assert len(g) == 15, (exp, src, m, len(g))
        if ref is None:
            cmp_b = cmp_a = "reference"
        else:
            b, a = paired(f, m, ref, "balanced_accuracy"), paired(f, m, ref, "auc")
            cmp_b = f"{b['diff_mean']:+.3f} ({b['corrected_p']:.2f}) vs {REF_LABEL[ref]}"
            cmp_a = "unchanged (same scores)" if m.endswith("_valthr") else f"{a['diff_mean']:+.3f} ({a['corrected_p']:.2f})"
        L.append(f"| {label} | {g.balanced_accuracy.mean():.3f} ± {g.balanced_accuracy.std():.3f} | "
                 f"{g.auc.mean():.3f} ± {g.auc.std():.3f} | {cmp_b} | {cmp_a} |")
    L += ["", "## What each experiment tells us", ""]
    for exp, txt in READING.items():
        L.append(f"- **{exp.replace('improve_', '')}** (`results/{exp}/summary.md`): {txt}")
    L += ["- **seed noise**: single-seed balanced accuracy varies by SD 0.010 (EEGNet) to 0.020 (hybrid) across "
          "5 seeds on MPS, and the single task-05 CPU EEGNet run (0.852) lies above all 5 MPS seeds "
          "(see `results/improve_mps_rerun/device_check.md`). Single-run differences of a few points are not "
          "evidence either way.",
          "- **not run**: channel-dropout augmentation (no such option exists; left out of the reduced grid).", "",
          "## Secondary task: AD vs FTD vs HC (88 subjects, 87 without sub-086, chance = 0.333)", "",
          "Separate from the table above: these splits stratify over 3 groups, so a difference against the AD vs HC "
          "hybrid would not be valid. `eegnet`, `hybrid` = seed offset 0; `*_ens5` = 5-seed ensemble. Details in "
          "`results/improve_3class/summary.md` and `results/improve_3class_no086/summary.md`.", ""]
    S = os.path.join(R, "improve_3class", "summary.md")
    L += md_table(S, "## Results")
    L += ["", "With sub-086 removed from the evaluation only:", ""]
    L += md_table(S, "## Without sub-086")
    N = os.path.join(R, "improve_3class_no086", "summary.md")
    L += ["", "With sub-086 removed from training, early stopping, map fitting and test (87 subjects, same outer folds):", ""]
    L += md_table(N, "## Results")
    L += ["", "Effect of that removal on identical test subjects (this run minus the full-cohort run scored without sub-086):", ""]
    L += md_table(N, "## Effect of removing")
    L += ["", READING_3CLASS, "",
          f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `experiments/make_improvements.py`."]
    with open(os.path.join(R, "improvements.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
