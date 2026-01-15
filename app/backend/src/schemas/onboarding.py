"""Onboarding API schemas.

Issue 3.4: Pydantic schemas for onboarding endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class OnboardingMessageRequest(BaseModel):
    """Request schema for POST /onboarding/message."""

    message: str = Field(..., min_length=1, max_length=2000, description="User's message")


class OnboardingStartResponse(BaseModel):
    """Response schema for POST /onboarding/start."""

    status: str = Field(..., description="Onboarding status (NOT_STARTED, IN_PROGRESS, COMPLETED)")
    current_step: str = Field(..., description="Current onboarding step")
    message: str = Field(..., description="Welcome message from the assistant")
    started_at: datetime = Field(..., description="When onboarding started")


class OnboardingMessageResponse(BaseModel):
    """Response schema for POST /onboarding/message."""

    current_step: str = Field(..., description="Current onboarding step")
    next_step: str | None = Field(None, description="Next step (null if complete)")
    assistant_message: str = Field(..., description="Response message from assistant")
    is_step_complete: bool = Field(..., description="Whether current step is complete")
    validation_error: str | None = Field(None, description="Validation error message if any")


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
