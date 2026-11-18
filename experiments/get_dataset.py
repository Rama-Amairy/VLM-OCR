"""Download 20 English text pages from OmniDocBench: page images + reference text.

The experiments run on images only. The API itself accepts PDF and images.

Output (dataset/ is git-ignored):
    dataset/uploads/train/page_001.png ...
    dataset/uploads/test/page_015.jpg ...
    dataset/ground_truth/page_001.txt     reference text in reading order
    dataset/ground_truth/page_001.json    {"titles": [...]}  main headings of the page
    dataset/sources.csv                   page name -> original image name

usage: python -m experiments.get_dataset
"""

import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://huggingface.co/datasets/opendatalab/OmniDocBench/resolve/main"
OUT = Path("dataset")
N_PAGES = 20
N_TEST = 6

# blocks that count as page text (headers, footers and page numbers are left out)
TEXT_BLOCKS = {"title", "text_block", "figure_caption", "page_footnote", "reference"}
# pages with any of these are skipped, to keep the test about plain text
SKIP_BLOCKS = {"table", "equation_isolated", "equation_semantic", "code_txt", "list_group",
               "text_mask", "chart_mask", "table_mask", "unknown_mask", "need_mask",
               "organic_chemical_formula_mask", "algorithm_mask"}


def get(url: str) -> bytes:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vlm-ocr"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:
            time.sleep(3 * (attempt + 1))  # connection dropped, try again
    raise RuntimeError(f"could not download {url}")


def page_blocks(page: dict) -> list[dict]:
    """The text blocks of a page, in reading order."""
    blocks = [b for b in page["layout_dets"] if b["category_type"] in TEXT_BLOCKS and not b.get("ignore")]
    blocks.sort(key=lambda b: (b.get("order") is None, b.get("order") or 0))  # no order -> last
    return blocks


def usable(page: dict) -> bool:
    attrs = page["page_info"]["page_attribute"]
    blocks = page["layout_dets"]
    titles = [b for b in blocks if b["category_type"] == "title" and not b.get("ignore")]
    chinese = re.search(r"[一-鿿]", " ".join(b.get("text", "") for b in page_blocks(page)))
    return (attrs["language"] == "english"
            and attrs["layout"] in ("single_column", "double_column")
            and attrs["data_source"] != "PPT2PDF"
            and not any(b["category_type"] in SKIP_BLOCKS for b in blocks)
            and len(titles) >= 2
            and not chinese)  # some "english" pages still contain Chinese text


def pick(pages: list[dict]) -> list[dict]:
    """Take pages in turns from each document type, so the 20 pages are mixed."""
    groups = {}
    for p in sorted(pages, key=lambda p: p["page_info"]["image_path"]):
        groups.setdefault(p["page_info"]["page_attribute"]["data_source"], []).append(p)
    picked = []
    while len(picked) < N_PAGES and any(groups.values()):
        for group in groups.values():
            if group and len(picked) < N_PAGES:
                picked.append(group.pop(0))
    return picked


def main() -> None:
    OUT.mkdir(exist_ok=True)
    annotations = OUT / "OmniDocBench.json"
    if not annotations.exists():
        print("downloading annotations (42 MB, once)...", flush=True)
        annotations.write_bytes(get(f"{BASE}/OmniDocBench.json"))

    pages = [p for p in json.loads(annotations.read_text(encoding="utf-8")) if usable(p)]
    print(f"{len(pages)} pages match, taking {N_PAGES}", flush=True)

    sources = ["name,image"]
    for i, page in enumerate(pick(pages), start=1):
        image_name = page["page_info"]["image_path"]
        name = f"page_{i:03d}"
        split = "test" if i > N_PAGES - N_TEST else "train"

        blocks = page_blocks(page)
        text = "\n\n".join(b["text"].strip() for b in blocks if b.get("text", "").strip())
        titles = [b["text"].strip() for b in blocks if b["category_type"] == "title" and b.get("text", "").strip()]

        (OUT / "uploads" / split).mkdir(parents=True, exist_ok=True)
        (OUT / "ground_truth").mkdir(exist_ok=True)
        cached = OUT / "images" / image_name  # keeps downloaded originals between runs
        if not cached.exists():
            cached.parent.mkdir(exist_ok=True)
            cached.write_bytes(get(f"{BASE}/images/{urllib.parse.quote(image_name)}"))
        image_file = OUT / "uploads" / split / f"{name}{Path(image_name).suffix}"
        shutil.copyfile(cached, image_file)
        (OUT / "ground_truth" / f"{name}.txt").write_text(text, encoding="utf-8")
        (OUT / "ground_truth" / f"{name}.json").write_text(json.dumps({"titles": titles}, indent=2), encoding="utf-8")
        sources.append(f"{name},{image_name}")
        print(f"{name} ({split}) <- {image_name}, {len(titles)} titles", flush=True)

    (OUT / "sources.csv").write_text("\n".join(sources) + "\n", encoding="utf-8")
    print(f"done: {N_PAGES - N_TEST} train, {N_TEST} test in {OUT}/", flush=True)


if __name__ == "__main__":
    main()
