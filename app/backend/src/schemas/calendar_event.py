"""Pydantic schemas for CalendarEvent."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.db.models.calendar_event import EventType


class CalendarEventBase(BaseModel):
    """Base schema for CalendarEvent."""

    title: str = Field(..., max_length=500, description="Event title")
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, max_length=500, description="Event location")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    is_all_day: bool = Field(False, description="Whether this is an all-day event")
    calendar_name: str = Field(..., max_length=255, description="Name of the calendar")
    event_type: EventType | None = Field(None, description="Inferred event type")
    is_recurring: bool = Field(False, description="Whether this is a recurring event")


class CalendarEventResponse(BaseModel):
    """Schema for CalendarEvent API responses."""

    id: uuid.UUID
    integration_id: uuid.UUID
    user_id: uuid.UUID
    external_id: str
    title: str
    description: str | None
    location: str | None
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    calendar_id: str
    calendar_name: str
    event_type: EventType | None
    is_recurring: bool
    synced_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalendarEventListResponse(BaseModel):
    """Schema for paginated list of calendar events."""

    events: list[CalendarEventResponse]
    total: int = Field(..., description="Total number of events in date range")
    start_date: datetime = Field(..., description="Start of queried date range")
    end_date: datetime = Field(..., description="End of queried date range")
