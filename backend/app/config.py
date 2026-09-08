from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local AI Keycap Configurator"
    frontend_origin: str = "http://localhost:5173"
    data_dir: str = "./data"
    database_path: str = "./data/products.db"
    scraper_provider: Literal["playwright", "firecrawl"] = "playwright"
    firecrawl_api_key: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
