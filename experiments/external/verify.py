"""Open every external recording with MNE, record what is actually in it, and save
signal fingerprints for the duplicate check.

Outputs (all under data/checks/, git-ignored):
  verification.csv   one row per recording: channels, sfreq, duration, problems
  fingerprints.npz   per recording: up to 60 s resampled to 128 Hz, 1-30 Hz band-passed;
                     'fp|<id>' in standard-19 order (labelled channels only), 'fpraw|<id>' in file order
Usage: python -I verify.py [cohort_id ...]
"""
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt, resample_poly, welch
from fractions import Fraction

sys.path.insert(0, os.path.dirname(__file__))
import cohorts  # noqa: E402

import mne  # noqa: E402

mne.set_log_level("ERROR")
OUT = os.path.join(cohorts.ROOT, "data", "checks")
FS_FP = 128
FP_SECONDS = 60
ALIAS = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6", "FP1": "Fp1", "FP2": "Fp2", "FZ": "Fz",
         "CZ": "Cz", "PZ": "Pz"}


def norm_name(c):
    c = c.strip().replace("EEG ", "").split("-")[0].strip()
    return ALIAS.get(c.upper(), ALIAS.get(c, c))


def to_mne(seg, ch, sf):
    names = ch if ch and len(ch) == seg.shape[0] else [f"ch{i+1:02d}" for i in range(seg.shape[0])]
    info = mne.create_info(names, sf if np.isfinite(sf) else 128.0, "eeg")
    return mne.io.RawArray(seg, info, verbose="error")


def fingerprint(segs, ch, sf):
    """First FP_SECONDS s, resampled to 128 Hz and 1-30 Hz band-passed.

    Returns (std19, raw): std19 is in STD19 order with NaN rows for missing channels (None when
    channels are unlabelled); raw keeps the file's own channel order (segments with the most
    common channel count only), for channel-agnostic comparisons.
    """
    if not np.isfinite(sf):
        return None, None
    nch = max({s.shape[0] for s in segs}, key=[s.shape[0] for s in segs].count)
    fr = Fraction(FS_FP / sf).limit_denominator(1000)
    sos = butter(4, [1, 30], btype="band", fs=FS_FP, output="sos")
    pieces, total = [], 0
    for s in segs:
        if s.shape[0] != nch:
            continue
        x = resample_poly(s, fr.numerator, fr.denominator, axis=1) if fr != 1 else s
        if x.shape[1] < 3 * 64:
            continue
        pieces.append(sosfiltfilt(sos, x, axis=1))
        total += x.shape[1]
        if total >= FP_SECONDS * FS_FP:
            break
    if not pieces:
        return None, None
    raw = np.concatenate(pieces, axis=1)[:, :FP_SECONDS * FS_FP].astype(np.float32)
    std = None
    if ch and len(ch) == nch:
        names = [norm_name(c) for c in ch]
        idx = [names.index(c) if c in names else -1 for c in cohorts.STD19]
        if sum(i >= 0 for i in idx) >= 10:
            std = np.full((19, raw.shape[1]), np.nan, dtype=np.float32)
            for k, i in enumerate(idx):
                if i >= 0:
                    std[k] = raw[i]
    return std, raw


def check(rec):
    row = dict(recording_id=rec.recording_id, cohort_id=rec.cohort_id, source_subject_id=rec.source_subject_id,
               path=rec.path, readable=False, problems="")
    probs = []
    if rec.group in ("", "unclear"):
        probs.append(f"no usable diagnosis label (given: '{rec.diagnosis_given}')")
    try:
        data, ch, sf, extra = rec.load()
    except Exception as e:  # unreadable
        row["problems"] = "UNREADABLE: " + repr(e)[:300]
        return row, None, None
    segs = data if isinstance(data, list) else [data]
    if not segs:
        row["problems"] = "UNREADABLE: no segments/files in folder"
        return row, None, None
    raw0 = extra.get("raw")
    try:
        raws = [raw0] if raw0 is not None else [to_mne(s, ch, sf) for s in segs]  # MNE opens every segment
    except Exception as e:
        row["problems"] = "MNE could not build Raw: " + repr(e)[:300]
        return row, None, None
    nchs = sorted({s.shape[0] for s in segs})
    n_samp = sum(s.shape[1] for s in segs)
    row.update(readable=True, n_channels="/".join(map(str, nchs)),
               channel_names=";".join(raws[0].ch_names) if ch else f"unlabelled ({'/'.join(map(str, nchs))} columns)",
               sfreq=sf, n_segments=len(segs), duration_s=round(n_samp / sf, 2) if np.isfinite(sf) else np.nan)
    if len(nchs) > 1:
        probs.append(f"channel count differs between segments: {nchs}")
    if not np.isfinite(sf):
        probs.append("sampling rate not stated for this recording")
    allx = np.concatenate([s[:, :min(s.shape[1], 200000)] for s in segs if s.shape[0] == nchs[-1]], axis=1)
    if not np.isfinite(allx).all():
        probs.append("NaN/Inf values")
    sd = np.nanstd(allx, axis=1)
    flat = int((sd < 1e-12).sum())
    if flat:
        probs.append(f"{flat} flat channel(s)")
    fp, fpraw = fingerprint(segs, ch, sf)
    if fpraw is not None:  # amplitude on the 1-30 Hz signal, so DC offsets and drift do not count
        med_uv = float(np.nanmedian(np.nanstd(fpraw, axis=1)) * 1e6)
        row["median_channel_sd_uV_1_30Hz"] = round(med_uv, 3)
        if not 1 <= med_uv <= 200:
            probs.append(f"implausible 1-30 Hz amplitude (median SD {med_uv:.3g} uV): units differ from the assumed uV")
    # truncation checks
    if rec.fmt.startswith("EEGLAB"):
        side = rec.files[0][:-8] + "_eeg.json" if rec.files[0].endswith("_eeg.set") else None
        if side and os.path.exists(side):
            js = json.load(open(side))
            exp = js.get("RecordingDuration")
            if exp and abs(exp - row["duration_s"]) > 2:
                probs.append(f"duration {row['duration_s']} s differs from sidecar RecordingDuration {exp} s")
    if rec.cohort_id in ("fsu_duke", "adsz_fsu") and n_samp != 1024:
        probs.append(f"expected 1024 samples, found {n_samp}")
    if rec.cohort_id == "fsu_duke":
        f1p = os.path.join(rec.files[0], "F1.txt")
        if os.path.exists(f1p):
            if not np.allclose(np.loadtxt(f1p), np.loadtxt(os.path.join(rec.files[0], "Fp1.txt"))):
                probs.append("F1.txt differs from Fp1.txt")
    row["problems"] = "; ".join(probs)
    return row, fp, fpraw


def main(which):
    os.makedirs(OUT, exist_ok=True)
    rows, fps = [], {}
    for rec in cohorts.all_recordings(which or None):
        try:
            row, fp, psd = check(rec)
        except Exception:
            row = dict(recording_id=rec.recording_id, cohort_id=rec.cohort_id, path=rec.path, readable=False,
                       problems="CHECK FAILED: " + traceback.format_exc(limit=1)[-300:])
            fp = psd = None
        rows.append(row)
        if fp is not None:
            fps["fp|" + rec.recording_id] = fp
        if psd is not None:
            fps["fpraw|" + rec.recording_id] = psd
        print(rec.recording_id, row.get("readable"), row.get("problems", "")[:120], flush=True)
    df = pd.DataFrame(rows)
    path = os.path.join(OUT, "verification.csv")
    if which and os.path.exists(path):  # update in place for a subset of cohorts
        old = pd.read_csv(path)
        df = pd.concat([old[~old.cohort_id.isin(which)], df], ignore_index=True)
    df.to_csv(path, index=False)
    fpath = os.path.join(OUT, "fingerprints.npz")
    if which and os.path.exists(fpath):
        old = dict(np.load(fpath, allow_pickle=True))
        keep = {k: v for k, v in old.items() if k.split("|", 1)[1].split(":")[0] not in which}
    else:
        keep = {}
    keep.update(fps)
    np.savez_compressed(fpath, **keep)


if __name__ == "__main__":
    main(sys.argv[1:])
