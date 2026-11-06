"""Task 09 analysis, fixed in results/followup_seqcnn/PREREGISTERED.md. Writes results/followup_seqcnn/summary.md.

Stops before any comparison if logistic regression does not reproduce the confirmation run.

  .venv/bin/python followup_analysis.py --main-runs ../results/followup_seqcnn/main_seed{0..4} \\
      --smooth-runs ../results/followup_seqcnn/smooth_seed{0..4} --corr-runs ../results/followup_seqcnn/corr_seed{0..4} \\
      --curve-run ../results/followup_seqcnn/curve --confirmation ../results/confirmation --out ../results/followup_seqcnn
"""
import argparse
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from improve_analysis import fold_metrics, paired
from run_experiment import env_info

SEQ, LOG, SEQS, LOGS, SEQC, EEG = "seqcnn_onehot", "logreg", "seqcnn_onehot_smoothed", "logreg_smoothed", "seqcnn_corr", "eegnet_ens5"
RF, RFS = "random_forest", "random_forest_smoothed"
NAMES = {SEQ: "seq-CNN one-hot, primary labels", LOG: "Logistic regression, primary labels",
         SEQS: "seq-CNN one-hot, smoothed labels", LOGS: "Logistic regression, smoothed labels",
         SEQC: "seq-CNN on absolute correlation", EEG: "EEGNet ensemble (reused)", RF: "Random forest, primary labels (reference)",
         RFS: "Random forest, smoothed labels (reference)"}
TESTS = [(SEQ, LOG, "balanced_accuracy", "PRIMARY"), (SEQ, LOG, "auc", "secondary"), (SEQ, LOG, "f1", "secondary"),
         (SEQS, LOGS, "balanced_accuracy", "secondary"), (SEQS, LOGS, "auc", "secondary"),
         (SEQS, SEQ, "balanced_accuracy", "secondary"), (LOGS, LOG, "balanced_accuracy", "secondary"),
         (SEQC, SEQ, "balanced_accuracy", "secondary"), (SEQC, LOG, "balanced_accuracy", "secondary"),
         (SEQ, EEG, "balanced_accuracy", "secondary"), (LOG, EEG, "balanced_accuracy", "secondary")]
KEY = ["repeat", "fold", "subject", "label"]
COLS = KEY + ["model", "prob", "thr"]


def read(runs):
    return [pd.read_csv(os.path.join(r, "oof_predictions.csv")) for r in runs]


def seq_ensemble(frames, name):
    a = pd.concat([f[f.model == "seqcnn"].assign(run=i) for i, f in enumerate(frames)])
    assert (a.groupby(KEY).run.nunique() == len(frames)).all(), f"{name}: missing seeds"
    return a.groupby(KEY).prob.mean().reset_index().assign(model=name, thr=0.5)[COLS]


def baseline(frames, model, name):
    ref = frames[0][frames[0].model == model].set_index(["repeat", "fold", "subject"]).prob.sort_index()
    for f in frames[1:]:
        g = f[f.model == model].set_index(["repeat", "fold", "subject"]).prob.sort_index()
        assert g.index.equals(ref.index) and np.allclose(g.values, ref.values), f"{name} differs across seeds"
    return frames[0][frames[0].model == model].assign(model=name, thr=0.5)[COLS]


def curve(run, sizes):
    p = pd.read_csv(os.path.join(run, "curve_predictions.csv"))
    k = ["repeat", "fold", "draw", "size", "subject", "label"]
    ens = p[p.model == "seqcnn"].groupby(k).prob.mean().reset_index().assign(model="seqcnn")
    pp = pd.concat([ens, p[p.model == "logreg"][k + ["prob"]].assign(model="logreg")], ignore_index=True)
    rows = []
    for size in sizes:
        for (r, f, d), g in pp[pp["size"] == size].groupby(["repeat", "fold", "draw"]):
            m = fold_metrics(g.assign(thr=0.5)[["repeat", "fold", "model", "label", "prob", "thr"]])
            rows.append(m.assign(draw=d, size=size))
    return pd.concat(rows, ignore_index=True)


def check_subsets(run, test_folds):
    """Nested inside each draw, and never containing a test subject."""
    s = pd.read_csv(os.path.join(run, "subsets.csv"))
    for (r, f, d), g in s.groupby(["repeat", "fold", "draw"]):
        sizes = sorted(g["size"].unique())
        for a, b in zip(sizes, sizes[1:]):
            assert set(g[g["size"] == a].subject) <= set(g[g["size"] == b].subject), "subsets not nested"
        assert not set(g.subject) & test_folds[(r, f)], "test subject in a training subset"
    return s


def main():
    ap = argparse.ArgumentParser()
    for a in ("--main-runs", "--smooth-runs", "--corr-runs"):
        ap.add_argument(a, nargs="+", required=True)
    ap.add_argument("--curve-run", required=True)
    ap.add_argument("--confirmation", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    main_f, smooth_f, corr_f = read(args.main_runs), read(args.smooth_runs), read(args.corr_runs)
    conf = pd.read_csv(os.path.join(args.confirmation, "seed0", "oof_predictions.csv"))
    conf = conf[conf.model == "baseline_logreg"].set_index(["repeat", "fold", "subject"]).prob.sort_index()
    log = baseline(main_f, "baseline_logreg", LOG)
    mine = log.set_index(["repeat", "fold", "subject"]).prob.sort_index()
    same = mine.index.equals(conf.index)
    gap = float(np.abs(mine.values - conf.values).max()) if same else float("nan")
    sanity = f"Logistic regression vs confirmation run: same test subjects {same}; largest probability difference {gap}."
    if not same or gap != 0:
        open(os.path.join(args.out, "summary.md"), "w").write(f"# SANITY CHECK FAILED\n\n{sanity}\n\nNo comparison was run.\n")
        sys.exit(sanity)

    e = pd.read_csv(os.path.join(args.confirmation, "oof_predictions.csv"))
    e = e[e.model == EEG].assign(thr=0.5)[COLS]
    oof = pd.concat([seq_ensemble(main_f, SEQ), log, baseline(main_f, "baseline_rf", RF), seq_ensemble(smooth_f, SEQS),
                     baseline(smooth_f, "baseline_logreg", LOGS), baseline(smooth_f, "baseline_rf", RFS),
                     seq_ensemble(corr_f, SEQC), e], ignore_index=True)
    folds = fold_metrics(oof)
    n_folds = len(folds) // oof.model.nunique()
    ba = lambda m: folds[folds.model == m].balanced_accuracy.mean()
    L = ["# Follow-up: microstate sequence CNN vs summary features", "",
         "Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.", "",
         f"Fixed in `PREREGISTERED.md` before the run. {oof.subject.nunique()} subjects, {n_folds} test folds (repeats "
         f"{sorted(oof.repeat.unique())}), threshold 0.5. Same subjects and splits as the confirmation run: not independent, and "
         "logistic regression and EEGNet were already known on them.", "", f"**Sanity check.** {sanity} Mean balanced accuracy "
         f"{ba(LOG):.3f}.", "", "## Results", "", "Mean ± SD over folds. Sensitivity and specificity: AD = positive.", "",
         "| Model | Balanced acc. | AUC | F1 | Sensitivity | Specificity | Sens. (pooled) | Spec. (pooled) |", "|---|---|---|---|---|---|---|---|"]
    rows = {}
    for m in (SEQ, LOG, SEQS, LOGS, SEQC, EEG, RF, RFS):
        f, g = folds[folds.model == m], oof[oof.model == m]
        pred = (g.prob >= 0.5).astype(int)
        se, sp = float((pred[g.label == 1] == 1).mean()), float((pred[g.label == 0] == 0).mean())
        cell = lambda k: f"{f[k].mean():.3f} ± {f[k].std():.3f}"
        rows[m] = {k: {"mean": float(f[k].mean()), "sd": float(f[k].std())} for k in ("balanced_accuracy", "auc", "f1", "sensitivity", "specificity")}
        rows[m].update(pooled_sensitivity=se, pooled_specificity=sp)
        L.append(f"| {NAMES[m]} | {cell('balanced_accuracy')} | {cell('auc')} | {cell('f1')} | {cell('sensitivity')} | "
                 f"{cell('specificity')} | {se:.3f} | {sp:.3f} |")

    L += ["", "## Preregistered tests", "", "Paired over the folds. Nadeau-Bengio corrected resampled t-test (test/train 13/52), two-sided, "
          f"unadjusted; {len(TESTS)} tests in total. A non-significant result does not show that the models are equal.", "",
          "| # | Role | Comparison | Metric | Diff. mean (SD) | better / tied / worse | t | p |", "|---|---|---|---|---|---|---|---|"]
    stats = []
    for i, (a, b, metric, role) in enumerate(TESTS, 1):
        s = paired(folds, a, b, metric)
        stats.append({"test": i, "role": role, "a": a, "b": b, "metric": metric, **s})
        L.append(f"| {i} | {role} | {NAMES[a]} vs {NAMES[b]} | {metric} | {s['diff_mean']:+.3f} ({s['diff_sd']:.3f}) | {s['better']} / {s['tied']} / "
                 f"{s['worse']} | {s['corrected_t']:.2f} | {s['corrected_p']:.3g} |")
    won = stats[0]["diff_mean"] > 0 and stats[0]["corrected_p"] < 0.05
    sig = [s["test"] for s in stats if s["corrected_p"] < 0.05]
    L += ["", f"Significant at p < 0.05: {sig or 'none'}. The seq-CNN wins on the primary test (positive difference and p < 0.05): {'yes' if won else 'no'}."]

    # learning curve: draws averaged within each fold, then mean +/- SD over folds; descriptive only
    cfg = json.load(open(os.path.join(args.curve_run, "results.json")))["_config"]
    sizes = cfg["sizes"]
    test_folds = {k: set(g.subject) for k, g in oof[oof.model == SEQ].groupby(["repeat", "fold"])}
    check_subsets(args.curve_run, test_folds)
    c = curve(args.curve_run, sizes)
    full = folds[folds.model.isin([SEQ, LOG])].assign(model=lambda d: d.model.map({SEQ: "seqcnn", LOG: "logreg"}), size="full", draw=0)
    allc = pd.concat([c, full], ignore_index=True)
    n_full = len(oof[oof.model == LOG].drop_duplicates("subject")) - round(len(oof[oof.model == LOG].drop_duplicates("subject")) / cfg["folds"])
    L += ["", "## Learning curve (descriptive, primary labels)", "", f"Metrics averaged over {cfg['draws']} draws within each fold, then mean ± SD over "
          f"folds. seq-CNN = {len(cfg['seed_offsets'])}-seed ensemble per draw. The full fold has one possible subset, so no draws. There are no tests, and the "
          f"curve cannot show what happens beyond {n_full} subjects.", ""]
    table, curve_out = [], {}
    for metric in ("balanced_accuracy", "auc"):
        L += [f"**{metric}**", "", "| Training size | seq-CNN | Logistic regression | Difference (seq-CNN − logreg) | SD across draws, seq-CNN | SD across draws, logreg |", "|---|---|---|---|---|---|"]
        for size in sizes + ["full"]:
            g = allc[allc["size"] == size]
            pf = g.groupby(["model", "repeat", "fold"])[metric].mean().unstack("model")
            sd = g.groupby(["model", "repeat", "fold"])[metric].std(ddof=1).groupby("model").mean() if size != "full" else None
            d = pf.seqcnn - pf.logreg
            lab = n_full if size == "full" else size
            L.append(f"| {lab}{' (full)' if size == 'full' else ''} | {pf.seqcnn.mean():.3f} ± {pf.seqcnn.std():.3f} | {pf.logreg.mean():.3f} ± {pf.logreg.std():.3f} | "
                     f"{d.mean():+.3f} ± {d.std():.3f} | {'-' if sd is None else f'{sd.seqcnn:.3f}'} | {'-' if sd is None else f'{sd.logreg:.3f}'} |")
            curve_out[f"{metric}_{lab}"] = {"seqcnn": float(pf.seqcnn.mean()), "seqcnn_sd": float(pf.seqcnn.std()), "logreg": float(pf.logreg.mean()),
                                            "logreg_sd": float(pf.logreg.std()), "diff": float(d.mean()), "diff_sd": float(d.std())}
            if metric == "balanced_accuracy":
                table.append((lab, pf.seqcnn.mean(), pf.seqcnn.std(), pf.logreg.mean(), pf.logreg.std()))
        L.append("")
    t = np.array(table, dtype=float)
    fig, ax = plt.subplots(figsize=(3.5, 2.5), layout="constrained")
    ax.errorbar(t[:, 0] - 0.4, t[:, 1], yerr=t[:, 2], color="#2a78d6", marker="o", ms=4, lw=1.4, capsize=2, label="seq-CNN (one-hot)")
    ax.errorbar(t[:, 0] + 0.4, t[:, 3], yerr=t[:, 4], color="#eb6834", marker="s", ms=4, lw=1.4, ls="--", capsize=2, label="Logistic regression")
    ax.set(xlabel="Training subjects", ylabel="Balanced accuracy (mean ± SD over folds)", xticks=t[:, 0], ylim=(0.4, 1.0))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e4df", lw=0.5)
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(os.path.join(args.out, "learning_curve.png"), dpi=300, metadata={"Software": None})
    L += ["Figure: `learning_curve.png`.", ""]

    mins = {os.path.basename(r): json.load(open(os.path.join(r, "results.json")))["_config"]["minutes"] for r in args.main_runs + args.smooth_runs + args.corr_runs + [args.curve_run]}
    L += ["## Settings", "", f"Runtime: {sum(mins.values()) / 60:.2f} h in total.", f"Device: {cfg['device']}.", ""]
    oof.to_csv(os.path.join(args.out, "oof_predictions.csv"), index=False)
    folds.to_csv(os.path.join(args.out, "fold_metrics.csv"), index=False)
    allc.to_csv(os.path.join(args.out, "curve_fold_metrics.csv"), index=False)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump({"models": rows, "tests": stats, "curve": curve_out, "sanity": sanity, "seqcnn_wins_primary": bool(won), "minutes": mins,
                   "created": time.strftime("%Y-%m-%d %H:%M"), "_environment": env_info()}, fh, indent=2, default=float)
    with open(os.path.join(args.out, "summary.md"), "w") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
