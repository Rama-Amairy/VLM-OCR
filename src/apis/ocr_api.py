import logging
from typing import Annotated

from fastapi import APIRouter, Request, UploadFile,Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
import httpx

from src.config import Settings , get_settings
from src.controllers import OCRController
from src.schemas import OCRResponse
from src.services import OllamaClient
from src. dependencies import get_ocr_model, get_ocr_controller, get_file_controller
from src.exceptions import ModelUnavailableError,OCRModelError, FileValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ocr"])
settings= get_settings()
@router.get("/health")
def health(ocr_model: Annotated[OllamaClient, Depends(get_ocr_model)]):
    return {"status": "ok" if ocr_model.check_model() else "model_unavailable"}

@router.post("/ocr", response_model=OCRResponse)
async def ocr(
    file: UploadFile,
    controller: Annotated[OCRController, Depends(get_ocr_controller)],
):
    try:
        data = await file.read(settings.max_file_size_bytes + 1)
        logger.info("received %s (%d bytes)", file.filename, len(data))
        return await run_in_threadpool(
            controller.process,
            data,
            file.filename or "upload" ,
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "status": "error",
                "message": "OCR processing timed out. Please try again.",
            },
        )
    finally:
        await file.close()