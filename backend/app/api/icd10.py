from fastapi import APIRouter, Query

from app.pipeline.icd10 import search_codes

router = APIRouter(tags=["reference data"])


@router.get("/icd10")
def find_icd10(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = False,
):
    return search_codes(q, limit, active_only=not include_inactive)
