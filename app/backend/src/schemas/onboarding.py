"""Onboarding API schemas.

Pydantic schemas for onboarding status and skip endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class OnboardingStatusResponse(BaseModel):
    """Response schema for GET /onboarding/status."""

    status: str = Field(..., description="Onboarding status (NOT_STARTED, IN_PROGRESS, COMPLETED)")
    current_step: str | None = Field(None, description="Current onboarding step")
    progress_percent: int = Field(..., ge=0, le=100, description="Progress percentage")
    started_at: datetime | None = Field(None, description="When onboarding started")
    completed_at: datetime | None = Field(None, description="When onboarding completed")


class OnboardingSkipResponse(BaseModel):
    """Response schema for PATCH /onboarding/skip."""

    status: str = Field(..., description="Onboarding status (should be COMPLETED)")
    completed_at: datetime = Field(..., description="When onboarding was marked as completed")
