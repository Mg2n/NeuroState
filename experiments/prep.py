"""Step 1 - Prepare ds004504 for the experiments.

For every subject in participants.tsv this script:
  1. loads the preprocessed EEG from derivatives/ (falls back to the raw BIDS .set),
  2. keeps the 19 scalp channels in a fixed order and re-references to the average,
  3. makes two band-limited copies, both resampled to 128 Hz:
       - "dl": 1-40 Hz, input for the EEGNet branch
       - "ms": 2-20 Hz, used for microstates (Koenig et al. 2002 band)
  4. saves them to <out>/sub-XXX.npz (float32, microvolts).

Usage:
    python prep.py --bids /path/to/ds004504 --out /path/to/prepared
"""
import argparse
import glob
import os

import mne
import numpy as np
import pandas as pd

CHANNELS = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T3", "C3", "Cz",
            "C4", "T4", "T5", "P3", "Pz", "P4", "T6", "O1", "O2"]
SFREQ = 128.0


def find_set_file(bids, sub):
    for pattern in (f"{bids}/derivatives/{sub}/eeg/*.set", f"{bids}/{sub}/eeg/*.set"):
        files = sorted(glob.glob(pattern))
        if files:
            return files[0]
    return None


def band_copy(raw, l_freq, h_freq):
    r = raw.copy().filter(l_freq, h_freq, method="fir", phase="zero", verbose="ERROR")
    r.resample(SFREQ, verbose="ERROR")
    return (r.get_data() * 1e6).astype(np.float32)  # volts -> microvolts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bids", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    parts = pd.read_csv(os.path.join(args.bids, "participants.tsv"), sep="\t")
    rows = []
    for _, p in parts.iterrows():
        sub = p["participant_id"]
        out_file = os.path.join(args.out, f"{sub}.npz")
        f = find_set_file(args.bids, sub)
        if f is None:
            print(f"{sub}: no .set file found, skipped")
            continue
        if not os.path.exists(out_file):
            raw = mne.io.read_raw_eeglab(f, preload=True, verbose="ERROR")
            # T7/T8/P7/P8 are the newer names of T3/T4/T5/T6
            alias = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}
            raw.rename_channels({c: alias[c] for c in raw.ch_names if c in alias})
            missing = [c for c in CHANNELS if c not in raw.ch_names]
            if missing:
                print(f"{sub}: missing channels {missing}, skipped")
                continue
            raw.pick(CHANNELS)  # fixed channel order for every subject
            raw.set_eeg_reference("average", projection=False, verbose="ERROR")
            np.savez_compressed(out_file, dl=band_copy(raw, 1.0, 40.0),
                                ms=band_copy(raw, 2.0, 20.0),
                                sfreq=SFREQ, ch_names=np.array(CHANNELS))
        n = np.load(out_file)["dl"].shape[1]
        rows.append({"participant_id": sub, "Group": p["Group"],
                     "duration_s": round(n / SFREQ, 1)})
        print(f"{sub} ({p['Group']}): {n / SFREQ:.0f} s")
    pd.DataFrame(rows).to_csv(os.path.join(args.out, "subjects.csv"), index=False)
    print(f"done: {len(rows)} subjects")


if __name__ == "__main__":
    main()
