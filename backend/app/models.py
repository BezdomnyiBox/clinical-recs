from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Разделы КР по приказу 103н (названия менять нельзя). Тезисы-рекомендации допустимы только в разделах 2-5.
SECTIONS = {
    "1.1": "Определение заболевания или состояния (группы заболеваний или состояний)",
    "1.2": "Этиология и патогенез заболевания или состояния (группы заболеваний или состояний)",
    "1.3": "Эпидемиология заболевания или состояния (группы заболеваний или состояний)",
    "1.4": "Особенности кодирования заболевания или состояния (группы заболеваний или состояний) по Международной статистической классификации болезней и проблем, связанных со здоровьем",
    "1.5": "Классификация заболевания или состояния (группы заболеваний или состояний)",
    "1.6": "Клиническая картина заболевания или состояния (группы заболеваний или состояний)",
    "2.1": "Жалобы и анамнез",
    "2.2": "Физикальное обследование",
    "2.3": "Лабораторные диагностические исследования",
    "2.4": "Инструментальные диагностические исследования",
    "2.5": "Иные диагностические исследования",
    "3.1": "Консервативное лечение",  # 3.x в приказе не заданы: названия по КР846, сверить с шаблоном
    "3.2": "Хирургическое лечение",
    "3.3": "Иное лечение",
    "4": "Медицинская реабилитация и санаторно-курортное лечение, медицинские показания и противопоказания к применению методов медицинской реабилитации, в том числе основанных на использовании природных лечебных факторов",
    "5": "Профилактика и диспансерное наблюдение, медицинские показания и противопоказания к применению методов профилактики",
    "6": "Организация оказания медицинской помощи",
    "7": "Дополнительная информация (в том числе факторы, влияющие на исход заболевания или состояния)",
}


class Base(DeclarativeBase):
    pass


class TS:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Project(TS, Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    age_group: Mapped[str] = mapped_column(String(64), default="")
    icd_codes: Mapped[list] = mapped_column(
        JSON, default=list
    )  # TODO: проверка по справочнику МКБ-10
    organization: Mapped[str] = mapped_column(String(255), default="")


class Document(TS, Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    # queued | processing | done | done_empty | done_partial | failed | unsupported
    status: Mapped[str] = mapped_column(String(32), default="queued")
    status_detail: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None]
    biblio: Mapped[dict | None] = mapped_column(
        JSON
    )  # source: title, authors, year, journal, doi, pmid, sample_size, population
    study_design: Mapped[str | None] = mapped_column(
        String(32)
    )  # study_design_enum, определяет УДД источника
    content_hash: Mapped[str | None] = mapped_column(
        String(64), index=True
    )  # sha256 файла: точные дубликаты
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    relevance: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending | relevant | irrelevant | uncertain
    relevance_reason: Mapped[str | None] = mapped_column(Text)


class Page(Base):
    """Текст каждой страницы хранится: по нему проверяются цитаты и считается покрытие."""

    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    number: Mapped[
        int
    ]  # порядковый номер страницы PDF (печатная нумерация - отдельным полем при необходимости)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending | processed | skipped | error
    error: Mapped[str | None] = mapped_column(Text)


class EvidenceCard(TS, Base):
    __tablename__ = "evidence_cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    page_number: Mapped[int]
    subject: Mapped[str | None] = mapped_column(Text)  # триплет evidence_unit
    predicate: Mapped[str | None] = mapped_column(Text)
    object_: Mapped[str | None] = mapped_column(Text)
    negation: Mapped[bool] = mapped_column(default=False)  # вмешательство НЕ эффективно
    intervention_type: Mapped[str | None] = mapped_column(
        String(16)
    )  # diagnostic | therapeutic | preventive | rehab
    udd_source: Mapped[
        int | None
    ]  # УДД источника, выводится из дизайна (pipeline/grading.py)
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    kr_section: Mapped[str | None] = mapped_column(String(8))
    statement_ru: Mapped[str] = mapped_column(Text)
    card_type: Mapped[str] = mapped_column(
        String(16), default="result"
    )  # result | recommendation
    population: Mapped[str | None] = mapped_column(Text)
    intervention: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(
        Text
    )  # доза, сроки, пороги, ограничения
    polarity: Mapped[str] = mapped_column(
        String(16), default="descriptive"
    )  # positive|negative|conditional|descriptive
    quote: Mapped[str] = mapped_column(Text)  # дословно, на языке источника
    quote_verified: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending|verified|failed
    meaning_verified: Mapped[str] = mapped_column(String(16), default="pending")
    problems: Mapped[list] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(
        String(16), default="new"
    )  # new|confirmed|rejected|merged
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_cards.id"))
    content_hash: Mapped[str] = mapped_column(
        String(64), index=True
    )  # ключ сопоставления при повторной обработке
    auto_data: Mapped[dict] = mapped_column(
        JSON
    )  # результат автомата, не меняется после создания
    user_edits: Mapped[dict | None] = mapped_column(
        JSON
    )  # поля, исправленные пользователем
    pending_version: Mapped[dict | None] = mapped_column(
        JSON
    )  # новая версия после перезапуска, ждёт решения


thesis_cards = Table(
    "thesis_cards",
    Base.metadata,
    Column("thesis_id", ForeignKey("theses.id"), primary_key=True),
    Column("card_id", ForeignKey("evidence_cards.id"), primary_key=True),
)


class Thesis(TS, Base):
    __tablename__ = "theses"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    section: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(
        String(24), default="auto"
    )  # auto | auto+expert_review | manual
    comment: Mapped[str | None] = mapped_column(Text)
    udd: Mapped[int | None]  # 1-5
    uur: Mapped[str | None] = mapped_column(
        String(8)
    )  # без подтверждения эксперта - предварительный
    subsection_title: Mapped[str | None] = mapped_column(String(255))
    direction: Mapped[str | None] = mapped_column(String(16))  # positive | negative
    strength_phrase: Mapped[str | None] = mapped_column(String(64))
    intervention: Mapped[dict | None] = mapped_column(
        JSON
    )  # type, scale_ref, action, target_population, comparator, outcome, mnn, atc_code
    evidence_backed_core: Mapped[str | None] = mapped_column(Text)
    expert_additions: Mapped[list] = mapped_column(
        JSON, default=list
    )  # [{claim, basis}]: то, что не следует из источников
    grade_rationale: Mapped[str | None] = mapped_column(Text)
    consensus: Mapped[dict | None] = mapped_column(
        JSON
    )  # {agreement, conflicting_refs}
    quality_criterion: Mapped[dict | None] = mapped_column(
        JSON
    )  # {is_criterion, criterion_text, ...}
    review_flags: Mapped[list] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String(16), default="new")
    auto_data: Mapped[dict | None] = mapped_column(JSON)
    user_edits: Mapped[dict | None] = mapped_column(JSON)
    pending_version: Mapped[dict | None] = mapped_column(JSON)
    cards: Mapped[list[EvidenceCard]] = relationship(secondary=thesis_cards)


class Conflict(TS, Base):
    __tablename__ = "conflicts"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    card_ids: Mapped[list] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open")


class QualityCriterion(TS, Base):
    __tablename__ = "quality_criteria"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    thesis_ids: Mapped[list] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String(16), default="new")


class ChecklistAnswer(TS, Base):
    __tablename__ = "checklist_answers"
    __table_args__ = (UniqueConstraint("project_id", "item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    item_id: Mapped[str] = mapped_column(String(16))
    response: Mapped[str] = mapped_column(String(24), default="unreviewed")
    comment: Mapped[str] = mapped_column(Text, default="")


class ExpertEdit(TS, Base):
    """Журнал решений и правок пользователя."""

    __tablename__ = "expert_edits"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int]
    field: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[dict | list | str | None] = mapped_column(JSON)
    new_value: Mapped[dict | list | str | None] = mapped_column(JSON)


class Job(TS, Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(
        String(16), default="queued", index=True
    )  # queued|running|done|error
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class LlmCall(TS, Base):
    """Каждый вызов модели: из этой таблицы строится отчёт о времени, токенах и стоимости."""

    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), index=True
    )
    step: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    seconds: Mapped[float] = mapped_column(Float, default=0)
