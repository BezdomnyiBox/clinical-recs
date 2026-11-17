import os
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default_factory=lambda: os.environ["DATABASE_URL"])
    llm_provider: Literal["openrouter", "iacpaas"] = "openrouter"
    iacpaas_api_key: str = ""
    iacpaas_base_url: str = "https://aichat.iacpaas.dvo.ru/api"
    iacpaas_model: str = "qwen3.8-27b"
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    llm_max_tokens: int = Field(
        default=6000,
        validation_alias=AliasChoices("LLM_MAX_TOKENS", "OPENROUTER_MAX_TOKENS"),
    )
    upload_dir: str = "/data/uploads"

    @property
    def active_llm_api_key(self) -> str:
        if self.llm_provider == "iacpaas":
            return self.iacpaas_api_key
        return self.openrouter_api_key

    @property
    def active_llm_base_url(self) -> str:
        if self.llm_provider == "iacpaas":
            return self.iacpaas_base_url
        return "https://openrouter.ai/api/v1"

    @property
    def active_llm_model(self) -> str:
        if self.llm_provider == "iacpaas":
            return self.iacpaas_model
        return self.openrouter_model

    @property
    def active_llm_extra_body(self) -> dict:
        if self.llm_provider == "iacpaas":
            return {
                "top_k": 20,
                "min_p": 0.0,
                "repetition_penalty": 1.0,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        return {"usage": {"include": True}}


settings = Settings()
