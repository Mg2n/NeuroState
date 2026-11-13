import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

SAMPLE = APP / "cache" / "sample" / "S001R02.edf"
TEMPLATE = REPO / "NeuroState-Microstates" / "templates" / "Koenig2002_4class.json"
DEMO = APP / "cache" / "demo"

needs_inputs = pytest.mark.skipif(not (SAMPLE.exists() and TEMPLATE.exists()),
                                  reason="run app/tools/fetch_public_inputs.py first")


@pytest.fixture(scope="session")
def pa():
    from app import pipeline_adapter
    return pipeline_adapter


@pytest.fixture(scope="session")
def sample_run(pa):
    if not (SAMPLE.exists() and TEMPLATE.exists()):
        pytest.skip("run app/tools/fetch_public_inputs.py first")
    return pa.run_pipeline(str(SAMPLE), source="sample")
