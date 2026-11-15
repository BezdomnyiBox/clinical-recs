from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session, to_dict
from app.models import SECTIONS, Conflict, EvidenceCard, ExpertEdit, Thesis

router = APIRouter(tags=["review"])

CARD_FIELDS = {"statement_ru", "population", "intervention", "outcome", "conditions", "polarity", "review_status"}
THESIS_FIELDS = {"section", "text", "comment", "udd", "uur", "review_status"}


def apply_edits(s: Session, obj, kind: str, payload: dict, allowed: set[str]):
    """Правка пользователя. Оригинал автомата остаётся в auto_data, правка попадает в журнал и в user_edits.
    Повторная обработка не должна перезаписывать поля из user_edits: новая версия кладётся в pending_version."""
    edits = dict(obj.user_edits or {})
    for field, value in payload.items():
        if field not in allowed:
            raise HTTPException(400, f"Поле «{field}» нельзя менять")
        old = getattr(obj, field)
        if old == value:
            continue
        s.add(ExpertEdit(project_id=obj.project_id, entity_type=kind, entity_id=obj.id,
                         field=field, old_value=old, new_value=value))
        setattr(obj, field, value)
        edits[field] = value
    obj.user_edits = edits


@router.get("/projects/{pid}/cards")
def list_cards(pid: int, s: Session = Depends(get_session)):
    return [to_dict(c) for c in s.query(EvidenceCard).filter_by(project_id=pid).order_by(EvidenceCard.id)]


@router.patch("/cards/{cid}")
def patch_card(cid: int, payload: dict, s: Session = Depends(get_session)):
    c = s.get(EvidenceCard, cid)
    if not c:
        raise HTTPException(404, "Карточка не найдена")
    apply_edits(s, c, "card", payload, CARD_FIELDS)
    s.commit()
    return to_dict(c)


def thesis_dict(t: Thesis) -> dict:
    return {**to_dict(t), "card_ids": [c.id for c in t.cards]}


@router.get("/projects/{pid}/theses")
def list_theses(pid: int, s: Session = Depends(get_session)):
    return [thesis_dict(t) for t in s.query(Thesis).filter_by(project_id=pid).order_by(Thesis.id)]


class ExpertThesisIn(BaseModel):
    section: str
    text: str
    comment: str | None = None


@router.post("/projects/{pid}/theses")
def add_expert_thesis(pid: int, body: ExpertThesisIn, s: Session = Depends(get_session)):
    """Экспертный тезис: без цитаты и с явной отметкой происхождения."""
    if body.section not in SECTIONS:
        raise HTTPException(400, "Неизвестный раздел")
    t = Thesis(project_id=pid, origin="expert", review_status="confirmed", **body.model_dump())
    s.add(t)
    s.commit()
    return thesis_dict(t)


@router.patch("/theses/{tid}")
def patch_thesis(tid: int, payload: dict, s: Session = Depends(get_session)):
    t = s.get(Thesis, tid)
    if not t:
        raise HTTPException(404, "Тезис не найден")
    apply_edits(s, t, "thesis", payload, THESIS_FIELDS)
    s.commit()
    return thesis_dict(t)


@router.get("/projects/{pid}/conflicts")
def list_conflicts(pid: int, s: Session = Depends(get_session)):
    return [to_dict(c) for c in s.query(Conflict).filter_by(project_id=pid)]
