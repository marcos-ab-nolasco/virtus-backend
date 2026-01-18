"""Tests for onboarding API endpoints.

Issue 3.4: Tests for /onboarding endpoints.
Following TDD - RED phase: write failing tests first.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


class TestOnboardingStartEndpoint:
    """Test POST /onboarding/start endpoint."""

    @pytest.mark.asyncio
    async def test_start_onboarding_success(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Should start onboarding for authenticated user."""
        response = await client.post("/api/v1/onboarding/start", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["current_step"] == "welcome"
        assert "message" in data
        assert "started_at" in data

    @pytest.mark.asyncio
    async def test_start_onboarding_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.post("/api/v1/onboarding/start")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_start_onboarding_already_completed(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Should return error if onboarding already completed."""
        # Set user as completed
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_status = OnboardingStatus.COMPLETED
        await db_session.commit()

        response = await client.post("/api/v1/onboarding/start", headers=auth_headers)
        assert response.status_code == 400
        assert "already completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_onboarding_idempotent_for_in_progress(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Starting when IN_PROGRESS should return current state."""
        # Start onboarding first
        response1 = await client.post("/api/v1/onboarding/start", headers=auth_headers)
        assert response1.status_code == 200

        # Try to start again - should return current state
        response2 = await client.post("/api/v1/onboarding/start", headers=auth_headers)
        assert response2.status_code == 200
        assert response2.json()["status"] == "IN_PROGRESS"


class TestOnboardingMessageEndpoint:
    """Test POST /onboarding/message endpoint."""

    @pytest.mark.asyncio
    async def test_message_endpoint_processes_response(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Should process user message and return assistant response."""
        # Start onboarding first
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        # Send message
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Olá!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "assistant_message" in data
        assert "current_step" in data

    @pytest.mark.asyncio
    async def test_message_endpoint_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.post(
            "/api/v1/onboarding/message",
            json={"message": "test"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_message_endpoint_validates_message(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Should validate message is not empty."""
        # Start onboarding
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        # Send empty message
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": ""},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_message_endpoint_returns_validation_error(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Should return validation error for invalid responses."""
        # Start onboarding
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        # Advance to name step
        await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "ok"},
        )

        # Send whitespace-only name (invalid)
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "   "},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_step_complete"] is False
        assert "validation_error" in data


class TestOnboardingStatusEndpoint:
    """Test GET /onboarding/status endpoint."""

    @pytest.mark.asyncio
    async def test_status_returns_not_started(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Should return NOT_STARTED for new user."""
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "NOT_STARTED"
        assert data["current_step"] is None
        assert data["progress_percent"] == 0

    @pytest.mark.asyncio
    async def test_status_returns_progress(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Should return current onboarding progress."""
        # Start onboarding
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["current_step"] == "welcome"
        assert "progress_percent" in data
        assert "started_at" in data

    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.get("/api/v1/onboarding/status")
        assert response.status_code == 401


class TestOnboardingSkipEndpoint:
    """Test PATCH /onboarding/skip endpoint."""

    @pytest.mark.asyncio
    async def test_skip_marks_completed(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Should mark onboarding as completed when skipped."""
        response = await client.patch("/api/v1/onboarding/skip", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert "completed_at" in data

    @pytest.mark.asyncio
    async def test_skip_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.patch("/api/v1/onboarding/skip")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_skip_already_completed(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Should return error if already completed."""
        # Skip once
        await client.patch("/api/v1/onboarding/skip", headers=auth_headers)

        # Try to skip again
        response = await client.patch("/api/v1/onboarding/skip", headers=auth_headers)
        assert response.status_code == 400
