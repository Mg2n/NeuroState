"""One-time fetch of the two public inputs the demo needs, with verification.

  1. PhysioNet EEGMMIDB v1.0.0 S001/S001R02.edf (eyes-closed baseline, 64 ch, 160 Hz).
  2. The Koenig 2002 four-class template (MICROSTATELAB Templates/Koenig2002.set), converted to
     NeuroState-Microstates/templates/Koenig2002_4class.json, which is where
     experiments/validate_microstates.py and edf_pipeline_check.py read it from.

Order of attempts (each step is logged to stdout; nothing is retried silently):
  * NeuroState-Microstates' own tool, unmodified:
      tools/fetch_public_inputs.py --step physionet --physionet-subject S001 --step microstatelab-api
      tools/convert_templates.py
  * if the GitHub REST API is unreachable (the API step fails), the template SET file is taken from a
    sparse `git clone` of the same repository and commit, its git blob SHA-1 is checked against the
    commit tree, and its SHA-256 against NeuroState-Microstates/docs/data_checksums.csv. The JSON is then
    written with the same NeuroState-Microstates functions convert_templates.py uses (read_set_template,
    second reader, JSON round-trip check), with the retrieval method recorded truthfully.
  * the sample's SHA-256 is always checked against PhysioNet's SHA256SUMS.txt.

The verified sample is copied to app/cache/sample/S001R02.edf (gitignored), and the demo bundle is built from it
(app/tools/build_demo.py -> app/cache/demo/). After this has run once, the app needs no internet access.

  experiments/.venv/bin/python app/tools/fetch_public_inputs.py
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NS = REPO / "NeuroState-Microstates"
CACHE = REPO / "app" / "cache"
SAMPLE_REL = "S001/S001R02.edf"
NS_SAMPLE = NS / "data" / "raw" / "physionet_eegmmidb_1.0.0" / SAMPLE_REL
NS_SUMS = NS / "data" / "raw" / "physionet_eegmmidb_1.0.0" / "SHA256SUMS.txt"
SAMPLE = CACHE / "sample" / "S001R02.edf"
TEMPLATE_JSON = NS / "templates" / "Koenig2002_4class.json"
MSL_URL = "https://github.com/ThomasKoenigBern/microstates.git"
MSL_COMMIT = "3e142e326078fb189848d97def048d91704e5419"  # the commit NeuroState-Microstates records


def say(**kw):
    print(json.dumps(kw), flush=True)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def physionet_sum(rel: str) -> str | None:
    if not NS_SUMS.exists():
        return None
    for line in NS_SUMS.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == rel:
            return parts[0]
    return None


def ns_tool(*args: str) -> int:
    cmd = [sys.executable, str(NS / "tools" / args[0]), *args[1:]]
    say(step="run", cmd=" ".join(cmd[1:]))
    return subprocess.call(cmd, cwd=NS)


def fetch_sample() -> None:
    if SAMPLE.exists() and physionet_sum(SAMPLE_REL) == sha256(SAMPLE):
        say(step="sample", status="cached", path=str(SAMPLE.relative_to(REPO)), sha256=sha256(SAMPLE))
        return
    if not (NS_SAMPLE.exists() and NS_SUMS.exists()):
        ns_tool("fetch_public_inputs.py", "--step", "physionet", "--physionet-subject", "S001")
    if not NS_SAMPLE.exists():
        raise SystemExit("S001R02.edf could not be downloaded from physionet.org (see the log above).")
    exp, got = physionet_sum(SAMPLE_REL), sha256(NS_SAMPLE)
    if exp is None or exp != got:
        raise SystemExit(f"S001R02.edf SHA-256 {got} does not match PhysioNet's SHA256SUMS.txt ({exp}).")
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(NS_SAMPLE, SAMPLE)
    say(step="sample", status="ok", physionet_sha256=exp, sha256=got, path=str(SAMPLE.relative_to(REPO)))


def ns_checksum(rel: str) -> str | None:
    with (NS / "docs" / "data_checksums.csv").open() as f:
        for row in csv.DictReader(f):
            if row["file"] == rel:
                return row["sha256"]
    return None


def convert_from_git() -> None:
    """Fallback when api.github.com is unreachable: sparse git clone of the recorded commit."""
    sys.path.insert(0, str(NS))
    from neurostate.templates import (read_set_template, template_positions, to_json,
                                      verify_json_against_set, verify_with_pymatreader)
    spec = importlib.util.spec_from_file_location("ns_convert_templates", NS / "tools" / "convert_templates.py")
    ct = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ct)  # constants only (JOBS, VERIFIED_CITATIONS); main() is not called

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "msl"
        for cmd in (["git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1", MSL_URL, str(d)],
                    ["git", "-C", str(d), "sparse-checkout", "set", "Templates"],
                    ["git", "-C", str(d), "checkout"]):
            subprocess.run(cmd, check=True, capture_output=True)
        head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], check=True, capture_output=True,
                              text=True).stdout.strip()
        if head != MSL_COMMIT:
            raise SystemExit(f"MICROSTATELAB main is now {head}, not the recorded commit {MSL_COMMIT}; "
                             "refusing to use an unverified template.")
        date = subprocess.run(["git", "-C", str(d), "log", "-1", "--format=%cI"], check=True,
                              capture_output=True, text=True).stdout.strip()
        rel = "Templates/Koenig2002.set"
        blob = subprocess.run(["git", "-C", str(d), "rev-parse", f"HEAD:{rel}"], check=True,
                              capture_output=True, text=True).stdout.strip()
        src = d / rel
        data = src.read_bytes()
        expected = ns_checksum("microstatelab/files_3e142e3260/Templates/Koenig2002.set")
        ok_sha1, got = git_blob_sha1(data) == blob, sha256(src)
        say(step="template-git", commit=head, git_blob_sha1=blob, git_sha1_match=ok_sha1, sha256=got,
            sha256_matches_neurostate_checksums=(got == expected))
        if not ok_sha1 or got != expected:
            raise SystemExit("Koenig2002.set failed verification; not converted.")
        fname, k, role = next(j for j in ct.JOBS if j[0] == "Koenig2002.set")
        ts = read_set_template(src, k)
        ts.positions_head_m = template_positions(ts)
        prov = {
            "repository": "https://github.com/ThomasKoenigBern/microstates", "commit": head,
            "commit_date": date, "path_in_repository": rel, "git_blob_sha1": blob,
            "retrieval_method": "sparse git clone over HTTPS (GitHub REST API unreachable from this machine); "
                                "git blob SHA-1 recomputed locally; SHA-256 checked against "
                                "NeuroState-Microstates docs/data_checksums.csv",
            "git_sha1_verified": ok_sha1, "set_sha256": ts.source_sha256, "role_in_neurostate": role,
            "license": "No LICENSE file in the repository at this commit and GitHub reports license=null: "
                       "redistribution permission NOT established. Do not publish these maps.",
            "verified_citation": ct.VERIFIED_CITATIONS.get("Koenig2002"),
            "converted_by": "app/tools/fetch_public_inputs.py using neurostate.templates (unmodified)",
        }
        pym = verify_with_pymatreader(ts)
        out = to_json(ts, prov)
        out["second_reader_check"] = pym
        TEMPLATE_JSON.parent.mkdir(exist_ok=True)
        TEMPLATE_JSON.write_text(json.dumps(out, indent=1), encoding="utf-8")
        ver = verify_json_against_set(TEMPLATE_JSON, src, k)
        say(step="template-convert", json=str(TEMPLATE_JSON.relative_to(REPO)), second_reader=pym,
            json_roundtrip=ver)
        if not (pym["maps_identical"] and pym["channel_order_identical"] and all(ver.values())):
            TEMPLATE_JSON.unlink()
            raise SystemExit("template conversion checks failed")


def fetch_template() -> None:
    if TEMPLATE_JSON.exists():
        say(step="template", status="cached", path=str(TEMPLATE_JSON.relative_to(REPO)))
        return
    ns_tool("fetch_public_inputs.py", "--step", "microstatelab-api")
    if list((NS / "data" / "raw" / "microstatelab").glob("files_*/Templates/Koenig2002.set")):
        ns_tool("convert_templates.py")
    if not TEMPLATE_JSON.exists():
        say(step="template", status="NeuroState-Microstates API fetch unavailable; using git fallback")
        convert_from_git()


def main() -> int:
    if not (NS / "neurostate").is_dir():
        raise SystemExit(f"Clone NeuroState-Microstates (unmodified) into {NS} first; see app/README.md.")
    fetch_sample()
    fetch_template()
    if not (CACHE / "demo" / "bundle.json").exists():
        say(step="demo-bundle", status="building (app/tools/build_demo.py)")
        subprocess.check_call([sys.executable, str(REPO / "app" / "tools" / "build_demo.py")])
    else:
        say(step="demo-bundle", status="cached", path="app/cache/demo")
    say(step="done", sample=str(SAMPLE.relative_to(REPO)), template=str(TEMPLATE_JSON.relative_to(REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
