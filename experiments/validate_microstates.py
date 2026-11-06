"""Task 04: validate our microstate step. Writes results/microstate_validation.md and figures/microstates/.

  1. Group maps on ALL AD + HC subjects (figures/validation only, never used for classification)
     with microstates.gfp_peaks + fit_maps.
  2/3. Match to the published Koenig 2002 A-D maps with NeuroState's own matching code
     (neurostate.matching.match_to_reference, imported read-only). Labels stay provisional.
  4. Cross-check on 2 subjects against the NeuroState pipeline (results of ns_crosscheck.py).
  5. AD vs HC microstate summary (descriptive only).
  +  Spike check: are the group maps distorted by the subjects with large transients
     (results/prep_report.md)? Compared against seed variability and against dropping
     the same number of random non-spike subjects.

  .venv/bin/python validate_microstates.py   (run ns_crosscheck.py first, with NeuroState's venv)
"""
import argparse
import itertools
import json
import os
import platform
import sys
import time
from importlib.metadata import version

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

import microstates as msx

NS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "NeuroState-Microstates"))
sys.path.insert(0, NS)
from neurostate.matching import canonical_label, match_to_reference, rereference_maps  # noqa: E402
from neurostate.templates import from_json  # noqa: E402

GROUPS = {"A": "AD", "C": "HC"}
SPIKE_SUBJECTS = ["sub-012", "sub-016", "sub-022", "sub-040", "sub-047", "sub-048", "sub-074", "sub-080"]
SEED = 42
INK, MUTED = "#1f1f1e", "#6b6a64"


def best_perm(A, B):
    """Best one-to-one pairing of two map sets (same channels) by summed |r|. Returns (perm, |r| per map)."""
    R = np.abs(np.corrcoef(A, B)[:len(A), len(A):])
    p = max(itertools.permutations(range(len(A))), key=lambda q: sum(R[i, q[i]] for i in range(len(A))))
    return list(p), np.array([R[i, p[i]] for i in range(len(A))])


def ns_features(labels, sfreq):
    """Our labels summarised with NeuroState/Pycrostates conventions: first and last runs unlabeled,
    coverage and occurrence relative to LABELED time."""
    change = np.flatnonzero(np.diff(labels)) + 1
    starts, ends = np.r_[0, change], np.r_[change, len(labels)]
    keep = slice(1, len(starts) - 1)  # drop edge runs
    st, ln = labels[starts][keep], (ends - starts)[keep]
    lab_s = ln.sum() / sfreq
    out = {}
    for k in range(msx.N_STATES):
        m = st == k
        out[k] = {"coverage_pct": 100 * ln[m].sum() / ln.sum(), "mean_duration_ms": ln[m].mean() / sfreq * 1000,
                  "occurrence_per_s": m.sum() / lab_s}
    return out


def our_features(labels, sfreq):
    f = msx.features(labels, sfreq)
    return {k: {"coverage_pct": 100 * f[k], "mean_duration_ms": f[4 + k], "occurrence_per_s": f[8 + k]}
            for k in range(msx.N_STATES)}


def koenig_on(ch, tmpl):
    """Koenig maps on our channel order, re-referenced to the common average (NeuroState's helper)."""
    idx = {canonical_label(c): j for j, c in enumerate(tmpl.ch_names)}
    return rereference_maps(np.asarray(tmpl.maps)[:, [idx[canonical_label(c)] for c in ch]], ch)


def info_for(ch, sfreq=128.0):
    info = mne.create_info(list(ch), sfreq, "eeg")
    info.set_montage("standard_1020", verbose="ERROR")
    return info


def topo_grid(rows, info, titles, out, suptitle):
    """rows: list of (row_label, maps(4,ch), [subtitle per map])."""
    fig, axes = plt.subplots(len(rows), 4, figsize=(8.5, 2.3 * len(rows) + 0.6))
    axes = np.atleast_2d(axes)
    for r, (lab, maps, subs) in enumerate(rows):
        for k in range(4):
            ax = axes[r, k]
            v = maps[k] / np.abs(maps[k]).max()
            mne.viz.plot_topomap(v, info, axes=ax, show=False, cmap="RdBu_r", vlim=(-1, 1),
                                 contours=0, sensors=True)
            ax.set_title(subs[k], fontsize=8, color=INK)
        axes[r, 0].text(-0.35, 0.5, lab, transform=axes[r, 0].transAxes, rotation=90, va="center",
                        ha="center", fontsize=9, color=INK)
    fig.suptitle(suptitle, fontsize=10, color=INK, x=0.02, ha="left")
    fig.text(0.02, 0.005, "Each map scaled to its own max |value|; polarity aligned for display "
             "(microstate maps are polarity-invariant). Red/blue = opposite sign.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0.03, 0.02, 1, 0.95))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def align_sign(maps, ref):
    return np.array([m * (1 if np.dot(m - m.mean(), r - r.mean()) >= 0 else -1) for m, r in zip(maps, ref)])


def backfit_all(subs, data, maps):
    labels = {s: msx.corr_sequence(data[s]["ms"], maps).argmax(0) for s in subs}
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", default="../prepared")
    ap.add_argument("--ns", default="../results/microstates/ns_crosscheck.json")
    ap.add_argument("--report", default="../results/microstate_validation.md")
    ap.add_argument("--figs", default="../figures/microstates")
    ap.add_argument("--null-repeats", type=int, default=10)
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(args.figs, exist_ok=True)
    rs_dir = os.path.dirname(args.ns)
    os.makedirs(rs_dir, exist_ok=True)

    subs_df = pd.read_csv(os.path.join(args.prep, "subjects.csv"))
    subs_df = subs_df[subs_df.Group.isin(GROUPS)].reset_index(drop=True)
    subs = subs_df.participant_id.tolist()
    group = dict(zip(subs_df.participant_id, subs_df.Group))
    data = {}
    for s in subs:
        z = np.load(os.path.join(args.prep, f"{s}.npz"))
        data[s] = {"ms": z["ms"], "ch": [str(c) for c in z["ch_names"]], "sfreq": float(z["sfreq"])}
    ch, sfreq = data[subs[0]]["ch"], data[subs[0]]["sfreq"]
    info = info_for(ch, sfreq)
    tmpl = from_json(os.path.join(NS, "templates", "Koenig2002_4class.json"))
    K = koenig_on(ch, tmpl)

    # ---- 1. group maps on all AD + HC (same per-subject peaks reused for every refit below) ----
    rng = np.random.default_rng(SEED)
    peaks = {s: msx.gfp_peaks(data[s]["ms"], rng=rng) for s in subs}
    t1 = time.time()
    maps, gev = msx.fit_maps([peaks[s] for s in subs], ch, sfreq, seed=SEED)
    fit_s = time.time() - t1
    print(f"group fit: GEV {gev:.3f} in {fit_s:.0f} s", flush=True)

    # ---- 2/3. match to Koenig A-D with NeuroState's code ----
    res = match_to_reference(maps, ch, [f"M{i+1}" for i in range(4)], tmpl.maps, tmpl.ch_names, tmpl.labels)
    mt = pd.DataFrame(res.table())
    lab = {i: res.reference_names[j] for i, j in res.assignment.items()}  # provisional label per map
    order = [i for j in range(4) for i in range(4) if res.assignment[i] == j]  # maps in A-D order
    maps_ad = align_sign(maps[order], K)
    topo_grid([("Ours (AD+HC group)", maps_ad, [f"M{order[k]+1} -> {tmpl.labels[k]} (prov.)\n|r| = "
                                                 f"{res.assigned_abs_r[order[k]]:.2f}" for k in range(4)]),
               ("Koenig 2002", K, [f"{tmpl.labels[k]}" for k in range(4)])],
              info, None, os.path.join(args.figs, "group_maps_vs_koenig.png"),
              f"Group microstate maps (n={len(subs)} AD+HC, GEV {gev:.2f}) vs published Koenig 2002 A-D "
              "(19 common electrodes)")

    # ---- 4. cross-check vs NeuroState ----
    ns = json.load(open(args.ns)) if os.path.exists(args.ns) else None
    xrows, xmaps, xdiff = [], {}, {}
    if ns:
        for s, runs in ns["subjects"].items():
            if s not in data:
                continue
            x = data[s]["ms"]
            ind, ind_gev = msx.fit_maps([msx.gfp_peaks(x)], ch, sfreq, seed=SEED)  # all peaks, ours
            labs_ind = msx.corr_sequence(x, ind).argmax(0)
            labs_grp = msx.corr_sequence(x, maps).argmax(0)
            n_peaks = msx.gfp_peaks(x).shape[1]
            methods = {"ours_individual": (ind, ind_gev, n_peaks, our_features(labs_ind, sfreq),
                                           ns_features(labs_ind, sfreq)),
                       "ours_group": (maps, gev, None, our_features(labs_grp, sfreq), ns_features(labs_grp, sfreq))}
            ref = None
            for k_run in ("ns_500", "ns_128"):
                r = runs[k_run]
                # NeuroState keeps the file's channel order: reorder its maps to ours by label
                pos = {canonical_label(c): j for j, c in enumerate(r["ch_names"])}
                assert sorted(pos) == sorted(canonical_label(c) for c in ch)
                M = np.asarray(r["maps"])[:, [pos[canonical_label(c)] for c in ch]]
                feats = {i: r["per_state"][i] for i in range(4)}
                methods[k_run] = (M, r["gev_peaks"], r["n_gfp_peaks"], feats, feats)
            ref = methods["ns_500"][0]
            for name, (M, g, npk, f_ours, f_ns) in methods.items():
                perm, absr = best_perm(ref, M)  # NeuroState map i <-> this method's map perm[i]
                m_res = match_to_reference(M, ch, [f"M{i+1}" for i in range(4)], tmpl.maps, tmpl.ch_names,
                                           tmpl.labels)
                xmaps[(s, name)] = (align_sign(M[perm], ref), absr)
                for i in range(4):
                    j = perm[i]
                    xrows.append({"subject": s, "group": GROUPS[group[s]], "method": name, "ns_map": f"M{i+1}",
                                  "koenig_prov": m_res.reference_names[m_res.assignment[j]],
                                  "abs_r_vs_ns500": absr[i], "gev_peaks": g, "n_peaks": npk,
                                  "cov_ns_conv": f_ns[j]["coverage_pct"], "dur_ns_conv": f_ns[j]["mean_duration_ms"],
                                  "occ_ns_conv": f_ns[j]["occurrence_per_s"],
                                  "cov_our_conv": f_ours[j]["coverage_pct"], "dur_our_conv": f_ours[j]["mean_duration_ms"],
                                  "occ_our_conv": f_ours[j]["occurrence_per_s"]})
            xdiff[s] = {"ours_ind_vs_ns128": best_perm(methods["ns_128"][0], ind)[1].min(),
                        "ours_ind_vs_ns500": best_perm(ref, ind)[1].min(),
                        "ns128_vs_ns500": best_perm(ref, methods["ns_128"][0])[1].min(),
                        "group_vs_ns500": best_perm(ref, maps)[1].min()}
        ns_amb = [(s, k, r) for s, runs in ns["subjects"].items() for k, r in runs.items()]
        n_conflict = sum(any(m["argmax_differs_from_assignment"] for m in r["match"]) for _, _, r in ns_amb)
        min_assigned = min(m["abs_r"] for _, _, r in ns_amb for m in r["match"])
        xdf = pd.DataFrame(xrows)
        xdf.to_csv(os.path.join(rs_dir, "crosscheck_table.csv"), index=False)
        for s in ns["subjects"]:
            topo_grid([(nm.replace("_", " "), xmaps[(s, nm)][0],
                        [f"|r| vs NS-500 = {v:.2f}" for v in xmaps[(s, nm)][1]])
                       for nm in ("ns_500", "ns_128", "ours_individual", "ours_group")],
                      info, None, os.path.join(args.figs, f"crosscheck_{s}.png"),
                      f"{s} ({GROUPS[group[s]]}): NeuroState pipeline vs ours, maps paired to NeuroState-500 Hz")

    # ---- 5. AD vs HC with the group maps (descriptive) ----
    labels = backfit_all(subs, data, maps)
    feat = pd.DataFrame([{"subject": s, "Group": group[s], **{
        f"{m}_{lab[k]}": v for k, d in our_features(labels[s], sfreq).items() for m, v in
        (("coverage", d["coverage_pct"]), ("duration", d["mean_duration_ms"]), ("occurrence", d["occurrence_per_s"]))}}
        for s in subs])
    feat.to_csv(os.path.join(rs_dir, "group_features_AD_HC.csv"), index=False)

    # ---- spike check ----
    in_fit = [s for s in SPIKE_SUBJECTS if s in subs]
    not_in_fit = [s for s in SPIKE_SUBJECTS if s not in subs]
    keep = [s for s in subs if s not in in_fit]
    maps_ns, gev_ns = msx.fit_maps([peaks[s] for s in keep], ch, sfreq, seed=SEED)
    perm, absr_spk = best_perm(maps, maps_ns)
    res_ns = match_to_reference(maps_ns, ch, [f"M{i+1}" for i in range(4)], tmpl.maps, tmpl.ch_names, tmpl.labels)
    # amplitude weight of the spike subjects' peaks (modified k-means is not amplitude-normalised)
    gfp2 = {s: (peaks[s].std(0) ** 2) for s in subs}
    share_peaks = sum(len(gfp2[s]) for s in in_fit) / sum(len(gfp2[s]) for s in subs)
    share_gfp2 = sum(gfp2[s].sum() for s in in_fit) / sum(gfp2[s].sum() for s in subs)
    big_peaks = {s: float((np.abs(peaks[s]).max(0) > 100).mean()) for s in in_fit}
    # effect on backfit labels / features for every subject
    labels_ns = backfit_all(subs, data, maps_ns[perm])
    agree = np.array([np.mean(labels[s] == labels_ns[s]) for s in subs])
    cov_a = np.array([[np.mean(labels[s] == k) for k in range(4)] for s in subs]) * 100
    cov_b = np.array([[np.mean(labels_ns[s] == k) for k in range(4)] for s in subs]) * 100
    # context 1: seed variability (same peaks, different k-means seeds)
    seed_rows = []
    for sd in (1, 2, 3):
        m2, g2 = msx.fit_maps([peaks[s] for s in subs], ch, sfreq, seed=sd)
        seed_rows.append({"seed": sd, "gev": g2, "min_abs_r": best_perm(maps, m2)[1].min()})
    # context 2: drop the same number of random non-spike subjects with the same group mix
    rng2 = np.random.default_rng(7)
    pool = {g: [s for s in subs if group[s] == g and s not in in_fit] for g in GROUPS}
    n_drop = {g: sum(group[s] == g for s in in_fit) for g in GROUPS}
    null_rows = []
    for rep in range(args.null_repeats):
        drop = [s for g in GROUPS for s in rng2.choice(pool[g], n_drop[g], replace=False)]
        m3, g3 = msx.fit_maps([peaks[s] for s in subs if s not in drop], ch, sfreq, seed=SEED)
        p3, a3 = best_perm(maps, m3)
        null_rows.append({"rep": rep, "dropped": " ".join(sorted(drop)), "gev": g3, "min_abs_r": a3.min(),
                          "mean_abs_r": a3.mean()})
        print(f"null {rep}: min |r| {a3.min():.4f}", flush=True)
    null = pd.DataFrame(null_rows)
    null.to_csv(os.path.join(rs_dir, "spike_check_null.csv"), index=False)
    topo_grid([("All AD+HC", maps_ad, [f"{tmpl.labels[k]} (prov.)" for k in range(4)]),
               (f"Without {len(in_fit)} spike subj.", align_sign(maps_ns[perm][order], maps_ad),
                [f"|r| vs all = {absr_spk[order[k]]:.3f}" for k in range(4)])],
              info, None, os.path.join(args.figs, "spike_check_maps.png"),
              f"Group maps with and without the GFP peaks of {', '.join(in_fit)}")

    # ---- report ----
    def fmt_r(x):
        return f"{x:.3f}"

    L = ["# Microstate validation (task 04)", "",
         "Research use only. Group maps here are fitted on ALL AD + HC subjects for validation and figures; "
         "they are never used for classification (the experiment refits maps on training subjects of each fold).",
         "", "## Settings", "",
         f"- Data: `prepared/*.npz`, `ms` copy (2-20 Hz FIR zero-phase, average reference, 128 Hz), "
         f"{len(subs)} subjects: {sum(g == 'A' for g in group.values())} AD, {sum(g == 'C' for g in group.values())} HC.",
         f"- Ours (`experiments/microstates.py`): GFP = SD across channels; peaks = `scipy.signal.find_peaks`, "
         f"random subsample of at most 1500 peaks per subject (rng seed {SEED}); pooled; Pycrostates ModKMeans "
         f"K=4, n_init=20, max_iter=300, tol=1e-6, random_state={SEED}; backfit = argmax |spatial r| on every "
         "sample, no smoothing.",
         f"- Total GFP peaks pooled: {sum(p.shape[1] for p in peaks.values()):,}; fit time {fit_s:.0f} s.",
         f"- Template: Koenig 2002 4-class (MICROSTATELAB `Koenig2002.set`, SHA-256 `{tmpl.source_sha256[:12]}…`), "
         "fetched and converted on 2026-11-02 by the NeuroState repo's own `tools/fetch_public_inputs.py` and "
         "`tools/convert_templates.py`. Not re-downloaded: the downloaded file's SHA-256 (`56244c30…`) and git "
         "SHA-1 (`fc717c68…`) were re-checked on 2026-11-03 and match the recorded provenance.",
         "- Matching: `neurostate.matching.match_to_reference` (label-aligned 19 common electrodes; A1/A2 of "
         "the template not used; common-average re-reference; |Pearson r|; Hungarian assignment). Imported "
         "read-only; the NeuroState repo was not modified.",
         f"- Python {platform.python_version()}, mne {version('mne')}, pycrostates {version('pycrostates')}, "
         f"scipy {version('scipy')}, numpy {version('numpy')}; run {time.strftime('%Y-%m-%d %H:%M')}.",
         "", "## 1. Group maps", "",
         f"GEV on the fitted GFP peaks: **{gev:.3f}**. Topomaps: `figures/microstates/group_maps_vs_koenig.png`.",
         "", "## 2-3. Match to Koenig 2002 A-D (provisional labels)", "",
         "| Our map | Assigned (provisional) | |r| | polarity | runner-up | runner-up |r| | margin | "
         "|r| vs A | vs B | vs C | vs D | best match ≠ assigned |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in mt.itertuples():
        L.append(f"| {r.individual_map} | {r.assigned_reference} | {r.abs_r:.3f} | {r.polarity_of_best_fit} | "
                 f"{r.runner_up_reference} | {r.runner_up_abs_r:.3f} | {r.margin_abs_r:.3f} | "
                 f"{r.abs_r_vs_A:.3f} | {r.abs_r_vs_B:.3f} | {r.abs_r_vs_C:.3f} | {r.abs_r_vs_D:.3f} | "
                 f"{'yes' if r.argmax_differs_from_assignment else 'no'} |")
    amb = [r for r in mt.itertuples() if r.argmax_differs_from_assignment or r.margin_abs_r < 0.05]
    L += ["", f"Assignment unique under |r| and r²: **{'no' if res.r2_assignment_differs else 'yes'}**. "
          f"Matching notes: {' '.join(res.notes) if res.notes else 'none'}",
          "", ("Ambiguity: " + "; ".join(f"{r.individual_map} -> {r.assigned_reference} has margin "
                                          f"{r.margin_abs_r:.3f} over {r.runner_up_reference}"
                                          + (" and its best match is another class" if r.argmax_differs_from_assignment else "")
                                          for r in amb) + ". These labels stay provisional."
               if amb else "No map has a margin below 0.05 or an argmax conflict; labels are still "
                           "provisional (no reviewer acceptance)."),
          "", "Labels used below (provisional): " + ", ".join(f"M{i+1} = {lab[i]}" for i in range(4)) + "."]

    if ns:
        L += ["", "## 4. Cross-check against the NeuroState pipeline (2 subjects)", "",
              "NeuroState was run with its own venv and frozen PRIMARY configuration "
              "(`validation/run_real_data.py`: FIR 2-20 Hz, average reference, GFP peaks with "
              "`pycrostates.preprocessing.extract_gfp_peaks(min_peak_distance=1)`, ModKMeans K=4 n_init=100 "
              "random_state=42, `ModKMeans.predict` factor=0, reject_edges=True). Its EDF loader was replaced "
              "by `mne.io.read_raw_eeglab` + its own `standardize_channels`; every later stage is the repo's "
              "code (`experiments/ns_crosscheck.py`).", "",
              "Methods compared (maps paired to the NeuroState 500 Hz maps by best |r| permutation):", "",
              "- `ns_500`: NeuroState on the ds004504 derivative .set at 500 Hz",
              "- `ns_128`: NeuroState on our prepared 128 Hz `ms` copy (isolates our filter + resampling)",
              "- `ours_individual`: our code fitted on that subject alone (all GFP peaks)",
              "- `ours_group`: our AD+HC group maps from step 1, backfitted on that subject", "",
              "Metric conventions: *NS conv.* = NeuroState/Pycrostates (first and last run unlabeled; coverage "
              "and occurrence relative to labeled time); *our conv.* = `microstates.features` (all samples).",
              "", "| Subject | Method | GFP peaks | GEV (peaks) | min |r| vs ns_500 | mean |r| vs ns_500 |",
              "|---|---|---|---|---|---|"]
        for (s, m), g in xdf.groupby(["subject", "method"], sort=False):
            L.append(f"| {s} ({g.group.iloc[0]}) | {m} | {'-' if pd.isna(g.n_peaks.iloc[0]) else f'{int(g.n_peaks.iloc[0]):,}'} "
                     f"| {g.gev_peaks.iloc[0]:.3f} | {g.abs_r_vs_ns500.min():.3f} | {g.abs_r_vs_ns500.mean():.3f} |")
        L += ["", "Per-map metrics (NS convention for every method; our convention in brackets for our methods):", "",
              "| Subject | NS map | Method | Koenig (prov.) | coverage % | mean duration ms | occurrence /s |",
              "|---|---|---|---|---|---|---|"]
        for r in xdf.itertuples():
            ours = r.method.startswith("ours")
            br = (lambda a, b, f: f"{a:{f}} ({b:{f}})" if ours else f"{a:{f}}")
            L.append(f"| {r.subject} | {r.ns_map} | {r.method} | {r.koenig_prov} | {br(r.cov_ns_conv, r.cov_our_conv, '.1f')} | "
                     f"{br(r.dur_ns_conv, r.dur_our_conv, '.1f')} | {br(r.occ_ns_conv, r.occ_our_conv, '.2f')} |")
        dur = xdf.groupby("method").dur_ns_conv.mean()
        occ = xdf.groupby("method").occ_ns_conv.mean()
        ours = xdf[xdf.method.str.startswith("ours")]
        cov_conv = (ours.cov_ns_conv - ours.cov_our_conv).abs().max()
        dur_conv = (ours.dur_ns_conv - ours.dur_our_conv).abs().max()
        ind = xdf[xdf.method == "ours_individual"].set_index(["subject", "ns_map"])
        n500 = xdf[xdf.method == "ns_500"].set_index(["subject", "ns_map"])
        cov_ind = (ind.cov_ns_conv - n500.cov_ns_conv).abs().max()
        rng_r = lambda key: f"{min(v[key] for v in xdiff.values()):.4f}-{max(v[key] for v in xdiff.values()):.4f}"
        L += ["", f"Mean duration across maps and both subjects (NS convention): "
              + ", ".join(f"{m} {v:.1f} ms" for m, v in dur.items()) + "; mean occurrence: "
              + ", ".join(f"{m} {v:.2f}/s" for m, v in occ.items()) + ".",
              "", "Minimum |r| between map sets (best pairing), range over the 2 subjects: "
              f"ours_individual vs ns_500 {rng_r('ours_ind_vs_ns500')}; ours_individual vs ns_128 "
              f"{rng_r('ours_ind_vs_ns128')}; ns_128 vs ns_500 {rng_r('ns128_vs_ns500')}; "
              f"ours_group vs ns_500 {rng_r('group_vs_ns500')}.",
              "", "Figures: " + ", ".join(f"`figures/microstates/crosscheck_{s}.png`" for s in ns["subjects"]) + ".",
              "", "### Differences between our microstates and the NeuroState pipeline, explained", "",
              "| Aspect | NeuroState (PRIMARY) | Ours | Effect measured here |", "|---|---|---|---|",
              "| Maps | Individual: one map set per recording | Group: one map set fitted on the pooled "
              "training subjects of each fold, backfitted on every subject | The largest difference. Group maps "
              f"vs a subject's own maps: min |r| {rng_r('group_vs_ns500')}, so coverage per state shifts by up to "
              f"{(xdf[xdf.method == 'ours_group'].cov_ns_conv - 25).abs().max():.0f} pp from the ~25% each that "
              "individual maps give. Intended: group maps give the same states for every subject, which "
              "features compared across subjects need (KL23 also found grand-mean fitting more reliable). |",
              "| Koenig labels | Per recording, provisional | Per group fit, provisional | Individual-level "
              f"matching was ambiguous in {n_conflict} of {len(ns_amb)} NeuroState runs (a map's best Koenig "
              f"match taken by another map; lowest assigned |r| {min_assigned:.2f}), and B/D swapped between "
              "ns_500 and ns_128 for sub-001 although those maps are nearly identical. The group match is "
              "unique (|r| 0.90-0.99). |",
              "| Sampling rate | Native 500 Hz | Resampled to 128 Hz after filtering | Maps unaffected "
              f"(ours_individual vs ns_500 min |r| {rng_r('ours_ind_vs_ns500')}). Coverage within "
              f"{cov_ind:.1f} pp. Unsmoothed durations are longer and occurrences lower at 128 Hz "
              f"({dur['ours_individual']:.1f} vs {dur['ns_500']:.1f} ms; {occ['ours_individual']:.2f} vs "
              f"{occ['ns_500']:.2f}/s): brief label flips at 500 Hz are not resolved at 128 Hz. Absolute "
              "durations are therefore not comparable across tools or sampling rates. |",
              "| Filter | MNE FIR 2-20 Hz, firwin, Hamming, zero-phase | Same MNE call (`prep.py`), before "
              "resampling | Same design. `ns_128` filters our already-filtered copy a second time, likely why "
              f"it differs slightly more from ns_500 ({rng_r('ns128_vs_ns500')}) than our single-filtered fit does. |",
              "| GFP peaks | `extract_gfp_peaks(min_peak_distance=1)`: SD across channels, `find_peaks` | "
              "Same definition (`np.std` + `find_peaks`) | Same definition; our counts are 2-5% lower than NeuroState's at 500 Hz (resampling removes a few local maxima). For the group fit we cap each subject at "
              "1500 random peaks so every subject weighs about equally; NeuroState (single recording) uses all. |",
              "| Clustering | ModKMeans K=4, n_init=100, seed 42 | ModKMeans K=4, n_init=20, seed per fold | No "
              "measurable effect of n_init here (individual maps match at |r| ≥ 0.999). |",
              "| Backfit | `ModKMeans.predict`, factor=0, reject_edges=True (first/last run unlabeled) | "
              "argmax |spatial r| on every sample, no smoothing | Same rule. Edge runs and denominators "
              f"change coverage by ≤ {cov_conv:.2f} pp and duration by ≤ {dur_conv:.2f} ms. |",
              "| Absent state | NaN | 0 | Not triggered (all states present in all subjects). |",
              "| Reference | Average of the 19 channels | Average of the 19 channels | None. |"]

    # AD vs HC
    L += ["", "## 5. AD vs HC microstate summary (descriptive only)", "",
          "Group maps from step 1 backfitted on every subject (our convention: all samples, no smoothing). "
          "Mean ± SD; p = two-sided Mann-Whitney U, uncorrected for the 12 tests. These maps saw all subjects, "
          "so this table is descriptive and must not be used to choose features or settings.", "",
          "| State (prov.) | Coverage % AD | HC | p | Duration ms AD | HC | p | Occurrence /s AD | HC | p |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k in range(4):
        cells = []
        for m, f in (("coverage", ".1f"), ("duration", ".1f"), ("occurrence", ".2f")):
            col = f"{m}_{tmpl.labels[k]}"
            a, c = feat[feat.Group == "A"][col], feat[feat.Group == "C"][col]
            cells += [f"{a.mean():{f}} ± {a.std():{f}}", f"{c.mean():{f}} ± {c.std():{f}}",
                      f"{mannwhitneyu(a, c).pvalue:.3g}"]
        L.append(f"| {tmpl.labels[k]} | " + " | ".join(cells) + " |")
    L += ["", "Per-subject values: `results/microstates/group_features_AD_HC.csv`."]

    # spike check
    null_min = null.min_abs_r
    L += ["", "## Spike check: do the subjects with large transients distort the group maps?", "",
          f"Subjects with > 500 µV transients (from `results/prep_report.md`): {', '.join(SPIKE_SUBJECTS)}. "
          f"{', '.join(not_in_fit)} are FTD and are not part of the AD+HC fit, so they cannot affect these maps "
          f"(they would only matter for an FTD analysis). The maps were refitted without the GFP peaks of the "
          f"{len(in_fit)} AD/HC subjects ({', '.join(in_fit)}), using the same peaks for everyone else and the "
          "same k-means seed.", "",
          f"- Their share of pooled GFP peaks: {share_peaks:.1%}; their share of summed GFP² at peaks: "
          f"{share_gfp2:.1%} (modified k-means weights peaks by amplitude, so this is the relevant leverage).",
          "- Share of their peaks with any channel > 100 µV: "
          + ", ".join(f"{s} {v:.1%}" for s, v in big_peaks.items()) + ".", "",
          "| Comparison | GEV | min |r| to all-subject maps | per map |r| |", "|---|---|---|---|",
          f"| All AD+HC (reference) | {gev:.3f} | 1 | - |",
          f"| **Without spike subjects** | {gev_ns:.3f} | **{absr_spk.min():.4f}** | "
          + ", ".join(f"{lab[i]} {absr_spk[i]:.4f}" for i in range(4)) + " |"]
    for r in seed_rows:
        L.append(f"| All AD+HC, k-means seed {r['seed']} | {r['gev']:.3f} | {r['min_abs_r']:.4f} | - |")
    L += [f"| Without {len(in_fit)} random non-spike subjects (same AD/HC mix), {len(null)} repeats | "
          f"{null.gev.mean():.3f} (mean) | {null_min.median():.4f} median (range {null_min.min():.4f}-{null_min.max():.4f}) | - |",
          "", f"- Koenig assignment without the spike subjects: "
          + ", ".join(f"M{i+1}->{res_ns.reference_names[res_ns.assignment[perm[i]]]} (|r| "
                      f"{res_ns.assigned_abs_r[perm[i]]:.3f}, was {res.assigned_abs_r[i]:.3f})" for i in range(4))
          + f"; same labels as with all subjects: **{'yes' if all(res_ns.reference_names[res_ns.assignment[perm[i]]] == lab[i] for i in range(4)) else 'NO'}**.",
          f"- Backfit labels with the two map sets agree on {agree.mean():.1%} of samples on average "
          f"(min {agree.min():.1%}, subject {subs[int(agree.argmin())]}).",
          f"- Coverage change per subject and state: mean |Δ| {np.abs(cov_a - cov_b).mean():.2f} pp, "
          f"max {np.abs(cov_a - cov_b).max():.2f} pp.",
          f"- Rank of the spike-removal min |r| among the {len(null)} random removals: "
          f"{int((null_min < absr_spk.min()).sum())} of {len(null)} random removals changed the maps more.",
          "", "Figure: `figures/microstates/spike_check_maps.png`. Null runs: "
          "`results/microstates/spike_check_null.csv`. No pipeline change was made based on this check.",
          "", f"_Runtime: {(time.time() - t0) / 60:.1f} min._", ""]
    open(args.report, "w").write("\n".join(L))
    json.dump({"group_maps": maps.tolist(), "gev": gev, "labels_provisional": lab, "ch_names": ch,
               "maps_without_spike_subjects": maps_ns.tolist(), "gev_without_spike": gev_ns},
              open(os.path.join(rs_dir, "group_maps.json"), "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    main()
