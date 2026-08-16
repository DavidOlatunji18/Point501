from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"
    sleeper_api_base_url: str = "https://api.sleeper.app/v1"
    nfl_season: str = "2025"
    database_url: str = "sqlite:///./fantasy_football.db"
    chroma_persist_dir: str = "./chroma_data"
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
