"""Write app/study_results/schema.json from the Pydantic models:  experiments/.venv/bin/python -m app.tools.write_schema"""
import json
from pathlib import Path

from app.study_contract import json_schema

OUT = Path(__file__).resolve().parents[1] / "study_results" / "schema.json"

if __name__ == "__main__":
    OUT.write_text(json.dumps(json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
