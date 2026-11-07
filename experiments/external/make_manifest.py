"""Assign global participant IDs and write data/manifest.csv (one row per recording).

Inputs: cohorts.py registry, data/checks/verification.csv, data/checks/duplicate_pairs.csv,
data/checks/metadata_ds006036_vs_ds004504.csv, data/checksums_sha256.tsv.

Global IDs: union-find over (cohort_id, source_subject_id) nodes. Two nodes are joined when
  (a) the source states they are the same people AND the metadata agree (ds006036 <-> ds004504), or
  (b) the signal test finds the same signal (score >= 0.95) for recordings of the two nodes.
Every join is written to data/checks/global_ids.csv with its evidence.
"""
import hashlib
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import cohorts  # noqa: E402

CHK = os.path.join(cohorts.ROOT, "data", "checks")
ORDER = ["ds004504", "ds006036", "ds005048", "hk_czech", "apava_spain", "fsu_duke", "adsz_fsu", "padic_israel"]
RESTING = {"eyes_closed", "eyes_open", "rest_eo_ec_mixed"}

# Recording-level findings from the checks (participant IDs with labels) live outside the code,
# in the git-ignored file data/checks/known_issues.json: {recording_id: note}.
KNOWN_ISSUES_FILE = os.path.join(CHK, "known_issues.json")
KNOWN_ISSUES = json.load(open(KNOWN_ISSUES_FILE)) if os.path.exists(KNOWN_ISSUES_FILE) else {}
COHORT_ISSUES = {
    "hk_czech": "channel labels/order not documented; AD, MCI and two control recordings are per-segment 'export' files (mV, 17-20 columns, 128 or 256 Hz) while 100 controls are 'fir.mat' files (uV, 22/25 rows with zero-padded rows, 128 Hz, ~70 s): format separates the groups",
    "padic_israel": "channel order not stored; controls are clinical referrals (younger) not cognitively assessed; eyes open/closed not marked",
    "fsu_duke": "8-s segments only",
    "adsz_fsu": "every subject is a copy of an fsu_duke subject (same signals); some eyes-open files are longer (10-14 s) versions of the 8-s fsu_duke segments",
    "apava_spain": "AD/control labels from Smith et al. 2017 (patient1_control0 in SpainADdata.mat; file order confirmed by PLI matching); 16 channels",
    "ds005048": "40 Hz auditory stimulation task, already ICA-cleaned",
    "ds006036": "photic stimulation, same participants and session as ds004504",
}


class UF:
    def __init__(self):
        self.p, self.why = {}, {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b, why):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb, key=lambda n: (ORDER.index(n[0]), n[1]))] = min(ra, rb, key=lambda n: (ORDER.index(n[0]), n[1]))
        self.why.setdefault(a, []).append(f"{b[0]}:{b[1]} ({why})")
        self.why.setdefault(b, []).append(f"{a[0]}:{a[1]} ({why})")


def main():
    recs = list(cohorts.all_recordings())
    ver = pd.read_csv(os.path.join(CHK, "verification.csv")).set_index("recording_id")
    sums = pd.read_csv(os.path.join(cohorts.ROOT, "data", "checksums_sha256.tsv"), sep="\t").set_index("path")["sha256"].to_dict()
    uf = UF()
    nodes = {(r.cohort_id, r.source_subject_id) for r in recs}
    for n in nodes:
        uf.find(n)
    # (a) documented companion release, confirmed by metadata
    meta = pd.read_csv(os.path.join(CHK, "metadata_ds006036_vs_ds004504.csv"), dtype=str)
    for r in meta.itertuples():
        ok = all(getattr(r, c + "_match") == "True" for c in ["Gender", "Age", "Group", "MMSE"])
        if ok and ("ds006036", r.participant_id) in nodes and ("ds004504", r.participant_id) in nodes:
            uf.union(("ds006036", r.participant_id), ("ds004504", r.participant_id),
                     "README: participant numbers match ds004504; sex, age, group, MMSE identical")
    # (b) same signal
    dp = pd.read_csv(os.path.join(CHK, "duplicate_pairs.csv"))
    rid2node = {r.recording_id: (r.cohort_id, r.source_subject_id) for r in recs}
    for r in dp[dp.verdict == "same signal"].itertuples():
        a, b = rid2node.get(r.recording_a), rid2node.get(r.recording_b)
        if a and b and a != b:
            uf.union(a, b, f"same signal, r={r.score:.3f} ({r.method})")
    roots = sorted({uf.find(n) for n in nodes}, key=lambda n: (ORDER.index(n[0]), n[1]))
    gid = {root: f"EXT{i+1:04d}" for i, root in enumerate(roots)}
    gl = pd.DataFrame([(n[0], n[1], gid[uf.find(n)], "; ".join(sorted(set(uf.why.get(n, []))))) for n in sorted(nodes)],
                      columns=["cohort_id", "source_subject_id", "global_participant_id", "linked_to"])
    gl.to_csv(os.path.join(CHK, "global_ids.csv"), index=False)

    rows = []
    for r in recs:
        v = ver.loc[r.recording_id] if r.recording_id in ver.index else pd.Series(dtype=object)
        first = r.files[0] if r.files else os.path.join(cohorts.ROOT, r.path)
        files = sorted(r.files) if not os.path.isdir(first) else sorted(
            os.path.join(first, f) for f in os.listdir(first) if not f.startswith("."))
        hs = [(os.path.basename(f), sums.get(cohorts.rel(f), "")) for f in files]
        if len(hs) == 1:
            sha = hs[0][1]
        elif len(hs) == 0:
            sha = ""
        elif len(hs) <= 2:
            sha = ";".join(f"{n}:{h}" for n, h in hs)
        else:  # many files (segments / one file per channel): hash of the sorted name<TAB>sha256 list
            sha = "tree:" + hashlib.sha256("\n".join(f"{n}\t{h}" for n, h in hs).encode()).hexdigest()
        if any(h == "" for _, h in hs):
            sha = "INCOMPLETE:" + sha
        if "slice" in r.extra:  # one subject inside a multi-subject matrix file
            sha = f"{hs[0][1]}[subject index {r.extra['slice']}]"
        readable = bool(v.get("readable", False))
        labels_known = isinstance(v.get("channel_names"), str) and not str(v.get("channel_names")).startswith("unlabelled")
        url, lic = cohorts.SOURCES[r.cohort_id]
        rows.append(dict(
            cohort_id=r.cohort_id, source_subject_id=r.source_subject_id,
            global_participant_id=gid[uf.find((r.cohort_id, r.source_subject_id))],
            recording_id=r.recording_id, diagnosis_given=r.diagnosis_given, harmonised_group=r.group,
            recording_condition=r.condition, processing=r.processing, file_path=r.path, format=r.fmt,
            n_channels=v.get("n_channels", ""), channel_names=v.get("channel_names", ""),
            channel_labels_known=labels_known, sampling_rate=v.get("sfreq", ""), duration_s=v.get("duration_s", ""),
            n_segments=v.get("n_segments", ""), age=r.age, sex=r.sex, sha256=sha, source_url=url, licence=lic,
            readable=readable,
            verification_problems="; ".join(x for x in [v.get("problems", "") if isinstance(v.get("problems", ""), str) else "",
                                                        KNOWN_ISSUES.get(r.recording_id, "")] if x),
            cohort_caveats=COHORT_ISSUES.get(r.cohort_id, ""),
            mmse_or_m=r.extra.get("MMSE", r.extra.get("m_undocumented", "")),
            repeat_recording_index=r.extra.get("repeat_index", ""),
            in_primary_ad_hc_resting=bool(readable and r.group in ("AD", "HC") and r.condition in RESTING),
        ))
    m = pd.DataFrame(rows)
    # one real person with conflicting harmonised labels -> keep rows, but outside the primary set
    grp_sets = m[m.harmonised_group != "unclear"].groupby("global_participant_id").harmonised_group.agg(lambda s: set(s))
    conflict = grp_sets[grp_sets.map(len) > 1]
    for g, labels in conflict.items():
        sel = m.global_participant_id == g
        m.loc[sel, "in_primary_ad_hc_resting"] = False
        note = "conflicting diagnosis labels for the same person across records (" + "/".join(sorted(labels)) + "): excluded from the primary set"
        m.loc[sel, "verification_problems"] = m.loc[sel, "verification_problems"].map(lambda x: "; ".join(t for t in [x, note] if t))
    print("participants with conflicting labels:", dict(conflict.map(sorted)))
    m.to_csv(os.path.join(cohorts.ROOT, "data", "manifest.csv"), index=False)
    print(len(m), "rows;", m.global_participant_id.nunique(), "global participants")
    p = m[m.in_primary_ad_hc_resting]
    print(p.groupby(["cohort_id", "harmonised_group"]).global_participant_id.nunique().unstack(fill_value=0))
    print("unique primary participants:", p.groupby("harmonised_group").global_participant_id.nunique().to_dict())


if __name__ == "__main__":
    main()
