"""Детерминированные проверки карточек. Проверка смысла и отрицаний (LLM) добавляется отдельно."""
import hashlib
import re
import unicodedata

NUM = re.compile(r"\d+(?:[.,]\d+)?")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).replace("\u00ad", "")
    s = re.sub(r"-\s*\n\s*", "", s)  # перенос слова на границе строк
    s = re.sub(r"[\u2010-\u2015\u2212]", "-", s)
    return re.sub(r"\s+", " ", s).casefold().strip()


def quote_on_page(quote: str, page_text: str) -> bool:
    return bool(quote.strip()) and norm(quote) in norm(page_text)


def numbers_missing(statement: str, quote: str) -> list[str]:
    in_quote = {n.replace(",", ".") for n in NUM.findall(quote)}
    return [n for n in NUM.findall(statement) if n.replace(",", ".") not in in_quote]


def content_hash(document_id: int, page_number: int, quote: str) -> str:
    return hashlib.sha256(f"{document_id}|{page_number}|{norm(quote)}".encode()).hexdigest()
