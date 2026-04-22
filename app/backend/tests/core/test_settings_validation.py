import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_production_rejects_insecure_refresh_cookie() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="production", REFRESH_TOKEN_COOKIE_SECURE=False)

    assert "REFRESH_TOKEN_COOKIE_SECURE" in str(exc_info.value)


def test_production_accepts_secure_refresh_cookie() -> None:
    settings = Settings(ENVIRONMENT="production", REFRESH_TOKEN_COOKIE_SECURE=True)

    assert settings.ENVIRONMENT == "production"
    assert settings.REFRESH_TOKEN_COOKIE_SECURE is True


def test_development_permissive_default() -> None:
    settings = Settings(ENVIRONMENT="development", REFRESH_TOKEN_COOKIE_SECURE=False)

    assert settings.REFRESH_TOKEN_COOKIE_SECURE is False


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
