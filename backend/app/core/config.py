from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # FastF1
    fastf1_cache_dir: str = "./cache"

    # OpenF1
    openf1_ws_url: str = "wss://api.openf1.org/streaming"
    openf1_rest_url: str = "https://api.openf1.org"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()