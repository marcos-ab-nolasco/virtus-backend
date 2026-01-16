"""Test admin user management endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User


@pytest.mark.asyncio
async def test_admin_access_denied_for_non_admin(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Non-admin users should be denied access."""
    response = await client.get("/admin/users", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_block_and_unblock_user(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Admin can block and unblock another user."""
    user = User(
        email="member@example.com",
        hashed_password="hashed",
        full_name="Member User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    response = await client.patch(f"/admin/users/{user.id}/block", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_blocked"] is True

    response = await client.patch(f"/admin/users/{user.id}/unblock", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_blocked"] is False


@pytest.mark.asyncio
async def test_admin_cannot_block_self(
    client: AsyncClient, admin_headers: dict[str, str], admin_user: User
) -> None:
    """Admin cannot block themselves."""
    response = await client.patch(f"/admin/users/{admin_user.id}/block", headers=admin_headers)
    assert response.status_code == 409
