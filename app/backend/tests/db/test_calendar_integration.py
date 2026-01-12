"""Tests for CalendarIntegration model."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.encryption import decrypt_token, encrypt_token
from src.core.security import hash_password
from src.db.models.calendar_integration import (
    CalendarIntegration,
    CalendarProvider,
    IntegrationStatus,
)
from src.db.models.user import User


@pytest.mark.asyncio
async def test_calendar_integration_creation(db_session: AsyncSession, test_user: User):
    """Test creating a calendar integration."""
    integration = CalendarIntegration(
        user_id=test_user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ACTIVE,
        access_token=encrypt_token("test_access_token"),
        refresh_token=encrypt_token("test_refresh_token"),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly", "calendar.events"],
        sync_enabled=True,
    )

    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)

    assert integration.id is not None
    assert integration.user_id == test_user.id
    assert integration.provider == CalendarProvider.GOOGLE_CALENDAR
    assert integration.status == IntegrationStatus.ACTIVE
    assert integration.sync_enabled is True


@pytest.mark.asyncio
async def test_calendar_integration_token_encryption(db_session: AsyncSession, test_user: User):
    """Test that tokens are encrypted when stored."""
    original_access = "my_secret_access_token_12345"
    original_refresh = "my_secret_refresh_token_67890"

    integration = CalendarIntegration(
        user_id=test_user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ACTIVE,
        access_token=encrypt_token(original_access),
        refresh_token=encrypt_token(original_refresh),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly"],
    )

    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)

    # Tokens should be encrypted (different from original)
    assert integration.access_token != original_access
    assert integration.refresh_token != original_refresh

    # But should decrypt back to original
    decrypted_access = decrypt_token(integration.access_token)
    decrypted_refresh = decrypt_token(integration.refresh_token)

    assert decrypted_access == original_access
    assert decrypted_refresh == original_refresh


@pytest.mark.asyncio
async def test_calendar_integration_unique_per_user_provider(
    db_session: AsyncSession, test_user: User
):
    """Test that a user can have only one integration per provider."""
    # Create first integration
    integration1 = CalendarIntegration(
        user_id=test_user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ACTIVE,
        access_token=encrypt_token("token1"),
        refresh_token=encrypt_token("refresh1"),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly"],
    )
    db_session.add(integration1)
    await db_session.commit()

    # Try to create second integration for same user+provider (should fail)
    integration2 = CalendarIntegration(
        user_id=test_user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ACTIVE,
        access_token=encrypt_token("token2"),
        refresh_token=encrypt_token("refresh2"),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly"],
    )
    db_session.add(integration2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_calendar_integration_cascade_delete_user(db_session: AsyncSession):
    """Test that deleting a user cascades to calendar integrations."""
    # Create a user
    user = User(
        email="cascade_test@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Cascade Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create an integration
    integration = CalendarIntegration(
        user_id=user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ACTIVE,
        access_token=encrypt_token("token"),
        refresh_token=encrypt_token("refresh"),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly"],
    )
    db_session.add(integration)
    await db_session.commit()

    integration_id = integration.id

    # Delete the user
    await db_session.delete(user)
    await db_session.commit()

    # Integration should be deleted too
    result = await db_session.execute(
        select(CalendarIntegration).where(CalendarIntegration.id == integration_id)
    )
    deleted_integration = result.scalar_one_or_none()
    assert deleted_integration is None


@pytest.mark.asyncio
async def test_calendar_provider_enum_values():
    """Test CalendarProvider enum values."""
    assert CalendarProvider.GOOGLE_CALENDAR == "GOOGLE_CALENDAR"
    assert CalendarProvider.OUTLOOK == "OUTLOOK"
    assert CalendarProvider.APPLE_CALENDAR == "APPLE_CALENDAR"
    assert len(CalendarProvider) == 3


@pytest.mark.asyncio
async def test_integration_status_enum_values():
    """Test IntegrationStatus enum values."""
    assert IntegrationStatus.PENDING == "PENDING"
    assert IntegrationStatus.ACTIVE == "ACTIVE"
    assert IntegrationStatus.TOKEN_EXPIRED == "TOKEN_EXPIRED"
    assert IntegrationStatus.ERROR == "ERROR"
    assert IntegrationStatus.DISCONNECTED == "DISCONNECTED"
    assert len(IntegrationStatus) == 5


@pytest.mark.asyncio
async def test_calendar_integration_calendars_synced_jsonb(
    db_session: AsyncSession, test_user: User
):
    """Test storing calendars_synced JSONB data."""
    calendars_config = [
        {
            "calendar_id": "primary",
            "calendar_name": "Work",
            "color": "#FF0000",
            "include_in_planning": True,
        },
        {
            "calendar_id": "secondary",
            "calendar_name": "Personal",
            "color": "#00FF00",
            "include_in_planning": False,
        },
    ]

    integration = CalendarIntegration(
        user_id=test_user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ACTIVE,
        access_token=encrypt_token("token"),
        refresh_token=encrypt_token("refresh"),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly"],
        calendars_synced=calendars_config,
    )

    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)

    assert integration.calendars_synced is not None
    assert len(integration.calendars_synced) == 2
    assert integration.calendars_synced[0]["calendar_name"] == "Work"
    assert integration.calendars_synced[1]["color"] == "#00FF00"


@pytest.mark.asyncio
async def test_calendar_integration_sync_error_field(db_session: AsyncSession, test_user: User):
    """Test storing sync error messages."""
    integration = CalendarIntegration(
        user_id=test_user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ERROR,
        access_token=encrypt_token("token"),
        refresh_token=encrypt_token("refresh"),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly"],
        sync_error="Invalid credentials",
    )

    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)

    assert integration.sync_error == "Invalid credentials"
    assert integration.status == IntegrationStatus.ERROR
