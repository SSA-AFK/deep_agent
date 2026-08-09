"""Load committed, deterministic fixtures used by demo-mode tools."""

import json
from pathlib import Path

from tools.contracts import SourceItem


_DEMO_DIR = Path(__file__).resolve().parents[1] / "data" / "demo"


def load_search_results() -> list[SourceItem]:
    with (_DEMO_DIR / "search_results.json").open(encoding="utf-8") as fixture:
        rows = json.load(fixture)
    return [SourceItem.model_validate(row) for row in rows]
