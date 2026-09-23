"""Validated application settings with environment overrides for YAML defaults."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets belong in environment variables, never in YAML."""

    model_config = SettingsConfigDict(env_prefix="VDM_", env_file=".env", extra="forbid")

    app_name: str = "Virtual Dungeon Master"
    environment: str = "development"
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Let explicit environment variables override the configuration file."""
        return env_settings, dotenv_settings, init_settings, file_secret_settings


def load_settings(path: Path | None = None) -> Settings:
    """Load optional YAML defaults, then apply ``VDM_`` environment settings."""
    config_path = path or Path("vdm.yaml")
    if not config_path.exists():
        return Settings()
    raw: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"Settings file must contain a mapping: {config_path}")
    return Settings(**raw)
