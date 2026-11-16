"""Узлы графа: проверка релевантности источника (relevance) и извлечение карточек доказательств (extract)."""

import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.db import SessionLocal
from app.models import Document, EvidenceCard, Page, Project
from app.pipeline.grading import udd_for_source
from app.pipeline.llm import get_llm, record_usage
from app.pipeline.verify import content_hash, quote_on_page

SPEC = json.loads(
    (Path(__file__).parent.parent / "spec" / "kr_recommendation.schema.json").read_text(
        encoding="utf-8"
    )
)
DESIGNS = tuple(SPEC["$defs"]["study_design_enum"]["enum"])
MAX_CHARS = 7000  # размер фрагмента: сколько текста страниц уходит в один запрос
MIN_PAGE_CHARS = 200  # короче - страница пропускается (титул, пустая)
BIBLIO_MAX_TOKENS = 1500  # ответ с библиографией короткий
FATAL_HTTP = (
    401,
    402,
    403,
)  # ключ или кредиты: повторять остальные фрагменты бессмысленно

SYSTEM_BIBLIO = """Ты определяешь библиографические данные и дизайн научного источника по его первым страницам и оцениваешь его релевантность теме клинической рекомендации.

Дизайн (study_design) выбирай по признакам из текста, а не по названию журнала:
- rct: участников распределили по группам случайно;
- meta_analysis_rct / systematic_review_rct: обзор с описанной методикой поиска, только РКИ, с объединением данных / без него;
- meta_analysis_non_rct / systematic_review_non_rct: то же, но включены не только РКИ;
- narrative_review: обзор без методики поиска;
- cohort: сравнительное проспективное исследование без рандомизации;
- case_control: ретроспективное сравнение групп по наличию исхода;
- non_comparative: одна группа, в том числе «до-после»;
- case_series: ретроспективный анализ группы пациентов; case_report: один пациент;
- meta_analysis_diagnostic, diagnostic_with_reference, diagnostic_without_reference: оценка диагностической точности (обзор с мета-анализом; независимый референсный метод у всех пациентов; референсный метод не независим от оцениваемого);
- expert_opinion: клинические рекомендации, консенсус, письмо в редакцию, любое иное.
Если признаков недостаточно, оставь study_design пустым и объясни в design_basis.

Релевантность: relevant - источник про то же заболевание или про вопрос, которым КР по этой теме пользуется (обезболивание, профилактика ВТЭО, антибиотикопрофилактика и т. п. при той же травме или операции); irrelevant - явно другое заболевание, область или популяция; uncertain - не уверен. Причину напиши одной фразой."""

SYSTEM_EXTRACT = """Ты извлекаешь доказательства из научной статьи или руководства для составления клинической рекомендации. Верни утверждения об эффективности, безопасности или диагностической точности медицинских вмешательств, которые прямо сказаны в тексте.

Правила:
1. Только то, что есть в тексте. Ничего не домысливай и не обобщай.
2. Для оригинальных исследований бери результаты и выводы авторов; для обзоров и руководств - их выводы и рекомендации. Не извлекай пересказ чужих работ из введения и обсуждения, если это не выводы обзора.
3. quote - дословный фрагмент одной страницы, на языке оригинала, 1-2 предложения (до 300 символов), символ в символ: без сокращений, склеек и исправлений. Нет подходящего дословного фрагмента - утверждение не извлекай.
4. page - номер страницы из маркера <<<СТРАНИЦА N>>>, на которой стоит цитата.
5. statement_ru - одно предложение по-русски. Числа, дозы и сроки те же, что в цитате. Препараты по МНН.
6. negation=true, если показано отсутствие эффекта, отсутствие преимущества или вред.
7. card_type: recommendation - авторы или руководство прямо рекомендуют или не рекомендуют; result - результат исследования.
8. population и conditions (доза, режим, сроки, пороги) заполняй точно по тексту. Если утверждение относится к другой популяции, чем тема проекта, всё равно извлеки и укажи её в population.
9. Нет подходящих утверждений - верни пустой список."""

SYSTEM_MEANING = """Сравни русскую формулировку доказательства с дословной цитатой на языке источника.
Определи, следует ли формулировка из цитаты без добавленных фактов, и сохранены ли направление эффекта,
отрицание, популяция, числа и условия. Цитата может быть краткой, но не додумывай отсутствующие детали.
Если эквивалентность сомнительна, верни verified=false. Это проверка соответствия смысла, а не оценка качества исследования."""


class Biblio(BaseModel):
    title: str | None = None
    authors: list[str] = []
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None
    sample_size: int | None = None
    population: str | None = Field(
        None, description="Кто участвовал: возраст, состояние"
    )
    study_design: Literal[DESIGNS] | None = None
    design_basis: str | None = Field(
        None, description="Одна фраза: по каким признакам определён дизайн"
    )
    relevance: Literal["relevant", "irrelevant", "uncertain"] = "uncertain"
    relevance_reason: str = ""


class Unit(BaseModel):
    statement_ru: str = Field(
        description="Одно предложение по-русски; числа как в цитате"
    )
    subject: str = Field(
        description="Вмешательство, метод или фактор (по-русски, препараты по МНН)"
    )
    predicate: str = Field(
        description="Что установлено: «снижает», «не отличается по», «повышает риск»"
    )
    object_: str = Field(description="Исход или показатель, к которому относится вывод")
    negation: bool
    intervention_type: Literal["diagnostic", "therapeutic", "preventive", "rehab"]
    card_type: Literal["result", "recommendation"]
    population: str | None = None
    conditions: str | None = Field(
        None, description="Доза, режим, сроки, пороги, ограничения - как в тексте"
    )
    quote: str = Field(description="Дословная цитата со страницы, на языке оригинала")
    page: int = Field(description="Номер страницы из маркера <<<СТРАНИЦА N>>>")
    confidence: float = Field(ge=0, le=1)


class Units(BaseModel):
    units: list[Unit]


class MeaningCheck(BaseModel):
    verified: bool
    negation_mismatch: bool
    explanation: str


def check_meaning(
    statement: str, quote: str, negation: bool, doc_id: int, job_id: int | None
) -> MeaningCheck:
    return _call(
        MeaningCheck,
        SYSTEM_MEANING,
        f"Формулировка: {statement}\nОтрицание в карточке: {negation}\nЦитата источника: {quote}",
        doc_id,
        job_id,
        "meaning",
        600,
    )


def make_chunks(
    pages: list[tuple[int, str]], max_chars: int = MAX_CHARS
) -> list[list[tuple[int, str]]]:
    chunks, cur, size = [], [], 0
    for num, text in pages:
        if cur and size + len(text) > max_chars:
            chunks.append(cur)
            cur, size = [], 0
        cur.append((num, text))
        size += len(text)
    return chunks + [cur] if cur else chunks


def pages_text(chunk: list[tuple[int, str]]) -> str:
    return "\n\n".join(f"<<<СТРАНИЦА {n}>>>\n{t}" for n, t in chunk)


def looks_like_references(text: str) -> bool:
    numbered = len(re.findall(r"(?m)^\s*(?:\[\d{1,3}\]|\d{1,3}\.)\s", text))
    years = len(re.findall(r"\b(?:19|20)\d{2}\b", text))
    return numbered >= 8 and years >= 8


def _call(
    schema,
    system: str,
    user: str,
    doc_id: int,
    job_id: int | None,
    step: str,
    max_tokens: int | None = None,
):
    llm = get_llm(max_tokens=max_tokens).with_structured_output(
        schema, method="function_calling", include_raw=True
    )
    started = time.time()
    out = llm.invoke([("system", system), ("human", user)])
    record_usage(
        job_id, doc_id, step, out["raw"], started
    )  # токены пишем и при неудачном разборе
    if out.get("parsed") is None:
        if (getattr(out["raw"], "response_metadata", {}) or {}).get(
            "finish_reason"
        ) == "length":
            raise ValueError(
                "ответ обрезан по max_tokens: увеличьте OPENROUTER_MAX_TOKENS или уменьшите MAX_CHARS"
            )
        raise ValueError(f"ответ модели не разобран: {out.get('parsing_error')}")
    return out["parsed"]


def _project_context(s, doc: Document) -> str:
    p = s.get(Project, doc.project_id)
    age = {"adults": "взрослые", "children": "дети", "mixed": "взрослые и дети"}.get(
        p.age_group, p.age_group
    )
    return f"Тема КР: {p.title}. Коды МКБ-10: {', '.join(p.icd_codes or []) or 'не указаны'}. Возраст: {age}."


def relevance(state):
    """Библиография, дизайн источника и релевантность теме. Нерелевантный источник дальше не обрабатывается."""
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        if doc.relevance == "forced":  # пользователь настоял на обработке
            return {"relevant": True}
        first = (
            s.query(Page)
            .filter_by(document_id=doc.id)
            .order_by(Page.number)
            .limit(3)
            .all()
        )
        text, ctx = (
            pages_text([(p.number, p.text) for p in first])[:9000],
            _project_context(s, doc),
        )
    b = _call(
        Biblio,
        SYSTEM_BIBLIO,
        f"{ctx}\n\n{text}",
        state["document_id"],
        state.get("job_id"),
        "biblio",
        BIBLIO_MAX_TOKENS,
    )
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        doc.biblio = b.model_dump(
            exclude={"study_design", "relevance", "relevance_reason"}
        )
        doc.study_design, doc.relevance, doc.relevance_reason = (
            b.study_design,
            b.relevance,
            b.relevance_reason,
        )
        if b.relevance == "irrelevant":
            doc.status = "irrelevant"
            doc.status_detail = (
                f"Источник не относится к теме проекта: {b.relevance_reason}"
            )
        s.commit()
    return {"relevant": b.relevance != "irrelevant"}


def _save_units(doc_id: int, study_design: str | None, chunk, units: list[Unit]) -> int:
    texts = dict(chunk)
    with SessionLocal() as s:
        doc = s.get(Document, doc_id)
        existing_cards = s.query(EvidenceCard).filter_by(document_id=doc_id).all()
        existing = {c.content_hash: c for c in existing_cards}
        by_page = {}
        for card in existing_cards:
            by_page.setdefault(card.page_number, []).append(card)
        created = 0
        for u in units:
            # модель часто путает номер страницы: ищем цитату на странице фрагмента, иначе оставляем её ответ
            page = (
                u.page
                if quote_on_page(u.quote, texts.get(u.page, ""))
                else next((n for n, t in chunk if quote_on_page(u.quote, t)), u.page)
            )
            h = content_hash(doc_id, page, u.quote)
            data = u.model_dump() | {"page": page}
            c = existing.get(h)
            if c is None:
                # Quotes can change slightly on a rerun. Match only a strong,
                # unambiguous quote overlap on the same page so distinct claims
                # are not silently attached to the wrong card.
                candidates = []
                normalized_quote = content_hash(doc_id, page, u.quote)
                for old in by_page.get(page, []):
                    if old.content_hash == normalized_quote:
                        c = old
                        break
                    score = SequenceMatcher(
                        None,
                        " ".join((old.quote or "").casefold().split()),
                        " ".join(u.quote.casefold().split()),
                        autojunk=False,
                    ).ratio()
                    if score >= 0.78:
                        candidates.append((score, old))
                if c is None and candidates:
                    candidates.sort(key=lambda item: item[0], reverse=True)
                    best = candidates[0]
                    second_score = candidates[1][0] if len(candidates) > 1 else 0.0
                    if best[0] >= 0.86 and (len(candidates) == 1 or best[0] - second_score >= 0.12):
                        c = best[1]
            if c:
                if data != (c.auto_data or {}):
                    # Never replace a reviewed or unreviewed card in place;
                    # expose the re-extracted version for an expert decision.
                    c.pending_version = data
                else:
                    c.pending_version = None
                existing[h] = c
                continue
            c = EvidenceCard(
                project_id=doc.project_id,
                document_id=doc_id,
                page_number=page,
                statement_ru=u.statement_ru,
                card_type=u.card_type,
                subject=u.subject,
                predicate=u.predicate,
                object_=u.object_,
                intervention=u.subject,
                outcome=u.object_,
                negation=u.negation,
                population=u.population,
                conditions=u.conditions,
                polarity="negative" if u.negation else "positive",
                intervention_type=u.intervention_type,
                udd_source=udd_for_source(study_design, u.intervention_type),
                extraction_confidence=u.confidence,
                quote=u.quote,
                content_hash=h,
                auto_data=data,
            )
            s.add(c)
            existing[h] = c
            by_page.setdefault(page, []).append(c)
            created += 1
        s.commit()
    return created


def extract(state):
    """Фрагменты страниц -> LLM -> карточки. Каждый фрагмент сохраняется сразу; сбой фрагмента помечает его страницы."""
    doc_id, job_id = state["document_id"], state.get("job_id")
    with SessionLocal() as s:
        doc = s.get(Document, doc_id)
        study_design, ctx = doc.study_design, _project_context(s, doc)
        pages = []
        for p in s.query(Page).filter_by(document_id=doc_id).order_by(Page.number):
            if len(p.text.strip()) < MIN_PAGE_CHARS:
                p.status, p.error = "skipped", "почти нет текста"
            elif looks_like_references(p.text):
                p.status, p.error = "skipped", "список литературы"
            else:
                pages.append((p.number, p.text))
        s.commit()
    ok, last_err, fatal = 0, None, False
    for chunk in make_chunks(pages):
        nums = [n for n, _ in chunk]
        try:
            res = _call(
                Units,
                SYSTEM_EXTRACT,
                f"{ctx}\n\n{pages_text(chunk)}",
                doc_id,
                job_id,
                "extract",
            )
            _save_units(doc_id, study_design, chunk, res.units)
            status, err = "processed", None
        except Exception as e:  # сбой фрагмента не должен терять остальные
            status, err = "error", f"{type(e).__name__}: {e}"[:500]
            last_err, fatal = err, getattr(e, "status_code", None) in FATAL_HTTP
        with SessionLocal() as s:
            for p in s.query(Page).filter(
                Page.document_id == doc_id, Page.number.in_(nums)
            ):
                p.status, p.error = status, err
            s.commit()
        if fatal:  # нет кредитов или неверный ключ: остальные фрагменты упадут так же, прекращаем сразу
            raise RuntimeError(f"Обработка остановлена: {last_err}")
        ok += status == "processed"
    if pages and not ok:
        raise RuntimeError(
            f"Ни один фрагмент не обработан. Последняя ошибка: {last_err}"
        )
    return {}
