"""Verify a downloaded OpenNeuro snapshot against OpenNeuro's own published hashes.

OpenNeuro mirrors every snapshot as a git-annex repository on GitHub (OpenNeuroDatasets/<id>,
tag = snapshot version). Large files appear there as symlinks whose names are git-annex keys
of the form SHA256E-s<size>--<sha256>.<ext>; small files are stored in git directly. So:
  * annexed file  -> compare local size and sha256 with the key
  * git file      -> compare the local git blob hash (git hash-object) with the tree entry

Usage: python verify_openneuro.py <local_snapshot_dir> <shallow_clone_of_github_mirror> <out.tsv>
Prints a summary and writes one row per file. Exit code 1 if anything is missing or mismatched.
"""
import hashlib
import os
import re
import subprocess
import sys

KEY = re.compile(r"SHA256E-s(\d+)--([0-9a-f]{64})")


def sha256(path, bufsize=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(bufsize), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob(path):
    return subprocess.run(["git", "hash-object", "--no-filters", path], check=True,
                          capture_output=True, text=True).stdout.strip()


def main(local, clone, out):
    tree = subprocess.run(["git", "-C", clone, "ls-tree", "-r", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.splitlines()
    rows, bad = [], 0
    for line in tree:
        meta, rel = line.split("\t", 1)
        mode, _, blob = meta.split()
        lp = os.path.join(local, rel)
        if mode == "120000":  # annexed: symlink target holds the key
            target = os.readlink(os.path.join(clone, rel))
            m = KEY.search(target)
            if not m:
                status, kind, expect = "NO_KEY", "annex", target
            elif not os.path.exists(lp):
                status, kind, expect = "MISSING", "annex", m.group(2)
            else:
                size_ok = os.path.getsize(lp) == int(m.group(1))
                status = "OK" if size_ok and sha256(lp) == m.group(2) else "MISMATCH"
                kind, expect = "annex-sha256", m.group(2)
        else:
            kind, expect = "git-blob", blob
            if not os.path.exists(lp):
                status = "MISSING"
            else:
                status = "OK" if git_blob(lp) == blob else "MISMATCH"
        bad += status != "OK"
        rows.append((rel, kind, expect, status))
    with open(out, "w") as f:
        f.write("path\tcheck\texpected\tstatus\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    tracked = {r[0] for r in rows}
    extra = []
    for root, _, files in os.walk(local, followlinks=True):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), local)
            if rel not in tracked:
                extra.append(rel)
    counts = {}
    for r in rows:
        counts[(r[1], r[3])] = counts.get((r[1], r[3]), 0) + 1
    print(local, counts, "local files not in snapshot:", len(extra), extra[:5])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
