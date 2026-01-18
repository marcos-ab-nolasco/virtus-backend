"""Preferences API endpoints for user settings management."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.core.rate_limit import limiter_authenticated
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate
from src.services import preferences as preferences_service

router = APIRouter(prefix="/me/preferences", tags=["preferences"])


@router.get("", response_model=UserPreferencesResponse)
@limiter_authenticated.limit("20/minute")
async def get_my_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Get current user's preferences.

    Returns:
        UserPreferencesResponse with all settings
    """
    preferences = await preferences_service.get_user_preferences(db, current_user.id)
    return UserPreferencesResponse.model_validate(preferences)


@router.patch("", response_model=UserPreferencesResponse)
@limiter_authenticated.limit("10/minute")
async def update_my_preferences(
    request: Request,
    preferences_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    """Update current user's preferences (partial update).

    Args:
        preferences_update: Preference fields to update (only provided fields will be updated)

    Returns:
        Updated UserPreferencesResponse
    """
    preferences = await preferences_service.update_user_preferences(
        db, current_user.id, preferences_update
    )
    return UserPreferencesResponse.model_validate(preferences)
