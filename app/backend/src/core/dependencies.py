import logging
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache.decorator import redis_cache_decorator
from src.core.security import decode_token
from src.db.models.subscription import SubscriptionTier
from src.db.models.user import User
from src.db.session import get_db

http_bearer_scheme = HTTPBearer()

logger = logging.getLogger(__name__)


@redis_cache_decorator(
    ttl=180,
    ignore_positionals=[0],
    namespace="auth.user_by_id",
)
async def _get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Fetch user by ID from database (cached).

    This internal function is cached to reduce database load for authentication.
    The cache key is based on user_id, making it resilient to token refresh.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency to get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid token: reason=decode_failed error={str(e)}")
        raise credentials_exception from e

    # Check token type
    if payload.get("type") != "access":
        logger.warning(f"Invalid token: reason=wrong_token_type token_type={payload.get('type')}")
        raise credentials_exception

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        logger.warning("Invalid token: reason=missing_subject")
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid token: reason=invalid_uuid_format user_id_str={user_id_str}")
        raise credentials_exception from e

    # Fetch user from database (cached by user_id)
    user = await _get_user_by_id(db, user_id)

    if user is None:
        logger.warning(f"Invalid token: reason=user_not_found user_id={user_id}")
        raise credentials_exception
    if user.is_blocked:
        logger.warning(f"Blocked user access denied: user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked",
        )

    # Store user_id in request state for middleware logging
    request.state.user_id = str(user_id)

    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency to ensure the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_tier(required_tier: SubscriptionTier) -> Callable:
    """Create a dependency that checks if user has required subscription tier.

    Args:
        required_tier: Minimum subscription tier required (FREE, TRIAL, or PAID)

    Returns:
        FastAPI dependency function that enforces tier-based access control

    Example:
        @router.get("/premium-feature", dependencies=[Depends(require_tier(SubscriptionTier.PAID))])
        async def premium_endpoint():
            # This endpoint requires PAID tier
            return {"premium": "content"}
    """

    async def tier_checker(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        """Verify that current user's subscription meets the required tier."""
        from src.services.subscription import check_subscription_access

        has_access = await check_subscription_access(db, current_user.id, required_tier)

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {required_tier.value} subscription tier or higher",
            )

        return current_user

    return tier_checker
