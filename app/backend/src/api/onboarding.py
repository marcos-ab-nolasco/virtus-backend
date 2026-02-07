"""Onboarding API endpoints.

Provides status and skip endpoints for the onboarding flow.
The actual onboarding conversation happens through the chat endpoint
via AgentRouter delegation.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.onboarding import OnboardingSkipResponse, OnboardingStatusResponse
from src.services import onboarding as onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Get the current onboarding status and progress."""
    state = await onboarding_service.get_onboarding_state(db, current_user.id)

    return OnboardingStatusResponse(
        status=state["status"],
        current_step=state["current_step"],
        progress_percent=state["progress_percent"],
        started_at=datetime.fromisoformat(state["started_at"]) if state["started_at"] else None,
        completed_at=(
            datetime.fromisoformat(state["completed_at"]) if state["completed_at"] else None
        ),
    )


@router.patch("/skip", response_model=OnboardingSkipResponse)
async def skip_onboarding(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OnboardingSkipResponse:
    """Skip onboarding and mark as completed."""
    try:
        profile = await onboarding_service.skip_onboarding(db, current_user.id)

        return OnboardingSkipResponse(
            status=profile.onboarding_status.value,
            completed_at=profile.onboarding_completed_at or datetime.now(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e
