import json
from pathlib import Path

import jsonschema
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_session, to_dict
from app.models import (
    Conflict,
    Document,
    EvidenceCard,
    ExpertEdit,
    LlmCall,
    Page,
    Project,
    SECTIONS,
    Thesis,
)
from app.pipeline.word_export import render_template_docx

router = APIRouter(tags=["export"])
SCHEMA_VERSION = "0.2"
SCHEMA = json.loads(
    (Path(__file__).parent.parent / "spec" / "kr_recommendation.schema.json").read_text(
        encoding="utf-8"
    )
)


def processing_report(s: Session, doc_ids: list[int]) -> dict:
    docs = []
    for d in s.query(Document).filter(Document.id.in_(doc_ids)):
        by_status = dict(
            s.query(Page.status, func.count())
            .filter_by(document_id=d.id)
            .group_by(Page.status)
            .all()
        )
        docs.append(
            {
                "document_id": d.id,
                "filename": d.filename,
                "status": d.status,
                "detail": d.status_detail,
                "pages_total": d.page_count,
                "pages_by_status": by_status,
            }
        )
    tot = (
        s.query(
            func.count(),
            func.coalesce(func.sum(LlmCall.input_tokens), 0),
            func.coalesce(func.sum(LlmCall.output_tokens), 0),
            func.sum(LlmCall.cost_usd),
            func.coalesce(func.sum(LlmCall.seconds), 0),
        )
        .filter(LlmCall.document_id.in_(doc_ids))
        .one()
    )
    return {
        "documents": docs,
        "llm": {
            "requests": tot[0],
            "input_tokens": int(tot[1]),
            "output_tokens": int(tot[2]),
            "cost_usd": tot[3],
            "seconds": float(tot[4]),
        },
    }


def clean(d: dict) -> dict:
    return {
        k: v for k, v in d.items() if v is not None
    }  # пропуски видны при проверке по схеме, а не как null


def card_status(c: EvidenceCard) -> str:
    if "failed" in (c.quote_verified, c.meaning_verified):
        return "conflicted"
    return (
        "verified"
        if c.quote_verified == c.meaning_verified == "verified"
        else "unverified"
    )


def build_kr(s: Session, pid: int) -> dict:
    """Документ строго по kr_recommendation.schema.json: kr_meta, evidence_units, recommendation_theses."""
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Проект не найден")
    docs = {d.id: d for d in s.query(Document).filter_by(project_id=pid)}
    units = []
    for c in s.query(EvidenceCard).filter_by(project_id=pid):
        if c.review_status == "rejected":
            continue
        d = docs[c.document_id]
        units.append(
            clean(
                {
                    "id": f"ev_{c.id}",
                    "subject": c.subject,
                    "predicate": c.predicate,
                    "object": c.object_,
                    "negation": c.negation,
                    "source": clean(
                        {
                            **(d.biblio or {}),
                            "title": (d.biblio or {}).get("title") or d.filename,
                            "study_design": d.study_design,
                        }
                    ),
                    "intervention_type": c.intervention_type,
                    "udd_source": c.udd_source,
                    "extraction_confidence": c.extraction_confidence,
                    "verification_status": card_status(c),
                    "verification_notes": "; ".join(c.problems or []),
                    "kr_section": c.kr_section,
                    "quote": c.quote,
                    "page": c.page_number,
                    "document_id": c.document_id,
                }
            )
        )
    theses = [
        clean(
            {
                "id": f"rec_{t.id}",
                "kr_section": t.section,
                "subsection_title": t.subsection_title,
                "statement": t.text,
                "direction": t.direction,
                "strength_phrase": t.strength_phrase,
                "intervention": t.intervention,
                "evidence_refs": [f"ev_{c.id}" for c in t.cards],
                "evidence_backed_core": t.evidence_backed_core,
                "expert_additions": t.expert_additions,
                "udd": t.udd,
                "uur": t.uur,
                "grade_rationale": t.grade_rationale,
                "consensus": t.consensus,
                "quality_criterion": t.quality_criterion,
                "icd_codes": p.icd_codes,
                "provenance": t.provenance,
                "review_flags": t.review_flags,
            }
        )
        for t in s.query(Thesis).filter_by(project_id=pid)
    ]
    meta = clean(
        {
            "title": p.title,
            "year": p.created_at.year if p.created_at else None,
            "icd_codes": p.icd_codes,
            "age_category": p.age_group,
            "developer_org": p.organization,
            "schema_version": SCHEMA_VERSION,
        }
    )
    return {"kr_meta": meta, "evidence_units": units, "recommendation_theses": theses}


def build_export(s: Session, pid: int) -> dict:
    """Расширенная выгрузка: документ по схеме и служебные данные проекта."""
    kr = build_kr(s, pid)
    docs = s.query(Document).filter_by(project_id=pid).all()
    ids = [d.id for d in docs] or [0]
    return {
        **kr,
        "documents": [
            {k: v for k, v in to_dict(d).items() if k != "stored_path"} for d in docs
        ],
        "conflicts": [to_dict(r) for r in s.query(Conflict).filter_by(project_id=pid)],
        "expert_edits": [
            to_dict(r) for r in s.query(ExpertEdit).filter_by(project_id=pid)
        ],
        "processing_report": processing_report(s, ids),
    }


@router.get("/projects/{pid}/export/validate")
def validate(pid: int, s: Session = Depends(get_session)):
    doc = json.loads(json.dumps(build_kr(s, pid), default=str))
    errors = sorted(
        jsonschema.Draft202012Validator(SCHEMA).iter_errors(doc),
        key=lambda e: list(map(str, e.path)),
    )
    return {
        "valid": not errors,
        "errors": [
            {"path": "/".join(map(str, e.path)), "message": e.message[:200]}
            for e in errors[:50]
        ],
    }


@router.get("/projects/{pid}/export/full")
def export_full(pid: int, s: Session = Depends(get_session)):
    return build_export(s, pid)


@router.get("/projects/{pid}/export/json")
def export_json(pid: int, s: Session = Depends(get_session)):
    return build_kr(s, pid)


def render_text(s: Session, pid: int) -> str:
    """Readable draft text with recommendation numbering and source markers."""
    project = s.get(Project, pid)
    if not project:
        raise HTTPException(404, "Проект не найден")
    lines = [project.title, ""]
    theses = s.query(Thesis).filter_by(project_id=pid).order_by(Thesis.id).all()
    grouped = {}
    for thesis in theses:
        grouped.setdefault(thesis.section, []).append(thesis)
    for section in sorted(SECTIONS, key=lambda x: tuple(int(p) for p in x.split("."))):
        lines.extend([f"{section} {SECTIONS[section]}", ""])
        for index, thesis in enumerate(grouped.get(section, []), start=1):
            refs = ", ".join(f"[ev_{card.id}]" for card in thesis.cards)
            grade = f"УДД {thesis.udd or 'н/д'}, УУР {thesis.uur or 'н/д'}"
            lines.append(f"{index}. {thesis.text} ({grade})" + (f" {refs}" if refs else ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


@router.get("/projects/{pid}/export/text")
def export_text(pid: int, s: Session = Depends(get_session)):
    return Response(
        render_text(s, pid),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="kr-{pid}.txt"'},
    )


@router.get("/projects/{pid}/export/docx")
def export_docx(pid: int, s: Session = Depends(get_session)):
    project = s.get(Project, pid)
    if not project:
        raise HTTPException(404, "Проект не найден")
    theses = s.query(Thesis).filter_by(project_id=pid).order_by(Thesis.id).all()
    sources = s.query(Document).filter_by(project_id=pid).order_by(Document.id).all()
    output = render_template_docx(project, theses, sources)
    return Response(
        output,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="kr-{pid}.docx"'},
    )


@router.get("/projects/{pid}/report")
def report(pid: int, s: Session = Depends(get_session)):
    return build_export(s, pid)["processing_report"]


@router.get("/projects/{pid}/export/{fmt}")
def export_other(pid: int, fmt: str):
    raise HTTPException(
        501, f"Выгрузка «{fmt}» ещё не реализована"
    )  # TODO: текст и Word (python-docx + шаблон)
