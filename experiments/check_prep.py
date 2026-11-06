"""Sanity checks and figures for prepared/ (task 03). Writes results/prep_report.md and figures/prep/.

Checks: all subjects present, durations per group, channel order, sampling rate, NaN/Inf,
amplitude outliers (std > 3x median), flat channels, duration vs the source recording.
Figures: 10 s of prepared EEG (one AD, one HC); average power spectrum per group.

  .venv/bin/python check_prep.py --bids ../ds004504 --prep ../prepared --log ../results/prep_log.txt
"""
import argparse
import os
import platform
import time
from importlib.metadata import version

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
from scipy.signal import welch
from scipy.stats import mannwhitneyu

from prep import CHANNELS, SFREQ, find_set_file

GROUPS = {"A": "AD", "C": "HC", "F": "FTD"}
COLORS = {"A": "#2a78d6", "C": "#eb6834", "F": "#1baf7a"}  # validated categorical slots 1-3
BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e6e5e0"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def plot_traces(subs, z, out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 6.5), sharey=True)
    t0 = 60.0  # start 60 s in, away from the recording edges
    n = int(10 * SFREQ)
    i0 = int(t0 * SFREQ)
    spacing = 60.0
    for ax, (sub, grp) in zip(axes, subs):
        x = z[sub]["dl"][:, i0:i0 + n]
        t = t0 + np.arange(n) / SFREQ
        for k, ch in enumerate(CHANNELS):
            ax.plot(t, x[k] - k * spacing, color=COLORS[grp], lw=0.6)
        ax.set_yticks([-k * spacing for k in range(len(CHANNELS))], CHANNELS)
        ax.set_title(f"{GROUPS[grp]} - {sub}", color=INK, fontsize=10, loc="left")
        ax.set_xlabel("Time (s)", color=MUTED, fontsize=9)
        style(ax)
        ax.grid(False)
    for ax in axes:
        ax.set_xlim(t0, t0 + 11)
    axes[1].plot([t0 + 10.4] * 2, [0, -50], color=INK, lw=1.5)  # scale bar in the right margin
    axes[1].text(t0 + 10.55, -25, "50 µV", ha="left", va="center", fontsize=8, color=INK)
    fig.suptitle("Prepared EEG (1-40 Hz, average reference, 128 Hz), 10 s from t = 60 s",
                 color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def plot_psd(freqs, psd, groups, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sel = (freqs >= 1) & (freqs <= 40)
    for g in ("A", "C", "F"):
        m = np.log10(psd[groups == g][:, sel])
        mu, se = m.mean(0), m.std(0, ddof=1) / np.sqrt(len(m))
        ax.fill_between(freqs[sel], mu - se, mu + se, color=COLORS[g], alpha=0.18, lw=0)
        ax.plot(freqs[sel], mu, color=COLORS[g], lw=2, label=f"{GROUPS[g]} (n={len(m)})")
        ax.text(40.5, mu[-1], GROUPS[g], color=INK, fontsize=8, va="center")
    for name, (lo, hi) in BANDS.items():
        ax.axvline(hi, color=GRID, lw=0.8, zorder=0)
        ax.text((lo + hi) / 2, ax.get_ylim()[1], name, ha="center", va="bottom", fontsize=8, color=MUTED)
    ax.set_xlabel("Frequency (Hz)", color=MUTED, fontsize=9)
    ax.set_ylabel("log10 power (µV²/Hz)", color=MUTED, fontsize=9)
    ax.set_xlim(1, 43)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("Average power spectrum per group (mean of 19 channels, ±SEM across subjects)",
                 color=INK, fontsize=10, loc="left", pad=16)
    style(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bids", default="../ds004504")
    ap.add_argument("--prep", default="../prepared")
    ap.add_argument("--log", default="../results/prep_log.txt")
    ap.add_argument("--report", default="../results/prep_report.md")
    ap.add_argument("--figs", default="../figures/prep")
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(args.figs, exist_ok=True)

    parts = pd.read_csv(os.path.join(args.bids, "participants.tsv"), sep="\t")
    subs = pd.read_csv(os.path.join(args.prep, "subjects.csv"))
    npz = sorted(f for f in os.listdir(args.prep) if f.endswith(".npz"))
    absent = sorted(set(parts.participant_id) - set(subs.participant_id))
    log_skips = [l.strip() for l in open(args.log) if "skipped" in l] if os.path.exists(args.log) else []

    rows, z = [], {}
    for _, s in subs.iterrows():
        sub = s.participant_id
        d = np.load(os.path.join(args.prep, f"{sub}.npz"))
        dl, ms = d["dl"], d["ms"]
        z[sub] = {"dl": dl}
        src = find_set_file(args.bids, sub)
        raw = mne.io.read_raw_eeglab(src, preload=False, verbose="ERROR")
        ch_std = dl.std(1)
        f, p = welch(dl, fs=SFREQ, nperseg=int(4 * SFREQ))  # 4-s windows, 0.25 Hz resolution
        rows.append({
            "subject": sub, "Group": s.Group, "source": "derivatives" if "derivatives" in src else "raw",
            "ch_ok": list(d["ch_names"]) == CHANNELS, "sfreq": float(d["sfreq"]),
            "shape_ok": dl.shape == ms.shape and dl.shape[0] == 19,
            "nonfinite": int((~np.isfinite(dl)).sum() + (~np.isfinite(ms)).sum()),
            "dur_s": dl.shape[1] / SFREQ, "src_dur_s": raw.n_times / raw.info["sfreq"],
            "std_uv": float(dl.std()), "ms_std_uv": float(ms.std()),
            "max_abs_uv": float(np.abs(dl).max()), "max_abs_ch": CHANNELS[int(np.abs(dl).max(1).argmax())],
            "max_abs_t_s": int(np.abs(dl).argmax()) % dl.shape[1] / SFREQ,
            "frac_win_gt100": float((np.abs(dl[:, :dl.shape[1] // 512 * 512].reshape(19, -1, 512))
                                     .max(2) > 100).any(0).mean()),
            "min_ch_std": float(ch_std.min()), "min_ch": CHANNELS[int(ch_std.argmin())],
            "max_ch_std": float(ch_std.max()), "max_ch": CHANNELS[int(ch_std.argmax())],
            "psd": p.mean(0)})
    freqs = f
    df = pd.DataFrame(rows)
    med = df.std_uv.median()
    df["std_ratio"] = df.std_uv / med
    flagged = df[df.std_ratio > 3]
    flat = df[df.min_ch_std < 0.5]  # < 0.5 µV std on any channel = effectively flat
    df["dur_diff_s"] = (df.dur_s - df.src_dur_s).abs()

    # band power: relative to 1-30 Hz total, per subject
    psd = np.stack(df.psd.values)
    df_f = freqs[1] - freqs[0]
    tot = psd[:, (freqs >= 1) & (freqs < 30)].sum(1) * df_f
    for b, (lo, hi) in BANDS.items():
        df[f"rel_{b}"] = psd[:, (freqs >= lo) & (freqs < hi)].sum(1) * df_f / tot
    alpha_band = (freqs >= 6) & (freqs <= 14)
    df["peak_alpha_hz"] = freqs[alpha_band][psd[:, alpha_band].argmax(1)]
    groups = df.Group.values

    ad, hc = df[df.Group == "A"].iloc[0].subject, df[df.Group == "C"].iloc[0].subject
    plot_traces([(ad, "A"), (hc, "C")], z, os.path.join(args.figs, "raw_eeg_AD_vs_HC.png"))
    plot_psd(freqs, psd, groups, os.path.join(args.figs, "psd_per_group.png"))

    # ---- report ----
    ok = (len(df) == 88 and not absent and df.ch_ok.all() and df.shape_ok.all()
          and (df.sfreq == SFREQ).all() and df.nonfinite.sum() == 0)
    L = ["# Preprocessing report (task 03)", "",
         f"**Result: {'PASS' if ok else 'FAIL'}** - {len(df)}/{len(parts)} subjects prepared, "
         f"{len(absent)} excluded, {len(flagged)} amplitude flag(s), {len(flat)} flat-channel flag(s).", "",
         "## Settings", "",
         f"- Command: `.venv/bin/python prep.py --bids ../ds004504 --out ../prepared` (log: `results/prep_log.txt`)",
         f"- Source: {', '.join(f'{k} {v}' for k, v in df.source.value_counts().items())} "
         "(dataset authors' preprocessing: 0.5-45 Hz band-pass, ASR, ICA)",
         f"- 19 channels in fixed order, average reference, resampled to {SFREQ:g} Hz; "
         "`dl` = 1-40 Hz (EEGNet), `ms` = 2-20 Hz (microstates); FIR zero-phase; float32 µV",
         f"- Checked {time.strftime('%Y-%m-%d %H:%M')}; Python {platform.python_version()}, "
         f"mne {version('mne')}, numpy {version('numpy')}, scipy {version('scipy')}", "",
         "## Checks", "",
         "| Check | Result |", "|---|---|",
         f"| `.npz` files in prepared/ | {len(npz)} |",
         f"| Subjects in `subjects.csv` | {len(df)} of {len(parts)} in participants.tsv |",
         f"| Excluded / missing subjects | {', '.join(absent) if absent else 'none'} |",
         f"| Skip messages in prep log | {'; '.join(log_skips) if log_skips else 'none'} |",
         f"| Channel order identical to `{','.join(CHANNELS)}` | {'yes, all' if df.ch_ok.all() else 'NO: ' + ', '.join(df[~df.ch_ok].subject)} |",
         f"| Sampling rate 128 Hz | {'yes, all' if (df.sfreq == SFREQ).all() else 'NO'} |",
         f"| `dl` and `ms` same shape, 19 rows | {'yes, all' if df.shape_ok.all() else 'NO: ' + ', '.join(df[~df.shape_ok].subject)} |",
         f"| NaN / Inf values (dl + ms) | {int(df.nonfinite.sum())} |",
         f"| Duration matches source recording (max difference) | {df.dur_diff_s.max():.2f} s |",
         f"| Subjects with std > 3x median ({med:.2f} µV) | {', '.join(flagged.subject) if len(flagged) else 'none'} |",
         f"| Subjects with a flat channel (std < 0.5 µV) | {', '.join(flat.subject) if len(flat) else 'none'} |",
         "", "## Issues found (no subject excluded)", ""]
    for r in flagged.itertuples():
        L.append(f"- **{r.subject} ({GROUPS[r.Group]})**: overall std {r.std_uv:.1f} µV = {r.std_ratio:.1f}x the median, "
                 f"high on all channels for the whole recording ({r.frac_win_gt100:.0%} of 4-s windows exceed 100 µV; "
                 f"loudest {r.max_ch} {r.max_ch_std:.0f} µV). Kept. FTD is not in the main AD vs HC comparison; "
                 "if FTD is analysed, report results with and without it." if r.Group == "F" else
                 f"- **{r.subject} ({GROUPS[r.Group]})**: overall std {r.std_ratio:.1f}x the median. Kept.")
    big = df[df.max_abs_uv > 500]
    L.append(f"- Isolated large transients (> 500 µV) remain in {len(big)} subjects "
             f"({', '.join(big.subject)}); the worst is {big.nlargest(1, 'max_abs_uv').subject.iloc[0]} "
             f"({big.max_abs_uv.max():.0f} µV). They are short (median subject: {df.frac_win_gt100.median():.1%} "
             "of 4-s windows > 100 µV). Kept. Decision (2026-11-03, before task 05): no window rejection; "
             "all windows of all subjects are used, since the derivatives are already ASR/ICA-cleaned.")
    short = df[df.dur_s < 360]
    L.append(f"- Short recordings (< 6 min): {', '.join(f'{r.subject} ({GROUPS[r.Group]}, {r.dur_s:.0f} s)' for r in short.itertuples()) or 'none'}. "
             "Kept; these subjects contribute fewer 4-s windows, which matters if windows are pooled.")
    L += ["", "## Durations (s, after prep)", "",
         "| Group | n | min | median | max | total (min) |", "|---|---|---|---|---|---|"]
    for g in ("A", "C", "F"):
        d = df[df.Group == g].dur_s
        L.append(f"| {GROUPS[g]} ({g}) | {len(d)} | {d.min():.1f} | {d.median():.1f} | {d.max():.1f} | {d.sum() / 60:.0f} |")
    L += ["", "## Amplitude (1-40 Hz copy, µV)", "",
          "| Group | std median | std min | std max | max std/median ratio | max abs value |", "|---|---|---|---|---|---|"]
    for g in ("A", "C", "F"):
        d = df[df.Group == g]
        L.append(f"| {GROUPS[g]} | {d.std_uv.median():.2f} | {d.std_uv.min():.2f} | {d.std_uv.max():.2f} | "
                 f"{d.std_ratio.max():.2f} | {d.max_abs_uv.max():.0f} |")
    top = df.sort_values("std_ratio", ascending=False).head(5)
    L += ["", "Five highest-amplitude subjects (none are excluded; listed for transparency):", "",
          "| Subject | Group | std (µV) | ratio to median | loudest channel (std) | max abs (µV) |", "|---|---|---|---|---|---|"]
    for r in top.itertuples():
        L.append(f"| {r.subject} | {GROUPS[r.Group]} | {r.std_uv:.2f} | {r.std_ratio:.2f} | "
                 f"{r.max_ch} ({r.max_ch_std:.1f}) | {r.max_abs_uv:.0f} |")
    L += ["", "Large transients (largest absolute value per subject; share of non-overlapping 4-s windows "
          "with any channel > 100 µV). Not removed: the data are the authors' ASR/ICA-cleaned derivatives.", "",
          "| Subject | Group | max abs (µV) | channel | at t (s) | windows > 100 µV |", "|---|---|---|---|---|---|"]
    shown = pd.concat([df.nlargest(5, "max_abs_uv"), df.nlargest(5, "frac_win_gt100")]).drop_duplicates("subject")
    for r in shown.itertuples():
        L.append(f"| {r.subject} | {GROUPS[r.Group]} | {r.max_abs_uv:.0f} | {r.max_abs_ch} | {r.max_abs_t_s:.1f} | "
                 f"{r.frac_win_gt100:.1%} |")
    L.append(f"| median, all subjects | | {df.max_abs_uv.median():.0f} | | | {df.frac_win_gt100.median():.1%} |")
    L += ["", "## Spectral check: AD vs HC", "",
          "Relative band power (fraction of 1-30 Hz power, mean of 19 channels), group mean ± SD. "
          "p = two-sided Mann-Whitney U, AD vs HC, uncorrected. Descriptive only: not used for model selection.", "",
          "| Band | AD | HC | FTD | AD vs HC p |", "|---|---|---|---|---|"]
    for b in list(BANDS) + ["peak_alpha_hz"]:
        col = b if b == "peak_alpha_hz" else f"rel_{b}"
        a, c, f_ = (df[df.Group == g][col] for g in ("A", "C", "F"))
        p = mannwhitneyu(a, c).pvalue
        fmt = (lambda s: f"{s.mean():.2f} ± {s.std():.2f}") if b == "peak_alpha_hz" else \
              (lambda s: f"{s.mean():.3f} ± {s.std():.3f}")
        name = "peak alpha freq (Hz, 6-14)" if b == "peak_alpha_hz" else f"{b} {BANDS[b][0]}-{BANDS[b][1]} Hz"
        L.append(f"| {name} | {fmt(a)} | {fmt(c)} | {fmt(f_)} | {p:.3g} |")
    A, C = df[df.Group == "A"], df[df.Group == "C"]
    slow = (A.rel_delta + A.rel_theta).mean() > (C.rel_delta + C.rel_theta).mean()
    less_alpha = A.rel_alpha.mean() < C.rel_alpha.mean()
    L += ["", f"Expected pattern (AD more slow-wave, less alpha than HC): "
          f"slow-wave (delta+theta) higher in AD: **{'yes' if slow else 'no'}**; "
          f"alpha lower in AD: **{'yes' if less_alpha else 'no'}**.", "",
          "## Figures", "",
          f"- `figures/prep/raw_eeg_AD_vs_HC.png` - 10 s (t = 60-70 s) of the 1-40 Hz copy, "
          f"{ad} (AD) and {hc} (HC): the first subject of each group in participants.tsv.",
          "- `figures/prep/psd_per_group.png` - Welch PSD (4-s windows), mean of 19 channels, "
          "group mean ± SEM of log10 power.", "",
          "## Per-subject table", "",
          "| Subject | Group | Duration (s) | std (µV) | ratio | min ch std | rel. alpha | flags |",
          "|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        fl = [x for x, c in (("amp>3x", r.std_ratio > 3), ("flat ch", r.min_ch_std < 0.5)) if c]
        L.append(f"| {r.subject} | {r.Group} | {r.dur_s:.1f} | {r.std_uv:.2f} | {r.std_ratio:.2f} | "
                 f"{r.min_ch} {r.min_ch_std:.2f} | {r.rel_alpha:.3f} | {', '.join(fl) or '-'} |")
    L += ["", f"_Runtime: {time.time() - t0:.0f} s._", ""]
    open(args.report, "w").write("\n".join(L))
    print("\n".join(L[:75]))


if __name__ == "__main__":
    main()
