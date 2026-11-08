import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.apis.ocr_api import router as ocr_router
from src.config import get_settings
from src.dependencies import get_ocr_model


settings = get_settings()

Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(settings.log_dir) / "app.log", encoding="utf-8"),
    ],
    force=True,
)

# keep library noise out of the logs
for noisy in ("httpx", "httpcore", "PIL", "multipart"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not get_ocr_model().check_model():
        logger.warning(
            "Model not available at startup, requests will fail until it is"
        )

    logger.info("App started with model %s", settings.ollama_model)

    yield


app = FastAPI(
    title="VLM OCR",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ocr_router)