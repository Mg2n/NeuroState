"""Task 06 secondary task: AD vs FTD vs HC, 5-fold subject-wise CV x 3 repeats, settings fixed in advance.

Reports balanced accuracy, macro-F1 and macro one-vs-rest AUC (mean +/- SD over folds), single seeds and the seed
ensemble (mean probability vector per subject), per-class recall and pooled confusion matrices, a paired hybrid vs
EEGNet comparison, and the same metrics with sub-086 (FTD, about 4x median amplitude) left out of the evaluation.
Chance level for balanced accuracy is 1/3. Splits are not those of the AD vs HC runs: they stratify 88 subjects
over 3 groups.

  .venv/bin/python improve_3class.py --runs ../results/improve_3class_seed{0..4}

With runs that used --exclude sub-086 (same outer folds), --with-runs adds a paired comparison on identical test subjects:
those runs against the full-cohort runs scored without sub-086, which isolates the effect of sub-086 on training.

  .venv/bin/python improve_3class.py --runs ../results/improve_3class_no086_seed{0..4} \\
      --with-runs ../results/improve_3class_seed{0..4} --out ../results/improve_3class_no086
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.metrics import confusion_matrix, recall_score

from run_experiment import env_info, metrics
from summarize_main import corrected_t

NAMES = {2: "AD", 1: "FTD", 0: "HC"}  # class index = K-1-position in --groups A F C
PROB = ["prob_0", "prob_1", "prob_2"]
OUTLIER = "sub-086"


def fold_table(oof):
    rows = []
    for (r, f, m), g in oof.groupby(["repeat", "fold", "model"]):
        rows.append({"repeat": r, "fold": f, "model": m, **metrics(g.label.values, g[PROB].values)})
    return pd.DataFrame(rows)


def ens_probs(runs):
    key = ["repeat", "fold", "model", "subject", "label"]
    allp = pd.concat([pd.read_csv(os.path.join(r, "oof_predictions.csv")).assign(seed_run=i)
                      for i, r in enumerate(runs)])
    allp = allp[allp.model.isin(["eegnet", "hybrid"])]
    assert (allp.groupby(key).seed_run.nunique() == len(runs)).all(), "missing seeds"
    g = allp.groupby(key)[PROB].mean().reset_index()
    g["model"] = g.model + f"_ens{len(runs)}"
    return g


def paired(folds, a, b, metric, n_train, n_test):
    x = folds[folds.model == a].set_index(["repeat", "fold"]).sort_index()[metric]
    y = folds[folds.model == b].set_index(["repeat", "fold"]).sort_index()[metric]
    d = (x - y).values
    nz = d[np.abs(d) > 1e-12]
    return {"diff_mean": float(d.mean()), "diff_sd": float(d.std(ddof=1)), "better": int((d > 1e-12).sum()),
            "tied": int((np.abs(d) <= 1e-12).sum()), "worse": int((d < -1e-12).sum()),
            "wilcoxon_p": float(wilcoxon(nz).pvalue) if len(nz) else float("nan"),
            "corrected_p": corrected_t(d, n_train, n_test)[1]}


def model_table(folds, models):
    T = ["| Model | Balanced acc. (mean ± SD) | Macro-F1 | Macro AUC (one-vs-rest) |", "|---|---|---|---|"]
    for m in models:
        f = folds[folds.model == m]
        T.append(f"| {m} | {f.balanced_accuracy.mean():.3f} ± {f.balanced_accuracy.std():.3f} | "
                 f"{f.f1.mean():.3f} ± {f.f1.std():.3f} | {f.auc.mean():.3f} ± {f.auc.std():.3f} |")
    return T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default="../results/improve_3class")
    ap.add_argument("--with-runs", nargs="+", help="full-cohort runs to compare with runs that excluded sub-086")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    runs = args.runs
    n_ens = len(runs)

    # splits identical across seeds? baselines depend only on the outer split and fold seed
    base = pd.read_csv(os.path.join(runs[0], "oof_predictions.csv"))
    ref = base[base.model == "baseline_logreg"].set_index(["repeat", "fold", "subject"])[PROB].sort_index()
    for r in runs[1:]:
        o = pd.read_csv(os.path.join(r, "oof_predictions.csv"))
        o = o[o.model == "baseline_logreg"].set_index(["repeat", "fold", "subject"])[PROB].sort_index()
        assert o.index.equals(ref.index) and np.allclose(o.values, ref.values), f"{r}: splits differ"

    oof = pd.concat([base, ens_probs(runs)], ignore_index=True)
    folds = fold_table(oof)
    n_sub = base.subject.nunique()
    n_folds = base[["repeat", "fold"]].drop_duplicates().groupby("repeat").size().iloc[0]
    n_test, n_train = n_sub / n_folds, n_sub - n_sub / n_folds
    e, h = f"eegnet_ens{n_ens}", f"hybrid_ens{n_ens}"
    models = ["baseline_logreg", "baseline_rf", "eegnet", "hybrid", e, h]

    L = ["# Secondary task: AD vs FTD vs HC (5-fold subject-wise CV x 3 repeats)", "",
         "Research use only: this classifies groups in a public dataset; it is not a diagnostic test.", "",
         f"Subjects: {n_sub}" + (f" ({OUTLIER} excluded)" if OUTLIER not in set(base.subject) else "") + ". Settings fixed in advance (task 05 defaults, not chosen from any test fold). Maps and "
         "early-stopping subjects come from each training fold only. Chance balanced accuracy = 0.333. `eegnet`, "
         f"`hybrid` = network seed offset 0; `*_ens{n_ens}` = mean probability vector over {n_ens} seeds. Splits "
         "differ from the AD vs HC runs (they stratify over 3 groups), so numbers are not paired with those runs.",
         "", "## Results", ""] + model_table(folds, models)

    # single seeds
    L += ["", "## Single seeds (fold mean)", "", "| Run | EEGNet bal. acc. | Hybrid bal. acc. | Hybrid − EEGNet |",
          "|---|---|---|---|"]
    sp = []
    for r in runs:
        f = pd.read_csv(os.path.join(r, "fold_metrics.csv"))
        a, b = f[f.model == "eegnet"].balanced_accuracy.mean(), f[f.model == "hybrid"].balanced_accuracy.mean()
        sp.append((a, b))
        L.append(f"| {os.path.basename(r)} | {a:.3f} | {b:.3f} | {b - a:+.3f} |")
    sp = np.array(sp)
    L.append(f"| **mean ± SD** | {sp[:, 0].mean():.3f} ± {sp[:, 0].std(ddof=1):.3f} | "
             f"{sp[:, 1].mean():.3f} ± {sp[:, 1].std(ddof=1):.3f} | "
             f"{(sp[:, 1] - sp[:, 0]).mean():+.3f} ± {(sp[:, 1] - sp[:, 0]).std(ddof=1):.3f} |")

    # paired
    L += ["", "## Paired comparisons over the folds", "",
          "| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |",
          "|---|---|---|---|---|---|---|"]
    stats = {}
    for a, b in [(h, e), (h, "baseline_logreg"), (e, "baseline_logreg")]:
        for metric in ("balanced_accuracy", "f1", "auc"):
            s = paired(folds, a, b, metric, n_train, n_test)
            stats[f"{a}_vs_{b}_{metric}"] = s
            L.append(f"| {a} | {b} | {metric} | {s['diff_mean']:+.3f} ({s['diff_sd']:.3f}) | {s['better']} / "
                     f"{s['tied']} / {s['worse']} | {s['wilcoxon_p']:.3g} | {s['corrected_p']:.3g} |")
    L += ["", f"Corrected t-test: Nadeau & Bengio (2003), test/train ratio {n_test:.1f}/{n_train:.1f}.", ""]

    # per class
    L += ["## Per-class recall and confusion (all repeats pooled)", "",
          "| Model | AD recall | FTD recall | HC recall |", "|---|---|---|---|"]
    conf = {}
    for m in ["baseline_logreg", e, h]:
        g = oof[oof.model == m]
        pred = g[PROB].values.argmax(1)
        rec = recall_score(g.label, pred, labels=[2, 1, 0], average=None)
        L.append(f"| {m} | {rec[0]:.3f} | {rec[1]:.3f} | {rec[2]:.3f} |")
        conf[m] = confusion_matrix(g.label, pred, labels=[2, 1, 0])
    for m, c in conf.items():
        L += ["", f"`{m}`, rows = true, columns = predicted (counts over repeats):", "",
              "| | AD | FTD | HC |", "|---|---|---|---|"]
        for name, row in zip(("AD", "FTD", "HC"), c):
            L.append(f"| {name} | {row[0]} | {row[1]} | {row[2]} |")

    # outlier
    no = oof[oof.subject != OUTLIER]
    if OUTLIER in set(oof.subject):
        L += ["", f"## Without {OUTLIER} in the evaluation", "",
              f"`{OUTLIER}` (FTD, about 4x median amplitude) is removed from the test folds here but was still used for "
              "training when it was in a training fold, and in map fitting, so this is an evaluation-only sensitivity "
              "check, not a full exclusion.", ""] + model_table(fold_table(no), models)
        L += ["", f"`{OUTLIER}` prediction by model (fraction of repeats classified FTD): "
              + ", ".join(f"{m} {(oof[(oof.model == m) & (oof.subject == OUTLIER)][PROB].values.argmax(1) == 1).mean():.2f}"
                          for m in models)]

    if args.with_runs:
        assert OUTLIER not in set(oof.subject), f"--with-runs needs runs that excluded {OUTLIER}"
        wbase = pd.read_csv(os.path.join(args.with_runs[0], "oof_predictions.csv"))
        wall = pd.concat([wbase, ens_probs(args.with_runs)], ignore_index=True)
        wall = wall[wall.subject != OUTLIER]
        key = ["repeat", "fold", "subject"]
        a = oof[oof.model == "baseline_logreg"][key].sort_values(key).values
        b = wall[wall.model == "baseline_logreg"][key].sort_values(key).values
        assert (a == b).all(), "test subjects differ"
        both = pd.concat([folds, fold_table(wall.assign(model="with086_" + wall.model))], ignore_index=True)
        L += ["", f"## Effect of removing {OUTLIER} from training", "",
              f"`{OUTLIER}` (FTD, about 4x median amplitude) was removed from training, early stopping, map fitting and "
              "test. The outer folds are those of the full cohort, so test subjects are identical in both columns of "
              f"this comparison: `with086_*` are the full-cohort runs scored without {OUTLIER}. Early-stopping subjects "
              f"differ in folds where {OUTLIER} was a training subject, because the split is drawn from one fewer subject.",
              "", "| Model | Metric | This run − with086 (SD) | better / tied / worse | Wilcoxon p | Corrected t-test p |",
              "|---|---|---|---|---|---|"]
        for m in ["baseline_logreg", "baseline_rf", e, h]:
            for metric in ("balanced_accuracy", "f1", "auc"):
                s = paired(both, m, "with086_" + m, metric, n_train, n_test)
                stats[f"{m}_vs_with086_{metric}"] = s
                L.append(f"| {m} | {metric} | {s['diff_mean']:+.3f} ({s['diff_sd']:.3f}) | {s['better']} / {s['tied']} / "
                         f"{s['worse']} | {s['wilcoxon_p']:.3g} | {s['corrected_p']:.3g} |")
        L += ["", f"Per-class recall on the same test subjects (all repeats pooled), with {OUTLIER} in training → without:",
              "", "| Model | AD recall | FTD recall | HC recall | Predictions changed |", "|---|---|---|---|---|"]
        for m in ["baseline_logreg", "baseline_rf", e, h]:
            x, y = wall[wall.model == m].sort_values(key), oof[oof.model == m].sort_values(key)
            px, py = x[PROB].values.argmax(1), y[PROB].values.argmax(1)
            rx, ry = (recall_score(x.label, p, labels=[2, 1, 0], average=None) for p in (px, py))
            L.append(f"| {m} | " + " | ".join(f"{i:.3f} → {j:.3f}" for i, j in zip(rx, ry))
                     + f" | {(px != py).sum()} of {len(px)} |")
        held = wbase[wbase.subject == OUTLIER][["repeat", "fold"]].drop_duplicates()
        same = oof.merge(held).merge(wall.merge(held), on=key + ["model"], suffixes=("", "_w"))
        gap = np.abs(same[PROB].values - same[[c + "_w" for c in PROB]].values).max()
        L += ["", f"In the {len(held)} folds where {OUTLIER} was a test subject its removal leaves training unchanged: "
              f"max probability difference {gap:.3g} over all models. These folds count as ties above, so at most "
              f"{n_folds * base.repeat.nunique() - len(held)} folds can differ. There is no control run: removing any "
              "training subject also changes the early-stopping split and the batches, so these differences cannot all be "
              f"attributed to {OUTLIER}'s signal."]

    folds.to_csv(os.path.join(args.out, "fold_metrics.csv"), index=False)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump({"source_runs": runs, "with_runs": args.with_runs, "stats": stats, "n_subjects": n_sub,
                   "class_index": {str(k): v for k, v in NAMES.items()},
                   "created": time.strftime("%Y-%m-%d %H:%M"), "_environment": env_info()}, fh, indent=2)
    with open(os.path.join(args.out, "summary.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
