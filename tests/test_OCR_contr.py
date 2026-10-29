import logging
import sys
from pathlib import Path

from src.config import get_settings
from src.controllers.file_controller import FileController
from src.controllers.ocr_controller import OCRController
from src.exceptions import FileValidationError
from src.services.ocr_model import OllamaClient


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

    if len(sys.argv) < 2:
        sys.exit("usage: python -m tests.test_OCR_contr <pdf_or_image_path>")

    settings = get_settings()
    ollama = OllamaClient(settings)

    if not ollama.check_model():
        sys.exit(1)

    controller = OCRController(settings, FileController(settings), ollama)
    path = Path(sys.argv[1])

    try:
        result = controller.process(path.read_bytes(), path.name)
    except FileValidationError as e:
        print(f"rejected: {e}")
        sys.exit(1)

    print(result.markdown)
    print(f"\n--- {result.page_count} pages, {result.duration_seconds}s, saved as {result.id}.md ---")


if __name__ == "__main__":
    main()
