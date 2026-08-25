from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "RoadBuddy API"
    database_url: str = "postgresql+psycopg://roadbuddy:roadbuddy@localhost:5432/roadbuddy"
    ors_api_key: str | None = None
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    allowed_origins: str = "http://localhost:5173"
    use_mock_data: bool = False
    request_timeout_seconds: float = Field(default=12.0, gt=0, le=30)

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
