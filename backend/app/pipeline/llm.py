from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import settings


def get_llm(max_tokens: int | None = None) -> ChatOpenAI:
    if not settings.active_llm_api_key.strip():
        key_name = (
            "IACPAAS_API_KEY"
            if settings.llm_provider == "iacpaas"
            else "OPENROUTER_API_KEY"
        )
        raise ValueError(f"Не задан ключ API модели: {key_name}")
    return ChatOpenAI(
        model=settings.active_llm_model,
        api_key=SecretStr(settings.active_llm_api_key),
        base_url=settings.active_llm_base_url,
        temperature=0,
        timeout=120,
        max_retries=2,
        max_tokens=max_tokens or settings.llm_max_tokens,
        extra_body=settings.active_llm_extra_body,
    )
