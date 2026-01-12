"""CalendarIntegration model for storing calendar provider connections.

Stores OAuth credentials and configuration for syncing external calendars
(Google Calendar, Outlook, Apple Calendar).
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.calendar_event import CalendarEvent
    from src.db.models.user import User


class CalendarProvider(str, enum.Enum):
    """Calendar providers supported for integration."""

    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    OUTLOOK = "OUTLOOK"
    APPLE_CALENDAR = "APPLE_CALENDAR"


class IntegrationStatus(str, enum.Enum):
    """Status of calendar integration."""

    PENDING = "PENDING"  # OAuth in progress
    ACTIVE = "ACTIVE"  # Connected and syncing
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  # Needs reauthorization
    ERROR = "ERROR"  # Sync error occurred
    DISCONNECTED = "DISCONNECTED"  # Manually disconnected


class CalendarIntegration(Base):
    """Calendar integration for syncing external calendars.

    Stores OAuth credentials (encrypted) and configuration for calendar providers.
    A user can have one integration per provider.
    """

    __tablename__ = "calendar_integrations"

    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    # Primary key and foreign key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider and status
    provider: Mapped[CalendarProvider] = mapped_column(
        Enum(CalendarProvider, native_enum=False, name="calendar_provider_enum"),
        nullable=False,
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, native_enum=False, name="integration_status_enum"),
        nullable=False,
    )

    # OAuth tokens (encrypted in application layer before storage)
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted OAuth access token",
    )
    refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted OAuth refresh token",
    )
    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the access token expires",
    )
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        comment="OAuth scopes granted by user",
    )

    # Configuration
    calendars_synced: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {calendar_id, calendar_name, color, include_in_planning}",
    )
    sync_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether automatic sync is enabled",
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful sync timestamp",
    )
    sync_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Last sync error message if any",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="calendar_integrations",
    )
    events: Mapped[list["CalendarEvent"]] = relationship(
        "CalendarEvent",
        back_populates="integration",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CalendarIntegration(id={self.id}, user_id={self.user_id}, provider={self.provider}, status={self.status})>"
