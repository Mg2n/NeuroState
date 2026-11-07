"""Duplicate check for P-ADIC (run after verify.py padic_israel and dedup.py).

1. Metadata: within and across the three P-ADIC files, compare original EEG file names and
   (sex, age, EEG date). Birth dates are not read.
2. Signal, within P-ADIC: all files share one export (19 columns, same order assumed), so the
   channel-matched test of dedup.py is applied column by column.
3. Signal, P-ADIC vs ds004504/ds006036 raw (also Nihon Kohden, 19 ch, 500 Hz): channel-agnostic test.
Results are appended to data/checks/duplicate_pairs.csv (previous P-ADIC rows replaced) and the
metadata table is written to data/checks/padic_metadata_matches.csv.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import cohorts  # noqa: E402
import dedup  # noqa: E402


def channel_matched(fp):
    """dedup.labelled_scores on column-indexed arrays (19 rows, file order)."""
    return dedup.labelled_scores(fp)


def agnostic_subset(raw, queries, targets):
    sub = {k: raw[k] for k in targets}
    out = []
    for q in queries:
        sub_q = dict(sub)
        sub_q[q] = raw[q]
        out += [r for r in dedup.agnostic_scores(sub_q, [q]) if r[1] != q]
    return out


def main():
    z = np.load(os.path.join(dedup.CHK, "fingerprints.npz"))
    raw = {k[6:]: z[k] for k in z.files if k.startswith("fpraw|")}
    pad = sorted(k for k in raw if k.startswith("padic_israel:"))
    print("P-ADIC fingerprints:", len(pad), flush=True)
    pairs = channel_matched({k: raw[k] for k in pad if raw[k].shape[0] == 19})
    pairs = [p + ("" ,) for p in pairs]
    tgt = [k for k in raw if (k.startswith("ds004504:") or k.startswith("ds006036:")) and k.endswith(":raw")]
    pairs += [p + ("",) for p in agnostic_subset(raw, pad, tgt)]
    df = pd.DataFrame([p[:5] for p in pairs], columns=["recording_a", "recording_b", "score", "n_channels_used", "method"])
    df["method"] = np.where(df.recording_b.str.startswith("padic_israel:"), "column-matched (P-ADIC internal)", df.method)
    for c, i in [("cohort", 0), ("subject", 1)]:
        df[c + "_a"] = df.recording_a.str.split(":").str[i]
        df[c + "_b"] = df.recording_b.str.split(":").str[i]
    df["same_source_subject"] = (df.cohort_a == df.cohort_b) & (df.subject_a == df.subject_b)
    df["verdict"] = np.where(df.score >= dedup.SAME, "same signal", "review")
    path = os.path.join(dedup.CHK, "duplicate_pairs.csv")
    old = pd.read_csv(path)
    old = old[~(old.recording_a.str.startswith("padic_israel:") | old.recording_b.str.startswith("padic_israel:"))]
    pd.concat([old, df], ignore_index=True).sort_values("score", ascending=False).to_csv(path, index=False)
    print(df.groupby(["cohort_a", "cohort_b", "same_source_subject", "verdict"]).size())

    # metadata
    recs = [r for r in cohorts.padic_israel()]
    meta = pd.DataFrame([dict(recording_id=r.recording_id, subject=r.source_subject_id, group=r.group,
                              file_name=None, sex=r.sex, age=r.age, eegdate=r.extra["eegdate"],
                              repeat=r.extra["repeat_index"]) for r in recs])
    import h5py
    names = {}
    for fn, _, _, _ in cohorts.PADIC_FILES:
        p = os.path.join(cohorts.EXT, "padic_israel", "download", fn)
        with h5py.File(p, "r") as f:
            nm = [k for k in f.keys() if not k.startswith("#")][0]
            s = f[nm]
            for r in recs:
                if r.files[0] == p:
                    i, j = r.extra["cell"]
                    names[r.recording_id] = cohorts.padic_file_name(f, s, i, j)
    meta["file_name"] = meta.recording_id.map(names)
    out = []
    for key, how in [(["file_name"], "same original EEG file name"), (["sex", "age", "eegdate"], "same sex, age and EEG date")]:
        g = meta[meta[key].ne("").all(1)].groupby(key)
        for k, grp in g:
            if grp.subject.nunique() > 1:
                out.append(dict(rule=how, recordings=";".join(grp.recording_id), groups=";".join(grp.group)))
    mm = pd.DataFrame(out, columns=["rule", "recordings", "groups"])
    mm.to_csv(os.path.join(dedup.CHK, "padic_metadata_matches.csv"), index=False)
    # repeat recordings of one person: keep the date pattern only, to report the interval
    print("metadata matches across different P-ADIC subject IDs:", len(mm))
    print(mm.to_string())


if __name__ == "__main__":
    main()
