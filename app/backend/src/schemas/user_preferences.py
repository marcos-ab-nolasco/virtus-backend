import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserPreferencesBase(BaseModel):
    """Base schema with common UserPreferences fields."""

    timezone: str = Field(default="UTC", description="User's timezone (e.g., 'America/Sao_Paulo')")
    morning_checkin_enabled: bool = Field(default=True, description="Enable morning check-ins")
    morning_checkin_time: time = Field(default=time(8, 0), description="Morning check-in time")
    evening_checkin_enabled: bool = Field(default=True, description="Enable evening check-ins")
    evening_checkin_time: time = Field(default=time(21, 0), description="Evening check-in time")
    weekly_review_day: str = Field(
        default="SUNDAY",
        description="Preferred day for weekly review (MONDAY-SUNDAY, case-insensitive)",
    )
    communication_style: str = Field(
        default="DIRECT",
        description="AI communication style (DIRECT, GENTLE, MOTIVATING, case-insensitive)",
    )
    coach_name: str = Field(
        default="Virtus",
        min_length=1,
        max_length=50,
        description="Custom name for the AI coach",
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone using pytz."""
        import pytz

        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}. Must be a valid IANA timezone.")
        return v

    @field_validator("weekly_review_day")
    @classmethod
    def validate_weekly_review_day(cls, v: str) -> str:
        """Validate weekly review day (accepts case-insensitive, returns UPPERCASE)."""
        valid_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        if v.upper() not in valid_days:
            raise ValueError(f"Invalid day: {v}. Must be one of {valid_days}")
        return v.upper()

    @field_validator("communication_style")
    @classmethod
    def validate_communication_style(cls, v: str) -> str:
        """Validate communication style (accepts case-insensitive, returns UPPERCASE)."""
        valid_styles = ["DIRECT", "GENTLE", "MOTIVATING"]
        if v.upper() not in valid_styles:
            raise ValueError(f"Invalid style: {v}. Must be one of {valid_styles}")
        return v.upper()


class UserPreferencesUpdate(BaseModel):
    """Schema for updating UserPreferences (partial update via PATCH).

    All fields are optional to support partial updates.
    """

    timezone: str | None = Field(None, description="User's timezone (e.g., 'America/Sao_Paulo')")
    morning_checkin_enabled: bool | None = Field(None, description="Enable morning check-ins")
    morning_checkin_time: time | None = Field(None, description="Morning check-in time")
    evening_checkin_enabled: bool | None = Field(None, description="Enable evening check-ins")
    evening_checkin_time: time | None = Field(None, description="Evening check-in time")
    weekly_review_day: str | None = Field(
        None, description="Preferred day for weekly review (monday-sunday)"
    )
    communication_style: str | None = Field(
        None, description="AI communication style (direct, gentle, motivating)"
    )
    coach_name: str | None = Field(
        None, min_length=1, max_length=50, description="Custom name for the AI coach"
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        """Validate timezone using pytz."""
        if v is None:
            return v

        import pytz

        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}. Must be a valid IANA timezone.")
        return v

    @field_validator("weekly_review_day")
    @classmethod
    def validate_weekly_review_day(cls, v: str | None) -> str | None:
        """Validate weekly review day (accepts case-insensitive, returns UPPERCASE)."""
        if v is None:
            return v

        valid_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        if v.upper() not in valid_days:
            raise ValueError(f"Invalid day: {v}. Must be one of {valid_days}")
        return v.upper()

    @field_validator("communication_style")
    @classmethod
    def validate_communication_style(cls, v: str | None) -> str | None:
        """Validate communication style (accepts case-insensitive, returns UPPERCASE)."""
        if v is None:
            return v

        valid_styles = ["DIRECT", "GENTLE", "MOTIVATING"]
        if v.upper() not in valid_styles:
            raise ValueError(f"Invalid style: {v}. Must be one of {valid_styles}")
        return v.upper()


class UserPreferencesResponse(UserPreferencesBase):
    """Schema for UserPreferences API responses."""

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
