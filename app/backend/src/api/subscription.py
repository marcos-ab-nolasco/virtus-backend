"""Subscription API endpoints for subscription management."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user
from src.core.rate_limit import limiter_authenticated
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.subscription import SubscriptionResponse, SubscriptionUpdate
from src.services import subscription as subscription_service

router = APIRouter(prefix="/me/subscription", tags=["subscription"])


@router.get("", response_model=SubscriptionResponse)
@limiter_authenticated.limit("20/minute")
async def get_my_subscription(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Get current user's subscription.

    Returns:
        SubscriptionResponse with tier, status, and validity dates
    """
    subscription = await subscription_service.get_user_subscription(db, current_user.id)
    return SubscriptionResponse.model_validate(subscription)


@router.patch("", response_model=SubscriptionResponse)
@limiter_authenticated.limit("10/minute")
async def update_my_subscription(
    request: Request,
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Update current user's subscription (partial update).

    Args:
        subscription_update: Subscription fields to update (only provided fields will be updated)

    Returns:
        Updated SubscriptionResponse
    """
    subscription = await subscription_service.update_user_subscription(
        db, current_user.id, subscription_update
    )
    return SubscriptionResponse.model_validate(subscription)
