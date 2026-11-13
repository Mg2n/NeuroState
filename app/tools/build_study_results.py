"""Convert the repository's training output into the study results contract (app/study_contract.py).

  experiments/.venv/bin/python app/tools/build_study_results.py --run <results_dir> --study epilepsy \
      --out app/study_results/epilepsy/results.json --labels epilepsy "no epilepsy"

Reads either format the repository writes:
  * run_experiment.py:  results.json (one key per model, _config), fold_metrics.csv, oof_predictions.csv,
                        val_predictions.csv, log.txt
  * a follow-up summary such as results/followup_seqcnn: results.json with "models", "tests", "curve";
                        fold_metrics.csv, oof_predictions.csv, curve/ (results.json with _config), and the
                        run_experiment.py sub-runs in its sub-folders (main_seed0, ...)

Every number written comes from those files. Subject identifiers are read only to count patients; none is written.
Held-out values (evaluation) come only from the test folds in fold_metrics.csv / oof_predictions.csv. Values from
the training side (epochs, inner early-stopping validation patients) go to runs[].train_metrics.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
sys.path.insert(0, str(REPO))
from app.study_contract import SCHEMA_VERSION, StudyResults  # noqa: E402

PRETTY = {"seqcnn": "Sequence CNN (MicroStateNet, microstate input only)",
          "seqcnn_onehot": "Sequence CNN, one-hot labels",
          "seqcnn_onehot_smoothed": "Sequence CNN, one-hot smoothed labels",
          "seqcnn_corr": "Sequence CNN on |correlation|",
          "logreg": "Logistic regression on the 24 microstate measures",
          "baseline_logreg": "Logistic regression on the 24 microstate measures",
          "logreg_smoothed": "Logistic regression, smoothed labels",
          "random_forest": "Random forest on the 24 measures", "baseline_rf": "Random forest on the 24 measures",
          "random_forest_smoothed": "Random forest, smoothed labels",
          "eegnet": "EEGNet (waveform model)", "eegnet_ens5": "EEGNet ensemble (waveform model)",
          "hybrid": "Hybrid EEGNet + microstate CNN"}
FS = 128.0  # prep.SFREQ: run_experiment.py reads prepared data at this rate


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def is_run_experiment(res: dict) -> bool:
    return "_config" in res and "models" not in res


def epochs_from_log(run: Path, model: str) -> list[int]:
    log = run / "log.txt"
    if not log.exists():
        return []
    pat = re.compile(rf"^\S+\s+{re.escape(model)}: trained (\d+) epochs")
    return [int(m.group(1)) for line in log.read_text().splitlines() if (m := pat.match(line.strip()))]


def inner_val_bacc(run: Path, model: str) -> float | None:
    """Balanced accuracy on the inner early-stopping patients (part of each TRAINING fold), threshold 0.5."""
    f = run / "val_predictions.csv"
    if not f.exists():
        return None
    v = pd.read_csv(f)
    v = v[v.model == model]
    if v.empty or "prob" not in v:
        return None
    from sklearn.metrics import balanced_accuracy_score
    scores = [balanced_accuracy_score(g.label, (g.prob >= 0.5).astype(int)) for _, g in v.groupby(["repeat", "fold"])]
    return float(sum(scores) / len(scores))


def created_of(run: Path, res: dict) -> str:
    """results.json 'created' if recorded (file times are not used: a git checkout resets them)."""
    for r in (res, json.loads((run.parent / "results.json").read_text()) if (run.parent / "results.json").exists() else {}):
        if r.get("created"):
            return str(r["created"])
    return "not recorded in results.json"


def train_run(run: Path, res: dict, model: str) -> dict:
    cfg = res["_config"]
    win = int(round(float(cfg.get("win_sec", 4.0)) * FS))
    ms_in = cfg.get("ms_input", "corr")
    inp = {"onehot": f"one-hot 4×{win}", "corr": f"|correlation| 4×{win}", "corr+feats": f"|correlation| 4×{win} + 24 features"}[ms_in]
    if cfg.get("min_segment"):
        inp += f", labels smoothed (min segment {cfg['min_segment']} samples)"
    if model in ("eegnet", "hybrid"):
        inp = f"EEG 19×{win}" + (f" + {inp}" if model == "hybrid" else "")
    oof = pd.read_csv(run / "oof_predictions.csv")
    o = oof[oof.model == model]
    n_all = int(cfg.get("n_subjects", o.subject.nunique()))
    test_sizes = o.groupby(["repeat", "fold"]).subject.nunique()
    n_train = int(round(float((n_all - test_sizes).median()))) if len(test_sizes) else n_all
    tm: dict[str, float | int] = {}
    ep = epochs_from_log(run, model)
    if ep:
        tm["epochs_trained_mean"] = sum(ep) / len(ep)
        tm["n_networks_trained"] = len(ep)
    iv = inner_val_bacc(run, model)
    if iv is not None:
        tm["inner_validation_balanced_accuracy"] = iv
    return {"run_id": run.name, "created": created_of(run, res),
            "model": PRETTY.get(model, model), "input": inp, "n_train_patients": n_train, "train_metrics": tm,
            "source_path": rel(run / "results.json"), "source_sha256": sha256(run / "results.json")}


def evaluation(run: Path, model: str, metric: str, tests: list | None) -> tuple[dict, int]:
    fm = pd.read_csv(run / "fold_metrics.csv")
    oof = pd.read_csv(run / "oof_predictions.csv")
    if model not in set(fm.model):
        raise SystemExit(f"model {model!r} not in fold_metrics.csv; models: {sorted(set(fm.model))}")
    mine = fm[fm.model == model]
    n_folds = int(len(mine.groupby(["repeat", "fold"])))
    reps = sorted(set(mine.repeat))
    k = int(mine.fold.nunique())
    n_test = int(oof[oof.model == model].subject.nunique())
    others = [m for m in fm.model.unique() if m != model]
    first = [m for m in others if "logreg" in m and "smoothed" not in m]
    others = first + [m for m in others if m not in first]
    comps = [{"name": PRETTY.get(m, m), "value": float(fm[fm.model == m][metric].mean()),
              "sd": float(fm[fm.model == m][metric].std())} for m in others]
    p = None
    if tests and first:
        hit = [t for t in tests if t.get("a") == model and t.get("b") == first[0] and t.get("metric") == metric]
        if hit:
            p = float(hit[0].get("corrected_p", hit[0].get("p")))
    ev = {"split_description": f"Patient-level cross-validation: {k} stratified folds × {len(reps)} repeat(s) = "
                               f"{n_folds} test folds. Each patient is entirely in training or entirely in testing "
                               f"in every fold; microstate maps and early stopping use training patients only.",
          "n_test_patients": n_test, "metric": metric, "value": float(mine[metric].mean()),
          "sd": float(mine[metric].std()), "n_folds": n_folds, "comparators": comps}
    if p is not None:
        ev["p_value_vs_first_comparator"] = p
    return ev, n_test


def learning_curve(run: Path, res: dict) -> list[dict]:
    cur = res.get("curve") or {}
    if not cur:
        return []
    cfg = {}
    if (run / "curve" / "results.json").exists():
        cfg = json.loads((run / "curve" / "results.json").read_text()).get("_config", {})
    draws = int(cfg.get("draws", 1))
    sub = set(cfg.get("sizes", []))
    proto = (f"same held-out test folds ({cfg.get('folds', '?')} folds × {cfg.get('repeats', '?')} repeats); "
             "training subsets drawn within each training fold")
    pts = []
    for key, v in cur.items():
        m = re.match(r"(.+)_(\d+)$", key)
        if not m:
            continue
        metric, size = m.group(1), int(m.group(2))
        for model in ("seqcnn", "logreg"):
            if model in v:
                pts.append({"train_patients": size, "metric": metric, "mean": float(v[model]),
                            "sd": float(v.get(f"{model}_sd")) if v.get(f"{model}_sd") is not None else None,
                            "n_draws": draws if size in sub else 1, "model": PRETTY.get(model, model),
                            "evaluation_protocol": proto})
    return pts


def build(run: Path, study: str, labels: list[str] | None, model: str | None, metric: str,
          rec_ingested: int | None, rec_processed: int | None, eligible: int | None) -> dict:
    res = json.loads((run / "results.json").read_text())
    if is_run_experiment(res):
        model = model or ("seqcnn" if "seqcnn" in res else next(k for k in res if not k.startswith("_")))
        groups = res["_config"].get("groups", [])
        runs = [train_run(run, res, model)]
        tests = None
    else:  # follow-up summary with sub-runs
        model = model or ("seqcnn_onehot" if "seqcnn_onehot" in res.get("models", {}) else next(iter(res["models"])))
        runs, groups = [], []
        for sub in sorted(p for p in run.iterdir() if (p / "results.json").exists() and p.name != "curve"):
            sres = json.loads((sub / "results.json").read_text())
            if is_run_experiment(sres) and "seqcnn" in sres and (sub / "oof_predictions.csv").exists():
                runs.append(train_run(sub, sres, "seqcnn"))
                groups = groups or sres["_config"].get("groups", [])
        tests = res.get("tests")
    has_eval = (run / "fold_metrics.csv").exists() and (run / "oof_predictions.csv").exists()
    out = {"schema_version": SCHEMA_VERSION, "study_id": study,
           "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "status": "evaluated" if has_eval else "trained", "labels": labels or groups, "runs": runs}
    n_pat = None
    if has_eval:
        out["evaluation"], n_pat = evaluation(run, model, metric, tests)
    if n_pat is not None or rec_processed is not None:
        proc = rec_processed if rec_processed is not None else n_pat  # run_experiment.load: one recording per patient
        out["cohort"] = {"recordings_ingested": rec_ingested if rec_ingested is not None else proc,
                         "recordings_processed": proc, "unique_patients_training": n_pat,
                         "unique_patients_test": n_pat}
        if eligible is not None:
            out["cohort"]["eligible_patients_available"] = eligible
    lc = learning_curve(run, res)
    if lc:
        out["learning_curve"] = lc
    return StudyResults.model_validate(out).model_dump(exclude_none=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", required=True, type=Path, help="results folder written by run_experiment.py (or a "
                                                             "follow-up summary folder)")
    ap.add_argument("--study", required=True, help="study id, e.g. epilepsy")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--labels", nargs="+", help='class names, positive first, e.g. epilepsy "no epilepsy"')
    ap.add_argument("--model", help="model key to report (default: the sequence CNN)")
    ap.add_argument("--metric", default="balanced_accuracy")
    ap.add_argument("--recordings-ingested", type=int)
    ap.add_argument("--recordings-processed", type=int)
    ap.add_argument("--eligible-available", type=int, help="eligible patients available but not yet in the cohort")
    a = ap.parse_args(argv)
    d = build(a.run, a.study, a.labels, a.model, a.metric, a.recordings_ingested, a.recordings_processed,
              a.eligible_available)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {a.out}: status {d['status']}, {len(d['runs'])} run(s)"
          + (f", held-out {d['evaluation']['metric']} {d['evaluation']['value']:.3f}" if "evaluation" in d else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
