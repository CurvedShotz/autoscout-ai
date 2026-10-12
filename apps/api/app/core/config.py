from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, List

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AutoScout AI API")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://danielolowe.com",
        ]
    )
    auto_dev_api_key: SecretStr = Field(
        ...,
        validation_alias=AliasChoices("AUTO_DEV_API_KEY", "auto_dev_api_key"),
        description="Auto.dev API key used for external request authorization.",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
        description="OpenAI API key used for vehicle ranking.",
    )
    openai_ranking_model: str = Field(default="gpt-5-nano")
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "gemini_api_key"),
        description="Gemini API key used for vehicle ranking.",
    )
    gemini_ranking_model: str = Field(default="gemini-3.5-flash-lite")
    ai_ranking_provider: str = Field(default="gemini")
    auto_dev_search_distance_miles: int = Field(default=50, ge=1)
    location_geocoder_base_url: str = Field(
        default="https://nominatim.openstreetmap.org"
    )
    location_geocoder_user_agent: str = Field(
        default="AutoScoutAI/1.0 (https://danielolowe.com/autoscout/)"
    )
    search_rate_limit_requests: int = Field(default=10, ge=1)
    search_rate_limit_window_seconds: int = Field(default=60, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> List[str]:
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value.split(",")
            if isinstance(parsed_value, list):
                value = parsed_value
            elif isinstance(parsed_value, str):
                value = [parsed_value]
            else:
                raise ValueError("CORS_ORIGINS must be a comma-separated list")

        if not isinstance(value, list):
            raise ValueError("CORS_ORIGINS must be a list")

        origins = [str(origin).strip().rstrip("/") for origin in value]
        origins = [origin for origin in origins if origin]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must not contain a wildcard origin")
        return origins

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
