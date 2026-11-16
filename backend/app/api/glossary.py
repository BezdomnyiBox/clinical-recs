import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["glossary"])
GLOSSARY = json.loads(
    (Path(__file__).parent.parent / "spec" / "glossary.json").read_text(
        encoding="utf-8"
    )
)


@router.get("/glossary")
def glossary():
    return GLOSSARY
