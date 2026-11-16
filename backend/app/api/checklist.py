import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ChecklistAnswer, Project

router = APIRouter(tags=["reference data"])
CHECKLIST = json.loads(
    (Path(__file__).parent.parent / "spec" / "official_checklist.json").read_text(
        encoding="utf-8"
    )
)


@router.get("/checklist")
def get_checklist():
    return CHECKLIST


@router.get("/projects/{pid}/checklist")
def project_checklist(pid: int, s: Session = Depends(get_session)):
    if not s.get(Project, pid):
        raise HTTPException(404, "Проект не найден")
    answers = {
        answer.item_id: answer
        for answer in s.query(ChecklistAnswer).filter_by(project_id=pid)
    }
    return {
        **CHECKLIST,
        "items": [
            {
                **item,
                "response": answers[item["id"]].response if item["id"] in answers else "unreviewed",
                "comment": answers[item["id"]].comment if item["id"] in answers else "",
            }
            for item in CHECKLIST["items"]
        ],
    }


class ChecklistAnswerIn(BaseModel):
    response: Literal["unreviewed", "yes", "no", "not_applicable"]
    comment: str = ""


@router.put("/projects/{pid}/checklist/{item_id}")
def save_checklist_answer(
    pid: int, item_id: str, body: ChecklistAnswerIn, s: Session = Depends(get_session)
):
    if not s.get(Project, pid):
        raise HTTPException(404, "Проект не найден")
    if not any(item["id"] == item_id for item in CHECKLIST["items"]):
        raise HTTPException(404, "Пункт чек-листа не найден")
    answer = s.query(ChecklistAnswer).filter_by(project_id=pid, item_id=item_id).first()
    if answer is None:
        answer = ChecklistAnswer(project_id=pid, item_id=item_id)
        s.add(answer)
    answer.response, answer.comment = body.response, body.comment
    s.commit()
    return {"item_id": item_id, "response": answer.response, "comment": answer.comment}
