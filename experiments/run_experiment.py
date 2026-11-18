"""Run an experiment line on every file in the uploads folder.

usage:
    python -m experiments.run_experiment --line line1
    python -m experiments.run_experiment --line line2
    python -m experiments.run_experiment --line line3
    python -m experiments.run_experiment --line line3_best --split test

line1 / line2_best / line3_best : run one config and save the results
line2 : try each factor alone on top of line1, then combine the best
        values into line2_best (saved to experiments/configs/line2_best.json)
line3 : try each preprocessing step alone on top of line2_best, then combine
        the steps that lowered CER into line3_best
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from src.config import get_settings
from src.controllers.file_controller import FileController
from src.controllers.ocr_controller import OCRController
from src.services.ocr_model import OllamaClient
from src.utils.line_config import LINES_DIR, load_line_params

from experiments.metrics import cer, headings_found, wer

FILE_TYPES = (".pdf", ".png", ".jpg", ".jpeg")

logger = logging.getLogger("experiment")


class Runner:
    def __init__(self, uploads: Path, truth: Path, results: Path):
        self.files = sorted(p for p in uploads.rglob("*") if p.suffix.lower() in FILE_TYPES)
        if not self.files:
            raise SystemExit(f"no files found in {uploads}")
        self.truth = truth
        self.results = results
        settings = get_settings()
        self.ocr_model = OllamaClient(settings)
        self.file_controller = FileController(settings)
        self.settings = settings
        self.done = {}  # params already run in this session -> summary

    def warm_up(self):
        logger.info("warm-up (not timed): loading the model")
        self.controller(self.results / "warmup").process(self.files[0].read_bytes(), "warmup")

    def controller(self, out_dir: Path) -> OCRController:
        settings = self.settings.model_copy(update={"output_dir": out_dir})
        return OCRController(settings, self.file_controller, self.ocr_model)

    def run(self, name: str, params: dict) -> dict:
        key = json.dumps(params, sort_keys=True)
        if key in self.done:
            logger.info("%s: same params as %s, reusing result", name, self.done[key]["run"])
            return {**self.done[key], "run": name}

        out_dir = self.results / name
        controller = self.controller(out_dir)
        rows = []
        for path in self.files:
            result = controller.process(path.read_bytes(), path.name, params)
            (out_dir / f"{result.id}.md").rename(out_dir / f"{path.stem}.md")
            rows.append(self.score(path.stem, result.markdown, result.duration_seconds))
            logger.info("%s: %s cer=%.3f %.1fs", name, path.stem, rows[-1]["cer"], result.duration_seconds)

        with open(out_dir / "details.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        summary = summarize(name, params, rows)
        self.done[key] = summary
        logger.info("%s: cer=%.3f wer=%.3f headings=%s time=%.1fs",
                    name, summary["cer"], summary["wer"], summary["headings_found"], summary["total_seconds"])
        return summary

    def score(self, page_id: str, output: str, seconds: float) -> dict:
        # ground_truth/<name>.txt = page text, ground_truth/<name>.json = {"titles": [...]}
        reference = (self.truth / f"{page_id}.txt").read_text(encoding="utf-8")
        titles = json.loads((self.truth / f"{page_id}.json").read_text(encoding="utf-8"))["titles"]
        return {
            "file": page_id,
            "cer": cer(reference, output),
            "wer": wer(reference, output),
            "titles_total": len(titles),
            "titles_found": headings_found(titles, output),
            "seconds": seconds,
        }


def summarize(name: str, params: dict, rows: list[dict]) -> dict:
    titles_total = sum(r["titles_total"] for r in rows)
    return {
        "run": name,
        "params": json.dumps(params),
        "cer": round(sum(r["cer"] for r in rows) / len(rows), 4),
        "wer": round(sum(r["wer"] for r in rows) / len(rows), 4),
        "headings_found": round(sum(r["titles_found"] for r in rows) / titles_total, 4) if titles_total else None,
        "total_seconds": round(sum(r["seconds"] for r in rows), 1),
        "seconds_per_file": round(sum(r["seconds"] for r in rows) / len(rows), 1),
    }


def write_summary(path: Path, summaries: list[dict]):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    logger.info("summary saved to %s", path)


def run_line2(runner: Runner) -> list[dict]:
    config = json.loads((LINES_DIR / "line2.json").read_text())
    base = load_line_params(config["base"])
    summaries = [runner.run("line1", base)]

    # 1) each factor alone, everything else stays as line1
    best = {}
    for factor, values in config["search"].items():
        tried = [summaries[0]]
        for value in values:
            change = value if isinstance(value, dict) else {factor: value}
            params = {**base, **change}
            if params == base:
                continue
            tried.append(runner.run(f"{factor}_{len(tried)}", params))
        summaries += tried[1:]
        winner = min(tried, key=lambda s: s["cer"])
        best.update({k: v for k, v in json.loads(winner["params"]).items() if v != base.get(k)})
        logger.info("best %s: %s", factor, winner["run"])

    # 2) combine the best value of every factor
    combined = runner.run("line2_best", {**base, **best})
    summaries.append(combined)

    # 3) keep the combination only if it beats every single run
    save_best("line2_best", summaries)
    return summaries


def run_line3(runner: Runner) -> list[dict]:
    config = json.loads((LINES_DIR / "line3.json").read_text())
    if not (LINES_DIR / f"{config['base']}.json").exists():
        raise SystemExit(f"{config['base']}.json not found, run line2 first")
    base = load_line_params(config["base"])
    reference = runner.run(config["base"], base)
    summaries = [reference]

    # 1) each preprocessing step alone, on top of line2_best
    helped = []
    for step in config["preprocessing"]:
        summary = runner.run(step, {**base, "preprocessing": [step]})
        summaries.append(summary)
        if summary["cer"] < reference["cer"]:
            helped.append(step)
    logger.info("steps that lowered CER: %s", helped or "none")

    # 2) combine the steps that helped (if only one helped, it is already measured)
    if len(helped) > 1:
        summaries.append(runner.run("line3_best", {**base, "preprocessing": helped}))

    # 3) keep whatever run is best, it can also be line2_best with no preprocessing
    save_best("line3_best", summaries)
    return summaries


def save_best(name: str, summaries: list[dict]):
    winner = min(summaries, key=lambda s: s["cer"])
    if winner["run"] != name:
        logger.info("%s is the best run, using it as %s", winner["run"], name)
    (LINES_DIR / f"{name}.json").write_text(json.dumps({
        "name": name,
        "description": f"best run: {winner['run']}, cer {winner['cer']}",
        "params": json.loads(winner["params"]),
    }, indent=2) + "\n")
    logger.info("saved %s", LINES_DIR / f"{name}.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--line", required=True, help="line1, line2, line3, line2_best or line3_best")
    parser.add_argument("--split", default="train", help="subfolder of uploads (train / test), 'all' for everything")
    parser.add_argument("--uploads", type=Path, default=Path("dataset/uploads"))
    parser.add_argument("--truth", type=Path, default=Path("dataset/ground_truth"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    uploads = args.uploads if args.split == "all" else args.uploads / args.split
    results = Path("experiments/results") / args.line / args.split
    runner = Runner(uploads, args.truth, results)
    runner.warm_up()

    if args.line == "line2":
        summaries = run_line2(runner)
    elif args.line == "line3":
        summaries = run_line3(runner)
    else:
        summaries = [runner.run(args.line, load_line_params(args.line))]
    write_summary(results / "summary.csv", summaries)


if __name__ == "__main__":
    main()
