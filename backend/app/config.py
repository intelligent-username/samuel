from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://samuel:samuel_dev_only@localhost:5432/samuel"
    github_client_id: str = ""
    github_client_secret: str = ""
    session_secret: str = "change-me-in-production"
    encryption_key: str = "change-me-in-production"
    log_level: str = "INFO"
    debug_dir: str = "/tmp/samuel/debug"
    debug_retention_hours: int = 24
    secure_cookie: bool = False
    openrouter_api_key: str = ""
    openrouter_key: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()