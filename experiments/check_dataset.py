"""Verify the ds004504 download and write results/dataset_check.md (task 02).

Checks: participant/group counts, raw + derivative .set present for every subject,
every file opens in MNE (channels, sampling rate, duration), dataset version,
total size, SHA-256 of every .set file.

  .venv/bin/python check_dataset.py --bids ../ds004504 --out ../results/dataset_check.md
"""
import argparse
import hashlib
import json
import os
import platform
import time
from importlib.metadata import version

import mne
import pandas as pd

EXPECTED = {"A": 36, "F": 23, "C": 29}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def set_path(root, sub, deriv):
    base = os.path.join(root, "derivatives") if deriv else root
    return os.path.join(base, sub, "eeg", f"{sub}_task-eyesclosed_eeg.set")


def header(path):
    raw = mne.io.read_raw_eeglab(path, preload=False, verbose="error")
    return {"n_ch": len(raw.ch_names), "sfreq": raw.info["sfreq"],
            "dur_s": raw.n_times / raw.info["sfreq"], "ch": raw.ch_names}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bids", default="../ds004504")
    ap.add_argument("--out", default="../results/dataset_check.md")
    args = ap.parse_args()
    t0 = time.time()
    root = args.bids

    part = pd.read_csv(os.path.join(root, "participants.tsv"), sep="\t")
    counts = part.Group.value_counts().to_dict()
    desc = json.load(open(os.path.join(root, "dataset_description.json")))
    changes = open(os.path.join(root, "CHANGES")).readline().strip()
    folders = sorted(d for d in os.listdir(root) if d.startswith("sub-"))
    deriv_folders = sorted(d for d in os.listdir(os.path.join(root, "derivatives"))
                           if d.startswith("sub-"))

    rows, missing, unreadable = [], [], []
    for sub in part.participant_id:
        for kind, deriv in (("raw", False), ("derivative", True)):
            p = set_path(root, sub, deriv)
            if not os.path.isfile(p):
                missing.append(p)
                continue
            try:
                h = header(p)
            except Exception as e:  # report, do not stop
                unreadable.append(f"{p}: {e}")
                continue
            rows.append({"subject": sub, "kind": kind, "path": os.path.relpath(p, root),
                         "bytes": os.path.getsize(p), "sha256": sha256(p), **h})
    df = pd.DataFrame(rows)

    total = sum(os.path.getsize(os.path.join(d, f))
                for d, _, fs in os.walk(root) for f in fs)
    mtimes = [os.path.getmtime(os.path.join(root, r)) for r in df.path]
    st = os.stat(root)
    birth = getattr(st, "st_birthtime", st.st_ctime)
    ch_sets = df.ch.apply(tuple).value_counts()
    group = part.set_index("participant_id").Group

    ok_counts = len(part) == 88 and all(counts.get(g) == n for g, n in EXPECTED.items())
    ok = ok_counts and not missing and not unreadable and set(folders) == set(part.participant_id)

    L = ["# ds004504 dataset check", "",
         f"**Result: {'PASS' if ok else 'FAIL'}**"
         f" — {len(part)} subjects, A={counts.get('A')}, F={counts.get('F')}, C={counts.get('C')};"
         f" {len(missing)} missing and {len(unreadable)} unreadable .set files.", "",
         "## Dataset", "",
         f"- Name: {desc['Name']}",
         f"- Version / DOI: {desc['DatasetDOI']} (CHANGES top entry: `{changes}`)",
         f"- BIDS version: {desc['BIDSVersion']}; licence: {desc['License']}",
         f"- Local path: `{os.path.abspath(root)}`",
         f"- Total size: {total / 2**30:.2f} GiB = {total / 1e9:.2f} GB ({total:,} bytes)",
         f"- Download date (not logged; creation time of the local folder): "
         f"{time.strftime('%Y-%m-%d', time.localtime(birth))}. The .set modification times "
         f"({time.strftime('%Y-%m-%d', time.localtime(min(mtimes)))}) are the original upload "
         f"times kept by the download, not the download date.",
         f"- Check run: {time.strftime('%Y-%m-%d %H:%M')}, Python {platform.python_version()},"
         f" mne {version('mne')}, pandas {version('pandas')}", "",
         "Derivatives are already preprocessed by the dataset authors (0.5-45 Hz band-pass, "
         "ASR, ICA); state this in the paper's data section.", "",
         "## Participants", "",
         "| Group | Expected | Found |", "|---|---|---|"]
    for g, n in EXPECTED.items():
        L.append(f"| {g} | {n} | {counts.get(g, 0)} |")
    L += [f"| Total | 88 | {len(part)} |", "",
          f"- `sub-*` folders at top level: {len(folders)}; in `derivatives/`: {len(deriv_folders)}",
          f"- Folders not in participants.tsv: {sorted(set(folders) - set(part.participant_id)) or 'none'}",
          "", "## Files", "",
          f"- Raw .set found: {(df.kind == 'raw').sum()} / {len(part)}",
          f"- Derivative .set found: {(df.kind == 'derivative').sum()} / {len(part)}",
          f"- Missing: {', '.join(missing) if missing else 'none'}",
          f"- Unreadable by MNE: {'; '.join(unreadable) if unreadable else 'none'}",
          "- Signal data is stored inside each .set (no separate .fdt files).", "",
          "## Recording properties (read from file headers)", ""]
    for kind, g in df.groupby("kind"):
        L.append(f"- {kind}: channels {sorted(int(n) for n in g.n_ch.unique())}, sampling rate "
                 f"{sorted(float(f) for f in g.sfreq.unique())} Hz, duration {g.dur_s.min():.1f}-{g.dur_s.max():.1f} s "
                 f"(median {g.dur_s.median():.1f} s)")
    L.append(f"- Distinct channel lists across all files: {len(ch_sets)}"
             + (f" (`{', '.join(ch_sets.index[0])}`)" if len(ch_sets) == 1 else ""))
    d = df[df.kind == "derivative"].assign(Group=lambda x: x.subject.map(group))
    L += ["", "Derivative recording length by group (minutes, mean ± SD):", ""]
    for g in EXPECTED:
        m = d[d.Group == g].dur_s / 60
        L.append(f"- {g}: {m.mean():.1f} ± {m.std():.1f} (min {m.min():.1f}, max {m.max():.1f})")
    L += ["", "## SHA-256 of .set files", "", "```"]
    L += [f"{r.sha256}  {r.path}" for r in df.sort_values("path").itertuples()]
    L += ["```", "", f"_Runtime: {time.time() - t0:.0f} s._", ""]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write("\n".join(L))
    print("\n".join(L[:45]))


if __name__ == "__main__":
    main()
