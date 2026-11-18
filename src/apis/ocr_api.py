import logging
from typing import Annotated

from fastapi import APIRouter, Form, Request, UploadFile,Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
import httpx

from src.config import Settings , get_settings
from src.controllers import OCRController
from src.schemas import OCRResponse
from src.services import OllamaClient
from src. dependencies import get_ocr_model, get_ocr_controller, get_file_controller
from src.exceptions import ModelUnavailableError,OCRModelError, FileValidationError
from src.preprocessing import STEPS, check_steps
from src.utils.history import log_request
from src.utils.line_config import available_lines, load_line_params

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ocr"])
settings= get_settings()
@router.get("/health")
def health(ocr_model: Annotated[OllamaClient, Depends(get_ocr_model)]):
    return {"status": "ok" if ocr_model.check_model() else "model_unavailable"}

@router.get("/lines")
def lines():
    return {"lines": available_lines(), "preprocessing_steps": list(STEPS)}

@router.post("/ocr", response_model=OCRResponse)
async def ocr(
    file: UploadFile,
    controller: Annotated[OCRController, Depends(get_ocr_controller)],
    line: Annotated[str | None, Form()] = None,
    prompt: Annotated[str | None, Form()] = None,
    pdf_dpi: Annotated[int | None, Form(gt=0)] = None,
    max_image_side: Annotated[int | None, Form(gt=0)] = None,
    num_ctx: Annotated[int | None, Form(gt=0)] = None,
    preprocessing: Annotated[str | None, Form(description="comma separated, e.g. deskew,contrast")] = None,
):
    # priority: fields sent in the request > line config > defaults from config / .env
    try:
        params = load_line_params(line) if line else {}
        fields = {"prompt": prompt, "pdf_dpi": pdf_dpi, "max_image_side": max_image_side, "num_ctx": num_ctx}
        params.update({k: v for k, v in fields.items() if v is not None})
        if preprocessing is not None:
            params["preprocessing"] = [s.strip() for s in preprocessing.split(",") if s.strip()]
            check_steps(params["preprocessing"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    try:
        data = await file.read(settings.max_file_size_bytes + 1)
        logger.info("received %s (%d bytes), line %s", file.filename, len(data), line or "default")
        result = await run_in_threadpool(
            controller.process,
            data,
            file.filename or "upload" ,
            params,
        )
        result.params = params
        log_request(settings.output_dir, line, params, result)
        return result
    except FileValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
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