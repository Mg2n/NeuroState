"""Build the interactive demo's bundle once: run the real pipeline on the public sample and save every output.

  experiments/.venv/bin/python app/tools/build_demo.py

Input: app/cache/sample/S001R02.edf (PhysioNet EEGMMIDB v1.0.0, eyes-closed baseline; fetched and SHA-256-checked by
app/tools/fetch_public_inputs.py). Output: app/cache/demo/ (gitignored): arrays.npz, bundle.json and the PNG scalp
maps. The demo page then reads only this bundle, so every view shows the same outputs of the same run.
The bundle stays out of git: it holds EEG signal values, and the Koenig 2002 template maps, whose source repository
grants no redistribution licence.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from app import pipeline_adapter as pa  # noqa: E402

SAMPLE = REPO / "app" / "cache" / "sample" / "S001R02.edf"
OUT = REPO / "app" / "cache" / "demo"


def main() -> int:
    if not SAMPLE.exists():
        raise SystemExit("Run app/tools/fetch_public_inputs.py first (it fetches and verifies S001R02.edf).")
    run = pa.run_pipeline(str(SAMPLE), source="sample", file_name="S001R02.edf (PhysioNet EEGMMIDB, public)",
                          emit=lambda s, r: print(f"  {s}: done", flush=True))
    run.run_id = "demo"
    meta = pa.save_bundle(run, OUT)
    ex = meta["example_i"]
    print(json.dumps({"bundle": str(OUT.relative_to(REPO)), "samples": run.summary["n"],
                      "example_moment": {"sample": ex, "time_s": run.summary["t0"] + ex / run.summary["fs"],
                                         "sentence": pa.instant(run, ex)["sentence"]}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
