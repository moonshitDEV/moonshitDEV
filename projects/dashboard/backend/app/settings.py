from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DASH_", env_file=None, extra="ignore")

    # Environment and app
    env: Literal["dev", "prod", "test"] = Field(default="dev", env="ENV")
    app_name: str = Field(default="dash-api", env="APP_NAME")
    secret_key: str = Field(default="dev-insecure-secret", env="SECRET_KEY")

    # Networking
    host: str = Field(default="127.0.0.1", env="HOST")
    port: int = Field(default=8000, env="PORT")
    api_root: str = Field(default="/api/v1", env="API_ROOT")

    # Rates and uploads
    rate_default: str = Field(default="60/minute", env="RATE_DEFAULT")
    upload_max_mb: int = Field(default=50, env="UPLOAD_MAX_MB")
    upload_unrestricted: bool = Field(default=True, env="UPLOAD_UNRESTRICTED")

    # Admin credentials
    admin_user: str = Field(default="admin", env="ADMIN_USER")
    admin_pass_hash: Optional[str] = Field(default=None, env="ADMIN_PASS_HASH")

    # Files
    data_root: Path = Field(default=Path("/srv/dash-data"), env="DATA_ROOT")

    # CORS
    cors_origin: Optional[str] = Field(default=None, env="CORS_ORIGIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # reads env vars prefixed with DASH_
