"""The one place where the app touches the research pipeline.

Every scientific step calls the repository's own functions, unchanged, in the order and with the settings
of experiments/edf_pipeline_check.py (the reference implementation):

  prep.CHANNELS / prep.SFREQ / prep.band_copy          channel set, 128 Hz, 1-40 Hz and 2-20 Hz copies (µV)
  edf_pipeline_check.resting_segment                   segment from the first marker matching the regex
  microstates.gfp_peaks / fit_maps                     GFP peaks (cap 1500, rng seed), modified k-means (n_init 20)
  validate_microstates.match_to_reference / koenig_on / align_sign   A-D names by one-to-one matching to Koenig 2002
  microstates.corr_sequence / reject_short_segments    |r| of every sample with every map; optional smoothing
  edf_pipeline_check.gev_all_samples                   GEV over every sample
  microstates.features                                 the 24 numbers
  run_experiment.windows (WIN = 512)                   complete 4 x 512 one-hot windows

What is new here (app layer only; no research file is edited):
  * reading the header without loading data, and refusing incompatible files with a reason;
  * channel-name normalisation (trailing dots, case, 'EEG ' prefix, '-REF' suffix), before the T7/T8/P7/P8 ->
    T3/T4/T5/T6 renaming that edf_pipeline_check.py already does;
  * full-recording fallback when no marker matches (edf_pipeline_check.py stops instead), manual bounds;
  * EDF+D: gaps found with NeuroState-Microstates' own header/TAL readers (neurostate.io_edf, unmodified);
    the analysis is restricted to one continuous stretch and never filters across a gap;
  * per-step events, the instant inspector, export.

Maps are fitted on the single recording, as in edf_pipeline_check.py. In a study they must come from the
training patients of each fold, as run_experiment.py does.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
EXP = REPO / "experiments"
NS_DIR = REPO / "NeuroState-Microstates"
APP = Path(__file__).resolve().parent
TOKENS = json.loads((APP / "static" / "tokens.json").read_text())

if str(EXP) not in sys.path:
    sys.path.insert(0, str(EXP))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mne  # noqa: E402
import numpy as np  # noqa: E402
from scipy.signal import find_peaks  # noqa: E402

import edf_pipeline_check as epc  # noqa: E402  (reference implementation; imported, never run here)
import microstates as msx  # noqa: E402
import prep  # noqa: E402
import run_experiment as rx  # noqa: E402
import validate_microstates as vm  # noqa: E402  (adds NeuroState-Microstates to sys.path)
from neurostate import io_edf as ns_edf  # noqa: E402  (NeuroState-Microstates, unmodified)
from neurostate.templates import from_json  # noqa: E402

STATES = "ABCD"
SEED = 42            # edf_pipeline_check.py --seed default
N_INIT = 20          # microstates.fit_maps default, as in edf_pipeline_check.py
MAX_PEAKS = 1500     # microstates.gfp_peaks default
MS_BAND = (2.0, 20.0)
DL_BAND = (1.0, 40.0)
WIN_SEC = 4.0
MARKER = r"eyes\s*closed"  # edf_pipeline_check.py --marker default
ALIAS = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}  # as edf_pipeline_check.py / prep.py
MIN_SFREQ = 2 * DL_BAND[1]   # the 1-40 Hz copy needs a Nyquist frequency above 40 Hz (2-20 Hz needs > 40 Hz)
TEMPLATE_PATH = Path(vm.NS) / "templates" / "Koenig2002_4class.json"
DEFAULT_VIEW = ["Fp1", "F3", "Fz", "C3", "Cz", "P3", "Pz", "O1"]
STATE_COLORS = [TOKENS["states"][s] for s in STATES]

STEPS = [
    ("read", "File read"),
    ("segment", "Segment selected"),
    ("prepare", "Prepared"),
    ("peaks", "GFP peaks detected"),
    ("fit", "Four maps fitted"),
    ("name", "Maps named A–D"),
    ("label", "Samples labelled"),
    ("measures", "Measures computed"),
    ("cnn", "CNN input prepared"),
]


class Incompatible(Exception):
    def __init__(self, problems: list[dict]):
        super().__init__("; ".join(p["message"] for p in problems))
        self.problems = problems


def sha256(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------- channels
_CANON = {c.upper(): c for c in list(prep.CHANNELS) + list(ALIAS)}


def normalise_name(name: str) -> str:
    """'Fp1.' -> 'Fp1', 'FZ..' -> 'Fz', 'EEG FP1-REF' -> 'Fp1', 'T7' stays 'T7' (aliases are applied later)."""
    s = name.strip()
    s = re.sub(r"^EEG[\s_-]+", "", s, flags=re.I)
    s = re.sub(r"[-_](REF|LE|AVG|AR|M1|M2|A1|A2)$", "", s, flags=re.I)
    s = s.replace(".", "").strip()
    return _CANON.get(s.upper(), s)


def channel_plan(ch_names: list[str], ch_types: list[str] | None = None) -> dict:
    """Which original channel becomes each of the 19 prep.CHANNELS; the rest are 'not used'."""
    chosen: dict[str, str] = {}
    rows = []
    for i, orig in enumerate(ch_names):
        norm = normalise_name(orig)
        target = ALIAS.get(norm, norm)
        row = {"original": orig, "normalised": norm, "target": None, "status": "not used", "type":
               (ch_types[i] if ch_types else None)}
        if target in prep.CHANNELS and target not in chosen:
            chosen[target] = orig
            row.update(target=target, status="found")
        elif target in prep.CHANNELS:
            row["note"] = f"duplicate of {target} (using '{chosen[target]}')"
        rows.append(row)
    missing = [c for c in prep.CHANNELS if c not in chosen]
    rename = {orig: tgt for tgt, orig in chosen.items() if orig != tgt}
    renamed_from_alias = {tgt: normalise_name(orig) for tgt, orig in chosen.items()
                          if normalise_name(orig) in ALIAS}
    return {"rows": rows, "found": {c: chosen.get(c) for c in prep.CHANNELS}, "missing": missing,
            "rename": rename, "aliases_applied": renamed_from_alias,
            "not_used": [r["original"] for r in rows if r["status"] != "found"]}


def apply_channel_plan(raw: mne.io.BaseRaw, plan: dict) -> None:
    """Rename the chosen originals to the 19 standard names. Unchosen channels that would collide are renamed
    out of the way first (they are never analysed)."""
    clash = {c: f"{c}__unused" for c in raw.ch_names if c in prep.CHANNELS and plan["found"].get(c) != c}
    if clash:
        raw.rename_channels(clash)
    if plan["rename"]:
        raw.rename_channels(plan["rename"])


# --------------------------------------------------------------------------------------------- header check
def _markers(raw) -> list[tuple[float, float, str]]:
    return sorted(((float(a["onset"]), float(a["duration"]), str(a["description"])) for a in raw.annotations),
                  key=lambda t: t[0])


def _gaps(path: str, hdr: dict) -> tuple[list[dict], float | None]:
    if hdr["edf_plus_type"] not in ("EDF+C", "EDF+D"):
        return [], None
    onsets = ns_edf.read_record_onsets(path)
    if onsets is None:
        return [], None
    gaps = [g for g in ns_edf.find_record_gaps(onsets, hdr["record_duration_s"]) if "gap_start_s" in g]
    return gaps, float(onsets[0])


def _retime(raw, gaps, first):
    """NeuroState-Microstates' bookkeeping (io_edf.load_edf): MNE concatenates EDF+D records back to back but
    places annotations at their true time; move them onto the sample axis, drop those inside a gap."""
    new_on, new_du, new_de, inside = [], [], [], []
    for a in raw.annotations:
        t = ns_edf.map_true_to_sample_time(float(a["onset"]), gaps, first)
        if t is None:
            inside.append({"onset_true_s": float(a["onset"]), "description": a["description"]})
        else:
            new_on.append(t), new_du.append(float(a["duration"])), new_de.append(a["description"])
    raw.set_annotations(mne.Annotations(new_on, new_du, new_de, orig_time=raw.annotations.orig_time))
    return inside


def read_header(path: str) -> tuple[mne.io.BaseRaw, dict]:
    """Header only (preload=False). Raises Incompatible for unreadable or inconsistent headers."""
    try:
        hdr = ns_edf.read_edf_header_fields(path)
    except Exception as e:  # EDFHeaderError and anything else from a damaged file
        raise Incompatible([{"code": "header", "message": "The EDF header is damaged or unreadable, so the file "
                             "was refused rather than misread.", "found": str(e)[:400],
                             "needed": "a standard EDF/EDF+ header"}])
    probs = ns_edf.header_consistency_problems(hdr)
    if probs:
        raise Incompatible([{"code": "header", "message": "The EDF header is inconsistent with the file, so the "
                             "file was refused rather than misread.", "found": "; ".join(probs)[:400],
                             "needed": "header fields that match the data (NeuroState-Microstates check)"}])
    try:
        raw = mne.io.read_raw_edf(path, preload=False, verbose="ERROR")
    except Exception as e:
        raise Incompatible([{"code": "header", "message": "MNE could not read this EDF file, so it was refused.",
                             "found": f"{type(e).__name__}: {str(e)[:300]}", "needed": "a readable EDF/EDF+ file"}])
    return raw, hdr


def stretches(n_times: int, sfreq: float, gaps: list[dict], record_duration: float) -> list[tuple[float, float]]:
    """Continuous stretches on MNE's concatenated time axis, split at every EDF+D junction."""
    end = n_times / sfreq
    cuts = sorted({(g["after_record"] + 1) * record_duration for g in gaps})
    edges = [0.0] + [c for c in cuts if 0 < c < end] + [end]
    return [(a, b) for a, b in zip(edges[:-1], edges[1:]) if b > a]


def plan_segment(raw, gaps_stretches, marker: str, tmin: float | None, tmax: float | None) -> dict:
    sf = raw.info["sfreq"]
    end = raw.times[-1] + 1 / sf
    note = None
    if tmin is not None or tmax is not None:
        a = 0.0 if tmin is None else float(tmin)
        b = end if tmax is None else float(tmax)
        if not (0 <= a < b <= end + 1e-9):
            raise Incompatible([{"code": "segment", "message": "The manual start and end are outside the recording.",
                                 "found": f"{a:g}–{b:g} s", "needed": f"0 ≤ start < end ≤ {end:.3f} s"}])
        method = "manual"
        how = "manual start and end"
    else:
        try:
            a, b, _ = epc.resting_segment(raw, marker)
            method = "marker"
            hit = next(d for o, _, d in _markers(raw) if abs(o - a) < 1e-9 and re.search(marker, d, re.I))
            how = f"first marker matching /{marker}/ ('{hit}') to the next marker or the end"
        except SystemExit:  # edf_pipeline_check.resting_segment stops when no marker matches
            a, b, method = 0.0, end, "full"
            how = f"full recording: no event marker matches /{marker}/"
    if len(gaps_stretches) > 1:
        best = max(gaps_stretches, key=lambda s: min(b, s[1]) - max(a, s[0]))
        a2, b2 = max(a, best[0]), min(b, best[1])
        if (a2, b2) != (a, b):
            note = (f"The file has recording gaps (EDF+D). The selected span {a:.3f}–{b:.3f} s crosses a gap, so only "
                    f"its longest continuous stretch, {a2:.3f}–{b2:.3f} s, is analysed. Filtering never crosses a gap.")
            a, b = a2, b2
        else:
            note = "The file has recording gaps (EDF+D); the analysed segment lies inside one continuous stretch."
    return {"tmin": float(a), "tmax": float(b), "duration": float(b - a), "method": method, "how": how,
            "note": note}


def check_file(path: str, marker: str = MARKER, tmin: float | None = None, tmax: float | None = None) -> dict:
    """File check shown before 'Run analysis'. Never raises: returns ok=False with the problems."""
    out: dict[str, Any] = {"ok": False, "problems": [], "file": os.path.basename(path)}
    try:
        raw, hdr = read_header(path)
    except Incompatible as e:
        out["problems"] = e.problems
        return out
    sf = float(raw.info["sfreq"])
    gaps, first = _gaps(path, hdr)
    inside = _retime(raw, gaps, first) if gaps else []
    st = stretches(raw.n_times, sf, gaps, hdr["record_duration_s"])
    plan = channel_plan(raw.ch_names, raw.get_channel_types())
    eeg_rates = sorted({round(int(s["samples_per_record"]) / hdr["record_duration_s"], 6) for s in hdr["signals"]
                        if s["label"] != "EDF Annotations"})
    out.update({
        "edf_type": hdr["edf_plus_type"], "duration_s": raw.n_times / sf, "sfreq": sf, "signal_rates": eeg_rates,
        "n_channels": len(raw.ch_names), "channels": plan["rows"], "found": plan["found"], "missing": plan["missing"],
        "not_used": plan["not_used"], "aliases_applied": plan["aliases_applied"],
        "markers": [{"onset": o, "duration": d, "description": s} for o, d, s in _markers(raw)],
        "markers_inside_gaps": inside, "gaps": gaps, "stretches": st, "marker_regex": marker,
    })
    probs = []
    if plan["missing"]:
        probs.append({"code": "channels", "message": f"{len(plan['missing'])} of the 19 standard 10–20 channels "
                      f"{'is' if len(plan['missing']) == 1 else 'are'} missing: {', '.join(plan['missing'])}.",
                      "found": f"{19 - len(plan['missing'])}/19 recognised", "needed": ", ".join(prep.CHANNELS)})
    if sf <= MIN_SFREQ:
        probs.append({"code": "sfreq", "message": f"The sampling rate ({sf:g} Hz) is too low. The 2–20 Hz microstate "
                      f"band needs more than 40 Hz and the pipeline's 1–40 Hz copy needs more than {MIN_SFREQ:g} Hz.",
                      "found": f"{sf:g} Hz", "needed": f"> {MIN_SFREQ:g} Hz"})
    try:
        seg = plan_segment(raw, st, marker, tmin, tmax)
        out["segment"] = seg
        n128 = int(round(round(seg["duration"] * sf) * prep.SFREQ / sf))
        out["segment"]["expected_samples_128"] = n128
        if n128 < rx.WIN:
            probs.append({"code": "short", "message": f"The analysable segment is {seg['duration']:.2f} s long, "
                          f"shorter than one 4-s window ({rx.WIN} samples at {prep.SFREQ:g} Hz).",
                          "found": f"{seg['duration']:.2f} s ({n128} samples at 128 Hz)",
                          "needed": f"≥ {WIN_SEC:g} s ({rx.WIN} samples at 128 Hz)"})
    except Incompatible as e:
        probs += e.problems
    out["problems"] = probs
    out["ok"] = not probs
    return out


# --------------------------------------------------------------------------------------------- run
@dataclass
class Run:
    run_id: str
    path: str
    source: str
    file_name: str
    file_sha256: str
    settings: dict
    steps: dict = field(default_factory=dict)
    arrays: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    started: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)


def run_pipeline(path: str, *, source: str = "upload", marker: str = MARKER, tmin: float | None = None,
                 tmax: float | None = None, min_segment: int = 0, seed: int = SEED,
                 emit: Callable[[str, dict], None] | None = None, file_name: str | None = None) -> Run:
    """Run every step; call emit(step_id, result) when each step has really finished."""
    emit = emit or (lambda *_: None)
    chk = check_file(path, marker, tmin, tmax)
    if not chk["ok"]:
        raise Incompatible(chk["problems"])
    settings = {"seed": seed, "n_init": N_INIT, "max_gfp_peaks": MAX_PEAKS, "ms_band_hz": list(MS_BAND),
                "dl_band_hz": list(DL_BAND), "sfreq": prep.SFREQ, "reference": "average", "marker_regex": marker,
                "manual_tmin": tmin, "manual_tmax": tmax, "min_segment": int(min_segment),
                "window_samples": rx.WIN, "window_s": WIN_SEC, "n_states": msx.N_STATES,
                "template": "Koenig 2002 (MICROSTATELAB Koenig2002.set, 4 classes)",
                "matching": "one-to-one (Hungarian), polarity ignored: validate_microstates.match_to_reference"}
    run = Run(run_id=uuid.uuid4().hex[:12], path=path, source=source, file_name=file_name or os.path.basename(path),
              file_sha256=sha256(path), settings=settings)

    def done(step, res):
        run.steps[step] = res
        emit(step, res)

    # 1. read, exactly as edf_pipeline_check.py (preload=True), then the app-layer channel names
    raw = mne.io.read_raw_edf(path, preload=True, verbose="ERROR")
    sf0, dur0 = float(raw.info["sfreq"]), raw.n_times / raw.info["sfreq"]
    gaps, first = _gaps(path, ns_edf.read_edf_header_fields(path))
    if gaps:
        _retime(raw, gaps, first)
    plan = channel_plan(raw.ch_names, raw.get_channel_types())
    apply_channel_plan(raw, plan)
    n_eeg = sum(t == "eeg" for t in raw.get_channel_types())
    done("read", {"file": run.file_name, "sha256": run.file_sha256, "sfreq": sf0, "duration_s": dur0,
                  "n_channels": len(raw.ch_names), "n_eeg_channels": n_eeg, "edf_type": chk["edf_type"],
                  "recognised": 19 - len(plan["missing"]), "missing": plan["missing"], "not_used": plan["not_used"],
                  "aliases_applied": plan["aliases_applied"], "renamed": len(plan["rename"]),
                  "gaps": len(gaps)})

    # 2. segment (planned by check_file with the same rules)
    seg = chk["segment"]
    t_a, t_b = seg["tmin"], seg["tmax"]
    s = raw.copy().pick(prep.CHANNELS).crop(t_a, t_b, include_tmax=False)
    raw_uv = (s.get_data() * 1e6).astype(np.float32)  # as recorded, original reference
    done("segment", {"tmin": t_a, "tmax": t_b, "duration_s": t_b - t_a, "method": seg["method"], "how": seg["how"],
                     "note": seg["note"], "n_samples_original": int(s.n_times), "markers": chk["markers"]})

    # 3. preparation, exactly as edf_pipeline_check.py / prep.py
    s.set_eeg_reference("average", projection=False, verbose="ERROR")
    dl, ms = prep.band_copy(s, *DL_BAND), prep.band_copy(s, *MS_BAND)
    done("prepare", {"reference": "average", "ms_band_hz": list(MS_BAND), "dl_band_hz": list(DL_BAND),
                     "sfreq": prep.SFREQ, "shape": list(ms.shape), "dl_shape": list(dl.shape),
                     "duration_s": ms.shape[1] / prep.SFREQ, "filter": "FIR, zero phase (mne filter), then resample"})

    # 4. GFP peaks
    rng = np.random.default_rng(seed)
    peaks = msx.gfp_peaks(ms, rng=rng)
    gfp = ms.std(axis=0)
    peak_idx = find_peaks(gfp)[0]  # the maxima gfp_peaks starts from; the same draw reproduces its subset
    n_local_max = int(len(peak_idx))
    if n_local_max > MAX_PEAKS:
        peak_idx = np.sort(np.random.default_rng(seed).choice(peak_idx, MAX_PEAKS, replace=False))
    assert np.array_equal(ms[:, peak_idx], peaks), "peak indices do not reproduce microstates.gfp_peaks"
    done("peaks", {"n_local_maxima": n_local_max, "n_used": int(peaks.shape[1]), "cap": MAX_PEAKS,
                   "sampled": n_local_max > MAX_PEAKS,
                   "how": (f"{MAX_PEAKS} of {n_local_max} GFP maxima drawn at random without replacement "
                           f"(numpy default_rng({seed})), kept in time order" if n_local_max > MAX_PEAKS
                           else f"all {n_local_max} GFP maxima (fewer than the cap of {MAX_PEAKS})")})

    # 5. fit
    maps_raw, gev_peaks = msx.fit_maps([peaks], prep.CHANNELS, prep.SFREQ, seed=seed)
    done("fit", {"method": "modified k-means (Pycrostates ModKMeans), polarity-invariant", "n_clusters": 4,
                 "n_init": N_INIT, "seed": seed, "max_iter": 300, "tol": 1e-6, "gev_peaks": gev_peaks,
                 "n_peaks": int(peaks.shape[1])})

    # 6. names, exactly as edf_pipeline_check.py
    tmpl = from_json(str(TEMPLATE_PATH))
    res = vm.match_to_reference(maps_raw, prep.CHANNELS, [str(k) for k in range(4)], tmpl.maps, tmpl.ch_names,
                                tmpl.labels)
    to_ref = {k: res.assignment[k] for k in range(4)}
    order = [next(k for k in range(4) if to_ref[k] == j) for j in range(4)]
    names = [tmpl.labels[j] for j in range(4)]
    assert names == list(STATES), names
    kref = vm.koenig_on(prep.CHANNELS, tmpl)
    maps = vm.align_sign(maps_raw[order], kref)
    absr = [float(res.assigned_abs_r[order[j]]) for j in range(4)]
    greedy = [int(x) for x in res.greedy_disagrees]
    done("name", {"template": "Koenig 2002", "cluster_for_ABCD": order, "abs_r": dict(zip(STATES, absr)),
                  "greedy_disagrees": greedy, "template_sha256": tmpl.source_sha256,
                  "note": (f"Greedy matching would assign clusters {greedy} differently." if greedy
                           else "Greedy matching gives the same assignment.")})

    # 7. labels
    corr = msx.corr_sequence(ms, maps)
    labels_argmax = corr.argmax(0)
    labels = (msx.reject_short_segments(labels_argmax, ms, int(min_segment)) if min_segment else labels_argmax)
    gev_all = epc.gev_all_samples(ms, maps, labels)
    n_changed = int(np.sum(labels != labels_argmax))
    done("label", {"n_samples": int(len(labels)), "gev_all_samples": gev_all,
                   "smoothing": (f"minimum segment {int(min_segment)} samples (microstates.reject_short_segments); "
                                 f"{n_changed} samples changed" if min_segment else "none (--min-segment 0)"),
                   "min_segment": int(min_segment), "n_changed_by_smoothing": n_changed})

    # 8. measures, exactly as edf_pipeline_check.py
    f = msx.features(labels, prep.SFREQ)
    change = np.flatnonzero(np.diff(labels)) + 1
    run_state = labels[np.r_[0, change]]
    T = np.zeros((4, 4))
    for a, b in zip(run_state[:-1], run_state[1:]):
        T[a, b] += 1
    joint = T / max(T.sum(), 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cond = T / T.sum(1, keepdims=True)
    assert np.allclose([joint[i, j] for i in range(4) for j in range(4) if i != j], f[12:])
    table = [{"state": STATES[k], "coverage_pct": float(100 * f[k]), "mean_duration_ms": float(f[4 + k]),
              "occurrence_per_s": float(f[8 + k]), "abs_r_with_koenig2002": absr[k],
              "n_visits": int(np.sum(run_state == k)), "n_samples": int(np.sum(labels == k))} for k in range(4)]
    done("measures", {"table": table, "n_visits": int(len(run_state)), "n_transitions": int(T.sum()),
                      "features": [float(v) for v in f], "feature_names": msx.FEATURE_NAMES})

    # 9. CNN input, as edf_pipeline_check.py (rx.FS / rx.WIN from the 128 Hz prepared data)
    onehot = np.eye(4, dtype=np.float32)[labels].T.copy()
    rx.FS = prep.SFREQ
    rx.WIN = int(round(WIN_SEC * rx.FS))
    W = rx.windows(onehot)
    left = onehot.shape[1] - len(W) * rx.WIN
    assert W.shape[1:] == (4, 512) and np.allclose(W.sum(1), 1)
    done("cnn", {"n_windows": int(len(W)), "window_shape": list(W.shape[1:]), "leftover_samples": int(left),
                 "leftover_s": left / rx.FS, "input": "one-hot A–D (run_experiment.py --ms-input onehot)",
                 "win": rx.WIN})

    run.arrays = {"raw_uv": raw_uv, "ms": ms, "dl": dl, "peaks": peaks, "peak_idx": peak_idx, "gfp": gfp, "maps_raw": maps_raw, "maps": maps,
                  "kref": kref, "corr": corr, "labels": labels, "labels_argmax": labels_argmax, "onehot": onehot,
                  "W": W, "T": T, "joint": joint, "cond": cond, "features": f}
    run.summary = {"sf0": sf0, "t0": t_a, "t1": t_b, "fs": prep.SFREQ, "n": int(ms.shape[1]),
                   "n_raw": int(raw_uv.shape[1]), "absr": absr, "order": order, "gev_peaks": gev_peaks,
                   "gev_all": gev_all, "greedy": greedy, "channel_plan": plan, "check": chk,
                   "environment": rx.env_info(), "template_provenance": tmpl.provenance,
                   "template_sha256": tmpl.source_sha256}
    return run


# --------------------------------------------------------------------------------------------- views of a run
def _f(x):
    """JSON-safe float (NaN -> None)."""
    x = float(x)
    return None if not np.isfinite(x) else x


def results_payload(run: Run) -> dict:
    a, s = run.arrays, run.summary
    return {
        "run_id": run.run_id, "source": run.source, "file": run.file_name, "file_sha256": run.file_sha256,
        "settings": run.settings, "steps": run.steps, "channels": list(prep.CHANNELS), "default_view": DEFAULT_VIEW,
        "t0": s["t0"], "t1": s["t1"], "fs": s["fs"], "sf0": s["sf0"], "n": s["n"], "n_raw": s["n_raw"],
        "labels": a["labels"].astype(int).tolist(),
        "labels_argmax": a["labels_argmax"].astype(int).tolist() if run.settings["min_segment"] else None,
        "abs_r_template": s["absr"], "gev_peaks": s["gev_peaks"], "gev_all": s["gev_all"],
        "greedy_disagrees": s["greedy"],
        "measures": run.steps["measures"]["table"],
        "features": [float(v) for v in a["features"]], "feature_names": msx.FEATURE_NAMES,
        "transitions": {"counts": a["T"].astype(int).tolist(), "joint": [[_f(v) for v in r] for r in a["joint"]],
                        "conditional": [[_f(v) for v in r] for r in a["cond"]]},
        "cnn": run.steps["cnn"],
        "maps": {"fitted": a["maps"].tolist(), "templates": a["kref"].tolist()},
        "gfp": np.round(a["gfp"].astype(float), 4).tolist(), "peak_idx": a["peak_idx"].astype(int).tolist(),
        "example_i": s.get("example_i"), "built_utc": s.get("built_utc"),
        "environment": s["environment"],
    }


def instant(run: Run, i: int) -> dict:
    a, s = run.arrays, run.summary
    i = int(min(max(i, 0), s["n"] - 1))
    r = [float(v) for v in a["corr"][:, i]]
    lab = int(a["labels"][i])
    lab_raw = int(a["labels_argmax"][i])
    t = s["t0"] + i / s["fs"]
    rank = sorted(range(4), key=lambda k: -r[k])
    others = ", ".join(f"{STATES[k]} {r[k]:.2f}" for k in rank[1:])
    w = rank[0]
    sentence = (f"At {t:.2f} s the scalp map matches fitted map {STATES[w]} most closely (|r| = {r[w]:.2f}, vs "
                f"{others}), so this moment is labelled {STATES[w]}.")
    smooth = None
    if run.settings["min_segment"]:
        smooth = (f"Smoothing (minimum segment {run.settings['min_segment']} samples) changed this sample from "
                  f"{STATES[lab_raw]} to {STATES[lab]}." if lab != lab_raw else
                  f"Smoothing (minimum segment {run.settings['min_segment']} samples) kept the label "
                  f"{STATES[lab]}.")
        if lab != lab_raw:
            sentence = (f"At {t:.2f} s the scalp map matches fitted map {STATES[w]} most closely (|r| = {r[w]:.2f}, "
                        f"vs {others}); the best match alone would give {STATES[w]}, and after smoothing the final "
                        f"label is {STATES[lab]}.")
    return {"i": i, "t": t, "values_uv": [float(v) for v in a["ms"][:, i]], "channels": list(prep.CHANNELS),
            "abs_r": r, "label": lab, "label_argmax": lab_raw, "winner": w, "sentence": sentence,
            "smoothing": smooth or "No smoothing applied"}


def signal(run: Run, view: str, t0: float, t1: float, channels: list[str], max_points: int = 8000) -> dict:
    s, a = run.summary, run.arrays
    if view == "raw":
        fs, arr, n = s["sf0"], a["raw_uv"], s["n_raw"]
    else:
        fs, arr, n = s["fs"], a["ms"], s["n"]
    i0 = max(int(np.floor((t0 - s["t0"]) * fs)) - 1, 0)
    i1 = min(int(np.ceil((t1 - s["t0"]) * fs)) + 2, n)
    step = max(1, int(np.ceil((i1 - i0) / max_points)))
    idx = np.arange(i0, i1, step)
    ci = [prep.CHANNELS.index(c) for c in channels]
    return {"view": view, "fs": fs, "step": step, "t": (s["t0"] + idx / fs).round(6).tolist(),
            "data": {c: arr[k, idx].round(3).tolist() for c, k in zip(channels, ci)}}


# --------------------------------------------------------------------------------------------- figures
def _light_outlines(ax, color):
    for ln in ax.lines:
        ln.set_color(color)
    for coll in ax.collections:
        if coll.__class__.__name__ == "PathCollection":  # sensor markers
            coll.set_facecolor(color), coll.set_edgecolor(color)


def topomap_png(values, *, normalise=True, size=2.2, dpi=110, dark=True, contours=0) -> bytes:
    """mne.viz.plot_topomap with the info and montage of the fit (validate_microstates.info_for)."""
    v = np.asarray(values, dtype=float)
    lim = np.abs(v).max() or 1.0
    if normalise:
        v, lim = v / lim, 1.0
    fig, ax = plt.subplots(figsize=(size, size))
    mne.viz.plot_topomap(v, _info(), axes=ax, show=False, cmap="RdBu_r", vlim=(-lim, lim), contours=contours,
                         sensors=True)
    if dark:
        _light_outlines(ax, TOKENS["text"]["muted"])
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return buf.getvalue()


@lru_cache(maxsize=1)
def _info():
    return vm.info_for(prep.CHANNELS)


def map_png(run: Run, kind: str, k: int) -> bytes:
    key = f"png_{kind}_{k}"
    with run.lock:
        if key not in run.arrays:
            m = run.arrays["maps" if kind == "fitted" else "kref"][k]
            run.arrays[key] = topomap_png(m, contours=0)
        return run.arrays[key]


def instant_png(run: Run, i: int) -> bytes:
    i = int(min(max(i, 0), run.summary["n"] - 1))
    cache = run.arrays.setdefault("_instant_png", {})
    with run.lock:
        if i not in cache:
            if len(cache) > 200:
                cache.clear()
            cache[i] = topomap_png(run.arrays["ms"][:, i], normalise=False, size=3.0, dpi=110)
        return cache[i]


def _fig_maps(run: Run) -> bytes:
    a, s = run.arrays, run.summary
    fig, axes = plt.subplots(2, 4, figsize=(8.0, 4.6))
    for j in range(4):
        for r, (m, title) in enumerate(((a["maps"][j], f"Fitted {STATES[j]}   |r| = {s['absr'][j]:.2f}"),
                                        (a["kref"][j], f"Koenig 2002 {STATES[j]}"))):
            ax = axes[r, j]
            mne.viz.plot_topomap(m / np.abs(m).max(), _info(), axes=ax, show=False, cmap="RdBu_r", vlim=(-1, 1),
                                 contours=0, sensors=True)
            ax.set_title(title, fontsize=9, color=STATE_COLORS[j])
    fig.suptitle(f"Fitted maps (this recording) vs published templates (Koenig 2002); GEV over all samples "
                 f"{s['gev_all']:.3f}", fontsize=9, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    return buf.getvalue()


def _fig_timeline(run: Run, seconds: float = 2.0) -> bytes:
    a, s = run.arrays, run.summary
    n = min(int(seconds * s["fs"]), s["n"])
    t = s["t0"] + np.arange(n) / s["fs"]
    gfp = a["ms"].std(0)[:n]
    fig, ax = plt.subplots(figsize=(8.0, 2.2))
    for i in range(n):
        ax.axvspan(t[i], t[i] + 1 / s["fs"], color=STATE_COLORS[a["labels"][i]], alpha=0.75, lw=0)
    ax.plot(t, gfp, color="#1f1f1e", lw=0.8)
    ax.set(xlabel="Time in the recording (s)", ylabel="GFP (µV)", xlim=(t[0], t[-1] + 1 / s["fs"]))
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in STATE_COLORS], labels=list(STATES), ncol=4,
              frameon=False, loc="lower right", bbox_to_anchor=(1, 1), fontsize=8)
    ax.set_title(f"First {seconds:g} s of the A–D sequence (2–20 Hz, 128 Hz), "
                 f"{'no smoothing' if not run.settings['min_segment'] else 'smoothed'}", fontsize=9, loc="left")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    return buf.getvalue()


def _csv(rows: list[list]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def app_git_commit() -> str | None:
    try:
        head = (REPO / ".git" / "HEAD").read_text().strip()
        if head.startswith("ref:"):
            ref = REPO / ".git" / head.split(" ", 1)[1]
            return ref.read_text().strip() if ref.exists() else None
        return head
    except OSError:
        return None


def export_zip(run: Run) -> bytes:
    a, s = run.arrays, run.summary
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    z.writestr("measures.csv", _csv([["state", "coverage_pct", "mean_duration_ms", "occurrence_per_s",
                                      "abs_r_with_koenig2002", "n_visits", "n_samples"]] +
                                    [[r["state"], r["coverage_pct"], r["mean_duration_ms"], r["occurrence_per_s"],
                                      r["abs_r_with_koenig2002"], r["n_visits"], r["n_samples"]]
                                     for r in run.steps["measures"]["table"]]))
    z.writestr("features_24.csv", _csv([["feature", "value"]] +
                                       [[n, float(v)] for n, v in zip(msx.FEATURE_NAMES, a["features"])]))
    for name, M in (("counts", a["T"]), ("joint", a["joint"]), ("conditional", a["cond"])):
        z.writestr(f"transitions_{name}.csv", _csv([["from \\ to"] + list(STATES)] +
                                                   [[STATES[i]] + [float(v) for v in M[i]] for i in range(4)]))
    rows = [["sample", "time_s", "label_argmax", "label_final"] + [f"abs_r_{c}" for c in STATES]]
    for i in range(s["n"]):
        rows.append([i, round(s["t0"] + i / s["fs"], 6), STATES[a["labels_argmax"][i]], STATES[a["labels"][i]]]
                    + [float(v) for v in a["corr"][:, i]])
    z.writestr("labels_per_sample.csv", _csv(rows))
    z.writestr("maps.csv", _csv([["map", "source"] + list(prep.CHANNELS)] +
                                [[STATES[j], "fitted (this recording, sign aligned to Koenig)"] +
                                 [float(v) for v in a["maps"][j]] for j in range(4)] +
                                [[STATES[j], "Koenig 2002 template on these 19 channels, average reference"] +
                                 [float(v) for v in a["kref"][j]] for j in range(4)]))
    npy = io.BytesIO()
    np.save(npy, a["maps"])
    z.writestr("maps_fitted.npy", npy.getvalue())
    npy = io.BytesIO()
    np.save(npy, a["W"])
    z.writestr("cnn_input_onehot_windows.npy", npy.getvalue())
    z.writestr("figures/fitted_maps_vs_templates.png", _fig_maps(run))
    z.writestr("figures/timeline_first_2s.png", _fig_timeline(run))
    for j in range(4):
        z.writestr(f"figures/map_{STATES[j]}_fitted.png", map_png(run, "fitted", j))
        z.writestr(f"figures/map_{STATES[j]}_koenig2002.png", map_png(run, "template", j))
    manifest = {
        "tool": "NeuroState hackathon interface (app/), research use only",
        "app_git_commit": app_git_commit(),
        "input": {"file": run.file_name, "source": run.source, "sha256": run.file_sha256,
                  "sfreq": s["sf0"], "edf_type": s["check"]["edf_type"]},
        "segment": {k: run.steps["segment"][k] for k in ("tmin", "tmax", "duration_s", "method", "how", "note")},
        "channels": {"used": list(prep.CHANNELS), "source_channel_for_each": s["channel_plan"]["found"],
                     "aliases_applied": s["channel_plan"]["aliases_applied"],
                     "not_used": s["channel_plan"]["not_used"]},
        "settings": run.settings,
        "steps": run.steps,
        "template": {"sha256": s["template_sha256"], "provenance": s["template_provenance"]},
        "environment": s["environment"],
        "maps_note": "Maps were fitted on this one recording; in a study they come from the training patients of "
                     "each fold (run_experiment.py).",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    z.writestr("manifest.json", json.dumps(manifest, indent=2, default=_f))
    z.close()
    return buf.getvalue()


def png_data_uri(b: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(b).decode()


# --------------------------------------------------------------------------------------------- demo bundle
BUNDLE_ARRAYS = ("raw_uv", "ms", "dl", "peaks", "peak_idx", "gfp", "maps_raw", "maps", "kref", "corr", "labels",
                 "labels_argmax", "onehot", "W", "T", "joint", "cond", "features")


def jsonable(o):
    """JSON-safe: numpy scalars/arrays to Python, NaN/inf to None."""
    import math
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return jsonable(o.tolist())
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if not math.isfinite(float(o)) else float(o)
    return o


def pick_example(run: Run, first_s: float = 30.0) -> int:
    """The preselected 'Show an example' moment: among the GFP peaks in the first `first_s` seconds, the one whose
    best |r| beats the runner-up by the widest margin (a clear, typical case). Deterministic for a given run."""
    a, s = run.arrays, run.summary
    idx = [int(i) for i in a["peak_idx"] if i < first_s * s["fs"] and i > s["fs"]]
    c = np.sort(a["corr"][:, idx], axis=0)
    return idx[int(np.argmax(c[-1] - c[-2]))]


def save_bundle(run: Run, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "arrays.npz", **{k: run.arrays[k] for k in BUNDLE_ARRAYS})
    ex = pick_example(run)
    meta = {"format": "neurostate-demo-bundle v1", "run_id": run.run_id, "source": run.source,
            "file_name": run.file_name, "file_sha256": run.file_sha256, "settings": run.settings,
            "steps": run.steps, "summary": run.summary, "example_i": ex,
            "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (out / "bundle.json").write_text(json.dumps(jsonable(meta), indent=1), encoding="utf-8")
    pngs = out / "png"
    pngs.mkdir(exist_ok=True)
    for k in range(4):
        (pngs / f"fitted_{k}.png").write_bytes(map_png(run, "fitted", k))
        (pngs / f"template_{k}.png").write_bytes(map_png(run, "template", k))
    (pngs / f"instant_{ex}.png").write_bytes(instant_png(run, ex))
    return meta


def load_bundle(src: Path, run_id: str = "demo") -> Run:
    meta = json.loads((src / "bundle.json").read_text(encoding="utf-8"))
    z = np.load(src / "arrays.npz")
    run = Run(run_id=run_id, path="", source=meta["source"], file_name=meta["file_name"],
              file_sha256=meta["file_sha256"], settings=meta["settings"], steps=meta["steps"],
              arrays={k: z[k] for k in z.files}, summary=meta["summary"])
    run.summary["example_i"] = meta["example_i"]
    run.summary["built_utc"] = meta["built_utc"]
    for p in (src / "png").glob("*.png"):  # precomputed figures
        kind, k = p.stem.split("_")
        if kind == "instant":
            run.arrays.setdefault("_instant_png", {})[int(k)] = p.read_bytes()
        else:
            run.arrays[f"png_{kind}_{int(k)}"] = p.read_bytes()
    return run
