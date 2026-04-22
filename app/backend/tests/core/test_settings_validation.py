from typing import Any

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from src.core.config import Settings

_VALID_FERNET_KEY = Fernet.generate_key().decode()


def _prod_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ENVIRONMENT": "production",
        "REFRESH_TOKEN_COOKIE_SECURE": True,
        "SECRET_KEY": "x" * 48,
        "ENCRYPTION_KEY": _VALID_FERNET_KEY,
        "LOG_LEVEL": "INFO",
    }
    base.update(overrides)
    return base


def test_production_rejects_insecure_refresh_cookie() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(**_prod_kwargs(REFRESH_TOKEN_COOKIE_SECURE=False))

    assert "REFRESH_TOKEN_COOKIE_SECURE" in str(exc_info.value)


def test_production_accepts_fully_safe_config() -> None:
    settings = Settings(**_prod_kwargs())

    assert settings.ENVIRONMENT == "production"
    assert settings.REFRESH_TOKEN_COOKIE_SECURE is True
    assert settings.LOG_LEVEL == "INFO"


def test_production_rejects_placeholder_secret_key() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(**_prod_kwargs(SECRET_KEY="change-this-to-a-random-secret-key-in-production"))

    assert "SECRET_KEY" in str(exc_info.value)


def test_production_rejects_placeholder_encryption_key() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            **_prod_kwargs(ENCRYPTION_KEY="generate-using-python-cryptography-fernet-generate-key")
        )

    assert "ENCRYPTION_KEY" in str(exc_info.value)


def test_production_rejects_malformed_fernet_key() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(**_prod_kwargs(ENCRYPTION_KEY="not-a-valid-fernet-key"))

    assert "ENCRYPTION_KEY" in str(exc_info.value)
    assert "Fernet" in str(exc_info.value)


def test_production_rejects_debug_log_level() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(**_prod_kwargs(LOG_LEVEL="DEBUG"))

    assert "LOG_LEVEL" in str(exc_info.value)


def test_production_rejects_unknown_log_level() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(**_prod_kwargs(LOG_LEVEL="VERBOSE"))

    assert "LOG_LEVEL" in str(exc_info.value)


def test_production_accumulates_multiple_violations() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            **_prod_kwargs(
                REFRESH_TOKEN_COOKIE_SECURE=False,
                SECRET_KEY="change-this-to-a-random-secret-key-in-production",
                LOG_LEVEL="DEBUG",
            )
        )

    message = str(exc_info.value)
    assert "REFRESH_TOKEN_COOKIE_SECURE" in message
    assert "SECRET_KEY" in message
    assert "LOG_LEVEL" in message


def test_development_permissive_default() -> None:
    settings = Settings(ENVIRONMENT="development", REFRESH_TOKEN_COOKIE_SECURE=False)

    assert settings.REFRESH_TOKEN_COOKIE_SECURE is False


def test_development_allows_debug_log_level() -> None:
    settings = Settings(ENVIRONMENT="development", LOG_LEVEL="DEBUG")

    assert settings.LOG_LEVEL == "DEBUG"


def test_test_environment_permissive() -> None:
    settings = Settings(ENVIRONMENT="test", REFRESH_TOKEN_COOKIE_SECURE=False)

    assert settings.REFRESH_TOKEN_COOKIE_SECURE is False


def test_invalid_environment_value_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="testing")

    assert "ENVIRONMENT" in str(exc_info.value)


def test_invalid_algorithm_value_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(ALGORITHM="HS257")

    assert "ALGORITHM" in str(exc_info.value)
