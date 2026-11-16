"""Офлайн-проверка relevance -> extract -> verify без OpenRouter (модель подменена).
Запуск из каталога backend:  python -m tests.test_extract_offline путь/к/статье.pdf"""

import os
import re
import shutil
import sys

DB = "/tmp/kr_offline.db"
if os.path.exists(DB):
    os.remove(DB)
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"

from langchain_core.messages import AIMessage  # noqa: E402

import app.pipeline.extract as ex  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Document, EvidenceCard, LlmCall, Page, Project  # noqa: E402
from app.pipeline.graph import graph  # noqa: E402


class Bound:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, messages):
        raw = AIMessage(
            content="",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
        )
        if self.schema.__name__ == "Biblio":
            return {
                "raw": raw,
                "parsed": ex.Biblio(
                    title="Тест",
                    year=2020,
                    study_design="rct",
                    relevance="relevant",
                    relevance_reason="тест",
                ),
            }
        user = messages[1][1]
        page = int(re.search(r"<<<СТРАНИЦА (\d+)>>>", user).group(1))
        quote = re.search(r"[A-Za-z][^.\n\-]{80,200}\.", user).group(
            0
        )  # реальная фраза из текста
        mk = lambda q, p: ex.Unit(
            statement_ru="Тест",
            subject="метод",
            predicate="снижает",
            object_="боль",
            negation=False,
            intervention_type="therapeutic",
            card_type="result",
            quote=q,
            page=p,
            confidence=0.9,
        )
        units = [
            mk(quote, page + 5),
            mk("Этой цитаты нет в тексте и модель её выдумала", page),
        ]  # страница перепутана; цитата выдумана
        return {"raw": raw, "parsed": ex.Units(units=units)}


class FakeLLM:
    def with_structured_output(self, schema, **kw):
        return Bound(schema)


ex.get_llm = lambda **kw: FakeLLM()
init_db()
shutil.copy(sys.argv[1], "/tmp/kr_offline.pdf")
with SessionLocal() as s:
    p = Project(
        title="Переломы дистального отдела костей предплечья",
        age_group="children",
        icd_codes=["S52.5"],
        organization="тест",
    )
    s.add(p)
    s.flush()
    d = Document(project_id=p.id, filename="a.pdf", stored_path="/tmp/kr_offline.pdf")
    s.add(d)
    s.commit()
    doc_id = d.id

graph.invoke({"document_id": doc_id, "job_id": None})
with SessionLocal() as s:
    cards = s.query(EvidenceCard).order_by(EvidenceCard.id).all()
    doc = s.get(Document, doc_id)
    print(
        "статус:",
        doc.status,
        "| дизайн:",
        doc.study_design,
        "| карточек:",
        len(cards),
        "| вызовов LLM:",
        s.query(LlmCall).count(),
    )
    for c in cards:
        print(
            f"  стр.{c.page_number} цитата={c.quote_verified} УДД источника={c.udd_source} проблемы={c.problems}"
        )
    assert doc.status in ("done", "done_partial") and len(cards) >= 2
    assert any(c.quote_verified == "verified" for c in cards) and any(
        c.quote_verified == "failed" for c in cards
    )
    assert all(c.udd_source == 2 for c in cards)  # rct + therapeutic
    good = next(c for c in cards if c.quote_verified == "verified")
    good.user_edits = {"statement_ru": "правка эксперта"}
    s.commit()
    n = len(cards)

graph.invoke({"document_id": doc_id, "job_id": None})  # повторная обработка
with SessionLocal() as s:
    cards = s.query(EvidenceCard).all()
    print(
        "после повтора карточек:",
        len(cards),
        "| правка сохранена, есть pending_version:",
        bool(s.get(EvidenceCard, good.id).pending_version),
    )
    assert len(cards) == n and s.get(EvidenceCard, good.id).pending_version
print("OK")
