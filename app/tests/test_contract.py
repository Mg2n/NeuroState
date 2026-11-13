"""Study results contract: pending without a file, pending + logged error for an invalid file, converter output."""
import json
import logging

import pytest

from app import study_contract as sc
from app.tools import build_study_results as bsr
from conftest import APP, REPO

FOLLOWUP = REPO / "results" / "followup_seqcnn"


def _write(tmp_path, obj, study="epilepsy"):
    d = tmp_path / study
    d.mkdir(parents=True, exist_ok=True)
    (d / "results.json").write_text(json.dumps(obj) if not isinstance(obj, str) else obj)
    return tmp_path


def _base(**kw):
    d = {"schema_version": "1.0", "study_id": "epilepsy", "generated_at": "2026-11-20T10:00:00Z", "status": "trained",
         "labels": ["epilepsy", "no epilepsy"],
         "cohort": {"recordings_ingested": 120, "recordings_processed": 110, "unique_patients_training": 80},
         "runs": [{"run_id": "r1", "created": "2026-11-20", "model": "seq-CNN", "input": "one-hot 4×512",
                   "n_train_patients": 80, "train_metrics": {"epochs_trained_mean": 20.5}, "source_path": "results/x/results.json",
                   "source_sha256": "0" * 64}]}
    d.update(kw)
    return d


def test_no_file_is_pending(tmp_path):
    assert sc.load_study("epilepsy", tmp_path)["state"] == "pending"


def test_repo_has_no_epilepsy_results_file():
    assert not (APP / "study_results" / "epilepsy" / "results.json").exists()
    assert sc.load_study("epilepsy")["state"] == "pending"


def test_invalid_file_is_pending_and_logged(tmp_path, caplog):
    with caplog.at_level(logging.ERROR, logger="neurostate.study"):
        out = sc.load_study("epilepsy", _write(tmp_path, {"schema_version": "1.0", "status": "evaluated"}))
    assert out["state"] == "pending" and "invalid" in out["reason"]
    assert any("invalid study results file" in r.message for r in caplog.records)
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="neurostate.study"):
        assert sc.load_study("epilepsy", _write(tmp_path, "{not json"))["state"] == "pending"
    assert caplog.records


def test_patient_ids_rejected(tmp_path):
    bad = _base()
    bad["cohort"]["patient_ids"] = ["sub-001"]
    assert sc.load_study("epilepsy", _write(tmp_path, bad))["state"] == "pending"


def test_without_evaluation_no_eval_panel(tmp_path):
    out = sc.load_study("epilepsy", _write(tmp_path, _base()))
    assert out["state"] == "results" and out["results"]["evaluation"] is None


def test_with_evaluation(tmp_path):
    ev = {"split_description": "5-fold patient-level CV", "n_test_patients": 40, "metric": "balanced_accuracy",
          "value": 0.7, "sd": 0.05, "n_folds": 5, "comparators": [{"name": "logreg", "value": 0.68}]}
    out = sc.load_study("epilepsy", _write(tmp_path, _base(status="evaluated", evaluation=ev)))
    assert out["state"] == "results" and out["results"]["evaluation"]["value"] == 0.7
    with pytest.raises(Exception):  # evaluation without the evaluated status is inconsistent
        sc.StudyResults.model_validate(_base(evaluation=ev))


def test_learning_curve_needs_two_sizes(tmp_path):
    one = [{"train_patients": 40, "metric": "balanced_accuracy", "mean": 0.7, "sd": 0.05, "n_draws": 5}]
    out = sc.load_study("epilepsy", _write(tmp_path, _base(learning_curve=one)))
    assert out["curve_groups"] == []
    two = one + [{"train_patients": 80, "metric": "balanced_accuracy", "mean": 0.74, "sd": 0.04, "n_draws": 1}]
    assert len(sc.load_study("epilepsy", _write(tmp_path, _base(learning_curve=two)))["curve_groups"]) == 1
    mixed = one + [{"train_patients": 80, "metric": "auc", "mean": 0.8, "n_draws": 1}]
    assert sc.load_study("epilepsy", _write(tmp_path, _base(learning_curve=mixed)))["curve_groups"] == []


@pytest.mark.skipif(not FOLLOWUP.exists(), reason="results/followup_seqcnn not present")
def test_converter_on_alzheimer_outputs(tmp_path):
    out = tmp_path / "alz" / "results.json"
    bsr.main(["--run", str(FOLLOWUP), "--study", "alz", "--out", str(out), "--labels", "AD", "HC"])
    d = json.loads(out.read_text())
    sc.StudyResults.model_validate(d)
    res = json.loads((FOLLOWUP / "results.json").read_text())
    assert d["status"] == "evaluated"
    assert d["evaluation"]["value"] == pytest.approx(res["models"]["seqcnn_onehot"]["balanced_accuracy"]["mean"], abs=1e-12)
    assert d["evaluation"]["sd"] == pytest.approx(res["models"]["seqcnn_onehot"]["balanced_accuracy"]["sd"], abs=1e-12)
    assert d["evaluation"]["n_folds"] == 15 and d["evaluation"]["n_test_patients"] == 65
    assert d["evaluation"]["comparators"][0]["value"] == pytest.approx(res["models"]["logreg"]["balanced_accuracy"]["mean"], abs=1e-12)
    assert d["evaluation"]["p_value_vs_first_comparator"] == pytest.approx(res["tests"][0]["corrected_p"])
    assert sorted({p["train_patients"] for p in d["learning_curve"]}) == [20, 35, 52]
    assert "sub-" not in out.read_text()
    out_loaded = sc.load_study("alz", tmp_path)
    assert out_loaded["state"] == "results" and len(out_loaded["curve_groups"]) == 4  # 2 models x (balanced accuracy, AUC)


@pytest.mark.skipif(not FOLLOWUP.exists(), reason="results/followup_seqcnn not present")
def test_converter_on_run_experiment_fixture(tmp_path):
    """A run_experiment.py output folder (one of the pilot's sub-runs serves as the fixture)."""
    out = tmp_path / "x" / "results.json"
    bsr.main(["--run", str(FOLLOWUP / "main_seed0"), "--study", "x", "--out", str(out), "--labels", "epilepsy", "no epilepsy"])
    d = json.loads(out.read_text())
    assert d["labels"] == ["epilepsy", "no epilepsy"] and d["runs"][0]["input"] == "one-hot 4×512"
    assert d["runs"][0]["train_metrics"]["n_networks_trained"] == 15
    assert "sub-" not in out.read_text()


def test_schema_file_is_current():
    assert json.loads((APP / "study_results" / "schema.json").read_text()) == sc.json_schema()


@pytest.mark.skipif(not FOLLOWUP.exists(), reason="results/followup_seqcnn not present")
def test_alzheimer_panel_reads_files():
    from app import alz_pilot
    p = alz_pilot.load()
    res = json.loads((FOLLOWUP / "results.json").read_text())
    assert p["seqcnn"]["mean"] == res["models"]["seqcnn_onehot"]["balanced_accuracy"]["mean"]
    assert p["logreg"]["mean"] == res["models"]["logreg"]["balanced_accuracy"]["mean"]
    assert p["n_participants"] == 65 and p["n_test_folds"] == 15
    assert p["primary_test"]["p"] == res["tests"][0]["corrected_p"]
    assert [c["train_subjects"] for c in p["curve"]] == [20, 35, 52]
