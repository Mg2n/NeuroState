"""Step 2 - Subject-wise comparison of three models on ds004504.

  A. Baseline : microstate features (24 per subject) -> logistic regression / random forest
  B. EEGNet   : EEGNet-style CNN on raw 4-s EEG windows
  C. Hybrid   : EEGNet branch + small microstate CNN branch (our model)

Evaluation: stratified K-fold over SUBJECTS (a subject is never in train and test at once).
Inside each training fold, some subjects are held out for early stopping. Microstate maps are
fitted on training subjects only. Window predictions are averaged into one score per subject.

Also runs a leakage demo: EEGNet with windows split at random (subjects mixed across train/test).

Usage:
    python run_experiment.py --prep /path/to/prepared --out results --groups A C
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import microstates as msx
from models import MicroStateNet

WIN = 512           # 4 s at 128 Hz (set from --win-sec in main)
FS = 128.0          # sampling rate of the prepared data (set in main)
SCALE = 1 / 50.0    # fixed amplitude scaling (no data-dependent normalisation -> no leakage)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def env_info():
    """Python, platform and library versions, saved with every result."""
    import platform
    from importlib.metadata import version
    libs = ["numpy", "pandas", "scipy", "scikit-learn", "torch", "mne", "pycrostates"]
    return {"python": platform.python_version(), "platform": platform.platform(),
            "libraries": {lib: version(lib) for lib in libs}}


def load(prep, groups):
    subs = pd.read_csv(os.path.join(prep, "subjects.csv"))
    subs = subs[subs.Group.isin(groups)].reset_index(drop=True)
    data = {}
    for s in subs.participant_id:
        z = np.load(os.path.join(prep, f"{s}.npz"))
        data[s] = {"dl": z["dl"] * SCALE, "ms": z["ms"], "sfreq": float(z["sfreq"]),
                   "ch": list(z["ch_names"])}
    # class index = K-1-position in --groups: two groups -> 1 = first group (e.g. AD), 0 = second
    y = np.array([len(groups) - 1 - groups.index(g) for g in subs.Group])
    return subs.participant_id.tolist(), y, data


def fold_microstates(train_subs, all_subs, data, seed):
    rng = np.random.default_rng(seed)
    any_s = all_subs[0]
    peaks = [msx.gfp_peaks(data[s]["ms"], rng=rng) for s in train_subs]
    maps, gev = msx.fit_maps(peaks, data[any_s]["ch"], data[any_s]["sfreq"], seed=seed)
    corr, feats = {}, {}
    for s in all_subs:
        c = msx.corr_sequence(data[s]["ms"], maps)
        corr[s] = c
        feats[s] = msx.features(c.argmax(0), data[s]["sfreq"])
    return maps, gev, corr, feats


def windows(arr):
    n = arr.shape[1] // WIN
    return np.stack([arr[:, i * WIN:(i + 1) * WIN] for i in range(n)])


def random_crops(subs, ylab, data, corr, n_crops, rng):
    X, M, Y = [], [], []
    for s, lab in zip(subs, ylab):
        T = data[s]["dl"].shape[1]
        for st in rng.integers(0, T - WIN, n_crops):
            X.append(data[s]["dl"][:, st:st + WIN])
            M.append(corr[s][:, st:st + WIN] if corr is not None else np.zeros((4, WIN), np.float32))
            Y.append(lab)
    return np.stack(X), np.stack(M), np.array(Y)


def win_feats(M, norm=None):
    """24 microstate features per window (labels = argmax of its (4, time) sequence), optionally standardised."""
    F = np.stack([msx.features(m.argmax(0), FS) for m in M]).astype(np.float32)
    return F if norm is None else ((F - norm[0]) / norm[1]).astype(np.float32)


def predict_subject(model, s, data, corr, device="cpu"):
    model.eval()
    xw = torch.from_numpy(windows(data[s]["dl"])).to(device)
    mw = torch.from_numpy(windows(corr[s])).to(device) if corr is not None else None
    norm = getattr(model, "feat_norm", None)
    fw = torch.from_numpy(win_feats(windows(corr[s]), norm)).to(device) if norm is not None else None
    probs = []
    with torch.no_grad():
        for i in range(0, len(xw), 256):
            out = model(xw[i:i + 256], mw[i:i + 256] if mw is not None else None,
                        fw[i:i + 256] if fw is not None else None)
            probs.append(torch.softmax(out, 1))
    return torch.cat(probs).cpu().numpy()


def subject_score(model, s, data, corr, device="cpu"):
    """Mean window probability: P(class 1) with two classes, the probability vector with more."""
    P = predict_subject(model, s, data, corr, device)
    return P[:, 1].mean() if P.shape[1] == 2 else P.mean(0)


def prob_fields(p):
    return {"prob": float(p)} if np.ndim(p) == 0 else {f"prob_{c}": float(v) for c, v in enumerate(p)}


def train_net(use_ms, tr, ytr, va, yva, data, corr, seed, args):
    dev = args.device
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    nf = 24 if (use_ms and args.ms_input == "corr+feats") else 0
    K = len(args.groups)
    model = MicroStateNet(n_times=WIN, n_classes=K, use_ms=use_ms, dropout=args.dropout, n_feats=nf).to(dev)
    model.feat_norm = None
    if nf:  # feature standardisation from the training subjects' windows only
        Ftr = win_feats(np.concatenate([windows(corr[s]) for s in tr]))
        model.feat_norm = (Ftr.mean(0), Ftr.std(0) + 1e-6)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.wd)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    w = torch.tensor([len(ytr) / (K * max((ytr == c).sum(), 1)) for c in range(K)], dtype=torch.float32)
    lossf = nn.CrossEntropyLoss(weight=w.to(dev))
    Xv, Mv, Yv = random_crops(va, yva, data, corr, 64, np.random.default_rng(seed + 999))
    Fv = win_feats(Mv, model.feat_norm) if nf else np.zeros((len(Yv), 1), np.float32)
    Xv, Mv, Yv, Fv = (torch.from_numpy(a).to(dev) for a in (Xv, Mv, Yv, Fv))
    best, best_state, bad = np.inf, None, 0
    for ep in range(args.epochs):
        model.train()
        X, M, Y = random_crops(tr, ytr, data, corr, args.crops, rng)
        X = X * rng.uniform(0.9, 1.1, (len(X), 1, 1)).astype(np.float32)        # amplitude jitter
        X = X + rng.normal(0, 0.05, X.shape).astype(np.float32)                 # small noise
        F = win_feats(M, model.feat_norm) if nf else np.zeros((len(Y), 1), np.float32)
        perm = rng.permutation(len(Y))
        X, M, Y, F = (torch.from_numpy(a[perm]).to(dev) for a in (X, M, Y, F))
        for i in range(0, len(Y), args.batch):
            opt.zero_grad()
            loss = lossf(model(X[i:i + args.batch], M[i:i + args.batch] if use_ms else None,
                               F[i:i + args.batch] if nf else None), Y[i:i + args.batch])
            loss.backward()
            opt.step()
        sched.step()
        model.eval()
        with torch.no_grad():
            vl = float(np.mean([lossf(model(Xv[i:i + 256], Mv[i:i + 256] if use_ms else None,
                                            Fv[i:i + 256] if nf else None),
                                      Yv[i:i + 256]).item() for i in range(0, len(Yv), 256)]))
        if vl < best - 1e-4:
            best, bad = vl, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= args.patience:
                break
    model.load_state_dict(best_state)
    return model, ep + 1


REG_GRID = [(0.5, 1e-3), (0.5, 1e-4), (0.25, 1e-3), (0.25, 1e-4)]  # (dropout, weight decay); default first


def select_reg(models, tr, ytr, data, seed, args):
    """Nested selection on TRAINING subjects only: inner 3-fold CV, maps refitted on each inner-train set.
    Score = mean inner-test subject AUC; ties go to the earlier grid entry (the default setting comes first)."""
    inner = StratifiedKFold(3, shuffle=True, random_state=seed)
    rows = []
    for j, (a, b) in enumerate(inner.split(tr, ytr)):
        itr, ite = [tr[i] for i in a], [tr[i] for i in b]
        _, _, icorr, _ = fold_microstates(itr, itr + ite, data, seed + 1000 + j)
        tr2, va, ytr2, yva = train_test_split(itr, ytr[a], test_size=0.15, stratify=ytr[a], random_state=seed + j)
        for name, use_ms in models:
            for dropout, wd in REG_GRID:
                cfg = argparse.Namespace(**{**vars(args), "dropout": dropout, "wd": wd})
                model, n_ep = train_net(use_ms, tr2, ytr2, va, yva, data, icorr, seed + 10000 + j, cfg)
                p = [subject_score(model, s, data, icorr, args.device) for s in ite]
                rows.append({"model": name, "inner_fold": j, "dropout": dropout, "wd": wd,
                             "inner_auc": roc_auc_score(ytr[b], p), "epochs": n_ep})
    rows = pd.DataFrame(rows)
    chosen = {}
    for name, _ in models:
        means = [rows[(rows.model == name) & (rows.dropout == d) & (rows.wd == w)].inner_auc.mean() for d, w in REG_GRID]
        chosen[name] = REG_GRID[int(np.argmax(means))]
    return chosen, rows


def metrics(y, p):
    if np.ndim(p) == 2:  # more than two classes: macro-F1 and macro one-vs-rest AUC
        pred = p.argmax(1)
        return {"balanced_accuracy": balanced_accuracy_score(y, pred),
                "accuracy": float(np.mean(pred == y)),
                "f1": f1_score(y, pred, average="macro"),
                "auc": roc_auc_score(y, p / p.sum(1, keepdims=True), multi_class="ovr", average="macro")}
    pred = (p >= 0.5).astype(int)
    return {"balanced_accuracy": balanced_accuracy_score(y, pred),
            "accuracy": float(np.mean(pred == y)),
            "f1": f1_score(y, pred),
            "auc": roc_auc_score(y, p) if len(set(y)) == 2 else float("nan")}


def leakage_demo(subs, y, data, args):
    """EEGNet trained/tested on windows split at RANDOM: the same people appear in both sets."""
    X, Y = [], []
    for s, lab in zip(subs, y):
        w = windows(data[s]["dl"])
        X.append(w)
        Y += [lab] * len(w)
    X, Y = np.concatenate(X), np.array(Y)
    Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=0, stratify=Y)
    dev = args.device
    torch.manual_seed(0)
    model = MicroStateNet(n_times=WIN, use_ms=False, dropout=args.dropout).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.wd)
    lossf = nn.CrossEntropyLoss()
    rng = np.random.default_rng(0)
    Xtr_t, Ytr_t = torch.from_numpy(Xtr), torch.from_numpy(Ytr)
    for ep in range(args.leak_epochs):
        model.train()
        perm = torch.from_numpy(rng.permutation(len(Ytr)))
        for i in range(0, len(Ytr), args.batch):
            idx = perm[i:i + args.batch]
            opt.zero_grad()
            lossf(model(Xtr_t[idx].to(dev)), Ytr_t[idx].to(dev)).backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        p = torch.cat([torch.softmax(model(torch.from_numpy(Xte[i:i + 256]).to(dev)), 1)[:, 1]
                       for i in range(0, len(Xte), 256)]).cpu().numpy()
    m = metrics(Yte, p)
    m["n_test_windows"] = int(len(Yte))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--groups", nargs="+", default=["A", "C"], help="2 groups (positive first) or 3 groups")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--crops", type=int, default=64, help="random 4-s crops per subject per epoch")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--wd", type=float, default=1e-3)
    ap.add_argument("--dropout", type=float, default=0.5)
    ap.add_argument("--leak-epochs", type=int, default=15)
    ap.add_argument("--skip-leak", action="store_true")
    ap.add_argument("--models", nargs="+", default=["baseline", "eegnet", "hybrid"])
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--seed-offset", type=int, default=0, help="added to the network training seed only")
    ap.add_argument("--win-sec", type=float, default=4.0, help="window / crop length in seconds")
    ap.add_argument("--ms-input", default="corr", choices=["corr", "onehot", "corr+feats"],
                    help="hybrid microstate branch input: |correlation| sequence, one-hot labels, "
                         "or |correlation| plus 24 window-level features through a small MLP")
    ap.add_argument("--reg-grid", action="store_true",
                    help="choose dropout / weight decay per outer fold by nested inner CV on training subjects")
    ap.add_argument("--reg-choices", help="reuse the choices of an earlier --reg-grid run (reg_choices.csv)")
    args = ap.parse_args()
    K = len(args.groups)
    assert K in (2, 3) and (K == 2 or not (args.reg_grid or args.reg_choices)), "--reg-* needs two groups"
    os.makedirs(args.out, exist_ok=True)
    torch.set_num_threads(os.cpu_count())
    t0 = time.time()

    subs, y, data = load(args.prep, args.groups)
    global WIN, FS
    FS = data[subs[0]]["sfreq"]
    WIN = int(round(args.win_sec * FS))
    log(f"{len(subs)} subjects: " + ", ".join(f"{(y == K - 1 - i).sum()} {g}" for i, g in enumerate(args.groups)))
    oof_rows, fold_rows, val_rows, reg_rows, inner_rows = [], [], [], [], []
    saved_reg = pd.read_csv(args.reg_choices) if args.reg_choices else None

    for rep in range(args.repeats):
        skf = StratifiedKFold(args.folds, shuffle=True, random_state=rep)
        for fold, (tr_i, te_i) in enumerate(skf.split(subs, y)):
            seed = 100 * rep + fold
            tr = [subs[i] for i in tr_i]
            te = [subs[i] for i in te_i]
            ytr, yte = y[tr_i], y[te_i]
            maps, gev, corr, feats = fold_microstates(tr, subs, data, seed)
            if args.ms_input == "onehot":  # hybrid branch sees hard labels instead of |correlation|
                corr = {s: np.eye(4, dtype=np.float32)[c.argmax(0)].T.copy() for s, c in corr.items()}
            log(f"rep {rep} fold {fold}: maps fitted (GEV {gev:.3f}), "
                f"{len(tr)} train / {len(te)} test subjects")

            preds = {}
            if "baseline" in args.models:
                Ftr = np.stack([feats[s] for s in tr])
                Fte = np.stack([feats[s] for s in te])
                lr = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, class_weight="balanced",
                                                                        max_iter=5000))
                rf = RandomForestClassifier(500, class_weight="balanced", random_state=seed,
                                            min_samples_leaf=2)
                pl, pf = lr.fit(Ftr, ytr).predict_proba(Fte), rf.fit(Ftr, ytr).predict_proba(Fte)
                preds["baseline_logreg"] = pl[:, 1] if K == 2 else pl
                preds["baseline_rf"] = pf[:, 1] if K == 2 else pf

            # inner split of training subjects for early stopping
            tr2, va, ytr2, yva = train_test_split(tr, ytr, test_size=0.15, stratify=ytr,
                                                  random_state=seed)
            nets = [(n, u) for n, u in (("eegnet", False), ("hybrid", True)) if n in args.models]
            chosen = {}
            if args.reg_grid:
                chosen, inner = select_reg(nets, tr, ytr, data, seed, args)
                inner_rows.append(inner.assign(repeat=rep, fold=fold))
            elif saved_reg is not None:
                sel = saved_reg[(saved_reg.repeat == rep) & (saved_reg.fold == fold)]
                chosen = {r.model: (r.dropout, r.wd) for r in sel.itertuples()}
            for name, use_ms in nets:
                cfg = args
                if chosen:
                    d, w = chosen[name]
                    cfg = argparse.Namespace(**{**vars(args), "dropout": d, "wd": w})
                    reg_rows.append({"repeat": rep, "fold": fold, "model": name, "dropout": d, "wd": w})
                    log(f"   {name}: dropout {d}, weight decay {w}")
                # --seed-offset changes only network training; maps and inner split stay on the fold seed
                model, n_ep = train_net(use_ms, tr2, ytr2, va, yva, data, corr, seed + args.seed_offset, cfg)
                preds[name] = np.array([subject_score(model, s, data, corr, args.device) for s in te])
                # inner-validation subjects (training fold only), saved for threshold selection
                for s, lab in zip(va, yva):
                    val_rows.append({"repeat": rep, "fold": fold, "model": name, "subject": s, "label": int(lab),
                                     **prob_fields(subject_score(model, s, data, corr, args.device))})
                log(f"   {name}: trained {n_ep} epochs")

            for name, p in preds.items():
                m = metrics(yte, p)
                fold_rows.append({"repeat": rep, "fold": fold, "model": name, **m})
                log(f"   {name:16s} bal.acc {m['balanced_accuracy']:.3f}")
                for s, lab, pp in zip(te, yte, p):
                    oof_rows.append({"repeat": rep, "fold": fold, "model": name,
                                     "subject": s, "label": int(lab), **prob_fields(pp)})

    oof = pd.DataFrame(oof_rows)
    folds = pd.DataFrame(fold_rows)
    oof.to_csv(os.path.join(args.out, "oof_predictions.csv"), index=False)
    folds.to_csv(os.path.join(args.out, "fold_metrics.csv"), index=False)
    if val_rows:
        pd.DataFrame(val_rows).to_csv(os.path.join(args.out, "val_predictions.csv"), index=False)
    if reg_rows:
        pd.DataFrame(reg_rows).to_csv(os.path.join(args.out, "reg_choices.csv"), index=False)
    if inner_rows:
        pd.concat(inner_rows).to_csv(os.path.join(args.out, "reg_inner_scores.csv"), index=False)

    summary = {}
    for name, g in oof.groupby("model"):
        cols = ["prob"] if K == 2 else [f"prob_{c}" for c in range(K)]
        per_rep = [metrics(gg.label.values, gg[cols].values.squeeze()) for _, gg in g.groupby("repeat")]
        f = folds[folds.model == name]
        summary[name] = {
            "pooled_balanced_accuracy": float(np.mean([m["balanced_accuracy"] for m in per_rep])),
            "pooled_auc": float(np.mean([m["auc"] for m in per_rep])),
            "pooled_f1": float(np.mean([m["f1"] for m in per_rep])),
            "fold_balanced_accuracy_mean": float(f.balanced_accuracy.mean()),
            "fold_balanced_accuracy_sd": float(f.balanced_accuracy.std()),
        }
    if not args.skip_leak and K == 2:
        log("leakage demo (random window split)...")
        summary["leakage_demo_eegnet_window_split"] = leakage_demo(subs, y, data, args)
    summary["_config"] = {**vars(args), "n_subjects": len(subs), "minutes": (time.time() - t0) / 60}
    summary["_seeds"] = {
        "scheme": "outer split StratifiedKFold random_state=repeat; per-fold seed=100*repeat+fold "
                  "(microstate fit, RF, inner early-stopping split, torch/numpy in training); "
                  "leakage demo seed=0",
        "outer_split_random_state": list(range(args.repeats)),
        "fold_seeds": [100 * rep + fold for rep in range(args.repeats) for fold in range(args.folds)],
        "network_seed_offset": args.seed_offset,
        "leakage_demo": 0,
    }
    summary["_environment"] = env_info()
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=float)
    log(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
