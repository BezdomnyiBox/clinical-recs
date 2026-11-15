from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.db import SessionLocal
from app.models import Document, EvidenceCard, Page
from app.pipeline.ingest import extract_pages, has_text_layer
from app.pipeline.verify import numbers_missing, quote_on_page


class State(TypedDict, total=False):
    document_id: int
    job_id: int
    supported: bool


def ingest(state: State):
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        doc.status = "processing"
        texts = extract_pages(doc.stored_path)
        doc.page_count = len(texts)
        # TODO при повторной обработке не удалять страницы и карточки, а сопоставлять по content_hash
        s.query(Page).filter_by(document_id=doc.id).delete()
        s.add_all(Page(document_id=doc.id, number=i, text=t) for i, t in enumerate(texts, 1))
        ok = has_text_layer(texts)
        if not ok:
            doc.status = "unsupported"
            doc.status_detail = "В PDF нет текстового слоя (скан). Такие документы не обрабатываются."
        s.commit()
    return {"supported": ok}


def extract(state: State):
    # TODO: фрагменты (страницы) -> LLM со structured output (схема карточки + дословная цитата).
    # Результат каждого фрагмента сразу писать в БД и обновлять Page.status, чтобы сбой не терял полученное.
    # Вызовы модели логировать через llm.record_usage.
    raise NotImplementedError("Извлечение карточек ещё не реализовано")


def verify(state: State):
    with SessionLocal() as s:
        pages = {p.number: p.text for p in s.query(Page).filter_by(document_id=state["document_id"])}
        for c in s.query(EvidenceCard).filter_by(document_id=state["document_id"]):
            problems = []
            if not quote_on_page(c.quote, pages.get(c.page_number, "")):
                problems.append("цитата не найдена на указанной странице")
            if missing := numbers_missing(c.statement_ru, c.quote):
                problems.append("числа из формулировки нет в цитате: " + ", ".join(missing))
            c.quote_verified = "failed" if problems else "verified"
            c.problems = problems
            # TODO: проверка смысла и отрицаний (отдельный проход LLM) -> c.meaning_verified
        s.commit()
    return {}


def dedupe(state: State):
    # TODO: кандидаты на дубли (эмбеддинги) -> решение по действию, группе, условиям, направлению, числам;
    # источники объединяются, противоречия пишутся в conflicts.
    return {}


def assign_sections(state: State):
    # TODO: карточки -> тезисы по разделам (SECTIONS), УДД/УУР по выданной шкале, критерии качества.
    return {}


def finalize(state: State):
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        failed = s.query(Page).filter_by(document_id=doc.id, status="error").count()
        cards = s.query(EvidenceCard).filter_by(document_id=doc.id).count()
        doc.status = "done_partial" if failed else ("done" if cards else "done_empty")
        s.commit()
    return {}


NODES = [("ingest", ingest), ("extract", extract), ("verify", verify), ("dedupe", dedupe),
         ("assign_sections", assign_sections), ("finalize", finalize)]

builder = StateGraph(State)
for name, fn in NODES:
    builder.add_node(name, fn)
builder.add_edge(START, "ingest")
builder.add_conditional_edges("ingest", lambda st: "extract" if st["supported"] else END)
for (a, _), (b, _) in zip(NODES[1:], NODES[2:]):
    builder.add_edge(a, b)
builder.add_edge("finalize", END)

graph = builder.compile()
