"""Task 09 check on real labels, no training: mean visit length with and without the preregistered smoothing rule.

Maps are fitted as in the main runs (repeats 3-5, each training fold). A subject's value is the mean run length over its whole
recording, averaged over the 15 folds. Reports these numbers only; they do not change the preregistered rule.

  .venv/bin/python seqcnn_visit_lengths.py --prep ../prepared --out ../results/followup_seqcnn/visit_lengths.md
"""
import argparse
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

import microstates as msx
import run_experiment as rx


def mean_run(labels):
    return len(labels) / (np.count_nonzero(np.diff(labels)) + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-segment", type=int, default=4)
    args = ap.parse_args()
    subs, y, data = rx.load(args.prep, ["A", "C"])
    sf = data[subs[0]]["sfreq"]
    rows, t_fit, t_smooth = [], [], []
    for rep in (3, 4, 5):
        for fold, (tr_i, _) in enumerate(StratifiedKFold(5, shuffle=True, random_state=rep).split(subs, y)):
            t = time.time()
            _, _, corr, _ = rx.fold_microstates([subs[i] for i in tr_i], subs, data, 100 * rep + fold)
            t_fit.append(time.time() - t)
            t = time.time()
            for s, c in corr.items():
                a = c.argmax(0)
                rows.append({"subject": s, "rep": rep, "fold": fold, "primary": mean_run(a),
                             "smoothed": mean_run(msx.reject_short_segments(a, data[s]["ms"], args.min_segment))})
            t_smooth.append(time.time() - t)
    r = pd.DataFrame(rows).groupby("subject")[["primary", "smoothed"]].mean()
    r["group"] = [{1: "AD", 0: "HC"}[y[subs.index(s)]] for s in r.index]
    L = ["# Mean visit length on real labels (no training)", "",
         f"65 subjects, maps from the 15 training folds of repeats 3-5, whole recordings, all runs including the first and last. Smoothing: segments under {args.min_segment} samples rejected, as preregistered. Mean ± SD across subjects. 1 sample = {1000 / sf:.2f} ms.", "",
         "| Group | n | Primary, samples | Primary, ms | Smoothed, samples | Smoothed, ms |", "|---|---|---|---|---|---|"]
    for g in ("AD", "HC"):
        d = r[r.group == g]
        L.append(f"| {g} | {len(d)} | {d.primary.mean():.2f} ± {d.primary.std():.2f} | {1000 * d.primary.mean() / sf:.1f} ± {1000 * d.primary.std() / sf:.1f} | "
                 f"{d.smoothed.mean():.2f} ± {d.smoothed.std():.2f} | {1000 * d.smoothed.mean() / sf:.1f} ± {1000 * d.smoothed.std() / sf:.1f} |")
    L += ["", f"Timing: map fit and backfit {np.mean(t_fit):.1f} s per fold; relabelling all subjects with smoothing {np.mean(t_smooth):.1f} s per fold.", ""]
    open(args.out, "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
