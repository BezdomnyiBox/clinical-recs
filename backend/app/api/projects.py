from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db import get_session, to_dict
from app.models import Project
from app.pipeline.icd10 import validate_codes

router = APIRouter(tags=["projects"])


class ProjectIn(BaseModel):
    title: str
    age_group: Literal["adults", "children", "mixed"] = "adults"
    icd_codes: list[str] = []
    organization: str = ""

    @field_validator("icd_codes")
    @classmethod
    def known_icd_codes(cls, value):
        try:
            return validate_codes(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


@router.get("/projects")
def list_projects(s: Session = Depends(get_session)):
    return [to_dict(p) for p in s.query(Project).order_by(Project.id.desc())]


@router.post("/projects")
def create_project(body: ProjectIn, s: Session = Depends(get_session)):
    p = Project(**body.model_dump())
    s.add(p)
    s.commit()
    return to_dict(p)


@router.get("/projects/{pid}")
def get_project(pid: int, s: Session = Depends(get_session)):
    p = s.get(Project, pid)
    if not p:
        raise HTTPException(404, "Проект не найден")
    return to_dict(p)
