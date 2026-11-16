import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session, to_dict
from app.models import Document, Job, Page, Project

router = APIRouter(tags=["documents"])


@router.post("/projects/{pid}/documents")
def upload(pid: int, files: list[UploadFile], s: Session = Depends(get_session)):
    if not s.get(Project, pid):
        raise HTTPException(404, "Проект не найден")
    docs = []
    for f in files:
        if not (f.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"{f.filename}: нужен файл PDF")
        data = f.file.read()
        digest = hashlib.sha256(data).hexdigest()
        orig = (
            s.query(Document)
            .filter_by(project_id=pid, content_hash=digest, duplicate_of_id=None)
            .first()
        )
        if orig:  # точный дубликат не обрабатывается: иначе одна статья посчитается двумя источниками
            d = Document(
                project_id=pid,
                filename=f.filename,
                stored_path=orig.stored_path,
                content_hash=digest,
                duplicate_of_id=orig.id,
                status="duplicate",
                status_detail=f"Совпадает с файлом «{orig.filename}», повторно не обрабатывается",
            )
            s.add(d)
            docs.append(d)
            continue
        path = Path(settings.upload_dir) / f"{uuid.uuid4().hex}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        d = Document(
            project_id=pid,
            filename=f.filename,
            stored_path=str(path),
            content_hash=digest,
        )
        s.add(d)
        s.flush()
        s.add(Job(kind="process_document", document_id=d.id))
        docs.append(d)
    s.commit()
    return [to_dict(d) for d in docs]


@router.get("/projects/{pid}/documents")
def list_documents(pid: int, s: Session = Depends(get_session)):
    return [
        to_dict(d)
        for d in s.query(Document).filter_by(project_id=pid).order_by(Document.id)
    ]


@router.get("/documents/{did}/pages")
def list_pages(did: int, s: Session = Depends(get_session)):
    return [
        {"number": p.number, "status": p.status, "error": p.error, "chars": len(p.text)}
        for p in s.query(Page).filter_by(document_id=did).order_by(Page.number)
    ]


@router.get("/documents/{did}/file")
def get_file(did: int, s: Session = Depends(get_session)):
    d = s.get(Document, did)
    if not d:
        raise HTTPException(404, "Документ не найден")
    return FileResponse(
        d.stored_path,
        media_type="application/pdf",
        filename=d.filename,
        content_disposition_type="inline",
    )


@router.post("/documents/{did}/reprocess")
def reprocess(did: int, force: bool = False, s: Session = Depends(get_session)):
    d = s.get(Document, did)
    if not d:
        raise HTTPException(404, "Документ не найден")
    if d.duplicate_of_id:
        raise HTTPException(400, "Дубликат не обрабатывается")
    d.status, d.status_detail = "queued", None
    if (
        force
    ):  # пользователь настаивает на обработке, даже если источник признан нерелевантным
        d.relevance = "forced"
    s.add(Job(kind="process_document", document_id=did))
    s.commit()
    return to_dict(d)
