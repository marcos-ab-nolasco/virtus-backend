from __future__ import annotations

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.db.models.conversation import InteractionChannel
from src.db.models.habit import FrequencyType

# ===== Habit Schemas =====


class HabitCreate(BaseModel):
    """Schema for creating a habit."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=7)
    frequency_type: FrequencyType = FrequencyType.DAILY
    frequency_config: dict | None = None
    target_per_period: int = Field(default=1, ge=1)
    target_unit: str | None = Field(default=None, max_length=50)
    minimum_version: int = Field(default=1, ge=1)


class HabitUpdate(BaseModel):
    """Schema for updating a habit (partial)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=7)
    frequency_type: FrequencyType | None = None
    frequency_config: dict | None = None
    target_per_period: int | None = Field(default=None, ge=1)
    target_unit: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    minimum_version: int | None = Field(default=None, ge=1)


class HabitResponse(BaseModel):
    """Schema for reading a habit."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    icon: str | None
    color: str | None
    frequency_type: FrequencyType
    frequency_config: dict | None
    target_per_period: int
    target_unit: str | None
    is_active: bool
    is_archived: bool
    minimum_version: int
    archived_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


# ===== HabitLog Schemas =====


class HabitLogCreate(BaseModel):
    """Schema for creating/toggling a habit log."""

    date: dt.date = Field(default_factory=dt.date.today)
    completed: bool = True
    quantity: float | None = None
    notes: str | None = None
    channel: InteractionChannel = InteractionChannel.WEB


class HabitLogResponse(BaseModel):
    """Schema for reading a habit log."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    habit_id: UUID
    user_id: UUID
    date: dt.date
    completed: bool
    quantity: float | None
    notes: str | None
    channel: InteractionChannel
    created_at: dt.datetime


class HabitLogListResponse(BaseModel):
    """Schema for listing habit logs."""

    logs: list[HabitLogResponse]
    total: int


# ===== Stats Schemas =====


class HeatmapEntry(BaseModel):
    """Single day in the heatmap."""

    date: dt.date
    completed: bool
    quantity: float | None = None


class HabitStatsResponse(BaseModel):
    """Aggregated stats for a habit."""

    habit_id: UUID
    current_streak: int
    longest_streak: int
    completion_rate_7d: float
    completion_rate_30d: float
    total_completions: int
    heatmap: list[HeatmapEntry]
