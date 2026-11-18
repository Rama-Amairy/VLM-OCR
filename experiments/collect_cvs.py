"""Download 30 English Accountant CVs (PDF + text + fields), split into dev / test.

Source: Hugging Face dataset "md-zain/resume-parser-dataset", folder Accountant,
pinned to a fixed revision so the same 30 CVs come back every time.

Only CVs that pass both checks are kept:
  - name, email and phone are all present in the annotation
  - the PDF has a real text layer (not a scanned image)

Output:
    storage/dataset/uploads/dev/cv_001.pdf ... cv_020.pdf
    storage/dataset/uploads/test/cv_021.pdf ... cv_030.pdf
    storage/dataset/ground_truth/cv_001.txt    reference text
    storage/dataset/ground_truth/cv_001.json   name, email, phone
    storage/dataset/sources.csv                cv id -> dataset resume id

usage: python -m experiments.collect_cvs
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

import pymupdf

DATASET = "md-zain/resume-parser-dataset"
REVISION = "5b9cbddf29c8acba243cc2ec8ff722ca2f54c915"  # fixed dataset version
CATEGORY = "Accountant"
TREE_URL = f"https://huggingface.co/api/datasets/{DATASET}/tree/{REVISION}/raw/{CATEGORY}"
FILE_URL = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}"
OUT = Path("storage/dataset")
N_DEV, N_TEST = 20, 10
MIN_TEXT_CHARS = 200


def get(url: str) -> bytes:
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?=&"), headers={"User-Agent": "vlm-ocr"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def has_text_layer(pdf: bytes) -> bool:
    try:
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            return sum(len(p.get_text().strip()) for p in doc) >= MIN_TEXT_CHARS
    except Exception:
        return False


def main() -> None:
    total = N_DEV + N_TEST
    ids = sorted(Path(f["path"]).stem for f in json.loads(get(TREE_URL)) if f["path"].endswith(".pdf"))
    print(f"{len(ids)} {CATEGORY} CVs in the dataset", flush=True)

    gt_dir = OUT / "ground_truth"
    gt_dir.mkdir(parents=True, exist_ok=True)

    sources = ["id,split,source_id"]
    saved = 0
    for resume_id in ids:
        if saved == total:
            break
        try:
            # 1) fields first (small file): skip CVs with a missing name, email or phone
            target = json.loads(get(f"{FILE_URL}/annotated/{CATEGORY}/{resume_id}.json"))
            info = target.get("personal_information") or {}
            phones = info.get("phone_numbers") or []
            fields = {"name": info.get("full_name"), "email": info.get("email"),
                      "phone": phones[0] if phones else None}
            if not all(fields.values()):
                continue

            # 2) the PDF must have a real text layer (not a scanned image)
            pdf = get(f"{FILE_URL}/raw/{CATEGORY}/{resume_id}.pdf")
            if not has_text_layer(pdf):
                continue

            text = get(f"{FILE_URL}/extracted/{CATEGORY}/{resume_id}.txt").decode("utf-8")
            if len(text.strip()) < MIN_TEXT_CHARS:
                continue
        except Exception as e:
            print(f"skip {resume_id}: {e}", flush=True)
            continue

        saved += 1
        cv_id = f"cv_{saved:03d}"
        split = "dev" if saved <= N_DEV else "test"
        (OUT / "uploads" / split).mkdir(parents=True, exist_ok=True)
        (OUT / "uploads" / split / f"{cv_id}.pdf").write_bytes(pdf)
        (gt_dir / f"{cv_id}.txt").write_text(text, encoding="utf-8")
        (gt_dir / f"{cv_id}.json").write_text(json.dumps(fields, indent=2), encoding="utf-8")
        sources.append(f"{cv_id},{split},{resume_id}")
        print(f"{cv_id} ({split}) <- {resume_id}", flush=True)

    (OUT / "sources.csv").write_text("\n".join(sources) + "\n", encoding="utf-8")
    print(f"saved {saved} CVs to {OUT}", flush=True)


if __name__ == "__main__":
    main()
