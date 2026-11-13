"""Launch: experiments/.venv/bin/python -m app [--port 8765] [--no-browser]   (or app/run.sh)"""
import argparse
import logging
import threading
import webbrowser

import uvicorn


def main():
    ap = argparse.ArgumentParser(prog="python -m app")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from app.server import SAMPLE
    from app.pipeline_adapter import TEMPLATE_PATH
    if not (SAMPLE.exists() and TEMPLATE_PATH.exists()):
        print("Sample or Koenig template not cached yet: run  experiments/.venv/bin/python app/tools/fetch_public_inputs.py")
    url = f"http://{a.host}:{a.port}/"
    print(f"NeuroState interface: {url}  (research use only; press Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("app.server:app", host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
