"""Subscription service layer for business logic.

Handles Subscription CRUD operations with tier-based access control and Redis caching.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache.decorator import redis_cache_decorator
from src.db.models.subscription import Subscription, SubscriptionTier
from src.schemas.subscription import SubscriptionUpdate


@redis_cache_decorator(ttl=180, ignore_positionals=[0], namespace="subscription")
async def get_user_subscription(db: AsyncSession, user_id: uuid.UUID) -> Subscription:
    """Get user subscription by user_id with Redis caching.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Subscription instance

    Raises:
        HTTPException: 404 if subscription not found
    """
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User subscription not found",
        )

    return subscription


async def update_user_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
    subscription_update: SubscriptionUpdate,
) -> Subscription:
    """Update user subscription (partial update).

    Args:
        db: Database session
        user_id: UUID of the user
        subscription_update: Subscription update data (only provided fields will be updated)

    Returns:
        Updated Subscription instance

    Raises:
        HTTPException: 404 if subscription not found
    """
    # Get existing subscription (bypasses cache to ensure fresh data)
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User subscription not found",
        )

    # Update only provided fields (exclude_unset=True for partial updates)
    update_data = subscription_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)

    await db.commit()
    await db.refresh(subscription)

    return subscription


async def check_subscription_access(
    db: AsyncSession,
    user_id: uuid.UUID,
    required_tier: SubscriptionTier,
) -> bool:
    """Check if user's subscription tier meets the required tier level.

    Uses tier hierarchy: FREE (0) < TRIAL (1) < PAID (2)

    Args:
        db: Database session
        user_id: UUID of the user
        required_tier: Minimum required subscription tier

    Returns:
        True if user has sufficient tier access, False otherwise

    Raises:
        HTTPException: 404 if subscription not found
    """
    subscription = await get_user_subscription(db, user_id)

    # Compare using the __ge__ method defined in SubscriptionTier enum
    return subscription.tier >= required_tier
