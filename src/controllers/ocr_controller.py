import logging
import time
import uuid

from src.config import Settings
from src.controllers.file_controller import FileController
from src.schemas.ocr_schema import OCRResponse, PageResult
from src.services.ocr_model import OllamaClient
from src.utils.markdown_cleaner import clean_markdown

logger = logging.getLogger(__name__)


class OCRController:
    def __init__(self, settings: Settings, file_controller: FileController, ocr_model: OllamaClient):
        self.file_controller = file_controller
        self.ocr_model = ocr_model
        self.output_dir = settings.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process(self, data: bytes, filename: str) -> OCRResponse:
        start = time.perf_counter()
        job_id = uuid.uuid4().hex[:12]

        images = self.file_controller.to_images(data)
        logger.info("job %s: %s, %d page(s)", job_id, filename, len(images))

        pages = []
        for i, image in enumerate(images, start=1):
            page_start = time.perf_counter()
            text = clean_markdown(self.ocr_model.ocr_image(image))
            pages.append(PageResult(page=i, text=text))
            logger.info("job %s: page %d done in %.1fs", job_id, i, time.perf_counter() - page_start)

        markdown = "\n\n---\n\n".join(p.text for p in pages)
        (self.output_dir / f"{job_id}.md").write_text(markdown, encoding="utf-8")

        duration = round(time.perf_counter() - start, 2)
        logger.info("job %s: finished in %.1fs", job_id, duration)

        return OCRResponse(
            id=job_id,
            filename=filename,
            page_count=len(pages),
            markdown=markdown,
            pages=pages,
            duration_seconds=duration,
        )