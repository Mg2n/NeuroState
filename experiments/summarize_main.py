"""Task 05 step 3-4: write results/main_AD_vs_HC/summary.md from a run_experiment.py output folder.

Statistics:
  - per model: balanced accuracy / AUC / F1, mean +/- SD over folds (folds x repeats) and pooled
  - hybrid vs EEGNet: Wilcoxon signed-rank on the paired fold scores, plus the Nadeau-Bengio corrected
    resampled t-test (folds from repeated CV share training subjects, so plain fold tests are optimistic)
  - bootstrap 95% CI of the pooled AUC per model (resampling subjects; AUC averaged over repeats),
    and a paired bootstrap CI of the AUC difference hybrid - EEGNet

  .venv/bin/python summarize_main.py --run ../results/main_AD_vs_HC
"""
import argparse
import json
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist
from scipy.stats import wilcoxon
from sklearn.metrics import roc_auc_score

MODELS = ["baseline_logreg", "baseline_rf", "eegnet", "hybrid"]
N_BOOT = 2000
BOOT_SEED = 12345

BENCHMARKS = [  # as listed in CLAUDE.md; protocol details beyond that must be checked in each paper
    ("Two-Stage Microstate Fusion (Biosensors 2026)", "74.3% balanced acc.", "dementia vs HC, LOSO",
     "different class definition ('dementia'; check whether FTD is included) and leave-one-subject-out"),
    ("DICE-Net (Miltiadous et al. 2023)", "83.28% acc.", "AD vs HC, LOSO",
     "plain accuracy, not balanced accuracy; LOSO trains on 64 subjects per fold vs about 52 here"),
    ("ADformer (2024)", "92.82% F1", "AD vs HC, subject-independent",
     "different metric (F1) and split; check the paper's evaluation unit (subject or sample) before comparing"),
]


def parse_epochs(log_path):
    """Epochs actually trained per fold and model, from the run log."""
    rows, cur = [], None
    for line in open(log_path):
        m = re.search(r"rep (\d+) fold (\d+): maps fitted \(GEV ([\d.]+)\)", line)
        if m:
            cur = (int(m.group(1)), int(m.group(2)), float(m.group(3)))
        m = re.search(r"(eegnet|hybrid): trained (\d+) epochs", line)
        if m and cur:
            rows.append({"repeat": cur[0], "fold": cur[1], "gev": cur[2], "model": m.group(1),
                         "epochs": int(m.group(2))})
    return pd.DataFrame(rows)


def fold_times(log_path):
    stamps = []
    for line in open(log_path):
        m = re.match(r"(\d\d):(\d\d):(\d\d) rep \d+ fold \d+", line)
        if m:
            stamps.append(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)))
    d = np.diff(stamps)
    d = np.where(d < 0, d + 86400, d)  # past midnight
    return d / 60


def boot_auc(oof, models, rng):
    """Subject bootstrap: resample subjects (stratified by label), AUC per repeat, mean over repeats."""
    subj = oof[["subject", "label"]].drop_duplicates().set_index("subject").label
    pos, neg = subj[subj == 1].index.values, subj[subj == 0].index.values
    piv = {m: oof[oof.model == m].pivot_table(index="subject", columns="repeat", values="prob") for m in models}
    lab = subj
    out = {m: [] for m in models}
    for _ in range(N_BOOT):
        s = np.r_[rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]
        y = lab.loc[s].values
        for m in models:
            P = piv[m].loc[s]
            out[m].append(np.mean([roc_auc_score(y, P[c].values) for c in P.columns]))
    point = {m: np.mean([roc_auc_score(lab.loc[piv[m].index].values, piv[m][c].values) for c in piv[m].columns])
             for m in models}
    return point, {m: np.array(v) for m, v in out.items()}


def corrected_t(d, n_train, n_test):
    """Nadeau & Bengio (2003) corrected resampled t-test for repeated CV fold differences."""
    n = len(d)
    var = np.var(d, ddof=1)
    if var == 0:
        return float("nan"), float("nan")
    t = np.mean(d) / np.sqrt((1 / n + n_test / n_train) * var)
    return float(t), float(2 * t_dist.sf(abs(t), n - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="../results/main_AD_vs_HC")
    args = ap.parse_args()
    R = json.load(open(os.path.join(args.run, "results.json")))
    folds = pd.read_csv(os.path.join(args.run, "fold_metrics.csv"))
    oof = pd.read_csv(os.path.join(args.run, "oof_predictions.csv"))
    cfg, env, seeds = R["_config"], R.get("_environment", {}), R.get("_seeds", {})
    ep = parse_epochs(os.path.join(args.run, "log.txt"))
    ft = fold_times(os.path.join(args.run, "log.txt"))
    models = [m for m in MODELS if m in folds.model.unique()]
    n_sub = oof.subject.nunique()
    n_pos = oof.drop_duplicates("subject").label.sum()
    n_folds_total = folds[folds.model == models[0]].shape[0]

    rng = np.random.default_rng(BOOT_SEED)
    auc_point, auc_boot = boot_auc(oof, models, rng)

    L = [f"# Main experiment: AD vs HC ({cfg['folds']}-fold subject-wise CV x {cfg['repeats']} repeats)", "",
         "Research use only: this classifies AD vs healthy controls in a public dataset; it is not a diagnostic test.",
         "", f"Subjects: {n_sub} ({n_pos} AD, {n_sub - n_pos} HC), ds004504 derivatives, prepared as in "
         "`results/prep_report.md` (no window rejection). Every subject is in exactly one test fold per repeat; "
         "early-stopping subjects (15%) and microstate maps come from the training fold only. "
         "Subject score = mean of its 4-s window probabilities; threshold 0.5.", "",
         "## Results", "",
         f"Mean ± SD over the {n_folds_total} test folds; *pooled* = all out-of-fold subject predictions of a "
         "repeat scored together, averaged over repeats. AUC 95% CI: subject bootstrap "
         f"({N_BOOT} resamples, stratified, seed {BOOT_SEED}).", "",
         "| Model | Balanced accuracy (fold mean ± SD) | AUC (fold mean ± SD) | F1 (fold mean ± SD) | "
         "Pooled bal. acc. | Pooled AUC [95% CI] | Pooled F1 |", "|---|---|---|---|---|---|---|"]
    names = {"baseline_logreg": "A. Baseline: microstate features + logistic regression",
             "baseline_rf": "A. Baseline: microstate features + random forest",
             "eegnet": "B. EEGNet alone", "hybrid": "C. Hybrid (EEGNet + microstate CNN)"}
    for m in models:
        f = folds[folds.model == m]
        lo, hi = np.percentile(auc_boot[m], [2.5, 97.5])
        L.append(f"| {names[m]} | {f.balanced_accuracy.mean():.3f} ± {f.balanced_accuracy.std():.3f} | "
                 f"{f.auc.mean():.3f} ± {f.auc.std():.3f} | {f.f1.mean():.3f} ± {f.f1.std():.3f} | "
                 f"{R[m]['pooled_balanced_accuracy']:.3f} | {auc_point[m]:.3f} [{lo:.3f}, {hi:.3f}] | "
                 f"{R[m]['pooled_f1']:.3f} |")
    # per repeat
    L += ["", "Pooled balanced accuracy per repeat (shows split-to-split variation):", "",
          "| Model | " + " | ".join(f"repeat {r}" for r in sorted(oof.repeat.unique())) + " |",
          "|---|" + "---|" * oof.repeat.nunique()]
    from sklearn.metrics import balanced_accuracy_score
    for m in models:
        g = oof[oof.model == m]
        L.append(f"| {m} | " + " | ".join(f"{balanced_accuracy_score(gg.label, (gg.prob >= 0.5).astype(int)):.3f}"
                                         for _, gg in g.groupby("repeat")) + " |")
    # sensitivity / specificity (explains F1 vs balanced-accuracy gaps)
    L += ["", "Sensitivity and specificity at threshold 0.5 (all out-of-fold subject predictions, 3 repeats pooled; "
          "AD = positive class):", "",
          "| Model | Sensitivity (AD recall) | Specificity (HC recall) | Median score, AD | Median score, HC |",
          "|---|---|---|---|---|"]
    for m in models:
        g = oof[oof.model == m]
        pred = (g.prob >= 0.5).astype(int)
        L.append(f"| {m} | {(pred[g.label == 1] == 1).mean():.3f} | {(pred[g.label == 0] == 0).mean():.3f} | "
                 f"{g.prob[g.label == 1].median():.3f} | {g.prob[g.label == 0].median():.3f} |")
    if {"eegnet", "hybrid"} <= set(models):
        sens = {m: ((oof[(oof.model == m) & (oof.label == 1)].prob >= 0.5)).mean() for m in ("eegnet", "hybrid")}
        L += ["", f"The hybrid misses more AD subjects than EEGNet (sensitivity {sens['hybrid']:.3f} vs "
              f"{sens['eegnet']:.3f}) and fewer HC subjects; its AUC is close to EEGNet's, so most of the gap is in "
              "which side of the fixed 0.5 threshold subjects fall on, not in how they are ranked. Fewer AD subjects "
              "caught lowers F1 (AD = positive) more than balanced accuracy. The 0.5 threshold was fixed in advance "
              "and is not tuned here."]

    # statistics
    L += ["", "## Hybrid vs EEGNet (paired)", ""]
    if {"eegnet", "hybrid"} <= set(models):
        a = folds[folds.model == "hybrid"].set_index(["repeat", "fold"]).sort_index()
        b = folds[folds.model == "eegnet"].set_index(["repeat", "fold"]).sort_index()
        n_test = n_sub / cfg["folds"]
        n_train = n_sub - n_test
        L += ["| Metric | Hybrid − EEGNet, mean (SD) | folds hybrid better / tied / worse | Wilcoxon signed-rank p | "
              "Corrected resampled t-test p |", "|---|---|---|---|---|"]
        for met in ("balanced_accuracy", "auc", "f1"):
            d = (a[met] - b[met]).values
            nz = d[d != 0]
            w = wilcoxon(nz).pvalue if len(nz) >= 1 and np.any(nz) else float("nan")
            tt, tp = corrected_t(d, n_train, n_test)
            L.append(f"| {met.replace('_', ' ')} | {d.mean():+.3f} ({d.std(ddof=1):.3f}) | "
                     f"{(d > 0).sum()} / {(d == 0).sum()} / {(d < 0).sum()} | {w:.3g} | {tp:.3g} (t = {tt:.2f}) |")
        diff = auc_boot["hybrid"] - auc_boot["eegnet"]
        lo, hi = np.percentile(diff, [2.5, 97.5])
        L += ["", f"Pooled AUC difference hybrid − EEGNet: {auc_point['hybrid'] - auc_point['eegnet']:+.3f}, "
              f"paired subject-bootstrap 95% CI [{lo:+.3f}, {hi:+.3f}]; share of resamples with hybrid > EEGNet: "
              f"{(diff > 0).mean():.1%}.", "",
              f"Wilcoxon uses the {len(d)} fold scores (zero differences dropped, two-sided). Folds from different "
              "repeats share subjects, so they are not independent and the plain Wilcoxon p is optimistic; the "
              f"corrected resampled t-test (Nadeau & Bengio 2003, test/train ratio {n_test:.0f}/{n_train:.0f}) "
              "accounts for this and is the more conservative number."]
        # secondary: hybrid vs microstate baseline
        c = folds[folds.model == "baseline_logreg"].set_index(["repeat", "fold"]).sort_index()
        d2 = (a.balanced_accuracy - c.balanced_accuracy).values
        tt2, tp2 = corrected_t(d2, n_train, n_test)
        nz2 = d2[d2 != 0]
        L += ["", f"Secondary (not pre-specified in the task): hybrid − logistic-regression baseline, balanced "
              f"accuracy {d2.mean():+.3f}; Wilcoxon p {wilcoxon(nz2).pvalue if len(nz2) else float('nan'):.3g}; "
              f"corrected t-test p {tp2:.3g}."]

    # leakage
    L += ["", "## Leakage demo vs honest subject-wise evaluation", ""]
    if "leakage_demo_eegnet_window_split" in R:
        lk = R["leakage_demo_eegnet_window_split"]
        e = folds[folds.model == "eegnet"]
        L += ["| Evaluation | Unit | Balanced acc. | AUC | F1 |", "|---|---|---|---|---|",
              f"| EEGNet, windows split at random (same people in train and test) | {lk['n_test_windows']:,} test windows | "
              f"{lk['balanced_accuracy']:.3f} | {lk['auc']:.3f} | {lk['f1']:.3f} |",
              f"| EEGNet, subject-wise CV (this study) | {n_sub} subjects × {cfg['repeats']} repeats | "
              f"{e.balanced_accuracy.mean():.3f} ± {e.balanced_accuracy.std():.3f} | {e.auc.mean():.3f} | {e.f1.mean():.3f} |",
              "", f"The random window split trains {cfg['leak_epochs']} epochs on 80% of all windows (seed 0, no early "
              "stopping) and tests on the remaining 20%, which come from the same people. "
              f"The gap ({lk['balanced_accuracy'] - e.balanced_accuracy.mean():+.3f} balanced accuracy) is what "
              "subject leakage adds; the subject-wise number is the honest estimate."]
    else:
        L.append("Not run (`--skip-leak`).")

    # benchmarks
    L += ["", "## Comparison with published results on ds004504", "",
          "| Study | Reported | Task / protocol | Why not directly comparable |", "|---|---|---|---|"]
    for s, rep, task, why in BENCHMARKS:
        L.append(f"| {s} | {rep} | {task} | {why} |")
    best = max(models, key=lambda m: folds[folds.model == m].balanced_accuracy.mean())
    L += [f"| **This study (highest mean: {best})** | {folds[folds.model == best].balanced_accuracy.mean():.1%} "
          f"balanced acc. | AD vs HC, {cfg['folds']}-fold subject-wise × {cfg['repeats']} | - |", "",
          "Different cohort, not ds004504: Brookshire et al. 2024, 53% -> 99.8% acc., subject-wise vs leaky split, "
          "49 subjects with dementia due to Alzheimer's disease vs 49 with subjective cognitive impairment; "
          "methodological reference only.", "",
          "Corrected on 6 Nov 2026: Brookshire et al. moved out of this ds004504 table.", "",
          "Our protocol differs from all of them: 5-fold (about 52 training subjects per fold) instead of LOSO "
          "(64), balanced accuracy over subjects instead of accuracy or window-level F1, early-stopping subjects "
          "taken from the training fold, and no tuning on test folds. Numbers across protocols should be read "
          "as context, not a ranking."]

    # epochs, runtime, seeds, versions
    L += ["", "## Training details", ""]
    if len(ep):
        L += [f"Epochs actually trained (max {cfg['epochs']}, early stopping patience {cfg['patience']} on "
              "validation-subject loss; the best epoch's weights are kept):", "",
              "| Repeat | Fold | Microstate GEV | EEGNet epochs | Hybrid epochs |", "|---|---|---|---|---|"]
        piv = ep.pivot_table(index=["repeat", "fold", "gev"], columns="model", values="epochs").reset_index()
        for r in piv.itertuples():
            L.append(f"| {r.repeat} | {r.fold} | {r.gev:.3f} | {int(r.eegnet)} | {int(r.hybrid)} |")
        L.append(f"| mean | | {piv.gev.mean():.3f} | {piv.eegnet.mean():.1f} | {piv.hybrid.mean():.1f} |")
        n_cap = int((ep.epochs == cfg["epochs"]).sum())
        L += ["", f"Runs that reached the {cfg['epochs']}-epoch cap without early stopping: {n_cap} of {len(ep)}."]
    L += ["", "| Setting | Value |", "|---|---|"]
    for k in ("folds", "repeats", "epochs", "patience", "crops", "batch", "lr", "wd", "dropout", "leak_epochs", "models"):
        L.append(f"| {k} | {cfg[k]} |")
    L += [f"| seeds | {seeds.get('scheme', 'see results.json')} |",
          f"| fold seeds | {seeds.get('fold_seeds')} |",
          f"| bootstrap | {N_BOOT} resamples, seed {BOOT_SEED} |",
          f"| runtime | {cfg['minutes'] / 60:.2f} h total; {np.mean(ft):.1f} min per fold on average "
          f"(range {np.min(ft):.1f}-{np.max(ft):.1f}) |" if len(ft) else f"| runtime | {cfg['minutes']:.1f} min |",
          f"| environment | Python {env.get('python')}, {env.get('platform')}, device: {cfg.get('device', 'cpu')} |",
          "| libraries | " + ", ".join(f"{k} {v}" for k, v in env.get("libraries", {}).items()) + " |",
          "", "Files: `results.json`, `fold_metrics.csv`, `oof_predictions.csv`, `log.txt` in this folder.", ""]
    out = os.path.join(args.run, "summary.md")
    open(out, "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
