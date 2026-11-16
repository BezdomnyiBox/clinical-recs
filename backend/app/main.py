from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import checklist, documents, evaluation, export, glossary, icd10, projects, review
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Черновик клинических рекомендаций", lifespan=lifespan)
for module in (projects, documents, review, export, glossary, evaluation, icd10, checklist):
    app.include_router(module.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
