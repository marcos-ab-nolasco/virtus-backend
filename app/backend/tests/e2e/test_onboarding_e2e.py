"""End-to-end tests for onboarding flow.

Issue 3.7: Complete flow tests for onboarding.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


class TestOnboardingCompleteFlow:
    """E2E tests for complete onboarding flow."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test complete flow: start -> all steps -> completion."""
        # 1. Start onboarding
        response = await client.post("/api/v1/onboarding/start", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["current_step"] == "welcome"

        # 2. Welcome step - send any response to proceed
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Olá! Vamos começar!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_step_complete"] is True
        assert data["next_step"] == "name"

        # 3. Name step
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "João Silva"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_step_complete"] is True
        assert data["next_step"] == "goals"

        # 4. Goals step
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Quero crescer na carreira e cuidar melhor da minha saúde"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_step_complete"] is True
        assert data["next_step"] == "preferences"

        # 5. Preferences step
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "America/Sao_Paulo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_step_complete"] is True
        assert data["next_step"] == "conclusion"

        # 6. Conclusion step - final response
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Sim, vamos começar!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_step_complete"] is True
        assert data["next_step"] is None  # No more steps

        # 7. Verify completion via status endpoint
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["progress_percent"] == 100
        assert data["completed_at"] is not None


class TestOnboardingResumeFlow:
    """E2E tests for resuming onboarding."""

    @pytest.mark.asyncio
    async def test_resume_onboarding_from_saved_state(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        """Test resuming onboarding from saved state."""
        # 1. Start and progress through welcome and name
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Olá!"},
        )

        await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Maria Santos"},
        )

        # 2. Verify state is at goals step
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)
        assert response.json()["current_step"] == "goals"

        # 3. "Leave" (simulate by getting fresh status)
        # 4. "Return" - check status shows saved state
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["current_step"] == "goals"

        # 5. Continue from goals
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Melhorar minha produtividade"},
        )
        assert response.status_code == 200
        assert response.json()["next_step"] == "preferences"


class TestOnboardingSkipFlow:
    """E2E tests for skipping onboarding."""

    @pytest.mark.asyncio
    async def test_skip_onboarding_flow(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test skipping onboarding entirely."""
        # 1. Initial status should be NOT_STARTED
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)
        assert response.json()["status"] == "NOT_STARTED"

        # 2. Skip onboarding
        response = await client.patch("/api/v1/onboarding/skip", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["completed_at"] is not None

        # 3. Verify status shows COMPLETED
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)
        assert response.json()["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_skip_onboarding_midway(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test skipping onboarding after starting."""
        # 1. Start onboarding
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        # 2. Progress through welcome
        await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "ok"},
        )

        # 3. Skip midway
        response = await client.patch("/api/v1/onboarding/skip", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"


class TestOnboardingValidationFlow:
    """E2E tests for validation during onboarding."""

    @pytest.mark.asyncio
    async def test_validation_error_does_not_advance_step(
        self, client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test that validation errors don't advance the step."""
        # 1. Start and get to name step
        await client.post("/api/v1/onboarding/start", headers=auth_headers)
        await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "ok"},
        )

        # 2. Send invalid name (whitespace only)
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "   "},
        )
        data = response.json()
        assert data["is_step_complete"] is False
        assert data["validation_error"] is not None

        # 3. Still at name step
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)
        assert response.json()["current_step"] == "name"

        # 4. Now send valid name
        response = await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Carlos Silva"},
        )
        assert response.json()["is_step_complete"] is True
        assert response.json()["next_step"] == "goals"


class TestOnboardingTimeoutFlow:
    """E2E tests for session timeout."""

    @pytest.mark.asyncio
    async def test_timeout_resets_onboarding(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        """Test that session timeout resets onboarding state."""
        from src.services.onboarding import check_session_timeout

        # 1. Start onboarding
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        # 2. Manually set started_at to 10 days ago
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_started_at = datetime.now(UTC) - timedelta(days=10)
        await db_session.commit()

        # 3. Check timeout (would be called by API in real scenario)
        was_reset = await check_session_timeout(db_session, test_user.id, max_days=7)
        assert was_reset is True

        # 4. Verify status is reset to NOT_STARTED
        # Note: The actual API doesn't call check_session_timeout automatically,
        # but the state should be NOT_STARTED after the reset
        await db_session.refresh(profile)
        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED


class TestOnboardingDataPersistence:
    """E2E tests for data persistence during onboarding."""

    @pytest.mark.asyncio
    async def test_collected_data_is_persisted(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user: User
    ):
        """Test that collected data is persisted in UserProfile."""
        # 1. Complete onboarding
        await client.post("/api/v1/onboarding/start", headers=auth_headers)

        # Welcome
        await client.post(
            "/api/v1/onboarding/message", headers=auth_headers, json={"message": "Olá!"}
        )

        # Name
        await client.post(
            "/api/v1/onboarding/message", headers=auth_headers, json={"message": "Ana Paula"}
        )

        # Goals
        await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "Emagrecer, aprender inglês"},
        )

        # Preferences
        await client.post(
            "/api/v1/onboarding/message",
            headers=auth_headers,
            json={"message": "America/Sao_Paulo"},
        )

        # 2. Check that data was saved to UserProfile
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()

        assert profile.onboarding_data is not None
        assert profile.onboarding_data.get("name") == "Ana Paula"
        assert "goals" in profile.onboarding_data
        assert len(profile.onboarding_data["goals"]) >= 1
        # Preferences are saved directly (timezone, language) not nested
        assert profile.onboarding_data.get("timezone") == "America/Sao_Paulo"
        assert profile.onboarding_data.get("language") == "pt-BR"
