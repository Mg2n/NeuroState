"""Redraws learning_curve.png with the y-axis label visible, as learning_curve_fixed.png.

Same values (results.json), same style and size as the frozen followup_analysis.py. The only change is the label, split
over two lines so it fits. The original figure and the frozen snapshot are left unchanged.

  ../../experiments/.venv/bin/python redraw_learning_curve.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
curve = json.load(open(os.path.join(HERE, "results.json")))["curve"]
sizes = [20, 35, 52]
get = lambda key: [curve[f"balanced_accuracy_{n}"][key] for n in sizes]

fig, ax = plt.subplots(figsize=(3.5, 2.5), layout="constrained")
ax.errorbar([n - 0.4 for n in sizes], get("seqcnn"), yerr=get("seqcnn_sd"), color="#2a78d6", marker="o", ms=4, lw=1.4, capsize=2, label="seq-CNN (one-hot)")
ax.errorbar([n + 0.4 for n in sizes], get("logreg"), yerr=get("logreg_sd"), color="#eb6834", marker="s", ms=4, lw=1.4, ls="--", capsize=2, label="Logistic regression")
ax.set(xlabel="Training subjects", ylabel="Balanced accuracy\n(mean ± SD over folds)", xticks=sizes, ylim=(0.4, 1.0))
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", color="#e5e4df", lw=0.5)
ax.legend(frameon=False, loc="lower right")
fig.savefig(os.path.join(HERE, "learning_curve_fixed.png"), dpi=300, metadata={"Software": None})
