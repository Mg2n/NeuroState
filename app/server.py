"""Local FastAPI backend.

Two flows:
  * /api/demo ...       the interactive demo: ONE fixed public recording, served from the precomputed bundle in
                        app/cache/demo (built by app/tools/build_demo.py with the real pipeline). Nothing is recomputed.
  * /api/research/...   epilepsy research processing: compatible EDF files are checked, then run through the real
                        pipeline in a background worker; status and outputs are read back by polling.
  * /api/study/...      study results (epilepsy contract, Alzheimer's pilot panel).
"""
from __future__ import annotations

import json
import logging
import queue
import shutil
import threading
import time
import traceback
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import alz_pilot, study_contract
from . import pipeline_adapter as pa

APP = Path(__file__).resolve().parent
CACHE = APP / "cache"
UPLOADS = CACHE / "uploads"
SAMPLE = CACHE / "sample" / "S001R02.edf"
DEMO = CACHE / "demo"
log = logging.getLogger("neurostate")

app = FastAPI(title="NeuroState hackathon interface", docs_url=None, redoc_url=None)
RUNS: "OrderedDict[str, pa.Run]" = OrderedDict()
MAX_RUNS = 24
JOBS: "OrderedDict[str, dict]" = OrderedDict()
WORK: queue.Queue = queue.Queue()
_demo_lock = threading.Lock()


def J(o, status=200) -> Response:
    return Response(json.dumps(pa.jsonable(o), ensure_ascii=False, allow_nan=False), status_code=status,
                    media_type="application/json")


def demo_run() -> pa.Run:
    with _demo_lock:
        if "demo" not in RUNS:
            if not (DEMO / "bundle.json").exists():
                raise HTTPException(503, "The demo bundle is not built yet. Run once: "
                                         "experiments/.venv/bin/python app/tools/fetch_public_inputs.py")
            RUNS["demo"] = pa.load_bundle(DEMO)
            threading.Thread(target=_warm_demo, args=(RUNS["demo"],), daemon=True).start()
        return RUNS["demo"]


def _warm_demo(run: pa.Run):
    """Render the demo's explanatory scalp maps ahead of time so the walkthrough never waits (presentation only)."""
    try:
        for m in pa.peak_examples(run, 4):
            for e in m["examples"]:
                pa.instant_png(run, e["i"])
        for k in range(4):
            pa.map_png(run, "fitted", k), pa.map_png(run, "template", k)
    except Exception:  # noqa: BLE001  (warm-up only; requests render on demand anyway)
        log.warning("demo warm-up failed: %s", traceback.format_exc())


def get_run(rid: str) -> pa.Run:
    if rid == "demo":
        return demo_run()
    if rid not in RUNS:
        raise HTTPException(404, "unknown run (research runs are kept in memory; process the file again)")
    return RUNS[rid]


def _opt(x) -> float | None:
    return None if x in (None, "") else float(x)


@app.get("/api/status")
def status():
    return J({"demo_ready": (DEMO / "bundle.json").exists(), "sample_cached": SAMPLE.exists(),
              "template_cached": pa.TEMPLATE_PATH.exists(), "steps": [{"id": s, "title": t} for s, t in pa.STEPS],
              "channels": pa.prep.CHANNELS, "default_view": pa.DEFAULT_VIEW,
              "settings": {"seed": pa.SEED, "n_init": pa.N_INIT, "max_peaks": pa.MAX_PEAKS, "marker": pa.MARKER,
                           "win": pa.rx.WIN, "fs": pa.prep.SFREQ}})


# ------------------------------------------------------------------------------------------------ demo
@app.get("/api/demo")
def demo():
    return J(pa.results_payload(demo_run()))


# ------------------------------------------------------------------------------------------------ research jobs
def _job_view(j: dict) -> dict:
    keys = ("job_id", "name", "source", "status", "step", "step_title", "steps_done", "n_steps", "problems", "message",
            "run_id", "created", "finished", "check", "seconds")
    return {k: j.get(k) for k in keys}


def _worker():
    titles = dict(pa.STEPS)
    while True:
        jid = WORK.get()
        j = JOBS.get(jid)
        if j is None:
            continue
        j["status"], t0 = "running", time.time()

        def emit(step, _res, j=j):
            j["steps_done"] = j.get("steps_done", 0) + 1
            j["step"], j["step_title"] = step, titles[step]

        try:
            run = pa.run_pipeline(j["path"], source=j["source"], tmin=j["tmin"], tmax=j["tmax"],
                                  min_segment=j["min_segment"], emit=emit, file_name=j["name"])
            RUNS[run.run_id] = run
            while len(RUNS) > MAX_RUNS:
                k = next(k for k in RUNS if k != "demo")
                RUNS.pop(k)
            j.update(status="done", run_id=run.run_id)
        except pa.Incompatible as e:
            j.update(status="incompatible", problems=e.problems)
        except Exception as e:  # noqa: BLE001
            log.error("research job %s failed: %s", jid, traceback.format_exc())
            j.update(status="failed", message=f"{type(e).__name__}: {e}")
        j["finished"], j["seconds"] = time.time(), time.time() - t0


threading.Thread(target=_worker, daemon=True, name="research-worker").start()


def _submit(path: str, name: str, source: str, tmin, tmax, min_segment: int) -> dict:
    jid = uuid.uuid4().hex[:10]
    chk = pa.check_file(path, pa.MARKER, tmin, tmax)
    j = {"job_id": jid, "path": path, "name": name, "source": source, "tmin": tmin, "tmax": tmax,
         "min_segment": int(min_segment), "created": time.time(), "n_steps": len(pa.STEPS), "steps_done": 0,
         "check": {k: chk.get(k) for k in ("ok", "duration_s", "sfreq", "edf_type", "missing", "segment", "markers",
                                            "gaps", "stretches", "aliases_applied")} | {"n_not_used": len(chk.get("not_used", []))}}
    if chk["ok"]:
        j["status"] = "queued"
        WORK.put(jid)
    else:
        j.update(status="incompatible", problems=chk["problems"], finished=time.time())
    JOBS[jid] = j
    return _job_view(j)


@app.post("/api/research/upload")
async def research_upload(file: UploadFile = File(...), tmin: str = Form(""), tmax: str = Form(""),
                          min_segment: int = Form(0)):
    UPLOADS.mkdir(parents=True, exist_ok=True)
    dest = UPLOADS / f"{uuid.uuid4().hex[:12]}.edf"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return J(_submit(str(dest), file.filename or "upload.edf", "upload", _opt(tmin), _opt(tmax), min_segment))


@app.post("/api/research/sample")
def research_sample():
    """Queue the cached public sample through the real pipeline (a quick end-to-end check of the research flow)."""
    if not SAMPLE.exists():
        raise HTTPException(404, "The sample is not cached. Run app/tools/fetch_public_inputs.py once.")
    return J(_submit(str(SAMPLE), "S001R02.edf (PhysioNet EEGMMIDB, public test file)", "sample", None, None, 0))


@app.get("/api/research/jobs")
def research_jobs():
    return J({"jobs": [_job_view(j) for j in reversed(JOBS.values())]})


@app.get("/api/research/jobs/{jid}")
def research_job(jid: str):
    if jid not in JOBS:
        raise HTTPException(404, "unknown job")
    return J(_job_view(JOBS[jid]))


# ------------------------------------------------------------------------------------------------ run views
@app.get("/api/runs/{rid}")
def results(rid: str):
    return J(pa.results_payload(get_run(rid)))


@app.get("/api/runs/{rid}/signal")
def signal(rid: str, view: str = "proc", t0: float = 0.0, t1: float = 10.0, channels: str = ""):
    run = get_run(rid)
    chs = [c for c in channels.split(",") if c in pa.prep.CHANNELS] or pa.DEFAULT_VIEW
    return J(pa.signal(run, "raw" if view == "raw" else "proc", t0, t1, chs))


@app.get("/api/runs/{rid}/instant")
def instant(rid: str, i: int):
    return J(pa.instant(get_run(rid), i))


@app.get("/api/runs/{rid}/instant.png")
def instant_png(rid: str, i: int, vmax: float | None = None):
    return Response(pa.instant_png(get_run(rid), i, vmax), media_type="image/png", headers={"Cache-Control": "max-age=3600"})


@app.get("/api/runs/{rid}/peak_examples")
def peak_examples(rid: str, n: int = 4):
    return J({"maps": pa.peak_examples(get_run(rid), max(1, min(n, 8)))})


@app.get("/api/runs/{rid}/map/{kind}/{k}.png")
def map_png(rid: str, kind: str, k: int):
    if kind not in ("fitted", "template") or not 0 <= k < 4:
        raise HTTPException(404)
    return Response(pa.map_png(get_run(rid), kind, k), media_type="image/png", headers={"Cache-Control": "max-age=3600"})


@app.get("/api/runs/{rid}/cnn_window/{k}")
def cnn_window(rid: str, k: int):
    run = get_run(rid)
    W = run.arrays["W"]
    if not 0 <= k < len(W):
        raise HTTPException(404, f"window {k} does not exist ({len(W)} complete windows)")
    s = run.summary
    return J({"k": k, "n_windows": len(W), "shape": list(W[k].shape), "onehot": W[k].astype(int).tolist(),
              "t_start": s["t0"] + k * pa.rx.WIN / s["fs"], "t_end": s["t0"] + (k + 1) * pa.rx.WIN / s["fs"],
              "first_sample": k * pa.rx.WIN})


@app.get("/api/runs/{rid}/export.zip")
def export(rid: str):
    run = get_run(rid)
    stem = Path(run.file_name.split(" ")[0]).stem
    return Response(pa.export_zip(run), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="neurostate_{stem}_{rid}.zip"'})


# ------------------------------------------------------------------------------------------------ studies
@app.get("/api/study/{study}")
def study(study: str):
    if study == "alzheimers-pilot":
        return J({"panel": alz_pilot.load()})
    if not study.isidentifier():
        raise HTTPException(404)
    return J(study_contract.load_study(study))


app.mount("/static", StaticFiles(directory=APP / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(APP / "static" / "index.html", headers={"Cache-Control": "no-cache"})
