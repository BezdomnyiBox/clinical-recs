from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.pipeline.metrics import evaluate

router = APIRouter(tags=["evaluation"])


class EvaluationIn(BaseModel):
    gold: list[dict] = Field(description="Эталонные карточки с action/population/conditions/direction/numbers")
    predicted: list[dict] = Field(description="Предсказанные карточки в том же формате")


@router.post("/evaluation/metrics")
def evaluate_metrics(payload: EvaluationIn):
    return evaluate(payload.gold, payload.predicted)
