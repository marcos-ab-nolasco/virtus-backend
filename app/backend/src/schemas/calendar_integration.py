"""Pydantic schemas for CalendarIntegration."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.db.models.calendar_integration import CalendarProvider, IntegrationStatus


class CalendarConfigItem(BaseModel):
    """Individual calendar configuration within an integration."""

    calendar_id: str = Field(..., description="Calendar ID from external provider")
    calendar_name: str = Field(..., description="Display name of the calendar")
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code (#RRGGBB)")
    include_in_planning: bool = Field(
        True, description="Whether to include this calendar in planning features"
    )


class CalendarIntegrationBase(BaseModel):
    """Base schema for CalendarIntegration."""

    provider: CalendarProvider
    calendars_synced: list[CalendarConfigItem] | None = Field(
        None, description="List of calendars to sync from this provider"
    )
    sync_enabled: bool = Field(True, description="Whether automatic sync is enabled")


class CalendarIntegrationCreate(CalendarIntegrationBase):
    """Schema for creating a new CalendarIntegration.

    Note: access_token and refresh_token are passed separately via OAuth flow,
    not through this schema.
    """

    access_token: str = Field(..., description="OAuth access token (will be encrypted)")
    refresh_token: str = Field(..., description="OAuth refresh token (will be encrypted)")
    token_expires_at: datetime = Field(..., description="When the access token expires")
    scopes: list[str] = Field(..., description="OAuth scopes granted by user")


class CalendarIntegrationUpdate(BaseModel):
    """Schema for updating CalendarIntegration (partial update)."""

    calendars_synced: list[CalendarConfigItem] | None = None
    sync_enabled: bool | None = None


class CalendarIntegrationResponse(BaseModel):
    """Schema for CalendarIntegration API responses.

    IMPORTANT: Never expose access_token or refresh_token in responses!
    """

    id: uuid.UUID
    user_id: uuid.UUID
    provider: CalendarProvider
    status: IntegrationStatus
    calendars_synced: list[CalendarConfigItem] | None
    sync_enabled: bool
    last_sync_at: datetime | None
    sync_error: str | None
    created_at: datetime
    updated_at: datetime

    # Token expiration info (but not the token itself)
    token_expires_at: datetime
    scopes: list[str]

    model_config = ConfigDict(from_attributes=True)
