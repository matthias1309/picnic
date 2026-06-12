"""
Configuration for Picnic Expense Tracker backend.

Loads settings from .env file using Pydantic Settings v2.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables (.env)."""

    # IMAP Configuration
    imap_host: str = "localhost"
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_mailbox: str = "INBOX"
    imap_use_ssl: bool = True

    # Polling Configuration
    polling_interval: int = 1800  # 30 minutes in seconds

    # Database Configuration
    database_url: str = "sqlite:///./picnic.db"

    # Application Configuration
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # CORS Configuration (for frontend)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
