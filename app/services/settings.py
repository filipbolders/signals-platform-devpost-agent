from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8030

    demo_mode: bool = True

    restricted_api_token: str = Field(
        default="devpost-local-demo-token",
        min_length=16,
    )

    signals_platform_base_url: str = (
        "http://127.0.0.1:8030/api/devpost/v1"
    )
    signals_platform_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        le=60,
    )


settings = Settings()
