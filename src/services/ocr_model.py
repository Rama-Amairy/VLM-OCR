"""

"""

import logging
from ollama import Client, ResponseError
from src.config import Settings

logger= logging.getLogger(__name__)

class OllamaClient:
    def __init__(self,settings: Settings):
        self.model = settings.ollama_model
        self.temperature = settings.ollama_temperature
        self.num_gpu = settings.num_gpu
        self.default_prompt = settings.ocr_prompt
        self.url = settings.ollama_url
        self.client = Client(host=settings.ollama_url, timeout=settings.ollama_timeout)

    def check_model(self) -> bool:
        try:
            models = [m.model for m in self.client.list().models]
        except Exception as e:
            logger.error("cannot reach ollama at %s: %s", self.url, e)
            return False

        if not any(m == self.model or m.split(":")[0] == self.model for m in models):
            logger.error("model %r not found, run: ollama pull %s", self.model, self.model)
            return False

        return True

    def ocr_image(self, image_bytes: bytes, prompt: str | None = None) -> str:
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": prompt or self.default_prompt,
                    "images": [image_bytes],
                }],
                options={"temperature": self.temperature, "num_gpu":self.num_gpu},
            )
        except ResponseError as e:
            logger.error("ollama error: %s", e.error)
            raise

        return response.message.content
