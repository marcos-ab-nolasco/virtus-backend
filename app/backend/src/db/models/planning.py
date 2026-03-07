"""Planning models: goals, objectives, and onboarding insights.

These entities are populated during the deep onboarding flow and used
throughout the advisory and planning cycles.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class GoalStatus(enum.StrEnum):
    """Status of an annual goal."""

    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    REVIEW_PENDING = "REVIEW_PENDING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class ObjectiveStatus(enum.StrEnum):
    """Status of a monthly or weekly objective."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    NOT_COMPLETED = "NOT_COMPLETED"
    DROPPED = "DROPPED"


class ObjectivePriority(enum.StrEnum):
    """Priority level of an objective."""

    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"


class LifeAreaScore(Base):
    """Wheel-of-Life scores per area for a user.

    Collected during deep onboarding (phase 1) and updatable in reviews.
    UNIQUE(user_id, area) — one row per area per user.
    """

    __tablename__ = "life_area_scores"
    __table_args__ = (UniqueConstraint("user_id", "area", name="uq_life_area_scores_user_area"),)

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
    area: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="LifeArea value (VARCHAR, no native enum)",
    )
    current_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Current satisfaction score 1-10",
    )
    desired_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Desired satisfaction score 1-10",
    )
    is_priority: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False,
        comment="Whether this area is a top priority for improvement",
    )
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

    user: Mapped["User"] = relationship("User", back_populates="life_area_scores")

    def __repr__(self) -> str:
        return f"<LifeAreaScore(user_id={self.user_id}, area={self.area}, current={self.current_score})>"


class AnnualGoal(Base):
    """A high-level annual goal tied to a life area.

    Created during deep onboarding (phase 3) for each priority area.
    """

    __tablename__ = "annual_goals"

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    life_area: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="LifeArea value (VARCHAR)",
    )
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Ordering priority (lower = higher priority)",
    )
    status: Mapped[str] = mapped_column(
        Enum(GoalStatus, native_enum=False, name="goal_status_enum"),
        default=GoalStatus.PLANNING,
        nullable=False,
    )
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

    user: Mapped["User"] = relationship("User", back_populates="annual_goals")
    monthly_objectives: Mapped[list["MonthlyObjective"]] = relationship(
        "MonthlyObjective",
        back_populates="annual_goal",
        cascade="all, delete-orphan",
    )
    weekly_objectives: Mapped[list["WeeklyObjective"]] = relationship(
        "WeeklyObjective",
        back_populates="annual_goal",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnnualGoal(id={self.id}, user_id={self.user_id}, title={self.title!r})>"


class MonthlyObjective(Base):
    """A monthly objective, optionally linked to an annual goal.

    monthly_plan_id is stored as a plain UUID without FK — the
    MonthlyPlan table will be added in M3.
    """

    __tablename__ = "monthly_objectives"

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
    annual_goal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("annual_goals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # No FK — MonthlyPlan table does not exist yet (M3)
    monthly_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        comment="FK to monthly_plans.id (table added in M3)",
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(ObjectiveStatus, native_enum=False, name="objective_status_enum"),
        default=ObjectiveStatus.PENDING,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
    )
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

    user: Mapped["User"] = relationship("User", back_populates="monthly_objectives")
    annual_goal: Mapped["AnnualGoal | None"] = relationship(
        "AnnualGoal",
        back_populates="monthly_objectives",
    )
    weekly_objectives: Mapped[list["WeeklyObjective"]] = relationship(
        "WeeklyObjective",
        back_populates="monthly_objective",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MonthlyObjective(id={self.id}, user_id={self.user_id})>"


class WeeklyObjective(Base):
    """A weekly priority objective, optionally linked to monthly/annual goals.

    weekly_plan_id stored without FK — WeeklyPlan table is M3.
    """

    __tablename__ = "weekly_objectives"

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
    # No FK — WeeklyPlan table does not exist yet (M3)
    weekly_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        comment="FK to weekly_plans.id (table added in M3)",
    )
    monthly_objective_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("monthly_objectives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    annual_goal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("annual_goals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        Enum(ObjectivePriority, native_enum=False, name="objective_priority_enum"),
        default=ObjectivePriority.PRIMARY,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(ObjectiveStatus, native_enum=False, name="objective_status_enum"),
        default=ObjectiveStatus.PENDING,
        nullable=False,
    )
    area: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="LifeArea value (VARCHAR, nullable)",
    )
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

    user: Mapped["User"] = relationship("User", back_populates="weekly_objectives")
    monthly_objective: Mapped["MonthlyObjective | None"] = relationship(
        "MonthlyObjective",
        back_populates="weekly_objectives",
    )
    annual_goal: Mapped["AnnualGoal | None"] = relationship(
        "AnnualGoal",
        back_populates="weekly_objectives",
    )

    def __repr__(self) -> str:
        return f"<WeeklyObjective(id={self.id}, user_id={self.user_id}, priority={self.priority})>"


class OnboardingInsight(Base):
    """Structured insights collected during the deep onboarding conversation.

    One row per user (UNIQUE on user_id). Upserted phase by phase.
    Covers Ikigai, ACT values, Future Self, Working Backwards, and WOOP data.
    """

    __tablename__ = "onboarding_insights"

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

    # Ikigai fields (phase 2)
    energizing_activities: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Activities that energize / what the user loves doing",
    )
    recognized_skills: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Skills recognized by others / what the user is good at",
    )
    market_problems: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Problems the world needs solved that the user sees",
    )

    # ACT values (phase 2)
    top_values: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Top 3-5 personal values identified",
    )
    value_behavior_gap: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Gap between stated values and current behavior",
    )

    # Future Self / Working Backwards (phase 3)
    future_self_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of ideal life in 12 months",
    )
    milestone_6months: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="What needs to be true at 6 months to reach the 12-month vision",
    )
    milestone_3months: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="What needs to be true at 3 months",
    )
    first_step: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="The very first concrete step toward the vision",
    )

    # WOOP (phase 4)
    best_outcome: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Best imaginable outcome if goals are achieved (WOOP: Outcome)",
    )
    internal_obstacle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Main internal obstacle (WOOP: Obstacle)",
    )
    if_then_plan: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="If [obstacle] then [plan] — implementation intention (WOOP: Plan)",
    )

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

    user: Mapped["User"] = relationship("User", back_populates="onboarding_insight")

    def __repr__(self) -> str:
        return f"<OnboardingInsight(user_id={self.user_id})>"
