from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_session, to_dict
from app.models import (Conflict, Document, EvidenceCard, ExpertEdit, LlmCall, Page, Project,
                        QualityCriterion, Thesis)

router = APIRouter(tags=["export"])
SCHEMA_VERSION = "0.1"  # TODO: сверить поля с выданным описанием JSON и задокументировать схему


def processing_report(s: Session, doc_ids: list[int]) -> dict:
    docs = []
    for d in s.query(Document).filter(Document.id.in_(doc_ids)):
        by_status = dict(s.query(Page.status, func.count()).filter_by(document_id=d.id).group_by(Page.status).all())
        docs.append({"document_id": d.id, "filename": d.filename, "status": d.status, "detail": d.status_detail,
                     "pages_total": d.page_count, "pages_by_status": by_status})
    tot = s.query(func.count(), func.coalesce(func.sum(LlmCall.input_tokens), 0),
                  func.coalesce(func.sum(LlmCall.output_tokens), 0), func.sum(LlmCall.cost_usd),
                  func.coalesce(func.sum(LlmCall.seconds), 0)).filter(LlmCall.document_id.in_(doc_ids)).one()
    return {"documents": docs, "llm": {"requests": tot[0], "input_tokens": int(tot[1]), "output_tokens": int(tot[2]),
                                       "cost_usd": tot[3], "seconds": float(tot[4])}}


def build_export(s: Session, pid: int) -> dict:
    project = s.get(Project, pid)
    if not project:
        raise HTTPException(404, "Проект не найден")
    docs = s.query(Document).filter_by(project_id=pid).all()
    ids = [d.id for d in docs] or [0]
    by_project = lambda model: [to_dict(r) for r in s.query(model).filter_by(project_id=pid)]  # noqa: E731
    return {
        "schema_version": SCHEMA_VERSION,
        "project": to_dict(project),
        "documents": [{k: v for k, v in to_dict(d).items() if k != "stored_path"} for d in docs],
        "evidence_cards": by_project(EvidenceCard),
        "recommendations": [{**to_dict(t), "card_ids": [c.id for c in t.cards]}
                            for t in s.query(Thesis).filter_by(project_id=pid)],
        "conflicts": by_project(Conflict),
        "quality_criteria": by_project(QualityCriterion),
        "expert_edits": by_project(ExpertEdit),
        "processing_report": processing_report(s, ids),
    }


@router.get("/projects/{pid}/export/json")
def export_json(pid: int, s: Session = Depends(get_session)):
    return build_export(s, pid)


@router.get("/projects/{pid}/report")
def report(pid: int, s: Session = Depends(get_session)):
    return build_export(s, pid)["processing_report"]


@router.get("/projects/{pid}/export/{fmt}")
def export_other(pid: int, fmt: str):
    raise HTTPException(501, f"Выгрузка «{fmt}» ещё не реализована")  # TODO: текст и Word (python-docx + шаблон)
