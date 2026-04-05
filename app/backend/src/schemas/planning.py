"""Pydantic schemas for planning entities (AnnualGoal, MonthlyObjective)."""

from __future__ import annotations

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.db.models.planning import GoalStatus, ObjectiveStatus

# ===== AnnualGoal Schemas =====


class AnnualGoalCreate(BaseModel):
    """Schema for creating an annual goal."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    life_area: str = Field(..., min_length=1, max_length=50)
    target_year: int = Field(..., ge=2020, le=2100)
    priority: int = Field(default=1, ge=1)


class AnnualGoalUpdate(BaseModel):
    """Schema for updating an annual goal (partial)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    life_area: str | None = Field(default=None, min_length=1, max_length=50)
    target_year: int | None = Field(default=None, ge=2020, le=2100)
    priority: int | None = Field(default=None, ge=1)
    status: GoalStatus | None = None


class AnnualGoalResponse(BaseModel):
    """Schema for reading an annual goal."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: str | None
    life_area: str
    target_year: int
    priority: int
    status: GoalStatus
    created_at: dt.datetime
    updated_at: dt.datetime


# ===== MonthlyObjective Schemas =====


class MonthlyObjectiveCreate(BaseModel):
    """Schema for creating a monthly objective."""

    description: str = Field(..., min_length=1)
    annual_goal_id: UUID | None = None
    is_active: bool = True


class MonthlyObjectiveUpdate(BaseModel):
    """Schema for updating a monthly objective (partial)."""

    description: str | None = Field(default=None, min_length=1)
    annual_goal_id: UUID | None = None
    status: ObjectiveStatus | None = None
    is_active: bool | None = None


class MonthlyObjectiveResponse(BaseModel):
    """Schema for reading a monthly objective."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    annual_goal_id: UUID | None
    description: str
    status: ObjectiveStatus
    is_active: bool
    created_at: dt.datetime
    updated_at: dt.datetime
