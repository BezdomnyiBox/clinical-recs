from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import settings


def get_llm(max_tokens: int | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openrouter_model,
        api_key=SecretStr(settings.openrouter_api_key),
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
        timeout=120,
        max_retries=2,
        max_completion_tokens=max_tokens or settings.openrouter_max_tokens,
        extra_body={"usage": {"include": True}},
    )
