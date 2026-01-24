"""Test admin user management endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_preferences import CommunicationStyle, UserPreferences, WeekDay
from src.db.models.user_profile import OnboardingStatus, UserProfile


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


@pytest.mark.asyncio
async def test_admin_can_get_onboarding_data(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Admin can read onboarding data for a user."""
    user = User(
        email="onboarding@example.com",
        hashed_password="hashed",
        full_name="Onboarding User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile_result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one()
    profile.onboarding_status = OnboardingStatus.IN_PROGRESS
    profile.onboarding_data = {"name": "Maria", "goals": ["Goal 1"]}
    profile.vision_5_years = "Vision"

    preferences_result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    preferences = preferences_result.scalar_one()
    preferences.timezone = "America/Sao_Paulo"
    preferences.communication_style = CommunicationStyle.MOTIVATING

    await db_session.commit()

    response = await client.get(f"/admin/users/{user.id}/onboarding", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user.id)
    assert data["profile"]["onboarding_status"] == "IN_PROGRESS"
    assert data["profile"]["onboarding_data"]["name"] == "Maria"
    assert data["preferences"]["timezone"] == "America/Sao_Paulo"


@pytest.mark.asyncio
async def test_admin_can_reset_onboarding(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Admin can reset onboarding data and preferences for a user."""
    user = User(
        email="reset@example.com",
        hashed_password="hashed",
        full_name="Reset User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile_result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one()
    profile.onboarding_status = OnboardingStatus.COMPLETED
    profile.onboarding_data = {"name": "Ana"}
    profile.vision_5_years = "Old vision"
    profile.satisfaction_health = 7

    preferences_result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    preferences = preferences_result.scalar_one()
    preferences.timezone = "America/Sao_Paulo"
    preferences.weekly_review_day = WeekDay.MONDAY
    preferences.communication_style = CommunicationStyle.GENTLE

    await db_session.commit()

    response = await client.post(
        f"/admin/users/{user.id}/onboarding/reset",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["onboarding_status"] == "NOT_STARTED"
    assert data["profile"]["onboarding_data"] is None
    assert data["preferences"]["timezone"] == "UTC"
    assert data["preferences"]["communication_style"] == "DIRECT"

    profile_result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one()
    assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
    assert profile.onboarding_data is None
    assert profile.vision_5_years is None
    assert profile.satisfaction_health is None

    preferences_result = await db_session.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    preferences = preferences_result.scalar_one()
    assert preferences.timezone == "UTC"
    assert preferences.weekly_review_day == WeekDay.SUNDAY
    assert preferences.communication_style == CommunicationStyle.DIRECT


@pytest.mark.asyncio
async def test_admin_onboarding_access_denied_for_non_admin(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Non-admin users should be denied onboarding reset access."""
    user = User(
        email="member2@example.com",
        hashed_password="hashed",
        full_name="Member User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    response = await client.post(
        f"/admin/users/{user.id}/onboarding/reset",
        headers=auth_headers,
    )
    assert response.status_code == 403
