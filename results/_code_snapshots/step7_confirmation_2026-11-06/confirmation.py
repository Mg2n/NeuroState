"""Task 06 Phase 4: confirmation run on new splits, analysis fixed in advance (results/confirmation/PREREGISTERED.md).

Fixed models: fusion (0.5 * EEGNet 5-seed ensemble + 0.5 * logistic regression), hybrid 5-seed ensemble, EEGNet 5-seed
ensemble; baselines for reference. Threshold 0.5, nothing tuned. Earlier splits are listed as context only.

  .venv/bin/python confirmation.py --runs ../results/confirmation/seed{0..4} \\
      --earlier-runs ../results/improve_mps_rerun ../results/improve_seed{1..4}
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score

from improve_analysis import N_TEST, N_TRAIN, ens_probs, fold_metrics, paired, same_splits
from run_experiment import env_info
from summarize_main import BOOT_SEED, N_BOOT, boot_auc

REPEATS = [3, 4, 5]
COLS = ["repeat", "fold", "model", "subject", "label", "prob", "thr"]


def build(runs):
    """Baselines of the first run, seed ensembles, and fusion, as subject probabilities with threshold 0.5."""
    same_splits(runs, [])
    oof = pd.read_csv(os.path.join(runs[0], "oof_predictions.csv"))
    n = len(runs)
    oof = pd.concat([oof[oof.model.isin(["baseline_logreg", "baseline_rf"])],
                     ens_probs(runs, "oof_predictions.csv")], ignore_index=True).assign(thr=0.5)
    key = ["repeat", "fold", "subject", "label"]
    fus = oof[oof.model == f"eegnet_ens{n}"].merge(oof[oof.model == "baseline_logreg"], on=key, suffixes=("", "_lr"),
                                                   validate="one_to_one")
    assert len(fus) == (oof.model == f"eegnet_ens{n}").sum(), "fusion lost subjects"
    fus["prob"] = 0.5 * fus.prob + 0.5 * fus.prob_lr
    fus["model"] = f"fusion_eegnet_ens{n}_logreg"
    return pd.concat([oof, fus], ignore_index=True)[COLS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--earlier-runs", nargs="+", required=True)
    ap.add_argument("--out", default="../results/confirmation")
    args = ap.parse_args()
    n = len(args.runs)
    F, H, E = f"fusion_eegnet_ens{n}_logreg", f"hybrid_ens{n}", f"eegnet_ens{n}"
    models = [F, H, E, "baseline_logreg", "baseline_rf"]

    cfgs = [json.load(open(os.path.join(r, "results.json"))) for r in args.runs]
    for k, c in enumerate(cfgs):
        c = c["_config"]
        assert c["seed_offset"] == 1000 * k and c["first_repeat"] == REPEATS[0] and c["repeats"] == len(REPEATS)
        assert (c["dropout"], c["wd"], c["win_sec"], c["ms_input"], c["reg_grid"]) == (0.5, 1e-3, 4.0, "corr", False)
        assert c["exclude"] == [] and c["groups"] == ["A", "C"]

    oof = build(args.runs)
    assert sorted(oof.repeat.unique()) == REPEATS, "unexpected repeats"
    folds = fold_metrics(oof)
    n_sub, n_ad = oof.subject.nunique(), oof.drop_duplicates("subject").label.sum()
    point, boots = boot_auc(oof, models, np.random.default_rng(BOOT_SEED))

    L = ["# Confirmation run: AD vs HC on new splits", "",
         "Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.", "",
         f"Models, settings, splits and this analysis were fixed in `PREREGISTERED.md` before the run. {n_sub} subjects "
         f"({n_ad} AD, {n_sub - n_ad} HC), repeat seeds {REPEATS}, {len(folds) // len(models)} test folds, {n} network "
         "seeds, threshold 0.5, nothing tuned. Same subjects as all earlier comparisons, on new splits: not an "
         "independent test set.", "",
         "## Results", "",
         f"Mean ± SD over folds. Pooled AUC = per repeat, then averaged; 95% CI: subject bootstrap ({N_BOOT} resamples, "
         f"stratified, seed {BOOT_SEED}).", "",
         "| Model | Balanced acc. | AUC | F1 | Pooled AUC [95% CI] |", "|---|---|---|---|---|"]
    rows = {}
    for m in models:
        f = folds[folds.model == m]
        lo, hi = np.percentile(boots[m], [2.5, 97.5])
        rows[m] = {k: {"mean": float(f[k].mean()), "sd": float(f[k].std())}
                   for k in ("balanced_accuracy", "auc", "f1", "sensitivity", "specificity")}
        rows[m]["pooled_auc"] = {"point": float(point[m]), "ci95": [float(lo), float(hi)]}
        L.append(f"| {m} | {f.balanced_accuracy.mean():.3f} ± {f.balanced_accuracy.std():.3f} | "
                 f"{f.auc.mean():.3f} ± {f.auc.std():.3f} | {f.f1.mean():.3f} ± {f.f1.std():.3f} | "
                 f"{point[m]:.3f} [{lo:.3f}, {hi:.3f}] |")

    L += ["", "## Sensitivity and specificity", "", "Threshold 0.5, AD = positive.", "",
          "| Model | Sensitivity (fold mean ± SD) | Specificity (fold mean ± SD) | Sensitivity (pooled) | Specificity (pooled) |",
          "|---|---|---|---|---|"]
    for m in models:
        f, g = folds[folds.model == m], oof[oof.model == m]
        pred = (g.prob >= 0.5).astype(int)
        se, sp = float((pred[g.label == 1] == 1).mean()), float((pred[g.label == 0] == 0).mean())
        rows[m]["pooled_sensitivity"], rows[m]["pooled_specificity"] = se, sp
        L.append(f"| {m} | {f.sensitivity.mean():.3f} ± {f.sensitivity.std():.3f} | "
                 f"{f.specificity.mean():.3f} ± {f.specificity.std():.3f} | {se:.3f} | {sp:.3f} |")

    L += ["", "## Preregistered comparisons", "",
          f"Paired over the folds. p = Nadeau-Bengio corrected resampled t-test (test/train {N_TEST}/{N_TRAIN}, two-sided), "
          "unadjusted. Balanced accuracy = 3 primary tests; AUC and F1 = 6 secondary tests.", "",
          "| Comparison | Metric | Diff. mean (SD) | better / tied / worse | t | p |", "|---|---|---|---|---|---|"]
    stats = {}
    for a, b in [(F, E), (H, E), (F, H)]:
        for metric in ("balanced_accuracy", "auc", "f1"):
            s = paired(folds, a, b, metric)
            stats[f"{a}_vs_{b}_{metric}"] = s
            L.append(f"| {a} vs {b} | {metric} | {s['diff_mean']:+.3f} ({s['diff_sd']:.3f}) | {s['better']} / {s['tied']} / "
                     f"{s['worse']} | {s['corrected_t']:.2f} | {s['corrected_p']:.3g} |")
    prim = [k for k, s in stats.items() if k.endswith("balanced_accuracy") and s["corrected_p"] < 0.05]
    sec = [k for k, s in stats.items() if not k.endswith("balanced_accuracy") and s["corrected_p"] < 0.05]
    L += ["", f"Significant at p < 0.05: primary tests {prim or 'none'}; secondary tests {sec or 'none'}."]

    L += ["", "## Pooled balanced accuracy per repeat", "",
          "| Model | " + " | ".join(f"repeat {r}" for r in REPEATS) + " |", "|---|" + "---|" * len(REPEATS)]
    for m in models:
        g = oof[oof.model == m]
        L.append(f"| {m} | " + " | ".join(f"{balanced_accuracy_score(x.label, (x.prob >= 0.5).astype(int)):.3f}"
                                         for _, x in g.groupby("repeat")) + " |")

    L += ["", "## Single network seeds (fold mean balanced accuracy)", "", "| Run | EEGNet | Hybrid |", "|---|---|---|"]
    sp = []
    for r in args.runs:
        f = pd.read_csv(os.path.join(r, "fold_metrics.csv"))
        a, b = (f[f.model == x].balanced_accuracy.mean() for x in ("eegnet", "hybrid"))
        sp.append((a, b))
        L.append(f"| {os.path.basename(r)} | {a:.3f} | {b:.3f} |")
    sp = np.array(sp)
    L.append(f"| **mean ± SD** | {sp[:, 0].mean():.3f} ± {sp[:, 0].std(ddof=1):.3f} | "
             f"{sp[:, 1].mean():.3f} ± {sp[:, 1].std(ddof=1):.3f} |")

    # context only: the same rows on the splits used for all earlier comparisons
    n_e = len(args.earlier_runs)
    ef = fold_metrics(build(args.earlier_runs))
    assert n_e == n, "earlier runs need the same number of seeds"
    L += ["", "## Context: same rows on the earlier splits (not headline results)", "",
          "Repeats 0-2 are the splits on which the 17 variants were compared. The 3 models were fixed with their earlier "
          "scores known. The 5-seed fusion on those splits was first computed for this table.", "",
          "| Model | Bal. acc., repeats 0-2 | Bal. acc., repeats 3-5 | Change | AUC, repeats 0-2 | AUC, repeats 3-5 | Change |",
          "|---|---|---|---|---|---|---|"]
    context = {}
    for m in models:
        o, c = ef[ef.model == m], folds[folds.model == m]
        d1, d2 = c.balanced_accuracy.mean() - o.balanced_accuracy.mean(), c.auc.mean() - o.auc.mean()
        context[m] = {"balanced_accuracy_earlier": float(o.balanced_accuracy.mean()), "auc_earlier": float(o.auc.mean())}
        L.append(f"| {m} | {o.balanced_accuracy.mean():.3f} ± {o.balanced_accuracy.std():.3f} | "
                 f"{c.balanced_accuracy.mean():.3f} ± {c.balanced_accuracy.std():.3f} | {d1:+.3f} | "
                 f"{o.auc.mean():.3f} | {c.auc.mean():.3f} | {d2:+.3f} |")

    env = cfgs[0].get("_environment", {})
    mins = [c["_config"]["minutes"] for c in cfgs]
    L += ["", "## Settings and environment", "", "| Setting | Value |", "|---|---|"]
    for k in ("folds", "repeats", "first_repeat", "epochs", "patience", "crops", "batch", "lr", "wd", "dropout", "win_sec",
              "ms_input", "device"):
        L.append(f"| {k} | {cfgs[0]['_config'][k]} |")
    L += ["| seed offsets | " + ", ".join(str(c["_config"]["seed_offset"]) for c in cfgs) + " |",
          f"| fold seeds | {cfgs[0]['_seeds']['fold_seeds']} |",
          f"| bootstrap | {N_BOOT} resamples, seed {BOOT_SEED} |",
          f"| runtime | {sum(mins):.1f} min total; per seed " + ", ".join(f"{m:.1f}" for m in mins) + " |",
          f"| environment | Python {env.get('python')}, {env.get('platform')} |",
          "| libraries | " + ", ".join(f"{k} {v}" for k, v in env.get("libraries", {}).items()) + " |", ""]

    os.makedirs(args.out, exist_ok=True)
    oof.to_csv(os.path.join(args.out, "oof_predictions.csv"), index=False)
    folds.to_csv(os.path.join(args.out, "fold_metrics.csv"), index=False)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump({"source_runs": args.runs, "earlier_runs": args.earlier_runs, "models": rows, "comparisons": stats,
                   "context": context, "n_subjects": int(n_sub), "repeats": REPEATS,
                   "seeds": cfgs[0]["_seeds"], "config": cfgs[0]["_config"], "minutes_per_seed": mins,
                   "created": time.strftime("%Y-%m-%d %H:%M"), "_environment": env_info()}, fh, indent=2, default=float)
    with open(os.path.join(args.out, "summary.md"), "w") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
