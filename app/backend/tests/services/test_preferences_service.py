"""Tests for preferences service layer.

Following TDD RED-GREEN-REFACTOR cycle:
- RED: Write failing tests first
- GREEN: Implement minimal code to pass
- REFACTOR: Clean up and improve
"""

import uuid
from datetime import time

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_preferences import CommunicationStyle, WeekDay
from src.schemas.user_preferences import UserPreferencesUpdate
from src.services import preferences as preferences_service


@pytest.mark.asyncio
async def test_get_user_preferences_success(db_session: AsyncSession, test_user: User):
    """Test getting user preferences successfully."""
    preferences = await preferences_service.get_user_preferences(db_session, test_user.id)

    assert preferences is not None
    assert preferences.user_id == test_user.id
    assert preferences.timezone == "UTC"  # Default


@pytest.mark.asyncio
async def test_get_user_preferences_not_found(db_session: AsyncSession):
    """Test getting preferences for non-existent user raises 404."""
    fake_user_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await preferences_service.get_user_preferences(db_session, fake_user_id)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_update_user_preferences_success(db_session: AsyncSession, test_user: User):
    """Test updating user preferences successfully."""
    update_data = UserPreferencesUpdate(
        timezone="America/Sao_Paulo",
        morning_checkin_time=time(7, 0),
        communication_style="gentle",
    )

    updated_prefs = await preferences_service.update_user_preferences(
        db_session, test_user.id, update_data
    )

    assert updated_prefs.timezone == "America/Sao_Paulo"
    assert updated_prefs.morning_checkin_time == time(7, 0)
    assert updated_prefs.communication_style == CommunicationStyle.GENTLE
    assert updated_prefs.user_id == test_user.id


@pytest.mark.asyncio
async def test_update_user_preferences_partial(db_session: AsyncSession, test_user: User):
    """Test partial update of user preferences."""
    # First update
    update_data_1 = UserPreferencesUpdate(
        timezone="Europe/London",
        coach_name="Athena",
    )
    await preferences_service.update_user_preferences(db_session, test_user.id, update_data_1)

    # Partial update (only timezone)
    update_data_2 = UserPreferencesUpdate(
        timezone="Asia/Tokyo",
    )
    updated_prefs = await preferences_service.update_user_preferences(
        db_session, test_user.id, update_data_2
    )

    assert updated_prefs.timezone == "Asia/Tokyo"
    assert updated_prefs.coach_name == "Athena"  # Unchanged


@pytest.mark.asyncio
async def test_update_user_preferences_checkin_settings(db_session: AsyncSession, test_user: User):
    """Test updating check-in settings."""
    update_data = UserPreferencesUpdate(
        morning_checkin_enabled=False,
        evening_checkin_enabled=True,
        evening_checkin_time=time(22, 30),
        weekly_review_day="saturday",
    )

    updated_prefs = await preferences_service.update_user_preferences(
        db_session, test_user.id, update_data
    )

    assert updated_prefs.morning_checkin_enabled is False
    assert updated_prefs.evening_checkin_enabled is True
    assert updated_prefs.evening_checkin_time == time(22, 30)
    assert updated_prefs.weekly_review_day == WeekDay.SATURDAY


@pytest.mark.asyncio
async def test_update_user_preferences_not_found(db_session: AsyncSession):
    """Test updating preferences for non-existent user raises 404."""
    fake_user_id = uuid.uuid4()
    update_data = UserPreferencesUpdate(timezone="UTC")

    with pytest.raises(HTTPException) as exc_info:
        await preferences_service.update_user_preferences(db_session, fake_user_id, update_data)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_user_preferences_empty_update(db_session: AsyncSession, test_user: User):
    """Test updating with no fields provided returns preferences unchanged."""
    # Get initial preferences
    initial_prefs = await preferences_service.get_user_preferences(db_session, test_user.id)
    initial_timezone = initial_prefs.timezone

    # Update with empty data
    update_data = UserPreferencesUpdate()
    updated_prefs = await preferences_service.update_user_preferences(
        db_session, test_user.id, update_data
    )

    assert updated_prefs.timezone == initial_timezone
    assert updated_prefs.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_user_preferences_returns_fresh_data(db_session: AsyncSession, test_user: User):
    """Test that get_user_preferences returns fresh data after update."""
    # Update preferences
    update_data = UserPreferencesUpdate(timezone="America/New_York")
    await preferences_service.update_user_preferences(db_session, test_user.id, update_data)

    # Get preferences again
    preferences = await preferences_service.get_user_preferences(db_session, test_user.id)

    assert preferences.timezone == "America/New_York"
