from functools import lru_cache

from src.config import get_settings
from src.controllers.file_controller import FileController
from src.controllers.ocr_controller import OCRController
from src.services.ocr_model import OllamaClient


@lru_cache
def get_ocr_model() -> OllamaClient:
    return OllamaClient(get_settings())


@lru_cache
def get_file_controller() -> FileController:
    return FileController(get_settings())


@lru_cache
def get_ocr_controller() -> OCRController:
    return OCRController(get_settings(), get_file_controller(), get_ocr_model())