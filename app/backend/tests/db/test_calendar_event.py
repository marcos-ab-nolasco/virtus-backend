"""Tests for CalendarEvent model."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.encryption import encrypt_token
from src.db.models.calendar_event import CalendarEvent, EventType
from src.db.models.calendar_integration import (
    CalendarIntegration,
    CalendarProvider,
    IntegrationStatus,
)
from src.db.models.user import User


@pytest.mark.asyncio
async def test_calendar_event_creation(
    db_session: AsyncSession, test_user: User, test_calendar_integration: CalendarIntegration
):
    """Test creating a calendar event."""
    event = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_123_google",
        title="Team Meeting",
        description="Discuss Q1 objectives",
        location="Conference Room A",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        is_all_day=False,
        calendar_id="primary",
        calendar_name="Work Calendar",
        event_type=EventType.MEETING,
        is_recurring=False,
    )

    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.id is not None
    assert event.integration_id == test_calendar_integration.id
    assert event.user_id == test_user.id
    assert event.external_id == "event_123_google"
    assert event.title == "Team Meeting"
    assert event.event_type == EventType.MEETING


@pytest.mark.asyncio
async def test_calendar_event_external_id_unique_per_integration(
    db_session: AsyncSession, test_user: User, test_calendar_integration: CalendarIntegration
):
    """Test that external_id must be unique per integration."""
    # Create first event
    event1 = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_unique_123",
        title="Event 1",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        calendar_id="primary",
        calendar_name="Work",
    )
    db_session.add(event1)
    await db_session.commit()

    # Try to create second event with same external_id and integration (should fail)
    event2 = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_unique_123",
        title="Event 2",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        calendar_id="primary",
        calendar_name="Work",
    )
    db_session.add(event2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_calendar_event_cascade_delete_integration(db_session: AsyncSession, test_user: User):
    """Test that deleting an integration cascades to calendar events."""
    # Create integration
    integration = CalendarIntegration(
        user_id=test_user.id,
        provider=CalendarProvider.GOOGLE_CALENDAR,
        status=IntegrationStatus.ACTIVE,
        access_token=encrypt_token("token"),
        refresh_token=encrypt_token("refresh"),
        token_expires_at=datetime.now() + timedelta(hours=1),
        scopes=["calendar.readonly"],
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)

    # Create event
    event = CalendarEvent(
        integration_id=integration.id,
        user_id=test_user.id,
        external_id="cascade_event_123",
        title="Test Event",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        calendar_id="primary",
        calendar_name="Work",
    )
    db_session.add(event)
    await db_session.commit()

    event_id = event.id

    # Delete the integration
    await db_session.delete(integration)
    await db_session.commit()

    # Event should be deleted too
    result = await db_session.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    deleted_event = result.scalar_one_or_none()
    assert deleted_event is None


@pytest.mark.asyncio
async def test_calendar_event_time_range_queries(
    db_session: AsyncSession, test_user: User, test_calendar_integration: CalendarIntegration
):
    """Test querying events by time range."""
    now = datetime.now()

    # Create events at different times
    event_past = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_past",
        title="Past Event",
        start_time=now - timedelta(days=7),
        end_time=now - timedelta(days=7, hours=-1),
        calendar_id="primary",
        calendar_name="Work",
    )

    event_current = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_current",
        title="Current Event",
        start_time=now,
        end_time=now + timedelta(hours=1),
        calendar_id="primary",
        calendar_name="Work",
    )

    event_future = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_future",
        title="Future Event",
        start_time=now + timedelta(days=7),
        end_time=now + timedelta(days=7, hours=1),
        calendar_id="primary",
        calendar_name="Work",
    )

    db_session.add_all([event_past, event_current, event_future])
    await db_session.commit()

    # Query events in current week
    start_range = now - timedelta(days=1)
    end_range = now + timedelta(days=1)

    result = await db_session.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == test_user.id)
        .where(CalendarEvent.start_time >= start_range)
        .where(CalendarEvent.start_time <= end_range)
        .order_by(CalendarEvent.start_time)
    )
    events_in_range = result.scalars().all()

    assert len(events_in_range) == 1
    assert events_in_range[0].title == "Current Event"


@pytest.mark.asyncio
async def test_event_type_enum_values():
    """Test EventType enum values."""
    assert EventType.MEETING == "MEETING"
    assert EventType.FOCUS == "FOCUS"
    assert EventType.PERSONAL == "PERSONAL"
    assert EventType.TRAVEL == "TRAVEL"
    assert EventType.OTHER == "OTHER"
    assert len(EventType) == 5


@pytest.mark.asyncio
async def test_calendar_event_all_day_event(
    db_session: AsyncSession, test_user: User, test_calendar_integration: CalendarIntegration
):
    """Test creating an all-day event."""
    event = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_all_day",
        title="All Day Conference",
        start_time=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        end_time=datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999),
        is_all_day=True,
        calendar_id="primary",
        calendar_name="Work",
    )

    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.is_all_day is True
    assert event.title == "All Day Conference"


@pytest.mark.asyncio
async def test_calendar_event_recurring_flag(
    db_session: AsyncSession, test_user: User, test_calendar_integration: CalendarIntegration
):
    """Test recurring event flag."""
    event = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_recurring",
        title="Weekly Standup",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(minutes=30),
        calendar_id="primary",
        calendar_name="Work",
        is_recurring=True,
    )

    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.is_recurring is True
    assert event.title == "Weekly Standup"


@pytest.mark.asyncio
async def test_calendar_event_nullable_fields(
    db_session: AsyncSession, test_user: User, test_calendar_integration: CalendarIntegration
):
    """Test that description, location, and event_type are nullable."""
    event = CalendarEvent(
        integration_id=test_calendar_integration.id,
        user_id=test_user.id,
        external_id="event_minimal",
        title="Minimal Event",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        calendar_id="primary",
        calendar_name="Work",
        # description, location, event_type omitted
    )

    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.description is None
    assert event.location is None
    assert event.event_type is None
