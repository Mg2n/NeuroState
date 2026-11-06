"""Microstate helpers.

Maps are fitted with Pycrostates' modified k-means (polarity-invariant) on GFP peaks pooled from the
TRAINING subjects of each fold only, so no test-subject information leaks into the maps.
Backfitting and the summary features (coverage, duration, occurrence, transitions) are simple,
standard definitions computed with NumPy.
"""
import mne
import numpy as np
from pycrostates.cluster import ModKMeans
from pycrostates.io import ChData
from scipy.signal import find_peaks

N_STATES = 4


def gfp_peaks(x, max_peaks=1500, rng=None):
    """x: (channels, time), average-referenced. Returns (channels, n_peaks) maps at GFP peaks."""
    gfp = x.std(axis=0)
    idx, _ = find_peaks(gfp)
    if rng is not None and len(idx) > max_peaks:
        idx = np.sort(rng.choice(idx, max_peaks, replace=False))
    return x[:, idx]


def fit_maps(peak_list, ch_names, sfreq, seed=42, n_init=20):
    pooled = np.concatenate(peak_list, axis=1) * 1e-6  # back to volts for the library
    info = mne.create_info(list(ch_names), sfreq, "eeg")
    info.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    km = ModKMeans(n_clusters=N_STATES, n_init=n_init, max_iter=300, tol=1e-6, random_state=seed)
    km.fit(ChData(pooled, info), verbose="ERROR")
    return np.asarray(km.cluster_centers_, dtype=np.float64), float(km.GEV_)


def _unit(v, axis):
    v = v - v.mean(axis=axis, keepdims=True)  # common average
    return v / (np.linalg.norm(v, axis=axis, keepdims=True) + 1e-12)


def corr_sequence(x, maps):
    """|spatial correlation| of every sample with every map -> (4, time) float32."""
    return np.abs(_unit(maps, 1) @ _unit(x, 0)).astype(np.float32)


def reject_short_segments(labels, x, min_len):
    """Same labels as Pycrostates' _BaseCluster._reject_short_segments (min_segment_length), in linear time: that routine
    relists the whole recording after each fix. Edge segments are exempt. x: (channels, time)."""
    x = np.asarray(x, dtype=np.float64)
    a, b = x[:, :-1] - x[:, :-1].mean(0), x[:, 1:] - x[:, 1:].mean(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.abs(np.nan_to_num((a / np.linalg.norm(a, axis=0) * (b / np.linalg.norm(b, axis=0))).sum(0),
                                 posinf=0, neginf=0)).tolist()  # c[i] = |correlation| of samples i and i + 1
    lab = labels.tolist()
    n = len(lab)

    def run_end(i):
        j = i + 1
        while j < n and lab[j] == lab[i]:
            j += 1
        return j

    i = run_end(0)
    while i < n:
        j = run_end(i)
        if j == n:  # last segment
            break
        if j - i >= min_len:
            i = j
            continue
        left, right = i, j - 1
        while left <= right:
            if abs(c[right] - c[left - 1]) <= 1e-8:
                if left == right:
                    lab[left] = lab[left - 1]
                    left += 1
                else:
                    lab[right], lab[left] = lab[right + 1], lab[left - 1]
                    right -= 1
                    left += 1
            elif c[left - 1] < c[right]:
                lab[right] = lab[right + 1]
                right -= 1
            else:
                lab[left] = lab[left - 1]
                left += 1
        # earlier segments only grew, so the first short one is at or after the segment that now holds sample i - 1
        i -= 1
        while i > 0 and lab[i - 1] == lab[i]:
            i -= 1
        if i == 0:
            i = run_end(0)
    return np.array(lab, dtype=labels.dtype)


def features(labels, sfreq):
    """24 features per recording: coverage, mean duration (ms), occurrence (/s) per state,
    plus 12 transition probabilities between different states (self-transitions excluded)."""
    change = np.flatnonzero(np.diff(labels)) + 1
    starts = np.r_[0, change]
    lengths = np.diff(np.r_[starts, len(labels)])
    run_state = labels[starts]
    dur_s = len(labels) / sfreq
    cov, mdur, occ = [], [], []
    for k in range(N_STATES):
        m = run_state == k
        cov.append(np.mean(labels == k))
        mdur.append(lengths[m].mean() / sfreq * 1000 if m.any() else 0.0)
        occ.append(m.sum() / dur_s)
    T = np.zeros((N_STATES, N_STATES))
    for a, b in zip(run_state[:-1], run_state[1:]):
        T[a, b] += 1
    T /= max(T.sum(), 1)
    trans = [T[i, j] for i in range(N_STATES) for j in range(N_STATES) if i != j]
    return np.array(cov + mdur + occ + trans, dtype=np.float64)


FEATURE_NAMES = ([f"coverage_{k}" for k in range(N_STATES)]
                 + [f"duration_ms_{k}" for k in range(N_STATES)]
                 + [f"occurrence_{k}" for k in range(N_STATES)]
                 + [f"trans_{i}->{j}" for i in range(N_STATES) for j in range(N_STATES) if i != j])
