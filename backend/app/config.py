from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "NovelTTS Backend"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://noveltts:noveltts_dev@localhost:6543/noveltts"
    supabase_url: str = ""
    supabase_jwt_aud: str = "authenticated"

    model_config = SettingsConfigDict(
        # Prefer workspace root env files for a single-source local setup.
        env_file=(
            str(WORKSPACE_DIR / ".env.local"),
            str(WORKSPACE_DIR / ".env"),
            str(BACKEND_DIR / ".env.local"),
            str(BACKEND_DIR / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
