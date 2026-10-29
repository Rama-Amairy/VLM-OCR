from typing import Annotated

from fastapi import APIRouter, Request, UploadFile,Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from config import Settings , get_settings
from src.controllers import OCRController
from src.schemas import OCRResponse
from src.services import OllamaClient
from src.exceptions import ModelUnavailableError,OCRModelError, FileValidationError

router = APIRouter(prefix="/api", tags=["ocr"])

@router.get("/health")
def health(ocr_model: Annotated[OllamaClient, Depends(get_ocr_model)]):
    return {"status": "ok" if ocr_model.check_model() else "model_unavailable"}