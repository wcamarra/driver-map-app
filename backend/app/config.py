from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py → repo root is two levels up
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _env_files() -> tuple[str, ...]:
    """Prefer repo-root .env (shared with Vite), then backend/.env, then cwd."""
    candidates = (_REPO_ROOT / ".env", _BACKEND_ROOT / ".env", Path(".env"))
    return tuple(str(p) for p in candidates if p.is_file()) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://drivermap:drivermap@localhost:5432/drivermap"
    database_url_sync: str = "postgresql://drivermap:drivermap@localhost:5432/drivermap"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    google_maps_api_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    directions_daily_quota: int = 500
    places_daily_quota: int = 200

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
