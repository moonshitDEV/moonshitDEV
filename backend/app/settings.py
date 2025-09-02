from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DASH_", env_file=None, extra="ignore")

    # Environment and app
    env: Literal["dev", "prod", "test"] = Field(default="dev", alias="ENV")
    app_name: str = Field(default="dash-api", alias="APP_NAME")
    secret_key: str = Field(default="dev-insecure-secret", alias="SECRET_KEY")

    # Networking
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    api_root: str = Field(default="/api/v1", alias="API_ROOT")

    # Rates and uploads
    rate_default: str = Field(default="60/minute", alias="RATE_DEFAULT")
    upload_max_mb: int = Field(default=50, alias="UPLOAD_MAX_MB")
    upload_unrestricted: bool = Field(default=True, alias="UPLOAD_UNRESTRICTED")

    # Admin credentials
    admin_user: str = Field(default="admin", alias="ADMIN_USER")
    admin_pass_hash: Optional[str] = Field(default=None, alias="ADMIN_PASS_HASH")

    # Files
    data_root: Path = Field(default=Path("/srv/dash-data"), alias="DATA_ROOT")

    # CORS
    cors_origin: Optional[str] = Field(default=None, alias="CORS_ORIGIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # reads env vars prefixed with DASH_
