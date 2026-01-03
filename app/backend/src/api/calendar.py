"""Calendar integration and events API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.calendar_event import CalendarEventListResponse, CalendarEventResponse
from src.schemas.calendar_integration import (
    CalendarIntegrationCreate,
    CalendarIntegrationResponse,
    CalendarIntegrationUpdate,
)
from src.services import calendar_event as event_service
from src.services import calendar_integration as integration_service

router = APIRouter(prefix="/me/calendar", tags=["Calendar"])


@router.post("/integrations", response_model=CalendarIntegrationResponse, status_code=201)
async def connect_calendar(
    integration_data: CalendarIntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a calendar provider (Google Calendar, Outlook, Apple Calendar).

    This endpoint is called after successful OAuth flow to store the integration.
    Tokens are encrypted before storage and never exposed in responses.
    """
    integration = await integration_service.create_integration(
        db, current_user.id, integration_data
    )
    return integration


@router.get("/integrations", response_model=list[CalendarIntegrationResponse])
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all calendar integrations for the authenticated user.

    Returns integration status, provider info, and sync settings.
    OAuth tokens are never exposed.
    """
    integrations = await integration_service.get_user_integrations(db, current_user.id)
    return integrations


@router.get("/integrations/{integration_id}", response_model=CalendarIntegrationResponse)
async def get_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific calendar integration."""
    integration = await integration_service.get_integration_by_id(
        db, current_user.id, integration_id
    )
    return integration


@router.patch("/integrations/{integration_id}", response_model=CalendarIntegrationResponse)
async def update_integration(
    integration_id: uuid.UUID,
    update_data: CalendarIntegrationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update calendar integration settings.

    Allows updating:
    - calendars_synced: Which calendars to include
    - sync_enabled: Enable/disable automatic sync
    """
    integration = await integration_service.update_integration(
        db, current_user.id, integration_id, update_data
    )
    return integration


@router.delete("/integrations/{integration_id}", status_code=204)
async def disconnect_calendar(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect a calendar integration.

    This will:
    - Delete the integration and all OAuth tokens
    - Cascade delete all synced events from this integration
    """
    await integration_service.disconnect_integration(db, current_user.id, integration_id)
    return None


@router.get("/events", response_model=CalendarEventListResponse)
async def list_events(
    start_date: datetime = Query(..., description="Start of date range (ISO 8601)"),
    end_date: datetime = Query(..., description="End of date range (ISO 8601)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List calendar events within a date range.

    Returns all synced events from connected calendar providers.
    Used by planning features to show availability and commitments.
    """
    events = await event_service.get_user_events(db, current_user.id, start_date, end_date)
    total = await event_service.get_events_count(db, current_user.id, start_date, end_date)

    return CalendarEventListResponse(
        events=[CalendarEventResponse.model_validate(event) for event in events],
        total=total,
        start_date=start_date,
        end_date=end_date,
    )
