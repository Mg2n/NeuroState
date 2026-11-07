"""Duplicate check across the external cohorts: signals and metadata.

Signal test. For each recording A, a 4-s template (starting 2 s in) is slid over the first 60 s
of every other recording B (128 Hz, 1-30 Hz; see verify.py). Score = peak normalised
cross-correlation (Pearson r of the template with the best-aligned window, sign kept).
  * labelled channels: r per shared standard channel, averaged across channels at each lag
  * unlabelled channels (hk_czech, padic_israel) or mixed pairs: channel-agnostic, three
    template channels each matched to its best channel in B; score = mean of the three peaks
r >= 0.95 means the same signal (identical or re-processed copy); 0.80-0.95 is reported for review.

Metadata test: ds006036 vs ds004504 participants.tsv (same IDs per README): sex, age, group, MMSE.

Outputs in data/checks/: duplicate_pairs.csv (every pair with score >= 0.80), metadata_ds006036_vs_ds004504.csv,
global_ids.csv (recording_id -> global_participant_id with the evidence used).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import cohorts  # noqa: E402

CHK = os.path.join(cohorts.ROOT, "data", "checks")
T0, TL, NFFT, MAXL = 256, 512, 8192, 7680
REPORT, SAME = 0.80, 0.95


def zero_mean(x):
    return x - np.nanmean(x, axis=-1, keepdims=True)


def ncc_batch(t, B, Bf, B2c):
    """t: (C, TL) template; B: (n, C, L) data (zeros where missing); returns (n, C, lags) r."""
    t = zero_mean(t)
    tn = np.sqrt((t ** 2).sum(-1))  # (C,)
    tf = np.fft.rfft(t[:, ::-1], NFFT)
    num = np.fft.irfft(Bf * tf[None], NFFT)[..., TL - 1:MAXL]  # valid lags
    # window sums for mean removal and norm
    s1 = B2c[0][..., TL:] - B2c[0][..., :-TL]
    s2 = B2c[1][..., TL:] - B2c[1][..., :-TL]
    n = num.shape[-1]
    s1, s2 = s1[..., :n], s2[..., :n]
    var = np.maximum(s2 - s1 ** 2 / TL, 0)
    den = np.sqrt(var) * tn[None, :, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(den > 1e-12, num / den, np.nan)  # t is zero-mean so sum(t*mean(b)) = 0
    return r


def prep(arrs, nch):
    n = len(arrs)
    B = np.zeros((n, nch, MAXL), np.float64)
    M = np.zeros((n, nch), bool)
    for i, a in enumerate(arrs):
        a = np.asarray(a, np.float64)[:nch, :MAXL]
        ok = np.isfinite(a).all(-1)
        B[i, :a.shape[0], :a.shape[1]] = np.where(np.isfinite(a), a, 0)
        M[i, :a.shape[0]] = ok
    Bf = np.fft.rfft(B, NFFT)
    c1 = np.concatenate([np.zeros((n, nch, 1)), np.cumsum(B, -1)], -1)
    c2 = np.concatenate([np.zeros((n, nch, 1)), np.cumsum(B ** 2, -1)], -1)
    return B, Bf, (c1, c2), M


def labelled_scores(fp):
    ids = sorted(fp)
    print("labelled recordings:", len(ids), flush=True)
    B, Bf, C, M = prep([fp[i] for i in ids], 19)
    out = []
    for a, ida in enumerate(ids):
        x = fp[ida]
        if x.shape[1] < T0 + TL:
            t0 = 0
        else:
            t0 = T0
        if x.shape[1] < TL:
            continue
        t = np.nan_to_num(x[:, t0:t0 + TL].astype(np.float64))
        okc = np.isfinite(x[:, 0])
        r = ncc_batch(t, B, Bf, C)  # (n, 19, lags)
        mask = (M & okc[None])[..., None]
        cnt = mask.sum(1)
        with np.errstate(invalid="ignore"):
            mean_r = np.where(cnt > 0, np.nansum(np.where(mask, r, 0), 1) / np.maximum(cnt, 1), np.nan)
        peak = np.nanmax(mean_r, -1)
        for b in np.where(peak >= REPORT)[0]:
            if b != a:
                out.append((ida, ids[b], float(peak[b]), int(cnt[b].max()), "labelled"))
        if a % 100 == 0:
            print("  ", a, flush=True)
    return out


def agnostic_scores(raw, queries):
    """Channel-agnostic: queries (ids) vs all raw fingerprints."""
    ids = sorted(raw)
    maxch = max(v.shape[0] for v in raw.values())
    B, Bf, C, M = prep([raw[i] for i in ids], maxch)
    out = []
    for k, ida in enumerate(queries):
        x = raw[ida].astype(np.float64)
        if x.shape[1] < TL:
            continue
        t0 = T0 if x.shape[1] >= T0 + TL else 0
        sd = x[:, t0:t0 + TL].std(-1)
        chans = [c for c in np.argsort(sd)[::-1] if sd[c] > 0][:3]  # three most active channels
        peaks = []
        for c in chans:
            t = np.repeat(x[c:c + 1, t0:t0 + TL], maxch, 0)
            r = ncc_batch(t, B, Bf, C)
            r = np.where(M[..., None], r, np.nan)
            peaks.append(np.nanmax(np.nanmax(r, -1), -1))  # best channel and lag in B
        score = np.nanmean(np.vstack(peaks), 0)
        for b in np.where(score >= REPORT)[0]:
            if ids[b] != ida:
                out.append((ida, ids[b], float(score[b]), len(chans), "channel-agnostic"))
        if k % 50 == 0:
            print("  agnostic", k, "/", len(queries), flush=True)
    return out


def metadata_ahepa():
    a = pd.DataFrame(cohorts.read_tsv(os.path.join(cohorts.EXT, "ds004504", "participants.tsv")))
    b = pd.DataFrame(cohorts.read_tsv(os.path.join(cohorts.EXT, "ds006036", "participants.tsv")))
    m = a.merge(b, on="participant_id", how="outer", suffixes=("_ds004504", "_ds006036"), indicator=True)
    for c in ["Gender", "Age", "Group", "MMSE"]:
        m[c + "_match"] = m[c + "_ds004504"] == m[c + "_ds006036"]
    m.to_csv(os.path.join(CHK, "metadata_ds006036_vs_ds004504.csv"), index=False)
    return m


def main():
    z = np.load(os.path.join(CHK, "fingerprints.npz"))
    fp = {k[3:]: z[k] for k in z.files if k.startswith("fp|")}
    raw = {k[6:]: z[k] for k in z.files if k.startswith("fpraw|")}
    unl = sorted(k for k in raw if k not in fp)
    print("unlabelled:", len(unl), flush=True)
    pairs = labelled_scores(fp) + agnostic_scores(raw, unl)
    df = pd.DataFrame(pairs, columns=["recording_a", "recording_b", "score", "n_channels_used", "method"])
    df["cohort_a"] = df.recording_a.str.split(":").str[0]
    df["cohort_b"] = df.recording_b.str.split(":").str[0]
    df["subject_a"] = df.recording_a.str.split(":").str[1]
    df["subject_b"] = df.recording_b.str.split(":").str[1]
    df["same_source_subject"] = (df.cohort_a == df.cohort_b) & (df.subject_a == df.subject_b)
    df["verdict"] = np.where(df.score >= SAME, "same signal", "review")
    df.sort_values("score", ascending=False).to_csv(os.path.join(CHK, "duplicate_pairs.csv"), index=False)
    m = metadata_ahepa()
    print(df.groupby(["cohort_a", "cohort_b", "same_source_subject", "verdict"]).size())
    print("ds006036 vs ds004504 metadata:", m["_merge"].value_counts().to_dict(),
          {c: int(m[c + "_match"].sum()) for c in ["Gender", "Age", "Group", "MMSE"]})


if __name__ == "__main__":
    main()
