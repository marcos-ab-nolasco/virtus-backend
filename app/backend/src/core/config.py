from functools import lru_cache
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_KNOWN_INSECURE_SECRETS: frozenset[str] = frozenset(
    {
        "change-this-to-a-random-secret-key-in-production",
        "generate-using-python-cryptography-fernet-generate-key",
    }
)

_SAFE_PRODUCTION_LOG_LEVELS: frozenset[str] = frozenset({"INFO", "WARNING", "ERROR", "CRITICAL"})


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: SecretStr

    # Redis
    REDIS_URL: SecretStr
    CACHE_PREFIX: str = "app_cache"

    # Security
    SECRET_KEY: SecretStr
    ENCRYPTION_KEY: SecretStr  # Fernet key for encrypting sensitive data (OAuth tokens, etc.)
    ALGORITHM: Literal["HS256", "RS256", "ES256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    REFRESH_TOKEN_COOKIE_SECURE: bool = False
    REFRESH_TOKEN_COOKIE_SAMESITE: Literal["lax", "strict", "none"] | None = "lax"
    REFRESH_TOKEN_COOKIE_DOMAIN: str | None = None

    # CORS
    CORS_ORIGINS: str

    # AI Providers
    OPENAI_API_KEY: SecretStr | None = None
    ANTHROPIC_API_KEY: SecretStr | None = None

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    FRONTEND_OAUTH_REDIRECT_URL: str

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 1

    # - Development -
    DEV_UVICORN_RELOAD: bool = False

    # Environment
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "DEBUG"

    @model_validator(mode="after")
    def _validate_production_security(self) -> "Settings":
        """Reject insecure configurations when ENVIRONMENT=production.

        Defaults stay permissive for local DX (HTTP dev). Production enforcement
        is centralized here so adding a new security variable is one `append`.
        """
        if self.ENVIRONMENT != "production":
            return self

        violations: list[str] = []

        if not self.REFRESH_TOKEN_COOKIE_SECURE:
            violations.append(
                "REFRESH_TOKEN_COOKIE_SECURE must be True in production "
                "(refresh cookie would be sent without the Secure flag over HTTP)"
            )

        if self.SECRET_KEY.get_secret_value() in _KNOWN_INSECURE_SECRETS:
            violations.append("SECRET_KEY is a placeholder from .env.example")

        encryption_key = self.ENCRYPTION_KEY.get_secret_value()
        if encryption_key in _KNOWN_INSECURE_SECRETS:
            violations.append("ENCRYPTION_KEY is a placeholder from .env.example")
        else:
            try:
                Fernet(encryption_key.encode())
            except (ValueError, TypeError):
                violations.append(
                    "ENCRYPTION_KEY is not a valid Fernet key "
                    "(must be 32 url-safe base64-encoded bytes)"
                )

        if self.LOG_LEVEL not in _SAFE_PRODUCTION_LOG_LEVELS:
            violations.append(
                f"LOG_LEVEL={self.LOG_LEVEL!r} may expose sensitive data in production "
                f"(allowed: {sorted(_SAFE_PRODUCTION_LOG_LEVELS)})"
            )

        if violations:
            raise ValueError("Insecure production configuration:\n  - " + "\n  - ".join(violations))
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
