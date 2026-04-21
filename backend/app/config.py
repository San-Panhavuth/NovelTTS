from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NovelTTS Backend"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://noveltts:noveltts_dev@localhost:5432/noveltts"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
