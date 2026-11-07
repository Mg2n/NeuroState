"""Follow-up learning curve for the paper: Table VII and Fig. 7, from the saved outputs in results/followup_seqcnn/.

Writes figures/paper/table7_followup_curve.{md,tex} and fig7_followup_curve.{png,pdf}. Nothing is trained, no result file
is written, and the frozen followup_analysis.py is neither run nor changed. No new test or interval is added: means, SDs
over folds, paired differences and the SD across draws are the ones PREREGISTERED.md fixes. Stops if the fold metrics
disagree with results.json or summary.md.

  .venv/bin/python make_followup_curve.py
"""
import json
import os

import matplotlib.pyplot as plt
import pandas as pd

from make_figures import COL1, INK, LINES, LOGREG, MUTED, R, save, table

FU = os.path.join(R, "followup_seqcnn")
SIZES = [20, 35, 52]
METRICS = (("balanced_accuracy", "Balanced accuracy", "Bal. acc."), ("auc", "AUC", "AUC"))
SEQ_COLOR, SEQ_MARK = "#008300", "o"
LR_COLOR, LR_DASH = LINES[LOGREG]  # the same line as logistic regression in Fig. 2
OFFSET = 0.6  # training subjects, so the two error bars do not overlap


def load():
    curve = json.load(open(os.path.join(FU, "results.json")))["curve"]
    folds = pd.read_csv(os.path.join(FU, "curve_fold_metrics.csv"))
    summary = open(os.path.join(FU, "summary.md")).read()
    draw_sd = {}
    for metric, _, _ in METRICS:
        for n in SIZES:
            g = folds[folds["size"].astype(str) == ("full" if n == 52 else str(n))]
            per_fold = g.groupby(["model", "repeat", "fold"])[metric].mean().unstack("model")
            diff = per_fold.seqcnn - per_fold.logreg
            c = curve[f"{metric}_{n}"]
            assert len(per_fold) == 15, (metric, n)
            assert abs(diff.mean() - c["diff"]) < 1e-12 and abs(diff.std() - c["diff_sd"]) < 1e-12, (metric, n)
            assert abs(diff.mean()) < diff.std(), ("difference outside its SD", metric, n)
            assert abs(per_fold.seqcnn.mean() - c["seqcnn"]) < 1e-12 and abs(per_fold.logreg.mean() - c["logreg"]) < 1e-12, (metric, n)
            label = f"{n} (full)" if n == 52 else str(n)
            row = f"| {label} | {c['seqcnn']:.3f} ± {c['seqcnn_sd']:.3f} | {c['logreg']:.3f} ± {c['logreg_sd']:.3f} | {c['diff']:+.3f} ± {c['diff_sd']:.3f} | "
            if n == 52:
                assert row + "- | - |" in summary, (metric, n)
            else:
                sd = g.groupby(["model", "repeat", "fold"])[metric].std(ddof=1).groupby("model").mean()
                draw_sd[metric, n] = (sd.seqcnn, sd.logreg)
                assert row + f"{sd.seqcnn:.3f} | {sd.logreg:.3f} |" in summary, (metric, n)
    return curve, draw_sd


def write_table(curve, draw_sd):
    head = ["Training subjects"]
    for _, _, short in METRICS:
        head += [f"{short} seq-CNN", f"{short} LR", f"{short} diff.", f"{short} SD across draws (seq-CNN / LR)"]
    rows = []
    for n in SIZES:
        row = [f"{n} (full)" if n == 52 else str(n)]
        for metric, _, _ in METRICS:
            c = curve[f"{metric}_{n}"]
            row += [f"{c['seqcnn']:.3f} ± {c['seqcnn_sd']:.3f}", f"{c['logreg']:.3f} ± {c['logreg_sd']:.3f}", f"{c['diff']:+.3f} ± {c['diff_sd']:.3f}",
                    "-" if n == 52 else "{:.3f} / {:.3f}".format(*draw_sd[metric, n])]
        rows.append(row)
    table("table7_followup_curve", head, rows, "Follow-up learning curve, primary labels (descriptive, no tests). Mean ± SD over 15 folds; "
          "diff. = seq-CNN minus logistic regression (LR), paired by fold; SD across draws = SD over the 5 draws within a fold, averaged "
          "over folds; 52 is the full fold, with one possible subset and so no draws.", "lcccccccc", wide=True)


def write_figure(curve):
    fig, axes = plt.subplots(2, 2, figsize=(COL1, 3.2), layout="constrained", sharex=True, height_ratios=[1.25, 1], sharey="row")
    val = lambda metric, key: [curve[f"{metric}_{n}"][key] for n in SIZES]
    for j, (metric, title, _) in enumerate(METRICS):
        top, bottom = axes[0, j], axes[1, j]
        top.errorbar([n - OFFSET for n in SIZES], val(metric, "seqcnn"), yerr=val(metric, "seqcnn_sd"), color=SEQ_COLOR, marker=SEQ_MARK, ms=4,
                     lw=1.4, capsize=2, elinewidth=0.8, label="seq-CNN (one-hot)")
        top.errorbar([n + OFFSET for n in SIZES], val(metric, "logreg"), yerr=val(metric, "logreg_sd"), color=LR_COLOR, ls=LR_DASH, marker="s", ms=3.5,
                     lw=1.4, capsize=2, elinewidth=0.8, label="Logistic regression")
        top.set_title(title, color=INK)
        top.set_ylim(0.6, 1.0)
        bottom.axhline(0, color=MUTED, lw=0.8, zorder=1)
        bottom.errorbar(SIZES, val(metric, "diff"), yerr=val(metric, "diff_sd"), color=INK, marker="D", ms=3, lw=1.0, capsize=2, elinewidth=0.8, zorder=3)
        bottom.set_ylim(-0.12, 0.12)
        bottom.set_xticks(SIZES, ["20", "35", "52\n(full)"])
        bottom.set_xlabel("Training subjects")
    axes[0, 0].set_ylabel("Mean ± SD over folds")
    axes[1, 0].set_ylabel("seq-CNN minus LR\n(mean ± SD)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncols=2, handlelength=2.6)
    save(fig, "fig7_followup_curve")


def main():
    curve, draw_sd = load()
    write_table(curve, draw_sd)
    write_figure(curve)


if __name__ == "__main__":
    main()
