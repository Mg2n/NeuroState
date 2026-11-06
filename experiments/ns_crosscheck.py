"""Task 04 step 4: run the NeuroState-Microstates pipeline (unmodified, imported read-only) on 2 subjects.

Run with the NeuroState repo's OWN venv:
  ../NeuroState-Microstates/.venv/bin/python ns_crosscheck.py --subs sub-001 sub-037

NeuroState only loads EDF, so the load stage is built here (MNE read_raw_eeglab + the repo's
standardize_channels); every later stage is the repo's own run_preprocess / run_fit / run_match /
run_backfit with its frozen PRIMARY configuration (validation/run_real_data.py).

Two inputs per subject:
  ns_500 : ds004504 derivative .set at 500 Hz (NeuroState filters 2-20 Hz itself)
  ns_128 : our prepared `ms` copy (2-20 Hz, 128 Hz) -> isolates the effect of our filter + resampling
"""
import argparse
import json
import os
import sys
import time

import mne
import numpy as np

NS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "NeuroState-Microstates"))
sys.path.insert(0, NS)
sys.path.insert(0, os.path.join(NS, "validation"))

from neurostate.io_edf import standardize_channels  # noqa: E402
from neurostate.pipeline import (AnalysisSpec, Stage, run_backfit, run_fit, run_match,  # noqa: E402
                                 run_preprocess)
from neurostate.provenance import environment_record, utc_now  # noqa: E402
from neurostate.templates import from_json  # noqa: E402
from run_real_data import PRIMARY  # noqa: E402  (frozen primary configuration)

mne.set_log_level("ERROR")


def load_stage(raw, path):
    raw, chrep = standardize_channels(raw)
    return Stage("load", "built-by-ns_crosscheck", {"path": path}, utc_now(),
                 {"raw": raw, "report": None, "channels": chrep})


def run(raw, path, tmpl):
    spec = AnalysisSpec(path, **PRIMARY)
    t0 = time.time()
    ld = load_stage(raw, path)
    pre = run_preprocess(spec, ld)
    fit = run_fit(spec, pre)
    match = run_match(spec, fit, tmpl)
    bf = run_backfit(spec, pre, fit, match, tmpl)
    rep, res, met = fit.payload["report"], match.payload["result"], bf.payload["metrics"]
    modk = fit.payload["modk"]
    return {
        "input": os.path.relpath(path, os.path.dirname(NS)), "sfreq": pre.payload["raw"].info["sfreq"],
        "seconds": round(time.time() - t0, 1),
        "n_gfp_peaks": rep.n_peaks_total, "gev_peaks": rep.fit_gev_peaks,
        "maps": np.asarray(modk.cluster_centers_).tolist(), "ch_names": list(modk.info["ch_names"]),
        "match": res.table(), "match_notes": res.notes,
        "per_state": met["per_state"], "unlabeled_fraction": met["unlabeled_fraction_all_samples"],
        "total_gev_backfit": met["total_gev_backfit"],
        "executed": {"preprocess": pre.executed, "fit": fit.executed, "backfit": bf.executed},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subs", nargs="+", default=["sub-001", "sub-037"])
    ap.add_argument("--bids", default="../ds004504")
    ap.add_argument("--prep", default="../prepared")
    ap.add_argument("--out", default="../results/microstates/ns_crosscheck.json")
    args = ap.parse_args()
    tmpl = from_json(os.path.join(NS, "templates", "Koenig2002_4class.json"))
    out = {"config_PRIMARY": {k: str(v) for k, v in PRIMARY.items()}, "environment": environment_record(),
           "template_sha256": tmpl.source_sha256, "subjects": {}}
    for sub in args.subs:
        set_path = os.path.abspath(f"{args.bids}/derivatives/{sub}/eeg/{sub}_task-eyesclosed_eeg.set")
        raw500 = mne.io.read_raw_eeglab(set_path, preload=True)
        z = np.load(os.path.abspath(f"{args.prep}/{sub}.npz"))
        info = mne.create_info([str(c) for c in z["ch_names"]], float(z["sfreq"]), "eeg")
        raw128 = mne.io.RawArray(z["ms"].astype(np.float64) * 1e-6, info)
        out["subjects"][sub] = {
            "ns_500": run(raw500, set_path, tmpl),
            "ns_128": run(raw128, os.path.abspath(f"{args.prep}/{sub}.npz"), tmpl)}
        for k, v in out["subjects"][sub].items():
            print(sub, k, f"{v['seconds']} s, {v['n_gfp_peaks']} peaks, GEV {v['gev_peaks']:.3f}", flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, default=str)


if __name__ == "__main__":
    main()
