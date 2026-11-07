"""sha256 of every file under data/external/ (follows the ds004504 symlink), plus the
published checksum where the source provides one.

Writes data/checksums_sha256.tsv: path, bytes, sha256, published_algo, published_value, match.
Published values: OpenNeuro git-annex keys (data/checks/openneuro_*.tsv), figshare/OSF/Zenodo/Dryad
values recorded below from the repositories' APIs during Phase 1.
"""
import hashlib
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import cohorts  # noqa: E402

PUBLISHED = {  # path relative to data/external -> (algo, value, source)
    "hk_czech/download/dataset.zip": ("md5", "3ebb58a06078679379c871edb2b387fc", "figshare API"),
    "apava_spain/download/AD_Data.tar.gz": ("sha256", "125b85ae83c5258a25cb46935069fe6c7aa3aea9482c54c3710a9c3ed17d0812", "OSF API"),
    "fsu_duke/download/EEG_data.zip": ("sha256", "f5b30df4fd0d18e3224dde0bd564e2a5cea61845ae5a9b8142ae722c5d99ba93", "OSF API"),
    "adsz_fsu/download/dataset.zip": ("md5", "61d6cfb2f6a31802fde5229bb5cf86d5", "figshare API"),
    "padic_israel/download/alz_c1_new.mat": ("sha256", "0c2fcee914d52d614596a721e385e8218017074eff9fae8a17676ba95e51576d", "Dryad API"),
    "padic_israel/download/controls_c1_new.mat": ("sha256", "3272bb5be59f40225832d48046b85c9f79cbf343bb4328e0cf4f2d70244f5955", "Dryad API"),
    "padic_israel/download/mci_c1_new.mat": ("sha256", "6366147687ff766b8510dd541a04dfc2dd3ad26c7a7e3b51c05bdd581a5a5c18", "Dryad API"),
    "padic_israel/download/AUTHOR_DATASET_SHOR_BENNINGER.txt": ("sha256", "808b9cc79fb87df13d7fc0249b56e882edcc637de83cc1054ca055e027f64ee3", "Dryad API"),
}


def digest(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    chk = os.path.join(cohorts.ROOT, "data", "checks")
    for cid in ("ds004504", "ds006036", "ds005048"):
        p = os.path.join(chk, f"openneuro_{cid}.tsv")
        if os.path.exists(p):
            for r in pd.read_csv(p, sep="\t").itertuples():
                if r.check == "annex-sha256":
                    PUBLISHED[f"{cid}/{r.path}"] = ("sha256", r.expected, "OpenNeuro git-annex key")
                else:
                    PUBLISHED[f"{cid}/{r.path}"] = ("git-blob", r.expected, f"OpenNeuro git tree (verified: {r.status})")
    rows = []
    for root, dirs, files in os.walk(cohorts.EXT, followlinks=True):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "_leftovers")
        for fn in sorted(files):
            if fn.startswith("."):
                continue
            p = os.path.join(root, fn)
            relp = os.path.relpath(p, cohorts.EXT)
            s = digest(p, "sha256")
            algo, val, src = PUBLISHED.get(relp, ("", "", ""))
            if algo == "sha256":
                match = s == val
            elif algo == "md5":
                match = digest(p, "md5") == val
            elif algo == "git-blob":
                match = "verified" in src and "OK" in src
            else:
                match = ""
            rows.append((os.path.join("data", "external", relp), os.path.getsize(p), s, algo, val, src, match))
    df = pd.DataFrame(rows, columns=["path", "bytes", "sha256", "published_algo", "published_value", "published_source", "match"])
    out = os.path.join(cohorts.ROOT, "data", "checksums_sha256.tsv")
    df.to_csv(out, sep="\t", index=False)
    pub = df[df.published_algo != ""]
    print(len(df), "files;", len(pub), "with a published checksum;", int((pub.match == True).sum()), "match;",  # noqa: E712
          "mismatches:", pub[pub.match != True].path.tolist()[:10])  # noqa: E712


if __name__ == "__main__":
    main()
