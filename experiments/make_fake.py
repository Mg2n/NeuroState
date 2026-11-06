"""Make a small fake ds004504-like dataset (BIDS layout, EEGLAB .set) to test the pipeline.

Group "A" gets longer microstate-0 segments and more 6 Hz activity; group "C" more 10 Hz.
"""
import os
import sys

import mne
import numpy as np
import pandas as pd

from prep import CHANNELS

out = sys.argv[1]
n_per_group, dur, sf = 8, 120, 500
rng = np.random.default_rng(0)
maps = rng.normal(size=(4, len(CHANNELS)))
maps -= maps.mean(1, keepdims=True)
rows = []
for i in range(2 * n_per_group):
    grp = "A" if i < n_per_group else "C"
    sub = f"sub-{i + 1:03d}"
    n = dur * sf
    states = np.empty(n, int)
    t = 0
    while t < n:
        k = rng.integers(4)
        ms = rng.gamma(4, 20) * (2.0 if (grp == "A" and k == 0) else 1.0)
        L = max(int(ms / 1000 * sf), 5)
        states[t:t + L] = k
        t += L
    tt = np.arange(n) / sf
    f = 6.0 if grp == "A" else 10.0
    amp = np.abs(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6))) + 0.3
    x = maps[states].T * amp * 20e-6 + rng.normal(0, 5e-6, (len(CHANNELS), n))
    info = mne.create_info(CHANNELS, sf, "eeg")
    raw = mne.io.RawArray(x, info, verbose="ERROR")
    d = os.path.join(out, "derivatives", sub, "eeg")
    os.makedirs(d, exist_ok=True)
    mne.export.export_raw(os.path.join(d, f"{sub}_task-eyesclosed_eeg.set"), raw,
                          fmt="eeglab", overwrite=True, verbose="ERROR")
    rows.append({"participant_id": sub, "Gender": "F", "Age": 70, "Group": grp, "MMSE": 25})
pd.DataFrame(rows).to_csv(os.path.join(out, "participants.tsv"), sep="\t", index=False)
print("fake dataset written to", out)
