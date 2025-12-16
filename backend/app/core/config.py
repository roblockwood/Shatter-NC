"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Shatter"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "shatter"
    POSTGRES_USER: str = "shatter_user"
    POSTGRES_PASSWORD: str = "changeme"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # CNC Polling
    DEFAULT_POLL_INTERVAL: int = 5  # seconds

    # Security (optional)
    SECRET_KEY: Optional[str] = None
    ENABLE_AUTH: bool = False

    # CORS
    # Can be set as JSON array in environment variable: ["*"] or ["http://example.com"]
    # Pydantic-settings will parse JSON strings automatically for list types
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",      # Development - Vite/React
        "http://localhost:5173",      # Development - Vite alternative port
        "http://localhost",           # Production - Nginx on port 80
        "http://localhost:80",        # Production - Nginx explicit port
        "*",                          # Allow all origins (use for testing/internal networks)
    ]

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables (like VITE_API_URL)


# Global settings instance
settings = Settings()
