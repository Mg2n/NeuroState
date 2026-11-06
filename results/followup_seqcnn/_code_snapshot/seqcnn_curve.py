"""Task 09 learning curve: seq-CNN vs logistic regression on nested, class-stratified training subsets.

Fixed in results/followup_seqcnn/PREREGISTERED.md. Primary labels only. Test subjects stay those of the outer fold; maps,
features and network are fitted on the subset only. The full-fold point comes from the main runs.

  .venv/bin/python seqcnn_curve.py --prep ../prepared --out ../results/followup_seqcnn/curve --device mps
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import run_experiment as rx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sizes", nargs="+", type=int, default=[20, 35])
    ap.add_argument("--draws", type=int, default=5)
    ap.add_argument("--seed-offsets", nargs="+", type=int, default=[0, 1000, 2000, 3000, 4000])
    ap.add_argument("--first-repeat", type=int, default=3)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--crops", type=int, default=64)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--wd", type=float, default=1e-3)
    ap.add_argument("--dropout", type=float, default=0.5)
    args = ap.parse_args()
    assert args.sizes == sorted(args.sizes)
    os.makedirs(args.out, exist_ok=True)
    torch.set_num_threads(os.cpu_count())
    t0 = time.time()
    cfg = argparse.Namespace(**vars(args), groups=["A", "C"], ms_input="onehot")

    subs, y, data = rx.load(args.prep, cfg.groups)
    rx.FS = data[subs[0]]["sfreq"]
    rx.WIN = int(round(4.0 * rx.FS))
    rows, subset_rows, epoch_rows = [], [], []
    for rep in range(args.first_repeat, args.first_repeat + args.repeats):
        skf = StratifiedKFold(args.folds, shuffle=True, random_state=rep)
        for fold, (tr_i, te_i) in enumerate(skf.split(subs, y)):
            fold_seed = 100 * rep + fold
            te, yte = [subs[i] for i in te_i], y[te_i]
            ad = [subs[i] for i in tr_i if y[i] == 1]
            hc = [subs[i] for i in tr_i if y[i] == 0]
            for draw in range(args.draws):
                rng = np.random.default_rng(910000 + 1000 * rep + 10 * fold + draw)
                ad_o, hc_o = [str(s) for s in rng.permutation(ad)], [str(s) for s in rng.permutation(hc)]
                for size_i, size in enumerate(args.sizes):
                    n_ad = round(size * len(ad) / len(tr_i))
                    sub = ad_o[:n_ad] + hc_o[:size - n_ad]
                    ysub = np.array([1] * n_ad + [0] * (size - n_ad))
                    assert len(sub) == size and min(n_ad, size - n_ad) >= 2, f"too few subjects: {rep} {fold} {size}"
                    s = fold_seed + 100000 * (draw + 1) + 10000 * size_i
                    _, gev, corr, feats = rx.fold_microstates(sub, subs, data, s)
                    corr = {k: np.eye(4, dtype=np.float32)[c.argmax(0)].T.copy() for k, c in corr.items()}
                    lr = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, class_weight="balanced", max_iter=5000))
                    pl = lr.fit(np.stack([feats[k] for k in sub]), ysub).predict_proba(np.stack([feats[k] for k in te]))[:, 1]
                    tr2, va, ytr2, yva = train_test_split(sub, ysub, test_size=0.15, stratify=ysub, random_state=s)
                    assert set(ytr2) == set(yva) == {0, 1}, f"class missing in early-stopping split: {rep} {fold} {size}"
                    for k, lab, pp in zip(te, yte, pl):
                        rows.append({"repeat": rep, "fold": fold, "draw": draw, "size": size, "seed_offset": -1,
                                     "model": "logreg", "subject": k, "label": int(lab), "prob": float(pp)})
                    for k in sub:
                        subset_rows.append({"repeat": rep, "fold": fold, "draw": draw, "size": size, "subject": k,
                                            "early_stopping": k in va})
                    for offset in args.seed_offsets:
                        model, n_ep = rx.train_net(True, tr2, ytr2, va, yva, data, corr, s + offset, cfg, use_eeg=False)
                        for k, lab in zip(te, yte):
                            rows.append({"repeat": rep, "fold": fold, "draw": draw, "size": size, "seed_offset": offset,
                                         "model": "seqcnn", "subject": k, "label": int(lab),
                                         "prob": float(rx.subject_score(model, k, data, corr, args.device))})
                        epoch_rows.append({"repeat": rep, "fold": fold, "draw": draw, "size": size,
                                           "seed_offset": offset, "epochs": n_ep})
                    rx.log(f"rep {rep} fold {fold} draw {draw} size {size}: GEV {gev:.3f}, {n_ad} AD + {size - n_ad} HC")
            # saved after every fold, so a crash leaves a record of what ran
            pd.DataFrame(rows).to_csv(os.path.join(args.out, "curve_predictions.csv"), index=False)
            pd.DataFrame(subset_rows).to_csv(os.path.join(args.out, "subsets.csv"), index=False)
            pd.DataFrame(epoch_rows).to_csv(os.path.join(args.out, "epochs.csv"), index=False)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump({"_config": {**vars(args), "minutes": (time.time() - t0) / 60},
                   "_seeds": {"shuffle": "default_rng(910000 + 1000*repeat + 10*fold + draw)",
                              "subset": "s = 100*repeat + fold + 100000*(draw + 1) + 10000*size_index",
                              "network": "s + seed_offset"},
                   "_environment": rx.env_info()}, fh, indent=2)
    rx.log("done")


if __name__ == "__main__":
    main()
