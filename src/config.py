from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict 
class Settings(BaseSettings):
    model_config= SettingsConfigDict(env_file=".env", extra="ignore")
    log_dir : str = "logs"

    ollama_url:str= "http://localhost:11434"
    ollama_model: str = "glm-ocr"
    ollama_timeout: int =300
    ollama_temperature: float = 0.0
    num_gpu: int = 0
    ocr_prompt:str="Text Recognition:"

    max_file_size_mb: int =20
    max_pages: int =12
    pdf_dpi: int =150
    max_image_side: int =1280
    output_dir: Path = Path("storage/outputs")
    allowed_types: tuple[str, ...] = ("application/pdf", "image/png", "image/jpeg")

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()