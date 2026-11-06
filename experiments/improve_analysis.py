"""Task 06: improvements that need no retraining, computed from saved out-of-fold predictions.

  fusion    : 0.5 * EEGNet + 0.5 * baseline logistic regression probability (weights fixed in advance), threshold 0.5
  threshold : per outer fold, a decision threshold chosen on that fold's inner-validation subjects only
              (val_predictions.csv; they are training-fold subjects held out for early stopping), then applied
              unchanged to the test subjects. Rule fixed in advance: candidates = 0.5 and the midpoints between
              the sorted validation scores; keep the highest validation balanced accuracy; ties -> closest to 0.5.
  ensemble  : mean subject probability of 5 network seeds per fold (ensemble size fixed in advance); seed k adds
              1000*k to the network training seed only, so microstate maps and inner splits are unchanged; the
              threshold rule above is also applied to the averaged validation-subject probabilities.
  variant   : a changed setting (window length, microstate branch input, ...) run with the same 5 seed offsets;
              its 5-seed ensemble is compared with the reference 5-seed ensemble (threshold 0.5, nothing tuned).

Every variant is compared with the hybrid and EEGNet of the SAME run (same device, same splits):
paired fold differences, Wilcoxon signed-rank and Nadeau-Bengio corrected resampled t-test.

  .venv/bin/python improve_analysis.py --exp fusion --runs ../results/main_AD_vs_HC ../results/improve_mps_rerun
  .venv/bin/python improve_analysis.py --exp threshold --runs ../results/improve_mps_rerun
  .venv/bin/python improve_analysis.py --exp ensemble --runs ../results/improve_mps_rerun ../results/improve_seed{1..4}
  .venv/bin/python improve_analysis.py --exp variant --name win8 --runs <5 reference seed runs> \
      --variant-runs ../results/improve_win8_seed{0..4}
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score

from run_experiment import env_info
from summarize_main import BOOT_SEED, N_BOOT, boot_auc, corrected_t

N_TRAIN, N_TEST = 52, 13  # subjects per outer fold (65 subjects, 5 folds)


def choose_threshold(y, p):
    """Fixed rule: best validation balanced accuracy over {0.5} + midpoints; ties -> closest to 0.5."""
    s = np.unique(p)
    cands = np.r_[0.5, (s[:-1] + s[1:]) / 2] if len(s) > 1 else np.array([0.5])
    scores = np.array([balanced_accuracy_score(y, (p >= t).astype(int)) for t in cands])
    best = cands[scores >= scores.max() - 1e-12]
    return float(best[np.argmin(np.abs(best - 0.5))]), float(scores.max())


def fold_metrics(oof):
    """oof needs repeat, fold, model, label, prob, thr -> one row per (repeat, fold, model)."""
    rows = []
    for (r, f, m), g in oof.groupby(["repeat", "fold", "model"]):
        pred = (g.prob >= g.thr).astype(int)
        rows.append({"repeat": r, "fold": f, "model": m, "threshold": float(g.thr.iloc[0]),
                     "balanced_accuracy": balanced_accuracy_score(g.label, pred),
                     "f1": f1_score(g.label, pred), "auc": roc_auc_score(g.label, g.prob),
                     "sensitivity": float((pred[g.label == 1] == 1).mean()),
                     "specificity": float((pred[g.label == 0] == 0).mean())})
    return pd.DataFrame(rows)


def paired(folds, a, b, metric):
    x = folds[folds.model == a].set_index(["repeat", "fold"]).sort_index()[metric]
    y = folds[folds.model == b].set_index(["repeat", "fold"]).sort_index()[metric]
    d = (x - y).values
    nz = d[np.abs(d) > 1e-12]
    pw = wilcoxon(nz).pvalue if len(nz) > 0 else float("nan")
    t, pt = corrected_t(d, N_TRAIN, N_TEST)
    return {"diff_mean": float(d.mean()), "diff_sd": float(d.std(ddof=1)), "better": int((d > 1e-12).sum()),
            "tied": int((np.abs(d) <= 1e-12).sum()), "worse": int((d < -1e-12).sum()),
            "wilcoxon_p": float(pw), "corrected_t": t, "corrected_p": pt}


def val_thresholds(val, models):
    """Per (repeat, fold, model): threshold from the inner-validation subjects with the fixed rule."""
    rows = []
    for m in models:
        for (r, f), g in val[val.model == m].groupby(["repeat", "fold"]):
            t, vb = choose_threshold(g.label.values, g.prob.values)
            rows.append({"repeat": r, "fold": f, "model": f"{m}_valthr", "thr": t, "val_bal_acc": vb,
                         "n_val": len(g), "n_val_ad": int(g.label.sum())})
    return pd.DataFrame(rows)


def apply_thresholds(oof, thr, models):
    out = []
    for m in models:
        sub = oof[oof.model == m].copy()
        sub["model"] = f"{m}_valthr"
        out.append(sub.drop(columns="thr").merge(thr[["repeat", "fold", "model", "thr"]],
                                                 on=["repeat", "fold", "model"]))
    return pd.concat([oof] + out, ignore_index=True)


def ens_probs(runs, fname, prefix=""):
    """Mean subject probability of eegnet / hybrid over the seed runs -> models '<prefix><model>_ens<n>'."""
    key = ["repeat", "fold", "model", "subject", "label"]
    allp = pd.concat([pd.read_csv(os.path.join(r, fname)).assign(seed_run=i) for i, r in enumerate(runs)])
    allp = allp[allp.model.isin(["eegnet", "hybrid"])]
    n = allp.groupby(key).seed_run.nunique()
    assert (n == len(runs)).all(), f"{fname}: not every subject has all {len(runs)} seeds"
    g = allp.groupby(key).prob.mean().reset_index()
    g["model"] = prefix + g.model + f"_ens{len(runs)}"
    return g


def same_splits(runs_a, runs_b):
    """Baseline probabilities depend only on the outer split and fold seed -> must be identical."""
    ref = pd.read_csv(os.path.join(runs_a[0], "oof_predictions.csv"))
    ref = ref[ref.model == "baseline_logreg"].set_index(["repeat", "fold", "subject"]).prob.sort_index()
    for r in list(runs_a) + list(runs_b):
        o = pd.read_csv(os.path.join(r, "oof_predictions.csv"))
        o = o[o.model == "baseline_logreg"].set_index(["repeat", "fold", "subject"]).prob.sort_index()
        assert o.index.equals(ref.index) and np.allclose(o.values, ref.values), f"{r}: splits differ"


def ensemble(runs):
    """Seed ensemble: mean subject probability over the seed runs (runs[0] = seed offset 0 = reference run)."""
    oof = pd.read_csv(os.path.join(runs[0], "oof_predictions.csv"))
    oof["thr"] = 0.5
    ens, ens_val = ens_probs(runs, "oof_predictions.csv").assign(thr=0.5), ens_probs(runs, "val_predictions.csv")
    oof = pd.concat([oof, ens], ignore_index=True)
    names = [f"eegnet_ens{len(runs)}", f"hybrid_ens{len(runs)}"]
    thr = val_thresholds(ens_val, names)
    thr.to_csv(os.path.join(args.out, "thresholds_ensemble.csv"), index=False)
    oof = apply_thresholds(oof, thr, names)
    e, h = names
    new = names + [f"{e}_valthr", f"{h}_valthr"]
    pairs = [(h, e), (e, "eegnet"), (h, "hybrid"), (f"{e}_valthr", e), (f"{h}_valthr", h)]
    return oof, new, pairs


def variant(ref_runs, var_runs, name):
    """Variant seed ensemble vs reference seed ensemble, same splits and seed offsets; threshold 0.5."""
    same_splits(ref_runs, var_runs)
    oof = pd.read_csv(os.path.join(ref_runs[0], "oof_predictions.csv"))
    oof["thr"] = 0.5
    ref = ens_probs(ref_runs, "oof_predictions.csv")
    var = ens_probs(var_runs, "oof_predictions.csv", prefix=f"{name}_")
    oof = pd.concat([oof, ref.assign(thr=0.5), var.assign(thr=0.5)], ignore_index=True)
    re, rh = f"eegnet_ens{len(ref_runs)}", f"hybrid_ens{len(ref_runs)}"
    ve, vh = f"{name}_eegnet_ens{len(var_runs)}", f"{name}_hybrid_ens{len(var_runs)}"
    has_e = ve in set(var.model)
    pairs = [(vh, rh), (vh, re)] + ([(ve, re), (vh, ve)] if has_e else [])
    new = [re, rh] + ([ve] if has_e else []) + [vh]
    return oof, new, pairs


def seed_spread(runs):
    """Single-seed results of every run: shows how much one training seed moves the numbers."""
    rows = []
    for i, r in enumerate(runs):
        f = pd.read_csv(os.path.join(r, "fold_metrics.csv"))
        cfg = json.load(open(os.path.join(r, "results.json")))
        off = cfg.get("_seeds", {}).get("network_seed_offset", 0)
        h = f[f.model == "hybrid"].set_index(["repeat", "fold"]).sort_index()
        row = {"run": os.path.basename(r), "seed_offset": off, "eegnet_bal_acc": np.nan,
               "hybrid_bal_acc": h.balanced_accuracy.mean(), "eegnet_auc": np.nan, "hybrid_auc": h.auc.mean(),
               "hybrid_minus_eegnet_bal_acc": np.nan, "corrected_p": np.nan}
        if (f.model == "eegnet").any():  # variants that only retrain the hybrid have no EEGNet
            e = f[f.model == "eegnet"].set_index(["repeat", "fold"]).sort_index()
            d = (h.balanced_accuracy - e.balanced_accuracy).values
            row.update(eegnet_bal_acc=e.balanced_accuracy.mean(), eegnet_auc=e.auc.mean(),
                       hybrid_minus_eegnet_bal_acc=d.mean(), corrected_p=corrected_t(d, N_TRAIN, N_TEST)[1])
        rows.append(row)
    return pd.DataFrame(rows)


def variants(run, exp):
    """Return (oof with a thr column, new model names, (variant, reference) pairs) for one source run."""
    oof = pd.read_csv(os.path.join(run, "oof_predictions.csv"))
    oof["thr"] = 0.5
    new = []
    if exp == "fusion":
        key = ["repeat", "fold", "subject", "label"]
        e = oof[oof.model == "eegnet"].set_index(key).prob
        lr = oof[oof.model == "baseline_logreg"].set_index(key).prob
        fused = (0.5 * e + 0.5 * lr.loc[e.index]).reset_index()
        fused["model"], fused["thr"] = "fusion_eegnet_logreg", 0.5
        oof = pd.concat([oof, fused], ignore_index=True)
        new = ["fusion_eegnet_logreg"]
    elif exp == "threshold":
        val = pd.read_csv(os.path.join(run, "val_predictions.csv"))
        thr = val_thresholds(val, ("eegnet", "hybrid"))
        thr.to_csv(os.path.join(args.out, f"thresholds_{os.path.basename(run)}.csv"), index=False)
        oof = apply_thresholds(oof, thr, ("eegnet", "hybrid"))
        new = ["eegnet_valthr", "hybrid_valthr"]
    return oof, new, [(m, ref) for m in new for ref in ("hybrid", "eegnet")]


def section(run, oof, new, pairs, rng):
    folds = fold_metrics(oof)
    base = [m for m in ("baseline_logreg", "eegnet", "hybrid") if m in folds.model.unique()]
    models = base + new
    point, boot = boot_auc(oof[["repeat", "subject", "label", "prob", "model"]], models, rng)
    run_cfg = json.load(open(os.path.join(run, "results.json")))["_config"]
    dev = run_cfg.get("device", "cpu")
    L = [f"## Source run: `{os.path.relpath(run, os.path.dirname(args.out))}` (device: {dev})", "",
         "| Model | Balanced acc. (mean ± SD, 15 folds) | AUC | F1 | Sensitivity (fold mean) | Specificity (fold mean) | "
         "Pooled AUC [95% CI] |", "|---|---|---|---|---|---|---|"]
    for m in models:
        f = folds[folds.model == m]
        lo, hi = np.percentile(boot[m], [2.5, 97.5])
        L.append(f"| {m} | {f.balanced_accuracy.mean():.3f} ± {f.balanced_accuracy.std():.3f} | "
                 f"{f.auc.mean():.3f} ± {f.auc.std():.3f} | {f.f1.mean():.3f} ± {f.f1.std():.3f} | "
                 f"{f.sensitivity.mean():.3f} | {f.specificity.mean():.3f} | {point[m]:.3f} [{lo:.3f}, {hi:.3f}] |")
    L += ["", "Paired comparison over the 15 folds (difference = variant − reference; same run, same splits):", "",
          "| Variant | Reference | Metric | Diff. mean (SD) | better / tied / worse | Wilcoxon p | "
          "Corrected t-test p |", "|---|---|---|---|---|---|---|"]
    stats = {}
    for m, ref in pairs:
        for metric in ("balanced_accuracy", "auc", "f1"):
            if metric == "auc" and m.endswith("_valthr"):
                continue  # threshold does not change the ranking
            s = paired(folds, m, ref, metric)
            stats[f"{m}_vs_{ref}_{metric}"] = s
            L.append(f"| {m} | {ref} | {metric} | {s['diff_mean']:+.3f} ({s['diff_sd']:.3f}) | "
                     f"{s['better']} / {s['tied']} / {s['worse']} | {s['wilcoxon_p']:.3g} | "
                     f"{s['corrected_p']:.3g} |")
    folds["source_run"] = os.path.basename(run)
    return L, folds, stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True, choices=["fusion", "threshold", "ensemble", "variant"])
    ap.add_argument("--runs", nargs="+", required=True, help="source runs; for 'variant' the reference seed runs")
    ap.add_argument("--variant-runs", nargs="+", help="'variant' only: the variant's seed runs (same seed offsets)")
    ap.add_argument("--name", help="'variant' only: short name, e.g. win8")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    args.out = args.out or f"../results/improve_{args.name if args.exp == 'variant' else args.exp}"
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(BOOT_SEED)
    title = {"fusion": "Late fusion: 0.5 × EEGNet + 0.5 × logistic-regression baseline (fixed weights, threshold 0.5)",
             "threshold": "Decision threshold chosen on inner-validation subjects of each training fold",
             "ensemble": f"Seed ensemble: {len(args.runs)} network seeds per fold, probabilities averaged",
             "variant": f"Variant `{args.name}` vs reference, both as {len(args.runs)}-seed ensembles"}[args.exp]
    L = [f"# {title}", "", (__doc__.split("\n\n")[1]), "",
         f"AUC CI: subject bootstrap ({N_BOOT} resamples, seed {BOOT_SEED}). Corrected t-test: Nadeau & Bengio "
         f"(2003), test/train ratio {N_TEST}/{N_TRAIN}. Research use only: classification, not diagnosis.", ""]
    all_folds, all_stats = [], {}
    def spread_table(runs, label, csv):
        sp = seed_spread(runs)
        sp.to_csv(os.path.join(args.out, csv), index=False)
        f = lambda v, fmt: "–" if pd.isna(v) else format(v, fmt)
        T = [f"## Single seeds: {label} (each run alone, fold mean of 15 folds)", "",
             "| Run | Network seed offset | EEGNet bal. acc. | Hybrid bal. acc. | EEGNet AUC | Hybrid AUC | "
             "Hybrid − EEGNet bal. acc. | Corrected t-test p |", "|---|---|---|---|---|---|---|---|"]
        for _, r in sp.iterrows():
            T.append(f"| {r.run} | {r.seed_offset} | {f(r.eegnet_bal_acc, '.3f')} | {r.hybrid_bal_acc:.3f} | "
                     f"{f(r.eegnet_auc, '.3f')} | {r.hybrid_auc:.3f} | {f(r.hybrid_minus_eegnet_bal_acc, '+.3f')} | "
                     f"{f(r.corrected_p, '.3g')} |")
        ms = lambda c, fmt=".3f": "–" if sp[c].isna().all() else f"{sp[c].mean():{fmt}} ± {sp[c].std():.3f}"
        T.append(f"| **mean ± SD over seeds** | | {ms('eegnet_bal_acc')} | {ms('hybrid_bal_acc')} | "
                 f"{ms('eegnet_auc')} | {ms('hybrid_auc')} | {ms('hybrid_minus_eegnet_bal_acc', '+.3f')} | |")
        return T + [""]

    if args.exp == "variant":
        L += spread_table(args.variant_runs, f"variant `{args.name}`", "seed_spread_variant.csv")
        L += spread_table(args.runs, "reference (4-s windows, |correlation| input)", "seed_spread_reference.csv")
        L += ["Reference single-seed models below (`eegnet`, `hybrid`, `baseline_logreg`) are the seed-offset-0 "
              "reference run. `*_ens5` = mean probability over the 5 seeds; variant and reference use the same "
              "outer splits, fold seeds, inner early-stopping subjects and network seed offsets "
              "(checked: identical baseline probabilities).", ""]
        sec, folds, stats = section(args.runs[0], *variant(args.runs, args.variant_runs, args.name), rng)
        L += sec + [""]
        all_folds.append(folds)
        all_stats["variant"] = stats
    elif args.exp == "ensemble":
        L += spread_table(args.runs, "5 network seeds", "seed_spread.csv")
        L += ["Reference single-seed models below (`eegnet`, `hybrid`, `baseline_logreg`) are the seed-offset-0 "
              "run; every comparison uses the same splits.", ""]
        sec, folds, stats = section(args.runs[0], *ensemble(args.runs), rng)
        L += sec + [""]
        all_folds.append(folds)
        all_stats["ensemble"] = stats
        t = pd.read_csv(os.path.join(args.out, "thresholds_ensemble.csv"))
        L += ["Chosen ensemble thresholds: "
              + "; ".join(f"{m}: median {g.thr.median():.3f}, range {g.thr.min():.3f}-{g.thr.max():.3f}, "
                          f"left at 0.5 in {int((g.thr == 0.5).sum())}/15 folds" for m, g in t.groupby("model")), ""]
    else:
        for run in args.runs:
            sec, folds, stats = section(run, *variants(run, args.exp), rng)
            L += sec + [""]
            all_folds.append(folds)
            all_stats[os.path.basename(run)] = stats
    if args.exp == "threshold":
        for run in args.runs:
            t = pd.read_csv(os.path.join(args.out, f"thresholds_{os.path.basename(run)}.csv"))
            L += [f"Chosen thresholds ({os.path.basename(run)}): "
                  + "; ".join(f"{m}: median {g.thr.median():.3f}, range {g.thr.min():.3f}-{g.thr.max():.3f}, "
                              f"left at 0.5 in {int((g.thr == 0.5).sum())}/15 folds"
                              for m, g in t.groupby("model"))
                  + f". Validation subjects per fold: {t.n_val.min()}-{t.n_val.max()} "
                    f"({t.n_val_ad.min()}-{t.n_val_ad.max()} AD).", ""]
    pd.concat(all_folds).to_csv(os.path.join(args.out, "fold_metrics.csv"), index=False)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump({"experiment": args.exp, "rule": __doc__.split("\n\n")[1], "source_runs": args.runs,
                   "stats": all_stats, "bootstrap": {"n": N_BOOT, "seed": BOOT_SEED},
                   "created": time.strftime("%Y-%m-%d %H:%M"), "_environment": env_info()}, fh, indent=2)
    with open(os.path.join(args.out, "summary.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
