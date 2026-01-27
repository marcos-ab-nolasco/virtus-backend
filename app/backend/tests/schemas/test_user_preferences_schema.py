"""Tests for UserPreferences schema validation."""

import pytest
from pydantic import ValidationError

from src.schemas.user_preferences import UserPreferencesBase, UserPreferencesUpdate


def test_contact_frequency_validation_uppercase():
    """Test contact_frequency validates and returns UPPERCASE."""
    schema = UserPreferencesUpdate(contact_frequency="rarely")
    assert schema.contact_frequency == "RARELY"


def test_contact_frequency_validation_case_insensitive():
    """Test contact_frequency accepts various cases."""
    test_cases = ["rarely", "RARELY", "Rarely", "RaReLy"]

    for test_case in test_cases:
        schema = UserPreferencesUpdate(contact_frequency=test_case)
        assert schema.contact_frequency == "RARELY"


def test_contact_frequency_validation_all_values():
    """Test all valid ContactFrequency values."""
    valid_values = {
        "rarely": "RARELY",
        "sometimes": "SOMETIMES",
        "frequently": "FREQUENTLY",
    }

    for input_val, expected in valid_values.items():
        schema = UserPreferencesUpdate(contact_frequency=input_val)
        assert schema.contact_frequency == expected


def test_contact_frequency_validation_invalid_value():
    """Test contact_frequency rejects invalid values."""
    with pytest.raises(ValidationError) as exc_info:
        UserPreferencesUpdate(contact_frequency="INVALID")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "contact_frequency" in errors[0]["loc"]


def test_contact_frequency_optional_in_update():
    """Test contact_frequency is optional in UserPreferencesUpdate."""
    schema = UserPreferencesUpdate(timezone="UTC")
    assert schema.contact_frequency is None


def test_contact_frequency_default_in_base():
    """Test contact_frequency has default in UserPreferencesBase."""
    schema = UserPreferencesBase()
    assert schema.contact_frequency == "SOMETIMES"


def test_contact_frequency_in_update_with_other_fields():
    """Test contact_frequency can be updated alongside other fields."""
    schema = UserPreferencesUpdate(contact_frequency="rarely", timezone="America/Sao_Paulo")
    assert schema.contact_frequency == "RARELY"
    assert schema.timezone == "America/Sao_Paulo"
