import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class OnboardingStatus(str, enum.Enum):
    """Onboarding workflow states."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class LifeArea(str, enum.Enum):
    """Life areas for objectives and satisfaction tracking."""

    HEALTH = "HEALTH"
    WORK = "WORK"
    RELATIONSHIPS = "RELATIONSHIPS"
    PERSONAL_TIME = "PERSONAL_TIME"


class PatternType(str, enum.Enum):
    """Types of observed behavioral patterns."""

    ENERGY = "ENERGY"
    PROCRASTINATION = "PROCRASTINATION"
    STRESS = "STRESS"
    COMMUNICATION = "COMMUNICATION"


class StrengthCategory(str, enum.Enum):
    """Categories of personal strengths."""

    TECHNICAL = "TECHNICAL"
    INTERPERSONAL = "INTERPERSONAL"
    COGNITIVE = "COGNITIVE"
    CREATIVE = "CREATIVE"
    ORGANIZATIONAL = "ORGANIZATIONAL"


class StrengthSource(str, enum.Enum):
    """Source of strength identification."""

    DECLARED = "DECLARED"
    INFERRED = "INFERRED"


class InterestType(str, enum.Enum):
    """Types of interests."""

    HOBBY = "HOBBY"
    PROFESSIONAL_INTEREST = "PROFESSIONAL_INTEREST"
    LEARNING_GOAL = "LEARNING_GOAL"
    CURIOSITY = "CURIOSITY"


class EngagementLevel(str, enum.Enum):
    """Level of engagement with an interest."""

    ACTIVE = "ACTIVE"
    OCCASIONAL = "OCCASIONAL"
    ASPIRATIONAL = "ASPIRATIONAL"


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
    onboarding_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When onboarding was started",
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    onboarding_current_step: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Current onboarding step (welcome, name, goals, preferences, conclusion)",
    )
    onboarding_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Partial onboarding data (name, goals, preferences, conversation_history)",
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

    # Vision and challenges
    vision_5_years: Mapped[str | None] = mapped_column(Text, nullable=True)
    vision_5_years_themes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    main_obstacle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSONB fields (structured data, validated via Pydantic)
    annual_objectives: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {id, description, area, created_at}",
    )
    observed_patterns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {pattern_type, description, confidence, observed_at, evidence_count}",
    )
    moral_profile: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Object with care, fairness, loyalty, authority, purity, liberty scores (0-1)",
    )

    # Strengths and interests (M01 expansion)
    strengths: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {id, description, category, source, confidence, evidence, created_at}",
    )
    interests: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {id, name, type, engagement_level, related_to_goals, created_at}",
    )

    # Energy and drain activities
    energy_activities: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Activities that give energy",
    )
    drain_activities: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Activities that drain energy",
    )

    # Life satisfaction (individual fields replacing life_dashboard JSONB)
    satisfaction_health: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Health satisfaction score (1-10)",
    )
    satisfaction_work: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Work satisfaction score (1-10)",
    )
    satisfaction_relationships: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Relationships satisfaction score (1-10)",
    )
    satisfaction_personal_time: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Personal time satisfaction score (1-10)",
    )
    dashboard_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last update of satisfaction scores",
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
