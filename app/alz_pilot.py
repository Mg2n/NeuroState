"""Read the completed Alzheimer's pilot (results/followup_seqcnn) for its own, separate panel.

Every value is read from the files written by the pilot; nothing is typed in here. Returns None when the folder
is absent, and the page then simply leaves the panel out.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
PILOT = REPO / "results" / "followup_seqcnn"
GROUP_NAMES = {"A": "Alzheimer's disease", "C": "healthy controls"}  # as GROUPS in experiments/validate_microstates.py


def load(path: Path = PILOT) -> dict | None:
    f = path / "results.json"
    if not f.exists():
        return None
    res = json.loads(f.read_text())
    models = res.get("models", {})
    if "seqcnn_onehot" not in models or "logreg" not in models:
        return None
    fm = pd.read_csv(path / "fold_metrics.csv")
    oof = pd.read_csv(path / "oof_predictions.csv")
    seq = oof[oof.model == "seqcnn_onehot"]
    per_subject = seq.drop_duplicates("subject")
    groups = None
    for sub in sorted(path.glob("main_seed*/results.json")):
        groups = json.loads(sub.read_text())["_config"].get("groups")
        break
    counts = {}
    if groups and len(groups) == 2:  # run_experiment.load: class 1 = first group
        counts = {GROUP_NAMES.get(groups[0], groups[0]): int((per_subject.label == 1).sum()),
                  GROUP_NAMES.get(groups[1], groups[1]): int((per_subject.label == 0).sum())}
    primary = next((t for t in res.get("tests", []) if t.get("role") == "PRIMARY"), None)
    curve = {}
    for key, v in (res.get("curve") or {}).items():
        m = re.match(r"(balanced_accuracy)_(\d+)$", key)
        if m:
            curve[int(m.group(2))] = {"seqcnn": v["seqcnn"], "seqcnn_sd": v.get("seqcnn_sd"),
                                      "logreg": v["logreg"], "logreg_sd": v.get("logreg_sd")}
    sizes = sorted(curve)
    return {
        "title": "Alzheimer’s pilot (completed study, ds004504)",
        "dataset": "OpenNeuro ds004504",
        "source": str(path.relative_to(REPO)),
        "created": res.get("created"),
        "n_participants": int(seq.subject.nunique()),
        "group_counts": counts,
        "n_test_folds": int(len(fm[fm.model == "seqcnn_onehot"].groupby(["repeat", "fold"]))),
        "seqcnn": models["seqcnn_onehot"]["balanced_accuracy"],
        "logreg": models["logreg"]["balanced_accuracy"],
        "primary_test": None if primary is None else {
            "metric": primary["metric"], "diff_mean": primary["diff_mean"], "p": primary["corrected_p"],
            "test": "Nadeau–Bengio corrected resampled t-test, paired over folds"},
        "seqcnn_wins_primary": res.get("seqcnn_wins_primary"),
        "curve": [{"train_subjects": s, **curve[s]} for s in sizes],
    }
