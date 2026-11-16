import fitz  # PyMuPDF
from typing import cast

MIN_CHARS = 200  # меньше - считаем, что текстового слоя нет (скан)


def extract_pages(path: str) -> list[str]:
    with fitz.open(path) as doc:
        return [cast(str, page.get_text("text")) for page in doc]


def has_text_layer(pages: list[str]) -> bool:
    return sum(len(t.strip()) for t in pages) >= MIN_CHARS
