"""Application configuration using Pydantic settings."""
from typing import List, Union
from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Auth API Service"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    #Environment tracking
    env: str = "development"

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Database
    database_url: str

    # Redis
    redis_url: str
    redis_session_prefix: str = "session:"
    redis_session_expire_seconds: int = 1800

    # CORS
    # Using Union[List[str], str] helps type checkers understand it starts as a string
    cors_origins: Union[List[str], str] = ["http://localhost:3000", "http://localhost:8000"]

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list, handling whitespace and quotes."""
        if isinstance(v, str):
            # Handles: "['url1', 'url2']", "url1, url2", or "[url1, url2]"
            return [
                item.strip().strip("'").strip('"')
                for item in v.strip("[]").split(",")
                if item.strip()
            ]
        return v

# Global settings instance
settings = Settings()