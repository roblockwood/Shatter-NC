"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Shatter"
    APP_VERSION: str = "0.12.2"
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

    # Min seconds between compressor_status_samples rows (MQTT + poll). 1 Hz matches sidecar operational publish cadence.
    COMPRESSOR_STATUS_SAMPLE_MIN_INTERVAL_SECONDS: float = Field(default=1.0, ge=0.1, le=5.0)
    # Raw hypertable retention window; older chart data comes from compressor_status_samples_1min (see DB migration 19).
    COMPRESSOR_STATUS_SAMPLES_RAW_DAYS: int = Field(default=14, ge=1, le=90)

    # CNC Polling
    DEFAULT_POLL_INTERVAL: int = 5  # seconds
    DEFAULT_TOOL_POLL_INTERVAL: int = 30  # seconds (tool table/ATC polling, separate from fast status polling)
    HEARTBEAT_INTERVAL_MINUTES: int = 2  # minutes between status/heartbeat log events when status unchanged

    # MQTT publish (optional) - publish full snapshots to Mosquitto.
    # Leave MQTT_PUBLISH_HOST unset/empty to disable publishing.
    MQTT_PUBLISH_HOST: Optional[str] = None
    MQTT_PUBLISH_PORT: int = 1883
    MQTT_PUBLISH_USERNAME: Optional[str] = None
    MQTT_PUBLISH_PASSWORD: Optional[str] = None
    MQTT_PUBLISH_TOPIC_PREFIX: str = "shatter"

    # Security (optional)
    SECRET_KEY: Optional[str] = None
    ENABLE_AUTH: bool = False

    # CORS
    # Can be set via environment variable as JSON array
    # Example: CORS_ORIGINS='["http://localhost:3000","*"]'
    # For production with dynamic IPs, use "*" to allow all origins
    # Note: When "*" is used, credentials must be disabled (browser security)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",      # Development - Vite/React
        "http://localhost:5173",      # Development - Vite alternative port
        "http://localhost",           # Production - Nginx on port 80
        "http://localhost:80",        # Production - Nginx explicit port
        "*",                          # Allow all origins (for production with dynamic IPs)
    ]

    # Timezone for interpreting CNC timestamps (e.g., PRD3) and for
    # default "local" views in history endpoints. This should be an
    # IANA timezone name.
    LOCAL_TIMEZONE: str = "America/Los_Angeles"

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables (like VITE_API_URL)
        # Allow JSON parsing for list fields like CORS_ORIGINS
        json_schema_extra = {
            "example": {
                "CORS_ORIGINS": '["http://localhost:3000","http://192.168.86.60","*"]'
            }
        }


# Global settings instance
settings = Settings()
