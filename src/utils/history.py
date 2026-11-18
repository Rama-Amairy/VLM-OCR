import csv
import json
from datetime import datetime
from pathlib import Path

FIELDS = ["time", "id", "filename", "line", "params", "pages", "seconds"]


def log_request(output_dir: Path, line: str | None, params: dict, result) -> None:
    """Add one row per OCR request to <output_dir>/history.csv, to keep track of what was tried."""
    path = output_dir / "history.csv"
    new_file = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "time": datetime.now().isoformat(timespec="seconds"),
            "id": result.id,
            "filename": result.filename,
            "line": line or "",
            "params": json.dumps(params),
            "pages": result.page_count,
            "seconds": result.duration_seconds,
        })
