import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubscriptionBase(BaseModel):
    """Base schema with common Subscription fields."""

    tier: str = Field(
        default="FREE",
        description="Subscription tier (FREE, TRIAL, PAID, case-insensitive)",
    )
    status: str = Field(
        default="ACTIVE",
        description="Subscription status (ACTIVE, CANCELLED, EXPIRED, TRIAL_ENDED, case-insensitive)",
    )
    end_date: datetime | None = Field(
        None,
        description="Subscription end date (NULL for FREE tier or unlimited PAID)",
    )
    trial_ends_at: datetime | None = Field(
        None,
        description="Trial period expiration (only for TRIAL tier)",
    )

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        """Validate subscription tier (accepts case-insensitive, returns UPPERCASE)."""
        valid_tiers = ["FREE", "TRIAL", "PAID"]
        if v.upper() not in valid_tiers:
            raise ValueError(f"Invalid tier: {v}. Must be one of {valid_tiers}")
        return v.upper()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate subscription status (accepts case-insensitive, returns UPPERCASE)."""
        valid_statuses = ["ACTIVE", "CANCELLED", "EXPIRED", "TRIAL_ENDED"]
        if v.upper() not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
        return v.upper()


class SubscriptionUpdate(BaseModel):
    """Schema for updating Subscription (partial update via PATCH).

    All fields are optional to support partial updates.
    """

    tier: str | None = Field(None, description="Subscription tier (FREE, TRIAL, PAID)")
    status: str | None = Field(
        None, description="Subscription status (ACTIVE, CANCELLED, EXPIRED, TRIAL_ENDED)"
    )
    end_date: datetime | None = Field(
        None,
        description="Subscription end date (NULL for FREE tier or unlimited PAID)",
    )
    trial_ends_at: datetime | None = Field(
        None,
        description="Trial period expiration (only for TRIAL tier)",
    )

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str | None) -> str | None:
        """Validate subscription tier (accepts case-insensitive, returns UPPERCASE)."""
        if v is None:
            return v

        valid_tiers = ["FREE", "TRIAL", "PAID"]
        if v.upper() not in valid_tiers:
            raise ValueError(f"Invalid tier: {v}. Must be one of {valid_tiers}")
        return v.upper()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate subscription status (accepts case-insensitive, returns UPPERCASE)."""
        if v is None:
            return v

        valid_statuses = ["ACTIVE", "CANCELLED", "EXPIRED", "TRIAL_ENDED"]
        if v.upper() not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
        return v.upper()


class SubscriptionResponse(SubscriptionBase):
    """Schema for Subscription API responses."""

    id: uuid.UUID
    user_id: uuid.UUID
    start_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
