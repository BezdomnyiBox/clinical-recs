from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Table, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Разделы черновика, в которые попадают тезисы. Титул, критерии качества и литература собираются отдельно.
SECTIONS = {
    "summary": "Краткая информация",
    "diagnostics": "Диагностика",
    "treatment": "Лечение",
    "rehabilitation": "Реабилитация",
    "prevention": "Профилактика",
    "care_organization": "Организация помощи",
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
    icd_codes: Mapped[list] = mapped_column(JSON, default=list)  # TODO: проверка по справочнику МКБ-10
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
    biblio: Mapped[dict | None] = mapped_column(JSON)  # название, авторы, год, журнал, DOI/PMID, дизайн


class Page(Base):
    """Текст каждой страницы хранится: по нему проверяются цитаты и считается покрытие."""
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    number: Mapped[int]  # порядковый номер страницы PDF (печатная нумерация - отдельным полем при необходимости)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | processed | skipped | error
    error: Mapped[str | None] = mapped_column(Text)


class EvidenceCard(TS, Base):
    __tablename__ = "evidence_cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    page_number: Mapped[int]
    statement_ru: Mapped[str] = mapped_column(Text)
    card_type: Mapped[str] = mapped_column(String(16), default="result")  # result | recommendation
    population: Mapped[str | None] = mapped_column(Text)
    intervention: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(Text)  # доза, сроки, пороги, ограничения
    polarity: Mapped[str] = mapped_column(String(16), default="descriptive")  # positive|negative|conditional|descriptive
    quote: Mapped[str] = mapped_column(Text)  # дословно, на языке источника
    quote_verified: Mapped[str] = mapped_column(String(16), default="pending")  # pending|verified|failed
    meaning_verified: Mapped[str] = mapped_column(String(16), default="pending")
    problems: Mapped[list] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String(16), default="new")  # new|confirmed|rejected|merged
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_cards.id"))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # ключ сопоставления при повторной обработке
    auto_data: Mapped[dict] = mapped_column(JSON)  # результат автомата, не меняется после создания
    user_edits: Mapped[dict | None] = mapped_column(JSON)  # поля, исправленные пользователем
    pending_version: Mapped[dict | None] = mapped_column(JSON)  # новая версия после перезапуска, ждёт решения


thesis_cards = Table(
    "thesis_cards", Base.metadata,
    Column("thesis_id", ForeignKey("theses.id"), primary_key=True),
    Column("card_id", ForeignKey("evidence_cards.id"), primary_key=True),
)


class Thesis(TS, Base):
    __tablename__ = "theses"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    section: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(16), default="suggested")  # extracted | suggested | expert
    comment: Mapped[str | None] = mapped_column(Text)
    udd: Mapped[str | None] = mapped_column(String(8))
    uur: Mapped[str | None] = mapped_column(String(8))  # без подтверждения эксперта - предварительный
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
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)  # queued|running|done|error
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class LlmCall(TS, Base):
    """Каждый вызов модели: из этой таблицы строится отчёт о времени, токенах и стоимости."""
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), index=True)
    step: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    seconds: Mapped[float] = mapped_column(Float, default=0)
