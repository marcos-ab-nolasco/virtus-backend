"""Onboarding service layer for business logic.

Issue 3.6: Handles onboarding state persistence with proper error handling.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user_profile import OnboardingStatus, UserProfile

# Onboarding step sequence
ONBOARDING_STEPS = ["welcome", "name", "goals", "preferences", "conclusion"]

# Step to progress percentage mapping
STEP_PROGRESS = {
    "welcome": 0,
    "name": 20,
    "goals": 40,
    "preferences": 60,
    "conclusion": 80,
}


async def _get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Get user profile by user_id.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        UserProfile instance

    Raises:
        HTTPException: 404 if profile not found
    """
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    return profile


async def start_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Start the onboarding process for a user.

    Sets status to IN_PROGRESS, sets started_at timestamp,
    sets current_step to 'welcome', and initializes empty onboarding_data.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Updated UserProfile instance

    Raises:
        HTTPException: 400 if onboarding already completed, 404 if user not found
    """
    profile = await _get_user_profile(db, user_id)

    if profile.onboarding_status == OnboardingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed for this user",
        )

    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    profile.onboarding_started_at = datetime.now(UTC)
    profile.onboarding_current_step = "welcome"
    profile.onboarding_data = {}

    await db.commit()
    await db.refresh(profile)

    return profile


async def get_onboarding_state(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    """Get the current onboarding state for a user.

    Returns a dictionary with status, current_step, progress percentage,
    started_at timestamp, completed_at timestamp, and collected data.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Dictionary with onboarding state information
    """
    profile = await _get_user_profile(db, user_id)

    # Calculate progress percentage
    progress = 0
    if profile.onboarding_status == OnboardingStatus.COMPLETED:
        progress = 100
    elif profile.onboarding_current_step:
        progress = STEP_PROGRESS.get(profile.onboarding_current_step, 0)

    return {
        "status": profile.onboarding_status.value,
        "current_step": profile.onboarding_current_step,
        "progress_percent": progress,
        "started_at": (
            profile.onboarding_started_at.isoformat() if profile.onboarding_started_at else None
        ),
        "completed_at": (
            profile.onboarding_completed_at.isoformat() if profile.onboarding_completed_at else None
        ),
        "data": profile.onboarding_data or {},
    }


async def save_step_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    step: str,
    data: dict[str, Any],
    user_response: str | None = None,
) -> UserProfile:
    """Save a step response to the user's onboarding data.

    Merges the provided data into onboarding_data and optionally
    appends to conversation_history.

    Args:
        db: Database session
        user_id: UUID of the user
        step: Current step name
        data: Data to save (e.g., {"name": "João"})
        user_response: Optional raw user response for history

    Returns:
        Updated UserProfile instance
    """
    profile = await _get_user_profile(db, user_id)

    # Ensure onboarding_data is a dict
    if profile.onboarding_data is None:
        profile.onboarding_data = {}

    # Create a copy to trigger SQLAlchemy change detection for JSONB
    current_data = dict(profile.onboarding_data)

    # Merge new data
    current_data.update(data)

    # Add to conversation history if user_response provided
    if user_response is not None:
        if "conversation_history" not in current_data:
            current_data["conversation_history"] = []

        current_data["conversation_history"].append(
            {
                "step": step,
                "timestamp": datetime.now(UTC).isoformat(),
                "user_response": user_response,
            }
        )

    # Assign back to trigger change detection
    profile.onboarding_data = current_data

    await db.commit()
    await db.refresh(profile)

    return profile


async def advance_step(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Advance to the next onboarding step.

    If at the conclusion step, completes the onboarding.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Updated UserProfile instance
    """
    profile = await _get_user_profile(db, user_id)

    current_step = profile.onboarding_current_step

    if current_step is None:
        # Not started, set to first step
        profile.onboarding_current_step = ONBOARDING_STEPS[0]
    elif current_step == "conclusion":
        # At conclusion, complete onboarding
        return await complete_onboarding(db, user_id)
    else:
        # Find current index and advance
        try:
            current_index = ONBOARDING_STEPS.index(current_step)
            next_index = current_index + 1
            if next_index < len(ONBOARDING_STEPS):
                profile.onboarding_current_step = ONBOARDING_STEPS[next_index]
            else:
                # Past last step, complete
                return await complete_onboarding(db, user_id)
        except ValueError:
            # Unknown step, reset to first
            profile.onboarding_current_step = ONBOARDING_STEPS[0]

    await db.commit()
    await db.refresh(profile)

    return profile


async def complete_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Mark onboarding as completed.

    Sets status to COMPLETED and sets completed_at timestamp.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Updated UserProfile instance
    """
    profile = await _get_user_profile(db, user_id)

    profile.onboarding_status = OnboardingStatus.COMPLETED
    profile.onboarding_completed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(profile)

    return profile


async def check_session_timeout(db: AsyncSession, user_id: uuid.UUID, max_days: int = 7) -> bool:
    """Check if the onboarding session has timed out.

    If the session is IN_PROGRESS and started more than max_days ago,
    resets the onboarding state.

    Args:
        db: Database session
        user_id: UUID of the user
        max_days: Maximum days before session times out

    Returns:
        True if session was reset, False otherwise
    """
    profile = await _get_user_profile(db, user_id)

    # Only check IN_PROGRESS sessions
    if profile.onboarding_status != OnboardingStatus.IN_PROGRESS:
        return False

    # Check if started_at is set and older than max_days
    if profile.onboarding_started_at:
        elapsed = datetime.now(UTC) - profile.onboarding_started_at
        if elapsed > timedelta(days=max_days):
            # Reset onboarding
            profile.onboarding_status = OnboardingStatus.NOT_STARTED
            profile.onboarding_started_at = None
            profile.onboarding_current_step = None
            profile.onboarding_data = None

            await db.commit()
            await db.refresh(profile)
            return True

    return False


async def reset_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Reset onboarding state to NOT_STARTED.

    Clears all onboarding fields.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Updated UserProfile instance
    """
    profile = await _get_user_profile(db, user_id)

    profile.onboarding_status = OnboardingStatus.NOT_STARTED
    profile.onboarding_started_at = None
    profile.onboarding_current_step = None
    profile.onboarding_data = None
    profile.onboarding_completed_at = None

    await db.commit()
    await db.refresh(profile)

    return profile


async def skip_onboarding(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Skip onboarding and mark as completed.

    This allows users to skip the onboarding flow entirely.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Updated UserProfile instance

    Raises:
        HTTPException: 400 if onboarding already completed
    """
    profile = await _get_user_profile(db, user_id)

    if profile.onboarding_status == OnboardingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed for this user",
        )

    profile.onboarding_status = OnboardingStatus.COMPLETED
    profile.onboarding_completed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(profile)

    return profile
