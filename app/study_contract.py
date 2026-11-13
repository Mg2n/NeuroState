"""Results contract for a study page (app/study_results/<study>/results.json).

The epilepsy page reads this file at load time. No file, or an invalid file, means the pending state; an invalid
file also logs the validation error for developers. The JSON Schema in app/study_results/schema.json is generated
from these models (python -m app.tools.write_schema) and checked by the tests.

No patient identifiers: every model forbids extra fields, so the file can only hold counts and metrics.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SCHEMA_VERSION = "1.0"
STUDY_DIR = Path(os.environ.get("NEUROSTATE_STUDY_DIR") or Path(__file__).resolve().parent / "study_results")
log = logging.getLogger("neurostate.study")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Cohort(_Strict):
    recordings_ingested: int = Field(ge=0)
    recordings_processed: int = Field(ge=0)
    unique_patients_training: Optional[int] = Field(default=None, ge=0)
    unique_patients_test: Optional[int] = Field(default=None, ge=0)
    eligible_patients_available: Optional[int] = Field(default=None, ge=0,
                                                       description="eligible patients not yet in the cohort")


class TrainRun(_Strict):
    run_id: str
    created: str
    model: str
    input: str = Field(description='e.g. "one-hot 4×512"')
    n_train_patients: int = Field(ge=0)
    train_metrics: dict[str, Union[float, int]] = Field(
        default_factory=dict, description="values logged during training (training data only, never held-out)")
    source_path: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Comparator(_Strict):
    name: str
    value: float
    sd: Optional[float] = None


class Evaluation(_Strict):
    split_description: str
    n_test_patients: int = Field(ge=1)
    metric: str = Field(description="e.g. balanced_accuracy")
    value: float
    sd: Optional[float] = None
    ci95: Optional[tuple[float, float]] = None
    n_folds: Optional[int] = Field(default=None, ge=1)
    p_value_vs_first_comparator: Optional[float] = Field(default=None, ge=0, le=1)
    comparators: list[Comparator] = Field(default_factory=list)

    @model_validator(mode="after")
    def _uncertainty(self):
        if self.sd is None and self.ci95 is None and self.n_folds is None:
            raise ValueError("evaluation needs an uncertainty: sd, ci95 or n_folds")
        return self


class CurvePoint(_Strict):
    train_patients: int = Field(ge=1)
    metric: str
    mean: float
    sd: Optional[float] = None
    n_draws: int = Field(ge=1)
    model: Optional[str] = None
    evaluation_protocol: Optional[str] = Field(
        default=None, description="points are drawn together only when model, metric and protocol agree")


class StudyResults(_Strict):
    schema_version: Literal["1.0"]
    study_id: str
    generated_at: str
    status: Literal["pending", "training", "trained", "evaluated"]
    labels: list[str] = Field(min_length=2)
    cohort: Optional[Cohort] = None
    runs: list[TrainRun] = Field(default_factory=list)
    evaluation: Optional[Evaluation] = None
    learning_curve: list[CurvePoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self):
        if self.evaluation is not None and self.status != "evaluated":
            raise ValueError("an evaluation block requires status 'evaluated'")
        if self.status == "evaluated" and self.evaluation is None:
            raise ValueError("status 'evaluated' requires an evaluation block")
        if self.status in ("trained", "evaluated") and not self.runs:
            raise ValueError(f"status '{self.status}' requires at least one entry in runs")
        return self


def curve_groups(points: list[CurvePoint]) -> list[dict]:
    """Groups that may be drawn: same model, metric and protocol, at least two distinct training sizes."""
    groups: dict[tuple, list[CurvePoint]] = {}
    for p in points:
        groups.setdefault((p.model, p.metric, p.evaluation_protocol), []).append(p)
    out = []
    for (model, metric, proto), pts in groups.items():
        if len({p.train_patients for p in pts}) >= 2:
            out.append({"model": model, "metric": metric, "evaluation_protocol": proto,
                        "points": [p.model_dump() for p in sorted(pts, key=lambda p: p.train_patients)]})
    return out


def load_study(study: str, base: Path = STUDY_DIR) -> dict:
    """What the page needs: {'state': 'pending'|'results', 'results': ..., 'curve_groups': ...}."""
    path = base / study / "results.json"
    if not path.exists():
        return {"state": "pending", "reason": "no results file", "path": str(path)}
    try:
        res = StudyResults.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (ValidationError, json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error("invalid study results file %s: %s", path, e)
        return {"state": "pending", "reason": "invalid results file (see server log)", "path": str(path)}
    if res.study_id != study:
        log.error("study results file %s has study_id %r, expected %r", path, res.study_id, study)
        return {"state": "pending", "reason": "results file is for another study (see server log)", "path": str(path)}
    return {"state": "results", "results": res.model_dump(), "curve_groups": curve_groups(res.learning_curve)}


def json_schema() -> dict:
    s = StudyResults.model_json_schema()
    s["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    s["$id"] = "neurostate/study_results/schema.json"
    s["title"] = "NeuroState study results"
    return s
