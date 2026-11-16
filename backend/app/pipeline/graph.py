from collections import Counter
from typing import Any, cast
from typing_extensions import NotRequired, TypedDict
import re
import unicodedata

from langgraph.graph import END, START, StateGraph

from app.db import SessionLocal
from app.models import Conflict, Document, EvidenceCard, Page, Thesis
from app.pipeline.activity import finish_processing_event, start_processing_event
from app.pipeline.extract import check_meaning, extract, relevance
from app.pipeline.ingest import extract_pages, has_text_layer
from app.pipeline.verify import numbers_missing, quote_on_page
from app.pipeline.grading import (
    STRENGTH,
    THESIS_SECTIONS,
    udd_for_source,
    validate_thesis,
)


class State(TypedDict):
    document_id: int
    job_id: NotRequired[int]
    supported: NotRequired[bool]
    relevant: NotRequired[bool]


_NUMBER = re.compile(
    r"(?<!\w)[+-]?\d+(?:[.,]\d+)?(?:\s*(?:%|[a-zа-яёμµ]+))?",
    re.IGNORECASE,
)


def _normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^\w]+", " ", value).strip()


def _number_signature(*values: str | None) -> tuple[str, ...]:
    """Keep numeric values and adjacent units as part of clinical identity."""
    result = []
    for value in values:
        for match in _NUMBER.findall(value or ""):
            number = re.sub(r"\s+", "", match.casefold()).replace(",", ".")
            if number not in result:
                result.append(number)
    return tuple(result)


def _clinical_identity(card: EvidenceCard) -> tuple | None:
    """Exact normalized identity; missing action, group or outcome stays unmerged."""
    action = _normalize(card.intervention or card.subject)
    population = _normalize(card.population)
    outcome = _normalize(card.outcome or card.object_)
    if not action or not population or not outcome:
        return None
    return (
        action,
        population,
        _normalize(card.conditions),
        outcome,
        _normalize(card.predicate),
        bool(card.negation),
        _number_signature(card.statement_ru, card.conditions),
    )


def _predicate_direction(predicate: str | None) -> str | None:
    value = _normalize(predicate)
    if any(word in value for word in ("повыш", "увелич", "возраст", "продлева")):
        return "increase"
    if any(word in value for word in ("снижа", "уменьш", "сокращ", "снижен")):
        return "decrease"
    if "улучш" in value:
        return "improve"
    if "ухудш" in value:
        return "worsen"
    return None


def _section_for_card(card: EvidenceCard, intervention_type: str | None) -> str | None:
    if card.kr_section in THESIS_SECTIONS:
        return card.kr_section
    return {
        "diagnostic": "2.5",
        "therapeutic": "3.1",
        "preventive": "5",
        "rehab": "4",
    }.get(intervention_type or "")


def _recommendation_sentence(statement: str, direction: str, uur: str) -> tuple[str, str]:
    phrase = STRENGTH[(direction, uur)]
    body = statement.strip()
    for prefix in RECOMMENDATION_PREFIXES:
        body = body.removeprefix(prefix)
    return f"{phrase} {body.lstrip(' ,:—-.')}".strip(), phrase


RECOMMENDATION_PREFIXES = (
    "Не рекомендуется рассматривать возможность",
    "Не рекомендуется рассматривать",
    "Не рекомендуется",
    "Рекомендуется рассмотреть возможность",
    "Рекомендуется",
)


def ingest(state: State):
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        if doc is None:
            raise ValueError(f"Document {state['document_id']} not found")
        doc.status = "processing"
        texts = extract_pages(doc.stored_path)
        doc.page_count = len(texts)
        # Pages are refreshed; extracted cards survive and are reconciled by quote hash.
        s.query(Page).filter_by(document_id=doc.id).delete()
        s.add_all(
            Page(document_id=doc.id, number=i, text=t) for i, t in enumerate(texts, 1)
        )
        ok = has_text_layer(texts)
        if not ok:
            doc.status = "unsupported"
            doc.status_detail = (
                "В PDF нет текстового слоя (скан). Такие документы не обрабатываются."
            )
        s.commit()
    return {"supported": ok}


def verify(state: State):
    with SessionLocal() as s:
        pages = {
            p.number: p.text
            for p in s.query(Page).filter_by(document_id=state["document_id"])
        }
        for c in s.query(EvidenceCard).filter_by(document_id=state["document_id"]):
            pending = dict(c.pending_version or {})
            is_pending = bool(pending)
            statement = str(pending.get("statement_ru") or c.statement_ru)
            quote = str(pending.get("quote") or c.quote)
            page_number = pending.get("page", c.page_number)
            negation = bool(pending.get("negation", c.negation))
            problems = []
            if not quote_on_page(quote, pages.get(page_number, "")):
                problems.append("цитата не найдена на указанной странице")
            if missing := numbers_missing(statement, quote):
                problems.append(
                    "числа из формулировки нет в цитате: " + ", ".join(missing)
                )
            quote_status = "failed" if problems else "verified"
            try:
                result = check_meaning(
                    statement,
                    quote,
                    negation,
                    c.document_id,
                    state.get("job_id"),
                    card_id=c.id,
                    page_number=page_number,
                )
                meaning_status = "verified" if result.verified and not result.negation_mismatch else "failed"
                if meaning_status == "failed":
                    problems.append(
                        "проверка смысла: " + (result.explanation or "цитата не подтверждает формулировку")
                    )
            except Exception as exc:
                meaning_status = "pending"
                problems.append(f"проверка смысла не выполнена: {type(exc).__name__}")
            if is_pending:
                pending.update({
                    "quote_verified": quote_status,
                    "meaning_verified": meaning_status,
                    "problems": problems,
                })
                c.pending_version = pending
            else:
                c.quote_verified = quote_status
                c.meaning_verified = meaning_status
                c.problems = problems
        s.commit()
    return {}


def dedupe(state: State):
    """Merge exact clinical duplicates and retain both sides of contradictions."""
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        if doc is None:
            return {}
        if not doc:
            return {}
        cards = (
            s.query(EvidenceCard)
            .filter_by(project_id=doc.project_id)
            .filter(EvidenceCard.review_status != "rejected")
            .order_by(EvidenceCard.id)
            .all()
        )
        duplicate_keys = {}
        by_comparison = {}
        for card in cards:
            key = _clinical_identity(card)
            if key is not None and key in duplicate_keys:
                card.review_status = "merged"
                card.merged_into_id = duplicate_keys[key].id
            elif key is not None:
                duplicate_keys[key] = card

            # Compare matching action, population, conditions, outcome and numbers;
            # direction is deliberately excluded so opposite results can conflict.
            if key is not None and card.review_status != "merged":
                compare = key[:4] + (key[-1],)
                by_comparison.setdefault(compare, []).append(card)

        existing_pairs = {
            tuple(sorted(c.card_ids or []))
            for c in s.query(Conflict).filter_by(project_id=doc.project_id).all()
        }
        project_documents = {
            d.id: d for d in s.query(Document).filter_by(project_id=doc.project_id)
        }
        for group in by_comparison.values():
            for i, left in enumerate(group):
                for right in group[i + 1:]:
                    left_direction = _predicate_direction(left.predicate)
                    right_direction = _predicate_direction(right.predicate)
                    inverse = {"increase": "decrease", "decrease": "increase",
                               "improve": "worsen", "worsen": "improve"}
                    opposite = left.negation != right.negation or (
                        left_direction is not None
                        and inverse.get(left_direction) == right_direction
                    )
                    if not opposite:
                        continue
                    pair = tuple(sorted((left.id, right.id)))
                    if pair in existing_pairs:
                        continue
                    left_doc = project_documents.get(left.document_id)
                    right_doc = project_documents.get(right.document_id)
                    left_source = (
                        f"{left_doc.filename}, стр. {left.page_number}"
                        if left_doc else f"документ {left.document_id}, стр. {left.page_number}"
                    )
                    right_source = (
                        f"{right_doc.filename}, стр. {right.page_number}"
                        if right_doc else f"документ {right.document_id}, стр. {right.page_number}"
                    )
                    s.add(Conflict(
                        project_id=doc.project_id,
                        card_ids=list(pair),
                        description=(
                            "Кандидат на противоречие: совпадают действие, популяция, условия, исход и "
                            "числовые параметры, но направление утверждений различается. "
                            f"Источник 1: {left_source}; источник 2: {right_source}. Требуется экспертная оценка."
                        ),
                    ))
                    existing_pairs.add(pair)
        s.commit()
    return {}


def assign_sections(state: State):
    """Создаёт предварительные тезисы только из явных рекомендаций источников.

    Результаты исследований сами по себе не превращаются в рекомендации: это
    клинический вывод, который должен сделать эксперт. Каждая рекомендация
    сохраняет ссылку на исходную карточку и пометку auto.
    """
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        if doc is None:
            return {}
        if not doc:
            return {}
        cards = (
            s.query(EvidenceCard)
            .filter_by(document_id=doc.id)
            .filter(EvidenceCard.review_status != "rejected")
            .filter(EvidenceCard.review_status != "merged")
            .order_by(EvidenceCard.id)
            .all()
        )
        project_theses = s.query(Thesis).filter_by(project_id=doc.project_id).all()
        for card in cards:
            thesis = next(
                (
                    item for item in project_theses
                    if item.provenance != "manual" and card in item.cards
                ),
                None,
            )
            pending = card.pending_version or {}
            pending_statement = str(pending.get("statement_ru") or card.statement_ru or "").strip()
            pending_type = pending.get("card_type", card.card_type)

            if card.pending_version and thesis:
                if pending_type != "recommendation":
                    thesis.pending_version = {
                        "evidence_card_id": card.id,
                        "withdrawn": True,
                        "text": "Новая версия карточки больше не содержит явную рекомендацию; тезис требует пересмотра.",
                    }
                    continue
                pending_intervention_type = pending.get("intervention_type") or card.intervention_type
                pending_section = _section_for_card(card, pending_intervention_type)
                if not pending_section:
                    thesis.pending_version = {
                        "evidence_card_id": card.id,
                        "text": pending_statement,
                        "reason": "Для новой версии не определён раздел КР.",
                    }
                    continue
                pending_direction = "negative" if pending.get("negation", card.negation) else "positive"
                pending_udd = card.udd_source or udd_for_source(doc.study_design, pending_intervention_type)
                pending_text, pending_phrase = _recommendation_sentence(
                    pending_statement, pending_direction, "C"
                )
                thesis.pending_version = {
                    "evidence_card_id": card.id,
                    "section": pending_section,
                    "text": pending_text,
                    "direction": pending_direction,
                    "strength_phrase": pending_phrase,
                    "udd": pending_udd,
                    "uur": "C",
                    "page": pending.get("page", card.page_number),
                    "quote": pending.get("quote", card.quote),
                    "quote_verified": pending.get("quote_verified", "pending"),
                    "meaning_verified": pending.get("meaning_verified", "pending"),
                    "problems": pending.get("problems", []),
                    "provenance": "auto",
                }
                continue

            if thesis and thesis.pending_version and thesis.pending_version.get("evidence_card_id") == card.id:
                thesis.pending_version = None

            if card.card_type != "recommendation" or not card.statement_ru.strip():
                continue
            # Keep section assignment within the recommendation chapters.
            section = _section_for_card(card, card.intervention_type)
            if section is None:
                continue

            direction = "negative" if card.negation else "positive"
            udd = card.udd_source or udd_for_source(
                doc.study_design, card.intervention_type
            )
            # УУР не определяется одним УДД. Ставим предварительный C, пока
            # клиническая значимость и согласованность не оценены экспертом.
            uur = "C"
            text, phrase = _recommendation_sentence(card.statement_ru, direction, uur)
            if thesis is None:
                thesis = Thesis(project_id=card.project_id, section=section, text=text)
                s.add(thesis)
                thesis.cards.append(card)
                project_theses.append(thesis)
            elif not thesis.user_edits:
                thesis.section, thesis.text = section, text
            if thesis.id is None:
                thesis.provenance = "auto"
            generated_values = {
                "subsection_title": {
                "2.1": "Жалобы и анамнез", "2.2": "Физикальное обследование",
                "2.3": "Лабораторная диагностика", "2.4": "Инструментальная диагностика",
                "2.5": "Иные диагностические исследования", "3.1": "Консервативное лечение",
                "3.2": "Хирургическое лечение", "3.3": "Иное лечение",
                "4": "Медицинская реабилитация", "5": "Профилактика",
                }.get(section, section),
                "direction": direction,
                "strength_phrase": phrase,
                "intervention": {
                "type": card.intervention_type,
                "action": card.intervention or card.subject or "",
                "target_population": card.population or "",
                "comparator": None,
                "outcome": card.outcome or card.object_ or "",
                "mnn": None,
                "atc_code": None,
                "scale_ref": "udd_diagnostic" if card.intervention_type == "diagnostic" else "udd_treatment",
                },
                "evidence_backed_core": card.statement_ru,
                "udd": udd,
                "uur": uur,
                "grade_rationale": (
                f"Предварительно: УДД {udd if udd is not None else 'не определён'} по дизайну "
                f"источника ({doc.study_design or 'не указан'}); УУР C назначен до экспертной оценки "
                "клинической значимости и согласованности."
                ),
                "consensus": {"agreement": "consistent", "conflicting_refs": []},
                "quality_criterion": {"is_criterion": False},
                "expert_additions": [],
            }
            for field, value in generated_values.items():
                if field not in (thesis.user_edits or {}):
                    setattr(thesis, field, value)
            thesis.auto_data = {
                "card_ids": [card.id], "section": section, "text": text,
                "udd": udd, "uur": uur,
            }
            thesis.review_flags = validate_thesis({
                "section": thesis.section, "text": thesis.text, "provenance": thesis.provenance,
                "card_ids": [card.id], "udd": thesis.udd, "uur": thesis.uur,
                "grade_rationale": thesis.grade_rationale,
            })
        s.commit()
    return {}


def finalize(state: State):
    with SessionLocal() as s:
        doc = s.get(Document, state["document_id"])
        if doc is None:
            return {}
        if doc.status == "irrelevant":  # статус и причину выставил узел relevance
            return {}
        failed = s.query(Page).filter_by(document_id=doc.id, status="error").count()
        cards = s.query(EvidenceCard).filter_by(document_id=doc.id).count()
        doc.status = "done_partial" if failed else ("done" if cards else "done_empty")
        s.commit()
    return {}


NODES = [
    ("ingest", ingest),
    ("relevance", relevance),
    ("extract", extract),
    ("verify", verify),
    ("dedupe", dedupe),
    ("assign_sections", assign_sections),
    ("finalize", finalize),
]


def _stage_summary(step: str, document_id: int) -> dict:
    with SessionLocal() as s:
        doc = s.get(Document, document_id)
        if doc is None:
            return {}
        pages = s.query(Page).filter_by(document_id=document_id).all()
        cards = s.query(EvidenceCard).filter_by(document_id=document_id).all()
        page_counts = Counter(page.status for page in pages)
        if step == "ingest":
            return {
                "pages_total": doc.page_count or 0,
                "text_layer_supported": doc.status != "unsupported",
            }
        if step == "relevance":
            return {
                "relevance": doc.relevance,
                "study_design": doc.study_design,
                "reason": doc.relevance_reason,
            }
        if step == "extract":
            return {
                "cards_total": len(cards),
                "recommendations": sum(
                    card.card_type == "recommendation" for card in cards
                ),
                "results": sum(card.card_type == "result" for card in cards),
                "pending_versions": sum(bool(card.pending_version) for card in cards),
                "pages_processed": page_counts.get("processed", 0),
                "pages_failed": page_counts.get("error", 0),
            }
        if step == "verify":
            return {
                "cards_checked": len(cards),
                "quotes_verified": sum(
                    card.quote_verified == "verified" for card in cards
                ),
                "quotes_failed": sum(card.quote_verified == "failed" for card in cards),
                "meaning_verified": sum(
                    card.meaning_verified == "verified" for card in cards
                ),
                "meaning_failed": sum(
                    card.meaning_verified == "failed" for card in cards
                ),
                "meaning_pending": sum(
                    card.meaning_verified == "pending" for card in cards
                ),
            }
        if step == "dedupe":
            return {
                "merged_cards_in_project": s.query(EvidenceCard)
                .filter_by(project_id=doc.project_id, review_status="merged")
                .count(),
                "conflicts_in_project": s.query(Conflict)
                .filter_by(project_id=doc.project_id)
                .count(),
            }
        if step == "assign_sections":
            linked_theses = [
                thesis
                for thesis in s.query(Thesis).filter_by(project_id=doc.project_id).all()
                if any(card.document_id == document_id for card in thesis.cards)
            ]
            return {
                "theses_linked": len(linked_theses),
                "automatic_theses": sum(
                    thesis.provenance != "manual" for thesis in linked_theses
                ),
                "pending_theses": sum(
                    bool(thesis.pending_version) for thesis in linked_theses
                ),
            }
        if step == "finalize":
            return {
                "document_status": doc.status,
                "pages_total": doc.page_count or 0,
                "pages_processed": page_counts.get("processed", 0),
                "pages_failed": page_counts.get("error", 0),
                "cards_total": len(cards),
            }
        return {}


def _record_skipped_stage(step: str, document_id: int, job_id: int | None, reason: str):
    event_id, started = start_processing_event(job_id, document_id, step)
    finish_processing_event(
        event_id,
        started,
        result_summary={"reason": reason},
        status="skipped",
    )


def _observe_node(name, fn):
    def run(state: State):
        document_id = state["document_id"]
        job_id = state.get("job_id")
        event_id, started = start_processing_event(job_id, document_id, name)
        try:
            result = fn(state)
        except Exception as exc:
            finish_processing_event(event_id, started, error=exc)
            raise
        finish_processing_event(
            event_id,
            started,
            result_summary=_stage_summary(name, document_id),
        )
        if name == "ingest" and not result.get("supported", False):
            for skipped in (
                "relevance",
                "extract",
                "verify",
                "dedupe",
                "assign_sections",
                "finalize",
            ):
                _record_skipped_stage(
                    skipped,
                    document_id,
                    job_id,
                    "PDF не содержит поддерживаемый текстовый слой",
                )
        elif name == "relevance" and not result.get("relevant", False):
            for skipped in ("extract", "verify", "dedupe", "assign_sections"):
                _record_skipped_stage(
                    skipped, document_id, job_id, "Источник признан нерелевантным"
                )
        return result

    return run


builder = StateGraph(cast(Any, State))
for name, fn in NODES:
    builder.add_node(name, _observe_node(name, fn))
builder.add_edge(START, "ingest")
builder.add_conditional_edges(
    "ingest", lambda st: "relevance" if st["supported"] else END
)
builder.add_conditional_edges(
    "relevance", lambda st: "extract" if st["relevant"] else "finalize"
)
for (a, _), (b, _) in zip(NODES[2:], NODES[3:]):
    builder.add_edge(a, b)
builder.add_edge("finalize", END)

graph = builder.compile()
