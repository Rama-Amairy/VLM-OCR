
import logging
import io
import pymupdf as fitz #PyMuPDF for dealing with pdf files
from PIL import Image 
from src.config import Settings
from src.exceptions import FileValidationError

logger = logging.getLogger(__name__)


class FileController:
    def __init__(self, settings: Settings):
        self.max_size = settings.max_file_size_bytes
        self.max_size_mb = settings.max_file_size_mb
        self.max_pages = settings.max_pages
        self.dpi = settings.pdf_dpi
        self.max_side = settings.max_image_side

    def detect_type(self, data: bytes) -> str:
        if data.startswith(b"%PDF"):
            return "pdf"
        if data.startswith(b"\x89PNG"):
            return "png"
        if data.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        raise FileValidationError("unsupported file type, only PDF, PNG and JPEG are allowed")

    def file_validate(self, data: bytes) -> str:
        if not data:
            raise FileValidationError("file is empty")
        if len(data) > self.max_size:
            raise FileValidationError(f"file is larger than {self.max_size_mb} MB")
        return self.detect_type(data)
    def to_images(self, data: bytes) -> list[bytes]:
        file_type = self.file_validate(data)

        if file_type == "pdf":
            pages = self._pdf_to_images(data)
        else:
            pages = [data]

        logger.info("file type %s, %d page(s)", file_type, len(pages))
        return [self._resize(p) for p in pages]

    def _pdf_to_images(self, data: bytes) -> list[bytes]:
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as e:
            raise FileValidationError("cannot open PDF, file may be corrupted") from e

        with doc:
            if doc.needs_pass:
                raise FileValidationError("PDF is password protected")
            if doc.page_count == 0:
                raise FileValidationError("PDF has no pages")
            if doc.page_count > self.max_pages:
                raise FileValidationError(
                    f"PDF has {doc.page_count} pages, maximum is {self.max_pages}"
                )

            return [page.get_pixmap(dpi=self.dpi).tobytes("png") for page in doc]

    def _resize(self, image_bytes: bytes) -> bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()
        except Exception as e:
            raise FileValidationError("cannot read image, file may be corrupted") from e

        if img.mode != "RGB":
            img = img.convert("RGB")

        img.thumbnail((self.max_side, self.max_side))

        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    