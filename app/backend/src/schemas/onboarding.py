"""Onboarding API schemas.

Pydantic schemas for onboarding status, module progress, and skip endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModuleProgress(BaseModel):
    """Progress for a single onboarding module."""

    phase: str = Field(..., description="Phase identifier (phase_1 ... phase_5)")
    status: str = Field(..., description="Module status: not_started, in_progress, completed")
    started_at: datetime | None = Field(None, description="When the module was started")
    completed_at: datetime | None = Field(None, description="When the module was completed")


class OnboardingStatusResponse(BaseModel):
    """Response schema for GET /onboarding/status."""

    status: str = Field(
        ...,
        description="Onboarding status (NOT_STARTED, IN_PROGRESS, SETUP_COMPLETED, COMPLETED)",
    )
    current_step: str | None = Field(None, description="Current onboarding step")
    progress_percent: int = Field(..., ge=0, le=100, description="Progress percentage")
    started_at: datetime | None = Field(None, description="When onboarding started")
    completed_at: datetime | None = Field(None, description="When onboarding completed")
    modules: list[ModuleProgress] = Field(
        default_factory=list, description="Progress for each of the 5 modules"
    )


class StartModuleResponse(BaseModel):
    """Response schema for POST /onboarding/modules/{index}/start."""

    conversation_id: str = Field(..., description="Conversation ID to use for this module")
    module_status: str = Field(..., description="Current module status")
    is_enrichment: bool = Field(
        ..., description="True when revisiting a completed module (enrichment mode)"
    )
    modules: list[ModuleProgress] = Field(..., description="Updated module progress list")


class OnboardingSkipResponse(BaseModel):
    """Response schema for PATCH /onboarding/skip."""

    status: str = Field(..., description="Onboarding status (should be COMPLETED)")
    completed_at: datetime = Field(..., description="When onboarding was marked as completed")
