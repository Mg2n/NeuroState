"""The adapter must give exactly what the repository's own functions give, called as edf_pipeline_check.py does."""
import json
import re
import sys

import mne
import numpy as np
import pandas as pd
import pytest

from conftest import SAMPLE, needs_inputs

pytestmark = needs_inputs


def _normalised_raw():
    """S001R02 with EEGMMIDB names normalised ('Fp1.' -> 'Fp1', 'FZ' -> 'Fz'); nothing else changed."""
    raw = mne.io.read_raw_edf(str(SAMPLE), preload=True, verbose="ERROR")
    canon = {c.upper(): c for c in ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T7", "C3", "Cz", "C4", "T8", "P7",
                                    "P3", "Pz", "P4", "P8", "O1", "O2"]}
    ren = {c: canon[c.replace(".", "").upper()] for c in raw.ch_names if c.replace(".", "").upper() in canon}
    raw.rename_channels(ren)
    return raw


def test_inline_reference(pa, sample_run):
    """Every step re-done here with prep / microstates / validate_microstates / run_experiment, in the reference order."""
    import microstates as msx
    import prep
    import run_experiment as rx
    import validate_microstates as vm
    from neurostate.templates import from_json

    raw = _normalised_raw()
    raw.rename_channels({c: a for c, a in {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}.items() if c in raw.ch_names})
    assert not [c for c in prep.CHANNELS if c not in raw.ch_names]
    tmin, tmax = 0.0, raw.times[-1] + 1 / raw.info["sfreq"]  # no 'eyes closed' marker: full recording
    seg = raw.copy().pick(prep.CHANNELS).crop(tmin, tmax, include_tmax=False)
    seg.set_eeg_reference("average", projection=False, verbose="ERROR")
    dl, ms = prep.band_copy(seg, 1.0, 40.0), prep.band_copy(seg, 2.0, 20.0)
    peaks = msx.gfp_peaks(ms, rng=np.random.default_rng(42))
    maps_raw, gev_peaks = msx.fit_maps([peaks], prep.CHANNELS, prep.SFREQ, seed=42)
    tmpl = from_json(str(pa.TEMPLATE_PATH))
    res = vm.match_to_reference(maps_raw, prep.CHANNELS, [str(k) for k in range(4)], tmpl.maps, tmpl.ch_names, tmpl.labels)
    order = [next(k for k in range(4) if res.assignment[k] == j) for j in range(4)]
    maps = vm.align_sign(maps_raw[order], vm.koenig_on(prep.CHANNELS, tmpl))
    absr = [float(res.assigned_abs_r[order[j]]) for j in range(4)]
    corr = msx.corr_sequence(ms, maps)
    labels = corr.argmax(0)
    f = msx.features(labels, prep.SFREQ)
    rx.FS, rx.WIN = prep.SFREQ, 512
    W = rx.windows(np.eye(4, dtype=np.float32)[labels].T.copy())

    a, st = sample_run.arrays, sample_run.steps
    assert st["read"]["recognised"] == 19 and st["read"]["missing"] == []
    assert (st["segment"]["tmin"], st["segment"]["tmax"]) == (tmin, tmax) and st["segment"]["method"] == "full"
    np.testing.assert_array_equal(a["ms"], ms)
    np.testing.assert_array_equal(a["dl"], dl)
    assert st["peaks"]["n_used"] == peaks.shape[1]
    np.testing.assert_array_equal(a["peaks"], peaks)
    np.testing.assert_allclose(np.abs(a["maps_raw"]), np.abs(maps_raw), rtol=0, atol=1e-12)  # up to sign
    np.testing.assert_array_equal(a["maps"], maps)
    assert st["fit"]["gev_peaks"] == gev_peaks
    assert st["name"]["cluster_for_ABCD"] == order
    assert sample_run.summary["absr"] == absr
    np.testing.assert_array_equal(a["corr"], corr)
    np.testing.assert_array_equal(a["labels"], labels)
    np.testing.assert_array_equal(a["features"], f)
    np.testing.assert_array_equal(a["W"], W)
    assert st["cnn"]["n_windows"] == len(W) == 15


def test_against_edf_pipeline_check_main(pa, sample_run, tmp_path, monkeypatch):
    """Run the unmodified edf_pipeline_check.main() on S001R02 (names normalised on read, full recording given as
    --tmin/--tmax because the file has no 'eyes closed' marker) and compare with the adapter."""
    import edf_pipeline_check as epc
    orig = mne.io.read_raw_edf

    def read_normalised(path, **kw):
        raw = orig(path, **kw)
        canon = {c.upper(): c for c in ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T7", "C3", "Cz", "C4", "T8",
                                        "P7", "P3", "Pz", "P4", "P8", "O1", "O2"]}
        raw.rename_channels({c: canon[c.replace(".", "").upper()] for c in raw.ch_names
                             if c.replace(".", "").upper() in canon})
        return raw

    monkeypatch.setattr(mne.io, "read_raw_edf", read_normalised)
    out = tmp_path / "epc"
    monkeypatch.setattr(sys, "argv", ["edf_pipeline_check.py", "--edf", str(SAMPLE), "--out", str(out),
                                      "--tmin", "0", "--tmax", "61.0"])
    epc.main()
    ref = json.loads((out / "results.json").read_text())
    st, a = sample_run.steps, sample_run.arrays
    assert ref["edf_sha256"] == sample_run.file_sha256
    assert ref["segment"]["tmin_s"] == st["segment"]["tmin"] and ref["segment"]["tmax_s"] == st["segment"]["tmax"]
    assert ref["prep"]["n_samples"] == st["label"]["n_samples"]
    m = ref["microstates"]
    assert m["n_gfp_peaks"] == st["peaks"]["n_used"]
    assert m["cluster_for_ABCD"] == st["name"]["cluster_for_ABCD"]
    assert m["abs_r_with_koenig"] == st["name"]["abs_r"]
    assert m["greedy_disagrees"] == st["name"]["greedy_disagrees"]
    assert m["gev_gfp_peaks"] == pytest.approx(st["fit"]["gev_peaks"], abs=1e-12)
    assert m["gev_all_samples"] == pytest.approx(st["label"]["gev_all_samples"], abs=1e-12)
    np.testing.assert_allclose(m["transitions_joint_pipeline"], a["joint"], atol=1e-15)
    for row, mine in zip(m["table"], st["measures"]["table"]):
        assert row["state"] == mine["state"]
        for k in ("coverage_pct", "mean_duration_ms", "occurrence_per_s", "abs_r_with_koenig2002"):
            assert row[k] == pytest.approx(mine[k], abs=1e-12)
    W = np.load(out / "cnn_input_onehot_4x512.npy")
    np.testing.assert_array_equal(W, a["W"])
    assert ref["cnn"]["n_complete_windows"] == st["cnn"]["n_windows"]
    assert ref["cnn"]["leftover_samples"] == st["cnn"]["leftover_samples"]
    npz = np.load(next((out / "prepared").glob("*.npz")))
    np.testing.assert_array_equal(npz["ms"], a["ms"])
    np.testing.assert_array_equal(npz["dl"], a["dl"])


def test_channel_normalisation(pa):
    assert pa.normalise_name("Fp1.") == "Fp1"
    assert pa.normalise_name("Fz..") == "Fz"
    assert pa.normalise_name("EEG FP1-REF") == "Fp1"
    assert pa.normalise_name("T7..") == "T7"
    plan = pa.channel_plan(["Fp1.", "T7..", "T3", "Iz.."])
    assert plan["found"]["T3"] == "T7.." and "T3" in plan["not_used"]


def test_smoothing_option(pa, sample_run):
    """--min-segment > 0 uses microstates.reject_short_segments on the argmax labels."""
    import microstates as msx
    run = pa.run_pipeline(str(SAMPLE), min_segment=3)
    np.testing.assert_array_equal(run.arrays["labels_argmax"], sample_run.arrays["labels"])
    np.testing.assert_array_equal(run.arrays["labels"], msx.reject_short_segments(sample_run.arrays["labels"], sample_run.arrays["ms"], 3))
    d = pa.instant(run, int(np.flatnonzero(run.arrays["labels"] != run.arrays["labels_argmax"])[0]))
    assert d["label"] != d["label_argmax"] and "changed this sample" in d["smoothing"]
    assert pa.instant(sample_run, 10)["smoothing"] == "No smoothing applied"
