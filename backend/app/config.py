from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    upload_dir: str = "/data/uploads"


settings = Settings()
