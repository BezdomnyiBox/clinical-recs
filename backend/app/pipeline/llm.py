import time

from langchain_openai import ChatOpenAI

from app.config import settings
from app.db import SessionLocal
from app.models import LlmCall


def get_llm(max_tokens: int | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
        timeout=120,
        max_retries=2,
        max_tokens=max_tokens or settings.openrouter_max_tokens,
    )


def record_usage(job_id: int | None, document_id: int, step: str, msg, started: float):
    """Записать вызов модели (токены, время, стоимость). Стоимость OpenRouter отдаёт, если включён учёт usage."""
    usage = getattr(msg, "usage_metadata", None) or {}
    cost = (getattr(msg, "response_metadata", {}).get("token_usage") or {}).get("cost")
    with SessionLocal() as s:
        s.add(
            LlmCall(
                job_id=job_id,
                document_id=document_id,
                step=step,
                model=settings.openrouter_model,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cost_usd=cost,
                seconds=time.time() - started,
            )
        )
        s.commit()
