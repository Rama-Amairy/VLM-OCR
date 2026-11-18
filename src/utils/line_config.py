import json
from pathlib import Path

LINES_DIR = Path("experiments/configs")


def available_lines() -> list[str]:
    return sorted(p.stem for p in LINES_DIR.glob("*.json") if "params" in json.loads(p.read_text()))


def load_line_params(name: str) -> dict:
    """Return the OCR params of a line config, e.g. "line1" or "line2_best"."""
    if name not in available_lines():
        raise ValueError(f"unknown line {name!r}, available: {', '.join(available_lines())}")
    return json.loads((LINES_DIR / f"{name}.json").read_text())["params"]
