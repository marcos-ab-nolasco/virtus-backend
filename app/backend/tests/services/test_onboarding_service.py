"""Tests for OnboardingService.

Issue 3.6: Tests for onboarding state persistence service.
Following TDD - RED phase: write failing tests first.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


class TestOnboardingServiceStart:
    """Test OnboardingService.start_onboarding method."""

    @pytest.mark.asyncio
    async def test_start_onboarding_sets_status_to_in_progress(
        self, db_session: AsyncSession, test_user: User
    ):
        """start_onboarding should set status to IN_PROGRESS."""
        from src.services.onboarding import start_onboarding

        profile = await start_onboarding(db_session, test_user.id)

        assert profile.onboarding_status == OnboardingStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_start_onboarding_sets_started_at(
        self, db_session: AsyncSession, test_user: User
    ):
        """start_onboarding should set onboarding_started_at timestamp."""
        from src.services.onboarding import start_onboarding

        before = datetime.now(UTC)
        profile = await start_onboarding(db_session, test_user.id)
        after = datetime.now(UTC)

        assert profile.onboarding_started_at is not None
        assert before <= profile.onboarding_started_at <= after

    @pytest.mark.asyncio
    async def test_start_onboarding_sets_current_step_to_welcome(
        self, db_session: AsyncSession, test_user: User
    ):
        """start_onboarding should set current_step to 'welcome'."""
        from src.services.onboarding import start_onboarding

        profile = await start_onboarding(db_session, test_user.id)

        assert profile.onboarding_current_step == "welcome"

    @pytest.mark.asyncio
    async def test_start_onboarding_initializes_empty_data(
        self, db_session: AsyncSession, test_user: User
    ):
        """start_onboarding should initialize onboarding_data as empty dict."""
        from src.services.onboarding import start_onboarding

        profile = await start_onboarding(db_session, test_user.id)

        assert profile.onboarding_data == {}

    @pytest.mark.asyncio
    async def test_start_onboarding_raises_if_already_completed(
        self, db_session: AsyncSession, test_user: User
    ):
        """start_onboarding should raise error if onboarding already completed."""
        from src.services.onboarding import start_onboarding

        # Set onboarding as completed
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_status = OnboardingStatus.COMPLETED
        profile.onboarding_completed_at = datetime.now(UTC)
        await db_session.commit()

        # Try to start again
        with pytest.raises(HTTPException) as exc_info:
            await start_onboarding(db_session, test_user.id)

        assert exc_info.value.status_code == 400
        assert "already completed" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_start_onboarding_raises_if_user_not_found(self, db_session: AsyncSession):
        """start_onboarding should raise 404 if user not found."""
        import uuid

        from src.services.onboarding import start_onboarding

        fake_user_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await start_onboarding(db_session, fake_user_id)

        assert exc_info.value.status_code == 404


class TestOnboardingServiceGetState:
    """Test OnboardingService.get_onboarding_state method."""

    @pytest.mark.asyncio
    async def test_get_onboarding_state_returns_current_state(
        self, db_session: AsyncSession, test_user: User
    ):
        """get_onboarding_state should return current onboarding state."""
        from src.services.onboarding import get_onboarding_state, start_onboarding

        # Start onboarding first
        await start_onboarding(db_session, test_user.id)

        state = await get_onboarding_state(db_session, test_user.id)

        assert state["status"] == OnboardingStatus.IN_PROGRESS.value
        assert state["current_step"] == "welcome"
        assert "started_at" in state
        assert "data" in state

    @pytest.mark.asyncio
    async def test_get_onboarding_state_returns_not_started(
        self, db_session: AsyncSession, test_user: User
    ):
        """get_onboarding_state should return NOT_STARTED for new users."""
        from src.services.onboarding import get_onboarding_state

        state = await get_onboarding_state(db_session, test_user.id)

        assert state["status"] == OnboardingStatus.NOT_STARTED.value
        assert state["current_step"] is None

    @pytest.mark.asyncio
    async def test_get_onboarding_state_calculates_progress(
        self, db_session: AsyncSession, test_user: User
    ):
        """get_onboarding_state should calculate progress percentage."""
        from src.services.onboarding import get_onboarding_state, start_onboarding

        await start_onboarding(db_session, test_user.id)
        state = await get_onboarding_state(db_session, test_user.id)

        assert "progress_percent" in state
        assert 0 <= state["progress_percent"] <= 100


class TestOnboardingServiceSaveStepResponse:
    """Test OnboardingService.save_step_response method."""

    @pytest.mark.asyncio
    async def test_save_step_response_stores_name(self, db_session: AsyncSession, test_user: User):
        """save_step_response should store name in onboarding_data."""
        from src.services.onboarding import save_step_response, start_onboarding

        await start_onboarding(db_session, test_user.id)
        profile = await save_step_response(
            db_session, test_user.id, step="name", data={"name": "João Silva"}
        )

        assert profile.onboarding_data is not None
        assert profile.onboarding_data["name"] == "João Silva"

    @pytest.mark.asyncio
    async def test_save_step_response_stores_goals(self, db_session: AsyncSession, test_user: User):
        """save_step_response should store goals in onboarding_data."""
        from src.services.onboarding import save_step_response, start_onboarding

        await start_onboarding(db_session, test_user.id)
        goals = ["career growth", "health improvement", "work-life balance"]
        profile = await save_step_response(
            db_session, test_user.id, step="goals", data={"goals": goals}
        )

        assert profile.onboarding_data["goals"] == goals

    @pytest.mark.asyncio
    async def test_save_step_response_stores_preferences(
        self, db_session: AsyncSession, test_user: User
    ):
        """save_step_response should store preferences in onboarding_data."""
        from src.services.onboarding import save_step_response, start_onboarding

        await start_onboarding(db_session, test_user.id)
        preferences = {"timezone": "America/Sao_Paulo", "language": "pt-BR"}
        profile = await save_step_response(
            db_session, test_user.id, step="preferences", data={"preferences": preferences}
        )

        assert profile.onboarding_data["preferences"] == preferences

    @pytest.mark.asyncio
    async def test_save_step_response_appends_to_history(
        self, db_session: AsyncSession, test_user: User
    ):
        """save_step_response should append to conversation_history."""
        from src.services.onboarding import save_step_response, start_onboarding

        await start_onboarding(db_session, test_user.id)
        profile = await save_step_response(
            db_session,
            test_user.id,
            step="name",
            data={"name": "João"},
            user_response="João Silva",
        )

        assert "conversation_history" in profile.onboarding_data
        assert len(profile.onboarding_data["conversation_history"]) >= 1
        history_entry = profile.onboarding_data["conversation_history"][-1]
        assert history_entry["step"] == "name"
        assert history_entry["user_response"] == "João Silva"


class TestOnboardingServiceAdvanceStep:
    """Test OnboardingService.advance_step method."""

    @pytest.mark.asyncio
    async def test_advance_step_moves_to_next_step(self, db_session: AsyncSession, test_user: User):
        """advance_step should move to the next step in sequence."""
        from src.services.onboarding import advance_step, start_onboarding

        await start_onboarding(db_session, test_user.id)

        # welcome -> name
        profile = await advance_step(db_session, test_user.id)
        assert profile.onboarding_current_step == "name"

        # name -> goals
        profile = await advance_step(db_session, test_user.id)
        assert profile.onboarding_current_step == "goals"

        # goals -> preferences
        profile = await advance_step(db_session, test_user.id)
        assert profile.onboarding_current_step == "preferences"

        # preferences -> conclusion
        profile = await advance_step(db_session, test_user.id)
        assert profile.onboarding_current_step == "conclusion"

    @pytest.mark.asyncio
    async def test_advance_step_from_conclusion_completes_onboarding(
        self, db_session: AsyncSession, test_user: User
    ):
        """advance_step from conclusion should complete onboarding."""
        from src.services.onboarding import advance_step, start_onboarding

        await start_onboarding(db_session, test_user.id)

        # Advance through all steps to conclusion
        for _ in range(4):  # welcome -> name -> goals -> preferences -> conclusion
            await advance_step(db_session, test_user.id)

        # From conclusion, should complete
        profile = await advance_step(db_session, test_user.id)
        assert profile.onboarding_status == OnboardingStatus.COMPLETED
        assert profile.onboarding_completed_at is not None


class TestOnboardingServiceComplete:
    """Test OnboardingService.complete_onboarding method."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_sets_status(self, db_session: AsyncSession, test_user: User):
        """complete_onboarding should set status to COMPLETED."""
        from src.services.onboarding import complete_onboarding, start_onboarding

        await start_onboarding(db_session, test_user.id)
        profile = await complete_onboarding(db_session, test_user.id)

        assert profile.onboarding_status == OnboardingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_complete_onboarding_sets_completed_at(
        self, db_session: AsyncSession, test_user: User
    ):
        """complete_onboarding should set onboarding_completed_at timestamp."""
        from src.services.onboarding import complete_onboarding, start_onboarding

        await start_onboarding(db_session, test_user.id)
        before = datetime.now(UTC)
        profile = await complete_onboarding(db_session, test_user.id)
        after = datetime.now(UTC)

        assert profile.onboarding_completed_at is not None
        assert before <= profile.onboarding_completed_at <= after


class TestOnboardingServiceTimeout:
    """Test OnboardingService session timeout handling."""

    @pytest.mark.asyncio
    async def test_check_session_timeout_returns_false_for_fresh_session(
        self, db_session: AsyncSession, test_user: User
    ):
        """check_session_timeout should return False for fresh sessions."""
        from src.services.onboarding import check_session_timeout, start_onboarding

        await start_onboarding(db_session, test_user.id)
        was_reset = await check_session_timeout(db_session, test_user.id, max_days=7)

        assert was_reset is False

    @pytest.mark.asyncio
    async def test_check_session_timeout_resets_expired_session(
        self, db_session: AsyncSession, test_user: User
    ):
        """check_session_timeout should reset sessions older than max_days."""
        from src.services.onboarding import check_session_timeout, start_onboarding

        # Start onboarding
        await start_onboarding(db_session, test_user.id)

        # Manually set started_at to 10 days ago
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_started_at = datetime.now(UTC) - timedelta(days=10)
        await db_session.commit()

        # Check timeout
        was_reset = await check_session_timeout(db_session, test_user.id, max_days=7)

        assert was_reset is True

        # Verify state was reset
        await db_session.refresh(profile)
        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
        assert profile.onboarding_started_at is None
        assert profile.onboarding_current_step is None
        assert profile.onboarding_data is None

    @pytest.mark.asyncio
    async def test_check_session_timeout_ignores_completed(
        self, db_session: AsyncSession, test_user: User
    ):
        """check_session_timeout should not reset COMPLETED onboarding."""
        from src.services.onboarding import (
            check_session_timeout,
            complete_onboarding,
            start_onboarding,
        )

        # Start and complete onboarding
        await start_onboarding(db_session, test_user.id)

        # Manually set started_at to 10 days ago
        result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        profile = result.scalar_one()
        profile.onboarding_started_at = datetime.now(UTC) - timedelta(days=10)
        await db_session.commit()

        await complete_onboarding(db_session, test_user.id)

        # Check timeout - should not reset because already completed
        was_reset = await check_session_timeout(db_session, test_user.id, max_days=7)

        assert was_reset is False


class TestOnboardingServiceReset:
    """Test OnboardingService.reset_onboarding method."""

    @pytest.mark.asyncio
    async def test_reset_onboarding_clears_all_fields(
        self, db_session: AsyncSession, test_user: User
    ):
        """reset_onboarding should clear all onboarding fields."""
        from src.services.onboarding import reset_onboarding, start_onboarding

        await start_onboarding(db_session, test_user.id)
        profile = await reset_onboarding(db_session, test_user.id)

        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
        assert profile.onboarding_started_at is None
        assert profile.onboarding_current_step is None
        assert profile.onboarding_data is None

    @pytest.mark.asyncio
    async def test_reset_onboarding_clears_completed_at(
        self, db_session: AsyncSession, test_user: User
    ):
        """reset_onboarding should clear completed_at after completion."""
        from src.services.onboarding import complete_onboarding, reset_onboarding, start_onboarding

        # Complete onboarding first
        await start_onboarding(db_session, test_user.id)
        await complete_onboarding(db_session, test_user.id)

        # Reset should clear completed_at
        profile = await reset_onboarding(db_session, test_user.id)

        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
        assert profile.onboarding_completed_at is None


class TestOnboardingServiceSkip:
    """Test OnboardingService.skip_onboarding method."""

    @pytest.mark.asyncio
    async def test_skip_onboarding_marks_completed(self, db_session: AsyncSession, test_user: User):
        """skip_onboarding should mark onboarding as COMPLETED."""
        from src.services.onboarding import skip_onboarding

        profile = await skip_onboarding(db_session, test_user.id)

        assert profile.onboarding_status == OnboardingStatus.COMPLETED
        assert profile.onboarding_completed_at is not None

    @pytest.mark.asyncio
    async def test_skip_onboarding_raises_if_already_completed(
        self, db_session: AsyncSession, test_user: User
    ):
        """skip_onboarding should raise error if already completed."""
        from src.services.onboarding import skip_onboarding

        # Skip once
        await skip_onboarding(db_session, test_user.id)

        # Try to skip again
        with pytest.raises(HTTPException) as exc_info:
            await skip_onboarding(db_session, test_user.id)

        assert exc_info.value.status_code == 400
