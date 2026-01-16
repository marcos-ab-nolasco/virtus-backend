"""Admin service layer for user management."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import _get_user_by_id
from src.db.models.user import User


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
