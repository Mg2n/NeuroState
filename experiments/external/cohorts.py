"""Registry and readers for the external AD/HC EEG cohorts stored under data/external/.

Each cohort function yields Recording objects. `load()` returns (data, ch_names, sfreq, info)
with data as float64 array (n_channels, n_samples) in volts, or a list of such arrays for
recordings that were released as separate artefact-free segments/epochs.

Nothing here modifies the downloaded files. Run with the project-local tools venv
(data/.venv) and `python -I`, because the inputs are third-party files.
"""
import csv
import glob
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXT = os.path.join(ROOT, "data", "external")

SOURCES = {
    "ds004504": ("https://openneuro.org/datasets/ds004504/versions/1.0.9", "CC0"),
    "ds006036": ("https://openneuro.org/datasets/ds006036/versions/1.0.7", "CC0"),
    "ds005048": ("https://openneuro.org/datasets/ds005048/versions/1.0.1", "CC0"),
    "hk_czech": ("https://doi.org/10.6084/m9.figshare.5450293.v1", "CC BY 4.0"),
    "apava_spain": ("https://osf.io/jbysn/", "none stated (cite Escudero et al. 2006; Smith et al. 2017)"),
    "fsu_duke": ("https://osf.io/2v5md/", "none stated (cite Vicchietti et al. 2023)"),
    "adsz_fsu": ("https://doi.org/10.6084/m9.figshare.19091771.v1", "CC0"),
    "padic_israel": ("https://doi.org/10.5061/dryad.8gtht76pw (copy: https://zenodo.org/records/7258868)", "CC0"),
}

STD19 = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T3", "C3", "Cz", "C4", "T4",
         "T5", "P3", "Pz", "P4", "T6", "O1", "O2"]


@dataclass
class Recording:
    cohort_id: str
    source_subject_id: str
    recording_id: str
    diagnosis_given: str
    group: str                      # AD / HC / MCI / FTD / other dementia / SCI / unclear
    condition: str                  # eyes_closed / eyes_open / rest_eo_ec_mixed / *_stimulation
    path: str                       # file or folder, relative to repo root
    fmt: str
    processing: str                 # raw / derivative / as released (described)
    files: list = field(default_factory=list)
    loader: Optional[Callable] = None
    age: str = ""
    sex: str = ""
    extra: dict = field(default_factory=dict)

    def load(self):
        return self.loader(self)


def rel(p):
    return os.path.relpath(p, ROOT)


def read_tsv(p):
    with open(p, encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f, delimiter="\t")]


# ---------------------------------------------------------------- OpenNeuro (BIDS, EEGLAB .set)
def _load_set(rec):
    import mne
    raw = mne.io.read_raw_eeglab(rec.files[0], preload=True, verbose="error")
    return raw.get_data(), raw.ch_names, raw.info["sfreq"], {"raw": raw}


AHEPA_GROUP = {"A": ("Alzheimer's disease (A)", "AD"), "C": ("healthy control (C)", "HC"),
               "F": ("frontotemporal dementia (F)", "FTD")}


def _bids_openneuro(cid, task, condition, group_map, raw_processing, deriv_dir=None,
                    deriv_processing=""):
    base = os.path.join(EXT, cid)
    for r in read_tsv(os.path.join(base, "participants.tsv")):
        sid = r["participant_id"]
        g = r.get("Group", "")
        dx, grp = group_map(g)
        age, sex = r.get("Age", ""), r.get("Gender", "")
        variants = [("raw", os.path.join(base, sid, "eeg", f"{sid}_task-{task}_eeg.set"), raw_processing)]
        if deriv_dir:
            variants.append(("derivative", os.path.join(base, deriv_dir, sid, "eeg",
                                                        f"{sid}_task-{task}_eeg.set"), deriv_processing))
        for var, p, proc in variants:
            files = [p] + ([p[:-4] + ".fdt"] if os.path.exists(p[:-4] + ".fdt") else [])
            yield Recording(cid, sid, f"{cid}:{sid}:{var}", dx, grp, condition, rel(p), "EEGLAB .set",
                            proc, files, _load_set, age, sex, {"MMSE": r.get("MMSE", "")})


def ds004504():
    yield from _bids_openneuro(
        "ds004504", "eyesclosed", "eyes_closed", lambda g: AHEPA_GROUP[g],
        "raw (exported from Nihon Kohden, Cz reference, no filtering beyond amplifier)",
        "derivatives", "derivative: 0.5-45 Hz Butterworth, A1-A2 re-reference, ASR, ICA (ICLabel eye/jaw removed)")


def ds006036():
    yield from _bids_openneuro(
        "ds006036", "photomark", "photic_stimulation_eyes_open", lambda g: AHEPA_GROUP[g],
        "raw (sidecar says SoftwareFilters 0.5-45; same recording session as ds004504)",
        os.path.join("derivatives", "eeglab"), "derivative (preprocessed, see ds006036 README)")


def ds005048():
    def gm(g):
        g = g.strip()
        if "AD" in g:
            return g, "AD"
        return g or "-", {"Normal": "HC", "MCI": "MCI"}.get(g, "unclear")
    yield from _bids_openneuro(
        "ds005048", "40HzAuditoryEntrainment", "auditory_40Hz_stimulation_eyes_open", gm,
        "as released: 1 Hz high-pass, line noise removal, bad-channel interpolation, ASR, ICA, average reference")


# ---------------------------------------------------------------- Hradec Kralove (figshare 5450293)
def _hk_readme():
    rates = {}
    with open(os.path.join(EXT, "hk_czech", "extracted", "readme.txt"), encoding="latin-1") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 8 and re.fullmatch(r"(AD|MCI|normal)\d+", parts[7].strip()):
                rates[parts[7].strip()] = (parts[6].strip(), parts[:6])
    return rates


def _load_hk(rec):
    import scipy.io as sio
    segs = []
    for f in rec.files:
        d = sio.loadmat(f)
        k = [k for k in d if not k.startswith("__")][0]
        x = np.asarray(d[k], dtype=np.float64)
        # folder segments are (samples, channels); CONTROL/<id>fir.mat is (channels, samples)
        # Units are not documented. Amplitudes imply millivolts for the per-segment 'export' files
        # (raw SD ~0.02) and microvolts for CONTROL/<id>fir.mat (raw SD ~30).
        if k == "export":
            x = x.T * 1e-3
        else:
            x = x * 1e-6
        segs.append(x)
    sf = float(rec.extra["sfreq"]) if rec.extra.get("sfreq") else np.nan
    return segs, None, sf, {}


def hk_czech():
    base = os.path.join(EXT, "hk_czech", "extracted")
    rates = _hk_readme()
    for folder, dx, grp in [("AD", "Alzheimer's disease (NINCDS-ADRDA)", "AD"),
                            ("MCI", "mild cognitive impairment", "MCI"),
                            ("CONTROL", "control", "HC")]:
        for name in sorted(os.listdir(os.path.join(base, folder))):
            p = os.path.join(base, folder, name)
            if os.path.isdir(p):
                files = sorted(glob.glob(os.path.join(p, "*.mat")), key=lambda s: int(re.sub(r"\D", "", os.path.basename(s)) or 0))
                sid = name
                sf = rates.get(name, ("", None))[0]
                fmt = "MATLAB .mat, one file per artefact-free segment (samples x channels), no channel labels"
            else:
                files = [p]
                sid = name.replace("fir.mat", "")
                sf = "128"  # readme footer: '*fir.mat 128'
                fmt = "MATLAB .mat 'segmenty' (channels x samples), FIR-filtered, no channel labels"
            yield Recording("hk_czech", sid, f"hk_czech:{sid}", dx, grp, "eyes_closed", rel(p), fmt,
                            "as released: artefacts removed by neurophysiologist, 50 Hz notch, detrended; 256 Hz machine data down-sampled per paper but readme lists 256",
                            files, _load_hk, extra={"sfreq": sf, "readme_scores": rates.get(name, ("", None))[1]})


# ---------------------------------------------------------------- APAVA / Valladolid (OSF jbysn)
def apava_labels():
    """AD(1)/control(0) per subject index, read from 'patient1_control0' in SpainADdata.mat
    (Smith et al. 2017, Edinburgh DataShare doi:10.7488/ds/2109; downloaded to apava_spain/metadata/).
    File order of preproctrialsNN.mat = this index order (checked by apava_label_check.py)."""
    import scipy.io as sio
    v = sio.loadmat(os.path.join(EXT, "apava_spain", "metadata", "SpainADdata.mat"))["patient1_control0"]
    return {i + 1: int(x) for i, x in enumerate(np.asarray(v).ravel())}


def _load_apava(rec):
    import scipy.io as sio
    d = sio.loadmat(rec.files[0], squeeze_me=True, struct_as_record=False)["data"]
    tr = d.trial
    if isinstance(tr, np.ndarray) and tr.dtype != object and tr.ndim == 2:
        trials = [np.asarray(tr, dtype=np.float64)]  # single trial: squeeze_me removed the cell level
    else:
        trials = [np.asarray(t, dtype=np.float64) for t in np.atleast_1d(tr)]
    return [t * 1e-6 for t in trials], [str(c) for c in d.label], float(d.fsample), {}


def apava_spain():
    base = os.path.join(EXT, "apava_spain", "extracted")
    labels = apava_labels()
    for p in sorted(glob.glob(os.path.join(base, "preproctrials*.mat"))):
        i = int(re.search(r"(\d+)", os.path.basename(p)).group(1))
        ad = labels[i] == 1
        yield Recording("apava_spain", f"{i:02d}", f"apava_spain:{i:02d}",
                        "AD (patient1_control0 = 1, Smith et al. 2017)" if ad else "control (patient1_control0 = 0, Smith et al. 2017)",
                        "AD" if ad else "HC", "eyes_closed", rel(p),
                        "FieldTrip struct (.mat), 5-s preprocessed trials", "as released: preprocessed FieldTrip trials",
                        [p], _load_apava)


# ---------------------------------------------------------------- Florida State (OSF 2v5md) and ADSZ copy
def _load_fsu(rec):
    folder = rec.files[0]
    if not os.listdir(folder):
        raise FileNotFoundError("empty folder in the released zip")
    data = [np.loadtxt(os.path.join(folder, c + ".txt")) for c in STD19]
    return np.vstack(data) * 1e-6, list(STD19), 128.0, {}


def fsu_duke():
    base = os.path.join(EXT, "fsu_duke", "extracted", "EEG_data")
    for gdir, dx, grp in [("AD", "probable AD (NINCDS-ADRDA, DSM-III-R)", "AD"), ("Healthy", "healthy elderly", "HC")]:
        for cdir, cond in [("Eyes_closed", "eyes_closed"), ("Eyes_open", "eyes_open")]:
            for folder in sorted(glob.glob(os.path.join(base, gdir, cdir, "*")), key=lambda s: int(re.sub(r"\D", "", os.path.basename(s)))):
                sid = f"{gdir}_{os.path.basename(folder)}"
                yield Recording("fsu_duke", sid, f"fsu_duke:{sid}:{cond}", dx, grp, cond, rel(folder),
                                "text, one file per channel (21 files; F1=Fp1 and F2=Fp2 duplicates)",
                                "as released: 8-s segment, band-limited 0.5-30 Hz", [folder], _load_fsu)


def _load_adsz(rec):
    x = np.loadtxt(rec.files[0])
    return x.T * 1e-6, list(STD19), 128.0, {}


def adsz_fsu():
    base = os.path.join(EXT, "adsz_fsu", "extracted", "dataset", "alzheimer")
    for gdir, grp in [("AD", "AD"), ("Healthy", "HC")]:
        for p in sorted(glob.glob(os.path.join(base, gdir, "*.out"))):
            fn = os.path.basename(p)[:-4]
            if gdir == "AD":
                m = re.fullmatch(r"(e[co])(\d\d)(\d\d)", fn)
                cond = "eyes_closed" if m.group(1) == "ec" else "eyes_open"
                sid = f"AD_{m.group(2)}{m.group(3)}"  # ecXXYY / eoXXYY pairs share XXYY
            else:
                m = re.fullmatch(r"eeg(\d+)([co])1", fn)
                cond = "eyes_closed" if m.group(2) == "c" else "eyes_open"
                sid = f"H_{m.group(1)}"
            yield Recording("adsz_fsu", sid, f"adsz_fsu:{fn}", gdir, grp, cond, rel(p),
                            "text matrix (1024 samples x 19 channels; channel order assumed from paper list)",
                            "as released: 8-s artefact-free segment", [p], _load_adsz)


# ---------------------------------------------------------------- P-ADIC, Israel (Dryad / Zenodo 7258868)
# Each file holds one MATLAB v7.3 struct (e.g. alz_r) with (3 x n_subjects) cell fields:
#   G = EEG (samples x 19, channel names not stored), g = sampling rate, age = [years (, months)],
#   sex, eegdate, birth (never read or copied here), eeg_files/n = original file name,
#   m = undocumented (range 0-30, looks like MMSE; reported as 'm (undocumented)').
# Row 0 = first recording; rows 1-2 = further recordings of the same person (other dates).
PADIC_FILES = [("alz_c1_new.mat", "AD (NIA-AA, two neurologists)", "AD", "AD"),
               ("mci_c1_new.mat", "MCI (NIA-AA, two neurologists)", "MCI", "MCI"),
               ("controls_c1_new.mat", "control: routine EEG for indications unrelated to neuropsychiatric disease (not cognitively assessed)", "HC", "C")]


def _h5str(f, ref):
    o = f[ref]
    if o.attrs.get("MATLAB_empty", 0):
        return ""
    return "".join(map(chr, o[()].ravel())).replace("\x00", "").strip()


def _h5num(f, ref):
    o = f[ref]
    if o.attrs.get("MATLAB_empty", 0):
        return None
    return o[()].ravel()


def padic_file_name(f, s, i, j):
    """Original EEG file name: field eeg_files, or the char inside cell field n (controls file)."""
    if "eeg_files" in s:
        return _h5str(f, s["eeg_files"][i, j])
    o = f[s["n"][i, j]]
    if o.attrs.get("MATLAB_empty", 0):
        return ""
    if o.dtype == object:
        return _h5str(f, o[()].ravel()[0])
    return _h5str(f, s["n"][i, j])


def _load_padic(rec):
    import h5py
    with h5py.File(rec.files[0], "r") as f:
        s = f[rec.extra["struct"]]
        i, j = rec.extra["cell"]
        o = f[s["G"][i, j]]
        if o.dtype == object:  # controls file wraps G in a 1x1 cell
            o = f[o[()].ravel()[0]]
        x = np.asarray(o[()], dtype=np.float64).T  # (19, samples)
        sf = float(_h5num(f, s["g"][i, j])[0])
    return x * 1e-6, None, sf, {}  # amplitudes imply microvolts (not documented)


def padic_israel():
    import h5py
    base = os.path.join(EXT, "padic_israel", "download")
    for fn, dx, grp, prefix in PADIC_FILES:
        p = os.path.join(base, fn)
        if not os.path.exists(p) or os.path.exists(p + ".part"):
            continue
        try:
            f = h5py.File(p, "r")
        except OSError:  # still downloading
            continue
        with f:
            name = [k for k in f.keys() if not k.startswith("#")][0]
            s = f[name]
            for j in range(s["G"].shape[1]):
                for i in range(s["G"].shape[0]):
                    if f[s["G"][i, j]].attrs.get("MATLAB_empty", 0):
                        continue
                    age = _h5num(f, s["age"][i, j])
                    sid = f"{prefix}{j + 1:03d}"
                    yield Recording("padic_israel", sid, f"padic_israel:{sid}:rec{i + 1}", dx, grp, "rest_eo_ec_mixed",
                                    rel(p) + f"#{name}.G{{{i + 1},{j + 1}}}",
                                    "MATLAB v7.3 struct field G (samples x 19), no channel labels, no eye-state markers",
                                    "as released: 'EEG raw data filtered with high pass band of 1Hz' (author readme)",
                                    [p], _load_padic,
                                    age=str(int(age[0])) if age is not None else "",
                                    sex=_h5str(f, s["sex"][i, j]),
                                    extra={"struct": name, "cell": (i, j), "slice": f"{name}.G{{{i + 1},{j + 1}}}",
                                           "eegdate": _h5str(f, s["eegdate"][i, j]) if "eegdate" in s else "",
                                           "m_undocumented": (lambda v: "" if v is None else str(v[0]))(_h5num(f, s["m"][i, j])) if "m" in s else "",
                                           "repeat_index": i + 1})


COHORTS = {"ds004504": ds004504, "ds006036": ds006036, "ds005048": ds005048, "hk_czech": hk_czech,
           "apava_spain": apava_spain, "fsu_duke": fsu_duke, "adsz_fsu": adsz_fsu,
           "padic_israel": padic_israel}


def all_recordings(which=None):
    for cid, fn in COHORTS.items():
        if which and cid not in which:
            continue
        if not os.path.exists(os.path.join(EXT, cid)):
            continue
        yield from fn()
