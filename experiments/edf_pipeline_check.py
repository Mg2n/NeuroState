"""Pipeline check on one EDF file: EDF -> resting segment -> microstates -> seq-CNN input.

Uses the project's existing code unchanged:
  prep.py            channel set and order, average reference, 2-20 Hz and 1-40 Hz copies at 128 Hz (band_copy)
  microstates.py     GFP peaks, modified k-means (Pycrostates), backfitting, the 24 features
  validate_microstates.py / NeuroState-Microstates   A-D labels by global matching to Koenig 2002 (as for Fig. 5)
  run_experiment.py  load(), windows(), predict_subject(), train_net() of the standalone seq-CNN (4 x 512 one-hot)
New here (not in prep.py, which takes whole eyes-closed recordings): selecting the resting segment from the EDF
event markers. Maps are fitted on this one recording only, because there are no training patients yet; in a real
study they must come from the training patients of each fold, as in run_experiment.py.

  .venv/bin/python edf_pipeline_check.py --edf /path/to/file.edf --out ../results/edf_pipeline_check
Writes: run_log.txt, results.json, microstate_table.csv, transitions_*.csv, fig_maps.png, fig_timeline.png,
prepared/<id>.npz + subjects.csv (same format as prep.py output), cnn_input_onehot_4x512.npy.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mne  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

import microstates as msx  # noqa: E402
import prep  # noqa: E402
import run_experiment as rx  # noqa: E402
from models import MicroStateNet  # noqa: E402
from validate_microstates import NS, align_sign, from_json, info_for, match_to_reference  # noqa: E402

STATES = "ABCD"
COLORS = {"A": "#2a6fdb", "B": "#e07b39", "C": "#3a9d5d", "D": "#b8457c"}
LOG = []


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.append(line)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resting_segment(raw, pattern):
    """Automatic selection: from the first marker matching `pattern` to the next marker (or the end)."""
    ann = sorted(((float(a["onset"]), a["description"]) for a in raw.annotations), key=lambda t: t[0])
    hits = [i for i, (_, d) in enumerate(ann) if re.search(pattern, d, re.I)]
    if not hits:
        raise SystemExit(f"no event marker matches {pattern!r}; markers: {ann}. Use --tmin/--tmax.")
    if len(hits) > 1:
        log(f"WARNING: {len(hits)} markers match {pattern!r}; using the first")
    i = hits[0]
    tmin = ann[i][0]
    tmax = ann[i + 1][0] if i + 1 < len(ann) else raw.times[-1] + 1 / raw.info["sfreq"]
    return tmin, tmax, ann


def gev_all_samples(x, maps, labels):
    """GEV over every sample of the segment: sum((GFP * corr with assigned map)^2) / sum(GFP^2)."""
    gfp = x.std(axis=0)
    c = msx.corr_sequence(x, maps)[labels, np.arange(x.shape[1])]
    return float(np.sum((gfp * c) ** 2) / np.sum(gfp ** 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--id", default=None, help="recording id for the prepared file (default: EDF patient id)")
    ap.add_argument("--marker", default=r"eyes\s*closed", help="regex for the resting-segment start marker")
    ap.add_argument("--tmin", type=float, help="manual segment start (s); overrides the markers")
    ap.add_argument("--tmax", type=float, help="manual segment end (s)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "prepared"), exist_ok=True)
    t0 = time.time()
    torch.manual_seed(args.seed)
    log(f"command: {' '.join(sys.argv)}")

    # 1. import ---------------------------------------------------------------------------------------
    raw = mne.io.read_raw_edf(args.edf, preload=True, verbose="ERROR")
    rid = args.id or (raw.info.get("subject_info") or {}).get("his_id") or "edf"
    rid = f"sub-{rid}" if not str(rid).startswith("sub-") else str(rid)
    sf0, dur0 = raw.info["sfreq"], raw.n_times / raw.info["sfreq"]
    eeg = [c for c, t in zip(raw.ch_names, raw.get_channel_types()) if t == "eeg"]
    raw.rename_channels({c: a for c, a in {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}.items() if c in raw.ch_names})
    missing = [c for c in prep.CHANNELS if c not in raw.ch_names]
    extra = [c for c in raw.ch_names if c not in prep.CHANNELS]
    log(f"import: {len(eeg)} EEG channels, {sf0:g} Hz, {dur0:.1f} s; channels {raw.ch_names}")
    log(f"channel names: {19 - len(missing)}/19 of prep.CHANNELS recognised; missing {missing}; not used {extra}")
    if missing:
        raise SystemExit("missing standard channels")

    # 2. resting segment ------------------------------------------------------------------------------
    if args.tmin is not None:
        tmin, tmax, ann = args.tmin, args.tmax, [(float(a["onset"]), a["description"]) for a in raw.annotations]
        how = "manual (--tmin/--tmax)"
    else:
        tmin, tmax, ann = resting_segment(raw, args.marker)
        how = f"automatic: first marker matching /{args.marker}/ to the next marker"
    log(f"markers: {[(round(o, 3), d) for o, d in ann]}")
    log(f"segment: {tmin:.3f}-{tmax:.3f} s ({tmax - tmin:.3f} s), selection {how}")
    seg = raw.copy().pick(prep.CHANNELS).crop(tmin, tmax, include_tmax=False)

    # 3. preparation, exactly as prep.py ----------------------------------------------------------------
    seg.set_eeg_reference("average", projection=False, verbose="ERROR")
    dl, ms = prep.band_copy(seg, 1.0, 40.0), prep.band_copy(seg, 2.0, 20.0)
    npz = os.path.join(args.out, "prepared", f"{rid}.npz")
    np.savez_compressed(npz, dl=dl, ms=ms, sfreq=prep.SFREQ, ch_names=np.array(prep.CHANNELS))
    pd.DataFrame([{"participant_id": rid, "Group": "X", "duration_s": round(ms.shape[1] / prep.SFREQ, 1)}]).to_csv(
        os.path.join(args.out, "prepared", "subjects.csv"), index=False)
    log(f"prepared (prep.py steps): average reference, 1-40 Hz 'dl' and 2-20 Hz 'ms' at {prep.SFREQ:g} Hz, "
        f"shape {ms.shape}, {ms.shape[1] / prep.SFREQ:.2f} s -> {npz}")

    # 4. microstates --------------------------------------------------------------------------------------
    rng = np.random.default_rng(args.seed)
    peaks = msx.gfp_peaks(ms, rng=rng)
    maps_raw, gev_peaks = msx.fit_maps([peaks], prep.CHANNELS, prep.SFREQ, seed=args.seed)
    log(f"maps: modified k-means (Pycrostates), 4 clusters, n_init=20, seed {args.seed}, on {peaks.shape[1]} GFP peaks "
        f"of this recording's 2-20 Hz segment; GEV at the peaks {gev_peaks:.3f}")
    tmpl = from_json(os.path.join(NS, "templates", "Koenig2002_4class.json"))
    res = match_to_reference(maps_raw, prep.CHANNELS, [str(k) for k in range(4)], tmpl.maps, tmpl.ch_names, tmpl.labels)
    to_ref = {k: res.assignment[k] for k in range(4)}  # cluster -> template index
    order = [next(k for k in range(4) if to_ref[k] == j) for j in range(4)]  # A, B, C, D -> cluster
    names = [tmpl.labels[j] for j in range(4)]
    assert names == list(STATES), names
    maps = maps_raw[order]
    from validate_microstates import koenig_on
    kref = koenig_on(prep.CHANNELS, tmpl)
    maps = align_sign(maps, kref)  # display/polarity only; backfitting is polarity-invariant
    absr = [float(res.assigned_abs_r[order[j]]) for j in range(4)]
    for j, s in enumerate(STATES):
        log(f"  {s} = k-means cluster {order[j]}, |r| with Koenig {s} = {absr[j]:.3f}")
    if res.greedy_disagrees:
        log(f"  note: greedy matching would differ for clusters {res.greedy_disagrees}")
    corr = msx.corr_sequence(ms, maps)
    labels = corr.argmax(0)  # 0..3 = A..D, no smoothing (run_experiment default --min-segment 0)
    gev_all = gev_all_samples(ms, maps, labels)
    f = msx.features(labels, prep.SFREQ)
    log(f"backfit: {len(labels)} samples; GEV over all segment samples {gev_all:.3f}")

    table = pd.DataFrame({"state": list(STATES),
                          "coverage_pct": 100 * f[0:4], "mean_duration_ms": f[4:8], "occurrence_per_s": f[8:12],
                          "abs_r_with_koenig2002": absr})
    table.to_csv(os.path.join(args.out, "microstate_table.csv"), index=False, float_format="%.4f")
    # transitions as in microstates.features: counts of state changes / all changes (self excluded)
    change = np.flatnonzero(np.diff(labels)) + 1
    run_state = labels[np.r_[0, change]]
    T = np.zeros((4, 4))
    for a, b in zip(run_state[:-1], run_state[1:]):
        T[a, b] += 1
    joint = T / T.sum()
    cond = T / T.sum(1, keepdims=True)
    pd.DataFrame(joint, index=[f"from_{s}" for s in STATES], columns=[f"to_{s}" for s in STATES]).to_csv(
        os.path.join(args.out, "transitions_joint_pipeline.csv"), float_format="%.4f")
    pd.DataFrame(cond, index=[f"from_{s}" for s in STATES], columns=[f"to_{s}" for s in STATES]).to_csv(
        os.path.join(args.out, "transitions_conditional.csv"), float_format="%.4f")
    assert np.allclose([joint[i, j] for i in range(4) for j in range(4) if i != j], f[12:]), "transition mismatch"

    # figures
    info = info_for(prep.CHANNELS)
    fig, axes = plt.subplots(1, 4, figsize=(8.0, 2.4))
    for j, ax in enumerate(axes):
        v = maps[j] / np.abs(maps[j]).max()
        mne.viz.plot_topomap(v, info, axes=ax, show=False, cmap="RdBu_r", vlim=(-1, 1), contours=0, sensors=True)
        ax.set_title(f"{STATES[j]}   |r| = {absr[j]:.2f}", fontsize=9)
    fig.suptitle(f"Microstate maps fitted on this recording ({tmax - tmin:.0f} s eyes closed); "
                 f"labels by matching to Koenig 2002; GEV {gev_all:.2f}", fontsize=8.5, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(os.path.join(args.out, "fig_maps.png"), dpi=200)
    plt.close(fig)

    n_show = int(2 * prep.SFREQ)
    t = np.arange(n_show) / prep.SFREQ
    gfp = ms.std(0)[:n_show]
    fig, ax = plt.subplots(figsize=(8.0, 2.2))
    ax.plot(t, gfp, color="#1f1f1e", lw=0.8)
    for s0 in range(n_show):
        ax.axvspan(t[s0], t[s0] + 1 / prep.SFREQ, color=COLORS[STATES[labels[s0]]], alpha=0.55, lw=0)
    ax.set(xlabel=f"Time from segment start (s; = {tmin:.0f} s in the recording)", ylabel="GFP (µV)", xlim=(0, t[-1]))
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=COLORS[s], alpha=0.55) for s in STATES], labels=list(STATES),
              ncol=4, frameon=False, loc="lower right", bbox_to_anchor=(1.0, 1.0), fontsize=8, borderaxespad=0.2)
    ax.set_title("First 2 s of the A-D sequence (2-20 Hz, 128 Hz), no smoothing", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig_timeline.png"), dpi=200)
    plt.close(fig)

    # 5. CNN handoff ----------------------------------------------------------------------------------------
    onehot = np.eye(4, dtype=np.float32)[labels].T.copy()  # as run_experiment.py with --ms-input onehot
    subs, _, data = rx.load(os.path.join(args.out, "prepared"), ["X"])
    rx.FS = data[subs[0]]["sfreq"]
    rx.WIN = int(round(4.0 * rx.FS))
    W = rx.windows(onehot)
    np.save(os.path.join(args.out, "cnn_input_onehot_4x512.npy"), W)
    left = onehot.shape[1] - len(W) * rx.WIN
    log(f"CNN input: one-hot A-D (4, {onehot.shape[1]}) -> {len(W)} complete windows of shape {W.shape[1:]} "
        f"(run_experiment.windows, WIN={rx.WIN} = 4 s at {rx.FS:g} Hz); {left} samples ({left / rx.FS:.2f} s) left over")
    assert W.shape[1:] == (4, 512) and np.allclose(W.sum(1), 1)
    model = MicroStateNet(n_times=rx.WIN, n_classes=2, use_ms=True, use_eeg=False)
    p = rx.predict_subject(model, subs[0], data, {subs[0]: onehot})
    log(f"seq-CNN forward pass (untrained, random weights): rx.predict_subject -> {p.shape} window probabilities; "
        f"loaded with rx.load from the prepared folder: {subs}")
    cfg = argparse.Namespace(device="cpu", dropout=0.5, ms_input="onehot", groups=["X", "Y"], lr=1e-3, wd=1e-3,
                             epochs=1, patience=1, crops=8, batch=8)
    # plumbing only: train_net needs two classes, so the one recording is entered twice with dummy labels 0 and 1
    m2, n_ep = rx.train_net(True, [subs[0], subs[0]], np.array([0, 1]), [subs[0], subs[0]], np.array([0, 1]),
                            data, {subs[0]: onehot}, args.seed, cfg, use_eeg=False)
    log(f"rx.train_net (seq-CNN, use_eeg=False) ran {n_ep} epoch on random 4 x 512 crops: the training code accepts "
        "this input (dummy labels; plumbing test only, no model is meaningful from one recording)")

    out = {"edf": os.path.abspath(args.edf), "edf_sha256": sha256(args.edf), "recording_id": rid,
           "import": {"n_eeg_channels": len(eeg), "sfreq": sf0, "duration_s": dur0, "channels": raw.ch_names,
                      "missing_standard": missing},
           "segment": {"tmin_s": tmin, "tmax_s": tmax, "duration_s": tmax - tmin, "selection": how,
                       "markers": [[o, d] for o, d in ann]},
           "prep": {"reference": "average", "ms_band_hz": [2, 20], "dl_band_hz": [1, 40], "sfreq": prep.SFREQ,
                    "n_samples": int(ms.shape[1])},
           "microstates": {"maps_source": "modified k-means on GFP peaks of this recording only (no training patients)",
                           "n_gfp_peaks": int(peaks.shape[1]), "seed": args.seed, "n_init": 20,
                           "gev_gfp_peaks": gev_peaks, "gev_all_samples": gev_all,
                           "labels": "global one-to-one matching (Hungarian, polarity ignored) to Koenig 2002 A-D",
                           "cluster_for_ABCD": order, "abs_r_with_koenig": dict(zip(STATES, absr)),
                           "greedy_disagrees": list(res.greedy_disagrees), "smoothing": "none",
                           "table": table.to_dict(orient="records"),
                           "transitions_joint_pipeline": joint.tolist(), "transitions_conditional": cond.tolist()},
           "cnn": {"input": "one-hot A-D", "window_shape": list(W.shape[1:]), "n_complete_windows": int(len(W)),
                   "leftover_samples": int(left), "forward_pass_output": list(p.shape), "train_net_epochs_run": n_ep},
           "environment": rx.env_info(), "minutes": (time.time() - t0) / 60}
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    log(f"done in {time.time() - t0:.1f} s")
    with open(os.path.join(args.out, "run_log.txt"), "w") as fh:
        fh.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
