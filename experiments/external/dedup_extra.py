"""Extra duplicate pass: channel-agnostic all-vs-all within the small labelled cohorts
(fsu_duke, adsz_fsu, apava_spain), to catch copies whose channel labels were permuted
(one such case was found between fsu_duke and adsz_fsu). Appends to
data/checks/duplicate_pairs.csv (method 'channel-agnostic (small cohorts)'), replacing earlier rows of that method.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import dedup  # noqa: E402

COH = ("fsu_duke:", "adsz_fsu:", "apava_spain:")
METHOD = "channel-agnostic (small cohorts)"


def main():
    z = np.load(os.path.join(dedup.CHK, "fingerprints.npz"))
    raw = {k[6:]: z[k] for k in z.files if k.startswith("fpraw|") and k[6:].startswith(COH)}
    # use the first 19 rows (fsu fingerprints come from the 19 named files in STD19 order)
    pairs = dedup.agnostic_scores(raw, sorted(raw))
    df = pd.DataFrame(pairs, columns=["recording_a", "recording_b", "score", "n_channels_used", "method"])
    df["method"] = METHOD
    for c, i in [("cohort", 0), ("subject", 1)]:
        df[c + "_a"] = df.recording_a.str.split(":").str[i]
        df[c + "_b"] = df.recording_b.str.split(":").str[i]
    df["same_source_subject"] = (df.cohort_a == df.cohort_b) & (df.subject_a == df.subject_b)
    df["verdict"] = np.where(df.score >= dedup.SAME, "same signal", "review")
    path = os.path.join(dedup.CHK, "duplicate_pairs.csv")
    old = pd.read_csv(path)
    old = old[old.method != METHOD]
    allp = pd.concat([old, df], ignore_index=True).sort_values("score", ascending=False)
    allp.to_csv(path, index=False)
    key = lambda d: set(zip(d.recording_a, d.recording_b))
    lab = old[(old.verdict == "same signal") & old.recording_a.str.startswith(COH) & old.recording_b.str.startswith(COH)]
    new = df[df.verdict == "same signal"]
    print("agnostic same-signal pairs:", len(new), "| labelled same-signal pairs:", len(lab))
    print("found only by the agnostic pass:", sorted(key(new) - key(lab)))
    print("found only by the labelled pass:", sorted(key(lab) - key(new)))


if __name__ == "__main__":
    main()
