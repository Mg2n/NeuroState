"""Starts two local servers (no epilepsy results file / a fixture results file) and runs the Playwright checks in
app/tests/e2e/e2e.js. Screenshots go to app/screenshots/."""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

import edf_fixtures as fx
from conftest import APP, DEMO, REPO, SAMPLE, needs_inputs

pytestmark = needs_inputs


def _port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _serve(env_extra):
    port = _port()
    env = {**os.environ, **env_extra}
    p = subprocess.Popen([sys.executable, "-m", "app", "--no-browser", "--port", str(port)], cwd=REPO, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1)
            return p, f"http://127.0.0.1:{port}/"
        except OSError:
            time.sleep(0.2)
    p.kill()
    raise RuntimeError("server did not start")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_browser_end_to_end(tmp_path):
    if not (DEMO / "bundle.json").exists():
        pytest.skip("demo bundle not built")
    (APP / "tests" / "fixtures").mkdir(exist_ok=True)
    fx.missing_channel(APP / "tests" / "fixtures" / "missing_pz.edf")
    study = tmp_path / "study"
    (study / "epilepsy").mkdir(parents=True)
    (study / "epilepsy" / "results.json").write_text(json.dumps({
        "schema_version": "1.0", "study_id": "epilepsy", "generated_at": "fixture", "status": "evaluated",
        "labels": ["epilepsy", "no epilepsy"],
        "cohort": {"recordings_ingested": 12, "recordings_processed": 11, "unique_patients_training": 10, "unique_patients_test": 10,
                   "eligible_patients_available": 30},
        "runs": [{"run_id": "fixture", "created": "fixture", "model": "fixture model", "input": "one-hot 4×512", "n_train_patients": 8,
                  "train_metrics": {"epochs_trained_mean": 3.0}, "source_path": "fixture", "source_sha256": "0" * 64}],
        "evaluation": {"split_description": "FIXTURE ONLY", "n_test_patients": 10, "metric": "balanced_accuracy", "value": 0.5,
                       "sd": 0.1, "n_folds": 5, "comparators": []},
        "learning_curve": [{"train_patients": 4, "metric": "balanced_accuracy", "mean": 0.5, "sd": 0.1, "n_draws": 3},
                           {"train_patients": 8, "metric": "balanced_accuracy", "mean": 0.5, "sd": 0.1, "n_draws": 1}]}))
    a, base = _serve({})
    b, base_res = _serve({"NEUROSTATE_STUDY_DIR": str(study)})
    try:
        r = subprocess.run(["node", str(APP / "tests" / "e2e" / "e2e.js")], cwd=APP / "tests" / "e2e", capture_output=True, text=True,
                           timeout=600, env={**os.environ, "BASE": base, "BASE_RESULTS": base_res, "SAMPLE": str(SAMPLE),
                                             "SHOTS": str(APP / "screenshots")})
        print(r.stdout[-6000:], r.stderr[-3000:])
        assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
    finally:
        a.kill(), b.kill()
