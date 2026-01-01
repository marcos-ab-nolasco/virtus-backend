"""Profile API endpoints for user profile management."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.core.rate_limit import limiter_authenticated
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.user_profile import UserProfileResponse, UserProfileUpdate
from src.services import profile as profile_service

router = APIRouter(prefix="/me/profile", tags=["profile"])


@router.get("", response_model=UserProfileResponse)
@limiter_authenticated.limit("20/minute")
async def get_my_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Get current user's profile.

    Returns:
        UserProfileResponse with all profile data
    """
    profile = await profile_service.get_user_profile(db, current_user.id)
    return UserProfileResponse.model_validate(profile)


@router.patch("", response_model=UserProfileResponse)
@limiter_authenticated.limit("10/minute")
async def update_my_profile(
    request: Request,
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Update current user's profile (partial update).

    Args:
        profile_update: Profile fields to update (only provided fields will be updated)

    Returns:
        Updated UserProfileResponse
    """
    profile = await profile_service.update_user_profile(db, current_user.id, profile_update)
    return UserProfileResponse.model_validate(profile)
