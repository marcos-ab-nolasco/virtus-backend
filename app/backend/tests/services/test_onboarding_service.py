"""Tests for OnboardingService."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.user_profile import OnboardingStatus, UserProfile


class TestCompleteOnboarding:
    """Test complete_onboarding()."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_sets_status(self, db_session: AsyncSession, test_user: User):
        from src.services.onboarding import complete_onboarding

        profile = await complete_onboarding(db_session, test_user.id)
        assert profile.onboarding_status == OnboardingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_complete_onboarding_sets_completed_at(
        self, db_session: AsyncSession, test_user: User
    ):
        from src.services.onboarding import complete_onboarding

        before = datetime.now(UTC)
        profile = await complete_onboarding(db_session, test_user.id)
        after = datetime.now(UTC)

        assert profile.onboarding_completed_at is not None
        assert before <= profile.onboarding_completed_at <= after


class TestOnboardingServiceReset:
    """Test reset_onboarding()."""

    @pytest.mark.asyncio
    async def test_reset_onboarding_clears_all_fields(
        self, db_session: AsyncSession, test_user: User
    ):
        from src.services.onboarding import complete_onboarding, reset_onboarding

        await complete_onboarding(db_session, test_user.id)
        profile = await reset_onboarding(db_session, test_user.id)

        assert profile.onboarding_status == OnboardingStatus.NOT_STARTED
        assert profile.onboarding_started_at is None
        assert profile.onboarding_current_step is None
        assert profile.onboarding_data is None
        assert profile.onboarding_completed_at is None


class TestOnboardingServiceSkip:
    """Test skip_onboarding()."""

    @pytest.mark.asyncio
    async def test_skip_onboarding_marks_completed(self, db_session: AsyncSession, test_user: User):
        from src.services.onboarding import skip_onboarding

        profile = await skip_onboarding(db_session, test_user.id)

        assert profile.onboarding_status == OnboardingStatus.COMPLETED
        assert profile.onboarding_completed_at is not None

    @pytest.mark.asyncio
    async def test_skip_onboarding_raises_if_already_completed(
        self, db_session: AsyncSession, test_user: User
    ):
        from src.services.onboarding import skip_onboarding

        await skip_onboarding(db_session, test_user.id)

        with pytest.raises(HTTPException) as exc_info:
            await skip_onboarding(db_session, test_user.id)

        assert exc_info.value.status_code == 400


class TestMarkStructuredSubmitted:
    """Tests for mark_structured_submitted()."""

    @pytest.mark.asyncio
    async def test_slider_grid_sets_life_areas_submitted(
        self, db_session: AsyncSession, test_user: User
    ):
        from src.services.onboarding import mark_structured_submitted

        await mark_structured_submitted(db_session, test_user.id, "slider_grid")

        profile = await db_session.scalar(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        assert profile.onboarding_data.get("life_areas_submitted") is True

    @pytest.mark.asyncio
    async def test_chip_selector_values_sets_values_submitted(
        self, db_session: AsyncSession, test_user: User
    ):
        from src.services.onboarding import mark_structured_submitted

        await mark_structured_submitted(db_session, test_user.id, "chip_selector_values")

        profile = await db_session.scalar(
            select(UserProfile).where(UserProfile.user_id == test_user.id)
        )
        assert profile.onboarding_data.get("values_submitted") is True

    @pytest.mark.asyncio
    async def test_unknown_type_does_nothing(self, db_session: AsyncSession, test_user: User):
        from src.services.onboarding import mark_structured_submitted

        # Should not raise
        await mark_structured_submitted(db_session, test_user.id, "unknown_type")
