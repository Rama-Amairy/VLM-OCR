from pydantic import BaseModel


class PageResult(BaseModel):
    page: int
    text: str


class OCRResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    markdown: str
    pages: list[PageResult]
    duration_seconds: float
    