import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class OnboardingStatus(str, enum.Enum):
    """Onboarding workflow states."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class UserProfile(Base):
    """User profile with onboarding data and personalization info.

    Stores user's vision, objectives, life assessment, and AI-inferred patterns.
    Created automatically when User is created (via SQLAlchemy event).
    """

    __tablename__ = "user_profiles"

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

    # Onboarding status
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        Enum(OnboardingStatus, native_enum=False, name="onboarding_status_enum"),
        default=OnboardingStatus.NOT_STARTED,
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

    # Optional text fields (onboarding questions)
    vision_5_years: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_challenge: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB fields (structured data, validated via Pydantic)
    annual_objectives: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {id, description, life_area, priority}",
    )
    life_dashboard: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Object with health, work, relationships, personal_time scores (1-10)",
    )
    observed_patterns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {pattern_type, description, confidence}",
    )
    moral_profile: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Object with care, fairness, loyalty, authority, purity, liberty scores (0-1)",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )

    def __repr__(self) -> str:
        return (
            f"<UserProfile(id={self.id}, user_id={self.user_id}, status={self.onboarding_status})>"
        )
