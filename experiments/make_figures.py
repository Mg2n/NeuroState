"""Task 07: every paper figure and table, generated from saved results. Writes figures/paper/.

Headline numbers come from the preregistered confirmation run (results/confirmation); Task 06 variants are labelled
exploratory. Nothing is trained here and no number is typed by hand, except the published benchmarks in LITERATURE,
which were checked against each paper. Figures: matplotlib, 300 dpi PNG + PDF, sized for IEEE columns (3.5 in / 7.16 in).
Re-running reproduces every file byte for byte (no timestamps in the metadata, fixed jitter seed).

  .venv/bin/python make_figures.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy.stats import mannwhitneyu
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

from make_improvements import md_table
from models import MicroStateNet
from validate_microstates import NS, align_sign, from_json, info_for, koenig_on, match_to_reference

R = "../results"
OUT = "../figures/paper"
COL1, COL2 = 3.5, 7.16  # IEEE column and full-page widths, inches
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e5e4df"
FUSION, HYBRID, EEGNET = "fusion_eegnet_ens5_logreg", "hybrid_ens5", "eegnet_ens5"
LOGREG, RF = "baseline_logreg", "baseline_rf"
MODELS = [FUSION, HYBRID, EEGNET, LOGREG, RF]
NAMES = {FUSION: "Late fusion (EEGNet ens. + LR)", HYBRID: "Hybrid ensemble", EEGNET: "EEGNet ensemble",
         LOGREG: "Logistic regression (baseline)", RF: "Random forest (baseline)"}
SHORT = {FUSION: "Late fusion", HYBRID: "Hybrid", EEGNET: "EEGNet", LOGREG: "Logistic regression", RF: "Random forest"}
# colour and dash follow the model in every figure; the reference baseline is neutral, not a categorical hue
LINES = {FUSION: ("#1baf7a", "-"), HYBRID: ("#eb6834", (0, (5, 1.5))), EEGNET: ("#2a78d6", (0, (1.5, 1))),
         LOGREG: (MUTED, (0, (4, 1, 1, 1)))}
BLUE_RAMP = ["#f4f8fd", "#c6dcf6", "#86b6ef", "#2a78d6", "#104281"]
AD_COLOR, HC_COLOR = "#6250d6", "#eb6834"  # validated as a pair; AD and HC are shown only in the microstate figure

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.axisbelow": True, "legend.frameon": False, "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300,
    "figure.facecolor": "white", "savefig.facecolor": "white", "hatch.linewidth": 0.6, "hatch.color": "white"})


def save(fig, name):
    fig.savefig(os.path.join(OUT, f"{name}.png"), metadata={"Software": None})
    fig.savefig(os.path.join(OUT, f"{name}.pdf"), metadata={"Creator": None, "Producer": None, "CreationDate": None})
    plt.close(fig)


def tex(s):
    """Plain table text -> LaTeX."""
    s = str(s).replace("\\", r"\textbackslash{}")
    parts = s.split("`")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")):
        parts = [p.replace(a, b) for p in parts]
    s = "".join(rf"\texttt{{{p}}}" if i % 2 else p for i, p in enumerate(parts))
    for a, b in (("±", r"$\pm$"), ("→", r"$\rightarrow$"), ("->", r"$\rightarrow$"), ("−", r"$-$"), ("Δ", r"$\Delta$"),
                 ("×", r"$\times$"), ("|r|", r"$|r|$")):
        s = s.replace(a, b)
    return s


def table(name, header, rows, caption, cols, wide=False):
    """Writes the same table as Markdown and as LaTeX (booktabs)."""
    rows = [[str(c) for c in r] for r in rows]
    md = [f"**{caption}**", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    with open(os.path.join(OUT, f"{name}.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    env = "table*" if wide else "table"
    t = [rf"\begin{{{env}}}[!t]", r"\centering", r"\footnotesize", rf"\caption{{{tex(caption)}}}",
         rf"\label{{tab:{name}}}", rf"\begin{{tabular}}{{{cols}}}", r"\toprule",
         " & ".join(tex(h) for h in header) + r" \\", r"\midrule"]
    t += [" & ".join(tex(c) for c in r) + r" \\" for r in rows]
    t += [r"\bottomrule", r"\end{tabular}", rf"\end{{{env}}}"]
    with open(os.path.join(OUT, f"{name}.tex"), "w") as fh:
        fh.write("\n".join(t) + "\n")


def ms(d, k):
    return f"{d[k]['mean']:.3f} ± {d[k]['sd']:.3f}"


# ---- figures ----

def fig_architecture():
    """Block sizes are read from the model itself, so the diagram cannot drift from models.py."""
    net = MicroStateNet(n_chans=19, n_times=512, n_classes=2, use_ms=True)
    d_e, d_m, d_c = net.eeg.out_dim, net.ms.out_dim, net.head.in_features
    n_out = net.head.out_features
    assert d_e + d_m == d_c
    fig = plt.figure(figsize=(COL2, 2.55))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set(xlim=(0, 100), ylim=(0, 36))
    ax.axis("off")

    def box(x, y, w, h, title, lines, fill):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", fc=fill, ec=MUTED, lw=0.6))
        ax.text(x + w / 2, y + h - 1.5, title, ha="center", va="top", fontsize=6.5, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h - 4.8, "\n".join(lines), ha="center", va="top", fontsize=5.8, color=MUTED, linespacing=1.3)

    def arrow(a, b):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=6, lw=0.7, color=MUTED, shrinkA=0, shrinkB=0))

    w, h, y1, y2 = 15.5, 13.5, 19.5, 3.5
    xs = [0.6, 17.6, 34.6, 51.6]
    eeg = [("Raw EEG", ["19 channels ×", "512 samples", "(4 s at 128 Hz)"]),
           ("Temporal conv", ["8 filters, 1×64", "BatchNorm"]),
           ("Depthwise spatial", ["D = 2, 19×1", "BatchNorm, ELU", "AvgPool 1×4", "dropout"]),
           ("Separable conv", ["16 filters, 1×16", "BatchNorm, ELU", "AvgPool 1×8", "dropout"])]
    mic = [("Microstate input", ["|correlation| with 4 maps", "× 512 samples", "(maps: training fold)"]),
           ("1D conv", ["8 filters, kernel 33", "BatchNorm, ELU", "AvgPool 4", "dropout"]),
           ("1D conv", ["16 filters, kernel 9", "BatchNorm, ELU", "AdaptivePool 8", "dropout"]),
           ("Linear", [f"Flatten → {d_m} units", "ELU"])]
    for row, y, fill in ((eeg, y1, "#eaf2fb"), (mic, y2, "#fdeee8")):
        for i, (t, ln) in enumerate(row):
            box(xs[i], y, w, h, t, ln, fill)
            if i:
                arrow((xs[i - 1] + w, y + h / 2), (xs[i], y + h / 2))
    ax.text(0.6, 34.6, "EEGNet branch (Lawhern et al., 2018)", fontsize=7, color=INK, va="center")
    ax.text(0.6, 1.7, "Microstate branch (ours)", fontsize=7, color=INK, va="center")
    cx, cw, lx, lw, ly = 71.5, 12, 86.5, 13, 11.5
    box(cx, ly, cw, h, "Concatenate", [f"{d_e} + {d_m}", f"= {d_c} units"], "#f3f2ee")
    box(lx, ly, lw, h, "Linear", [f"{d_c} → {n_out} classes", "AD / HC"], "#f3f2ee")
    arrow((xs[3] + w, y1 + h / 2), (cx, ly + 9))
    arrow((xs[3] + w, y2 + h / 2), (cx, ly + 4.5))
    arrow((cx + cw, ly + h / 2), (lx, ly + h / 2))
    ax.text(xs[3] + w + 0.5, y1 + h / 2 + 0.6, f"{d_e}", fontsize=5.8, color=MUTED)
    ax.text(xs[3] + w + 0.5, y2 + h / 2 - 2.2, f"{d_m}", fontsize=5.8, color=MUTED)
    save(fig, "fig1_architecture")


def fig_roc(oof, res):
    """Mean of the per-repeat ROC curves, so the curve's area matches the pooled AUC in the legend."""
    fig, ax = plt.subplots(figsize=(COL1, 3.1), layout="constrained")
    grid = np.linspace(0, 1, 1001)
    ax.plot([0, 1], [0, 1], color=GRID, lw=0.8, zorder=1)
    for m in (FUSION, HYBRID, EEGNET, LOGREG):
        g = oof[oof.model == m]
        tprs, aucs = [], []
        for _, x in g.groupby("repeat"):
            fpr, tpr, _ = roc_curve(x.label, x.prob)
            tprs.append(np.interp(grid, fpr, tpr))
            aucs.append(roc_auc_score(x.label, x.prob))
        p = res["models"][m]["pooled_auc"]
        assert abs(np.mean(aucs) - p["point"]) < 1e-9, m
        assert abs(np.trapezoid(np.mean(tprs, 0), grid) - p["point"]) < 0.01, m
        c, ls = LINES[m]
        ax.plot(grid, np.mean(tprs, 0), color=c, ls=ls, lw=1.4, zorder=3,
                label=f"{SHORT[m]}: {p['point']:.3f} [{p['ci95'][0]:.3f}, {p['ci95'][1]:.3f}]")
    ax.set(xlabel="1 − specificity (HC wrongly called AD)", ylabel="Sensitivity (AD recall)", xlim=(0, 1), ylim=(0, 1.005))
    ax.set_aspect("equal")
    ax.legend(loc="lower right", title="Pooled AUC [95% CI]", title_fontsize=7, handlelength=2.6)
    save(fig, "fig2_roc")


def fig_confusion(oof):
    fig, axes = plt.subplots(1, 3, figsize=(COL2 * 0.72, 1.85), layout="constrained", sharey=True)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    for ax, m in zip(axes, (EEGNET, HYBRID, FUSION)):
        g = oof[oof.model == m]
        c = confusion_matrix(g.label, (g.prob >= 0.5).astype(int), labels=[1, 0])
        share = c / c.sum(1, keepdims=True)
        ax.imshow(share, cmap=cmap, vmin=0, vmax=1)
        ax.grid(False)
        ax.spines[:].set_visible(False)
        ax.tick_params(length=0)
        ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["AD", "HC"], yticklabels=["AD", "HC"], title=SHORT[m],
               xlabel="Predicted")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{c[i, j]}\n{share[i, j]:.0%}", ha="center", va="center", fontsize=7,
                        color="white" if share[i, j] > 0.55 else INK)
    axes[0].set_ylabel("True")
    save(fig, "fig3_confusion")


def fig_leakage():
    """Both bars are the same Task 05 run (CPU, EEGNet, one seed), so only the split differs."""
    R5 = json.load(open(os.path.join(R, "main_AD_vs_HC", "results.json")))
    f5 = pd.read_csv(os.path.join(R, "main_AD_vs_HC", "fold_metrics.csv"))
    f5 = f5[f5.model == "eegnet"]
    leak = R5["leakage_demo_eegnet_window_split"]
    fig, ax = plt.subplots(figsize=(COL1, 2.2), layout="constrained")
    vals = [leak["balanced_accuracy"], f5.balanced_accuracy.mean()]
    b = ax.bar([0, 1], vals, width=0.55, color=LINES[EEGNET][0], zorder=3)
    b[0].set_hatch("////")
    ax.errorbar(1, vals[1], yerr=f5.balanced_accuracy.std(), color=INK, lw=0.8, capsize=2.5, zorder=4)
    ax.axhline(0.5, color=MUTED, lw=0.6, ls=(0, (2, 2)), zorder=2)
    ax.text(1.85, 0.51, "chance", fontsize=6, color=MUTED, ha="right", va="bottom")
    ax.text(0, vals[0] + 0.015, f"{vals[0]:.3f}", ha="center", va="bottom", color=INK)
    ax.text(1.31, vals[1] + 0.008, f"{vals[1]:.3f} ± {f5.balanced_accuracy.std():.3f}", ha="left", va="center", color=INK,
            fontsize=7, clip_on=False)
    ax.set_xticks([0, 1], ["Random window split\n(same people in both sets)", "Subject-wise CV\n(no person in both)"])
    ax.set(ylabel="EEGNet balanced accuracy", ylim=(0, 1.08), xlim=(-0.5, 1.85))
    ax.grid(False, axis="x")
    ax.spines["bottom"].set_position(("data", 0))
    save(fig, "fig4_leakage")
    return leak, f5


def fig_microstate_maps():
    """Task 04 group maps (all AD + HC, validation only, never used for classification) vs Koenig 2002."""
    g = json.load(open(os.path.join(R, "microstates", "group_maps.json")))
    maps, ch = np.array(g["group_maps"]), g["ch_names"]
    tmpl = from_json(os.path.join(NS, "templates", "Koenig2002_4class.json"))
    K = koenig_on(ch, tmpl)
    res = match_to_reference(maps, ch, [f"M{i + 1}" for i in range(4)], tmpl.maps, tmpl.ch_names, tmpl.labels)
    order = [i for j in range(4) for i in range(4) if res.assignment[i] == j]
    for i, lab in g["labels_provisional"].items():  # same assignment as Task 04
        assert res.reference_names[res.assignment[int(i)]] == lab
    ours = align_sign(maps[order], K)
    info = info_for(ch)
    fig, axes = plt.subplots(2, 4, figsize=(COL1, 2.0), layout="constrained")
    for r, (rows, label) in enumerate(((ours, "This study"), (K, "Koenig 2002"))):
        for k in range(4):
            ax = axes[r, k]
            mne.viz.plot_topomap(rows[k] / np.abs(rows[k]).max(), info, axes=ax, show=False, cmap="RdBu_r", vlim=(-1, 1),
                                 contours=0, sensors=False)
            t = f"{tmpl.labels[k]}  |r| = {res.assigned_abs_r[order[k]]:.2f}" if r == 0 else tmpl.labels[k]
            ax.set_title(t, fontsize=7, color=INK, pad=2)
        axes[r, 0].text(-0.16, 0.5, label, transform=axes[r, 0].transAxes, rotation=90, va="center", ha="center",
                        fontsize=7, color=MUTED)
    save(fig, "fig5_microstate_maps")
    return g["gev"], {tmpl.labels[k]: float(res.assigned_abs_r[order[k]]) for k in range(4)}


MS_FEATS = (("coverage", "Coverage (%)"), ("duration", "Mean duration (ms)"), ("occurrence", "Occurrence (per s)"))
STATES = "ABCD"
# (study, reported, task / protocol), checked against the papers on 6 Nov 2026
LITERATURE = [
    ("Jiang et al. 2026, two-stage microstate fusion", "74.3% balanced acc., AUC 0.851",
     "Dementia (AD + FTD) vs HC, ds004504, LOSO"),
    ("Jiang et al. 2026, two-stage microstate fusion", "63.9% balanced acc.", "AD vs FTD vs HC, ds004504, LOSO"),
    ("Miltiadous et al. 2023, DICE-Net", "83.28% acc.", "AD vs HC, 36 AD and 29 HC of the ds004504 cohort, LOSO"),
    ("Wang et al. 2024, ADformer (preprint)", "92.82% subject-level F1", "AD vs HC, ds004504 v1.0.8, subject-independent"),
    ("Brookshire et al. 2024, leakage study", "99.8% -> 53.0% acc.",
     "Segment-based vs subject-based holdout. Not ds004504: 49 subjects with dementia due to Alzheimer's disease vs 49 with subjective cognitive impairment (SCI)"),
]


def fig_microstate_features(f):
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.05), layout="constrained")
    rng = np.random.default_rng(0)
    for ax, (feat, label) in zip(axes, MS_FEATS):
        for k, s in enumerate(STATES):
            for g, off, c, mk in (("A", -0.19, AD_COLOR, "o"), ("C", 0.19, HC_COLOR, "^")):
                v = f[f.Group == g][f"{feat}_{s}"].values
                ax.scatter(k + off + rng.uniform(-0.09, 0.09, len(v)), v, s=5, color=c, alpha=0.4, marker=mk, lw=0, zorder=2)
                ax.plot([k + off - 0.15, k + off + 0.15], [v.mean()] * 2, color=INK, lw=1.2, zorder=3,
                        solid_capstyle="round")
        ax.set_xticks(range(4), STATES)
        ax.set(xlabel="Microstate (provisional label)", ylabel=label, xlim=(-0.55, 3.55))
        ax.grid(False, axis="x")
    h = [plt.Line2D([], [], color=AD_COLOR, marker="o", ls="", ms=3.5, label=f"AD (n = {(f.Group == 'A').sum()})"),
         plt.Line2D([], [], color=HC_COLOR, marker="^", ls="", ms=3.5, label=f"HC (n = {(f.Group == 'C').sum()})"),
         plt.Line2D([], [], color=INK, lw=1.2, label="Group mean")]
    fig.legend(handles=h, loc="outside upper center", ncol=3, handletextpad=0.3, columnspacing=1.5)
    save(fig, "fig6_microstate_features")


# ---- tables ----

def table_main(res):
    rows = []
    for m in MODELS:
        d = res["models"][m]
        p = d["pooled_auc"]
        rows.append([NAMES[m], ms(d, "balanced_accuracy"), ms(d, "auc"), ms(d, "f1"),
                     f"{p['point']:.3f} [{p['ci95'][0]:.3f}, {p['ci95'][1]:.3f}]",
                     f"{d['pooled_sensitivity']:.3f}", f"{d['pooled_specificity']:.3f}"])
    table("table1_main_results", ["Model", "Balanced acc.", "AUC", "F1", "Pooled AUC [95% CI]", "Sens. (pooled)", "Spec. (pooled)"], rows,
          f"Preregistered confirmation run: AD vs HC, {res['n_subjects']} subjects, 5-fold subject-wise CV with repeat seeds "
          "3-5 (15 folds), threshold 0.5. Mean ± SD over folds. The subjects are those of all earlier comparisons, on "
          "new splits: not an independent test set.", "lcccccc", wide=True)


def table_comparisons(res):
    rows = []
    for a, b in ((FUSION, EEGNET), (HYBRID, EEGNET), (FUSION, HYBRID)):
        for metric, lab in (("balanced_accuracy", "Balanced acc. (primary)"), ("auc", "AUC"), ("f1", "F1")):
            s = res["comparisons"][f"{a}_vs_{b}_{metric}"]
            rows.append([f"{SHORT[a]} vs {SHORT[b]}", lab, f"{s['diff_mean']:+.3f} ({s['diff_sd']:.3f})",
                         f"{s['better']} / {s['tied']} / {s['worse']}", f"{s['corrected_p']:.3f}"])
    table("table2_comparisons", ["Comparison", "Metric", "Mean diff. (SD)", "Better / tied / worse", "p"], rows,
          "Preregistered comparisons, paired over 15 folds. p = Nadeau-Bengio corrected resampled t-test, two-sided, "
          "unadjusted (3 primary and 6 secondary tests). No comparison reaches p < 0.05."
          if all(s["corrected_p"] >= 0.05 for s in res["comparisons"].values()) else
          "Preregistered comparisons, paired over 15 folds. p = Nadeau-Bengio corrected resampled t-test, two-sided, "
          "unadjusted (3 primary and 6 secondary tests).", "llccc", wide=True)


def table_literature(res):
    rows = [[s, rep.replace("->", "→"), task] for s, rep, task in LITERATURE]
    for m in (FUSION, EEGNET, HYBRID):
        v = res["models"][m]["balanced_accuracy"]["mean"]
        rows.append([f"This study: {NAMES[m].split(' (')[0]}", f"{100 * v:.1f}% balanced acc.",
                     "AD vs HC, 5-fold subject-wise × 3, preregistered"])
    table("table3_literature", ["Study", "Reported", "Task / protocol"], rows,
          "Published results and this study. Metrics, class definitions and protocols differ, so this is context, not a "
          "ranking. LOSO = leave-one-subject-out.", "p{6.2cm}p{3.2cm}p{6.2cm}", wide=True)


def table_improvements():
    md = md_table(os.path.join(R, "improvements.md"), "## Exploratory comparisons")
    head = [c.strip() for c in md[0].strip("|").split("|")]
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in md[2:]]
    assert all(len(r) == len(head) for r in rows)
    table("table4_improvements", head, rows,
          "Exploratory variants from Task 06 (repeat seeds 0-2, the Task 05 splits). No row was selected on test folds and "
          "none is the headline result; the variants share these splits, so the best row is expected to look better by "
          "chance. p = corrected resampled t-test.", "p{6.2cm}ccp{3.2cm}c", wide=True)


def table_three_class():
    a = pd.read_csv(os.path.join(R, "improve_3class", "fold_metrics.csv"))
    b = pd.read_csv(os.path.join(R, "improve_3class_no086", "fold_metrics.csv"))
    st = json.load(open(os.path.join(R, "improve_3class_no086", "results.json")))["stats"]
    n_a = json.load(open(os.path.join(R, "improve_3class", "results.json")))["n_subjects"]
    n_b = json.load(open(os.path.join(R, "improve_3class_no086", "results.json")))["n_subjects"]

    def cell(f, m, k):
        g = f[f.model == m][k]
        assert len(g) == 15
        return f"{g.mean():.3f} ± {g.std():.3f}"

    rows = []
    for m, lab in ((LOGREG, NAMES[LOGREG]), (RF, NAMES[RF]), (EEGNET, NAMES[EEGNET]), (HYBRID, NAMES[HYBRID])):
        s = st[f"{m}_vs_with086_balanced_accuracy"]
        rows.append([lab, cell(a, m, "balanced_accuracy"), cell(a, m, "f1"), cell(a, m, "auc"),
                     cell(b, m, "balanced_accuracy"), f"{s['diff_mean']:+.3f} ({s['corrected_p']:.2f})"])
    table("table5_three_class", ["Model", f"Bal. acc. (n = {n_a})", "Macro-F1", "Macro AUC",
                                 f"Bal. acc. without sub-086 (n = {n_b})", "Effect of removal (p)"], rows,
          "Secondary task: AD vs FTD vs HC, 5-fold subject-wise CV × 3 (repeat seeds 0-2), chance = 0.333. The full cohort "
          "is the main result and the sub-086 exclusion is a sensitivity analysis. Effect = same test subjects, sub-086 "
          "removed from training and map fitting minus kept; p = corrected resampled t-test.", "lccccc", wide=True)


def table_microstate_features(f):
    rows = []
    for s in STATES:
        row = [s]
        for feat, _ in MS_FEATS:
            x, y = f[f.Group == "A"][f"{feat}_{s}"], f[f.Group == "C"][f"{feat}_{s}"]
            dp = 2 if feat == "occurrence" else 1
            row += [f"{x.mean():.{dp}f} ± {x.std():.{dp}f}", f"{y.mean():.{dp}f} ± {y.std():.{dp}f}",
                    f"{mannwhitneyu(x, y, alternative='two-sided').pvalue:.3g}"]
        rows.append(row)
    table("table6_microstate_features", ["State (prov.)", "Coverage % AD", "HC", "p", "Duration ms AD", "HC", "p",
                                         "Occurrence /s AD", "HC", "p"], rows,
          "AD vs HC microstate features (descriptive). Group maps fitted on all AD and HC subjects, so these are not "
          "classification results. Mean ± SD; p = two-sided Mann-Whitney U, uncorrected for the 12 tests. State labels are "
          "provisional matches to Koenig 2002.", "l" + "ccc" * 3, wide=True)


def write_index(res, leak, f5, gev, r_map):
    e = res["models"][EEGNET]["balanced_accuracy"]["mean"]
    L = ["# Paper figures and tables", "",
         "Generated by `experiments/make_figures.py` from `results/`; do not edit by hand. Research use only: "
         "classification, not diagnosis.", "",
         "| File | Shows | Source |", "|---|---|---|",
         "| `fig1_architecture` | Hybrid model: two branches, concatenation, classifier | `experiments/models.py` |",
         "| `fig2_roc` | Mean of the per-repeat ROC curves, confirmation run | `results/confirmation/` |",
         "| `fig3_confusion` | Subject-level confusion matrices at threshold 0.5, counts over 3 repeats (65 subjects × 3 = "
         "195 predictions, not 195 independent people) | `results/confirmation/` |",
         "| `fig4_leakage` | EEGNet: random window split vs subject-wise CV | `results/main_AD_vs_HC/` |",
         "| `fig5_microstate_maps` | Group maps vs Koenig 2002 A-D | `results/microstates/group_maps.json` |",
         "| `fig6_microstate_features` | AD vs HC coverage, duration, occurrence | `results/microstates/` |",
         "| `fig7_followup_curve` | Follow-up learning curve; written by `experiments/make_followup_curve.py` | `results/followup_seqcnn/` |",
         "| `table1_main_results` | Headline results | `results/confirmation/` |",
         "| `table2_comparisons` | Preregistered comparisons | `results/confirmation/` |",
         "| `table3_literature` | Published results and this study | checked against the papers, `results/confirmation/` |",
         "| `table4_improvements` | Exploratory Task 06 variants | `results/improvements.md` |",
         "| `table5_three_class` | AD vs FTD vs HC, with and without sub-086 | `results/improve_3class*/` |",
         "| `table6_microstate_features` | AD vs HC microstate features | `results/microstates/` |",
         "| `table7_followup_curve` | Follow-up learning curve; written by `experiments/make_followup_curve.py` | `results/followup_seqcnn/` |", "",
         "## Notes for captions", "",
         f"- **Fig. 2:** the legend AUC is the pooled AUC (per repeat, then averaged) with its subject-bootstrap CI. Fold-mean "
         f"AUC in Table 1 is a different summary and is higher for some models.",
         f"- **Fig. 4:** both bars come from the Task 05 run (CPU, one seed), so only the split differs. Window split: "
         f"balanced accuracy {leak['balanced_accuracy']:.3f}, accuracy {leak['accuracy']:.3f}, {leak['n_test_windows']:,} test "
         f"windows. Subject-wise: balanced accuracy {f5.balanced_accuracy.mean():.3f} ± {f5.balanced_accuracy.std():.3f}, "
         f"accuracy {f5.accuracy.mean():.3f} ± {f5.accuracy.std():.3f}, 15 folds. That subject-wise value is above all 5 MPS "
         f"seeds and is unexplained; the headline EEGNet ensemble is {e:.3f}, so the leakage gap shown is on the small side.",
         f"- **Fig. 5:** maps fitted on all AD + HC subjects for validation and figures only (GEV {gev:.3f}); the experiment "
         "refits maps on each training fold. Labels are provisional. Polarity is aligned for display. |r| to Koenig: "
         + ", ".join(f"{k} {v:.3f}" for k, v in r_map.items()) + ".",
         "- **Fig. 6:** descriptive only; p values are in Table 6. Do not read them as classification evidence.",
         "- **Table 3:** published values were checked against each paper on 6 Nov 2026. Brookshire et al. used a different "
         "cohort, not ds004504, and ADformer's 92.82% is from arXiv version 2.",
         "- **Tables:** the `.tex` files need `\\usepackage{booktabs}`. No LaTeX compiler was available here, so they have not "
         "been compiled.", ""]
    with open(os.path.join(OUT, "README.md"), "w") as fh:
        fh.write("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    res = json.load(open(os.path.join(R, "confirmation", "results.json")))
    oof = pd.read_csv(os.path.join(R, "confirmation", "oof_predictions.csv"))
    feats = pd.read_csv(os.path.join(R, "microstates", "group_features_AD_HC.csv"))
    fig_architecture()
    fig_roc(oof, res)
    fig_confusion(oof)
    leak, f5 = fig_leakage()
    gev, r_map = fig_microstate_maps()
    fig_microstate_features(feats)
    table_main(res)
    table_comparisons(res)
    table_literature(res)
    table_improvements()
    table_three_class()
    table_microstate_features(feats)
    write_index(res, leak, f5, gev, r_map)


if __name__ == "__main__":
    main()
