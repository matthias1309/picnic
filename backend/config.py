"""
Configuration for Picnic Expense Tracker backend.

Loads settings from .env file using Pydantic Settings v2.
"""

from pydantic_settings import BaseSettings


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

    # Receipt Parsing Configuration
    parse_interval: int = 1800  # 30 minutes in seconds

    # Database Configuration
    database_url: str = "sqlite:///./picnic.db"

    # Application Configuration
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # CORS Configuration (for frontend), as a comma-separated list of origins
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Statistics Configuration
    monthly_budget_cents: int = 0

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed CORS origins, split from the comma-separated setting."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Whether the app is running in production.

        Security-sensitive behavior (cookie `Secure` flag, API docs exposure)
        is gated on this rather than `debug`, so a misconfigured `DEBUG` value
        cannot accidentally weaken it.
        """
        return self.environment.lower() == "production"

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
