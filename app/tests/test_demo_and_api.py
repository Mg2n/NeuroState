"""The demo serves one fixed bundle (same outputs everywhere, no recomputation); the API returns backend values;
research jobs run the real pipeline in the background."""
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from conftest import DEMO, SAMPLE, needs_inputs

pytestmark = needs_inputs


@pytest.fixture(scope="module")
def client():
    if not (DEMO / "bundle.json").exists():
        pytest.skip("demo bundle not built (app/tools/build_demo.py)")
    from app import server
    server.RUNS.pop("demo", None)
    return TestClient(server.app)


def test_bundle_equals_fresh_pipeline_run(pa, sample_run):
    demo = pa.load_bundle(DEMO)
    for k in ("ms", "raw_uv", "corr", "labels", "maps", "kref", "W", "features", "peak_idx", "gfp", "T"):
        np.testing.assert_array_equal(demo.arrays[k], sample_run.arrays[k], err_msg=k)
    assert demo.steps["measures"]["table"] == sample_run.steps["measures"]["table"]
    assert demo.summary["absr"] == sample_run.summary["absr"]
    assert demo.file_sha256 == sample_run.file_sha256


def test_demo_works_on_its_own(client, monkeypatch, tmp_path):
    """No EDF and no pipeline needed: the demo endpoints read the bundle only."""
    from app import pipeline_adapter as pa
    from app import server

    def boom(*a, **k):
        raise AssertionError("the demo must not run the pipeline")

    monkeypatch.setattr(pa, "run_pipeline", boom)
    monkeypatch.setattr(server, "SAMPLE", tmp_path / "absent.edf")
    server.RUNS.pop("demo", None)
    d = client.get("/api/demo").json()
    assert d["run_id"] == "demo" and d["example_i"] is not None
    i = d["example_i"]
    inst = client.get(f"/api/runs/demo/instant?i={i}").json()
    assert inst["winner"] == inst["label"] and inst["sentence"].startswith(f"At {inst['t']:.2f} s")
    assert client.get(f"/api/runs/demo/instant.png?i={i}").headers["content-type"] == "image/png"
    for kind in ("fitted", "template"):
        assert client.get(f"/api/runs/demo/map/{kind}/0.png").status_code == 200
    assert client.get("/api/runs/demo/cnn_window/1").json()["shape"] == [4, 512]
    assert client.get("/api/runs/demo/signal?view=raw&t0=0&t1=5").json()["fs"] == 160.0


def test_api_payload_equals_backend(client):
    from app import server
    d = client.get("/api/demo").json()
    run = server.demo_run()
    a, st = run.arrays, run.steps
    assert d["labels"] == a["labels"].astype(int).tolist()
    assert d["features"] == [float(v) for v in a["features"]]
    assert d["measures"] == st["measures"]["table"]
    assert d["abs_r_template"] == run.summary["absr"]
    assert d["transitions"]["counts"] == a["T"].astype(int).tolist()
    assert d["maps"]["fitted"] == a["maps"].tolist()
    assert d["peak_idx"] == a["peak_idx"].astype(int).tolist()
    assert d["gev_all"] == run.summary["gev_all"] and d["gev_peaks"] == run.summary["gev_peaks"]
    assert d["steps"]["cnn"]["n_windows"] == len(a["W"])
    for i in (0, 1234, d["example_i"], d["n"] - 1):
        inst = client.get(f"/api/runs/demo/instant?i={i}").json()
        assert inst["abs_r"] == [float(v) for v in a["corr"][:, i]]
        assert inst["label"] == int(a["labels"][i])
        assert inst["values_uv"] == [float(v) for v in a["ms"][:, i]]
    w = client.get("/api/runs/demo/cnn_window/3").json()
    assert w["onehot"] == a["W"][3].astype(int).tolist()


def _wait(client, jid, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/research/jobs/{jid}").json()
        if j["status"] not in ("queued", "running"):
            return j
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def test_research_job_runs_real_pipeline(client, sample_run):
    j = _wait(client, client.post("/api/research/sample").json()["job_id"])
    assert j["status"] == "done" and j["steps_done"] == 9
    d = client.get(f"/api/runs/{j['run_id']}").json()
    assert d["labels"] == sample_run.arrays["labels"].astype(int).tolist()
    assert d["measures"] == sample_run.steps["measures"]["table"]
    assert d["transitions"]["counts"] == sample_run.arrays["T"].astype(int).tolist()
    z = client.get(f"/api/runs/{j['run_id']}/export.zip")
    import io
    import json
    import zipfile
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    for n in ("measures.csv", "transitions_counts.csv", "labels_per_sample.csv", "maps.csv", "manifest.json",
              "figures/fitted_maps_vs_templates.png"):
        assert n in names
    man = json.loads(zipfile.ZipFile(io.BytesIO(z.content)).read("manifest.json"))
    assert man["input"]["sha256"] == sample_run.file_sha256 and man["settings"]["seed"] == 42
    assert man["segment"]["tmin"] == 0.0 and "mne" in man["environment"]["libraries"]


def test_research_upload_incompatible(client, tmp_path):
    import edf_fixtures as fx
    p = fx.missing_channel(tmp_path / "m.edf")
    with p.open("rb") as fh:
        j = client.post("/api/research/upload", files={"file": ("m.edf", fh, "application/octet-stream")}).json()
    assert j["status"] == "incompatible" and "Pz" in j["problems"][0]["message"]


def test_peak_examples_and_fixed_scale(client):
    """Presentation helpers of the walkthrough: they only re-read existing arrays."""
    from app import server
    run = server.demo_run()
    d = client.get("/api/runs/demo/peak_examples?n=4").json()["maps"]
    assert sum(m["n_peaks"] for m in d) == len(run.arrays["peak_idx"]) == run.steps["peaks"]["n_used"]
    for m in d:
        assert m["cluster"] == run.summary["order"][m["k"]]
        for e in m["examples"]:
            assert int(np.argmax(run.arrays["corr"][:, e["i"]])) == m["k"]
            assert e["abs_r"] == float(run.arrays["corr"][m["k"], e["i"]])
            assert e["i"] in set(run.arrays["peak_idx"].tolist())
    a = client.get("/api/runs/demo/instant.png?i=100&vmax=50")
    b = client.get("/api/runs/demo/instant.png?i=100")
    assert a.status_code == b.status_code == 200 and a.content != b.content
