import os

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default_factory=lambda: os.environ["DATABASE_URL"])
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_max_tokens: int = 6000  # потолок ответа; OpenRouter резервирует под него кредиты
    upload_dir: str = "/data/uploads"


settings = Settings()
