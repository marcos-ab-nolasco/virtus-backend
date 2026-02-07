"""Tests for onboarding status and skip API endpoints.

Tests the rewritten onboarding API with only GET /status and PATCH /skip.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


class TestOnboardingStatusEndpoint:
    """Test GET /onboarding/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_returns_not_started_for_new_user(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """GET /status should return NOT_STARTED for a new user."""
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "NOT_STARTED"
        assert data["current_step"] is None
        assert data["progress_percent"] == 0
        assert data["started_at"] is None
        assert data["completed_at"] is None

    @pytest.mark.asyncio
    async def test_get_status_returns_in_progress_with_step(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ):
        """GET /status should return IN_PROGRESS with current step."""
        # Set onboarding to IN_PROGRESS
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_status = OnboardingStatus.IN_PROGRESS
        profile.onboarding_started_at = datetime.now(UTC)
        profile.onboarding_current_step = "name"
        await db_session.commit()

        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["current_step"] == "name"
        assert data["progress_percent"] == 14
        assert data["started_at"] is not None


class TestOnboardingSkipEndpoint:
    """Test PATCH /onboarding/skip endpoint."""

    @pytest.mark.asyncio
    async def test_skip_onboarding_marks_completed(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
    ):
        """PATCH /skip should mark onboarding as completed."""
        response = await client.patch("/api/v1/onboarding/skip", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_skip_onboarding_already_completed_returns_400(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ):
        """PATCH /skip should return 400 if already completed."""
        # Set onboarding as completed
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_status = OnboardingStatus.COMPLETED
        profile.onboarding_completed_at = datetime.now(UTC)
        await db_session.commit()

        response = await client.patch("/api/v1/onboarding/skip", headers=auth_headers)

        assert response.status_code == 400
