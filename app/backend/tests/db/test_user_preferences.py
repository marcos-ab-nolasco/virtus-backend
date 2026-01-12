import uuid
from datetime import datetime, time

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models.user import User
from src.db.models.user_preferences import CommunicationStyle, UserPreferences, WeekDay


@pytest.mark.asyncio
async def test_user_has_auto_created_preferences_with_defaults(
    db_session: AsyncSession, test_user: User
):
    """Test that UserPreferences is automatically created with default values when User is created."""
    # Query for the auto-created preferences
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    assert preferences.id is not None
    assert isinstance(preferences.id, uuid.UUID)
    assert preferences.user_id == test_user.id
    assert preferences.timezone == "UTC"
    assert preferences.morning_checkin_enabled is True
    assert preferences.morning_checkin_time == time(8, 0)
    assert preferences.evening_checkin_enabled is True
    assert preferences.evening_checkin_time == time(21, 0)
    assert preferences.weekly_review_day == WeekDay.SUNDAY
    assert preferences.communication_style == CommunicationStyle.DIRECT
    assert preferences.coach_name == "Virtus"
    assert isinstance(preferences.created_at, datetime)
    assert isinstance(preferences.updated_at, datetime)


@pytest.mark.asyncio
async def test_user_preferences_unique_constraint(db_session: AsyncSession, test_user: User):
    """Test that only one UserPreferences can exist per user."""
    # test_user already has auto-created preferences
    # Try to create a second preferences for the same user
    prefs2 = UserPreferences(user_id=test_user.id)
    db_session.add(prefs2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_user_preferences_relationship_with_user(db_session: AsyncSession, test_user: User):
    """Test that UserPreferences has a relationship with User."""
    # Get the auto-created preferences
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    # Access relationship
    assert preferences.user is not None
    assert preferences.user.id == test_user.id
    assert preferences.user.email == test_user.email


@pytest.mark.asyncio
async def test_user_preferences_cascade_delete(db_session: AsyncSession, test_user: User):
    """Test that deleting a User cascades to UserPreferences."""
    # Get the auto-created preferences
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()
    prefs_id = preferences.id

    # Delete the user
    await db_session.delete(test_user)
    await db_session.commit()

    # Verify preferences was also deleted
    result = await db_session.execute(select(UserPreferences).where(UserPreferences.id == prefs_id))
    deleted_prefs = result.scalar_one_or_none()
    assert deleted_prefs is None


@pytest.mark.asyncio
async def test_timezone_custom_value(db_session: AsyncSession, test_user: User):
    """Test setting a custom timezone."""
    # Get the auto-created preferences and update it
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    preferences.timezone = "America/Sao_Paulo"
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.timezone == "America/Sao_Paulo"


@pytest.mark.asyncio
async def test_checkin_time_defaults(db_session: AsyncSession, test_user: User):
    """Test default check-in times are set correctly in auto-created preferences."""
    # Get the auto-created preferences
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    assert preferences.morning_checkin_time == time(8, 0)
    assert preferences.evening_checkin_time == time(21, 0)


@pytest.mark.asyncio
async def test_checkin_time_custom_values(db_session: AsyncSession, test_user: User):
    """Test setting custom check-in times."""
    # Get the auto-created preferences and update it
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    preferences.morning_checkin_time = time(6, 30)
    preferences.evening_checkin_time = time(22, 15)
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.morning_checkin_time == time(6, 30)
    assert preferences.evening_checkin_time == time(22, 15)


@pytest.mark.asyncio
async def test_communication_style_enum(db_session: AsyncSession):
    """Test communication_style enum values."""
    for style in [
        CommunicationStyle.DIRECT,
        CommunicationStyle.GENTLE,
        CommunicationStyle.MOTIVATING,
    ]:
        # Create a new user (which auto-creates preferences)
        user = User(
            email=f"test_{style.value}@example.com",
            hashed_password=hash_password("testpassword123"),
            full_name=f"Test User {style.value}",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Get the auto-created preferences
        result = await db_session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user.id)
        )
        preferences = result.scalar_one()

        # Update the communication style
        preferences.communication_style = style
        await db_session.commit()
        await db_session.refresh(preferences)

        assert preferences.communication_style == style


@pytest.mark.asyncio
async def test_weekly_review_day_enum(db_session: AsyncSession):
    """Test weekly_review_day enum values."""
    # Test a few different days
    test_days = [WeekDay.MONDAY, WeekDay.FRIDAY, WeekDay.SUNDAY]

    for day in test_days:
        # Create a new user (which auto-creates preferences)
        user = User(
            email=f"test_{day.value}@example.com",
            hashed_password=hash_password("testpassword123"),
            full_name=f"Test User {day.value}",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Get the auto-created preferences
        result = await db_session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user.id)
        )
        preferences = result.scalar_one()

        # Update the weekly review day
        preferences.weekly_review_day = day
        await db_session.commit()
        await db_session.refresh(preferences)

        assert preferences.weekly_review_day == day


@pytest.mark.asyncio
async def test_coach_name_default(db_session: AsyncSession, test_user: User):
    """Test default coach name is 'Virtus' in auto-created preferences."""
    # Get the auto-created preferences
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    assert preferences.coach_name == "Virtus"


@pytest.mark.asyncio
async def test_coach_name_custom_value(db_session: AsyncSession, test_user: User):
    """Test setting a custom coach name."""
    # Get the auto-created preferences and update it
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    preferences.coach_name = "Athena"
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.coach_name == "Athena"


@pytest.mark.asyncio
async def test_checkin_enabled_flags(db_session: AsyncSession, test_user: User):
    """Test check-in enabled flags can be disabled."""
    # Get the auto-created preferences and update it
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    preferences.morning_checkin_enabled = False
    preferences.evening_checkin_enabled = False
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.morning_checkin_enabled is False
    assert preferences.evening_checkin_enabled is False


@pytest.mark.asyncio
async def test_update_preferences(db_session: AsyncSession, test_user: User):
    """Test updating UserPreferences fields."""
    # Get the auto-created preferences
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    # Update fields
    preferences.timezone = "Europe/London"
    preferences.morning_checkin_time = time(7, 0)
    preferences.communication_style = CommunicationStyle.GENTLE
    preferences.weekly_review_day = WeekDay.SATURDAY
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.timezone == "Europe/London"
    assert preferences.morning_checkin_time == time(7, 0)
    assert preferences.communication_style == CommunicationStyle.GENTLE
    assert preferences.weekly_review_day == WeekDay.SATURDAY
    assert preferences.updated_at > preferences.created_at


@pytest.mark.asyncio
async def test_user_preferences_requires_user_id(db_session: AsyncSession):
    """Test that UserPreferences requires a user_id."""
    preferences = UserPreferences()

    db_session.add(preferences)

    with pytest.raises(IntegrityError):
        await db_session.commit()


# Tests for new UserPreferences fields (M01 expansion)


@pytest.mark.asyncio
async def test_week_start_day_field(db_session: AsyncSession, test_user: User):
    """Test that UserPreferences has week_start_day field (separate from weekly_review_day)."""
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    # Should have week_start_day attribute
    assert hasattr(preferences, "week_start_day")

    # Should default to MONDAY
    assert preferences.week_start_day == WeekDay.MONDAY

    # Should be settable
    preferences.week_start_day = WeekDay.SUNDAY
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.week_start_day == WeekDay.SUNDAY


@pytest.mark.asyncio
async def test_language_field_default(db_session: AsyncSession, test_user: User):
    """Test that UserPreferences has language field with 'pt-BR' default."""
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    # Should have language attribute
    assert hasattr(preferences, "language")

    # Should default to "pt-BR"
    assert preferences.language == "pt-BR"


@pytest.mark.asyncio
async def test_language_field_custom_value(db_session: AsyncSession, test_user: User):
    """Test setting a custom language value."""
    result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == test_user.id)
    )
    preferences = result.scalar_one()

    # Should be settable to different languages
    preferences.language = "en-US"
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.language == "en-US"

    # Test other language codes
    preferences.language = "es-ES"
    await db_session.commit()
    await db_session.refresh(preferences)

    assert preferences.language == "es-ES"
