"""Preferences service layer for business logic.

Handles UserPreferences CRUD operations with proper error handling and authorization.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user_preferences import UserPreferences
from src.schemas.user_preferences import UserPreferencesUpdate


async def get_user_preferences(db: AsyncSession, user_id: uuid.UUID) -> UserPreferences:
    """Get user preferences by user_id.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        UserPreferences instance

    Raises:
        HTTPException: 404 if preferences not found
    """
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))
    preferences = result.scalar_one_or_none()

    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User preferences not found",
        )

    return preferences


async def update_user_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
    preferences_update: UserPreferencesUpdate,
) -> UserPreferences:
    """Update user preferences (partial update).

    Args:
        db: Database session
        user_id: UUID of the user
        preferences_update: Preferences update data (only provided fields will be updated)

    Returns:
        Updated UserPreferences instance

    Raises:
        HTTPException: 404 if preferences not found
    """
    # Get existing preferences
    preferences = await get_user_preferences(db, user_id)

    # Update only provided fields (exclude_unset=True for partial updates)
    update_data = preferences_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)

    await db.commit()
    await db.refresh(preferences)

    return preferences
