"""Small EDF fixtures built with MNE (mne.export.export_raw, edfio backend) for the incompatible-file tests."""
from __future__ import annotations

import re
from pathlib import Path

import mne
import numpy as np

STD19 = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T3", "C3", "Cz", "C4", "T4", "T5", "P3", "Pz", "P4", "T6",
         "O1", "O2"]


def _raw(ch, sfreq, seconds, seed=0, annotations=None):
    rng = np.random.default_rng(seed)
    n = int(round(sfreq * seconds))
    t = np.arange(n) / sfreq
    data = (20e-6 * np.sin(2 * np.pi * 10 * t)[None] * rng.uniform(-1, 1, (len(ch), 1))
            + 10e-6 * rng.standard_normal((len(ch), n)))
    raw = mne.io.RawArray(data, mne.create_info(ch, sfreq, "eeg"), verbose="ERROR")
    if annotations:
        raw.set_annotations(mne.Annotations(*zip(*annotations)))
    return raw


def write(raw, path: Path) -> Path:
    mne.export.export_raw(str(path), raw, fmt="edf", overwrite=True, verbose="ERROR")
    return path


def valid(path: Path, seconds=30.0, sfreq=128.0, annotations=None) -> Path:
    return write(_raw(STD19, sfreq, seconds, annotations=annotations), path)


def missing_channel(path: Path) -> Path:
    return write(_raw([c for c in STD19 if c != "Pz"], 128.0, 30.0), path)


def low_rate(path: Path) -> Path:
    return write(_raw(STD19, 64.0, 30.0), path)


def too_short(path: Path) -> Path:
    return write(_raw(STD19, 128.0, 3.0), path)


def corrupted_header(path: Path) -> Path:
    """A valid file whose fixed header is shifted by one byte from byte 87 on (as the Zenodo 04^01.edf case)."""
    valid(path)
    b = bytearray(path.read_bytes())
    b[87:256] = b[88:256] + b" "
    path.write_bytes(bytes(b))
    return path


def with_gap(path: Path, gap_after_record: int = 12, gap_s: float = 5.0, seconds: float = 30.0) -> Path:
    """EDF+D: a valid EDF+ file whose time-keeping TALs jump by `gap_s` after one data record, with the reserved
    field set to 'EDF+D'. The signal samples are untouched; only the record onsets say there is a gap."""
    valid(path, seconds=seconds, annotations=[(2.0, 0.0, "eyes closed")])
    b = bytearray(path.read_bytes())
    ns = int(b[252:256].decode())
    hdr_bytes = int(b[184:192].decode())
    labels = [b[256 + i * 16: 256 + (i + 1) * 16].decode().strip() for i in range(ns)]
    off = 256 + ns * (16 + 80 + 8 + 8 + 8 + 8 + 8 + 80)
    spr = [int(b[off + i * 8: off + (i + 1) * 8].decode()) for i in range(ns)]
    n_rec = int(b[236:244].decode())
    ai = labels.index("EDF Annotations")
    rec_bytes = 2 * sum(spr)
    a_off = 2 * sum(spr[:ai])
    a_len = 2 * spr[ai]
    b[192:236] = b"EDF+D".ljust(44)
    for r in range(gap_after_record + 1, n_rec):
        s0 = hdr_bytes + r * rec_bytes + a_off
        chunk = bytes(b[s0:s0 + a_len])
        m = re.match(rb"([+-][0-9.]+)\x14\x14", chunk)
        onset = float(m.group(1)) + gap_s
        rest = chunk[m.end():]  # other TALs in this record keep their own (gap-including) onsets
        new = f"+{onset:g}".encode() + b"\x14\x14" + rest
        b[s0:s0 + a_len] = new[:a_len].ljust(a_len, b"\x00")
    path.write_bytes(bytes(b))
    return path
