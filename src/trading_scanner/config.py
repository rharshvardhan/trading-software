"""Environment configuration. Credentials live only in the local environment or .env."""

from __future__ import annotations

from pathlib import Path

from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGED_FIXTURE_DIR = Path(__file__).resolve().parent / "fixture_data"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # The project .env is found from any working directory (pnpm dev starts the API from frontend/);
    # a .env in the current directory, if any, takes precedence.
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", ".env"), env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    fixture_dir: Path | None = Field(default=None, alias="SCANNER_FIXTURE_DIR")
    data_dir: Path | None = Field(default=None, alias="SCANNER_DATA_DIR")
    ui_dir: Path | None = Field(default=None, alias="SCANNER_UI_DIR")
    dhan_client_id: SecretStr | None = Field(default=None, alias="DHAN_CLIENT_ID")
    dhan_access_token: SecretStr | None = Field(default=None, alias="DHAN_ACCESS_TOKEN")

    @field_validator("fixture_dir", "data_dir", "ui_dir", "dhan_client_id", "dhan_access_token", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: Any) -> Any:
        """Blank lines copied from .env.example mean "not set"."""
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def resolved_fixture_dir(self) -> Path:
        return self.fixture_dir if self.fixture_dir else PACKAGED_FIXTURE_DIR

    @property
    def resolved_data_dir(self) -> Path:
        """Local, git-ignored cache (for example Dhan's daily instrument list)."""
        return self.data_dir if self.data_dir else PROJECT_ROOT / "data"

    @property
    def resolved_ui_dir(self) -> Path:
        """Built web UI served at / (frontend/dist after `pnpm build`)."""
        return self.ui_dir if self.ui_dir else PROJECT_ROOT / "frontend" / "dist"

    @property
    def dhan_configured(self) -> bool:
        return all(
            secret is not None and secret.get_secret_value().strip()
            for secret in (self.dhan_client_id, self.dhan_access_token)
        )
