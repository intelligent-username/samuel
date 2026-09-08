from pydantic import Field, field_validator
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
    groq_api_key: str = ""
    ats_provider: str = Field(
        default="llm", validation_alias="ATS_PROVIDER", description="ATS_PROVIDER env"
    )
    ats_max_iterations: int = Field(default=6, ge=5, le=7)
    ats_stagnation_window: int = Field(default=3, ge=1, le=5)
    ats_min_gain: float = Field(default=0.03, ge=0.0, le=1.0)
    ats_threshold_default: int = Field(default=80, ge=0, le=100)

    @field_validator("ats_provider", mode="before")
    @classmethod
    def _lower_provider(cls, v: str | None) -> str:
        return str(v).lower().strip() if v else "llm"

    @field_validator("ats_max_iterations", mode="before")
    @classmethod
    def _clamp_iter(cls, v: int | str | None) -> int:
        if v is None:
            return 6
        try:
            iv = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 6
        return max(5, min(7, iv))

    @property
    def openrouter_key(self) -> str:
        """Alias for openrouter_api_key for backwards compatibility."""
        return self.openrouter_api_key

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
