import enum
import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class WeekDay(str, enum.Enum):
    """Days of the week for weekly review scheduling."""

    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class CommunicationStyle(str, enum.Enum):
    """AI communication style preferences."""

    DIRECT = "DIRECT"
    GENTLE = "GENTLE"
    MOTIVATING = "MOTIVATING"


class UserPreferences(Base):
    """User preferences for app behavior and AI personalization.

    Stores user configuration for check-ins, communication style, and scheduling.
    Created automatically when User is created (via SQLAlchemy event).
    """

    __tablename__ = "user_preferences"

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
        unique=True,
        nullable=False,
        index=True,
    )

    # Timezone configuration
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
    )

    # Morning check-in settings
    morning_checkin_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    morning_checkin_time: Mapped[time] = mapped_column(
        Time,
        default=time(8, 0),
        nullable=False,
    )

    # Evening check-in settings
    evening_checkin_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    evening_checkin_time: Mapped[time] = mapped_column(
        Time,
        default=time(21, 0),
        nullable=False,
    )

    # Weekly review settings
    weekly_review_day: Mapped[WeekDay] = mapped_column(
        Enum(WeekDay, native_enum=False, name="week_day_enum"),
        default=WeekDay.SUNDAY,
        nullable=False,
    )

    # Week start day (for calendar and planning)
    week_start_day: Mapped[WeekDay] = mapped_column(
        Enum(WeekDay, native_enum=False, name="week_day_enum"),
        default=WeekDay.MONDAY,
        nullable=False,
    )

    # Language preference
    language: Mapped[str] = mapped_column(
        String(10),
        default="pt-BR",
        nullable=False,
    )

    # Communication preferences
    communication_style: Mapped[CommunicationStyle] = mapped_column(
        Enum(CommunicationStyle, native_enum=False, name="communication_style_enum"),
        default=CommunicationStyle.DIRECT,
        nullable=False,
    )
    coach_name: Mapped[str] = mapped_column(
        String(50),
        default="Virtus",
        nullable=False,
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
        back_populates="preferences",
    )

    def __repr__(self) -> str:
        return f"<UserPreferences(id={self.id}, user_id={self.user_id}, style={self.communication_style})>"
