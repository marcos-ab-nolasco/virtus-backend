"""Admin API endpoints for user management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import require_admin
from src.db.models.user import User
from src.db.session import get_db
from src.schemas.admin import AdminUserList
from src.schemas.user import UserRead
from src.services import admin as admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserList)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_admin)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AdminUserList:
    """List users with pagination."""
    users, total = await admin_service.list_users(db, limit=limit, offset=offset)
    return AdminUserList(
        users=[UserRead.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/users/{user_id}/block", response_model=UserRead)
async def block_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_admin)],
) -> UserRead:
    """Block a user."""
    user = await admin_service.block_user(
        db, target_user_id=user_id, actor_user_id=current_admin.id
    )
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}/unblock", response_model=UserRead)
async def unblock_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_admin)],
) -> UserRead:
    """Unblock a user."""
    user = await admin_service.unblock_user(
        db, target_user_id=user_id, actor_user_id=current_admin.id
    )
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_admin)],
) -> None:
    """Delete a user."""
    await admin_service.delete_user(db, target_user_id=user_id, actor_user_id=current_admin.id)
    return None
