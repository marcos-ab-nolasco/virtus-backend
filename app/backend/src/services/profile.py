"""Profile service layer for business logic.

Handles UserProfile CRUD operations with proper error handling and authorization.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user_profile import UserProfile
from src.schemas.user_profile import UserProfileUpdate


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
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


async def update_user_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    profile_update: UserProfileUpdate,
) -> UserProfile:
    """Update user profile (partial update).

    Args:
        db: Database session
        user_id: UUID of the user
        profile_update: Profile update data (only provided fields will be updated)

    Returns:
        Updated UserProfile instance

    Raises:
        HTTPException: 404 if profile not found
    """
    # Get existing profile
    profile = await get_user_profile(db, user_id)

    # Update only provided fields (exclude_unset=True for partial updates)
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return profile
