"""Each incompatible case gives a message that says what was found and what is needed."""
import pytest

import edf_fixtures as fx
from conftest import needs_inputs


def _check(pa, path):
    c = pa.check_file(str(path))
    return c, " ".join(p["message"] for p in c["problems"])


def test_missing_channel(pa, tmp_path):
    c, msg = _check(pa, fx.missing_channel(tmp_path / "a.edf"))
    assert not c["ok"] and "missing: Pz" in msg and c["missing"] == ["Pz"]


def test_low_sampling_rate(pa, tmp_path):
    c, msg = _check(pa, fx.low_rate(tmp_path / "a.edf"))
    assert not c["ok"] and "too low" in msg and "64 Hz" in msg


def test_too_short(pa, tmp_path):
    c, msg = _check(pa, fx.too_short(tmp_path / "a.edf"))
    assert not c["ok"] and "shorter than one 4-s window" in msg


def test_corrupted_header_is_refused(pa, tmp_path):
    c, msg = _check(pa, fx.corrupted_header(tmp_path / "a.edf"))
    assert not c["ok"] and "refused rather than misread" in msg


def test_manual_bounds_outside(pa, tmp_path):
    c = pa.check_file(str(fx.valid(tmp_path / "a.edf")), tmin=5, tmax=99)
    assert not c["ok"] and "outside the recording" in c["problems"][0]["message"]


@needs_inputs
def test_gap_never_crossed(pa, tmp_path):
    p = fx.with_gap(tmp_path / "gap.edf", gap_after_record=12, gap_s=5.0)
    c = pa.check_file(str(p))
    assert c["ok"] and c["edf_type"] == "EDF+D" and len(c["gaps"]) == 1
    seg = c["segment"]
    assert "gaps" in seg["note"]
    junction = 13.0  # records are 1 s; MNE concatenates them, so the junction is after 13 s of samples
    assert seg["tmin"] >= junction or seg["tmax"] <= junction
    run = pa.run_pipeline(str(p))
    assert run.steps["segment"]["tmin"] >= junction or run.steps["segment"]["tmax"] <= junction


@needs_inputs
def test_valid_fixture_runs(pa, tmp_path):
    run = pa.run_pipeline(str(fx.valid(tmp_path / "v.edf", annotations=[(5.0, 0.0, "Eyes Closed"), (25.0, 0.0, "eyes open")])))
    assert run.steps["segment"]["method"] == "marker"
    assert (run.steps["segment"]["tmin"], run.steps["segment"]["tmax"]) == (5.0, 25.0)
    with pytest.raises(pa.Incompatible):
        pa.run_pipeline(str(fx.low_rate(tmp_path / "l.edf")))
