import logging
import sys
import time
from pathlib import Path

from src.config import get_settings
from src.services import OllamaClient


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

    if len(sys.argv) < 2:
        sys.exit("usage: python -m tests.test_ocr <image_path>")

    ollama = OllamaClient(get_settings())

    if not ollama.check_model():
        sys.exit(1)

    image = Path(sys.argv[1]).read_bytes()

    start = time.perf_counter()
    text = ollama.ocr_image(image)
    print(text)
    print(f"\n--- {time.perf_counter() - start:.1f}s ---")


if __name__ == "__main__":
    main()
