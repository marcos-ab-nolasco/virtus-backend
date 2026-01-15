"""Onboarding API endpoints.

Issue 3.4: REST API for onboarding flow.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus
from src.db.session import get_db
from src.schemas.onboarding import (
    OnboardingMessageRequest,
    OnboardingMessageResponse,
    OnboardingSkipResponse,
    OnboardingStartResponse,
    OnboardingStatusResponse,
)
from src.services import onboarding as onboarding_service
from src.skills.onboarding.skill_onboarding_short import SkillOnboardingShort
from src.skills.onboarding.steps import STEP_DEFINITIONS, get_step_from_string

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/start", response_model=OnboardingStartResponse)
async def start_onboarding(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OnboardingStartResponse:
    """Start the onboarding process.

    Creates a new onboarding session for the user if not already started or completed.
    If already in progress, returns the current state.
    """
    # Check current state
    state = await onboarding_service.get_onboarding_state(db, current_user.id)

    if state["status"] == OnboardingStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed for this user",
        )

    if state["status"] == OnboardingStatus.IN_PROGRESS.value:
        # Return current state
        current_step = get_step_from_string(state["current_step"])
        message = ""
        if current_step and current_step in STEP_DEFINITIONS:
            message = str(STEP_DEFINITIONS[current_step]["prompt"])

        return OnboardingStartResponse(
            status=state["status"],
            current_step=state["current_step"] or "welcome",
            message=message,
            started_at=(
                datetime.fromisoformat(state["started_at"])
                if state["started_at"]
                else datetime.now()
            ),
        )

    # Start new onboarding
    skill = SkillOnboardingShort(db_session=db)
    result = await skill.execute({"user_id": str(current_user.id), "action": "start"})

    if not result.success or result.data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or "Failed to start onboarding",
        )
    if not isinstance(result.data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid onboarding start response payload",
        )

    # Get fresh state after starting
    state = await onboarding_service.get_onboarding_state(db, current_user.id)

    return OnboardingStartResponse(
        status=state["status"],
        current_step=state["current_step"] or "welcome",
        message=str(result.data.get("message", "")),
        started_at=(
            datetime.fromisoformat(state["started_at"]) if state["started_at"] else datetime.now()
        ),
    )


@router.post("/message", response_model=OnboardingMessageResponse)
async def process_message(
    message_request: OnboardingMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OnboardingMessageResponse:
    """Process a user message during onboarding.

    Validates the user's response, saves progress, and returns the next prompt.
    """
    # Check onboarding state
    state = await onboarding_service.get_onboarding_state(db, current_user.id)

    if state["status"] == OnboardingStatus.NOT_STARTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding not started. Call /start first.",
        )

    if state["status"] == OnboardingStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed",
        )

    # Process the message using skill
    skill = SkillOnboardingShort(db_session=db)
    result = await skill.execute(
        {
            "user_id": str(current_user.id),
            "action": "process_response",
            "user_response": message_request.message,
        }
    )

    if not result.success or result.data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Failed to process message",
        )

    if not isinstance(result.data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid onboarding message response payload",
        )

    data = result.data
    is_valid = data.get("is_valid", True)
    validation_error = data.get("validation_error")
    next_step = data.get("next_step")
    next_message = data.get("next_message", "")

    # Get current step for response
    current_step = data.get("current_step", state["current_step"])

    # If valid and there's a next message, use it
    assistant_message = next_message if is_valid and next_message else ""

    # If invalid, provide feedback
    if not is_valid:
        assistant_message = validation_error or "Por favor, tente novamente."

    return OnboardingMessageResponse(
        current_step=current_step or "welcome",
        next_step=next_step,
        assistant_message=assistant_message,
        is_step_complete=is_valid,
        validation_error=validation_error if not is_valid else None,
    )


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
    """Skip onboarding and mark as completed.

    This allows users to skip the onboarding flow entirely.
    """
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
