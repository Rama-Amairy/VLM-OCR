import logging
import sys
from pathlib import Path

from src.config import get_settings
from src.controllers.file_controller import FileController
from src.exceptions import FileValidationError


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

    if len(sys.argv) < 2:
        sys.exit("usage: python -m tests.test_files <pdf_or_image_path>")

    controller = FileController(get_settings())
    data = Path(sys.argv[1]).read_bytes()

    try:
        pages = controller.to_images(data)
    except FileValidationError as e:
        print(f"rejected: {e}")
        sys.exit(1)

    out_dir = Path("storage/pages")
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, page in enumerate(pages, start=1):
        (out_dir / f"page_{i}.png").write_bytes(page)

    print(f"saved {len(pages)} page(s) to {out_dir}")


if __name__ == "__main__":
    main()
