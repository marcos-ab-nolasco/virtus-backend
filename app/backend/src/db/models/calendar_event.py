"""CalendarEvent model for storing synced calendar events.

Stores events from external calendar providers (Google, Outlook, Apple) with
denormalized user_id for efficient time-range queries.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.calendar_integration import CalendarIntegration
    from src.db.models.user import User


class EventType(str, enum.Enum):
    """Event types inferred from calendar event metadata."""

    MEETING = "MEETING"
    FOCUS = "FOCUS"
    PERSONAL = "PERSONAL"
    TRAVEL = "TRAVEL"
    OTHER = "OTHER"


class CalendarEvent(Base):
    """Calendar event synced from external calendar provider.

    Events are denormalized with user_id for efficient time-range queries
    without joining through calendar_integrations.
    """

    __tablename__ = "calendar_events"

    __table_args__ = (
        UniqueConstraint("integration_id", "external_id", name="uq_integration_external_id"),
        Index("ix_calendar_events_user_start_time", "user_id", "start_time"),
    )

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=func.gen_random_uuid(),
        index=True,
    )

    # Foreign keys (user_id is denormalized for performance)
    integration_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("calendar_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External provider event ID (unique per integration)
    external_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Event ID from external calendar provider",
    )

    # Event details
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Time range
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_all_day: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Calendar metadata
    calendar_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Calendar ID from external provider",
    )
    calendar_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Event classification (inferred by backend)
    event_type: Mapped[EventType | None] = mapped_column(
        Enum(EventType, native_enum=False, name="event_type_enum"),
        nullable=True,
        comment="Inferred event type (meeting, focus, etc.)",
    )

    # Recurrence
    is_recurring: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Sync metadata
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Last time this event was synced from provider",
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
    integration: Mapped["CalendarIntegration"] = relationship(
        "CalendarIntegration",
        back_populates="events",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="calendar_events",
    )

    def __repr__(self) -> str:
        return f"<CalendarEvent(id={self.id}, title={self.title}, start_time={self.start_time})>"
