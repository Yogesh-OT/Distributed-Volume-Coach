from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables prefixed DVC_, or from server/.env."""

    model_config = SettingsConfigDict(env_prefix="DVC_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    # "firebase" verifies Firebase ID tokens. "dev" accepts "Bearer dev:<anything>"
    # and must never be used on a server reachable from the internet.
    auth_mode: Literal["firebase", "dev"] = "firebase"
    # Production schemas come from Alembic. Tests and quick local runs can skip it.
    create_tables: bool = False
    # How far a check-in or max-test date may be from the user's local "today".
    date_tolerance_days: int = 1
