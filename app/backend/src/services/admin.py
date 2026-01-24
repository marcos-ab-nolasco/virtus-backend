"""Admin service layer for user management."""

import logging
from datetime import time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import _get_user_by_id
from src.db.models.user import User
from src.db.models.user_preferences import CommunicationStyle, UserPreferences, WeekDay
from src.db.models.user_profile import OnboardingStatus, UserProfile
from src.services import preferences as preferences_service
from src.services import profile as profile_service

logger = logging.getLogger(__name__)

# Defaults for resetting preferences
_PREFERENCES_DEFAULTS = {
    "timezone": "UTC",
    "morning_checkin_enabled": True,
    "morning_checkin_time": time(8, 0),
    "evening_checkin_enabled": True,
    "evening_checkin_time": time(21, 0),
    "weekly_review_day": WeekDay.SUNDAY,
    "week_start_day": WeekDay.MONDAY,
    "language": "pt-BR",
    "communication_style": CommunicationStyle.DIRECT,
    "coach_name": "Virtus",
}

_PROFILE_RESET_FIELDS = [
    "vision_5_years",
    "vision_5_years_themes",
    "main_obstacle",
    "annual_objectives",
    "observed_patterns",
    "moral_profile",
    "strengths",
    "interests",
    "energy_activities",
    "drain_activities",
    "satisfaction_health",
    "satisfaction_work",
    "satisfaction_relationships",
    "satisfaction_personal_time",
    "dashboard_updated_at",
]


async def list_users(db: AsyncSession, *, limit: int, offset: int) -> tuple[list[User], int]:
    """List users with pagination."""
    count_result = await db.execute(select(func.count()).select_from(User))
    total = int(count_result.scalar_one())

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = list(result.scalars().all())
    return users, total


async def _get_user_or_404(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def block_user(db: AsyncSession, *, target_user_id: UUID, actor_user_id: UUID) -> User:
    """Block a user by setting is_blocked."""
    if target_user_id == actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin cannot block themselves",
        )

    user = await _get_user_or_404(db, target_user_id)
    user.is_blocked = True
    await db.commit()
    await db.refresh(user)
    await _get_user_by_id.invalidate(db, target_user_id)  # type: ignore[attr-defined]
    return user


async def unblock_user(db: AsyncSession, *, target_user_id: UUID, actor_user_id: UUID) -> User:
    """Unblock a user by clearing is_blocked."""
    if target_user_id == actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin cannot unblock themselves",
        )

    user = await _get_user_or_404(db, target_user_id)
    user.is_blocked = False
    await db.commit()
    await db.refresh(user)
    await _get_user_by_id.invalidate(db, target_user_id)  # type: ignore[attr-defined]
    return user


async def delete_user(db: AsyncSession, *, target_user_id: UUID, actor_user_id: UUID) -> None:
    """Delete a user (hard delete)."""
    if target_user_id == actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin cannot delete themselves",
        )

    user = await _get_user_or_404(db, target_user_id)

    if user.is_admin:
        count_result = await db.execute(select(func.count()).where(User.is_admin.is_(True)))
        admin_count = int(count_result.scalar_one())
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last admin",
            )

    await db.delete(user)
    await db.commit()
    await _get_user_by_id.invalidate(db, target_user_id)  # type: ignore[attr-defined]


async def get_user_onboarding(
    db: AsyncSession, *, target_user_id: UUID
) -> tuple[UserProfile, UserPreferences]:
    """Fetch onboarding-related data for a user."""
    profile = await profile_service.get_user_profile(db, target_user_id)
    preferences = await preferences_service.get_user_preferences(db, target_user_id)
    return profile, preferences


async def reset_user_onboarding(
    db: AsyncSession, *, target_user_id: UUID, actor_user_id: UUID
) -> tuple[UserProfile, UserPreferences]:
    """Reset onboarding data, profile fields, and preferences to defaults."""
    profile = await profile_service.get_user_profile(db, target_user_id)
    preferences = await preferences_service.get_user_preferences(db, target_user_id)

    profile.onboarding_status = OnboardingStatus.NOT_STARTED
    profile.onboarding_started_at = None
    profile.onboarding_completed_at = None
    profile.onboarding_current_step = None
    profile.onboarding_data = None

    for field in _PROFILE_RESET_FIELDS:
        setattr(profile, field, None)

    for field, value in _PREFERENCES_DEFAULTS.items():
        setattr(preferences, field, value)

    await db.commit()
    await db.refresh(profile)
    await db.refresh(preferences)

    logger.info(
        "Admin reset onboarding: actor_user_id=%s target_user_id=%s",
        actor_user_id,
        target_user_id,
    )

    return profile, preferences
