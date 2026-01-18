"""Service layer for CalendarEvent operations."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.calendar_event import CalendarEvent


async def get_user_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
) -> list[CalendarEvent]:
    """Get all calendar events for a user within a date range.

    Args:
        db: Database session
        user_id: ID of the user
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of CalendarEvent instances ordered by start_time
    """
    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user_id)
        .where(CalendarEvent.start_time >= start_date)
        .where(CalendarEvent.start_time <= end_date)
        .order_by(CalendarEvent.start_time)
    )
    return list(result.scalars().all())


async def get_events_count(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
) -> int:
    """Count calendar events for a user within a date range.

    Args:
        db: Database session
        user_id: ID of the user
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Total count of events
    """
    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.user_id == user_id)
        .where(CalendarEvent.start_time >= start_date)
        .where(CalendarEvent.start_time <= end_date)
    )
    return len(result.scalars().all())


async def cleanup_old_events(db: AsyncSession, days_to_keep: int = 7) -> int:
    """Remove calendar events older than specified days.

    This is typically run as a background task to prevent database bloat.
    Events older than 7 days are usually not needed for planning features.

    Args:
        db: Database session
        days_to_keep: Number of days of events to retain (default 7)

    Returns:
        Number of events deleted
    """
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    result = await db.execute(delete(CalendarEvent).where(CalendarEvent.end_time < cutoff_date))
    await db.commit()

    return result.rowcount  # type: ignore


async def get_events_by_integration(
    db: AsyncSession, integration_id: uuid.UUID
) -> list[CalendarEvent]:
    """Get all events for a specific calendar integration.

    Used during sync operations to update existing events.

    Args:
        db: Database session
        integration_id: ID of the calendar integration

    Returns:
        List of CalendarEvent instances
    """
    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.integration_id == integration_id)
        .order_by(CalendarEvent.start_time)
    )
    return list(result.scalars().all())


async def upsert_event(
    db: AsyncSession,
    integration_id: uuid.UUID,
    user_id: uuid.UUID,
    external_id: str,
    event_data: dict,
) -> CalendarEvent:
    """Create or update a calendar event from external provider.

    Used during calendar sync to insert new events or update existing ones.

    Args:
        db: Database session
        integration_id: ID of the calendar integration
        user_id: ID of the user (denormalized for performance)
        external_id: Event ID from external provider
        event_data: Event data from provider API

    Returns:
        Created or updated CalendarEvent instance
    """
    # Check if event already exists
    result = await db.execute(
        select(CalendarEvent)
        .where(CalendarEvent.integration_id == integration_id)
        .where(CalendarEvent.external_id == external_id)
    )
    existing_event = result.scalar_one_or_none()

    if existing_event:
        # Update existing event
        for field, value in event_data.items():
            setattr(existing_event, field, value)
        existing_event.synced_at = datetime.now()
        await db.commit()
        await db.refresh(existing_event)
        return existing_event
    else:
        # Create new event
        new_event = CalendarEvent(
            integration_id=integration_id,
            user_id=user_id,
            external_id=external_id,
            synced_at=datetime.now(),
            **event_data,
        )
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
        return new_event
